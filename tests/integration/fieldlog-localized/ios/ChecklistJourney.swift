import Foundation
import UIKit
import XCTest

@MainActor
final class ChecklistJourney: XCTestCase {
  private enum Layout: String {
    case ltr, rtl, largeRTL = "large-rtl"

    var rightToLeft: Bool { self != .ltr }
    var category: UIContentSizeCategory {
      self == .largeRTL ? .accessibilityExtraExtraExtraLarge : .large
    }

    var arguments: [String] {
      let direction = rightToLeft ? "YES" : "NO"
      return ["-AppleLanguages", rightToLeft ? "(ar)" : "(en)",
              "-AppleTextDirection", direction, "-NSForceRightToLeftWritingDirection", direction,
              "-UIPreferredContentSizeCategoryName", category.rawValue]
    }
  }

  private struct SavedTask: Decodable, Equatable {
    let id: UUID
    let projectID: UUID
    let title: String
    let responsible: String
    let position: Int
    var completed: Bool
  }

  private struct Observation: Decodable {
    struct Health: Decodable {
      let installation: UUID
      let process: Int32
      let deliveryError: String?
      let healthLaunch: UUID
      let milestones: Set<String>
      let artifact: String
      let payload: String
      let previous: String?
    }

    let rotation: Health
    let workspaceID: UUID
    let taskID: UUID
    let projectID: UUID
    let taskBytes: Data
    let workspaceSHA256: String
    let revision: UInt64
    let outbox: Int
    let outboxIDs: [UUID]
    let outboxKinds: [String]
    let lastChangeRecord: UUID
    let candidate: String
    let launch: UUID
    let sequence: UInt64
    let partialBytes: Int
    let launchedArtifactSHA256: String?
    let rightToLeft: Bool
    let textSize: String
  }

  private struct PhaseReceipt: Decodable {
    struct Offer: Decodable {
      let platform: String
      let artifact: String
      let payloadSHA256: String
      let sequence: UInt64
    }

    let phase: String
    let verified: Bool
    let offers: [Offer]?
    let closure: [String: Bool]?

    func offer(_ sequence: UInt64) throws -> Offer {
      let offers = try XCTUnwrap(offers)
      XCTAssertEqual(offers.count, 1)
      let offer = try XCTUnwrap(offers.first)
      XCTAssertEqual(offer.platform, "ios")
      XCTAssertEqual(offer.sequence, sequence)
      return offer
    }
  }

  private let title = "فحص المضخة 07"
  private let project = "Checklist workshop"
  private let baselineOpen = "مفتوحة"
  private let reviewedOpen = "الفحص قيد التنفيذ"
  private let awaitingReview = "الفحص بانتظار التأكيد"
  private let completed = "اكتمل الفحص"
  private let baselineAction = "إكمال المهمة"
  private let reviewAction = "وضع علامة مكتملة"
  private let confirmAction = "تأكيد إكمال الفحص"
  private let reopenAction = "إعادة فتح الفحص"

