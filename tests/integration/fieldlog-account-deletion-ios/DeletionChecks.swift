import FieldLogModels
@testable import FieldLogStorage
import Foundation

private struct CheckFailure: Error { let context: String; init(_ context: String) { self.context = context } }
private func require(_ condition: Bool, _ context: String) throws {
  if !condition { throw CheckFailure(context) }
}

@MainActor private final class TestSlot: AccountCredentialStore {
  let url: URL
  var rejectWrites = false
  var rejectClear = false

  init(_ url: URL) { self.url = url }

  func read() throws -> AccountCredentialRecord? {
    guard FileManager.default.fileExists(atPath: url.path) else { return nil }
    return try JSONDecoder().decode(AccountCredentialRecord.self, from: Data(contentsOf: url))
  }

  func replace(with record: AccountCredentialRecord?) throws {
    guard !rejectWrites else { throw AccountFailure.refused }
    if let record {
      let bytes = try JSONEncoder().encode(record)
      try require(bytes.count <= FieldLogAccountOwner.byteLimit, "slot size")
      try bytes.write(to: url, options: .atomic)
    } else {
      guard !rejectClear else { throw AccountFailure.refused }
      if FileManager.default.fileExists(atPath: url.path) { try FileManager.default.removeItem(at: url) }
    }
  }
}

private final class Browser: NSObject, URLSessionTaskDelegate {
  func urlSession(
    _ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
    newRequest request: URLRequest, completionHandler: @escaping @Sendable (URLRequest?) -> Void
  ) {
    completionHandler(nil)
  }

  static func send(_ request: URLRequest, port: Int) async throws -> AccountResponse {
    let configuration = URLSessionConfiguration.ephemeral
    configuration.connectionProxyDictionary = ["HTTPEnable": false, "ProxyAutoConfigEnable": false]
    configuration.timeoutIntervalForResource = 5
    let session = URLSession(configuration: configuration, delegate: Browser(), delegateQueue: nil)
    defer { session.invalidateAndCancel() }
    let (bytes, raw) = try await session.bytes(for: request)
    guard let response = raw as? HTTPURLResponse, response.url == request.url,
      response.url?.port == port
    else { throw CheckFailure("fixture response escaped loopback") }
    var body = Data()
    for try await byte in bytes {
      try require(body.count < FieldLogAccountOwner.byteLimit, "fixture response limit")
      body.append(byte)
    }
    return .init(status: response.statusCode, body: body)
  }

  static func request(path: String, port: Int) throws -> URLRequest {
    try require((1...65535).contains(port) && port != 8765, "fixture owns an ephemeral port")
    let origin = URL(string: "http://127.0.0.1:\(port)")!
    var request = URLRequest(url: origin.appending(path: path))
    request.setValue("127.0.0.1:8765", forHTTPHeaderField: "Host")
    return request
  }

  static func exchange(_ operation: AccountRequest, port: Int) async throws -> AccountResponse {
    var request = try request(path: operation.path, port: port)
    request.httpMethod = operation.method.rawValue
    if let bearer = operation.bearer {
      request.setValue("Bearer \(bearer)", forHTTPHeaderField: "Authorization")
    }
    if let body = operation.body {
      request.setValue("application/json", forHTTPHeaderField: "Content-Type")
      request.httpBody = body
    }
    return try await send(request, port: port)
  }

  static func submit(_ form: String, to url: URL, port: Int) async throws -> URL {
    try require(url.absoluteString.hasPrefix(FieldLogAccountOwner.origin.absoluteString + "/v1/"),
      "browser is loopback")
    let configuration = URLSessionConfiguration.ephemeral
    configuration.connectionProxyDictionary = ["HTTPEnable": false, "ProxyAutoConfigEnable": false]
    configuration.timeoutIntervalForResource = 5
    let session = URLSession(configuration: configuration, delegate: Browser(), delegateQueue: nil)
    defer { session.invalidateAndCancel() }
    var request = try request(path: url.path, port: port)
    request.httpMethod = "POST"
    request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
    request.setValue(FieldLogAccountOwner.origin.absoluteString, forHTTPHeaderField: "Origin")
    request.httpBody = Data(form.utf8)
    let (_, raw) = try await session.data(for: request)
    guard let response = raw as? HTTPURLResponse, response.statusCode == 303,
      let location = response.value(forHTTPHeaderField: "Location"), let callback = URL(string: location)
    else { throw CheckFailure("browser approval") }
    return callback
  }
}

