import Foundation
@_spi(GuestUIV1) import MixerGuest

enum CapabilityColdStartOperationKind { case opening, download, start, milestone }
final class CapabilityColdStartOperation: @unchecked Sendable {
    let kind: CapabilityColdStartOperationKind
    private let lock = NSLock()
    private var cancelled = false
    init(_ kind: CapabilityColdStartOperationKind) { self.kind = kind }
    func cancel() { lock.lock(); cancelled = true; lock.unlock() }
    func check() throws {
        lock.lock(); let value = cancelled; lock.unlock()
        if value { throw CancellationError() }
        try Task.checkCancellation()
    }
}

final class CapabilityColdStartObservation: @unchecked Sendable {
    let signals: CapabilityAttemptSignals
    let consumer: Task<Void, Never>
    var timer: CapabilityColdStartObservationTimer?
    private let lock = NSLock()
    private var presentation: CapabilityPresentationInstallation?
    private var finishing = false
    private var finished = false
    private var result: CapabilityPresentationJoinStatus?
    init(signals: CapabilityAttemptSignals, consumer: Task<Void, Never>) { self.signals = signals; self.consumer = consumer }
    func install(_ value: CapabilityPresentationInstallation) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard !finishing, !finished, presentation == nil, let moved = value.move() else { return false }
        presentation = moved; return true
    }
    private func beginFinish() -> (Bool, CapabilityPresentationInstallation?, CapabilityPresentationJoinStatus?) {
        lock.lock(); defer { lock.unlock() }
        if finished { return (false, nil, result) }
        if finishing { return (false, nil, .pending) }
        finishing = true
        let moved = presentation?.move()
        if presentation != nil, moved == nil {
            result = .invariant(.wrongJoinOwner); finishing = false; finished = true
            return (false, nil, result)
        }
        presentation = nil
        return (true, moved, nil)
    }
    private func complete(_ result: CapabilityPresentationJoinStatus?) {
        lock.lock(); self.result = result; finishing = false; finished = true; lock.unlock()
    }
    func finish() async -> CapabilityPresentationJoinStatus? {
        let (first, presentation, early) = beginFinish()
        guard first else { return early }
        signals.guestUI?.stop(.closed)
        timer?.cancel()
        signals.finishNotifications()
        if let timer { await timer.waitForCancellation() }
        await consumer.value
        let result = await presentation?.finish()
        complete(result); return result
    }
}

/// No actor, group or session is retained by the notification stream's consumer.
/// Its inner callback temporarily loads this weak reference and returns before
/// the consumer waits for another event.
final class CapabilityColdStartWeakWorker: @unchecked Sendable {
    private let lock = NSLock()
    private weak var value: CapabilityColdStartWorker?
    init(_ worker: CapabilityColdStartWorker) { value = worker }
    func load() -> CapabilityColdStartWorker? { lock.lock(); defer { lock.unlock() }; return value }
}