  func testSignedLocalizedChecklist() async throws {
    continueAfterFailure = false
    let environment = ProcessInfo.processInfo.environment
    let control = try endpoint("FIELDLOG_CHECKLIST_CONTROL_URL", environment)
    let data = try endpoint("FIELDLOG_CHECKLIST_DATA_URL", environment)
    XCTAssertNotEqual(control, data)
    let token = try XCTUnwrap(environment["FIELDLOG_CHECKLIST_CONTROL_TOKEN"])
    let workspaceFolder = UUID()
    attach("workspace-folder", "FieldLogUITest-" + workspaceFolder.uuidString.lowercased())
    let app = XCUIApplication(bundleIdentifier: "dev.mixer.fieldlog")
    defer { if app.state != .notRunning { app.terminate() } }

    let baselineOffer = try await phase("baseline", control, token).offer(1)
    try open(app, data, workspaceFolder, layout: .ltr, seed: true)
    let baseline = try await checkpoint("baseline-ltr", app, baselineOffer, .ltr, baselineOpen)
    XCTAssertEqual(baseline.launchedArtifactSHA256, baselineOffer.artifact)
    XCTAssertNil(baseline.rotation.previous)
    XCTAssertNotEqual(baseline.rotation.installation, workspaceFolder)
    XCTAssertEqual(baseline.revision, 2)
    XCTAssertEqual(baseline.outboxKinds, ["projectCreated", "taskSaved"])
    XCTAssertFalse(try task(baseline).completed)
    let baselineLTR = try captureLayout("baseline-ltr", app, status: baselineOpen, action: baselineAction)

    try open(app, data, workspaceFolder, layout: .rtl, selected: baseline.taskID)
    let baselineRTL = try await checkpoint("baseline-rtl", app, baselineOffer, .rtl, baselineOpen)
    assertSameRelease(baseline, baselineRTL)
    assertUnchanged(baseline, baselineRTL)
    let baselineRegular = try captureLayout("baseline-rtl", app, status: baselineOpen, action: baselineAction)

    try open(app, data, workspaceFolder, layout: .largeRTL, selected: baseline.taskID)
    let baselineAX = try await checkpoint("baseline-large-rtl", app, baselineOffer, .largeRTL, baselineOpen)
    assertSameRelease(baseline, baselineAX)
    assertUnchanged(baseline, baselineAX)
    let baselineLarge = try captureLayout("baseline-large-rtl", app, status: baselineOpen, action: baselineAction)
    XCTAssertGreaterThan(baselineLarge, max(baselineLTR, baselineRegular))

    let reviewedOffer = try await phase("replacement", control, token).offer(2)
    XCTAssertNotEqual(reviewedOffer.artifact, baselineOffer.artifact)
    XCTAssertNotEqual(reviewedOffer.payloadSHA256, baselineOffer.payloadSHA256)
    try tap(app.buttons["checklist-check-updates"], in: app)
    let reviewed = try await checkpoint("reviewed-large-rtl", app, reviewedOffer, .largeRTL, reviewedOpen)
    assertUnchanged(baseline, reviewed)
    XCTAssertEqual(reviewed.rotation.process, baselineAX.rotation.process)
    XCTAssertEqual(reviewed.rotation.previous, baselineAX.candidate)
    XCTAssertEqual(reviewed.launchedArtifactSHA256, reviewedOffer.artifact)
    XCTAssertNotEqual(reviewed.candidate, baselineAX.candidate)
    XCTAssertNotEqual(reviewed.launch, baselineAX.launch)
    let reviewedLarge = try captureLayout("reviewed-large-rtl", app, status: reviewedOpen, action: reviewAction)

    try tapGuestAction(reviewAction, app)
    let pending = try await checkpoint("awaiting-confirmation", app, reviewedOffer, .largeRTL, awaitingReview)
    assertUnchanged(reviewed, pending)
    assertSameRelease(reviewed, pending)
    XCTAssertEqual(pending.launch, reviewed.launch)
    _ = try captureLayout("awaiting-confirmation", app, status: awaitingReview, action: confirmAction)

    try tapGuestAction(confirmAction, app)
    let saved = try await checkpoint("completed", app, reviewedOffer, .largeRTL, completed)
    assertSameRelease(pending, saved)
    XCTAssertEqual(saved.launch, pending.launch)
    var expected = try task(pending)
    XCTAssertFalse(expected.completed)
    expected.completed = true
    XCTAssertEqual(try task(saved), expected)
    XCTAssertEqual(saved.revision, pending.revision + 1)
    XCTAssertEqual(saved.outboxKinds, pending.outboxKinds + ["taskSaved"])
    XCTAssertEqual(Array(saved.outboxIDs.dropLast()), pending.outboxIDs)
    XCTAssertEqual(saved.outboxIDs.count, pending.outboxIDs.count + 1)
    XCTAssertEqual(Set(saved.outboxIDs).count, saved.outboxIDs.count)
    XCTAssertNotEqual(saved.workspaceSHA256, pending.workspaceSHA256)
    _ = try captureLayout("completed", app, status: completed, action: reopenAction)

    try open(app, data, workspaceFolder, layout: .rtl, selected: baseline.taskID, completed: true)
    let reviewedRTL = try await checkpoint("reviewed-rtl", app, reviewedOffer, .rtl, completed)
    assertUnchanged(saved, reviewedRTL)
    assertSameRelease(saved, reviewedRTL)
    let reviewedRegular = try captureLayout("reviewed-rtl", app, status: completed, action: reopenAction)

    try open(app, data, workspaceFolder, layout: .ltr, selected: baseline.taskID, completed: true)
    let reviewedLTR = try await checkpoint("reviewed-ltr", app, reviewedOffer, .ltr, completed)
    assertUnchanged(saved, reviewedLTR)
    assertSameRelease(saved, reviewedLTR)
    let reviewedLTRHeight = try captureLayout("reviewed-ltr", app, status: completed, action: reopenAction)
    XCTAssertGreaterThan(reviewedLarge, max(reviewedRegular, reviewedLTRHeight))

    app.terminate()
    XCTAssertEqual(app.state, .notRunning)
    let offline = try await phase("offline", control, token)
    XCTAssertEqual(offline.closure, ["socketClosed": true, "threadJoined": true, "connectionRefused": true])
    try await requireClosed(data)
    try open(app, data, workspaceFolder, layout: .largeRTL, selected: baseline.taskID, completed: true)
    let cold = try await checkpoint("offline-cold-reopen", app, reviewedOffer, .largeRTL, completed,
                                    deliveryError: "offline")
    assertUnchanged(saved, cold)
    assertSameRelease(saved, cold)
    XCTAssertNotEqual(cold.launch, reviewedLTR.launch)
    XCTAssertNotEqual(cold.rotation.process, reviewedLTR.rotation.process)
    XCTAssertNil(cold.launchedArtifactSHA256)
    let hostTitle = app.staticTexts["checklist-host-title"]
    let releaseState = app.staticTexts["checklist-release-state"]
    XCTAssertEqual(hostTitle.label, title)
    XCTAssertEqual(releaseState.label, "Using saved checklist release · Sequence 2")
    XCTAssertTrue(app.frame.contains(hostTitle.frame) && app.frame.contains(releaseState.frame),
                  app.debugDescription)
    XCTAssertLessThanOrEqual(hostTitle.frame.maxY, releaseState.frame.minY)
    attach("offline-cold-host-bounds", "title=\(hostTitle.frame) release=\(releaseState.frame)")
    _ = try captureLayout("offline-cold-reopen", app, status: completed, action: reopenAction)
    try await requireClosed(data)
    let done = app.navigationBars.buttons["checklist-done"]
    try tap(done, in: app)
    XCTAssertTrue(hostTitle.waitForNonExistence(timeout: 15), app.debugDescription)
    XCTAssertFalse(releaseState.exists, app.debugDescription)
    XCTAssertTrue(done.waitForNonExistence(timeout: 5), app.debugDescription)
    XCTAssertFalse(app.staticTexts["checklist-evidence"].exists, app.debugDescription)
    XCTAssertTrue(app.navigationBars[project].waitForExistence(timeout: 15), app.debugDescription)
    let rowID = "checklist-task-" + baseline.taskID.uuidString.lowercased()
    let row = app.buttons[rowID]
    XCTAssertTrue(row.waitForExistence(timeout: 15), app.debugDescription)
    let completedLabel = checkedRowLabel(row.label, completion: "completed")
    XCTAssertTrue(row.staticTexts[title].exists, app.debugDescription)
    let retirement = ["launch": cold.launch.uuidString.lowercased(), "rowID": rowID, "label": completedLabel]
    let retirementBytes = try JSONEncoder().encode(retirement)
    attach("retired-checklist", String(decoding: retirementBytes, as: UTF8.self))
    _ = try await phase("complete", control, token)
  }

