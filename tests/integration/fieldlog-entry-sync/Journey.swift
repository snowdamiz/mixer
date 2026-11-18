import AppKit
import FieldLogModels
import FieldLogStorage
import Foundation

private let note = "  Exact offline spacing\n\n測定 · العربية\n"

private struct TestFailure: Error, CustomStringConvertible {
  let description: String
  init(_ description: String) { self.description = description }
}

private func require(_ condition: Bool, _ message: String) throws {
  guard condition else { throw TestFailure(message) }
}

private func syntheticJPEG(width: Int, height: Int, seed: UInt32) throws -> Data {
  let rowBytes = width * 3
  guard let image = NSBitmapImageRep(
    bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height, bitsPerSample: 8, samplesPerPixel: 3,
    hasAlpha: false, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: rowBytes, bitsPerPixel: 24
  ), let pixels = image.bitmapData else { throw TestFailure("Could not create synthetic pixels.") }
  var state = seed
  for index in 0..<(rowBytes * height) {
    state = state &* 1_664_525 &+ 1_013_904_223
    pixels[index] = UInt8(truncatingIfNeeded: state >> 24)
  }
  guard let jpeg = image.representation(using: .jpeg, properties: [.compressionFactor: 0.83]),
    let decoded = NSBitmapImageRep(data: jpeg), decoded.pixelsWide == width, decoded.pixelsHigh == height
  else { throw TestFailure("Could not encode and decode the synthetic JPEG.") }
  return jpeg
}

private struct Fixture: Codable {
  let workspace: UUID
  let project: UUID
  let otherProject: UUID
  let event: UUID
  let otherEvent: UUID
  let entry: UUID
  let photo: UUID
  let otherPhoto: UUID
}

@main struct Journey {
  static func main() async throws {
    let arguments = CommandLine.arguments
    guard arguments.count == 3 else { throw TestFailure("Expected offline/online and a scratch path.") }
    let root = URL(fileURLWithPath: arguments[2], isDirectory: true)
    switch arguments[1] {
    case "offline": try await saveOffline(root)
    case "online": try await goOnline(root)
    default: throw TestFailure("Unknown test phase.")
    }
  }

  private static func saveOffline(_ root: URL) async throws {
    let directory = root.appendingPathComponent("workspace")
    let store = try WorkspaceRepository(directory: directory)
    let opening = await store.snapshot()
    try require(opening.projects.isEmpty && opening.outbox.isEmpty, "Expected a fresh workspace.")
    let project = UUID()
    let otherProject = UUID()
    let draft = EntryDraft(projectID: project, title: "Window inspection", note: note)
    let otherDraft = EntryDraft(projectID: otherProject, title: "Independent project", note: "Private")
    try await store.transact {
      try $0.createProject(id: project, title: "Workshop", site: "North")
      try $0.createProject(id: otherProject, title: "Other team", site: "South")
      try $0.saveTask(projectID: project, title: "Check window", responsible: "Synthetic operator")
      try $0.saveDraft(draft)
      try $0.saveDraft(otherDraft)
    }
    let jpeg = try syntheticJPEG(width: 640, height: 480, seed: 17)
    let otherJPEG = try syntheticJPEG(width: 8, height: 8, seed: 73)
    _ = try await store.addPhoto(jpeg: jpeg, to: draft.id)
    let afterPhotos = try await store.addPhoto(jpeg: otherJPEG, to: otherDraft.id)
    await store.close()

    let reopened = try WorkspaceRepository(directory: directory)
    let restored = await reopened.snapshot()
    try require(restored == afterPhotos, "Offline drafts and photo links did not survive reopen.")
    let saved = try await reopened.transact {
      try $0.commitDraft(draft.id)
      try $0.commitDraft(otherDraft.id)
    }
    guard let entry = saved.entries(for: project).first,
      let photo = entry.attachmentIDs.first,
      let otherPhoto = saved.entries(for: otherProject).first?.attachmentIDs.first,
      let event = saved.outbox.first(where: { $0.kind == .entrySaved && $0.recordID == draft.id }),
      let otherEvent = saved.outbox.first(where: { $0.kind == .entrySaved && $0.recordID == otherDraft.id })
    else { throw TestFailure("Offline commit failed to queue both original entries.") }
    try require(entry.note == note && entry.id == draft.id, "Saved entry content or identity changed.")
    let local = try await reopened.photoURL(photo)
    let otherLocal = try await reopened.photoURL(otherPhoto)
    try require(try Data(contentsOf: local) == jpeg, "Offline JPEG bytes changed.")
    try require(try Data(contentsOf: otherLocal) == otherJPEG, "Second project's JPEG bytes changed.")
    let report = try await reopened.exportReport(projectID: project)
    let reportBytes = try Data(contentsOf: report)
    let reportText = String(decoding: reportBytes, as: UTF8.self)
    try require(reportText.contains(note) && reportText.contains("Photos: 1"), "Unexpected offline report.")
    try require(!reportText.contains(otherDraft.title), "Offline report leaked another project.")

    let fixture = Fixture(
      workspace: saved.id, project: project, otherProject: otherProject, event: event.id,
      otherEvent: otherEvent.id, entry: entry.id, photo: photo, otherPhoto: otherPhoto)
    try JSONEncoder().encode(fixture).write(to: root.appendingPathComponent("fixture.json"))
    try reportBytes.write(to: root.appendingPathComponent("original-report.txt"))
    await reopened.close()
    print("offline: saved both entries and JPEGs, reopened drafts, and exported the scoped report")
  }

