#if canImport(Dispatch)
import Dispatch
#endif

/// The installed host's serial execution domain for one or more mounts.
package struct FeatureExecutor: Sendable {
    let isCurrent: @Sendable () -> Bool

    /// The host must provide a side-effect-free check safe to call from any
    /// context. It must identify the current serial domain, including across
    /// synchronous handoffs that stay on the same thread.
    package init(isCurrent: @escaping @Sendable () -> Bool) {
        self.isCurrent = isCurrent
    }

    #if canImport(Dispatch)
    /// The queue must be serial. Queues targeting it share its serial domain.
    package init(serialQueue: DispatchQueue) {
        let identity = DispatchExecutorIdentity(queue: serialQueue)
        self.init { identity.isCurrent }
    }
    #endif
}

#if canImport(Dispatch)
// Dispatch synchronizes queue-specific storage. The key and queue are immutable.
private final class DispatchExecutorIdentity: @unchecked Sendable {
    private let queue: DispatchQueue
    private let key = DispatchSpecificKey<Bool>()

    init(queue: DispatchQueue) {
        self.queue = queue
        queue.setSpecific(key: key, value: true)
    }

    deinit { queue.setSpecific(key: key, value: nil) }

    var isCurrent: Bool { DispatchQueue.getSpecific(key: key) == true }
}
#endif
