import XCTest
import Foundation
import CoreFoundation
import UIKit
import CryptoKit

private final class SettingsTelemetry: @unchecked Sendable {
    static let shared = SettingsTelemetry()
    private let chunkBytes = 4992
    let fixedCase = "public-settings-full-keyboard-access"
    private var generation = ""
    private var sequence = 0
    private var transport = DiagnosticTransportState()
    private let firstFailureDiagnostic = SettingsFirstFailureDiagnostic()
    private let lock = NSRecursiveLock()
    private final class Box: @unchecked Sendable { var data: Data?; var status: Int?; var error: Error? }
    enum Failure: Error { case budget, bridge, upload, setup(String) }
    private var now: Double { ProcessInfo.processInfo.systemUptime }
    private func post(_ record: [String: Any]) throws -> [String: Any] {
        var context = SettingsPostFailureContext(requestOrdinal: transport.requests + 1, beginUptime: now,
                                                 absoluteDeadlineUptime: transport.deadline)
        func diagnose(_ branch: SettingsPostFailureBranch, status: Int? = nil, errorCode: Int? = nil) {
            firstFailureDiagnostic.record(record, context: context, endUptime: now, branch: branch, status: status, errorCode: errorCode)
        }
        let remaining: Double
        do { remaining = try transport.begin(now: context.beginUptime) }
        catch {
            switch error {
            case DiagnosticTransportFailure.deadline: diagnose(.beginDeadline)
            case DiagnosticTransportFailure.requestLimit: diagnose(.beginRequestLimit)
            default: diagnose(.beginPriorFailure)
            }
            throw error
        }
        context.actualAllowanceSeconds = remaining
        let env = ProcessInfo.processInfo.environment
        guard let base = env["MIXER_BRIDGE_URL"], let cap = env["MIXER_BRIDGE_CAPABILITY"], let url = URL(string: base + "/evaluate") else { diagnose(.configuration); throw Failure.bridge }
        let body: Data
        do { body = try JSONSerialization.data(withJSONObject: ["settingsDiagnostic": record], options: [.sortedKeys, .withoutEscapingSlashes]) }
        catch { diagnose(.serialization, errorCode: (error as NSError).code); throw error }
        guard body.count <= 8192 else { diagnose(.bodyLimit); throw Failure.upload }
        var request = URLRequest(url: url, timeoutInterval: remaining)
        request.httpMethod = "POST"; request.httpBody = body
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(cap, forHTTPHeaderField: "X-Mixer-Capability")
        let box = Box(); let done = DispatchSemaphore(value: 0)
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            box.data = data; box.status = (response as? HTTPURLResponse)?.statusCode; box.error = error; done.signal()
        }
        context.taskIdentifier = task.taskIdentifier
        task.resume()
        guard done.wait(timeout: .now() + remaining) == .success else {
            task.cancel()
            let originalFailure = transport.latch(.network("request timeout within existing2second budget"))
            diagnose(.semaphoreExpiration)
            throw originalFailure
        }
        do { return try transport.response(status: box.status, data: box.data, networkError: box.error.map { String(describing: $0) }) }
        catch {
            // Only the successful semaphore path reads the completed callback box.
            switch error {
            case DiagnosticTransportFailure.network: diagnose(.foundationError, status: box.status, errorCode: (box.error as NSError?)?.code)
            case DiagnosticTransportFailure.http: diagnose(.httpRejection, status: box.status)
            default: diagnose(.invalidResponse, status: box.status)
            }
            throw error
        }
    }
    func start() throws {
        lock.lock(); defer { lock.unlock() }
        let initial = now; transport.deadline = initial + 29.0
        let result = try post(["kind": "start", "case": fixedCase, "uptime": initial, "chunkBytes": chunkBytes])
        guard let format = result["chunkBytes"] as? NSNumber,
              CFGetTypeID(format) != CFBooleanGetTypeID(),
              ["s", "i", "l", "q", "S", "I", "L", "Q"].contains(String(cString: format.objCType)),
              format.intValue == chunkBytes,
              let token = result["generation"] as? String, let remaining = result["remainingSessionSeconds"] as? Double else { throw Failure.bridge }
        generation = token; transport.deadline = min(transport.deadline, now + remaining)
    }
    private func send(_ fields: [String: Any]) throws -> [String: Any] {
        sequence += 1
        var value = fields
        value["case"] = fixedCase; value["generation"] = generation; value["sequence"] = sequence; value["uptime"] = now
        return try post(value)
    }
    func mark(_ stage: String, _ detail: [String: Any] = [:]) throws {
        lock.lock(); defer { lock.unlock() }
        _ = try send(["kind": "mark", "stage": stage, "detail": detail])
        print("MIXER_SETTINGS_DIAGNOSTIC " + stage)
    }
    func bestEffortMark(_ stage: String) { do { try mark(stage) } catch { print("MIXER_SETTINGS_DIAGNOSTIC_UNAVAILABLE " + stage + " " + String(describing: error)) } }
    func observe(_ stage: String, routeIndex: Int, attempt: Int, snapshot: [String: Any], started: Double, finished: Double, ax: Data?, png: Data?, routeWitness: [String: Any]? = nil, switchWitness: [String: Any]? = nil) throws -> Int {
        lock.lock(); defer { lock.unlock() }
        var files: [String: Any] = [:]; var payloads: [String: Data] = [:]
        for (form, payload, limit) in [("ax", ax, 200_000), ("png", png, 2_000_000)] {
            if let payload {
                guard payload.count > 0, payload.count <= limit else { throw Failure.upload }
                let digest = SHA256.hash(data: payload).map { String(format: "%02x", $0) }.joined()
                files[form] = ["bytes": payload.count, "sha256": digest]; payloads[form] = payload
            }
        }
        var record: [String: Any] = ["kind": "observe", "stage": stage, "routeIndex": routeIndex, "attempt": attempt,
                               "captureStartedUptime": started, "captureFinishedUptime": finished, "snapshot": snapshot, "files": files]
        if let routeWitness { record["routeWitness"] = routeWitness }
        if let switchWitness { record["switchWitness"] = switchWitness }
        let eventSequence = sequence + 1
        let result = try send(record)
        guard let slots = result["pending"] as? [String] else { throw Failure.bridge }
        for slot in slots {
            let form = slot.hasSuffix("-ax") ? "ax" : "png"
            guard let payload = payloads[form], let descriptor = files[form] as? [String: Any] else { throw Failure.upload }
            let count = (payload.count + chunkBytes - 1) / chunkBytes
            for index in 0..<count {
                let chunk = payload.subdata(in: index * chunkBytes..<min(payload.count, (index + 1) * chunkBytes))
                _ = try send(["kind": "chunk", "slot": slot, "index": index, "count": count, "bytes": payload.count,
                              "sha256": descriptor["sha256"]!, "data": chunk.base64EncodedString()])
            }
        }
        return eventSequence
    }
}