  private static func goOnline(_ root: URL) async throws {
    let env = ProcessInfo.processInfo.environment
    guard let port = env["FIELDLOG_TEST_PORT"].flatMap(UInt16.init),
      let token = env["FIELDLOG_TEST_OWNER_TOKEN"],
      let otherToken = env["FIELDLOG_TEST_OTHER_TOKEN"],
      let invalidToken = env["FIELDLOG_TEST_INVALID_TOKEN"]
    else { throw TestFailure("Missing synthetic backend session.") }
    let fixture = try JSONDecoder().decode(
      Fixture.self, from: Data(contentsOf: root.appendingPathComponent("fixture.json")))
    let directory = root.appendingPathComponent("workspace")
    let repository = try WorkspaceRepository(directory: directory)
    let original = await repository.snapshot()
    let photo = try await repository.photoURL(fixture.photo)
    let otherPhoto = try await repository.photoURL(fixture.otherPhoto)
    let originalJPEG = try Data(contentsOf: photo)
    let otherJPEG = try Data(contentsOf: otherPhoto)
    let originalReport = try Data(contentsOf: root.appendingPathComponent("original-report.txt"))
    let owner = try EntrySyncClient(
      port: port, workspaceID: fixture.workspace, projectID: fixture.project, token: token)

    let alreadyCancelled = Task {
      withUnsafeCurrentTask { $0?.cancel() }
      try await owner.send(eventID: fixture.event, from: repository)
    }
    do {
      _ = try await alreadyCancelled.value
      throw TestFailure("An already-cancelled send succeeded.")
    } catch is CancellationError {
      try require(await repository.snapshot() == original, "A cancelled request changed local state.")
    }

    let invalid = try EntrySyncClient(
      port: port, workspaceID: fixture.workspace, projectID: fixture.project, token: invalidToken)
    try await expectRejection(.rejected(401), client: invalid, event: fixture.event, store: repository)
    let other = try EntrySyncClient(
      port: port, workspaceID: fixture.workspace, projectID: fixture.project, token: otherToken)
    try await expectRejection(.rejected(404), client: other, event: fixture.event, store: repository)
    let otherProject = try EntrySyncClient(
      port: port, workspaceID: fixture.workspace, projectID: fixture.otherProject, token: token)
    try await expectRejection(.wrongScope, client: otherProject, event: fixture.event, store: repository)
    try await expectRejection(.rejected(404), client: otherProject, event: fixture.otherEvent, store: repository)
    let wrongWorkspace = try EntrySyncClient(
      port: port, workspaceID: UUID(), projectID: fixture.project, token: token)
    try await expectRejection(.wrongScope, client: wrongWorkspace, event: fixture.event, store: repository)
    try require(await repository.snapshot() == original, "A rejected request changed local state.")
    print("online: rejected invalid credentials, another user, and an unprovisioned project")

    do {
      try await owner.send(eventID: fixture.event, from: repository)
      throw TestFailure("A truncated post-commit acknowledgment was accepted.")
    } catch let error as URLError {
      try require(error.code == .networkConnectionLost, "Unexpected transport failure: \(error.code).")
    }
    try require(await repository.snapshot() == original, "Transport failure changed local state.")
    try require(try Data(contentsOf: photo) == originalJPEG, "Transport failure changed the JPEG.")
    await repository.close()
    let retryStore = try WorkspaceRepository(directory: directory)
    try require(await retryStore.snapshot() == original, "Pending event did not survive process-style reopen.")

    // The runner replaces the first valid replay receipt with a wrong photo ID.
    try await expectRejection(.invalidReceipt, client: owner, event: fixture.event, store: retryStore)
    try require(await retryStore.snapshot() == original, "Mismatched receipt cleared the queue.")
    try await cancelDuringReplay(owner, event: fixture.event, store: retryStore, root: root)
    try require(await retryStore.snapshot() == original, "A cancelled retry cleared the queue.")

    let outcome = try await owner.send(eventID: fixture.event, from: retryStore)
    try require(outcome == .reconciled, "Expected the existing remote event to be reconciled.")

    var expected = original
    expected.revision += 1
    expected.outbox.removeAll { $0.id == fixture.event }
    try require(await retryStore.snapshot() == expected, "Retry changed more than one queued event.")
    await retryStore.close()
    let confirmed = try WorkspaceRepository(directory: directory)
    try require(await confirmed.snapshot() == expected, "The queue acknowledgment was not durable.")
    let confirmedPhoto = try await confirmed.photoURL(fixture.photo)
    let confirmedOtherPhoto = try await confirmed.photoURL(fixture.otherPhoto)
    try require(try Data(contentsOf: confirmedPhoto) == originalJPEG, "Retry changed the uploaded JPEG.")
    try require(try Data(contentsOf: confirmedOtherPhoto) == otherJPEG, "Retry changed the other project's JPEG.")
    let export = try await confirmed.exportReport(projectID: fixture.project)
    try require(try Data(contentsOf: export) == originalReport, "Retry changed the local report.")
    await confirmed.close()
    print("online: refused truncated and mismatched receipts, cancelled a replay, reconciled the same event, preserved records and export")
  }

