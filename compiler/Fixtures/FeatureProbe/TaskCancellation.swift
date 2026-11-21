#if EXPLICIT_CONCURRENCY_IMPORT
import _Concurrency
#endif

func cancellationStateCode(cancelled: Bool, checkThrew: Bool) -> UInt32 {
    (cancelled ? 1 : 0) | (checkThrew ? 2 : 0)
}

#if EMBEDDED_SCALAR_CONTROL
@_cdecl("task_cancellation_state_code")
public func stateCode(_ cancelled: UInt32, _ checkThrew: UInt32) -> UInt32 {
    cancellationStateCode(cancelled: cancelled != 0, checkThrew: checkThrew != 0)
}
#else
func currentCancellationState() -> UInt32 {
    let cancelled = Task.isCancelled
    do {
        try Task.checkCancellation()
        return cancellationStateCode(cancelled: cancelled, checkThrew: false)
    } catch is CancellationError {
        return cancellationStateCode(cancelled: cancelled, checkThrew: true)
    } catch {
        fatalError("Unexpected cancellation error type")
    }
}

func observeTask(cancel: Bool) async -> (UInt32, UInt32) {
    let (started, start) = AsyncStream<Void>.makeStream()
    let (released, release) = AsyncStream<Void>.makeStream()
    let task = Task {
        let before = currentCancellationState()
        start.finish()
        for await _ in released { }
        return (before, currentCancellationState())
    }
    for await _ in started { }
    if cancel { task.cancel() }
    release.finish()
    return await task.value
}

@main
struct TaskCancellationProbe {
    static func main() async {
        for cancel in [false, true, false] {
            let (before, after) = await observeTask(cancel: cancel)
            print("\(before) \(after)")
        }
    }
}
#endif