/// The facade's synchronous admission/stop boundary. Captures are taken only
/// after ordinary/cancellation admission. Callbacks and native stop run outside
/// this lock. Reservation-retained store workers cannot point back to this owner.
final class CapabilityColdStartControl: @unchecked Sendable {
    let reservation: CapabilityAttemptReservation
    private let lock = NSLock()
    private var ordinary: CapabilityColdStartOperation?
    private var cancellation: CapabilityColdStartOperation?
    private var ordinaryJoin: CheckedContinuation<Void, Never>?
    private var closed = false
    private var selected = false
    private var notificationBusy = false
    private var pendingWake = false
    private var phase: CapabilityActivationPhase = .idle
    private var candidateID: String?
    private var launchID: String?
    private var lastSignal: CapabilityAttemptSignalSnapshot?
    private var lastSignalObject: CapabilityAttemptSignals?
    private var observation: CapabilityColdStartObservation?
    private var endingObservation: CapabilityColdStartObservation?
    private var concrete: CapabilityConcreteAttempt?
    private var retirementWait: CapabilityConcreteRetirement?
    private var lastRetirement: CapabilityConcreteRetirement?
    private var consumedActive = false
    private var store: CapabilityRecoveryStore?
    private var finalRecovery = CapabilityRecoverySnapshot()
    init(reservation: CapabilityAttemptReservation) { self.reservation = reservation }
    func admit(_ kind: CapabilityColdStartOperationKind) throws -> CapabilityColdStartOperation {
        lock.lock(); defer { lock.unlock() }
        guard !closed else { throw coldStartError("closed") }
        guard ordinary == nil, cancellation == nil, !notificationBusy else { throw coldStartError("busy") }
        guard observation?.signals.snapshot.stopped != true else { throw coldStartError("terminal") }
        switch kind {
        case .opening: break
        case .download: guard !selected else { throw coldStartError("selection_started") }
        case .start:
            guard !selected else { throw coldStartError("selection_started") }
            selected = true; phase = .starting
        case .milestone:
            guard phase == .provisionalGuest || phase == .healthyGuest else { throw coldStartError("not_observing") }
        }
        let op = CapabilityColdStartOperation(kind); ordinary = op; return op
    }
    func admitCancellation() throws -> CapabilityColdStartOperation {
        lock.lock()
        guard !closed, !selected else { lock.unlock(); throw coldStartError("selection_started") }
        guard cancellation == nil, !notificationBusy else { lock.unlock(); throw coldStartError("busy") }
        let op = CapabilityColdStartOperation(.download), old = ordinary
        cancellation = op; lock.unlock(); old?.cancel(); return op
    }
    func finish(_ op: CapabilityColdStartOperation, cancellationPath: Bool = false) {
        lock.lock()
        if cancellationPath { if cancellation === op { cancellation = nil } }
        else if ordinary === op { ordinary = nil }
        let join = ordinary == nil && cancellation == nil ? ordinaryJoin : nil
        if join != nil { ordinaryJoin = nil }
        let wake = pendingWake && !closed ? observation?.signals : nil
        if wake != nil { pendingWake = false }
        lock.unlock()
        join?.resume()
        if let wake { wake.recordControlWake(expectedGeneration: wake.generation) }
    }
    func requireCurrent(_ op: CapabilityColdStartOperation) throws {
        try op.check()
        lock.lock(); let valid = !closed && (ordinary === op || cancellation === op); lock.unlock()
        guard valid else { throw coldStartError("closed") }
    }
    func installStore(_ store: CapabilityRecoveryStore) -> Bool {
        lock.lock(); self.store = store; let open = !closed; lock.unlock()
        if !open { store.requestStop() }
        return open
    }
    func acceptPreparedPresentation(_ binding: CapabilityGuestUIPresentationBinding,
                                    installation: CapabilityPresentationInstallation) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard !closed else { return false }
        return binding.acceptPrepared(installation)
    }
    func installObservation(_ signals: CapabilityAttemptSignals, worker: CapabilityColdStartWorker,
                            candidate: String, launch: String, op: CapabilityColdStartOperation) throws {
        let box = CapabilityColdStartWeakWorker(worker), stream = signals.notifications, generation = signals.generation
        let reader = try signals.guestUI?.coordinatorWake.takeConsumer()
        lock.lock(); defer { lock.unlock() }
        guard !closed, ordinary === op, observation == nil, endingObservation == nil else { throw coldStartError("closed") }
        let consumer = Task.detached {
            if let reader {
                // Reader owns only its data queue; no exchange/signals/worker
                // survives the inner helper across the next suspension.
                while (try? await reader.next()) == true {
                    await CapabilityColdStartWorker.handleNotificationOwned(box, generation: generation)
                }
            } else {
                for await _ in stream {
                    await CapabilityColdStartWorker.handleNotificationOwned(box, generation: generation)
                }
            }
        }
        observation = CapabilityColdStartObservation(signals: signals, consumer: consumer)
        lastSignalObject = nil; lastSignal = nil
        candidateID = candidate; launchID = launch; phase = .starting
    }
    func installPresentationLifetime(_ installation: CapabilityPresentationInstallation, signals: CapabilityAttemptSignals,
                                     op: CapabilityColdStartOperation) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard !closed, ordinary === op, observation?.signals === signals, let observation,
              let exchange = signals.guestUI, installation.lifetime?.isBound(to: exchange) == true else { return false }
        return observation.install(installation)
    }
    func installConcrete(_ value: CapabilityConcreteAttempt, signals: CapabilityAttemptSignals) throws {
        lock.lock(); let valid = !closed && concrete == nil && observation?.signals === signals
        if valid { concrete = value; lastRetirement = nil }; lock.unlock()
        guard valid else { value.stop(); throw coldStartError("closed") }
    }
    func concreteForMethod() throws -> CapabilityConcreteAttempt {
        lock.lock(); defer { lock.unlock() }
        guard !closed, let concrete else { throw coldStartError("closed") }; return concrete
    }
    func armTimer(seconds: UInt64, signals: CapabilityAttemptSignals) throws {
        lock.lock(); defer { lock.unlock() }
        guard !closed, observation?.signals === signals, observation?.timer == nil else { throw coldStartError("closed") }
        // One fixed source is installed atomically with close, before it can
        // become an unregistered cancellation-join obligation.
        observation?.timer = try CapabilityColdStartObservationTimer(seconds: seconds, signals: signals)
    }
    func setPhase(_ next: CapabilityActivationPhase) {
        lock.lock(); if !closed { phase = next }; lock.unlock()
    }
    func markConsumed(_ value: Bool) { lock.lock(); consumedActive = value; lock.unlock() }
    func beginNotification(_ generation: UInt64) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard !closed, observation?.signals.generation == generation else { return false }
        guard ordinary == nil, cancellation == nil, !notificationBusy else { pendingWake = true; return false }
        notificationBusy = true; return true
    }
    func finishNotification() { lock.lock(); notificationBusy = false; lock.unlock() }
    func clearPendingWake() { lock.lock(); pendingWake = false; lock.unlock() }
    var timerFired: Bool { lock.lock(); let timer = observation?.timer; lock.unlock(); return timer?.fired == true }
    var isClosed: Bool { lock.lock(); defer { lock.unlock() }; return closed }
    func stopConcrete(cause: CapabilityAttemptLocalStop = .closed) -> CapabilityConcreteRetirement? {
        stopConcreteOwned(cause)
    }
    private func stopConcreteOwned(_ cause: CapabilityAttemptLocalStop) -> CapabilityConcreteRetirement? {
        lock.lock(); let value = concrete; concrete = nil; lock.unlock()
        let retirement = value?.stop(cause: cause)
        lock.lock(); if let retirement { lastRetirement = retirement }; lock.unlock()
        return retirement
    }
    func detachObservation() -> CapabilityColdStartObservation? {
        lock.lock(); defer { lock.unlock() }
        let old = observation ?? endingObservation
        if let old { lastSignal = old.signals.snapshot; lastSignalObject = old.signals }
        observation = nil; endingObservation = nil; pendingWake = false; return old
    }
    func endObservationFromConsumer() {
        lock.lock()
        let old = observation
        if let old { lastSignal = old.signals.snapshot; lastSignalObject = old.signals; endingObservation = old }
        observation = nil; pendingWake = false; lock.unlock()
        // Never join this consumer from its own handler. The counted closing
        // owner later joins both this Task and timer cancellation completion.
        old?.timer?.cancel(); old?.signals.finishNotifications()
    }
    func setRetirementWait(_ value: CapabilityConcreteRetirement?) {
        lock.lock(); retirementWait = value; let cancel = closed; lock.unlock()
        if cancel { value?.cancelWait() }
    }
    func requestClose(_ cause: CapabilityAttemptLocalStop) {
        lock.lock()
        closed = true; phase = .closed
        let signal = (observation ?? endingObservation)?.signals, value = concrete, wait = retirementWait
        let old = ordinary, cancel = cancellation, store = store
        let stopStore = !consumedActive
        concrete = nil; lock.unlock()
        signal?.requestStop(cause) // Before native cancellation or closing I/O.
        old?.cancel(); cancel?.cancel(); wait?.cancelWait()
        let retirement = value?.stop(cause: cause)
        lock.lock(); if let retirement { lastRetirement = retirement }; lock.unlock()
        if stopStore { store?.requestStop() }
    }
    func waitForOrdinaryTail() async {
        await withCheckedContinuation { continuation in
            lock.lock()
            if ordinary == nil && cancellation == nil { lock.unlock(); continuation.resume() }
            else { precondition(ordinaryJoin == nil); ordinaryJoin = continuation; lock.unlock() }
        }
    }
    func storeDidClose(_ recovery: CapabilityRecoverySnapshot) {
        lock.lock(); finalRecovery = recovery; let old = store; store = nil; lock.unlock()
        withExtendedLifetime(old) {}
    }
    var recoverySnapshot: CapabilityRecoverySnapshot {
        lock.lock(); let current = store, final = finalRecovery; lock.unlock()
        return current?.snapshot ?? final
    }
    var guestUISnapshot: CapabilityGuestUIActivationSnapshot {
        let base = snapshot
        lock.lock()
        let signal = (observation ?? endingObservation)?.signals.snapshot ?? lastSignalObject?.snapshot ?? lastSignal
        lock.unlock()
        return CapabilityGuestUIActivationSnapshot(base, ui: signal?.guestUI)
    }
    var snapshot: CapabilityActivationSnapshot {
        lock.lock()
        var currentPhase = phase
        let candidate = candidateID, launch = launchID, stopped = closed
        let signal = (observation ?? endingObservation)?.signals.snapshot ?? lastSignalObject?.snapshot ?? lastSignal
        let waiting = lastRetirement
        lock.unlock()
        let recovery = recoverySnapshot
        if !stopped, [.starting, .provisionalGuest, .healthyGuest].contains(currentPhase), signal?.stopped == true {
            currentPhase = signal?.effectsMayHaveOpened == true ? .recoveryRequired : .stopping
        }
        let cause: CapabilityColdStartTerminalCause?
        switch signal?.firstCause {
        case .local(.cancelled): cause = .cancelled
        case .local(.deadline): cause = .deadline
        case .local(.closed): cause = .closed
        case .bridge(let failure): cause = .bridge(failure)
        case nil: cause = nil
        }
        return CapabilityActivationSnapshot(phase: currentPhase, candidateID: candidate, launchID: launch,
            acceptedSequence: recovery.acceptedSequence, effectsMayHaveOpened: signal?.effectsMayHaveOpened == true,
            terminalCause: cause, firstBridgeFailure: signal?.firstBridgeFailure,
            requiresReopen: recovery.requiresReopen,
            cleanupPending: (stopped && !reservation.isReleased) || (waiting != nil && waiting?.completed == false))
    }
}
