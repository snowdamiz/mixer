import AppKit
import FieldLogModels
import Foundation
import SwiftUI

private let launchFlag = "--fieldlog-local-entry-sync"

private struct TestFailure: Error, CustomStringConvertible {
  let description: String
  init(_ description: String) { self.description = description }
}

private func require(_ condition: Bool, _ message: String) throws {
  guard condition else { throw TestFailure(message) }
}

private func makeJPEG(seed: UInt32 = 17) throws -> Data {
  let width = 640
  let height = 480
  let rowBytes = width * 3
  guard let image = NSBitmapImageRep(
    bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height, bitsPerSample: 8, samplesPerPixel: 3,
    hasAlpha: false, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: rowBytes, bitsPerPixel: 24
  ), let pixels = image.bitmapData else { throw TestFailure("Could not allocate JPEG pixels.") }
  var state = seed
  for index in 0..<(rowBytes * height) {
    state = state &* 1_664_525 &+ 1_013_904_223
    pixels[index] = UInt8(truncatingIfNeeded: state >> 24)
  }
  guard let jpeg = image.representation(using: .jpeg, properties: [.compressionFactor: 0.83]),
    let decoded = NSBitmapImageRep(data: jpeg), decoded.pixelsWide == width, decoded.pixelsHigh == height
  else { throw TestFailure("JPEG did not decode after encoding.") }
  return jpeg
}

private struct Fixture: Codable {
  let workspace: UUID
  let project: UUID
  let entry: UUID
  let photo: UUID
  let event: UUID
  let otherEvent: UUID
  let photoBytes: Int
}

@main @MainActor struct QueueJourney {
  static func main() async {
    do {
      let arguments = CommandLine.arguments
      guard arguments.count == 3 else { throw TestFailure("Expected phase and owned fixture directory.") }
      let root = URL(fileURLWithPath: arguments[2], isDirectory: true)
      switch arguments[1] {
      case "offline": try await offline(root)
      case "online": try await online(root)
      default: throw TestFailure("Unrecognized phase.")
      }
    } catch {
      FileHandle.standardError.write(Data("Queue journey failed: \(error)\n".utf8))
      exit(EXIT_FAILURE)
    }
  }

  private static func saveEntry(
    _ model: WorkspaceModel, project: UUID, title: String, photos: [Data]
  ) async throws -> PendingChange {
    guard var draft = await model.newDraft(projectID: project) else {
      throw TestFailure("Could not create an ordinary draft.")
    }
    draft.title = title
    draft.note = "  Exact local spacing\n\n測定 · العربية\n"
    for photo in photos {
      draft.attachmentIDs = try await model.addPhoto(photo, draftID: draft.id)
    }
    try require(await model.commit(draft), "Could not save the draft as an entry.")
    guard let event = model.workspace?.outbox.first(where: {
      $0.kind == .entrySaved && $0.recordID == draft.id
    }) else { throw TestFailure("Saving did not create an entry event.") }
    return event
  }

  private static func queue(_ model: WorkspaceModel) throws -> DeviceQueue<EmptyView> {
    guard let workspace = model.workspace else { throw TestFailure("Workspace did not open.") }
    return DeviceQueue(workspace: workspace, model: model, accent: .green, onEdit: { _ in }, entryDetail: { _ in EmptyView() })
  }

  private static func action(_ model: WorkspaceModel, _ eventID: UUID) throws -> EntrySyncAction {
    guard let action = try queue(model).entrySyncAction(for: eventID) else {
      throw TestFailure("Queue row did not expose an entry action.")
    }
    let rendered = ImageRenderer(content: action.frame(width: 440, alignment: .leading)).cgImage
    try require(rendered?.width == 440 && (rendered?.height ?? 0) > 0, "Could not render the real row action.")
    return action
  }

