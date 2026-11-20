import Foundation
import XCTest

@MainActor
final class ChecklistJourney: XCTestCase {
  private struct SavedTask: Decodable, Equatable {
    let id: UUID
    let projectID: UUID
    let title: String
    let responsible: String
    let position: Int
    let completed: Bool
  }

  private struct RotationObservation: Decodable, Equatable {
    let installation: String
    let process: Int32
    let deliveryError: String?
    let healthLaunch: String
    let milestones: [String]
    let artifact: String
    let payload: String
    let candidates: [String]
    let previous: String?
  }

  private struct Observation: Decodable, Equatable {
    let rotation: RotationObservation?
    let workspaceID: UUID
    let taskID: UUID
    let projectID: UUID
    let taskBytes: Data
    let workspaceSHA256: String
    let revision: UInt64
    let outbox: Int
    let lastChangeID: UUID?
    let lastChangeRecord: UUID?
    let candidate: String
    let launch: String
    let sequence: UInt64
    let partialBytes: Int
    let partialSHA256: String?
    let partialArtifactSHA256: String?
    let partialPrefixSHA256: String?
    let launchedArtifactSHA256: String?
    let replayedPrefixBytes: Int
    let replayedPrefixSHA256: String?
  }

  private struct PhaseReceipt: Decodable {
    struct Offer: Decodable {
      let platform: String
      let artifact: String
      let payloadSHA256: String?
      let prefixBytes: Int?
      let prefixSHA256: String?
    }

    struct Stop: Decodable {
      struct Relay: Decodable {
        let socketClosed: Bool
        let threadJoined: Bool
        let connectionRefused: Bool
      }

      struct Service: Decodable {
        let directChildReaped: Bool
        let groupAbsent: Bool
        let connectionRefused: Bool
        let forced: Bool
        let returncode: Int
      }

      let relay: Relay
      let service: Service
    }

    let phase: String
    let verified: Bool
    let offers: [Offer]?
    let stop: Stop?

    func iosOffer() throws -> Offer {
      try XCTUnwrap(offers?.first(where: { $0.platform == "ios" }))
    }
  }

  private let project = "Checklist workshop"
  private let title = "Inspect pump"
  private let responsible = "Night shift"
  private var lastObservation: Observation?
  private var lastInput: String?
  private var recoveredLaunch: String?
  private var recoveredSinceLastInput = false
  private var observedStops = 0
  private var verifiedReopens = 0

