import Foundation

/// A fixed data-only coalescing wake. It creates no tasks and holds no owners.
@_spi(GuestUIV1) public final class GuestUIWakeV1: Sendable {
    private let state = GuestUIWakeStateV1()
    init() {}
    public func takeConsumer() throws -> GuestUIWakeConsumerV1 {
        try state.issue(); return GuestUIWakeConsumerV1(state: state)
    }
    public func signal() { state.signal() }
    public func finish() { state.finish() }
    // Read-only internal test observation; never an executor or injection hook.
    var hasWaitingConsumer: Bool { state.hasWaitingConsumer }
}
@_spi(GuestUIV1) public final class GuestUIWakeConsumerV1: Sendable {
    private let state: GuestUIWakeStateV1
    fileprivate init(state: GuestUIWakeStateV1) { self.state = state }
    /// Explicit source finish owns lifetime. Task cancellation alone does not
    /// silently discard the one waiter or its final retirement hint.
    public func next() async throws -> Bool {
        try await withCheckedThrowingContinuation { state.wait($0) }
    }
}
private final class GuestUIWakeStateV1: @unchecked Sendable {
    private let lock = NSLock()
    private var issued = false
    private var pending = false
    private var finished = false
    private var waiter: CheckedContinuation<Bool, any Error>?
    var hasWaitingConsumer: Bool {
        lock.lock(); defer { lock.unlock() }; return waiter != nil
    }
    func issue() throws {
        lock.lock(); defer { lock.unlock() }
        guard !issued else { throw GuestUIControlRejectionV1.consumerAlreadyIssued }
        issued = true
    }
    func wait(_ incoming: CheckedContinuation<Bool, any Error>) {
        let result: Result<Bool, any Error>?
        lock.lock()
        if waiter != nil { result = .failure(GuestUIControlRejectionV1.readerBusy) }
        else if pending { pending = false; result = .success(true) }
        else if finished { result = .success(false) }
        else { waiter = incoming; result = nil }
        lock.unlock()
        if let result { incoming.resume(with: result) }
    }
    func signal() {
        lock.lock()
        guard !finished else { lock.unlock(); return }
        let outgoing = waiter; waiter = nil
        if outgoing == nil { pending = true }
        lock.unlock()
        outgoing?.resume(returning: true)
    }
    func finish() {
        lock.lock()
        finished = true
        let outgoing = waiter; waiter = nil
        let hint = pending
        if outgoing != nil { pending = false }
        lock.unlock()
        outgoing?.resume(returning: hint)
    }
}
