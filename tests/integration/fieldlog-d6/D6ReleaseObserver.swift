import Foundation
import XCTest

@MainActor
final class D6ReleaseObserver: XCTestCase {
    private let project = "Checklist workshop"
    private let task = "Measure opening"

    private struct Offer: Decodable {
        let sequence: Int
        let artifact: String
        let payloadSHA256: String
    }

    func testBaselineReviewRollbackAndOffline() async throws {
        continueAfterFailure = false
        let environment = ProcessInfo.processInfo.environment
        let workspace = try XCTUnwrap(environment["D6_WORKSPACE"].flatMap(UUID.init(uuidString:)))
        let control = try XCTUnwrap(environment["D6_CONTROL"].flatMap(URL.init(string:)))
        let ticket = try XCTUnwrap(environment["D6_TICKET"])
        let app = XCUIApplication(bundleIdentifier: "dev.mixer.fieldlog")
        app.launchArguments = ["--fieldlog-ui-workspace", workspace.uuidString,
                               "--fieldlog-checklist-observation", "--fieldlog-rotation-replay"]
        attach("workspace-folder", "FieldLogUITest-" + workspace.uuidString.lowercased())
        defer { if app.state != .notRunning { app.terminate() } }

        let baseline = try JSONDecoder().decode(Offer.self, from: await phase("baseline", control, ticket))
        XCTAssertEqual(baseline.sequence, 1)
        app.launch()
        let create = app.buttons["create-first-project"]
        tap(create)
        enter(app.textFields["project-name"], project)
        tap(app.buttons["save-project"])
        openProject(app)
        tap(app.buttons["Add task"])
        enter(app.textFields["task-title"], task)
        let owner = app.textFields["task-owner"]
        if owner.exists { enter(owner, "Operator") }
        let add = app.buttons["Add"].firstMatch
        tap(add.exists ? add : app.buttons["Save"].firstMatch)
        openTask(app)
        let first = try await readback(app, name: "baseline", workspace: workspace, offer: baseline,
                                       control: control, ticket: ticket)

        app.terminate()
        let staged = try JSONDecoder().decode(Offer.self, from: await phase("staged", control, ticket))
        XCTAssertEqual(staged.sequence, 2)
        XCTAssertNotEqual(staged.artifact, baseline.artifact)
        XCTAssertNotEqual(staged.payloadSHA256, baseline.payloadSHA256)
        app.launch()
        openProject(app)
        openTask(app)
        let second = try await readback(app, name: "review", workspace: workspace, offer: staged,
                                        control: control, ticket: ticket)

        app.terminate()
        let rollback = try JSONDecoder().decode(Offer.self, from: await phase("rollback", control, ticket))
        XCTAssertEqual(rollback.sequence, 3)
        XCTAssertEqual(rollback.artifact, baseline.artifact)
        XCTAssertEqual(rollback.payloadSHA256, baseline.payloadSHA256)
        app.launch()
        openProject(app)
        openTask(app)
        let third = try await readback(app, name: "rollback", workspace: workspace, offer: rollback,
                                        control: control, ticket: ticket)

        app.terminate()
        _ = try await phase("offline", control, ticket)
        app.launch()
        openProject(app)
        openTask(app)
        let last = try await readback(app, name: "offline", workspace: workspace, offer: rollback,
                                        control: control, ticket: ticket)
        for key in ["workspaceID", "projectID", "taskID", "workspaceSHA256", "signedExecutableSHA256", "ownedDeviceUUID"] {
            let value = try XCTUnwrap(first[key] as? String)
            for observation in [second, third, last] {
                XCTAssertEqual(observation[key] as? String, value, key)
            }
        }
        let installations = try [first, second, third, last].map {
            try XCTUnwrap(($0["rotation"] as? [String: Any])?["installation"] as? String)
        }
        XCTAssertEqual(Set(installations).count, 1)
        XCTAssertNotNil(UUID(uuidString: installations[0]))
        let launches = try [first, second, third, last].map { try XCTUnwrap($0["launch"] as? String) }
        XCTAssertEqual(Set(launches).count, 4)
        _ = try await phase("complete", control, ticket)
    }