  func testDevelopmentKeyRotation() async throws {
    continueAfterFailure = false
    let environment = ProcessInfo.processInfo.environment
    let control = try XCTUnwrap(environment["FIELDLOG_CHECKLIST_CONTROL_URL"].flatMap(URL.init(string:)))
    let data = try XCTUnwrap(environment["FIELDLOG_CHECKLIST_DATA_URL"].flatMap(URL.init(string:)))
    let token = try XCTUnwrap(environment["FIELDLOG_CHECKLIST_CONTROL_TOKEN"])
    let workspace = UUID()
    attach("workspace-folder", "FieldLogUITest-" + workspace.uuidString.lowercased())
    let app = XCUIApplication()
    app.launchArguments = ["--fieldlog-ui-workspace", workspace.uuidString,
                           "--fieldlog-checklist-observation", "--fieldlog-rotation-replay"]
    app.launchEnvironment["FIELDLOG_CHECKLIST_DATA_URL"] = data.absoluteString
    defer { app.terminate() }

    let baselineOffer = try await phase("baseline", control, token).iosOffer()
    app.launch()
    createTask(app)
    openChecklist(app.buttons[title + ", not completed"], in: app)
    let (baseline, initial) = try await rotationCheckpoint("rotation-baseline", app, sequence: 1)
    XCTAssertNotEqual(initial.installation, workspace.uuidString.lowercased())
    XCTAssertEqual(baseline.revision, 2)
    XCTAssertEqual(baseline.outbox, 2)
    XCTAssertEqual(baseline.lastChangeRecord, baseline.taskID)
    XCTAssertEqual(initial.artifact, baselineOffer.artifact)
    XCTAssertEqual(initial.payload, baselineOffer.payloadSHA256)
    XCTAssertEqual(initial.candidates, [baseline.candidate])
    XCTAssertNil(initial.previous)
    XCTAssertNil(initial.deliveryError)

    var previousLaunch = baseline.launch
    for denied in ["revoked-artifact", "revoked-assignment"] {
      let offer = try await phase(denied, control, token).iosOffer()
      XCTAssertNotEqual(offer.artifact, initial.artifact)
      tap(app.buttons["checklist-check-updates"], app)
      let (retained, observed) = try await rotationCheckpoint(
        "rotation-" + denied, app, sequence: 1, deliveryError: "v3.signature.authority", after: previousLaunch)
      assertRetained(baseline, initial, retained, observed)
      XCTAssertEqual(observed.process, initial.process)
      previousLaunch = retained.launch
    }

    app.terminate()
    XCTAssertEqual(app.state, .notRunning)
    _ = try await phase("offline", control, token)
    try await requireClosed(data)
    app.launch()
    let projectBar = app.navigationBars[project]
    if !projectBar.waitForExistence(timeout: 8) {
      tap(app.buttons.containing(.staticText, identifier: project).firstMatch, app)
      XCTAssertTrue(projectBar.waitForExistence(timeout: 12), app.debugDescription)
    }
    let row = app.buttons["checklist-task-" + baseline.taskID.uuidString.lowercased()]
    XCTAssertTrue(row.waitForExistence(timeout: 12), app.debugDescription)
    XCTAssertEqual(row.label, title + ", not completed")
    openChecklist(row, in: app)
    let (cold, offline) = try await rotationCheckpoint(
      "rotation-offline", app, sequence: 1, deliveryError: "offline", after: previousLaunch)
    assertRetained(baseline, initial, cold, offline)
    XCTAssertNotEqual(offline.process, initial.process)
    try await requireClosed(data)

    let replacement = try await phase("replacement", control, token).iosOffer()
    XCTAssertNotEqual(replacement.artifact, initial.artifact)
    tap(app.buttons["checklist-check-updates"], app)
    let (rotated, active) = try await rotationCheckpoint("rotation-replacement", app, sequence: 2, after: cold.launch)
    unchanged(baseline, rotated)
    XCTAssertEqual(active.process, offline.process)
    XCTAssertEqual(active.installation, initial.installation)
    XCTAssertEqual(active.artifact, replacement.artifact)
    XCTAssertEqual(active.payload, replacement.payloadSHA256)
    XCTAssertEqual(rotated.launchedArtifactSHA256, replacement.artifact)
    XCTAssertNotEqual(rotated.candidate, baseline.candidate)
    XCTAssertEqual(active.previous, baseline.candidate)
    XCTAssertEqual(active.candidates, [baseline.candidate, rotated.candidate].sorted())
    tap(app.navigationBars[title].buttons["Done"], app)
    XCTAssertTrue(app.navigationBars[project].waitForExistence(timeout: 15))
    _ = try await phase("complete", control, token)
  }

  private func assertRetained(_ baseline: Observation, _ initial: RotationObservation,
                              _ item: Observation, _ observed: RotationObservation) {
    unchanged(baseline, item)
    XCTAssertEqual(item.candidate, baseline.candidate)
    XCTAssertEqual(observed.installation, initial.installation)
    XCTAssertEqual(observed.artifact, initial.artifact)
    XCTAssertEqual(observed.payload, initial.payload)
    XCTAssertEqual(observed.candidates, initial.candidates)
    XCTAssertNil(observed.previous)
    XCTAssertNil(item.launchedArtifactSHA256)
  }

