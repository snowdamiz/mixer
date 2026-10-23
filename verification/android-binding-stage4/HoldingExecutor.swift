import Foundation
import Dispatch

/// Test scheduler of actual Swift jobs. It supplies no product outcome, Task,
/// resource callback or cleanup authority to the engine.
@available(macOS 15.0, *)
final class HoldingExecutor: TaskExecutor, @unchecked Sendable {
    private let queue = DispatchQueue(label: "mixer.stage4.test-executor")
    private let lock = NSLock()
    private var paused = false
    private var pending: [UnownedJob] = []
    private var enqueued = 0
    func enqueue(_ job: consuming ExecutorJob) {
        let unowned = UnownedJob(job)
        lock.lock(); enqueued += 1
        if paused { pending.append(unowned); lock.unlock(); return }
        lock.unlock(); run(unowned)
    }
    private func run(_ job: UnownedJob) {
        queue.async { job.runSynchronously(on: self.asUnownedTaskExecutor()) }
    }
    func pause() { lock.lock(); paused = true; lock.unlock() }
    func runOneAndPause() {
        lock.lock(); precondition(paused && !pending.isEmpty); let job = pending.removeFirst(); lock.unlock()
        run(job)
    }
    func resume() {
        lock.lock(); paused = false; let jobs = pending; pending.removeAll(); lock.unlock()
        for job in jobs { run(job) }
    }
    var heldJobs: Int { lock.lock(); defer { lock.unlock() }; return pending.count }
    var totalJobs: Int { lock.lock(); defer { lock.unlock() }; return enqueued }
}
