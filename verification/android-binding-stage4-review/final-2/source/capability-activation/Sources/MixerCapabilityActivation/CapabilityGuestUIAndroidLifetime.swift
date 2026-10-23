#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
import Foundation
@_spi(GuestUIV1) import MixerGuest
import CMixerUITransport
import CMixerUIAndroidHostBridge

struct CapabilityAndroidHostLifetimeKey: Sendable, Equatable {
    let facade: UInt64
    let lifetime: CapabilityPresentationLifetimeID
    let endpoint: UInt64
    fileprivate init(facade: UInt64, lifetime: CapabilityPresentationLifetimeID, endpoint: UInt64) {
        self.facade = facade; self.lifetime = lifetime; self.endpoint = endpoint
    }
}
final class CapabilityAndroidHostLifetimeCapsule: @unchecked Sendable {
    private let lock = NSLock()
    private var start: CapabilityAndroidHostLifetimeStart?
    fileprivate init(key: CapabilityAndroidHostLifetimeKey, task: Task<Void, Never>, control: CapabilityAndroidLifetimeControl) {
        start = CapabilityAndroidHostLifetimeStart(key: key, task: task, control: control)
    }
    func takeForCommonLifetime() -> CapabilityAndroidHostLifetimeStart? {
        lock.lock(); defer { lock.unlock() }; let result = start; start = nil; return result
    }
    deinit { start?.control.abandon() }
}
struct CapabilityAndroidHostLifetimeStart: Sendable {
    let key: CapabilityAndroidHostLifetimeKey
    let task: Task<Void, Never>
    let control: CapabilityAndroidLifetimeControl
    fileprivate init(key: CapabilityAndroidHostLifetimeKey, task: Task<Void, Never>, control: CapabilityAndroidLifetimeControl) {
        self.key = key; self.task = task; self.control = control
    }
}
enum CapabilityAndroidHostNativeJoinResult: Sendable, Equatable {
    case retired(CapabilityAndroidHostEndpointRetirementEvidence), quarantined(CapabilityAndroidHostFailure)
}
struct CapabilityAndroidHostEndpointRetirementEvidence: Sendable, Equatable {
    let key: CapabilityAndroidHostLifetimeKey
    let callbackFence: UInt64
    let uiEntryFence: UInt64
    let facadeCleanup: CapabilityAndroidHostFacadeCleanupEvidence?
    fileprivate init(key: CapabilityAndroidHostLifetimeKey, callbackFence: UInt64, uiEntryFence: UInt64,
                     facadeCleanup: CapabilityAndroidHostFacadeCleanupEvidence?) {
        self.key = key; self.callbackFence = callbackFence; self.uiEntryFence = uiEntryFence; self.facadeCleanup = facadeCleanup
    }
}

fileprivate struct CapabilityAndroidDelivery: Sendable {
    let generation: UInt64
    let reader: GuestUIWakeConsumerV1
}
fileprivate enum CapabilityAndroidBindOutcome: Sendable { case bound(CapabilityAndroidDelivery), stopped }
private struct CapabilityAndroidCompletion: Sendable {
    let kind: UInt32
    let result: Int32
}
private final class CapabilityAndroidRendezvous: @unchecked Sendable {
    let waiter: UInt64
    let requested: UInt32
    private var continuation: CheckedContinuation<Void, Never>?
    private var result: CapabilityAndroidCompletion?
    private let lock = NSLock()
    init(waiter: UInt64, requested: UInt32, continuation: CheckedContinuation<Void, Never>) {
        self.waiter = waiter; self.requested = requested; self.continuation = continuation
    }
    func consume(kind: UInt32, result: Int32) -> CheckedContinuation<Void, Never>? {
        lock.lock(); defer { lock.unlock() }
        guard self.result == nil, kind == requested || (requested == UInt32(MXUIT_PRESENT.rawValue) && kind == UInt32(MXUIT_RETIRE.rawValue)) else { return nil }
        self.result = CapabilityAndroidCompletion(kind: kind, result: result)
        let outgoing = continuation; continuation = nil; return outgoing
    }
    var completion: CapabilityAndroidCompletion? { lock.lock(); defer { lock.unlock() }; return result }
}

