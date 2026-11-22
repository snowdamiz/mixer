import FieldLogModels
import FieldLogStorage
import Foundation

@MainActor private final class TestCredentialStore: AccountCredentialStore {
  let file: URL
  var refuseWrite = false

  init(_ file: URL) { self.file = file }

  func read() throws -> AccountCredentialRecord? {
    guard FileManager.default.fileExists(atPath: file.path) else { return nil }
    return try JSONDecoder().decode(AccountCredentialRecord.self, from: Data(contentsOf: file))
  }

  func replace(with record: AccountCredentialRecord?) throws {
    guard !refuseWrite else { throw AccountFailure.refused }
    if let record {
      let encoded = try JSONEncoder().encode(record)
      try require(encoded.count <= FieldLogAccountOwner.byteLimit, "secure record byte budget")
      try encoded.write(to: file, options: .atomic)
    } else if FileManager.default.fileExists(atPath: file.path) {
      try FileManager.default.removeItem(at: file)
    }
  }
}

private final class BrowserDriver: NSObject, URLSessionTaskDelegate {
  func urlSession(
    _ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
    newRequest request: URLRequest, completionHandler: @escaping @Sendable (URLRequest?) -> Void
  ) {
    completionHandler(nil)
  }

  func submit(_ value: String, to url: URL, recovery: Bool, expecting status: Int = 303) async throws -> URL? {
    let configuration = URLSessionConfiguration.ephemeral
    configuration.timeoutIntervalForResource = 5
    let browser = URLSession(configuration: configuration, delegate: self, delegateQueue: nil)
    defer { browser.invalidateAndCancel() }
    let prefix = recovery ? "/v1/account/recovery/attempts/" : "/v1/auth/attempts/"
    try require(url.absoluteString.hasPrefix(FieldLogAccountOwner.origin.absoluteString + prefix),
      "purpose selects browser path")
    let (form, initial) = try await browser.data(from: url)
    try require((initial as? HTTPURLResponse)?.statusCode == 200, "browser form status")
    let text = String(decoding: form, as: UTF8.self)
    try require(text.contains(recovery ? "name=recoveryCode" : "name=proof") && !text.contains(value),
      "browser form purpose and privacy")
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue(FieldLogAccountOwner.origin.absoluteString, forHTTPHeaderField: "Origin")
    request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
    request.httpBody = Data((recovery ? "recoveryCode=\(value)&intent=recover" : "proof=\(value)").utf8)
    let (_, raw) = try await browser.data(for: request)
    let response = raw as? HTTPURLResponse
    try require(response?.statusCode == status, "browser submission status")
    guard status == 303 else { return nil }
    guard let location = response?.value(forHTTPHeaderField: "Location"), !location.contains(value),
      let callback = URL(string: location)
    else { throw CheckFailure("private callback redirect") }
    return callback
  }
}

private actor Probe {
  private let storage: URL
  private let path: String
  private let drops: Int
  private var firstRequest: AccountRequest?
  private(set) var statuses: [Int] = []
  private(set) var recoveryRequests = 0

  init(storage: URL, path: String, drops: Int) {
    self.storage = storage
    self.path = path
    self.drops = drops
  }

  func exchange(_ request: AccountRequest) async throws -> AccountResponse {
    if request.path == "/v1/account/recovery/exchange" {
      recoveryRequests += 1
      guard let body = request.body,
        let fields = try JSONSerialization.jsonObject(with: body) as? [String: String],
        let proof = fields["newProof"],
        Data(proof.utf8).count == 43,
        fields["state"] != proof, fields["verifier"] != proof,
        try Data(contentsOf: storage).range(of: Data(proof.utf8)) != nil
      else { throw CheckFailure("durable replacement precedes recovery exchange") }
    }
    let response = try await FieldLogAccountApple.exchange(request)
    guard request.path == path, request.method != .delete else { return response }
    if let firstRequest {
      try require(firstRequest.body == request.body && firstRequest.bearer == request.bearer,
        "retries use the exact staged proof or provisional bearer")
    } else {
      firstRequest = request
    }
    statuses.append(response.status)
    if statuses.count <= drops { throw AccountFailure.transportUnavailable }
    return response
  }
}

private struct CheckFailure: Error {
  let context: String
  init(_ context: String) { self.context = context }
}

private func require(_ pass: Bool, _ context: String) throws {
  if !pass { throw CheckFailure(context) }
}

@MainActor private func admission(_ owner: FieldLogAccountOwner) throws -> AccountAdmission {
  guard case .admitted(let admission) = owner.state else { throw CheckFailure("confirmed admission") }
  return admission
}

