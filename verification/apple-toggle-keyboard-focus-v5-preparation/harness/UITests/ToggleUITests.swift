import XCTest
import Foundation
import UIKit
import CryptoKit

private final class SettingsTelemetry: @unchecked Sendable {
    static let shared = SettingsTelemetry()
    let fixedCase = "public-settings-full-keyboard-access"
    private var generation = ""
    private var sequence = 0
    private var transport = DiagnosticTransportState()
    private let lock = NSRecursiveLock()
    private final class Box: @unchecked Sendable { var data: Data?; var status: Int?; var error: Error? }
    enum Failure: Error { case budget, bridge, upload, setup(String) }
    private var now: Double { ProcessInfo.processInfo.systemUptime }
    private func post(_ record: [String: Any]) throws -> [String: Any] {
        let remaining = try transport.begin(now: now)
        let env = ProcessInfo.processInfo.environment
        guard let base = env["MIXER_BRIDGE_URL"], let cap = env["MIXER_BRIDGE_CAPABILITY"], let url = URL(string: base + "/evaluate") else { throw Failure.bridge }
        let body = try JSONSerialization.data(withJSONObject: ["settingsDiagnostic": record], options: [.sortedKeys])
        guard body.count <= 8192 else { throw Failure.upload }
        var request = URLRequest(url: url, timeoutInterval: remaining)
        request.httpMethod = "POST"; request.httpBody = body
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(cap, forHTTPHeaderField: "X-Mixer-Capability")
        let box = Box(); let done = DispatchSemaphore(value: 0)
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            box.data = data; box.status = (response as? HTTPURLResponse)?.statusCode; box.error = error; done.signal()
        }
        task.resume()
        guard done.wait(timeout: .now() + remaining) == .success else { task.cancel(); throw transport.latch(.network("request timeout within existing2second budget")) }
        return try transport.response(status: box.status, data: box.data, networkError: box.error.map { String(describing: $0) })
    }
    func start() throws {
        lock.lock(); defer { lock.unlock() }
        let initial = now; transport.deadline = initial + 29.0
        let result = try post(["kind": "start", "case": fixedCase, "uptime": initial])
        guard let token = result["generation"] as? String, let remaining = result["remainingSessionSeconds"] as? Double else { throw Failure.bridge }
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
    func observe(_ stage: String, routeIndex: Int, attempt: Int, snapshot: [String: Any], started: Double, finished: Double, ax: Data?, png: Data?, routeWitness: [String: Any]? = nil) throws -> Int {
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
        let eventSequence = sequence + 1
        let result = try send(record)
        guard let slots = result["pending"] as? [String] else { throw Failure.bridge }
        for slot in slots {
            let form = slot.hasSuffix("-ax") ? "ax" : "png"
            guard let payload = payloads[form], let descriptor = files[form] as? [String: Any] else { throw Failure.upload }
            let count = (payload.count + 3071) / 3072
            for index in 0..<count {
                let chunk = payload.subdata(in: index * 3072..<min(payload.count, (index + 1) * 3072))
                _ = try send(["kind": "chunk", "slot": slot, "index": index, "count": count, "bytes": payload.count,
                              "sha256": descriptor["sha256"]!, "data": chunk.base64EncodedString()])
            }
        }
        return eventSequence
    }
}

private final class CompletionObserver: NSObject, XCTestObservation {
    func testCaseDidFinish(_ testCase: XCTestCase) { if testCase.name.contains("test000PublicSettingsFullKeyboardAccess") { SettingsTelemetry.shared.bestEffortMark("test-case-finished") } }
    func testSuiteDidFinish(_ testSuite: XCTestSuite) { if testSuite.name == "ToggleUITests" { SettingsTelemetry.shared.bestEffortMark("suite-finished") } }
    func testBundleDidFinish(_ testBundle: Bundle) { SettingsTelemetry.shared.bestEffortMark("bundle-finished") }
}

/// Diagnostic public Settings setup only. No application keyboard cases exist here.
@MainActor final class ToggleUITests: XCTestCase {
    private static let observer = CompletionObserver()
    private static var registered = false
    private let telemetry = SettingsTelemetry.shared
    private var now: Double { ProcessInfo.processInfo.systemUptime }
    override func setUpWithError() throws {
        continueAfterFailure = true
        if !Self.registered { XCTestObservationCenter.shared.addTestObserver(Self.observer); Self.registered = true }
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
        try telemetry.start()
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        settings.launch()
        defer {
            telemetry.bestEffortMark("terminate-before")
            settings.terminate()
            telemetry.bestEffortMark("terminate-after")
        }
        let control = settings.switches["Full Keyboard Access"].firstMatch
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
            let before = try capture(settings, control, stage: "before-switch", image: true)
            guard let initial = before.state["value"] as? String, before.state["valueKind"] as? String == "string", ["0", "1"].contains(initial) else { throw SettingsTelemetry.Failure.setup("Public switch value unavailable") }
            let anchor: Double
            if initial == "0" { control.tap(); anchor = now }
            else { anchor = before.state["observedUptime"] as! Double }
            let end = anchor + 3.0
            try telemetry.mark("switch-action", ["action": initial == "0" ? "tap" : "no-tap", "anchorUptime": anchor, "deadlineUptime": end])
            let after = try capture(settings, control, stage: "after-switch", image: true)
            var observedEnabled = initial == "1" || (after.state["value"] as? String == "1" && (after.state["observedUptime"] as! Double) <= end)
            var polls = 0
            while now < end && !observedEnabled && polls < 40 {
                RunLoop.current.run(until: Date(timeIntervalSinceNow: min(0.05, max(0, end - now))))
                guard now < end else { break }
                let state = try capture(settings, control, stage: "poll", tree: false)
                observedEnabled = state.state["valueKind"] as? String == "string" && state.state["value"] as? String == "1" && (state.state["observedUptime"] as! Double) <= end
                polls += 1
            }
            let terminal = try capture(settings, control, stage: "terminal", image: true)
            terminalRecorded = true
            guard observedEnabled && terminal.state["value"] as? String == "1" else { throw SettingsTelemetry.Failure.setup("Full Keyboard Access did not enable within unchanged3second public observation window") }
            print("MIXER_SETTINGS_DIAGNOSTIC enabled observed; six application cases remain unrun")
        } catch {
            let originalSetupError = error
            print("MIXER_SETTINGS_DIAGNOSTIC first setup error " + String(describing: originalSetupError))
            if !terminalRecorded { do { try capture(settings, control, stage: "terminal", image: true) } catch { print("MIXER_SETTINGS_DIAGNOSTIC terminal evidence incomplete " + String(describing: error)) } }
            throw originalSetupError
        }
    }
}