  private static func cancelDuringReplay(
    _ client: EntrySyncClient, event: UUID, store: WorkspaceRepository, root: URL
  ) async throws {
    let reachedServer = root.appendingPathComponent("cancel-ready")
    let returnedFromCancellation = root.appendingPathComponent("cancel-returned")
    let pending = Task { try await client.send(eventID: event, from: store) }
    defer { pending.cancel() }
    let deadline = ContinuousClock.now + .seconds(3)
    while !FileManager.default.fileExists(atPath: reachedServer.path) {
      try require(ContinuousClock.now < deadline, "The cancellation replay did not reach the server.")
      try await Task.sleep(for: .milliseconds(10))
    }
    pending.cancel()
    switch await pending.result {
    case .failure(let error) where error is CancellationError:
      break
    case .failure(let error as URLError) where error.code == .cancelled:
      break
    default:
      throw TestFailure("The in-flight retry did not return cancellation.")
    }
    try Data().write(to: returnedFromCancellation)
  }

  private static func expectRejection(
    _ failure: EntrySyncClient.Failure, client: EntrySyncClient, event: UUID, store: WorkspaceRepository
  ) async throws {
    do {
      try await client.send(eventID: event, from: store)
      throw TestFailure("Expected \(failure) but the request succeeded.")
    } catch let actual as EntrySyncClient.Failure {
      try require(actual == failure, "Expected \(failure), received \(actual).")
    }
  }
}