private final class CompletionObserver: NSObject, XCTestObservation {
    func testCaseDidFinish(_ testCase: XCTestCase) { if testCase.name.contains("test000PublicSettingsFullKeyboardAccess") { SettingsTelemetry.shared.bestEffortMark("test-case-finished") } }
}

/// Proven public Settings setup followed by the six original keyboard cases.
@MainActor final class ToggleUITests: XCTestCase {
    private var app: XCUIApplication?
    private let diagnostic = "dev.mixer.verification.authoredtoggle.diagnostics"
    private static var settingsReady = false
    private var caseName = ""

    private static let observer = CompletionObserver()
    private static var registered = false
    private let telemetry = SettingsTelemetry.shared
    private var now: Double { ProcessInfo.processInfo.systemUptime }
    override func setUpWithError() throws {
        continueAfterFailure = true
        if !Self.registered { XCTestObservationCenter.shared.addTestObserver(Self.observer); Self.registered = true }
    }
    override func tearDownWithError() throws { app?.terminate(); app = nil }

    private func bridge(_ op: String, _ fields: [String: Any] = [:]) throws -> [String: Any] {
        let env = ProcessInfo.processInfo.environment
        guard let endpoint = env["MIXER_BRIDGE_URL"], let capability = env["MIXER_BRIDGE_CAPABILITY"],
              let url = URL(string: endpoint + "/" + op) else { throw Failure.invalidBridge }
        var request = URLRequest(url: url, timeoutInterval: 12)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(capability, forHTTPHeaderField: "X-Mixer-Capability")
        request.httpBody = try JSONSerialization.data(withJSONObject: fields, options: [.sortedKeys])
        let done = DispatchSemaphore(value: 0)
        let box = ResponseBox()
        URLSession.shared.dataTask(with: request) { data, response, error in
            box.data = data; box.status = (response as? HTTPURLResponse)?.statusCode; box.error = error
            done.signal()
        }.resume()
        guard done.wait(timeout: .now() + 13) == .success else { throw Failure.timeout }
        if let error = box.error { throw error }
        guard let data = box.data, data.count <= 2_000_000,
              let result = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw Failure.invalidResponse }
        guard box.status == 200 else {
            throw Failure.bridgeRejected(status: box.status, reason: result["error"] as? String ?? "Unavailable bridge reason; inspect durable bridge failure receipt")
        }
        return result
    }
    private enum Failure: Error { case invalidBridge, invalidResponse, timeout, geometry
        case bridgeRejected(status: Int?, reason: String)
        case settings(String), focus(String) }
    private final class ResponseBox: @unchecked Sendable { var data: Data?; var status: Int?; var error: Error? }

    private let ids = ["authored-toggle", "plain-uibutton-reference", "next-focus"]
    private func jsonAttachment(_ name: String, _ value: [String: Any]) throws {
        let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .prettyPrinted])
        let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
    private func snapshot(_ settings: XCUIApplication, _ target: XCUIElement) -> [String: Any] {
        let exists = target.exists
        let frame = exists ? target.frame : .zero
        let identifier = exists ? target.identifier : ""
        let label = exists ? target.label : ""
        let elementType = exists ? Int(target.elementType.rawValue) : 0
        let hittable = exists && target.isHittable
        let enabled = exists && target.isEnabled
        let raw = exists ? target.value : nil
        let observed = now
        return ["bundle": "com.apple.Preferences", "foreground": settings.state == .runningForeground, "appState": Int(settings.state.rawValue),
                "observedUptime": observed, "identifier": identifier, "label": label, "elementType": elementType,
                "exists": exists, "hittable": hittable, "enabled": enabled,
                "valueKind": !exists ? "absent" : raw is String ? "string" : "unsupported", "value": raw as? String ?? "",
                "frame": ["x": frame.minX, "y": frame.minY, "width": frame.width, "height": frame.height]]
    }
    private struct SwitchQuery: PublicSwitchQuery {
        let settings: XCUIApplication
        let takeSnapshot: (XCUIElement) -> [String: Any]
        private var parents: XCUIElementQuery {
            settings.switches.matching(NSPredicate(format: "identifier == %@ AND label == %@", "FKAEnabledSwitch", "Full Keyboard Access"))
        }
        func parentCount() -> Int { parents.count }
        func parent(at index: Int) -> XCUIElement { parents.element(boundBy: index) }
        func childSwitchCount(_ parent: XCUIElement) -> Int { parent.children(matching: .switch).count }
        func childSwitch(_ parent: XCUIElement, at index: Int) -> XCUIElement { parent.children(matching: .switch).element(boundBy: index) }
        func descendantSwitchCount(_ leaf: XCUIElement) -> Int { leaf.descendants(matching: .switch).count }
        func snapshot(_ element: XCUIElement) -> [String: Any] { takeSnapshot(element) }
        func screenFrame() -> [String: Double] {
            let f = settings.frame
            return ["x": f.minX, "y": f.minY, "width": f.width, "height": f.height]
        }
    }
    private func resolveSwitch(_ settings: XCUIApplication) throws -> PublicSwitchSelection.Resolved<XCUIElement> {
        try PublicSwitchSelection.resolve(SwitchQuery(settings: settings, takeSnapshot: { self.snapshot(settings, $0) }))
    }
    private struct SwitchCapture { let state: [String: Any]; let witness: [String: Any]; let sequence: Int; let finished: Double }
    @discardableResult private func captureSwitch(_ settings: XCUIApplication, stage: String, image: Bool = false, tree: Bool = true) throws -> SwitchCapture {
        let started = now
        let resolved = try resolveSwitch(settings)
        let ax = tree ? Data(settings.debugDescription.utf8) : nil
        let png = image ? settings.screenshot().pngRepresentation : nil
        let finished = now
        let sequence = try telemetry.observe(stage, routeIndex: 3, attempt: 0, snapshot: resolved.parentState, started: started, finished: finished, ax: ax, png: png, switchWitness: resolved.witness)
        return SwitchCapture(state: resolved.parentState, witness: resolved.witness, sequence: sequence, finished: finished)
    }
    private struct Capture { let state: [String: Any]; let targetState: [String: Any]?; let sequence: Int }
    private struct RouteTarget { let container: XCUIElement; let target: XCUIElement; let searchSequence: Int }
    @discardableResult private func capture(_ settings: XCUIApplication, _ raw: XCUIElement, stage: String, route: Int = 3, attempt: Int = 0, image: Bool = false, tree: Bool = true, target: XCUIElement? = nil, relation: String? = nil, destination: XCUIElement? = nil) throws -> Capture {
        let started = now
        let state = snapshot(settings, raw)
        var witness: [String: Any]?; var targetState: [String: Any]?
        if let target, let relation {
            let fresh = relation == "self" ? state : snapshot(settings, target)
            targetState = fresh; witness = ["target": fresh, "relation": relation]
        }
        if let destination { witness = ["destination": snapshot(settings, destination)] }
        let ax = tree ? Data(settings.debugDescription.utf8) : nil
        let png = image ? settings.screenshot().pngRepresentation : nil
        let finished = now
        let sequence = try telemetry.observe(stage, routeIndex: route, attempt: attempt, snapshot: state, started: started, finished: finished, ax: ax, png: png, routeWitness: witness)
        return Capture(state: state, targetState: targetState, sequence: sequence)
    }
    private func row(_ settings: XCUIApplication, _ label: String, index: Int) throws -> RouteTarget {
        for attempt in 0...5 {
            let cell = settings.cells.containing(.staticText, identifier: label).firstMatch
            let container: XCUIElement; let target: XCUIElement; let relation: String
            if cell.exists {
                container = cell
                let text = cell.descendants(matching: .staticText)[label].firstMatch
                target = text.exists ? text : cell.descendants(matching: .button)[label].firstMatch
                relation = "descendant"
            } else {
                target = settings.staticTexts[label].firstMatch; container = target; relation = "self"
            }
            let seen = try capture(settings, container, stage: "route-search", route: index, attempt: attempt, target: target, relation: relation)
            if let state = seen.targetState, state["exists"] as? Bool == true, state["hittable"] as? Bool == true, state["enabled"] as? Bool == true {
                return RouteTarget(container: container, target: target, searchSequence: seen.sequence)
            }
            if attempt < 5 { settings.swipeUp() }
        }
        throw SettingsTelemetry.Failure.setup("Required public Settings row absent or not actionable")
    }
    func test000PublicSettingsFullKeyboardAccess() throws {
        Self.settingsReady = false
        try telemetry.start()
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        settings.launch()
        defer {
            telemetry.bestEffortMark("terminate-before")
            settings.terminate()
            telemetry.bestEffortMark("terminate-after")
        }
        let control = settings.switches.matching(NSPredicate(format: "identifier == %@ AND label == %@", "FKAEnabledSwitch", "Full Keyboard Access")).firstMatch
        var terminalRecorded = false
        do {
            try telemetry.mark("settings-launched")
            guard settings.wait(for: .runningForeground, timeout: 5) else { throw SettingsTelemetry.Failure.setup("Settings did not foreground") }
            for (index, label) in ["Accessibility", "Keyboards & Typing", "Full Keyboard Access"].enumerated() {
                let row = try row(settings, label, index: index)
                let targetState = snapshot(settings, row.target)
                let started = now; row.target.tap(); let finished = now
                try telemetry.mark("route-tap", ["routeIndex": index, "searchSequence": row.searchSequence, "target": targetState, "startedUptime": started, "finishedUptime": finished])
                try capture(settings, row.container, stage: "route-opened", route: index, destination: settings.navigationBars[label].firstMatch)
            }
            guard control.waitForExistence(timeout: 3), control.isHittable else { throw SettingsTelemetry.Failure.setup("Public switch unavailable") }
            let before = try captureSwitch(settings, stage: "before-switch", image: true)
            guard let initial = before.state["value"] as? String, before.state["valueKind"] as? String == "string", ["0", "1"].contains(initial) else { throw SettingsTelemetry.Failure.setup("Public switch value unavailable") }
            // Re-query and snapshot after the before capture/uploads. The host binds
            // these fresh public handles/frames/values to that exact before record.
            let actionTarget = try resolveSwitch(settings)
            let started = now
            try PublicSwitchSelection.validateAction(actionTarget, beforeParent: before.state, beforeWitness: before.witness, beforeFinished: before.finished, started: started)
            let finished: Double
            if initial == "0" {
                actionTarget.leaf.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
                finished = now
            } else { finished = started }
            let anchor = initial == "0" ? finished : before.state["observedUptime"] as! Double
            let end = anchor + 3.0
            try telemetry.mark("switch-action", ["action": initial == "0" ? "tap" : "no-tap", "anchorUptime": anchor, "deadlineUptime": end, "beforeSequence": before.sequence, "parent": actionTarget.parentState, "switchWitness": actionTarget.witness, "startedUptime": started, "finishedUptime": finished])
            let after = try captureSwitch(settings, stage: "after-switch", image: true)
            var observedEnabled = initial == "1" || (after.state["value"] as? String == "1" && (after.state["observedUptime"] as! Double) <= end)
            var polls = 0
            while now < end && !observedEnabled && polls < 40 {
                RunLoop.current.run(until: Date(timeIntervalSinceNow: min(0.05, max(0, end - now))))
                guard now < end else { break }
                let state = try captureSwitch(settings, stage: "poll", tree: false)
                observedEnabled = state.state["valueKind"] as? String == "string" && state.state["value"] as? String == "1" && (state.state["observedUptime"] as! Double) <= end
                polls += 1
            }
            let terminal = try captureSwitch(settings, stage: "terminal", image: true)
            terminalRecorded = true
            guard observedEnabled && terminal.state["value"] as? String == "1" else { throw SettingsTelemetry.Failure.setup("Full Keyboard Access did not enable within unchanged3second public observation window") }
            // Emit qualification evidence only after the measured terminal capture
            // and the unchanged within-window assertion above have succeeded.
            let tree = settings.debugDescription
            guard tree.utf8.count <= 200_000 else { throw Failure.settings("Settings observation exceeded fixed bound") }
            try jsonAttachment("Public Settings setup-enabled", ["schema": "mixer.apple-toggle.keyboard-settings.1", "step": "setup-enabled",
                "uptime": now, "bundle": "com.apple.Preferences", "passed": true,
                "route": ["Accessibility", "Keyboards & Typing", "Full Keyboard Access"],
                "fullKeyboardAccessValue": terminal.state["value"]!, "terminalSnapshot": terminal.state,
                "terminalSwitchWitness": terminal.witness, "observedEnabledWithinWindow": observedEnabled, "tree": tree])
            let picture = XCTAttachment(screenshot: settings.screenshot())
            picture.name = "Public Settings setup-enabled"; picture.lifetime = .keepAlways; add(picture)
            Self.settingsReady = true
            print("MIXER_SETTINGS_SETUP measured and asserted; dependent cases await host handoff")
        } catch {
            let originalSetupError = error
            print("MIXER_SETTINGS_DIAGNOSTIC first setup error " + String(describing: originalSetupError))
            if !terminalRecorded { do { try captureSwitch(settings, stage: "terminal", image: true) } catch { print("MIXER_SETTINGS_DIAGNOSTIC terminal evidence incomplete " + String(describing: error)) } }
            throw originalSetupError
        }
    }
    private func launchCase(_ name: String, initial: Bool) throws -> XCUIApplication {
        guard Self.settingsReady else { throw XCTSkip("Public Settings setup did not pass; dependent application input remains unrun") }
        caseName = name
        let target = XCUIApplication(bundleIdentifier: diagnostic); target.terminate()
        _ = try bridge("begin", ["candidate": "diagnostic", "case": name])
        target.launch(); guard target.wait(for: .runningForeground, timeout: 5) else { throw Failure.timeout }
        app = target; _ = try bridge("ready")
        for command in ["resume", "reset"] + (initial ? ["set-on"] : []) { _ = try bridge("command", ["command": command]) }
        return target
    }
    private func rectangle(_ f: CGRect) -> [String: Double] { ["x": f.minX, "y": f.minY, "width": f.width, "height": f.height] }
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
    private func focus(_ snapshot: [String: Any]) throws -> String? {
        guard let rows = snapshot["elements"] as? [String: [String: Any]] else { throw Failure.invalidResponse }
        let names = ids.filter { rows[$0]?["hasFocus"] as? Bool == true }
        guard names.count <= 1 else { throw Failure.focus("Multiple native elements report focus") }
        return names.first
    }
    @discardableResult private func key(_ phase: String, _ value: String, expectedFocus: String? = nil, expectedSelection: Bool? = nil, requiredFocusBefore: String? = nil) throws -> [String: Any] {
        guard let app else { throw Failure.invalidResponse }
        let toggle = app.descendants(matching: .any)["authored-toggle"].firstMatch
        let baseline = try bridge("baseline", ["action": "native-keyboard", "geometry": ["app": rectangle(app.frame), "target": rectangle(toggle.frame)]])
        focusDiagnosticObservations = []; focusDiagnosticObservationsDropped = 0
        let before = try ax("before")
        if let requiredFocusBefore {
            let observedFocus = try focus(before)
            let premisePassed = observedFocus == requiredFocusBefore
            try jsonAttachment("Reference first-Tab precondition", ["schema": "mixer.apple-focus-reference-precondition.1",
                "case": caseName, "phase": phase, "generation": baseline["generation"]!, "actionIndex": baseline["actionIndex"]!,
                "requiredFocus": requiredFocusBefore, "observedFocus": observedFocus as Any? ?? NSNull(),
                "passed": premisePassed, "actionInjectionCount": 0, "before": before])
            guard premisePassed else { throw Failure.focus("Reference first-Tab precondition failed before key injection") }
        }
        try jsonAttachment("Before public key " + phase, ["case": caseName, "phase": phase, "key": value, "generation": baseline["generation"]!, "actionIndex": baseline["actionIndex"]!, "before": before])
        let start = ProcessInfo.processInfo.systemUptime
        if value == "shift-tab" { app.typeKey(XCUIKeyboardKey.tab, modifierFlags: [.shift]) }
        else { app.typeKey(value == "space" ? XCUIKeyboardKey.space : XCUIKeyboardKey.tab, modifierFlags: []) }
        let finished = ProcessInfo.processInfo.systemUptime
        var after = try ax("after-primary"); let end = ProcessInfo.processInfo.systemUptime + 1
        while ProcessInfo.processInfo.systemUptime < end {
            let matchesFocus = try expectedFocus == nil || focus(after) == expectedFocus
            let matchesSelection = expectedSelection == nil || toggle.isSelected == expectedSelection
            if matchesFocus && matchesSelection { break }
            RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.05)); after = try ax("after-poll")
        }
        let witness: [String: Any] = ["case": caseName, "generation": baseline["generation"]!, "actionIndex": baseline["actionIndex"]!,
            "phase": phase, "key": value, "publicAPI": "XCUIElement.typeKey(_:modifierFlags:)", "returned": true,
            "before": before, "startedUptime": start, "finishedUptime": finished, "after": after]
        try jsonAttachment("Public keyboard " + phase, witness)
        // This one follow-up cannot choose the authoritative sample or alter its verdict.
        let followUp = focusOnlyDiagnostic((before["uptime"] as! Double) + 12.0)
        var focusDiagnostic: [String: Any] = ["schema": "mixer.apple-toggle.focus-diagnostic.1", "authoritative": false,
            "case": caseName, "generation": baseline["generation"]!, "actionIndex": baseline["actionIndex"]!,
            "atomic": false, "observations": focusDiagnosticObservations, "observationsDropped": focusDiagnosticObservationsDropped, "followUp": followUp]
        if let bytes = try? JSONSerialization.data(withJSONObject: focusDiagnostic), bytes.count <= 4096 {}
        else { focusDiagnostic = ["schema": "mixer.apple-toggle.focus-diagnostic.1", "authoritative": false,
            "case": caseName, "generation": baseline["generation"]!, "actionIndex": baseline["actionIndex"]!,
            "captureStatus": "incomplete-record-size", "observationsDropped": focusDiagnosticObservationsDropped] }
        let result = try bridge("evaluate", ["keyboardWitness": witness, "focusDiagnostic": focusDiagnostic])
        try jsonAttachment("Strict keyboard verdict " + phase, result)
        guard result["passed"] as? Bool == true else { XCTFail("Strict native keyboard evidence failed: \(result)"); throw Failure.focus("Strict keyboard verdict failed") }
        return after
    }
    private func acquire() throws {
        for _ in 0..<12 {
            let after = try key("acquire", "tab")
            if try focus(after) == "authored-toggle" { return }
        }
        throw Failure.focus("Native Tab never reached authored toggle within 12 steps")
    }
    private func enabled(_ initial: Bool) throws {
        _ = try launchCase("keyboard-enabled-" + (initial ? "on" : "off"), initial: initial); try acquire()
        try key("space-first", "space", expectedFocus: "authored-toggle", expectedSelection: !initial)
        try key("space-reverse", "space", expectedFocus: "authored-toggle", expectedSelection: initial)
        try key("tab-reference", "tab", expectedFocus: "plain-uibutton-reference")
        try key("tab-next", "tab", expectedFocus: "next-focus")
        try key("reverse-reference", "shift-tab", expectedFocus: "plain-uibutton-reference")
        try key("reverse-toggle", "shift-tab", expectedFocus: "authored-toggle")
    }
    private func stale(_ initial: Bool) throws {
        _ = try launchCase("keyboard-stale-" + (initial ? "on" : "off"), initial: initial); try acquire()
        _ = try bridge("command", ["command": "stale"])
        try key("stale-space", "space", expectedFocus: "authored-toggle", expectedSelection: initial)
        _ = try bridge("command", ["command": "resume"])
        try key("resumed-space", "space", expectedFocus: "authored-toggle", expectedSelection: !initial)
    }
    private func disabled(_ initial: Bool) throws {
        _ = try launchCase("keyboard-disabled-" + (initial ? "on" : "off"), initial: initial); try acquire()
        _ = try bridge("command", ["command": "disable"])
        let immediatelyDisabled = try ax(); try jsonAttachment("Actual native focus immediately after disable", immediatelyDisabled)
        if try focus(immediatelyDisabled) == "authored-toggle" { try key("disabled-held-space", "space", expectedSelection: initial) }
        try key("disabled-navigation", "tab", expectedSelection: initial)
        try key("disabled-space", "space", expectedSelection: initial)
        try key("disabled-reverse", "shift-tab", expectedSelection: initial)
    }
    func test010ReferenceFirstTab() throws {
        _ = try launchCase("keyboard-enabled-off", initial: false)
        try key("acquire", "tab", requiredFocusBefore: "plain-uibutton-reference")
    }
    func test010EnabledFromOff() throws { try enabled(false) }
    func test020EnabledFromOn() throws { try enabled(true) }
    func test030StaleFromOff() throws { try stale(false) }
    func test040StaleFromOn() throws { try stale(true) }
    func test050DisabledFromOff() throws { try disabled(false) }
    func test060DisabledFromOn() throws { try disabled(true) }
}
