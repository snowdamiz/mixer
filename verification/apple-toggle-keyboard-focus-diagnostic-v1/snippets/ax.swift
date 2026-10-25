    private var focusDiagnosticObservations: [[String: Any]] = []
    private var focusDiagnosticObservationsDropped = 0
    private func ax(_ diagnosticPhase: String = "other") throws -> [String: Any] {
        guard let app else { throw Failure.invalidResponse }
        let observationStarted = now
        var rows: [String: Any] = [:]
        var rowTimes: [[String: Any]] = []
        for id in ids {
            let rowStarted = now
            let element = app.descendants(matching: .any)[id].firstMatch
            guard element.waitForExistence(timeout: 2) else { throw Failure.focus("Fixed native element absent: " + id) }
            rows[id] = ["identifier": element.identifier, "exists": element.exists, "hittable": element.isHittable,
                        "enabled": element.isEnabled, "selected": element.isSelected, "hasFocus": element.hasFocus,
                        "label": element.label, "frame": rectangle(element.frame)]
            rowTimes.append(["identifier": id, "startedUptime": rowStarted, "finishedUptime": now])
        }
        // The witness remains its original closed shape, including its end time.
        let observedUptime = ProcessInfo.processInfo.systemUptime
        let foreground = app.state == .runningForeground
        if focusDiagnosticObservations.count < 4 {
            focusDiagnosticObservations.append(["phase": diagnosticPhase, "atomic": false, "startedUptime": observationStarted,
                "finishedUptime": now, "witnessUptime": observedUptime, "rows": rowTimes])
        } else { focusDiagnosticObservationsDropped += 1 }
        return ["uptime": observedUptime, "appForeground": foreground, "elements": rows]
    }
    private func focusOnlyDiagnostic(_ actionDeadline: Double) -> [String: Any] {
        let started = now
        let deadline = min(actionDeadline, started + 0.250)
        var rows: [[String: Any]] = []
        if let app {
            for id in ids {
                guard now < deadline else { break }
                let rowStarted = now
                let element = app.descendants(matching: .any)[id].firstMatch
                let focused = element.hasFocus
                let rowFinished = now
                rows.append(["identifier": id, "hasFocus": focused, "startedUptime": rowStarted, "finishedUptime": rowFinished])
                if rowFinished >= deadline { break }
            }
        }
        let finished = now
        return ["atomic": false, "startedUptime": started, "finishedUptime": finished, "deadlineUptime": deadline, "rows": rows,
                "captureStatus": rows.count == ids.count && finished <= deadline ? "complete" : "incomplete-budget"]
    }