  private func rotationCheckpoint(_ name: String, _ app: XCUIApplication, sequence: UInt64,
                                  deliveryError: String? = nil, after previous: String? = nil)
    async throws -> (Observation, RotationObservation) {
    let prefix = deliveryError == nil ? "Signed checklist" : "Using saved checklist release"
    let heading = "\(prefix) · Sequence \(sequence)"
    let deadline = ContinuousClock.now + .seconds(35)
    while ContinuousClock.now < deadline {
      if let (item, task, raw) = observation(app), let state = item.rotation,
         item.sequence == sequence, item.launch != previous, releaseHeading(app) == heading,
         guestState("Open", app) {
        validate(item, task)
        XCTAssertFalse(task.completed)
        XCTAssertEqual(item.partialBytes, 0)
        XCTAssertEqual(state.deliveryError, deliveryError)
        XCTAssertEqual(state.healthLaunch, item.launch)
        XCTAssertEqual(Set(state.milestones), ["feature_started", "first_screen"])
        XCTAssertEqual(state.milestones.count, 2)
        XCTAssertNotNil(UUID(uuidString: state.installation))
        XCTAssertNotEqual(state.installation, item.workspaceID.uuidString.lowercased())
        XCTAssertGreaterThan(state.process, 0)
        attach(name, raw)
        return (item, state)
      }
      try await Task.sleep(for: .milliseconds(100))
    }
    if let (_, _, raw) = observation(app) { attach(name + "-last", raw) }
    throw failure("Missing rotation checkpoint " + name, app)
  }

