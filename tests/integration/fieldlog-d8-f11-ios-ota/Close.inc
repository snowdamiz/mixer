    func closeReadOnly() async {
        guard phase != "successor", !busy, let owner, let repository, let input, let storage else { return }
        busy = true
        defer { busy = false }
        await owner.close()
        await repository.close()
        self.owner = nil
        self.repository = nil
        do {
            let deadline = ContinuousClock.now + .seconds(4)
            while !owner.ownerRetired && ContinuousClock.now < deadline {
                try await Task.sleep(for: .milliseconds(5))
            }
            let reads = await storage.reads
            let writes = await storage.writeCalls
            try check(owner.ownerRetired && reads == 0 && writes == 0, "Read-only owner did not retire cleanly")
            if phase == "prior" {
                try check(read(input.workspace, "workspace.json") == read(input.packet, "workspace.json"),
                          "Prior mutated the workspace")
            } else {
                _ = try await input.coldCommit()
            }
            status = "Closed " + phase
        } catch { status = "Failed: \(error)" }
    }
