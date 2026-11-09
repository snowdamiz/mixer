import Foundation
import FieldLogModels
import FieldLogStorage
import FieldLogFeatures
import MixerUI
import MixerAndroid


private typealias NativeCall = @convention(c) (Int64, Int32, UnsafePointer<UInt8>?, Int, UnsafePointer<UInt8>?, Int, UnsafePointer<UInt8>?, Int) -> Int32
nonisolated(unsafe) private var nativeCall: NativeCall?
@_cdecl("fieldlog_set_surface_callback")
public func fieldlogSetSurfaceCallback(_ call: @convention(c) @escaping (Int64, Int32, UnsafePointer<UInt8>?, Int, UnsafePointer<UInt8>?, Int, UnsafePointer<UInt8>?, Int) -> Int32) { nativeCall = call }
@MainActor private final class PresentationAdapter: AndroidUIPresentation {
  let form: TaskEditorPresentation
  init(_ form: TaskEditorPresentation) { self.form = form }
  var snapshot: UIRenderSnapshot { form.snapshot.render }
  func observe(_ receive: @escaping @MainActor (UIRenderSnapshot) -> Void) -> @MainActor () -> Void {
    let id = form.observe { receive($0.render) }
    return { [form] in form.removeObserver(id) }
  }
  func send(_ event: UIEventEnvelope) throws { try form.send(event) }
}
@MainActor private final class JNISurface: AndroidUINativeSurface {
  let context: Int64
  init(context: Int64) { self.context = context }
  let profile: AndroidUIProfile = .measuredMultilineRetirementV3
  var capabilities: AndroidUICapabilities { profile.capabilities }
  private func call(_ operation: Int32, _ owner: UUID, packet: Data = Data(), appearance: Data = Data()) throws {
    guard let nativeCall else { throw FieldLogError.validation("JNI surface unavailable outside Android UI pump") }
    let identity = Array(owner.uuidString.utf8)
    let status = identity.withUnsafeBufferPointer { token in
      packet.withUnsafeBytes { bytes in appearance.withUnsafeBytes { descriptor in
        nativeCall(context, operation, token.baseAddress, token.count, bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count,
          descriptor.bindMemory(to: UInt8.self).baseAddress, descriptor.count)
      } }
    }
    guard status == 0 else { throw FieldLogError.validation("Synchronous native surface rejected operation \(operation)") }
  }
  func activate(owner: UUID) throws { try call(0, owner) }
  func install(_ frame: AndroidUIFrame) throws { try call(1, frame.owner, packet: frame.packet, appearance: frame.appearanceDescriptorV2) }
  func revoke(owner: UUID) { do { try call(2, owner) } catch { Application.shared.recordSurfaceFailure(context, String(describing: error)) } }
}

