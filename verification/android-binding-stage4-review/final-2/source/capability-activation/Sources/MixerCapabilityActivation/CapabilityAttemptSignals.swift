import Foundation
@_spi(CapabilityLifecycle) import MixerExperimentalCapabilityRuntime
@_spi(GuestUIV1) import MixerGuest
import MixerUpdates

enum CapabilityAttemptLocalStop: Sendable { case cancelled, deadline, closed }
enum CapabilityAttemptFirstCause: Sendable {
    case bridge(ExperimentalCapabilityFailure)
    case local(CapabilityAttemptLocalStop)
}
struct CapabilityAttemptSignalSnapshot: Sendable {
    let generation: UInt64
    let firstCause: CapabilityAttemptFirstCause?
    let firstBridgeFailure: ExperimentalCapabilityFailure?
    let effectsMayHaveOpened: Bool
    let guestUI: GuestUIExchangeSnapshotV1?
    var stopped: Bool { guestUI.map { $0.stop != nil } ?? (firstCause != nil) }
}

/// One dedicated data-only sink per counted attempt. It has no strong reference
/// to an adapter group, construction, session, actor, reservation or cleanup job.
/// Its single buffered notification schedules no Task. The trusted coordinator
/// owns exactly one counted iterator: the buffer limit does not bound additional
/// iterator waiters. That consumer must not strongly retain coordinator/attempt/
/// group/session resources across next(), since a suspended stream continuation
/// could otherwise provide an ownership back-edge. Every unwind/close explicitly
/// finishes and joins the consumer before store close, independently of native
/// drain. Notifications are hints; snapshot is authoritative even when finish
/// races a pending yield. Local stop is recorded before native cancel/close.
final class CapabilityAttemptSignals: CapabilityBridgeTerminalObserver, @unchecked Sendable {
    let generation: UInt64
    let notifications: AsyncStream<Void>
    let guestUI: GuestUIExchangeV1?
    private let continuation: AsyncStream<Void>.Continuation
    private let lock = NSLock()
    private var firstCause: CapabilityAttemptFirstCause?
    private var firstBridgeFailure: ExperimentalCapabilityFailure?
    private var effectsMayHaveOpened = false
    private var notificationSent = false

    init(generation: UInt64, guestUI: GuestUIExchangeV1? = nil) {
        precondition(generation > 0)
        precondition(guestUI == nil || guestUI?.snapshot().generation == generation)
        self.generation = generation; self.guestUI = guestUI
        let stream = AsyncStream<Void>.makeStream(bufferingPolicy: .bufferingNewest(1))
        notifications = stream.stream; continuation = stream.continuation
    }
    func recordTerminalFailure(_ failure: ExperimentalCapabilityFailure) {
        guestUI?.stop(.bridge) // Admission stops before detail publication.
        lock.lock()
        if firstBridgeFailure == nil { firstBridgeFailure = failure }
        if firstCause == nil { firstCause = .bridge(failure) }
        let notify = !notificationSent; notificationSent = true
        lock.unlock()
        if guestUI != nil || notify { signalNotification() }
    }
    func requestStop(_ cause: CapabilityAttemptLocalStop) {
        switch cause {
        case .cancelled: guestUI?.stop(.cancelled)
        case .deadline: guestUI?.stop(.deadline)
        case .closed: guestUI?.stop(.closed)
        }
        lock.lock()
        if firstCause == nil { firstCause = .local(cause) }
        let notify = !notificationSent; notificationSent = true
        lock.unlock()
        if guestUI != nil || notify { signalNotification() }
    }
    /// A bounded coordinator-owned observation timer or ordinary-operation tail
    /// may re-poke the same consumer. This never consumes the first terminal
    /// notification: the consumer must inspect snapshot before acting on a hint.
    /// A stopped attempt still accepts a hint so a busy-consumer handoff cannot
    /// strand its terminal state. Foreign generations cannot schedule work.
    func recordControlWake(expectedGeneration: UInt64) {
        guard expectedGeneration == generation else { return }
        signalNotification()
    }
    var snapshot: CapabilityAttemptSignalSnapshot {
        lock.lock(); defer { lock.unlock() }
        let ui = guestUI?.snapshot()
        var cause = firstCause
        if let ui {
            // The shared guard is authoritative. A bridge tag can precede its
            // checked detail; nil here is unknown, never a fabricated failure.
            switch ui.stop {
            case .bridge: cause = firstBridgeFailure.map(CapabilityAttemptFirstCause.bridge)
            case .cancelled: cause = .local(.cancelled)
            case .deadline: cause = .local(.deadline)
            case .closed: cause = .local(.closed)
            case .protocolViolation, nil: cause = nil
            }
        }
        return CapabilityAttemptSignalSnapshot(generation: generation, firstCause: cause,
            firstBridgeFailure: firstBridgeFailure,
            effectsMayHaveOpened: ui?.effectsMayHaveOpened ?? effectsMayHaveOpened, guestUI: ui)
    }
    /// This lock check is the commit-entry linearization point, not a lock held
    /// across filesystem I/O. A later failure cannot undo an entered transaction;
    /// the store must inspect the latch again before returning a healthy result.
    func requireCommitEntry(expectedGeneration: UInt64) throws {
        lock.lock(); defer { lock.unlock() }
        try requireOpen(expectedGeneration)
    }
    /// Called after encoding and other preparation, immediately before the
    /// durable intent transaction. Even an uncertain write permanently prevents
    /// before-effects fallback for this attempt. This does not enable native I/O.
    func enterEffectsIntentCommit(expectedGeneration: UInt64) throws {
        lock.lock(); defer { lock.unlock() }
        try requireOpen(expectedGeneration)
        guard !effectsMayHaveOpened else { throw UpdateError("capability.activation.effects_intent", "Effects intent already entered") }
        try guestUI?.enterEffectsIntent(generation: expectedGeneration)
        effectsMayHaveOpened = true
    }
    func finishNotifications() { guestUI?.coordinatorWake.finish(); continuation.finish() }
    private func signalNotification() {
        if let guestUI { guestUI.coordinatorWake.signal() }
        else { continuation.yield(()) }
    }
    private func requireOpen(_ expectedGeneration: UInt64) throws {
        guard expectedGeneration == generation else { throw UpdateError("capability.activation.stale", "Attempt generation changed") }
        if let guestUI { try guestUI.requireCommitEntry(generation: expectedGeneration) }
        else if firstCause != nil { throw UpdateError("capability.activation.stopped", "Attempt stopped before commit entry") }
    }
}
