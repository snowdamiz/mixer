
extension WitnessInput {
    func recordHealthy(_ owner: CapabilityGuestUIRuntime, phase: String) async throws {
        let deadline = ContinuousClock.now + .seconds(10)
        while ContinuousClock.now < deadline {
            let health = await owner.recoverySnapshot()
            if health.activation.phase == .healthyGuest {
                let candidate = try need(health.healthy, "Missing healthy candidate")
                let launch = try need(health.activation.launchID, "Missing healthy launch")
                try check(owner.presentation.inputEnabled && health.activation.candidateID == candidate,
                          "Current native presentation did not reach health")
                let names = ["prior", "successor", "rollback", "offline"]
                let index = try need(names.firstIndex(of: phase), "Unknown healthy phase")
                var prior: [ReleaseObservation] = []
                for name in names.prefix(index) {
                    prior.append(try JSONDecoder().decode(ReleaseObservation.self, from: read(root, name + ".json")))
                }
                let pid = ProcessInfo.processInfo.processIdentifier
                try check(!prior.contains { $0.pid == pid || $0.launch == launch }, "Expected fresh process and launch")
                if let previous = prior.last {
                    if phase == "offline" {
                        try check(candidate == previous.candidate, "Cold rollback selected a different candidate")
                    } else {
                        try check(health.previousHealthy == previous.candidate && !prior.contains { $0.candidate == candidate },
                                  "Signed replacement did not advance the same installation")
                    }
                }
                let observation = ReleaseObservation(candidate: candidate, launch: launch, pid: pid)
                try JSONEncoder().encode(observation).write(to: root.appendingPathComponent(phase + ".json"),
                                                            options: .withoutOverwriting)
                return
            }
            try check(!health.requiresReopen && health.activation.terminalCause == nil, "Guest exited before display health")
            try await Task.sleep(for: .milliseconds(25))
        }
        throw UpdateError("f11.witness", "Guest did not reach native display health")
    }
}
