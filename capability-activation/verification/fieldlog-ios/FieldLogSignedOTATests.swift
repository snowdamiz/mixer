import Foundation
import XCTest

final class FieldLogSignedOTATests: XCTestCase {
    @MainActor
    func testSignedBaselineReviewRollbackAndOfflineReopen() async throws {
        continueAfterFailure = false
        let env = ProcessInfo.processInfo.environment
        let port = try XCTUnwrap(env["FIELDLOG_OTA_PORT"].flatMap(UInt16.init))
        let token = try XCTUnwrap(env["FIELDLOG_OTA_PUBLISHER"])
        let workspace = UUID()
        attach("workspace-id", workspace.uuidString)
        let app = XCUIApplication(bundleIdentifier: "dev.mixer.fieldlog")
        defer { app.terminate() }

        try await publish(1, port: port, token: token, environment: env)
        open(app, workspace, arguments: [String(port), "1"], release: "Baseline healthy · sequence 1")
        saved(app, "open · revision 1 · outbox 2")
        button("Complete task", app).tap()
        saved(app, "completed · revision 2 · outbox 3")
        XCTAssertTrue(button("Reopen task", app).exists)
        let baseline = capture("01-baseline", app)
        close(app)

        try await publish(2, port: port, token: token, environment: env)
        open(app, workspace, arguments: [String(port), "2"], release: "Reviewed healthy · sequence 2")
        saved(app, "completed · revision 2 · outbox 3")
        button("Reopen saved task", app).tap()
        saved(app, "open · revision 3 · outbox 4")
        button("Complete task", app).tap()
        let confirm = button("Confirm completion", app)
        XCTAssertTrue(app.staticTexts["Review required"].waitForExistence(timeout: 10))
        saved(app, "open · revision 3 · outbox 4")
        let reviewed = capture("02-reviewed-confirmation", app)
        XCTAssertNotEqual(reviewed.candidate, baseline.candidate)
        confirm.tap()
        saved(app, "completed · revision 4 · outbox 5")
        _ = capture("03-reviewed-completed", app)
        close(app)

        try await publish(3, port: port, token: token, environment: env)
        open(app, workspace, arguments: [String(port), "3"], release: "Rollback healthy · sequence 3")
        saved(app, "completed · revision 4 · outbox 5")
        button("Reopen saved task", app).tap()
        saved(app, "open · revision 5 · outbox 6")
        button("Complete task", app).tap()
        saved(app, "completed · revision 6 · outbox 7")
        XCTAssertFalse(app.buttons["Confirm completion"].exists)
        let rollback = capture("04-rollback", app)
        XCTAssertNotEqual(rollback.candidate, baseline.candidate)
        XCTAssertNotEqual(rollback.candidate, reviewed.candidate)
        close(app)

        open(app, workspace, arguments: ["offline"], release: "Offline rollback healthy · sequence 3")
        saved(app, "completed · revision 6 · outbox 7")
        let offline = capture("05-offline-reopen", app)
        XCTAssertEqual(offline.candidate, rollback.candidate)
        XCTAssertNotEqual(offline.launch, rollback.launch)
        close(app)
    }

    @MainActor
    private func publish(_ sequence: Int, port: UInt16, token: String, environment: [String: String]) async throws {
        let assignment = try XCTUnwrap(environment["FIELDLOG_OTA_ASSIGNMENT_\(sequence)"].flatMap { Data(base64Encoded: $0) })
        let operation = sequence == 3 ? "rollback" : "publish"
        let route = "http://127.0.0.1:\(port)/v3/orgs/mixer-local/projects/fieldlog/channels/beta/\(operation)"
        let url = try XCTUnwrap(URL(string: route))
        var request = URLRequest(url: url, timeoutInterval: 5)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        request.setValue("\(operation)-\(sequence)", forHTTPHeaderField: "Idempotency-Key")
        request.httpBody = try JSONSerialization.data(withJSONObject: [
            "signed_assignment": JSONSerialization.jsonObject(with: assignment)
        ])
        let (_, response) = try await URLSession.shared.data(for: request)
        XCTAssertEqual(response.url, url)
        XCTAssertEqual((response as? HTTPURLResponse)?.statusCode, 200)
    }

    @MainActor
    private func open(_ app: XCUIApplication, _ workspace: UUID, arguments: [String], release: String) {
        app.launchArguments = ["--fieldlog-signed-ota", workspace.uuidString] + arguments
        app.launch()
        wait(app.staticTexts["ota-release"], release, app)
    }

    @MainActor
    private func close(_ app: XCUIApplication) {
        button("Close signed task", app).tap()
        wait(app.staticTexts["ota-release"], "Signed task closed", app)
        app.terminate()
        XCTAssertEqual(app.state, .notRunning)
    }

    @MainActor
    private func saved(_ app: XCUIApplication, _ value: String) {
        wait(app.staticTexts["ota-saved-task"], "Saved task " + value, app)
    }

    @MainActor
    private func wait(_ element: XCUIElement, _ label: String, _ app: XCUIApplication) {
        let predicate = NSPredicate(format: "exists == true AND label == %@", label)
        let result = XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: predicate, object: element)], timeout: 35)
        let error = app.staticTexts["ota-error"]
        XCTAssertEqual(result, .completed, error.exists ? error.label : app.debugDescription)
    }

    @MainActor
    private func button(_ title: String, _ app: XCUIApplication) -> XCUIElement {
        let element = app.buttons[title]
        let ready = NSPredicate(format: "exists == true AND enabled == true AND hittable == true")
        XCTAssertEqual(XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: ready, object: element)], timeout: 10),
                       .completed, "Native button \(title) not ready")
        return element
    }

    @MainActor
    private func capture(_ phase: String, _ app: XCUIApplication) -> (candidate: String, launch: String) {
        let marker = app.staticTexts["ota-evidence"].label
        let components = marker.split(separator: " ")
        XCTAssertEqual(components.count, 2)
        XCTAssertTrue(components.first?.hasPrefix("candidate=") == true)
        XCTAssertTrue(components.last?.hasPrefix("launch=") == true)
        attach(phase + "-identity", marker)
        attach(phase + "-saved", app.staticTexts["ota-saved-task"].label)
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = phase
        screenshot.lifetime = .keepAlways
        add(screenshot)
        return (String(components[0].dropFirst("candidate=".count)), String(components[1].dropFirst("launch=".count)))
    }

    private func attach(_ name: String, _ value: String) {
        let attachment = XCTAttachment(string: value)
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
