import FieldLogModels
import FieldLogStorage
import Foundation

private struct TestFailure: Error, CustomStringConvertible {
  let description: String
  init(_ description: String) { self.description = description }
}

private func require(_ condition: Bool, _ message: String) throws {
  guard condition else { throw TestFailure(message) }
}

private struct Fixture: Decodable {
  let workspace: UUID
  let project: UUID
  let event: UUID
  let photo: UUID
  let otherPhoto: UUID
}

private struct ObservedProgress: Encodable, Sendable {
  let acceptedBytes: Int
  let totalBytes: Int
}

private final class ProgressLog: @unchecked Sendable {
  private let lock = NSLock()
  private var values: [ObservedProgress] = []

  func append(_ progress: EntrySyncClient.PhotoProgress) {
    lock.withLock {
      values.append(.init(acceptedBytes: progress.acceptedBytes, totalBytes: progress.totalBytes))
    }
  }

  func snapshot() -> [ObservedProgress] {
    lock.withLock { values }
  }
}

@main struct ResumeJourney {
  static func main() async throws {
    let arguments = CommandLine.arguments
    guard arguments.count == 3 else { throw TestFailure("Expected a phase and an owned scratch path.") }
    let phase = arguments[1]
    let root = URL(fileURLWithPath: arguments[2], isDirectory: true)
    let decoder = JSONDecoder()
    let fixture = try decoder.decode(Fixture.self, from: Data(contentsOf: root.appendingPathComponent("fixture.json")))
    let original = try decoder.decode(Workspace.self, from: Data(contentsOf: root.appendingPathComponent("offline-workspace.json")))
    let store = try WorkspaceRepository(directory: root.appendingPathComponent("workspace"))
    let progress = ProgressLog()
    var acknowledged = original
    acknowledged.revision += 1
    acknowledged.outbox.removeAll { $0.id == fixture.event }
    try require(acknowledged.outbox.count + 1 == original.outbox.count, "The fixture did not select one queued event.")

    if phase == "verify" {
      try require(await store.snapshot() == acknowledged, "A fresh repository did not reopen with the precise acknowledgment.")
    } else {
      try require(await store.snapshot() == original, "A fresh repository did not reopen with the original event pending.")
      let env = ProcessInfo.processInfo.environment
      guard let port = env["FIELDLOG_TEST_PORT"].flatMap(UInt16.init),
        let token = env["FIELDLOG_TEST_OWNER_TOKEN"]
      else { throw TestFailure("Missing the owned loopback session.") }
      let client = try EntrySyncClient(
        port: port, workspaceID: fixture.workspace, projectID: fixture.project, token: token)
      try await send(phase, client: client, event: fixture.event, store: store, progress: progress, root: root)
      let expected = phase == "replay" ? acknowledged : original
      try require(await store.snapshot() == expected, "Unexpected local repository change in \(phase).")
    }

    for id in [fixture.photo, fixture.otherPhoto] {
      let fresh = try await store.photoURL(id)
      let original = root.appendingPathComponent("offline-\(id.uuidString.lowercased()).jpg")
      try require(try Data(contentsOf: fresh) == Data(contentsOf: original), "A saved photo changed in \(phase).")
    }
    await store.close()
    let data = try JSONEncoder().encode(progress.snapshot())
    print(String(decoding: data, as: UTF8.self))
  }

  private static func send(
    _ phase: String, client: EntrySyncClient, event: UUID, store: WorkspaceRepository,
    progress: ProgressLog, root: URL
  ) async throws {
    let observer: @Sendable (EntrySyncClient.PhotoProgress) -> Void = { progress.append($0) }
    switch phase {
    case "drop-chunk", "drop-final":
      do {
        try await client.send(eventID: event, from: store, onProgress: observer)
        throw TestFailure("The truncated response in \(phase) was accepted.")
      } catch let error as URLError {
        try require(error.code == .networkConnectionLost, "Unexpected transport error in \(phase): \(error.code).")
      }
    case "invalid-progress", "oversized-progress":
      do {
        try await client.send(eventID: event, from: store, onProgress: observer)
        throw TestFailure("An invalid progress response was accepted.")
      } catch let error as EntrySyncClient.Failure {
        try require(error == .invalidProgress, "Expected invalidProgress, received \(error).")
      }
    case "cancel":
      let task = Task { try await client.send(eventID: event, from: store, onProgress: observer) }
      defer { task.cancel() }
      let ready = root.appendingPathComponent("cancel-ready")
      let deadline = ContinuousClock.now + .seconds(6)
      while !FileManager.default.fileExists(atPath: ready.path) {
        try require(ContinuousClock.now < deadline, "No committed chunk reached the cancellation barrier.")
        try await Task.sleep(for: .milliseconds(10))
      }
      task.cancel()
      switch await task.result {
      case .failure(let error) where error is CancellationError:
        break
      case .failure(let error as URLError) where error.code == .cancelled:
        break
      default:
        throw TestFailure("Explicit Task.cancel() did not cancel the in-flight send.")
      }
      try Data().write(to: root.appendingPathComponent("cancel-returned"), options: .atomic)
    case "replay":
      let result = try await client.send(eventID: event, from: store, onProgress: observer)
      try require(result == .reconciled, "The lost final receipt was not reconciled.")
    default:
      throw TestFailure("Unknown phase \(phase).")
    }
  }
}
