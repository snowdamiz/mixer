import Foundation

// Independently authored host language-semantics probe. This is not an Android
// binding, a substitute transport, or a release-qualification fixture.
private final class Owner: @unchecked Sendable {
    private let destroyed: Flag
    init(_ destroyed: Flag) { self.destroyed = destroyed }
    deinit { destroyed.set() }
}

private final class WeakOwner: @unchecked Sendable {
    private let lock = NSLock()
    private weak var value: Owner?
    func assign(_ owner: Owner) { lock.lock(); value = owner; lock.unlock() }
    var alive: Bool { lock.lock(); defer { lock.unlock() }; return value != nil }
}

private final class Cell: @unchecked Sendable {
    private let lock = NSLock()
    private var waiter: CheckedContinuation<Void, Never>?
    let parked = DispatchSemaphore(value: 0)
    func wait() async {
        await withCheckedContinuation { incoming in
            lock.lock()
            precondition(waiter == nil)
            waiter = incoming
            lock.unlock()
            parked.signal()
        }
    }
    func take() -> CheckedContinuation<Void, Never> {
        lock.lock(); defer { lock.unlock() }
        let result = waiter!
        waiter = nil
        return result
    }
}

private func require(_ condition: Bool, _ message: String) {
    if !condition { fatalError(message) }
}
private func wait(_ semaphore: DispatchSemaphore, _ label: String) {
    require(semaphore.wait(timeout: .now() + 5) == .success, "timeout: " + label)
}

@inline(never)
private func makeParkedTask(_ cell: Cell, _ weak: WeakOwner, _ destroyed: Flag) -> Task<Void, Never> {
    let owner = Owner(destroyed)
    weak.assign(owner)
    return Task.detached {
        await cell.wait()
        withExtendedLifetime(owner) {}
    }
}

private func continuationTail() async {
    let cell = Cell(), weak = WeakOwner(), destroyed = Flag()
    let task = makeParkedTask(cell, weak, destroyed)
    wait(cell.parked, "suspended task registered")
    require(weak.alive, "a continuation retains the task's explicit owner across its suspension")
    let progressResumed = DispatchSemaphore(value: 0)
    let releaseProgressTail = DispatchSemaphore(value: 0)
    let progressReturned = DispatchSemaphore(value: 0)
    DispatchQueue.global().async {
        let continuation = cell.take()
        continuation.resume()
        progressResumed.signal()
        wait(releaseProgressTail, "release process-only progress tail")
        // Keep the actual continuation value alive while the resumed task exits.
        withExtendedLifetime(continuation) {}
        progressReturned.signal()
    }
    wait(progressResumed, "progress resumed continuation")
    await task.value
    require(!weak.alive, "resumed continuation copy must not pin completed task owner on this toolchain")
    require(destroyed.isSet, "the captured owner's deinit must have executed before releasing the progress tail")
    releaseProgressTail.signal()
    wait(progressReturned, "progress tail returned")
    print("PASS continuation_tail: parked continuation retains owner; actual Task.value and captured owner deinit complete while copied resumed continuation and process-only hook tail remain held")
}

private final class Flag: @unchecked Sendable {
    private let lock = NSLock()
    private var value = false
    func set() { lock.lock(); value = true; lock.unlock() }
    var isSet: Bool { lock.lock(); defer { lock.unlock() }; return value }
}

private func actualTaskJoin() async {
    let cell = Cell(), weak = WeakOwner(), resultPublished = Flag(), joinReturned = Flag()
    let owner = Owner(Flag())
    weak.assign(owner)
    let task = Task.detached { [owner] in
        resultPublished.set()
        await cell.wait()
        withExtendedLifetime(owner) {}
    }
    wait(cell.parked, "task body tail held")
    let joiner = Task.detached {
        await task.value
        joinReturned.set()
    }
    require(resultPublished.isSet, "body result should already be published")
    require(!joinReturned.isSet, "an early result must not substitute for actual Task.value")
    cell.take().resume()
    await joiner.value
    require(joinReturned.isSet, "actual join should finish after held tail leaves")
    withExtendedLifetime(owner) {}
    print("PASS actual_task_join: early terminal data did not satisfy Task.value while task tail was held")
}

@main
private struct Main {
    static func main() async {
        switch CommandLine.arguments.dropFirst().first {
        case "continuation_tail": await continuationTail()
        case "actual_task_join": await actualTaskJoin()
        default: fatalError("expected exactly one known case")
        }
    }
}
