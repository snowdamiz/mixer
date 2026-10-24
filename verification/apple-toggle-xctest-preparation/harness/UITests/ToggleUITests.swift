import XCTest
import Foundation
import UIKit

/// Only public XCTest input. The loopback bridge supplies observations, never input.
@MainActor final class ToggleUITests: XCTestCase {
    private var app: XCUIApplication?
    private let diagnostic = "dev.mixer.verification.authoredtoggle.diagnostics"
    private let comparator = "dev.mixer.verification.authoredtoggle"

    override func setUpWithError() throws { continueAfterFailure = true }
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
        guard box.status == 200, let data = box.data, data.count <= 2_000_000,
              let result = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw Failure.invalidResponse }
        return result
    }
    private enum Failure: Error { case invalidBridge, invalidResponse, timeout, geometry }
    private final class ResponseBox: @unchecked Sendable { var data: Data?; var status: Int?; var error: Error? }

    private func launch(_ candidate: String, _ caseName: String, commands: [String] = []) throws -> XCUIApplication {
        let target = XCUIApplication(bundleIdentifier: candidate == "diagnostic" ? diagnostic : comparator)
        target.terminate()
        _ = try bridge("begin", ["candidate": candidate, "case": caseName])
        target.launch()
        guard target.wait(for: .runningForeground, timeout: 5) else { throw Failure.timeout }
        app = target
        _ = try bridge("ready")
        _ = try bridge("command", ["command": "resume"])
        _ = try bridge("command", ["command": "reset"])
        for command in commands { _ = try bridge("command", ["command": command]) }
        return target
    }
    private func frame(_ element: XCUIElement) throws -> CGRect {
        guard element.waitForExistence(timeout: 5), element.isHittable else { throw Failure.geometry }
        let result = element.frame
        guard result.width > 0, result.height > 0, !result.isInfinite, !result.isNull else { throw Failure.geometry }
        return result
    }
    private func point(_ value: CGPoint) -> [String: Double] { ["x": value.x, "y": value.y] }
    private func rect(_ value: CGRect) -> [String: Double] {
        ["x": value.minX, "y": value.minY, "width": value.width, "height": value.height]
    }
    private func baseline(_ action: String, start: CGPoint? = nil, end: CGPoint? = nil, target: CGRect) throws {
        var geometry: [String: Any] = ["target": rect(target), "app": rect(app!.frame)]
        if let start, let end {
            geometry["start"] = point(start); geometry["end"] = point(end)
            geometry["initialHoldSeconds"] = 0.15; geometry["velocity"] = 120.0; geometry["finalHoldSeconds"] = 0.15
        }
        let acknowledged = try bridge("baseline", ["action": action, "geometry": geometry])
        if ["authored-pan", "authored-tap", "carrier-scroll"].contains(action) {
            guard let state = acknowledged["state"] as? [String: Any], let nativeFrame = state["frameInWindow"] as? String else { throw Failure.geometry }
            let native = NSCoder.cgRect(for: nativeFrame)
            guard abs(native.minX - target.minX) <= 1, abs(native.minY - target.minY) <= 1,
                  abs(native.width - target.width) <= 1, abs(native.height - target.height) <= 1 else { throw Failure.geometry }
        }
    }
    private func evaluate() throws {
        let result = try bridge("evaluate")
        let attachment = XCTAttachment(data: try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys]), uniformTypeIdentifier: "public.json")
        attachment.name = "Strict native evidence verdict"; attachment.lifetime = .keepAlways; add(attachment)
        XCTAssertEqual(result["passed"] as? Bool, true, "Strict evidence predicates failed: \(result)")
    }
    private func drag(_ action: String, _ start: CGPoint, _ end: CGPoint, target: CGRect) throws {
        guard app!.frame.contains(start), app!.frame.contains(end) else { throw Failure.geometry }
        try baseline(action, start: start, end: end, target: target)
        let origin = app!.coordinate(withNormalizedOffset: .zero)
        let first = origin.withOffset(CGVector(dx: start.x - app!.frame.minX, dy: start.y - app!.frame.minY))
        let last = origin.withOffset(CGVector(dx: end.x - app!.frame.minX, dy: end.y - app!.frame.minY))
        first.press(forDuration: 0.15, thenDragTo: last, withVelocity: XCUIGestureVelocity(rawValue: 120), thenHoldForDuration: 0.15)
        try evaluate()
    }
    private func authoredDrag(caseName: String, rtl: Bool, initial: Bool) throws {
        var commands: [String] = []
        if rtl { commands.append("rtl") }
        if initial { commands.append("set-on") }
        let target = try launch("diagnostic", caseName, commands: commands)
        let bounds = try frame(target.descendants(matching: .any)["authored-toggle"])
        // Keep both endpoints inside the native 63x44 hit frame. Direction is semantic.
        let positive = (initial == rtl)
        let start = CGPoint(x: positive ? bounds.minX + 14 : bounds.maxX - 14, y: bounds.midY)
        let end = CGPoint(x: start.x + (positive ? 30 : -30), y: start.y)
        try drag("authored-pan", start, end, target: bounds)
    }

    func test010StandaloneNativePanPositiveControl() throws {
        let target = try launch("diagnostic", "standalone-pan")
        let label = try frame(target.staticTexts["Native pan delivery reference"])
        let surface = CGRect(x: label.minX - 8, y: label.minY - 8, width: min(300, target.frame.width - 48), height: 60)
        try drag("reference-pan", CGPoint(x: surface.minX + 30, y: surface.midY), CGPoint(x: surface.maxX - 30, y: surface.midY), target: surface)
    }
    func test020BlankListUpwardScrollPositiveControl() throws {
        let target = try launch("diagnostic", "blank-scroll")
        let toggle = try frame(target.descendants(matching: .any)["authored-toggle"])
        let scroll = CGRect(x: 16, y: toggle.minY - 30, width: target.frame.width - 32, height: 390)
        try drag("blank-scroll", CGPoint(x: scroll.minX + 75, y: scroll.maxY - 30), CGPoint(x: scroll.minX + 75, y: scroll.maxY - 210), target: scroll)
    }
    func test030LTRPanOffToOn() throws { try authoredDrag(caseName: "ltr-on", rtl: false, initial: false) }
    func test040LTRPanOnToOff() throws { try authoredDrag(caseName: "ltr-off", rtl: false, initial: true) }
    func test050RTLPanOffToOn() throws { try authoredDrag(caseName: "rtl-on", rtl: true, initial: false) }
    func test060RTLPanOnToOff() throws { try authoredDrag(caseName: "rtl-off", rtl: true, initial: true) }
    func test070VerticalDragStartingOnCarrierScrolls() throws {
        let target = try launch("diagnostic", "carrier-scroll")
        let bounds = try frame(target.descendants(matching: .any)["authored-toggle"])
        try drag("carrier-scroll", CGPoint(x: bounds.midX, y: bounds.midY), CGPoint(x: bounds.midX, y: bounds.midY - 130), target: bounds)
    }
    private func tapPair(candidate: String, caseName: String, plain: Bool) throws {
        let target = try launch(candidate, caseName)
        let button = target.descendants(matching: .any)[plain ? "plain-uibutton-reference" : "authored-toggle"]
        let bounds = try frame(button)
        for _ in 0..<2 { try baseline(plain ? "plain-tap" : "authored-tap", target: bounds); button.tap(); try evaluate() }
    }
    func test080DiagnosticAuthoredNativeTapPair() throws { try tapPair(candidate: "diagnostic", caseName: "diagnostic-taps", plain: false) }
    func test090DiagnosticPlainUIButtonNativeTapPair() throws { try tapPair(candidate: "diagnostic", caseName: "plain-taps", plain: true) }
    func test100ComparatorAuthoredNativeTapPair() throws { try tapPair(candidate: "comparator", caseName: "comparator-taps", plain: false) }
    func test110DiagnosticDirectAPIOriginalStrictChecks() throws {
        _ = try launch("diagnostic", "diagnostic-direct")
        try baseline("direct-suite", target: app!.frame)
        _ = try bridge("command", ["command": "self-tests"])
        try evaluate()
    }
    func test120ComparatorDirectAPIOriginalStrictChecks() throws {
        _ = try launch("comparator", "comparator-direct")
        try baseline("direct-suite", target: app!.frame)
        _ = try bridge("command", ["command": "self-tests"])
        try evaluate()
    }
}