private final class ReplyBox: @unchecked Sendable {
  let mailbox = ActivityMailbox()
  private let lock = NSLock()
  private var tail: Task<Void, Never>?
  func enqueue(_ context: Int64, _ text: String) -> Bool {
    guard let input = (try? JSONSerialization.jsonObject(with: Data(text.utf8))) as? [String: Any],
          let request = input["requestID"] as? String, UUID(uuidString: request) != nil,
          let command = input["command"] as? String, ["open", "event", "refresh"].contains(command) else { return false }
    lock.lock(); defer { lock.unlock() }
    guard let ticket = mailbox.reserve(context, request: request) else { return false }
    let previous = tail
    tail = Task { @MainActor in
      await previous?.value
      guard self.mailbox.accepts(ticket) else { return }
      self.mailbox.complete(ticket, reply: await Application.shared.execute(context, text))
    }
    return true
  }
  func close(_ context: Int64) -> Bool {
    lock.lock(); defer { lock.unlock() }
    guard mailbox.cancel(context) else { return false }
    let previous = tail
    tail = Task { @MainActor in
      await previous?.value
      do {
        try await Application.shared.close(context)
        guard let nativeCall, nativeCall(context, 3, nil, 0, nil, 0, nil, 0) == 0 else {
          throw FieldLogError.validation("JNI context release rejected: \(context)")
        }
        self.mailbox.release(context)
      } catch { print("FieldLogContextR24 close FAILED context=\(context): \(error)") }
    }
    return true
  }
}
private let replies = ReplyBox()
@MainActor private final class Application {
  static let shared = Application()
  var repository: WorkspaceRepository?
  var presentation: TaskEditorPresentation?
  var directory: URL?
  var host: AndroidUIHost?
  var surfaceFailure: String?
  var generation: UInt64 = 0
  var currentContext: Int64?
  func recordSurfaceFailure(_ context: Int64, _ message: String) {
    // A revoked surface still reports against its own lifetime during teardown.
    precondition(currentContext == context)
    surfaceFailure = message
  }
  func requireOpen(_ context: Int64) throws {
    guard replies.mailbox.isOpen(context) else { throw FieldLogError.validation("Closed Activity context") }
  }
  func open(_ context: Int64, _ path: String) async throws {
    try requireOpen(context)
    guard path.hasPrefix("/"), !path.contains("\u{0}") else { throw FieldLogError.validation("Invalid application files directory") }
    try await closeCurrent()
    try requireOpen(context)
    currentContext = context; surfaceFailure = nil
    generation += 1
    let folder = URL(fileURLWithPath: path, isDirectory: true).appendingPathComponent("fieldlog-public-workspace", isDirectory: true)
    directory = folder
    let repo = try WorkspaceRepository(directory: folder)
    repository = repo
    var workspace = await repo.snapshot()
    if workspace.projects.isEmpty {
      workspace = try await repo.transact { next in _ = try next.createProject(title: "My local workspace", site: "") }
    }
    try requireOpen(context)
    guard let project = workspace.projects.first else { throw FieldLogError.missingRecord }
    let form = try TaskEditorPresentation { title, responsible in
      do {
        _ = try await repo.transact { next in try next.saveTask(projectID: project.id, title: title, responsible: responsible) }
        return .saved
      } catch { return .failed(error.localizedDescription) }
    }
    presentation = form
    let host = try AndroidUIHost(surface: JNISurface(context: context), profile: .measuredMultilineRetirementV3,
      appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: { [weak self] in
        Task { @MainActor [weak self] in
          guard let self, self.currentContext == context, self.presentation === form,
                replies.mailbox.isOpen(context) else { return }
          do { _ = try self.host?.deliverLatest() }
          catch { self.surfaceFailure = String(describing: error) }
        }
      })
    self.host = host
    _ = try host.replace(with: PresentationAdapter(form))
    _ = try host.deliverLatest()
    if let surfaceFailure { throw FieldLogError.validation(surfaceFailure) }
  }
  func close(_ context: Int64) async throws {
    if currentContext == context { try await closeCurrent() }
  }
  private func closeCurrent() async throws {
    host?.close(); host = nil
    if let surfaceFailure { throw FieldLogError.validation(surfaceFailure) }
    try presentation?.close(); presentation = nil
    if let repository { await repository.close() }
    repository = nil; currentContext = nil; generation += 1
  }
  func execute(_ context: Int64, _ text: String) async -> String {
    do {
      try requireOpen(context)
      let data = Data(text.utf8)
      guard let input = try JSONSerialization.jsonObject(with: data) as? [String: Any], let command = input["command"] as? String else { throw FieldLogError.validation("Invalid command") }
      if command != "open", currentContext != context { throw FieldLogError.validation("Stale Activity context") }
      switch command {
      case "open":
        guard let path = input["filesDir"] as? String else { throw FieldLogError.validation("Missing application files directory") }
        try await open(context, path)
      case "event":
        guard let presentation, let host, let event = input["event"], let textOwner = input["owner"] as? String, let owner = UUID(uuidString: textOwner) else { throw FieldLogError.validation("Closed or stale editor owner") }
        try host.send(owner: owner, event: JSONDecoder().decode(UIEventEnvelope.self, from: JSONSerialization.data(withJSONObject: event)))
        await presentation.waitForSave()
      case "refresh":
        guard let host, let presentation else { throw FieldLogError.validation("No public host to refresh") }
        _ = try host.replace(with: PresentationAdapter(presentation))
      default: throw FieldLogError.validation("Unsupported application command")
      }
      try requireOpen(context)
      if let surfaceFailure { throw FieldLogError.validation(surfaceFailure) }
      if let host { _ = try host.deliverLatest() }
      var result: [String: Any] = ["ok": true, "contextID": String(context), "owner": host?.owner?.uuidString ?? "", "requestID": input["requestID"] as? String ?? ""]
      if let presentation {
        let s = presentation.snapshot
        result["title"] = s.state.title; result["responsible"] = s.state.responsible
        result["saved"] = s.state.saved; result["canSubmit"] = s.state.canSubmit
        result["failure"] = s.renderingFailure ?? s.state.failure ?? ""
      }
      if let repository {
        let workspace = await repository.snapshot()
        result["workspaceRevision"] = String(workspace.revision)
        result["taskCount"] = workspace.tasks.count
        result["outboxCount"] = workspace.outbox.count
        result["tasks"] = workspace.tasks.map { ["id": $0.id.uuidString, "title": $0.title, "responsible": $0.responsible] }
      }
      return String(decoding: try JSONSerialization.data(withJSONObject: result), as: UTF8.self)
    } catch {
      let request = (try? JSONSerialization.jsonObject(with: Data(text.utf8))) as? [String: Any]
      return String(decoding: (try? JSONSerialization.data(withJSONObject: ["ok": false, "contextID": String(context), "error": error.localizedDescription, "requestID": request?["requestID"] as? String ?? ""])) ?? Data(), as: UTF8.self)
    }
  }
}
@_cdecl("fieldlog_context_create")
public func fieldlogContextCreate(_ context: Int64) -> Int32 { replies.mailbox.register(context) ? 0 : 1 }
@_cdecl("fieldlog_context_close")
public func fieldlogContextClose(_ context: Int64) -> Int32 { replies.close(context) ? 0 : 1 }
@_cdecl("fieldlog_submit")
public func fieldlogSubmit(_ context: Int64, _ pointer: UnsafePointer<UInt8>?, _ count: Int) -> Int32 {
  guard let pointer, count > 0, count <= 131072, let text = String(bytes: UnsafeBufferPointer(start: pointer, count: count), encoding: .utf8) else { return 1 }
  return replies.enqueue(context, text) ? 0 : 1
}
@_cdecl("fieldlog_has_reply")
public func fieldlogHasReply(_ context: Int64, _ request: UnsafePointer<UInt8>?, _ count: Int) -> Int32 {
  guard let request, count > 0, count <= 128,
        let id = String(bytes: UnsafeBufferPointer(start: request, count: count), encoding: .utf8) else { return 0 }
  return replies.mailbox.hasReply(context, request: id) ? 1 : 0
}
@_cdecl("fieldlog_poll")
public func fieldlogPoll(_ context: Int64, _ request: UnsafePointer<UInt8>?, _ requestCount: Int,
                        _ output: UnsafeMutablePointer<UInt8>?, _ capacity: Int) -> Int {
  guard let output, capacity >= 0, requestCount >= 0, requestCount <= 128 else { return -1 }
  let id: String
  if requestCount == 0 { id = "" }
  else {
    guard let request, let value = String(bytes: UnsafeBufferPointer(start: request, count: requestCount), encoding: .utf8) else { return -1 }
    id = value
  }
  // The poller only pumps MainActor. JNISurface carries the command's exact
  // context through activation, installation and revocation.
  _ = RunLoop.main.run(mode: .default, before: Date(timeIntervalSinceNow: 0.001))
  let bytes = Array((replies.mailbox.take(context, request: id, capacity: capacity) ?? "").utf8)
  output.update(from: bytes, count: bytes.count)
  return bytes.count
}
