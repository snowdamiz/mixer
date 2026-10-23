import Foundation
@_spi(CapabilityLifecycle) import MixerExperimentalCapabilityRuntime

/// Data-only join sink. It owns no attempt, group, construction, session, actor,
/// callback or Task. Its obligation's reservation must never retain an adapter
/// owner; its retained store worker/stream consumer must have no such back-edge.
final class CapabilityConcreteRetirement: CapabilityBridgeRetirementObserver, @unchecked Sendable {
    private struct State {
        var obligation: CapabilityAdapterObligation?
        var groupExpected = false
        var bridgeRetired = false
        var setupReturned = false
        var methods = 0
        var retiring = false
        var completed = false
        var waiterIssued = false
        var waitCancelled = false
        var waiter: CheckedContinuation<Bool, Never>?
    }
    private let lock = NSLock()
    private var state: State
    init(obligation: CapabilityAdapterObligation) { state = State(obligation: obligation) }

    func expectGroup() { locked { $0.groupExpected = true } }
    func recordRetired() { locked { $0.bridgeRetired = true }; completeIfReady() }
    func setupDidReturn() { locked { $0.setupReturned = true }; completeIfReady() }
    func beginMethod() throws {
        try locked { s in
            guard !s.retiring, !s.completed, s.methods == 0 else { throw concreteAttemptError("busy") }
            s.methods = 1
        }
    }
    func methodDidReturn() { locked { $0.methods = 0 }; completeIfReady() }
    var completed: Bool { locked { $0.completed } }

    /// One fallback waiter, with cancellation latched even before registration.
    /// Cancellation only abandons this wait; it never asserts resource exit.
    func wait() async -> Bool {
        let result = await withTaskCancellationHandler {
            await withCheckedContinuation { continuation in
                let immediate = locked { s -> Bool? in
                    guard !s.waiterIssued else { return false }
                    s.waiterIssued = true
                    if s.waitCancelled || Task.isCancelled { return false }
                    if s.completed { return true }
                    s.waiter = continuation; return nil
                }
                if let immediate { continuation.resume(returning: immediate) }
            }
        } onCancel: { self.cancelWait() }
        return result && !Task.isCancelled && !locked { $0.waitCancelled }
    }
    func cancelWait() {
        let waiter = locked { s in
            s.waitCancelled = true; let waiter = s.waiter; s.waiter = nil; return waiter
        }
        waiter?.resume(returning: false)
    }
    private func completeIfReady() {
        let obligation = locked { s -> CapabilityAdapterObligation? in
            guard !s.completed, !s.retiring, s.setupReturned, s.methods == 0,
                  (!s.groupExpected || s.bridgeRetired), let obligation = s.obligation else { return nil }
            s.retiring = true; s.obligation = nil; return obligation
        }
        guard let obligation else { return }
        // adapterOwner stays nil: this is a bounded pool update, not destruction
        // of an attempt/group. Do not invoke it under the sink's lock.
        obligation.retire()
        let notification = locked { s -> (CheckedContinuation<Bool, Never>?, Bool) in
            s.completed = true
            let waiter = s.waiter; s.waiter = nil
            return (waiter, !s.waitCancelled)
        }
        // A true result is published only after reservation.retire returned and
        // cleared adapterRetiring, so the same reservation can admit fallback.
        notification.0?.resume(returning: notification.1)
    }
    private func locked<T>(_ body: (inout State) throws -> T) rethrows -> T {
        lock.lock(); defer { lock.unlock() }; return try body(&state)
    }
}