private struct Fixture: Decodable {
  let target: AccountDeletionTarget
  let peer: AccountDeletionTarget
  let proof: String
  let peerProof: String
  let recoveryCode: String
  let taskID: UUID
}

private actor HeldRecoveryReply {
  private var releaseReply: CheckedContinuation<Void, Never>?
  private var didHold: CheckedContinuation<Void, Never>?

  func hold() async {
    await withCheckedContinuation { continuation in
      releaseReply = continuation
      didHold?.resume()
      didHold = nil
    }
  }

  func waitUntilHeld() async {
    if releaseReply != nil { return }
    await withCheckedContinuation { didHold = $0 }
  }

  func release() {
    releaseReply?.resume()
    releaseReply = nil
  }
}

@main private struct DeletionChecks {
  @MainActor static func main() async {
    do { try await run() }
    catch let failure as CheckFailure {
      print("FAIL \(failure.context)")
      exit(1)
    } catch {
      print("FAIL unexpected fixture error")
      exit(2)
    }
  }

  @MainActor static func run() async throws {
    let fixture = try JSONDecoder().decode(Fixture.self, from: FileHandle.standardInput.readToEnd() ?? Data())
    let scratch = URL(filePath: CommandLine.arguments[1], directoryHint: .isDirectory)
    let phase = CommandLine.arguments[2]
    let port = Int(CommandLine.arguments[3])!
    let slot = TestSlot(scratch.appending(path: "credentials.json"))
    let manager = FileManager.default
    let scope = fixture.target.scope
    let directory = AccountWorkspaceFiles.directory(for: fixture.target, in: scratch)
    let peer = AccountWorkspaceFiles.directory(for: fixture.peer, in: scratch)
    let ordinary = scratch.appending(path: "ordinary/Workspace.json")
    let adjacent = directory.deletingLastPathComponent().appending(path: UUID().uuidString)
    let savedNames = ["Workspace.json", "Draft.json", "Outbox.json", "Photo.jpg"]
    let saved = Data("disposable synthetic file".utf8)

    let held = HeldRecoveryReply()
    let heldPath: String?
    switch phase {
    case "cancel-held-exchange": heldPath = "/v1/account/recovery/exchange"
    case "cancel-held-confirmation": heldPath = "/v1/account/session"
    default: heldPath = nil
    }
    let peerSlot = TestSlot(scratch.appending(path: "peer-credentials.json"))

    func makeOwner(allowed target: AccountDeletionTarget?, slot credentialSlot: TestSlot? = nil)
      -> FieldLogAccountOwner
    {
      FieldLogAccountOwner(platform: .ios, store: credentialSlot ?? slot,
        exchange: { operation in
          try require(port != 0, "cleanup unexpectedly requires network")
          let result = try await Browser.exchange(operation, port: port)
          if operation.path == heldPath && operation.method != .delete {
            await held.hold()
          }
          if phase == "superseded" && operation.path == "/v1/account/deletion" {
            try await MainActor.run {
              guard let peerRecord = try peerSlot.read() else { throw CheckFailure("peer slot") }
              try slot.replace(with: peerRecord)
            }
          }
          return result
        },
        makeProof: FieldLogAccountApple.makeProof, makeRecoveryCode: FieldLogAccountApple.randomToken,
        deletionTarget: target, makeDeletionKey: FieldLogAccountApple.randomToken)
    }
    let owner = makeOwner(allowed: fixture.target)

    func put(_ file: URL) throws {
      try manager.createDirectory(at: file.deletingLastPathComponent(), withIntermediateDirectories: true)
      try saved.write(to: file)
    }
    func checkFiles() throws {
      for name in savedNames {
        try require(try Data(contentsOf: directory.appending(path: name)) == saved, "unconfirmed file changed")
      }
    }
    func destroy(_ target: AccountDeletionTarget) throws {
      try require(target == fixture.target, "cleanup authority changed")
      try require(try slot.read() != nil, "cleanup started with empty slot")
      try AccountWorkspaceFiles.removeDeletedWorkspace(for: target, in: scratch)
    }
    func signIn(_ owner: FieldLogAccountOwner, proof: String, accepted: Bool = true) async throws {
      let url = try await owner.beginSignIn()
      let callback = try await Browser.submit("proof=\(proof)", to: url, port: port)
      try require(await owner.acceptCallback(callback) == accepted, "session confirmation")
    }
    func stage() throws {
      try owner.stageDeletion(generation: owner.generation)
      try require(owner.state == .deletionPending && owner.grant(for: scope) == nil, "staging suspends sync")
    }
    func mustNotClear(_ target: AccountDeletionTarget) throws {
      fatalError("cleanup called before positive durable receipt")
    }
    func rejectStaging(_ owner: FieldLogAccountOwner, generation: UUID) throws {
      do {
        try owner.stageDeletion(generation: generation)
      } catch AccountFailure.refused { return }
      throw CheckFailure("unauthorized intent was staged")
    }

    switch phase {
    case "normal", "lost", "stage", "superseded":
      let unconfigured = makeOwner(allowed: nil)
      try await signIn(unconfigured, proof: fixture.proof)
      try rejectStaging(unconfigured, generation: unconfigured.generation)
      let wrong = makeOwner(allowed: fixture.peer)
      await wrong.restore()
      try rejectStaging(wrong, generation: wrong.generation)
      await owner.restore()
      try require(owner.grant(for: scope) != nil && owner.canStageDeletion, "preexisting session was restored")
      try rejectStaging(owner, generation: UUID())
      slot.rejectWrites = true
      try rejectStaging(owner, generation: owner.generation)
      try require(owner.grant(for: scope) != nil, "failed stage discarded grant")
      slot.rejectWrites = false
      for name in savedNames { try put(directory.appending(path: name)) }
      try put(ordinary)
      try put(peer.appending(path: "Workspace.json"))
      try put(adjacent.appending(path: "Workspace.json"))
      try manager.createSymbolicLink(at: directory.appending(path: "peer-link"), withDestinationURL: peer)
      if phase == "superseded" {
        let other = makeOwner(allowed: nil, slot: peerSlot)
        try await signIn(other, proof: fixture.peerProof)
      }
      try stage()
      if phase == "stage" { break }
      if phase == "normal" {
        await owner.resumeDeletion(removeWorkspace: destroy)
        try require(owner.state == .welcome && !manager.fileExists(atPath: directory.path), "normal cleanup")
        try require(try slot.read() == nil, "normal slot removal")
      } else {
        await owner.resumeDeletion(removeWorkspace: mustNotClear)
        if phase == "superseded" {
          try require(owner.state == .unavailable, "response failed the durable generation fence")
          let fresh = makeOwner(allowed: fixture.target)
          await fresh.restore()
          try require(fresh.grant(for: fixture.peer.scope) != nil, "new credential preserved")
        } else {
          try require(owner.state == .deletionPending, "lost response remains pending")
        }
        try checkFiles()
      }
    case "mismatch", "retry", "receipt-write":
      await owner.restore()
      try require(owner.state == .deletionPending && owner.grant(for: scope) == nil, "pending restored across launch")
      let unconfigured = makeOwner(allowed: nil)
      await unconfigured.restore()
      await unconfigured.signOut()
      await unconfigured.resumeDeletion(removeWorkspace: mustNotClear)
      try require(unconfigured.state == .unavailable, "pending authorized only for test binding")
      owner.expire(generation: owner.generation)
      await owner.signOut()
      try require(owner.state == .deletionPending, "expiry and sign-out cannot overwrite journal")
      slot.rejectWrites = phase == "receipt-write"
      if phase == "retry" {
        await owner.resumeDeletion { target in
          try require(target == fixture.target, "retry target")
          try manager.removeItem(at: directory.appending(path: "Draft.json"))
          throw CheckFailure("simulated partial housekeeping")
        }
        try require(owner.state == .deletionCleanup, "cleanup remains after interruption")
        try require(!manager.fileExists(atPath: directory.appending(path: "Draft.json").path), "partial cleanup ran")
        try require(manager.fileExists(atPath: directory.appending(path: "Photo.jpg").path), "partial cleanup interrupted")
      } else {
        await owner.resumeDeletion(removeWorkspace: mustNotClear)
        try require(owner.state == .deletionPending, "unconfirmed outcome remains pending")
        try checkFiles()
      }
    case "cleanup", "clear":
      await owner.restore()
      try require(owner.state == .deletionCleanup, "durable positive receipt restored without network")
      if phase == "cleanup" {
        let accountPath = directory.deletingLastPathComponent().deletingLastPathComponent()
        let moved = scratch.appending(path: "parked-target")
        try manager.moveItem(at: accountPath, to: moved)
        try manager.createSymbolicLink(at: accountPath, withDestinationURL: peer)
        await owner.resumeDeletion(removeWorkspace: destroy)
        try require(owner.state == .deletionCleanup, "symbolic link must block cleanup")
        try require(try Data(contentsOf: peer.appending(path: "Workspace.json")) == saved, "link traversed peer")
        try manager.removeItem(at: accountPath)
        try manager.moveItem(at: moved, to: accountPath)
      }
      slot.rejectClear = phase == "cleanup"
      await owner.resumeDeletion(removeWorkspace: destroy)
      try require(!manager.fileExists(atPath: directory.path), "cleanup removed scoped directory")
      try require(owner.state == (slot.rejectClear ? .deletionCleanup : .welcome), "cleanup slot state")
      try require((try slot.read() == nil) == !slot.rejectClear, "cleanup checkpoint")
    case "reauthorize", "reauthorize-callback-first":
      await owner.restore()
      await owner.resumeDeletion(removeWorkspace: mustNotClear)
      try require(owner.state == .deletionSignInRequired, "expired bearer needs renewed sign-in")
      try checkFiles()
      let restarted = makeOwner(allowed: fixture.target)
      await restarted.restore()
      try require(restarted.state == .deletionSignInRequired, "restart preserves reauthorization")
      try await signIn(restarted, proof: fixture.peerProof, accepted: false)
      try require(restarted.state == .deletionSignInRequired, "peer cannot reauthorize")
      let url = try await restarted.beginSignIn()
      let callback = try await Browser.submit("proof=\(fixture.proof)", to: url, port: port)
      let stagedJournal = try Data(contentsOf: slot.url)
      let wrongOwner = makeOwner(allowed: fixture.peer)
      try require(!(await wrongOwner.acceptCallback(callback)), "wrong owner cannot consume stored callback")
      var wrongState = URLComponents(url: callback, resolvingAgainstBaseURL: false)!
      wrongState.queryItems = wrongState.queryItems?.map { item in
        item.name == "state" ? URLQueryItem(name: "state", value: String(repeating: "X", count: 43)) : item
      }
      let wrongStateOwner = makeOwner(allowed: fixture.target)
      try require(!(await wrongStateOwner.acceptCallback(wrongState.url!)), "wrong state cannot consume stored callback")
      try require(try Data(contentsOf: slot.url) == stagedJournal, "invalid callback changed deletion intent")
      let callbackOwner = makeOwner(allowed: fixture.target)
      if phase == "reauthorize" { await callbackOwner.restore() }
      let accepted = await callbackOwner.acceptCallback(callback)
      try require(accepted, "first delivery failed in \(phase), owner state \(callbackOwner.state)")
      try require(callbackOwner.state == .deletionReady && callbackOwner.grant(for: scope) == nil,
        "fresh session requires renewed explicit confirmation")
      let confirmedJournal = try Data(contentsOf: slot.url)
      if phase == "reauthorize-callback-first" {
        await callbackOwner.restore()
        try require(callbackOwner.state == .deletionReady && callbackOwner.grant(for: scope) == nil,
          "startup restore preserves the locked reauthorized session")
        try require(try Data(contentsOf: slot.url) == confirmedJournal, "startup restore changed deletion intent")
      }
      let replayOwner = makeOwner(allowed: fixture.target)
      try require(!(await replayOwner.acceptCallback(callback)), "duplicate callback cannot be consumed")
      try require(try Data(contentsOf: slot.url) == confirmedJournal, "duplicate callback changed deletion intent")
      try checkFiles()
      let confirmOwner = makeOwner(allowed: fixture.target)
      await confirmOwner.restore()
      try require(confirmOwner.state == .deletionReady, "fresh session restores for confirmation")
      try confirmOwner.stageDeletion(generation: confirmOwner.generation)
      await confirmOwner.resumeDeletion(removeWorkspace: destroy)
      try require(confirmOwner.state == .welcome && !manager.fileExists(atPath: directory.path), "renewed deletion")
    case "cancel-held-exchange", "cancel-held-confirmation":
      let url = try await owner.beginRecovery()
      let callback = try await Browser.submit("recoveryCode=\(fixture.recoveryCode)&intent=recover",
        to: url, port: port)
      let callbackFile = scratch.appending(path: "callback.txt")
      try Data(callback.absoluteString.utf8).write(to: callbackFile, options: .atomic)
      let request = Task { await owner.acceptCallback(callback) }
      await held.waitUntilHeld()
      owner.lockForSignOut()
      let locked = owner.state == .signOutPending && owner.grant(for: scope) == nil
      if phase == "cancel-held-exchange" { await owner.signOut() }
      let duplicateAccepted = await owner.acceptCallback(callback)
      await held.release()
      let lateAccepted = await request.value
      try require(locked && !duplicateAccepted && !lateAccepted && owner.grant(for: scope) == nil,
        "cancellation fences both held reply and duplicate callback")
      if phase == "cancel-held-exchange" {
        try require(owner.state == .welcome && owner.replacementSignInCodeForUser()?.count == 43,
          "cancelled exchange preserves an unacknowledged replacement")
      } else {
        try require(owner.state == .signOutPending && owner.replacementSignInCodeForUser() == nil,
          "cold revocation remains locked until restore")
      }
      print("PASS \(phase)")
      return
    case "restore-cancelled":
      let text = try String(contentsOf: scratch.appending(path: "callback.txt"), encoding: .utf8)
      guard let callback = URL(string: text) else { throw CheckFailure("stored callback") }
      await owner.restore()
      try require(owner.state == .welcome && owner.grant(for: scope) == nil,
        "fresh process restores only the welcome route")
      try require(await !owner.acceptCallback(callback), "fresh process refuses redelivery")
      guard let replacement = owner.replacementSignInCodeForUser() else {
        throw CheckFailure("fresh process reveals the saved replacement")
      }
      _ = try await owner.beginSignIn()
      owner.cancelBrowserFlow()
      try require(owner.state == .welcome && owner.replacementSignInCodeForUser() == replacement,
        "Apple Start over retains the replacement")
      try await signIn(owner, proof: replacement)
      try require(owner.grant(for: scope) != nil && !owner.hasReplacementSignInCode,
        "ordinary sign-in with the replacement clears the local copy")
      owner.lockForSignOut()
      try require(owner.state == .signOutPending && owner.grant(for: scope) == nil,
        "ordinary sign-out locks the admitted workspace")
      await owner.signOut()
      try require(owner.state == .welcome && (try slot.read()) == nil,
        "ordinary sign-out clears the slot")
      print("PASS \(phase)")
      return
    case "save-unacknowledged":
      let url = try await owner.beginRecovery()
      let callback = try await Browser.submit("recoveryCode=\(fixture.recoveryCode)&intent=recover",
        to: url, port: port)
      try require(await owner.acceptCallback(callback) && owner.hasReplacementSignInCode,
        "confirmed recovery stores a session and an unacknowledged code")
      print("PASS \(phase)")
      return
    case "supersede-unacknowledged":
      _ = try await owner.beginSignIn()
      owner.cancelBrowserFlow()
      guard let replacement = owner.replacementSignInCodeForUser() else {
        throw CheckFailure("a superseding browser flow preserves the unacknowledged code")
      }
      try await signIn(owner, proof: replacement)
      try require(owner.grant(for: scope) != nil, "replacement signs in to the same scope")
      await owner.signOut()
      try require(try slot.read() == nil, "sign-out clears the slot after ordinary sign-in")
      print("PASS \(phase)")
      return
    case "regression":
      try await signIn(owner, proof: fixture.proof)
      guard case .admitted(let admission) = owner.state, let grant = owner.grant(for: scope) else {
        throw CheckFailure("ordinary grant")
      }
      let activeDirectory = AccountWorkspace.directory(for: admission, in: scratch)
      let repository = try await AccountWorkspace.open(at: activeDirectory, scope: scope)
      _ = try await repository.transact {
        $0.tasks.append(.init(id: fixture.taskID, projectID: scope.projectID,
          title: "Disposable task", responsible: "Synthetic", position: 0))
      }
      func client(_ grant: AccountSyncGrant) throws -> TaskSyncClient {
        try TaskSyncClient(port: UInt16(port), workspaceID: scope.workspaceID, projectID: scope.projectID,
          token: grant.bearer) { fixturePort, path, bearer, upload in
            var request = try Browser.request(path: path, port: Int(fixturePort))
            request.httpMethod = upload == nil ? "GET" : "POST"
            request.setValue("Bearer \(bearer)", forHTTPHeaderField: "Authorization")
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = upload
            let response = try await Browser.send(request, port: Int(fixturePort))
            return (response.status, response.body)
          }
      }
      let oldSync = try client(grant)
      let synchronized = try await oldSync.synchronize(taskID: fixture.taskID, in: repository)
      try require(synchronized.tasks.contains(where: { $0.id == fixture.taskID }), "ordinary TaskSync")
      owner.lockForSignOut()
      let revocationOwner = makeOwner(allowed: fixture.target)
      await revocationOwner.restore()
      try require(revocationOwner.state == .welcome && revocationOwner.grant(for: scope) == nil,
        "ordinary revocation resumes from stored record")
      do {
        _ = try await oldSync.synchronize(taskID: fixture.taskID, in: repository)
        throw CheckFailure("revoked grant reached TaskSync")
      } catch TaskSyncClient.Failure.rejected(401) {}
      let url = try await revocationOwner.beginRecovery()
      let callback = try await Browser.submit("recoveryCode=\(fixture.recoveryCode)&intent=recover", to: url, port: port)
      let restored = makeOwner(allowed: fixture.target)
      await restored.restore()
      try require(await restored.acceptCallback(callback), "old recovery browser record on restart")
      guard let replacement = restored.replacementSignInCodeForUser() else {
        throw CheckFailure("replacement code")
      }
      let recovered = makeOwner(allowed: fixture.target)
      await recovered.restore()
      try require(recovered.hasReplacementSignInCode, "old recovery session format on restore")
      try recovered.acknowledgeReplacementSignInCode()
      guard let recoveryGrant = recovered.grant(for: scope) else { throw CheckFailure("recovery grant") }
      let recoveredSync = try await client(recoveryGrant).synchronize(taskID: fixture.taskID, in: repository)
      try require(recoveredSync.tasks.contains(where: { $0.id == fixture.taskID }), "TaskSync after recovery")
      await repository.close()
      await recovered.signOut()
      try require(recovered.state == .welcome && (try slot.read()) == nil,
        "sign-out after explicit acknowledgement clears the secure slot")
      let fresh = makeOwner(allowed: fixture.target)
      try await signIn(fresh, proof: replacement)
      try require(fresh.grant(for: scope) != nil, "ordinary sign-in using replacement")
      await fresh.signOut()
      print("PASS \(phase)")
      return
    default:
      throw CheckFailure("unknown phase")
    }
    try require(try Data(contentsOf: ordinary) == saved, "ordinary workspace unchanged")
    try require(try Data(contentsOf: peer.appending(path: "Workspace.json")) == saved, "peer workspace unchanged")
    // The preparation process chose the random sibling name only once.
    let siblings = try manager.contentsOfDirectory(at: directory.deletingLastPathComponent(),
      includingPropertiesForKeys: nil)
    try require(siblings.contains { (try? Data(contentsOf: $0.appending(path: "Workspace.json"))) == saved },
      "same-account other project survived")
    print("PASS \(phase)")
  }
}
