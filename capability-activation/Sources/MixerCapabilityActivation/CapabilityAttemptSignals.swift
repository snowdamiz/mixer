import Foundation
@_spi(CapabilityLifecycle) import MixerExperimentalCapabilityRuntime
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
    var stopped: Bool { firstCause != nil }
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
    private let continuation: AsyncStream<Void>.Continuation
    private let lock = NSLock()
    private var firstCause: CapabilityAttemptFirstCause?
    private var firstBridgeFailure: ExperimentalCapabilityFailure?
    private var effectsMayHaveOpened = false
    private var notificationSent = false

    init(generation: UInt64) {
        precondition(generation > 0)
        self.generation = generation
        let stream = AsyncStream<Void>.makeStream(bufferingPolicy: .bufferingNewest(1))
        notifications = stream.stream; continuation = stream.continuation
    }
    func recordTerminalFailure(_ failure: ExperimentalCapabilityFailure) {
        lock.lock()
        if firstBridgeFailure == nil { firstBridgeFailure = failure }
        if firstCause == nil { firstCause = .bridge(failure) }
        let notify = !notificationSent; notificationSent = true
        lock.unlock()
        if notify { continuation.yield(()) }
    }
    func requestStop(_ cause: CapabilityAttemptLocalStop) {
        lock.lock()
        if firstCause == nil { firstCause = .local(cause) }
        let notify = !notificationSent; notificationSent = true
        lock.unlock()
        if notify { continuation.yield(()) }
    }
    var snapshot: CapabilityAttemptSignalSnapshot {
        lock.lock(); defer { lock.unlock() }
        return CapabilityAttemptSignalSnapshot(generation: generation, firstCause: firstCause,
            firstBridgeFailure: firstBridgeFailure, effectsMayHaveOpened: effectsMayHaveOpened)
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
        effectsMayHaveOpened = true
    }
    func finishNotifications() { continuation.finish() }
    private func requireOpen(_ expectedGeneration: UInt64) throws {
        guard expectedGeneration == generation else { throw UpdateError("capability.activation.stale", "Attempt generation changed") }
        guard firstCause == nil else { throw UpdateError("capability.activation.stopped", "Attempt stopped before commit entry") }
    }
}
