#if EXPLICIT_CONCURRENCY_IMPORT
import _Concurrency
#endif

actor ChecklistProgress {
    private var completed: UInt32 = 0

    func complete() -> UInt32 {
        completed += 1
        return completed
    }

    func count() -> UInt32 {
        completed
    }
}

@MainActor
func refresh(_ progress: ChecklistProgress) async -> UInt32 {
    await progress.count()
}

@main
struct ActorProbe {
    @MainActor
    static func main() async {
        let progress = ChecklistProgress()
        print(await refresh(progress))
        print(await progress.complete())
        print(await refresh(progress))
    }
}