  private static func offline(_ root: URL) async throws {
    let model = WorkspaceModel()
    await model.open(supportDirectory: root, arguments: [launchFlag], environment: [:])
    try require(model.openError == nil && model.isLocalEntrySyncWorkspace && !model.isTestWorkspace,
                "Development launch did not open its isolated ordinary workspace.")
    guard let project = await model.createProject(title: "Workshop", site: "North"),
      let otherProject = await model.createProject(title: "Archive", site: "South")
    else { throw TestFailure("Could not create both projects.") }
    try require(await model.addTask(projectID: project, title: "Inspect frame", responsible: "Field tester"),
                "Could not save the unrelated checklist item.")
    let jpeg = try makeJPEG()
    let event = try await saveEntry(model, project: project, title: "Door inspection", photos: [jpeg])
    let otherEvent = try await saveEntry(
      model, project: otherProject, title: "Door inspection", photos: [try makeJPEG(seed: 37)])
    _ = try await saveEntry(model, project: project, title: "Unrelated JPEG", photos: [try makeJPEG(seed: 73)])
    _ = try await saveEntry(model, project: project, title: "Text only", photos: [])
    _ = try await saveEntry(model, project: project, title: "Two JPEGs", photos: [jpeg, jpeg])
    model.restoreProject(project)
    await model.flush()
    let queue = try queue(model)
    try require(queue.pendingMessage(for: .entrySaved) == "Send not confirmed",
                "A pending development entry was incorrectly described as unsent.")
    try require(queue.workspace.outbox.allSatisfy { queue.entrySyncAction(for: $0.id) == nil },
                "Development launch without provisioning exposed a send control.")
    guard let entry = queue.workspace.entries.first(where: { $0.id == event.recordID }),
      let photo = entry.attachmentIDs.first, let url = await model.photoURL(photo)
    else { throw TestFailure("Saved entry is missing the JPEG link.") }
    try require(try Data(contentsOf: url) == jpeg, "Linked local JPEG is not the original bytes.")
    let fixture = Fixture(workspace: queue.workspace.id, project: project, entry: entry.id,
                          photo: photo, event: event.id, otherEvent: otherEvent.id, photoBytes: jpeg.count)
    try JSONEncoder().encode(fixture).write(to: root.appendingPathComponent("fixture.json"))
    print("offline: ordinary app save created linked JPEG and selective outbox coverage")
  }

