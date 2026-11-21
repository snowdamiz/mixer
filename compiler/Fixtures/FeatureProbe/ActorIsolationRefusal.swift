actor ChecklistProgress {
    func count() -> UInt32 { 0 }
}

func refresh(_ progress: ChecklistProgress) -> UInt32 {
    progress.count()
}