  func testSignedChecklistSurvivesServiceOutage() async throws {
    continueAfterFailure = false
    let environment = ProcessInfo.processInfo.environment
    let control = try XCTUnwrap(environment["FIELDLOG_CHECKLIST_CONTROL_URL"].flatMap(URL.init(string:)))
    let data = try XCTUnwrap(environment["FIELDLOG_CHECKLIST_DATA_URL"].flatMap(URL.init(string:)))
    let token = try XCTUnwrap(environment["FIELDLOG_CHECKLIST_CONTROL_TOKEN"])
    let workspace = UUID()
    attach("workspace-folder", "FieldLogUITest-" + workspace.uuidString.lowercased())
    let app = XCUIApplication()
    app.launchArguments = ["--fieldlog-ui-workspace", workspace.uuidString, "--fieldlog-checklist-observation"]
    app.launchEnvironment["FIELDLOG_CHECKLIST_DATA_URL"] = data.absoluteString
    defer { app.terminate() }

    let baselineOffer = try await phase("1", control, token).iosOffer()
    app.launch()
    createTask(app)
    openChecklist(app.buttons[title + ", not completed"], in: app)
    let initial = try await capture("01-baseline-open", app, sequence: 1, completed: false)
    XCTAssertEqual(initial.launchedArtifactSHA256, baselineOffer.artifact)
    XCTAssertEqual(initial.outbox, 2)
    XCTAssertEqual(initial.partialBytes, 0)
    try await send("Complete task", in: app)
    let baseline = try await capture("02-baseline-committed", app, sequence: 1, completed: true, afterEdit: true)
    try edited(initial, baseline)
    if initial.launch != baseline.launch {
      XCTAssertEqual(recoveredLaunch, baseline.launch)
    }
    let row = app.buttons["checklist-task-" + baseline.taskID.uuidString.lowercased()]

    let reviewedOffer = try await phase("2", control, token).iosOffer()
    XCTAssertNotEqual(reviewedOffer.artifact, baselineOffer.artifact)
    try await refresh(2, in: app)
    let reviewed = try await capture("03-review-hydrated", app, sequence: 2, completed: true)
    unchanged(baseline, reviewed)
    XCTAssertEqual(reviewed.launchedArtifactSHA256, reviewedOffer.artifact)
    XCTAssertNotEqual(baseline.candidate, reviewed.candidate)
    XCTAssertNotEqual(baseline.launch, reviewed.launch)
    try await send("Reopen task", in: app)
    let reopened = try await capture("04-review-open", app, sequence: 2, completed: false, afterEdit: true)
    try edited(reviewed, reopened)
    try await send("Complete task", in: app)
    let awaiting = try await capture("05-review-awaiting-confirmation", app, sequence: 2, completed: false, visible: "Review required")
    unchanged(reopened, awaiting)
    try await send("Confirm completion", in: app)
    let confirmed = try await capture("06-review-confirmed", app, sequence: 2, completed: true, afterEdit: true)
    try edited(awaiting, confirmed)

    let rollbackOffer = try await phase("3", control, token).iosOffer()
    XCTAssertEqual(rollbackOffer.artifact, baselineOffer.artifact)
    try await refresh(3, in: app)
    let rolledBack = try await capture("07-rollback-hydrated", app, sequence: 3, completed: true)
    unchanged(confirmed, rolledBack)
    XCTAssertEqual(rolledBack.launchedArtifactSHA256, baselineOffer.artifact)
    XCTAssertNotEqual(rolledBack.candidate, reviewed.candidate)
    XCTAssertNotEqual(rolledBack.launch, confirmed.launch)
    try await send("Reopen task", in: app)
    let rollbackReopened = try await capture("08-rollback-reopened", app, sequence: 3, completed: false, afterEdit: true)
    try edited(rolledBack, rollbackReopened)
    try await send("Complete task", in: app)
    let rollbackCompleted = try await capture("09-rollback-immediate-completion", app, sequence: 3, completed: true, afterEdit: true)
    try edited(rollbackReopened, rollbackCompleted)
    XCTAssertFalse(app.buttons["Confirm completion"].exists)
    try await send("Reopen task", in: app)
    let rollbackOpen = try await capture("10-rollback-open-for-interruption", app, sequence: 3, completed: false, afterEdit: true)
    try edited(rollbackCompleted, rollbackOpen)

    let shortOffer = try await phase("interrupt", control, token).iosOffer()
    let prefixBytes = try XCTUnwrap(shortOffer.prefixBytes)
    let prefixSHA256 = try XCTUnwrap(shortOffer.prefixSHA256)
    XCTAssertEqual(shortOffer.artifact, reviewedOffer.artifact)
    XCTAssertEqual(prefixBytes, 2048)
    try await refresh(3, in: app)
    let interrupted = try await capture("11-interrupted", app, sequence: 3, completed: false, saved: true, partialBytes: 64 + prefixBytes)
    XCTAssertEqual(interrupted.partialArtifactSHA256, reviewedOffer.artifact)
    XCTAssertEqual(interrupted.partialPrefixSHA256, prefixSHA256)
    unchanged(rollbackOpen, interrupted)
    XCTAssertEqual(interrupted.candidate, rollbackOpen.candidate)
    XCTAssertNotNil(interrupted.partialSHA256)

    app.terminate()
    XCTAssertEqual(app.state, .notRunning)
    let offlinePhase = try await phase("offline", control, token)
    let stop = try XCTUnwrap(offlinePhase.stop)
    XCTAssertTrue(stop.relay.socketClosed && stop.relay.threadJoined && stop.relay.connectionRefused)
    XCTAssertTrue(stop.service.directChildReaped && stop.service.groupAbsent && stop.service.connectionRefused)
    XCTAssertFalse(stop.service.forced)
    XCTAssertEqual(stop.service.returncode, 0)
    // The application retains exactly the same endpoint after process death.
    try await requireClosed(data)
    app.launch()
    let projectBar = app.navigationBars[project]
    if !projectBar.waitForExistence(timeout: 8) {
      let restoredProject = app.buttons.containing(.staticText, identifier: project).firstMatch
      tap(restoredProject, app)
      XCTAssertTrue(projectBar.waitForExistence(timeout: 12), app.debugDescription)
    }
    XCTAssertTrue(row.waitForExistence(timeout: 12), app.debugDescription)
    XCTAssertEqual(row.label, title + ", not completed")
    openChecklist(row, in: app)
    let offline = try await capture("12-offline-cold-reopen", app, sequence: 3, completed: false, saved: true, partialBytes: 64 + prefixBytes)
    unchanged(interrupted, offline)
    XCTAssertEqual(offline.candidate, interrupted.candidate)
    XCTAssertNotEqual(offline.launch, interrupted.launch)
    XCTAssertEqual(offline.partialSHA256, interrupted.partialSHA256)
    try await requireClosed(data)

    let replayOffer = try await phase("4", control, token).iosOffer()
    XCTAssertEqual(replayOffer.artifact, reviewedOffer.artifact)
    try await refresh(4, in: app)
    let resumed = try await capture("13-resumed", app, sequence: 4, completed: false, partialBytes: 0)
    XCTAssertEqual(resumed.launchedArtifactSHA256, reviewedOffer.artifact)
    XCTAssertEqual(resumed.replayedPrefixBytes, prefixBytes)
    XCTAssertEqual(resumed.replayedPrefixSHA256, prefixSHA256)
    unchanged(offline, resumed)
    XCTAssertNotEqual(resumed.launch, offline.launch)
    XCTAssertNotEqual(resumed.candidate, offline.candidate)
    XCTAssertNil(resumed.partialSHA256)
    try await send("Complete task", in: app)
    let resumedPending = try await capture("14-resumed-awaiting-confirmation", app, sequence: 4, completed: false, visible: "Review required")
    unchanged(resumed, resumedPending)
    try await send("Confirm completion", in: app)
    let resumedSaved = try await capture("15-resumed-committed", app, sequence: 4, completed: true, afterEdit: true)
    try edited(resumedPending, resumedSaved)

    let finalOffer = try await phase("5", control, token).iosOffer()
    XCTAssertEqual(finalOffer.artifact, baselineOffer.artifact)
    try await refresh(5, in: app)
    let final = try await capture("16-final-rollback", app, sequence: 5, completed: true, partialBytes: 0)
    unchanged(resumedSaved, final)
    XCTAssertEqual(final.launchedArtifactSHA256, baselineOffer.artifact)
    XCTAssertNotEqual(final.candidate, resumedSaved.candidate)
    try await send("Done", in: app)
    let savedRow = NSPredicate(format: "exists == true AND label == %@", title + ", completed")
    let refreshed = await XCTWaiter.fulfillment(
      of: [XCTNSPredicateExpectation(predicate: savedRow, object: row)], timeout: 12)
    XCTAssertEqual(refreshed, .completed, app.debugDescription)
    record("journey-completed", [
      "path": observedStops == 0 ? "uninterrupted" : "completed-with-observed-fallback",
      "observedStops": observedStops, "verifiedReopens": verifiedReopens,
      "terminalSequence": final.sequence, "workspaceSHA256": final.workspaceSHA256,
    ])
  }