    private func phase(_ name: String, _ origin: URL, _ ticket: String, body: Data? = nil) async throws -> Data {
        var request = URLRequest(url: origin.appendingPathComponent(name), timeoutInterval: 45)
        request.httpMethod = "POST"
        request.setValue("Bearer " + ticket, forHTTPHeaderField: "Authorization")
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = body
        }
        let (data, response) = try await URLSession.shared.data(for: request)
        XCTAssertEqual((response as? HTTPURLResponse)?.statusCode, 200, name)
        return data
    }

    private func openProject(_ app: XCUIApplication) {
        if !app.navigationBars[project].waitForExistence(timeout: 3) {
            tap(app.buttons.containing(.staticText, identifier: project).firstMatch)
        }
        XCTAssertTrue(app.navigationBars[project].waitForExistence(timeout: 12))
    }

    private func openTask(_ app: XCUIApplication) {
        let row = app.buttons[task + ", not completed"]
        XCTAssertTrue(row.waitForExistence(timeout: 12), app.debugDescription)
        row.coordinate(withNormalizedOffset: CGVector(dx: 0.25, dy: 0.5)).tap()
        XCTAssertTrue(app.navigationBars[task].waitForExistence(timeout: 15), app.debugDescription)
    }

    private func tap(_ element: XCUIElement) {
        XCTAssertTrue(element.waitForExistence(timeout: 12), element.debugDescription)
        element.tap()
    }

    private func enter(_ field: XCUIElement, _ value: String) {
        tap(field)
        field.typeText(value)
    }

    private struct PhaseUI: Encodable {
        let nonce: String
        let project: String
        let task: String
        let heading: String
        let foreground: Bool
        let taskNavigationVisible: Bool
        let evidenceExists: Bool
        let evidenceValueBytes: Int
        let evidenceLaunch: String?
    }

    private func readback(_ app: XCUIApplication, name: String, workspace: UUID, offer: Offer,
                          control: URL, ticket: String) async throws -> [String: Any] {
        let offline = name == "offline"
        let mode = offline ? "Using saved checklist release" : "Signed checklist"
        let expectedHeading = "\(mode) · Sequence \(offer.sequence)"
        let heading = app.staticTexts["checklist-release-state"]
        let evidence = app.staticTexts["checklist-evidence"]
        let deadline = ContinuousClock.now + .seconds(42)
        var sample: PhaseUI
        repeat {
            let reopen = app.buttons["checklist-reopen-saved"]
            if offline && reopen.exists && reopen.isHittable { reopen.tap() }
            let label = heading.exists ? heading.label : ""
            let exists = evidence.exists
            let encoded = exists ? evidence.value as? String ?? "" : ""
            let value = (try? JSONSerialization.jsonObject(with: Data(encoded.utf8))) as? [String: Any]
            let rotation = value?["rotation"] as? [String: Any]
            let launch = value?["launch"] as? String
            let matches = value?["sequence"] as? Int == offer.sequence &&
                rotation?["artifact"] as? String == offer.artifact &&
                rotation?["payload"] as? String == offer.payloadSHA256 &&
                launch != nil && rotation?["healthLaunch"] as? String == launch &&
                Set(rotation?["milestones"] as? [String] ?? []) == ["feature_started", "first_screen"]
            sample = PhaseUI(nonce: workspace.uuidString.lowercased(), project: project, task: task,
                                heading: label, foreground: app.state == .runningForeground,
                                taskNavigationVisible: app.navigationBars[task].exists, evidenceExists: exists,
                                evidenceValueBytes: encoded.utf8.count, evidenceLaunch: matches ? launch : nil)
            if sample.foreground && sample.taskNavigationVisible && label == expectedHeading { break }
            if ContinuousClock.now >= deadline { break }
            try await Task.sleep(for: .milliseconds(150))
        } while true

        // Stay on the same task while the host reads the live data and bundle containers.
        let request = try JSONEncoder().encode(sample)
        attach(name + "-ui-before-live-readback", String(decoding: request, as: UTF8.self))
        let response = try await phase(name + "-live", control, ticket, body: request)
        let proof = try XCTUnwrap(JSONSerialization.jsonObject(with: response) as? [String: Any])
        attach(name + "-live", String(decoding: response, as: UTF8.self))
        XCTAssertEqual(proof["nonce"] as? String, sample.nonce)
        XCTAssertEqual(proof["sequence"] as? Int, offer.sequence)
        XCTAssertEqual(app.state, .runningForeground)
        XCTAssertTrue(app.navigationBars[task].exists)
        XCTAssertTrue(heading.exists && heading.label == expectedHeading)
        attach(name + "-ui-after-live-readback", heading.label)
        return proof
    }

    private func attach(_ name: String, _ value: String) {
        let attachment = XCTAttachment(string: value)
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
