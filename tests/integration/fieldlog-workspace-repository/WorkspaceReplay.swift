import FieldLogModels
import FieldLogStorage
import Foundation

private enum ReplayError: Error, Equatable {
  case refused
  case injected
  case check(String)
}

private func check(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
  if try !condition() { throw ReplayError.check(message) }
}

private func roster(_ directory: URL) throws -> [String: Data] {
  let fm = FileManager.default
  var entries: [String: Data] = [:]
  let enumerator = try checkNotNil(fm.enumerator(at: directory,
    includingPropertiesForKeys: [.isDirectoryKey, .isRegularFileKey]), "Workspace enumeration")
  for case let file as URL in enumerator {
    let relative = String(file.path.dropFirst(directory.path.count + 1))
    let values = try file.resourceValues(forKeys: [.isDirectoryKey, .isRegularFileKey])
    if values.isDirectory == true {
      entries[relative + "/"] = Data()
    } else {
      try check(values.isRegularFile == true, "Unexpected file type at \(relative)")
      entries[relative] = try Data(contentsOf: file)
    }
  }
  return entries
}

private func checkNotNil<T>(_ value: T?, _ message: String) throws -> T {
  guard let value else { throw ReplayError.check(message) }
  return value
}

private func emit(_ name: String, _ directory: URL, replacements: [String: String] = [:]) throws {
  var entries: [String: String] = [:]
  for (original, data) in try roster(directory) {
    var key = original
    var bytes = data
    for (id, token) in replacements {
      key = key.replacingOccurrences(of: id.lowercased(), with: token)
      if original == "workspace.json" {
        let text = try checkNotNil(String(data: bytes, encoding: .utf8), "Snapshot encoding")
        bytes = Data(text.replacingOccurrences(of: id, with: token)
          .replacingOccurrences(of: id.lowercased(), with: token).utf8)
      }
    }
    entries[key] = bytes.base64EncodedString()
  }
  let encoded = try JSONSerialization.data(withJSONObject: ["checkpoint": name, "roster": entries],
                                              options: [.sortedKeys, .withoutEscapingSlashes])
  print(String(decoding: encoded, as: UTF8.self))
}

private func cold(_ root: URL, equals expected: Workspace) async throws {
  let before = try roster(root)
  let store = try WorkspaceRepository(directory: root)
  let state = try await store.readCommittedSnapshot()
  try check(state == expected, "Cold readback differs from the complete expected state")
  for attachment in state.attachments {
    let url = try await store.photoURL(attachment.id)
    try check(try Data(contentsOf: url) == before["photos/" + attachment.filename],
              "Attachment resolution did not preserve the disk link")
  }
  await store.close()
  try check(try roster(root) == before, "Cold reopen or close changed disk bytes")
}

private func expectUnavailable(_ store: WorkspaceRepository) async throws {
  do {
    _ = try await store.transact { _ in throw ReplayError.check("Mutation admitted after shutdown") }
    throw ReplayError.check("Closed or uncertain repository accepted a transaction")
  } catch FieldLogError.storage {
    return
  }
}

private func assertCanonicalWrite(_ state: Workspace, _ root: URL) throws {
  let encoder = JSONEncoder()
  encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
  try check(try Data(contentsOf: root.appendingPathComponent("workspace.json")) == encoder.encode(state),
            "Snapshot bytes differ from the full canonical workspace")
}

@main private enum Replay {
  static func main() async {
    do { try await run() } catch {
      FileHandle.standardError.write(Data("Workspace replay failed: \(error)\n".utf8))
      exit(1)
    }
  }