  private func createTask(_ app: XCUIApplication) {
    XCTAssertTrue(app.staticTexts["test-workspace-badge"].waitForExistence(timeout: 20))
    tap(app.buttons["create-first-project"], app)
    let projectName = app.textFields["project-name"]
    tap(projectName, app)
    projectName.typeText(project)
    tap(app.buttons["save-project"], app)
    XCTAssertTrue(app.navigationBars[project].waitForExistence(timeout: 15))
    tap(app.buttons["Add task"], app)
    let titleInput = app.descendants(matching: .any).matching(identifier: "task-title").firstMatch
    tap(titleInput, app)
    titleInput.typeText(title)
    let ownerInput = app.textFields["task-owner"]
    tap(ownerInput, app)
    ownerInput.typeText(responsible)
    record("task-editor-before-add", [
      "title": titleInput.value as? String ?? "",
      "responsible": ownerInput.value as? String ?? "",
    ])
    let editor = app.navigationBars["New task"]
    tap(editor.buttons["Add"], app)
    XCTAssertTrue(editor.waitForNonExistence(timeout: 15), app.debugDescription)
  }

  private func openChecklist(_ row: XCUIElement, in app: XCUIApplication,
                             file: StaticString = #filePath, line: UInt = #line) {
    let titleLabel = row.staticTexts[title]
    let target = NSPredicate(format: "exists == true AND enabled == true AND hittable == true")
    let ready = XCTWaiter.wait(for: [
      XCTNSPredicateExpectation(predicate: target, object: row),
      XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true"), object: titleLabel),
    ], timeout: 15)
    XCTAssertEqual(ready, .completed, app.debugDescription, file: file, line: line)
    let titleFrame = titleLabel.frame
    let titleCenter = CGPoint(x: titleFrame.midX, y: titleFrame.midY)
    XCTAssertTrue(row.frame.contains(titleCenter) && app.frame.contains(titleCenter),
                  app.debugDescription, file: file, line: line)
    // The plain button reports the full row; its visible label is the touch target.
    let touch = titleLabel.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
    attach("checklist-row-tap", "row=\(row.frame) title=\(titleFrame) touch=\(touch.screenPoint)")
    touch.tap()
    let presented = app.navigationBars[title].waitForExistence(timeout: 10)
    XCTAssertTrue(presented, "Checklist sheet did not open after tapping the task title. " + app.debugDescription,
                  file: file, line: line)
  }

