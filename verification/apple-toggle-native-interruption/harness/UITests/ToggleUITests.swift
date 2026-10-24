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
        guard let data = box.data, data.count <= 2_000_000,
              let result = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw Failure.invalidResponse }
        guard box.status == 200 else {
            throw Failure.bridgeRejected(status: box.status, reason: result["error"] as? String ?? "Unavailable bridge reason; inspect durable bridge failure receipt")
        }
        return result
    }
    private enum Failure: Error { case invalidBridge, invalidResponse, timeout, geometry
        case bridgeRejected(status: Int?, reason: String) }
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
        if ["authored-pan", "authored-tap", "carrier-scroll", "native-pan-interruption"].contains(action) {
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

    private func interruption(_ name: String, mode: String?, rtl: Bool, initial: Bool) throws {
        var commands: [String] = []
        if rtl { commands.append("rtl") }
        if initial { commands.append("set-on") }
        if let mode { commands.append("arm-pan-" + mode) }
        let target = try launch("diagnostic", name, commands: commands)
        let bounds = try frame(target.descendants(matching: .any)["authored-toggle"])
        let positive = mode == nil ? (initial != rtl) : (initial == rtl)
        let start = CGPoint(x: positive ? bounds.minX + 14 : bounds.maxX - 14, y: bounds.midY)
        let end = CGPoint(x: start.x + (positive ? 30 : -30), y: start.y)
        try drag("native-pan-interruption", start, end, target: bounds)
    }
    func test001AccessibilityLtrOn() throws { try interruption("accessibility-ltr-on", mode: "accessibility", rtl: false, initial: false) }
    func test002AccessibilityLtrOff() throws { try interruption("accessibility-ltr-off", mode: "accessibility", rtl: false, initial: true) }
    func test003AccessibilityRtlOn() throws { try interruption("accessibility-rtl-on", mode: "accessibility", rtl: true, initial: false) }
    func test004AccessibilityRtlOff() throws { try interruption("accessibility-rtl-off", mode: "accessibility", rtl: true, initial: true) }
    func test005CancelLtrOn() throws { try interruption("cancel-ltr-on", mode: "cancel", rtl: false, initial: false) }
    func test006CancelLtrOff() throws { try interruption("cancel-ltr-off", mode: "cancel", rtl: false, initial: true) }
    func test007DisableLtrOn() throws { try interruption("disable-ltr-on", mode: "disable", rtl: false, initial: false) }
    func test008DisableLtrOff() throws { try interruption("disable-ltr-off", mode: "disable", rtl: false, initial: true) }
    func test009StaleLtrOn() throws { try interruption("stale-ltr-on", mode: "stale", rtl: false, initial: false) }
    func test010StaleLtrOff() throws { try interruption("stale-ltr-off", mode: "stale", rtl: false, initial: true) }
    func test011BindingLtrOn() throws { try interruption("binding-ltr-on", mode: "binding", rtl: false, initial: false) }
    func test012BindingLtrOff() throws { try interruption("binding-ltr-off", mode: "binding", rtl: false, initial: true) }
    func test013NochangeLtrOn() throws { try interruption("nochange-ltr-on", mode: nil, rtl: false, initial: false) }
    func test014NochangeLtrOff() throws { try interruption("nochange-ltr-off", mode: nil, rtl: false, initial: true) }
    func test015NochangeRtlOn() throws { try interruption("nochange-rtl-on", mode: nil, rtl: true, initial: false) }
    func test016NochangeRtlOff() throws { try interruption("nochange-rtl-off", mode: nil, rtl: true, initial: true) }
}
