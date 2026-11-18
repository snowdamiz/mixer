import Foundation
import Testing
import MixerUI
@testable import FieldLogFeatures
@testable import MixerApple
import FieldLogStorage

@MainActor private func saveEvent(_ owner: TaskEditorAppleFieldsHost) throws -> UIEventEnvelope {
  let snapshot = owner.snapshot.render
  return UIEventEnvelope(revision: snapshot.document.revision,
    identity: try #require(snapshot.identity(for: "task.save")), event: .activate)
}

@MainActor private func enterTitle(_ owner: TaskEditorAppleFieldsHost) throws {
  let native = owner.nativeHost.snapshot
  let event = UIEventEnvelope(revision: native.document.revision,
    identity: try #require(native.identity(for: "task.title")),
    event: .textChange, value: .string("Inspect pump"))
  let action = try owner.nativeHost.route(event)
  try owner.accept(action, from: owner.nativeHost, installation: owner.installation)
}

@Test("One displayed binding, two callbacks, and one ordinary Add persist the exact accepted value",
  arguments: [false, true])
@MainActor func ordinaryTaskEditorSaveOrdering(tracksText: Bool) async throws {
  let directory = FileManager.default.temporaryDirectory.appendingPathComponent("fieldlog-save-\(UUID())")
  defer { try? FileManager.default.removeItem(at: directory) }
  let repository = try WorkspaceRepository(directory: directory)
  let initial = try await repository.transact {
    try $0.createProject(title: "Checklist workshop", site: "")
  }
  let projectID = try #require(initial.projects.first?.id)
  let owner = try TaskEditorAppleFieldsHost { title, responsible in
    do {
      _ = try await repository.transact {
        try $0.saveTask(projectID: projectID, title: title, responsible: responsible)
      }
      return .saved
    } catch { return .failed(error.localizedDescription) }
  }
  try enterTitle(owner)
  let host = owner.nativeHost
  let receipt = owner.installation
  let field = try #require(receipt.native.document.root.children.last)
  #expect(field.id == "task.responsible")
  var errors: [UIRoutingError] = []
  var revisions: [UInt64] = []
  let binding = mixerNativeTextBinding(node: field, snapshot: receipt.native,
    host: tracksText ? host : nil) { envelope in
    revisions.append(envelope.revision)
    do {
      if tracksText {
        try owner.acceptIssued(host.routeIssued(envelope), from: host)
      } else {
        owner.receive(try host.route(envelope), from: host, installation: receipt)
      }
      return true
    } catch let error as UIRoutingError { errors.append(error) }
    catch { Issue.record(error) }
    return false
  }
  let before = receipt.native.document.revision
  binding.wrappedValue = "Night shif"
  binding.wrappedValue = "Night shift"
  let expected = tracksText ? "Night shift" : "Night shif"
  #expect(revisions == [before, tracksText ? before + 1 : before])
  #expect(errors == (tracksText ? [] : [.staleRevision]))
  #expect(owner.snapshot.state.responsible == expected)
  #expect(binding.wrappedValue == (tracksText ? expected : ""))
  try owner.acceptNative(saveEvent(owner))
  await owner.waitForSave()
  #expect(owner.snapshot.outcome == .saved)
  let committed = await repository.snapshot()
  #expect(committed.revision == 2 && committed.outbox.map(\.kind) == [.projectCreated, .taskSaved])
  #expect(committed.tasks.count == 1)
  #expect(committed.tasks.first?.title == "Inspect pump")
  #expect(committed.tasks.first?.responsible == expected)
  try owner.close()
  await repository.close()
  let reopened = try WorkspaceRepository(directory: directory)
  #expect(await reopened.snapshot() == committed)
  await reopened.close()
  print("ORDERING tracksText=\(tracksText) revisions=\(revisions) routingErrors=\(errors) persisted=\(expected.debugDescription)")
}

@Test @MainActor func unrelatedRenderDoesNotAdvanceTextCursorOrSave() throws {
  let owner = try TaskEditorAppleFieldsHost { _, _ in .failed("Unexpected Save") }
  try enterTitle(owner)
  let host = owner.nativeHost
  let before = host.snapshot
  let field = try #require(before.document.root.children.last)
  let staleSave = try saveEvent(owner)
  var errors: [UIRoutingError] = []
  let binding = mixerNativeTextBinding(node: field, snapshot: before, host: host) { event in
    do {
      try owner.acceptIssued(host.routeIssued(event), from: host)
      return true
    }
    catch let error as UIRoutingError { errors.append(error) }
    catch { Issue.record(error) }
    return false
  }
  binding.wrappedValue = "First"
  let latest = host.snapshot
  let unrelated = UIEventEnvelope(revision: latest.document.revision,
    identity: try #require(latest.identity(for: "task.title")),
    event: .textChange, value: .string("Unrelated edit"))
  try owner.acceptIssued(host.routeIssued(unrelated), from: host)
  binding.wrappedValue = "Late"
  #expect(errors == [.staleRevision])
  #expect(owner.snapshot.state.responsible == "First")
  #expect(throws: UIRoutingError.staleRevision) { try owner.acceptNative(staleSave) }
  try owner.close()
  binding.wrappedValue = "After close"
  #expect(owner.snapshot.state.responsible == "First")
}

@Test @MainActor func foreignAndExpiredIssuedEventsCannotUseCurrentReceipt() throws {
  let owner = try TaskEditorAppleFieldsHost { _, _ in .failed("Unused") }
  let host = owner.nativeHost
  let foreign = try MixerUIHost(document: host.snapshot.document)
  let native = host.snapshot
  let event = UIEventEnvelope(revision: native.document.revision,
    identity: try #require(native.identity(for: "task.responsible")),
    event: .textChange, value: .string("Foreign or expired"))
  let foreignIssued = try foreign.routeIssued(event)
  #expect(throws: UIRoutingError.staleIdentity) { try owner.acceptIssued(foreignIssued, from: host) }
  #expect(owner.snapshot.state.responsible.isEmpty)
  let expired = try host.routeIssued(event)
  try enterTitle(owner)
  #expect(throws: UIRoutingError.staleRevision) { try owner.acceptIssued(expired, from: host) }
  #expect(owner.snapshot.state.responsible.isEmpty)
  try owner.close()
}

@Test @MainActor func finalCallbackAfterAddCannotChangeTheAdmittedSave() async throws {
  let owner = try TaskEditorAppleFieldsHost { _, responsible in
    #expect(responsible == "Night shif")
    return .saved
  }
  try enterTitle(owner)
  let host = owner.nativeHost
  let before = host.snapshot
  let field = try #require(before.document.root.children.last)
  var errors: [UIRoutingError] = []
  let binding = mixerNativeTextBinding(node: field, snapshot: before, host: host) { event in
    do {
      try owner.acceptIssued(host.routeIssued(event), from: host)
      return true
    }
    catch let error as UIRoutingError { errors.append(error) }
    catch { Issue.record(error) }
    return false
  }
  binding.wrappedValue = "Night shif"
  try owner.acceptNative(saveEvent(owner))
  binding.wrappedValue = "Night shift"
  #expect(errors == [.staleRevision])
  let saving = host.snapshot
  let current = UIEventEnvelope(revision: saving.document.revision,
    identity: try #require(saving.identity(for: field.id)), event: .textChange, value: .string("Night shift"))
  #expect(throws: UIRoutingError.disabledNode) { _ = try host.routeIssued(current) }
  await owner.waitForSave()
  #expect(owner.snapshot.outcome == .saved)
  #expect(owner.snapshot.state.responsible == "Night shif")
  try owner.close()
}

@Test @MainActor func currentBindingFailureIsVisibleAndStaleFailureCannotOverwriteIt() throws {
  let owner = try TaskEditorAppleFieldsHost { _, _ in .failed("Unused") }
  let host = owner.nativeHost
  let before = host.snapshot
  let field = try #require(before.document.root.children.last)
  let identity = try #require(before.identity(for: field.id))
  let nativeView = MixerNativeView(host: host, trackSynchronousTextChanges: true,
    onIssuedAction: { try owner.acceptIssued($0, from: host) },
    onEventFailure: { owner.record($1, from: host, event: $0) })
  let binding = mixerNativeTextBinding(node: field, snapshot: before, host: host,
    dispatch: nativeView.dispatchEvent)
  binding.wrappedValue = "Night shift"
  #expect(owner.eventFailure == nil)
  binding.wrappedValue = String(repeating: "x", count: 16_385)
  let currentError = try #require(owner.eventFailure)
  #expect(owner.snapshot.state.responsible == "Night shift")
  #expect(binding.wrappedValue == "Night shift")
  #expect(!nativeView.dispatchEvent(UIEventEnvelope(revision: before.document.revision,
    identity: identity, event: .textChange, value: .string("Old callback"))))
  #expect(owner.eventFailure == currentError)
  binding.wrappedValue = "Morning shift"
  #expect(owner.eventFailure == nil)
  #expect(owner.snapshot.state.responsible == "Morning shift")
  try owner.close()
}