@main private struct RecoveryChecks {
  @MainActor static func main() async throws {
    let input = try FileHandle.standardInput.readToEnd() ?? Data()
    let fixture = try JSONDecoder().decode(Fixture.self, from: input)
    let root = URL(filePath: CommandLine.arguments[1], directoryHint: .isDirectory)
    let browser = BrowserDriver()
    func owner(
      _ store: TestCredentialStore, exchange: @escaping FieldLogAccountOwner.Exchange = FieldLogAccountApple.exchange
    ) -> FieldLogAccountOwner {
      FieldLogAccountOwner(platform: .ios, store: store, exchange: exchange,
        makeProof: FieldLogAccountApple.makeProof, makeRecoveryCode: FieldLogAccountApple.randomToken)
    }
    func signIn(_ owner: FieldLogAccountOwner, _ proof: String) async throws {
      let url = try await owner.beginSignIn()
      guard let callback = try await browser.submit(proof, to: url, recovery: false) else {
        throw CheckFailure("sign-in callback")
      }
      try require(await owner.acceptCallback(callback), "ordinary callback confirmed")
    }

    let original = owner(TestCredentialStore(root.appending(path: "old.json")))
    try await signIn(original, fixture.oldProof)
    let initial = try admission(original)
    let directory = AccountWorkspace.directory(for: initial, in: root)
    let repository = try await AccountWorkspace.open(at: directory, scope: initial.scope)
    let oldGrant = original.grant(for: initial.scope)!
    let oldSync = try TaskSyncClient(port: 8765, workspaceID: initial.scope.workspaceID,
      projectID: initial.scope.projectID, token: oldGrant.bearer)
    _ = try await repository.transact {
      $0.tasks.append(.init(id: fixture.taskID, projectID: initial.scope.projectID,
        title: "Synced task", responsible: "Field worker", position: 0))
    }
    let synced = try await oldSync.synchronize(taskID: fixture.taskID, in: repository)
    try require(synced.tasks.contains(where: { $0.id == fixture.taskID }), "original TaskSync")
    var edit = EntryDraft(projectID: initial.scope.projectID)
    edit.title = "Saved before recovery"
    let draft = edit
    _ = try await repository.transact {
      try $0.saveDraft(draft)
      $0.restoration.openDraftID = draft.id
      try $0.saveTask(projectID: draft.projectID, title: "Unsent task", responsible: "")
    }
    let jpeg = Data([0xff, 0xd8, 0xff, 0x12, 0x34, 0xff, 0xd9])
    let attachment = try await repository.addPhoto(jpeg: jpeg, to: draft.id).attachments[0]
    let photo = try await repository.photoURL(attachment.id)
    let workspaceFile = directory.appending(path: "workspace.json")
    let snapshot = try await repository.readCommittedSnapshot()
    try require(!snapshot.outbox.isEmpty && snapshot.restoration.openDraftID == draft.id,
      "snapshot includes restored draft and unsent work")
    let before = try Data(contentsOf: workspaceFile)
    await repository.close()
    let legacyFile = root.appending(path: "legacy-workspace.json")
    let legacy = Data("legacy workspace bytes".utf8)
    try legacy.write(to: legacyFile)

    let storage = root.appending(path: "recovery.json")
    let store = TestCredentialStore(storage)
    let loss = Probe(storage: storage, path: "/v1/account/recovery/exchange", drops: 1)
    let starter = owner(store)
    let obsoleteURL = try await starter.beginSignIn()
    let obsoleteCallback = try await browser.submit(fixture.oldProof, to: obsoleteURL, recovery: false)!
    let url = try await starter.beginRecovery()
    try require(starter.state == .waitingForBrowser(url) && !starter.hasReplacementSignInCode,
      "code remains private before an approved callback")
    let callback = try await browser.submit(fixture.recoveryCode, to: url, recovery: true)!
    let cold = owner(store, exchange: loss.exchange)
    let forged = URL(string: callback.absoluteString.replacingOccurrences(of: ".ios:", with: ".android:"))!
    try require(await !cold.acceptCallback(obsoleteCallback), "stale sign-in cannot advance recovery")
    try require(await !cold.acceptCallback(forged), "wrong-platform callback cannot advance recovery")
    store.refuseWrite = true
    try require(await !cold.acceptCallback(callback) && cold.state == .unavailable,
      "storage refusal prevents exchange")
    try require(await loss.recoveryRequests == 0 && cold.grant(for: initial.scope) == nil,
      "storage refusal leaves the operator code usable")
    store.refuseWrite = false
    await cold.restore()
    try require(cold.state == .waitingForBrowser(url), "restore retains the recovery purpose")
    try require(await !cold.acceptCallback(callback) && cold.state == .welcome,
      "lost recovery reply returns to ordinary sign-in")
    try require(await loss.statuses == [200, 401] && cold.grant(for: initial.scope) == nil,
      "commit followed by a spent callback cannot admit")
    try require(await !cold.acceptCallback(callback), "spent callback cannot start another exchange")

    let restarted = owner(TestCredentialStore(storage))
    await restarted.restore()
    guard let replacement = restarted.replacementSignInCodeForUser() else {
      throw CheckFailure("replacement survives owner restart")
    }
    let oldCodeURL = try await restarted.beginSignIn()
    _ = try await browser.submit(fixture.oldProof, to: oldCodeURL, recovery: false, expecting: 401)
    restarted.cancelBrowserFlow()
    try require(restarted.replacementSignInCodeForUser() == replacement,
      "cancelling ordinary sign-in keeps the replacement")
    try await signIn(restarted, replacement)
    let reinstated = try admission(restarted)
    try require(reinstated.accountID == initial.accountID && reinstated.scope == initial.scope
      && reinstated.online && !restarted.hasReplacementSignInCode
      && restarted.grant(for: initial.scope) != nil, "ordinary sign-in restores the exact account and scope")
    let readback = try await AccountWorkspace.open(at: directory, scope: reinstated.scope)
    let restoredSnapshot = try await readback.readCommittedSnapshot()
    try require(AccountWorkspace.directory(for: reinstated, in: root) == directory
      && restoredSnapshot == snapshot, "installed repository snapshot matches")
    try require(try Data(contentsOf: workspaceFile) == before && Data(contentsOf: photo) == jpeg
      && Data(contentsOf: legacyFile) == legacy, "workspace, outbox, photo and legacy bytes match")
    do {
      _ = try await oldSync.synchronize(taskID: fixture.taskID, in: readback)
      throw CheckFailure("prior TaskSync bearer still authorized")
    } catch TaskSyncClient.Failure.rejected(401) {}
    let freshSync = try TaskSyncClient(port: 8765, workspaceID: reinstated.scope.workspaceID,
      projectID: reinstated.scope.projectID, token: restarted.grant(for: reinstated.scope)!.bearer)
    _ = try await freshSync.synchronize(taskID: fixture.taskID, in: readback)
    await readback.close()
    await restarted.signOut()

    let nextFile = root.appending(path: "confirmation.json")
    let nextStore = TestCredentialStore(nextFile)
    let confirmation = Probe(storage: nextFile, path: "/v1/account/session", drops: 2)
    let next = owner(nextStore, exchange: confirmation.exchange)
    let nextURL = try await next.beginRecovery()
    let nextCallback = try await browser.submit(fixture.peerRecoveryCode, to: nextURL, recovery: true)!
    try require(await !next.acceptCallback(nextCallback) && next.state == .unavailable
      && next.grant(for: fixture.peerScope) == nil, "lost confirmation replies leave the workspace locked")
    let generation = next.generation
    await next.restore()
    let verified = try admission(next)
    try require(await confirmation.statuses == [200, 200, 200] && next.generation == generation
      && verified.accountID == fixture.peerID && verified.scope == fixture.peerScope
      && verified.expiresAt.timeIntervalSinceNow > 60
      && next.grant(for: initial.scope) == nil, "confirmation retry preserves generation and exact binding")
    let reopened = owner(TestCredentialStore(nextFile))
    await reopened.restore()
    let nextProof = reopened.replacementSignInCodeForUser()
    try require(try admission(reopened) == verified && nextProof != nil,
      "confirmed replacement remains available until acknowledged")
    try reopened.acknowledgeReplacementSignInCode()
    let acknowledged = owner(TestCredentialStore(nextFile))
    await acknowledged.restore()
    try require(try admission(acknowledged) == verified && !acknowledged.hasReplacementSignInCode,
      "acknowledgement removes only the locally retained code")
    await acknowledged.signOut()
    try require(acknowledged.state == .welcome && (try nextStore.read()) == nil,
      "ordinary sign-out removes the confirmed record")
    try await signIn(acknowledged, nextProof!)
    try require(try admission(acknowledged).accountID == fixture.peerID, "replacement signs in after sign-out")
    await acknowledged.signOut()
    print("PASS recovery purpose, staging refusal, lost exchange restart, ordinary sign-in, revocation, lost confirmation, acknowledgement, exact scope, TaskSync and local byte parity")
  }

  private struct Fixture: Decodable {
    let oldProof: String
    let recoveryCode: String
    let peerRecoveryCode: String
    let peerID: UUID
    let peerScope: WorkspaceScope
    let taskID: UUID
  }
}