  private func open(_ app: XCUIApplication, _ data: URL, _ workspace: UUID, layout: Layout,
                    seed: Bool = false, selected: UUID? = nil, completed: Bool = false) throws {
    if app.state != .notRunning { app.terminate() }
    XCTAssertEqual(app.state, .notRunning)
    app.launchArguments = ["--fieldlog-ui-workspace", workspace.uuidString,
                           "--fieldlog-checklist-observation", "--fieldlog-rotation-replay"] + layout.arguments
    if seed { app.launchArguments.append("--fieldlog-localized-seed") }
    app.launchEnvironment["FIELDLOG_CHECKLIST_DATA_URL"] = data.absoluteString
    app.launch()
    let projectBar = app.navigationBars[project]
    if !projectBar.waitForExistence(timeout: 8) {
      try tap(app.buttons.containing(.staticText, identifier: project).firstMatch, in: app)
      XCTAssertTrue(projectBar.waitForExistence(timeout: 12), app.debugDescription)
    }
    let row: XCUIElement
    if let selected {
      row = app.buttons["checklist-task-" + selected.uuidString.lowercased()]
    } else {
      let matches = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "checklist-task-"))
      row = matches.firstMatch
      XCTAssertTrue(row.waitForExistence(timeout: 15), app.debugDescription)
      XCTAssertEqual(matches.count, 1, app.debugDescription)
    }
    XCTAssertTrue(row.waitForExistence(timeout: 15), app.debugDescription)
    _ = checkedRowLabel(row.label, completion: completed ? "completed" : "not completed")
    let rowTitle = row.staticTexts[title]
    XCTAssertTrue(rowTitle.waitForExistence(timeout: 10), app.debugDescription)
    try tap(row, coordinateOf: rowTitle, in: app)
    let hostTitle = app.staticTexts["checklist-host-title"]
    if layout == .largeRTL {
      XCTAssertTrue(hostTitle.waitForExistence(timeout: 10), app.debugDescription)
      XCTAssertEqual(hostTitle.label, title)
    } else {
      XCTAssertTrue(app.navigationBars[title].waitForExistence(timeout: 10), app.debugDescription)
      XCTAssertFalse(hostTitle.exists, app.debugDescription)
    }
    let done = app.navigationBars.buttons["checklist-done"]
    let update = app.navigationBars.buttons["checklist-check-updates"]
    XCTAssertTrue(done.waitForExistence(timeout: 10) && update.exists, app.debugDescription)
    XCTAssertEqual(done.label, "Done")
    XCTAssertEqual(update.label, "Check for update")
    XCTAssertEqual(done.frame.midX > update.frame.midX, layout.rightToLeft, app.debugDescription)
  }

  private func checkedRowLabel(_ raw: String, completion: String) -> String {
    let label = title + ", " + completion
    let isolated = "\u{2068}\(title)\u{2069}, \u{2068}\(completion)\u{2069}"
    XCTAssertTrue(raw == label || raw == isolated, raw)
    return label
  }

  private func checkpoint(_ name: String, _ app: XCUIApplication, _ offer: PhaseReceipt.Offer,
                          _ layout: Layout, _ status: String, deliveryError: String? = nil) async throws -> Observation {
    let deadline = ContinuousClock.now + .seconds(35)
    let decoder = JSONDecoder()
    let marker = app.staticTexts["checklist-evidence"]
    let heading = app.staticTexts["checklist-release-state"]
    let release = (deliveryError == nil ? "Signed checklist" : "Using saved checklist release")
      + " · Sequence \(offer.sequence)"
    let statusNode = app.staticTexts["status"]
    while ContinuousClock.now < deadline {
      if marker.exists, let raw = marker.value as? String,
         let row = try? decoder.decode(Observation.self, from: Data(raw.utf8)),
         let saved = try? task(row), saved.completed == (status == completed),
         row.sequence == offer.sequence, heading.exists, heading.label == release,
         statusNode.exists, statusNode.label == status {
        attach(name, raw)
        XCTAssertEqual(row.rightToLeft, layout.rightToLeft)
        XCTAssertEqual(row.textSize, layout == .largeRTL ? "accessibility5" : "large")
        XCTAssertEqual(row.rotation.deliveryError, deliveryError)
        XCTAssertEqual(row.rotation.healthLaunch, row.launch)
        XCTAssertEqual(row.rotation.milestones, ["feature_started", "first_screen"])
        XCTAssertEqual(row.rotation.artifact, offer.artifact)
        XCTAssertEqual(row.rotation.payload, offer.payloadSHA256)
        XCTAssertGreaterThan(row.rotation.process, 0)
        XCTAssertEqual(row.candidate.count, 64)
        XCTAssertEqual(row.workspaceSHA256.count, 64)
        XCTAssertEqual(row.partialBytes, 0)
        XCTAssertEqual(row.outboxIDs.count, row.outbox)
        XCTAssertEqual(row.outboxKinds.count, row.outbox)
        XCTAssertEqual(row.lastChangeRecord, row.taskID)
        XCTAssertEqual(saved.id, row.taskID)
        XCTAssertEqual(saved.projectID, row.projectID)
        XCTAssertEqual(saved.title, title)
        XCTAssertEqual(saved.responsible, "Night shift")
        XCTAssertEqual(saved.position, 0)
        return row
      }
      try await Task.sleep(for: .milliseconds(100))
    }
    if let raw = marker.value as? String { attach(name + "-last", raw) }
    throw failure("Missing \(name) with \(release) and \(status)", app)
  }

  private func captureLayout(_ name: String, _ app: XCUIApplication, status: String, action: String) throws -> CGFloat {
    let titleNode = app.staticTexts["task"]
    let statusNode = app.staticTexts["status"]
    let actionNode = app.buttons["toggle"]
    let scroll = app.scrollViews.containing(.staticText, identifier: "task").firstMatch
    XCTAssertTrue(scroll.waitForExistence(timeout: 10), app.debugDescription)
    for _ in 0..<4 {
      if visible(titleNode, in: scroll) && visible(statusNode, in: scroll) { break }
      scroll.swipeDown()
    }
    XCTAssertTrue(visible(titleNode, in: scroll), app.debugDescription)
    XCTAssertTrue(visible(statusNode, in: scroll), app.debugDescription)
    XCTAssertEqual(titleNode.label, title)
    XCTAssertEqual(statusNode.label, status)
    attach(name + "-status", statusNode.label)
    let height = titleNode.frame.height
    recordLayout(name + "-title", app, scroll: scroll, element: titleNode)
    for _ in 0..<4 {
      if visible(actionNode, in: scroll) && actionNode.isHittable { break }
      scroll.swipeUp()
    }
    XCTAssertTrue(visible(actionNode, in: scroll) && actionNode.isHittable && actionNode.isEnabled,
                  app.debugDescription)
    XCTAssertEqual(actionNode.label, action)
    recordLayout(name + "-action", app, scroll: scroll, element: actionNode)
    return height
  }

  private func visible(_ element: XCUIElement, in scroll: XCUIElement) -> Bool {
    guard element.exists, scroll.exists else { return false }
    let bounds = element.frame
    return !bounds.isEmpty && scroll.frame.insetBy(dx: -1, dy: -1).contains(bounds)
  }

  private func tapGuestAction(_ label: String, _ app: XCUIApplication) throws {
    let action = app.buttons["toggle"]
    XCTAssertEqual(action.label, label)
    try tap(action, in: app)
  }

  private func tap(_ button: XCUIElement, coordinateOf label: XCUIElement? = nil, in app: XCUIApplication) throws {
    let predicate = NSPredicate(format: "exists == true AND enabled == true AND hittable == true")
    let expectation = XCTNSPredicateExpectation(predicate: predicate, object: button)
    guard XCTWaiter.wait(for: [expectation], timeout: 15) == .completed else {
      throw failure("Input unavailable", app)
    }
    if let label {
      let center = CGPoint(x: label.frame.midX, y: label.frame.midY)
      XCTAssertTrue(button.frame.contains(center) && app.frame.contains(center), app.debugDescription)
      label.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
    } else {
      button.tap()
    }
  }

  private func task(_ row: Observation) throws -> SavedTask {
    try JSONDecoder().decode(SavedTask.self, from: row.taskBytes)
  }

  private func assertSameRelease(_ before: Observation, _ after: Observation,
                                 file: StaticString = #filePath, line: UInt = #line) {
    XCTAssertEqual(before.rotation.installation, after.rotation.installation, file: file, line: line)
    XCTAssertEqual(before.workspaceID, after.workspaceID, file: file, line: line)
    XCTAssertEqual(before.candidate, after.candidate, file: file, line: line)
    XCTAssertEqual(before.sequence, after.sequence, file: file, line: line)
  }

  private func assertUnchanged(_ before: Observation, _ after: Observation,
                               file: StaticString = #filePath, line: UInt = #line) {
    XCTAssertEqual(before.rotation.installation, after.rotation.installation, file: file, line: line)
    XCTAssertEqual(before.workspaceID, after.workspaceID, file: file, line: line)
    XCTAssertEqual(before.taskBytes, after.taskBytes, file: file, line: line)
    XCTAssertEqual(before.workspaceSHA256, after.workspaceSHA256, file: file, line: line)
    XCTAssertEqual(before.revision, after.revision, file: file, line: line)
    XCTAssertEqual(before.outboxIDs, after.outboxIDs, file: file, line: line)
    XCTAssertEqual(before.outboxKinds, after.outboxKinds, file: file, line: line)
  }

  private func endpoint(_ name: String, _ values: [String: String]) throws -> URL {
    let parts = try XCTUnwrap(values[name].flatMap(URLComponents.init(string:)))
    XCTAssertEqual(parts.scheme, "http")
    XCTAssertEqual(parts.host, "127.0.0.1")
    XCTAssertTrue((1024...65535).contains(parts.port ?? 0))
    XCTAssertTrue(parts.path.isEmpty && parts.user == nil && parts.password == nil &&
                  parts.query == nil && parts.fragment == nil)
    return try XCTUnwrap(parts.url)
  }

  private func phase(_ phase: String, _ control: URL, _ token: String) async throws -> PhaseReceipt {
    let url = control.appendingPathComponent("phase").appendingPathComponent(phase)
    var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 15)
    request.httpMethod = "POST"
    request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
    let connection = session()
    defer { connection.finishTasksAndInvalidate() }
    let (body, response) = try await connection.data(for: request)
    XCTAssertEqual(response.url, url)
    XCTAssertEqual((response as? HTTPURLResponse)?.statusCode, 200, String(decoding: body, as: UTF8.self))
    attach("origin-" + phase, String(decoding: body, as: UTF8.self))
    let receipt = try JSONDecoder().decode(PhaseReceipt.self, from: body)
    XCTAssertEqual(receipt.phase, phase)
    XCTAssertTrue(receipt.verified)
    return receipt
  }

  private func requireClosed(_ data: URL) async throws {
    let request = URLRequest(url: data.appendingPathComponent("healthz"),
                             cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 4)
    let connection = session()
    defer { connection.finishTasksAndInvalidate() }
    do {
      let (_, response) = try await connection.data(for: request)
      XCTFail("Stopped data listener responded: \(response)")
    } catch let error as URLError {
      XCTAssertEqual(error.code, .cannotConnectToHost)
    }
  }

  private func session() -> URLSession {
    let config = URLSessionConfiguration.ephemeral
    config.urlCredentialStorage = nil
    config.httpShouldSetCookies = false
    config.connectionProxyDictionary = ["HTTPEnable": false, "HTTPSEnable": false, "SOCKSEnable": false]
    return URLSession(configuration: config)
  }

  private func recordLayout(_ name: String, _ app: XCUIApplication, scroll: XCUIElement, element: XCUIElement) {
    attach(name + "-bounds", "viewport=\(scroll.frame) element=\(element.frame) label=\(element.label)")
    let attachment = XCTAttachment(screenshot: app.screenshot())
    attachment.name = name
    attachment.lifetime = .keepAlways
    add(attachment)
  }

  private func failure(_ message: String, _ app: XCUIApplication) -> NSError {
    NSError(domain: "ChecklistJourney", code: 1,
            userInfo: [NSLocalizedDescriptionKey: message + "\n" + app.debugDescription])
  }

  private func attach(_ name: String, _ text: String) {
    let attachment = XCTAttachment(string: text)
    attachment.name = name
    attachment.lifetime = .keepAlways
    add(attachment)
  }
}