  private static func online(_ root: URL) async throws {
    let environment = ProcessInfo.processInfo.environment
    let fixture = try JSONDecoder().decode(
      Fixture.self, from: Data(contentsOf: root.appendingPathComponent("fixture.json")))
    let normal = WorkspaceModel()
    await normal.open(supportDirectory: root, arguments: [], environment: environment)
    try require(normal.openError == nil && !normal.isLocalEntrySyncWorkspace && !normal.isTestWorkspace,
                "Runtime environment alone changed the ordinary launch mode.")
    guard let normalProject = await normal.createProject(title: "Ordinary", site: "") else {
      throw TestFailure("Normal workspace did not support ordinary local saves.")
    }
    let normalEvent = try await saveEntry(normal, project: normalProject, title: "Local record", photos: [try makeJPEG()])
    let normalQueue = try queue(normal)
    try require(normalQueue.entrySyncAction(for: normalEvent.id) == nil &&
                normalQueue.inspectableEntry(for: normalEvent) == nil &&
                normalQueue.pendingMessage(for: .entrySaved) == "Saved on device · not sent",
                "Ordinary queue changed its presentation or offered a send action.")
    await normal.sendEntry(eventID: normalEvent.id)
    try require(normal.workspace?.outbox.contains(normalEvent) == true, "Ordinary launch changed its outbox.")

    let fixtureLaunch = WorkspaceModel()
    await fixtureLaunch.open(
      supportDirectory: root, arguments: ["--fieldlog-ui-workspace", UUID().uuidString], environment: environment)
    try require(fixtureLaunch.isTestWorkspace && !fixtureLaunch.isLocalEntrySyncWorkspace,
                "UI-test workspace opted into sending via the environment.")
    let conflicting = WorkspaceModel()
    await conflicting.open(
      supportDirectory: root, arguments: [launchFlag, "--fieldlog-ui-workspace", UUID().uuidString],
      environment: environment)
    try require(conflicting.openError != nil && conflicting.workspace == nil,
                "UI-test and local backend launch flags opened the same workspace.")

    let model = WorkspaceModel()
    await model.open(supportDirectory: root, arguments: [launchFlag], environment: environment)
    let initial = try queue(model)
    try require(initial.workspace.id == fixture.workspace &&
                initial.workspace.restoration.selectedProjectID == fixture.project,
                "Opened a different development workspace or selected project.")
    let selected = try action(model, fixture.event)
    try require(selected.state == .ready && selected.enabled, "Selected entry row did not show Send.")
    let unrelated = initial.workspace.outbox.filter { $0.id != fixture.event }
    let matchingTitles = initial.workspace.outbox.compactMap { initial.inspectableEntry(for: $0) }
      .filter { $0.title == "Door inspection" }
    try require(matchingTitles.count == 2 &&
                matchingTitles.first(where: { $0.id == fixture.entry })?.attachmentIDs == [fixture.photo] &&
                matchingTitles.first(where: { $0.id != fixture.entry })?.attachmentIDs != [fixture.photo],
                "Same-title rows did not resolve to their own saved JPEGs.")
    guard let eligible = unrelated.first(where: { event in
      initial.inspectableEntry(for: event)?.title == "Unrelated JPEG"
    }) else { throw TestFailure("Missing another eligible row.") }
    try require(initial.entrySyncAction(for: eligible.id)?.enabled == true, "Other eligible row missing.")
    for event in unrelated where event.id != eligible.id {
      try require(initial.entrySyncAction(for: event.id) == nil, "An ineligible row offered a send control.")
      await model.sendEntry(eventID: event.id)
    }

    let first = Task { await selected.send() }
    try await waitForMarker("held-second-receipt", in: root)
    let partial = try await waitForProgress(model, fixture: fixture, accepted: 32_768)
    try require(partial.cancel != nil, "The selected row did not have a Cancel action.")
    try require(try !action(model, eligible.id).enabled && action(model, eligible.id).cancel == nil,
                "An unrelated row acquired the active task.")
    await selected.send()
    await model.sendEntry(eventID: eligible.id)
    partial.cancel?()
    await first.value

    var paused = try action(model, fixture.event)
    guard case .paused = paused.state else { throw TestFailure("Cancel did not pause the selected row.") }
    try require(paused.enabled && paused.cancel == nil && paused.confirmedBytesText == partial.confirmedBytesText,
                "A paused row could not resume or lost its last confirmed count.")
    try require(model.workspace?.outbox == initial.workspace.outbox && model.lastEntrySync == nil,
                "Cancellation retired a queued change or confirmed completion.")
    print("first attempt: 32768 of \(fixture.photoBytes) bytes confirmed → Send paused")

    if environment["FIELDLOG_ENTRY_SYNC_TEST_PAUSE_AGAIN"] == "1" {
      let attempt = paused
      let resumeBeforeReceipt = Task { await attempt.send() }
      try await waitForMarker("held-resume-receipt", in: root)
      let checking = try action(model, fixture.event)
      try require(checking.state == .sending(nil, cancelling: false) && checking.cancel != nil,
                  "Resumed send did not wait for a freshly confirmed count.")
      checking.cancel?()
      await resumeBeforeReceipt.value
      paused = try action(model, fixture.event)
      try require(paused.state == attempt.state && paused.confirmedBytesText == attempt.confirmedBytesText,
                  "Cancelling a resume before its first receipt discarded the previous count.")
      print("second pause: last confirmed count preserved while the new receipt was pending")
    }

    let resumeAction = paused
    let resume = Task { await resumeAction.send() }
    let resumed = try await waitForProgress(model, fixture: fixture, accepted: 65_536)
    partial.cancel?()
    try require(try action(model, fixture.event).state == resumed.state,
                "An old cancel callback changed the new attempt.")
    try Data().write(to: root.appendingPathComponent("resume-progress-observed"))
    try await waitForMarker("held-final-receipt", in: root)
    _ = try await waitForProgress(model, fixture: fixture, accepted: fixture.photoBytes)
    try require(model.lastEntrySync == nil && model.workspace?.outbox == initial.workspace.outbox,
                "The row treated complete JPEG bytes as final entry confirmation.")
    try Data().write(to: root.appendingPathComponent("final-progress-observed"))
    await resume.value
    try require(model.lastEntrySync?.entry.id == fixture.entry &&
                model.lastEntrySync?.entry.attachmentIDs == [fixture.photo] &&
                model.lastEntrySync?.message == "Sent to the local backend",
                "The final receipt did not confirm the exact selected entry and JPEG.")
    try require(try queue(model).entrySyncAction(for: fixture.event) == nil &&
                model.workspace?.outbox == unrelated &&
                model.workspace?.entries == initial.workspace.entries &&
                model.workspace?.attachments == initial.workspace.attachments,
                "Acknowledgment changed unrelated rows or local records.")
    print("resume: 65536 of \(fixture.photoBytes) bytes confirmed → \(fixture.photoBytes) of \(fixture.photoBytes) bytes confirmed → Sent to the local backend")
    print("ordinary and UI-test launch isolation, unrelated rows, and stale cancellation preserved")
  }

  private static func waitForProgress(
    _ model: WorkspaceModel, fixture: Fixture, accepted: Int
  ) async throws -> EntrySyncAction {
    let expected = "\(accepted) of \(fixture.photoBytes) bytes confirmed"
    let deadline = ContinuousClock.now + .seconds(3)
    while ContinuousClock.now < deadline {
      if model.sendingEntryID == fixture.event,
        let row = try queue(model).entrySyncAction(for: fixture.event),
        row.confirmedBytesText == expected
      {
        return try action(model, fixture.event)
      }
      try await Task.sleep(for: .milliseconds(10))
    }
    let state = model.entrySyncState(for: fixture.event)
    throw TestFailure("Selected row did not show '\(expected)': \(String(describing: state))")
  }

  private static func waitForMarker(_ marker: String, in root: URL) async throws {
    let path = root.appendingPathComponent(marker).path
    let deadline = ContinuousClock.now + .seconds(5)
    while !FileManager.default.fileExists(atPath: path) {
      try require(ContinuousClock.now < deadline, "Backend marker '\(marker)' was not observed.")
      try await Task.sleep(for: .milliseconds(10))
    }
  }
}