/// Allocated while the Swift endpoint record is reserved, before C acquire.
/// It is an empty data-only bind-or-close gate, never a Task or owner callback.
final class CapabilityAndroidReservedBindGate: @unchecked Sendable {
    fileprivate let lock = NSLock()
    fileprivate var started = false
    fileprivate var closing = false
    fileprivate var bound = false
    fileprivate var binding = false
    fileprivate weak var exchange: GuestUIExchangeV1?
    fileprivate var delivery: CapabilityAndroidDelivery?
    fileprivate var waiter: CheckedContinuation<CapabilityAndroidBindOutcome, Never>?
    fileprivate init() {}
}

/// One fixed Task/control per endpoint. No resource alias, packet, frame, native
/// object or caller callback is retained in this class or across suspension.
final class CapabilityAndroidLifetimeControl: @unchecked Sendable {
    let key: CapabilityAndroidHostLifetimeKey
    let facadeSlot: Int
    private let gate: CapabilityAndroidReservedBindGate
    private var lock: NSLock { gate.lock }
    private var started: Bool { get { gate.started } set { gate.started = newValue } }
    private var closing: Bool { get { gate.closing } set { gate.closing = newValue } }
    private var bound: Bool { get { gate.bound } set { gate.bound = newValue } }
    private var binding: Bool { get { gate.binding } set { gate.binding = newValue } }
    private var exchange: GuestUIExchangeV1? { get { gate.exchange } set { gate.exchange = newValue } }
    private var delivery: CapabilityAndroidDelivery? { get { gate.delivery } set { gate.delivery = newValue } }
    private var bindWaiter: CheckedContinuation<CapabilityAndroidBindOutcome, Never>? { get { gate.waiter } set { gate.waiter = newValue } }
    private var fault: Int32 = 0
    private var waiterSerial: UInt64 = 0
    private var rendezvous: CapabilityAndroidRendezvous?
    private enum Terminal { case pending, retired, failed(CapabilityAndroidHostFailureCode) }
    private var terminal = Terminal.pending
    private var joinStarted = false
    private var joinResult: CapabilityAndroidHostNativeJoinResult?
    private var retirementEvidence: CapabilityAndroidHostEndpointRetirementEvidence?
    private init(_ acquired: CapabilityAndroidAcquiredEndpoint) {
        key = CapabilityAndroidHostLifetimeKey(facade: acquired.facade, lifetime: acquired.lifetime, endpoint: acquired.endpoint)
        facadeSlot = acquired.facadeSlot; gate = acquired.gate
    }
    @inline(never)
    static func reserveBindGate() -> CapabilityAndroidReservedBindGate { CapabilityAndroidReservedBindGate() }
    static func spawn(_ acquired: CapabilityAndroidAcquiredEndpoint) throws -> CapabilityAndroidHostLifetimeCapsule {
        guard acquired.take() else { throw coldStartError("android_endpoint_consumed") }
        let control = CapabilityAndroidLifetimeControl(acquired)
        // This is the only Task creation, immediately after successful acquire.
        let task = Task { await control.run() }
        let capsule = CapabilityAndroidHostLifetimeCapsule(key: control.key, task: task, control: control)
        let accepted = CapabilityAndroidRegistry.shared.publishControl(control)
        control.start(accepted: accepted)
        return capsule
    }
    private func start(accepted: Bool) {
        lock.lock(); started = true
        if !accepted { fault = Int32(MXUIT_IO.rawValue); closing = true }
        let outgoing = (closing || delivery != nil) ? bindWaiter : nil
        let outcome: CapabilityAndroidBindOutcome = closing ? .stopped : delivery.map { .bound($0) } ?? .stopped
        if outgoing != nil { bindWaiter = nil; delivery = nil }
        lock.unlock(); outgoing?.resume(returning: outcome)
    }
    func bind(_ incoming: GuestUIExchangeV1) throws {
        let reader = try incoming.deliveryWake.takeConsumer()
        let descriptor = CapabilityAndroidDelivery(generation: incoming.snapshot().generation, reader: reader)
        lock.lock()
        guard !bound, fault == 0, !closing else { lock.unlock(); incoming.stop(.closed); throw coldStartError("android_bind_state") }
        bound = true; binding = true; exchange = incoming
        lock.unlock()
        do {
            // The gate cannot release its pre-bind Task while this synchronous
            // counted setup alias exists. Close latches and stops the exchange.
            try CapabilityGuestUIAndroidResources.installExchange(incoming, key: key, slot: facadeSlot)
            let closed = completeBind(descriptor)
            if closed { incoming.stop(.closed); throw coldStartError("android_bind_closed") }
        } catch {
            _ = completeBind(nil); incoming.stop(.closed); requestStop(.closed); throw error
        }
    }
    private func completeBind(_ descriptor: CapabilityAndroidDelivery?) -> Bool {
        lock.lock(); binding = false
        if descriptor == nil { closing = true }
        if !closing { delivery = descriptor }
        let outgoing = started ? bindWaiter : nil
        let outcome: CapabilityAndroidBindOutcome = closing ? .stopped : descriptor.map { .bound($0) } ?? .stopped
        if outgoing != nil { bindWaiter = nil; delivery = nil }
        let closed = closing; lock.unlock()
        outgoing?.resume(returning: outcome); return closed
    }
    func requestStop(_ cause: CapabilityAttemptLocalStop) {
        lock.lock(); closing = true; let exchange = exchange
        let outgoing = started && !binding ? bindWaiter : nil
        if outgoing != nil { bindWaiter = nil; delivery = nil }
        lock.unlock()
        exchange?.stop(.closed)
        _ = mxuit_begin_close(key.endpoint)
        outgoing?.resume(returning: .stopped)
    }
    func transportFault(_ code: Int32) {
        lock.lock(); if fault == 0 { fault = code }; closing = true
        let exchange = exchange; let bind = bindWaiter; bindWaiter = nil; delivery = nil
        let native = rendezvous; lock.unlock()
        exchange?.stop(.bridge)
        bind?.resume(returning: .stopped)
        native?.consume(kind: native!.requested, result: Int32(MXUIT_DRAIN_FAILED.rawValue))?.resume()
    }
    func abandon() {
        CapabilityAndroidRegistry.shared.quarantine(slot: facadeSlot, facade: key.facade)
        requestStop(.closed)
    }
    private func waitForBind() async -> CapabilityAndroidBindOutcome {
        await withCheckedContinuation { incoming in
            lock.lock()
            if started && closing && !binding { lock.unlock(); incoming.resume(returning: .stopped) }
            else if started, let descriptor = delivery { delivery = nil; lock.unlock(); incoming.resume(returning: .bound(descriptor)) }
            else { precondition(bindWaiter == nil); bindWaiter = incoming; lock.unlock() }
        }
    }
    private var stopped: Bool { lock.lock(); defer { lock.unlock() }; return closing || fault != 0 }
    private var hasFault: Bool { lock.lock(); defer { lock.unlock() }; return fault != 0 }
    @inline(never)
    private func finishTask(_ result: Terminal) { lock.lock(); terminal = result; lock.unlock() }
    private func run() async {
        let initial = await waitForBind()
        if hasFault { finishTask(.failed(.transportIO)); return }
        if case .bound(let descriptor) = initial {
            while !stopped {
                do { guard try await descriptor.reader.next() else { break } }
                catch { requestStop(.closed); break }
                if stopped { break }
                // Every ordinary PRESENT consumes one real delivery hint first.
                let hint = mxuit_hint(key.endpoint)
                if hint != Int32(MXUIT_OK.rawValue) { requestStop(.closed); break }
                guard let completion = await request(kind: UInt32(MXUIT_PRESENT.rawValue)) else { finishTask(.failed(.identityExhausted)); return }
                if completion.kind == UInt32(MXUIT_RETIRE.rawValue) {
                    finishTask(completion.result == Int32(MXUIT_DRAIN_OK.rawValue) ? .retired : .failed(.retireFailed)); return
                }
                if completion.result != Int32(MXUIT_DRAIN_OK.rawValue) { requestStop(.closed); break }
            }
        }
        if hasFault { finishTask(.failed(.transportIO)); return }
        requestStop(.closed)
        guard let completion = await request(kind: UInt32(MXUIT_RETIRE.rawValue)) else { finishTask(.failed(.identityExhausted)); return }
        finishTask(completion.kind == UInt32(MXUIT_RETIRE.rawValue) && completion.result == Int32(MXUIT_DRAIN_OK.rawValue) ? .retired : .failed(.retireFailed))
    }
    @inline(never)
    private func reserveWaiter(kind: UInt32, continuation: CheckedContinuation<Void, Never>) -> CapabilityAndroidRendezvous? {
        lock.lock(); defer { lock.unlock() }
        guard fault == 0, rendezvous == nil, waiterSerial < .max else { return nil }
        waiterSerial += 1
        let token = CapabilityAndroidRendezvous(waiter: waiterSerial, requested: kind, continuation: continuation)
        rendezvous = token; return token
    }
    private func request(kind: UInt32) async -> CapabilityAndroidCompletion? {
        // The exact token is published before C, including synchronous completion.
        var token: CapabilityAndroidRendezvous?
        await withCheckedContinuation { continuation in
            guard let reserved = reserveWaiter(kind: kind, continuation: continuation) else { continuation.resume(); return }
            token = reserved
            let result = mxuit_request(key.endpoint, reserved.waiter)
            if result != Int32(MXUIT_OK.rawValue) { reserved.consume(kind: kind, result: Int32(MXUIT_DRAIN_FAILED.rawValue))?.resume() }
        }
        guard let token else { return nil }
        clearRendezvous(token)
        return token.completion
    }
    private func clearRendezvous(_ token: CapabilityAndroidRendezvous) {
        lock.lock(); if rendezvous === token { rendezvous = nil }; lock.unlock()
    }
    func matches(waiter: UInt64, kind: UInt32) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard let token = rendezvous, token.waiter == waiter, token.completion == nil else { return false }
        return token.requested == kind || (token.requested == UInt32(MXUIT_PRESENT.rawValue) && kind == UInt32(MXUIT_RETIRE.rawValue))
    }
    func complete(waiter: UInt64, kind: UInt32, result: Int32) {
        lock.lock(); let token = rendezvous?.waiter == waiter ? rendezvous : nil; lock.unlock()
        token?.consume(kind: kind, result: result)?.resume()
    }
    private func beginJoin(_ returned: CapabilityAndroidHostTaskReturnEvidence) -> CapabilityAndroidHostNativeJoinResult? {
        lock.lock(); defer { lock.unlock() }
        guard returned.key == key else { return .quarantined(.init(key: key, code: .invalidState)) }
        if let joinResult { return joinResult }
        guard !joinStarted else { return .quarantined(.init(key: key, code: .invalidState)) }
        joinStarted = true
        switch terminal {
        case .retired: return nil
        case .failed(let code): return .quarantined(.init(key: key, code: code))
        case .pending: return .quarantined(.init(key: key, code: .invalidState))
        }
    }
    private func publishJoin(_ result: CapabilityAndroidHostNativeJoinResult) -> CapabilityAndroidHostNativeJoinResult {
        lock.lock(); if joinResult == nil { joinResult = result }; let value = joinResult!; lock.unlock(); return value
    }
    func joinNative(after returned: CapabilityAndroidHostTaskReturnEvidence) async -> CapabilityAndroidHostNativeJoinResult {
        if let early = beginJoin(returned) { return publishJoin(early) }
        // This assertion is unreachable before the common actual Task.value.
        let joined = mxuit_consumer_joined(key.endpoint)
        guard joined == Int32(MXUIT_OK.rawValue) else { return failedJoin(.transportIO) }
        let reclaimed = await CapabilityAndroidProgress.shared.waitEndpoint(key, slot: facadeSlot)
        guard reclaimed == Int32(MXUIT_OK.rawValue) else { return failedJoin(reclaimed == Int32(MXUIT_EXHAUSTED.rawValue) ? .identityExhausted : .transportIO) }
        var snapshot = mxuit_snapshot()
        guard mxuit_inspect(&snapshot) == Int32(MXUIT_OK.rawValue),
              let record = CapabilityAndroidRegistry.shared.record(slot: facadeSlot, facade: key.facade) else { return failedJoin(.invalidState) }
        let cleanup = record.withLock { $0.cleanup?.key == key ? $0.cleanup : nil }
        let evidence = CapabilityAndroidHostEndpointRetirementEvidence(key: key, callbackFence: snapshot.fenced_epoch,
            uiEntryFence: snapshot.ui_entry_fenced, facadeCleanup: cleanup)
        retainRetirement(evidence)
        guard CapabilityAndroidRegistry.shared.removeEndpoint(key, slot: facadeSlot) else { return failedJoin(.invalidState) }
        return publishJoin(.retired(evidence))
    }
    private func retainRetirement(_ evidence: CapabilityAndroidHostEndpointRetirementEvidence) {
        lock.lock(); retirementEvidence = evidence; lock.unlock()
    }
    private func failedJoin(_ code: CapabilityAndroidHostFailureCode) -> CapabilityAndroidHostNativeJoinResult {
        CapabilityAndroidRegistry.shared.quarantine(slot: facadeSlot, facade: key.facade)
        return publishJoin(.quarantined(.init(key: key, code: code)))
    }
}
#endif