  static func run() async throws {
    let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true).standardizedFileURL
    let fixtures = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
    let fm = FileManager.default
    try fm.createDirectory(at: root, withIntermediateDirectories: false)
    for name in ["legacy", "current"] {
      let directory = root.appendingPathComponent(name)
      try fm.copyItem(at: fixtures.appendingPathComponent(name), to: directory)
      try await exercise(name, directory)
    }
    let uncertain = root.appendingPathComponent("uncertain")
    try fm.copyItem(at: fixtures.appendingPathComponent("current"), to: uncertain)
    try await uncertainWrite(uncertain)
  }

  static func exercise(_ name: String, _ root: URL) async throws {
    let file = root.appendingPathComponent("workspace.json")
    let seed = try JSONDecoder().decode(Workspace.self, from: Data(contentsOf: file))
    try await cold(root, equals: seed)
    let store = try WorkspaceRepository(directory: root)
    do {
      _ = try WorkspaceRepository(directory: root)
      throw ReplayError.check("Second owner acquired the same workspace")
    } catch FieldLogError.storage {}
    try emit(name + "-cold", root)
    let project = seed.projects[0].id
    let draft = seed.drafts[0]
    let selection = try await store.selectSavedDraft(projectID: project, draftID: draft.id)
    let date = Date(timeIntervalSinceReferenceDate: 796405701.25)
    let task = try await store.transact(expectedRevision: seed.revision) {
      try $0.saveTask(projectID: project, title: "  Verify / 東京 e\u{301}\n  ",
                      responsible: "  Zoë  ", now: date)
    }
    try check(task.revision == seed.revision + 1 && task.tasks.count == 1, "Task Save revision/roster")
    let record = task.tasks[0]
    let taskEvent = try checkNotNil(task.outbox.last, "Task Save outbox")
    try check(record.title.utf8.elementsEqual("Verify / 東京 e\u{301}".utf8) &&
              record.responsible.utf8.elementsEqual("  Zoë  ".utf8) && taskEvent.kind == .taskSaved &&
              taskEvent.recordID == record.id && taskEvent.revision == task.revision &&
              Array(task.outbox.dropLast()) == seed.outbox && task.drafts == seed.drafts &&
              task.entries == seed.entries, "Task Save bytes or preservation")
    var ids = [record.id.uuidString: "NEW-TASK", taskEvent.id.uuidString: "NEW-TASK-EVENT"]
    try assertCanonicalWrite(task, root)
    try emit(name + "-task-saved", root, replacements: ids)

    let beforeRefusal = try roster(root)
    let jpeg = Data([0xff, 0xd8, 0xff, 0xe0, 0x42, 0xff, 0xd9])
    var edited = draft
    edited.title = "  Merged / Café  "
    edited.attachmentIDs = []       // Caller holds a stale list. The saved link must survive.
    edited.followUpRequired = false // Ordinary save cannot overwrite the installed optional value.
    let edit = edited
    do {
      #if ANDROID_EXPORT
      _ = try await store.attachPhoto(jpeg: jpeg, to: edit, expectedRevision: task.revision, now: date) { next in
        guard next.drafts[0].attachmentIDs.count == 2, next.attachments.count == 2,
          next.drafts[0].followUpRequired == draft.followUpRequired else {
          throw ReplayError.check("Precommit did not see the real merged projection and reference")
        }
        throw ReplayError.refused
      }
      #else
      _ = try await store.transact(expectedRevision: task.revision) {
        try $0.saveDraft(edit)
        throw ReplayError.refused
      }
      #endif
      throw ReplayError.check("Precommit refusal was swallowed")
    } catch ReplayError.refused {}
    let refused = try await store.readCommittedSnapshot()
    try check(refused == task && roster(root) == beforeRefusal, "Refused precommit changed workspace files")
    try emit(name + "-refused", root, replacements: ids)
    do {
      _ = try await store.transact(expectedRevision: seed.revision) { _ in
        throw ReplayError.check("Stale revision reached mutation")
      }
      throw ReplayError.check("Stale revision was admitted")
    } catch FieldLogError.staleRevision {}

    let attached: Workspace
    #if ANDROID_EXPORT
    attached = try await store.attachPhoto(jpeg: jpeg, to: edit, expectedRevision: task.revision, now: date) {
      guard $0.drafts[0].attachmentIDs.count == 2,
        $0.restoration.openDraftID == edit.id,
        $0.restoration.selectedProjectID == project else { throw ReplayError.check("Android projection") }
    }
    try check(attached.revision == task.revision + 1, "Android photo used multiple commits")
    #else
    let saved = try await store.transact(expectedRevision: task.revision) { try $0.saveDraft(edit) }
    try check(saved.drafts[0].attachmentIDs == draft.attachmentIDs, "Apple draft save lost photo")
    attached = try await store.addPhoto(jpeg: jpeg, to: edit.id, now: date)
    try check(attached.revision == task.revision + 2, "Apple save then attach revision")
    #endif
    let photo = try checkNotNil(attached.attachments.last, "Photo record")
    ids[photo.id.uuidString] = "NEW-PHOTO"
    let photoURL = try await store.photoURL(photo.id)
    let selected = try await store.readSelectedDraft(selection)
    try check(try Data(contentsOf: photoURL) == jpeg &&
              attached.drafts[0].attachmentIDs == draft.attachmentIDs + [photo.id] &&
              attached.drafts[0].followUpRequired == draft.followUpRequired &&
              attached.outbox == task.outbox && selected.draft == attached.drafts[0],
              "Attachment bytes, old links, follow-up, selection or outbox changed")
    try assertCanonicalWrite(attached, root)
    try emit(name + "-attached", root, replacements: ids)

    let committed = try await store.transact(expectedRevision: attached.revision) {
      try $0.saveDraft(edit)
      try $0.commitDraft(edit.id, now: date)
    }
    let entry = try checkNotNil(committed.entries.last, "Committed entry")
    let event = try checkNotNil(committed.outbox.last, "Entry commit outbox")
    ids[event.id.uuidString] = "NEW-ENTRY-EVENT"
    let ended = try await store.readSelectedDraft(selection)
    try check(committed.revision == attached.revision + 1 && committed.entries[0] == seed.entries[0] &&
              committed.drafts == [seed.drafts[1]] && committed.restoration.openDraftID == nil &&
              entry.id == edit.id && entry.projectID == project && entry.title == "Merged / Café" &&
              entry.attachmentIDs == attached.drafts[0].attachmentIDs &&
              entry.followUpRequired == draft.followUpRequired && ended.draft == nil &&
              event.kind == .entrySaved && event.recordID == entry.id && event.revision == committed.revision &&
              Array(committed.outbox.dropLast()) == attached.outbox,
              "Commit lost draft lifetime, legacy pair, outbox, or references")
    try assertCanonicalWrite(committed, root)
    await store.close()
    try await expectUnavailable(store)
    try await cold(root, equals: committed)
    try emit(name + "-committed-cold", root, replacements: ids)
  }

  static func uncertainWrite(_ root: URL) async throws {
    let before = try Data(contentsOf: root.appendingPathComponent("workspace.json"))
    let initial = try JSONDecoder().decode(Workspace.self, from: before)
    let store = try WorkspaceRepository(directory: root) {
      if $0 == "after_rename" { throw ReplayError.injected }
    }
    do {
      _ = try await store.transact(expectedRevision: initial.revision) {
        $0.restoration.openDraftID = nil
      }
      throw ReplayError.check("Post-rename failure was swallowed")
    } catch ReplayError.injected {}
    let cached = await store.snapshot()
    try check(cached == initial, "Uncertain write published an in-memory revision")
    try await expectUnavailable(store)
    await store.close()
    var expected = initial
    expected.revision += 1
    expected.restoration.openDraftID = nil
    try assertCanonicalWrite(expected, root)
    try await cold(root, equals: expected)
    try emit("post-rename-uncertain-cold", root)
  }
}