  private func tap(_ element: XCUIElement, _ app: XCUIApplication,
                   file: StaticString = #filePath, line: UInt = #line) {
    let predicate = NSPredicate(format: "exists == true AND enabled == true AND hittable == true")
    let result = XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: predicate, object: element)], timeout: 15)
    XCTAssertEqual(result, .completed, app.debugDescription, file: file, line: line)
    element.tap()
  }

  private func refresh(_ sequence: UInt64, in app: XCUIApplication) async throws {
    try await send("Check for update to sequence \(sequence)", id: "checklist-check-updates", in: app)
  }

  private func send(_ action: String, id: String? = nil, in app: XCUIApplication) async throws {
    let button = app.buttons[id ?? action]
    let before = lastObservation
    let deadline = ContinuousClock.now + .seconds(20)
    while ContinuousClock.now < deadline {
      if try await recoverIfStopped("before " + action, app, mayHaveEdited: false) {
        if let before, let recovered = lastObservation {
          XCTAssertEqual(recovered.sequence, before.sequence)
          XCTAssertEqual(recovered.candidate, before.candidate)
        }
        continue
      }
      if ready(button) {
        lastInput = action
        recoveredSinceLastInput = false
        button.tap()
        return
      }
      try await Task.sleep(for: .milliseconds(100))
    }
    throw failure("Input unavailable: \(action)", app)
  }

  private func capture(_ name: String, _ app: XCUIApplication, sequence: UInt64,
                       completed: Bool, visible: String? = nil, afterEdit: Bool = false,
                       saved: Bool = false, partialBytes: Int? = nil) async throws -> Observation {
    let expectedLabel = (saved ? "Using saved checklist release" : "Signed checklist") + " · Sequence \(sequence)"
    let expectedGuest = visible ?? (completed ? "Completed" : "Open")
    let before = lastObservation
    let deadline = ContinuousClock.now + .seconds(35)
    while ContinuousClock.now < deadline {
      if try await recoverIfStopped(name, app, mayHaveEdited: afterEdit) { continue }
      let heading = releaseHeading(app)
      if let (item, task, raw) = observation(app),
         item.sequence == sequence, task.completed == completed,
         partialBytes == nil || item.partialBytes == partialBytes,
         heading == expectedLabel || (heading == "Using saved checklist release" && item.launch == recoveredLaunch),
         guestState(expectedGuest, app) {
        validate(item, task)
        if let before, before.sequence == sequence {
          XCTAssertEqual(item.candidate, before.candidate)
        }
        attach(name, raw)
        lastObservation = item
        return item
      }
      try await Task.sleep(for: .milliseconds(100))
    }
    if let (_, _, raw) = observation(app) { attach(name + "-last", raw) }
    throw failure("Missing required checkpoint \(name) (\(expectedLabel), \(expectedGuest)); input was sent at most once", app)
  }

  private func recoverIfStopped(_ checkpoint: String, _ app: XCUIApplication,
                                mayHaveEdited: Bool) async throws -> Bool {
    let reason = releaseHeading(app)
    guard reason == "Checklist timed out" || reason == "Checklist stopped" else { return false }
    observedStops += 1
    let event = "fallback-\(observedStops)"
    let before = lastObservation
    record(event + "-observed", [
      "checkpoint": checkpoint, "stopHeading": reason, "lastInput": lastInput ?? "",
      "previousLaunch": before?.launch ?? "",
    ])
    let reopen = app.buttons["checklist-reopen-saved"]
    let checkAgain = app.buttons["Check again"]
    let retirementDeadline = ContinuousClock.now + .seconds(25)
    var checkedAgain = false
    var savedCompleted: Bool?
    while ContinuousClock.now < retirementDeadline {
      if ready(reopen) {
        let open = app.staticTexts["Saved task status: Open"].exists
        let completed = app.staticTexts["Saved task status: Completed"].exists
        guard open != completed else { throw failure("Expected one visible saved task status", app) }
        savedCompleted = completed
        break
      }
      if !checkedAgain, ready(checkAgain) {
        checkedAgain = true
        checkAgain.tap()
      }
      if app.staticTexts["The saved checklist is unavailable."].exists { break }
      try await Task.sleep(for: .milliseconds(100))
    }
    guard let savedCompleted else { throw failure("Stopped checklist did not offer saved recovery", app) }
    XCTAssertFalse(guestState("Open", app) || guestState("Completed", app) ||
                   app.buttons["Confirm completion"].exists, app.debugDescription)
    let savedLabel = savedCompleted ? "Saved task status: Completed" : "Saved task status: Open"
    record(event + "-saved-visible", ["checkpoint": checkpoint, "status": savedLabel, "reopenButton": reopen.label])
    XCTAssertEqual(reopen.label, "Reopen saved checklist")
    reopen.tap()

    let reopenDeadline = ContinuousClock.now + .seconds(20)
    while ContinuousClock.now < reopenDeadline {
      let heading = releaseHeading(app)
      if heading == "Could not reopen the saved checklist" { break }
      if heading == "Using saved checklist release",
         let (item, task, raw) = observation(app), task.completed == savedCompleted,
         guestState(savedCompleted ? "Completed" : "Open", app) {
        validate(item, task)
        if let before {
          let priorTask = try JSONDecoder().decode(SavedTask.self, from: before.taskBytes)
          if mayHaveEdited && !recoveredSinceLastInput && priorTask.completed != task.completed {
            try edited(before, item)
          } else {
            unchanged(before, item)
          }
          XCTAssertNotEqual(item.launch, before.launch)
        } else {
          XCTAssertFalse(task.completed)
          XCTAssertEqual(item.revision, 2)
          XCTAssertEqual(item.outbox, 2)
          XCTAssertEqual(item.lastChangeRecord, item.taskID)
        }
        XCTAssertNil(item.launchedArtifactSHA256)
        XCTAssertEqual(item.replayedPrefixBytes, 0)
        XCTAssertNil(item.replayedPrefixSHA256)
        attach(event + "-committed-evidence", raw)
        verifiedReopens += 1
        recoveredLaunch = item.launch
        recoveredSinceLastInput = true
        lastObservation = item
        record(event + "-verified", [
          "checkpoint": checkpoint, "status": savedLabel, "sequence": item.sequence,
          "candidate": item.candidate, "launch": item.launch, "revision": item.revision,
          "outbox": item.outbox, "workspaceSHA256": item.workspaceSHA256,
        ])
        return true
      }
      try await Task.sleep(for: .milliseconds(100))
    }
    throw failure("Saved checklist did not regain live health with \(savedLabel)", app)
  }

  private func releaseHeading(_ app: XCUIApplication) -> String {
    let state = app.staticTexts["checklist-release-state"]
    return state.exists ? state.label : ""
  }

  private func guestState(_ label: String, _ app: XCUIApplication) -> Bool {
    app.staticTexts[label].exists
  }

  private func ready(_ button: XCUIElement) -> Bool {
    button.exists && button.isEnabled && button.isHittable
  }

  private func observation(_ app: XCUIApplication) -> (Observation, SavedTask, String)? {
    let marker = app.staticTexts["checklist-evidence"]
    guard marker.exists, let raw = marker.value as? String,
          let item = try? JSONDecoder().decode(Observation.self, from: Data(raw.utf8)),
          let task = try? JSONDecoder().decode(SavedTask.self, from: item.taskBytes)
    else { return nil }
    return (item, task, raw)
  }

  private func validate(_ item: Observation, _ task: SavedTask) {
    XCTAssertEqual(task.id, item.taskID)
    XCTAssertEqual(task.projectID, item.projectID)
    XCTAssertEqual(task.title, title)
    XCTAssertEqual(task.responsible, responsible)
    XCTAssertEqual(task.position, 0)
    XCTAssertEqual(item.workspaceSHA256.count, 64)
    XCTAssertEqual(item.candidate.count, 64)
    XCTAssertNotNil(UUID(uuidString: item.launch))
  }

  private func record(_ name: String, _ fields: [String: Any]) {
    let data = try! JSONSerialization.data(withJSONObject: fields, options: [.sortedKeys])
    attach(name, String(decoding: data, as: UTF8.self))
  }

  private func failure(_ message: String, _ app: XCUIApplication) -> NSError {
    NSError(domain: "ChecklistJourney", code: 1, userInfo: [
      NSLocalizedDescriptionKey: message + ". " + app.debugDescription,
    ])
  }

  private func unchanged(_ before: Observation, _ after: Observation,
                         file: StaticString = #filePath, line: UInt = #line) {
    identity(before, after, file: file, line: line)
    XCTAssertEqual(before.taskBytes, after.taskBytes, file: file, line: line)
    XCTAssertEqual(before.workspaceSHA256, after.workspaceSHA256, file: file, line: line)
    XCTAssertEqual(before.revision, after.revision, file: file, line: line)
    XCTAssertEqual(before.outbox, after.outbox, file: file, line: line)
    XCTAssertEqual(before.lastChangeID, after.lastChangeID, file: file, line: line)
  }

  private func edited(_ before: Observation, _ after: Observation,
                      file: StaticString = #filePath, line: UInt = #line) throws {
    identity(before, after, file: file, line: line)
    XCTAssertNotEqual(before.taskBytes, after.taskBytes, file: file, line: line)
    XCTAssertNotEqual(before.workspaceSHA256, after.workspaceSHA256, file: file, line: line)
    XCTAssertEqual(before.revision + 1, after.revision, file: file, line: line)
    XCTAssertEqual(before.outbox + 1, after.outbox, file: file, line: line)
    XCTAssertNotNil(after.lastChangeID, file: file, line: line)
    XCTAssertNotEqual(before.lastChangeID, after.lastChangeID, file: file, line: line)
    XCTAssertEqual(after.lastChangeRecord, after.taskID, file: file, line: line)
  }

  private func identity(_ before: Observation, _ after: Observation,
                        file: StaticString, line: UInt) {
    XCTAssertEqual(before.workspaceID, after.workspaceID, file: file, line: line)
    XCTAssertEqual(before.projectID, after.projectID, file: file, line: line)
    XCTAssertEqual(before.taskID, after.taskID, file: file, line: line)
  }

  private func phase(_ phase: String, _ control: URL, _ token: String) async throws -> PhaseReceipt {
    let url = control.appendingPathComponent("phase").appendingPathComponent(phase)
    var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 20)
    request.httpMethod = "POST"
    request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
    let (body, response) = try await session().data(for: request)
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
    do {
      let (_, response) = try await session().data(for: request)
      XCTFail("Delivery origin responded during physical service stop: \(response)")
    } catch let error as URLError {
      XCTAssertEqual(error.code, .cannotConnectToHost, "Unexpected offline error \(error.code)")
    }
  }

  private func session() -> URLSession {
    let config = URLSessionConfiguration.ephemeral
    config.urlCredentialStorage = nil
    config.httpShouldSetCookies = false
    config.connectionProxyDictionary = ["HTTPEnable": false, "HTTPSEnable": false]
    return URLSession(configuration: config)
  }

  private func attach(_ name: String, _ text: String) {
    let attachment = XCTAttachment(string: text)
    attachment.name = name
    attachment.lifetime = .keepAlways
    add(attachment)
  }
}
