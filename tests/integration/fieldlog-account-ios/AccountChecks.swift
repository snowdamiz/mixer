import FieldLogModels
import FieldLogStorage
import Foundation

@MainActor private final class MemoryStore: AccountCredentialStore {
  private var encoded: Data?
  func read() throws -> AccountCredentialRecord? {
    try encoded.map { try JSONDecoder().decode(AccountCredentialRecord.self, from: $0) }
  }
  func replace(with record: AccountCredentialRecord?) throws {
    encoded = try record.map { try JSONEncoder().encode($0) }
  }
}

private final class BrowserDriver: NSObject, URLSessionTaskDelegate {
  func urlSession(
    _ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
    newRequest request: URLRequest, completionHandler: @escaping @Sendable (URLRequest?) -> Void
  ) {
    completionHandler(nil)
  }

  func submit(_ proof: String, to url: URL) async throws -> URL {
    let configuration = URLSessionConfiguration.ephemeral
    configuration.timeoutIntervalForResource = 5
    let browser = URLSession(configuration: configuration, delegate: self, delegateQueue: nil)
    defer { browser.invalidateAndCancel() }
    let (form, initial) = try await browser.data(from: url)
    try require((initial as? HTTPURLResponse)?.statusCode == 200, "browser form status")
    try require(String(decoding: form, as: UTF8.self).contains("name=proof"), "browser form")
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue(FieldLogAccountOwner.origin.absoluteString, forHTTPHeaderField: "Origin")
    request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
    request.httpBody = Data("proof=\(proof)".utf8)
    let (_, raw) = try await browser.data(for: request)
    guard let response = raw as? HTTPURLResponse, response.statusCode == 303,
      let location = response.value(forHTTPHeaderField: "Location"), let callback = URL(string: location)
    else { throw CheckFailure("browser redirect") }
    return callback
  }
}

private actor ExchangeGate {
  private let path: String
  private var held: CheckedContinuation<Void, Never>?
  private var waiting: CheckedContinuation<AccountRequest, Never>?
  private var request: AccountRequest?

  init(path: String = "/v1/auth/exchange") { self.path = path }

  func exchange(_ request: AccountRequest) async throws -> AccountResponse {
    let response = try await FieldLogAccountApple.exchange(request)
    if request.path == path && self.request == nil {
      await withCheckedContinuation { continuation in
        self.request = request
        held = continuation
        waiting?.resume(returning: request)
        waiting = nil
      }
    }
    return response
  }

  func awaitHeldResponse() async -> AccountRequest {
    if let request { return request }
    return await withCheckedContinuation { waiting = $0 }
  }

  func release() {
    held?.resume()
    held = nil
  }
}

private actor ResponseLoss {
  private let path: String
  private let drops: Int
  private(set) var attempts: [AccountRequest] = []
  private(set) var responses: [AccountResponse] = []

  init(path: String, drops: Int) {
    self.path = path
    self.drops = drops
  }

  func exchange(_ request: AccountRequest) async throws -> AccountResponse {
    let response = try await FieldLogAccountApple.exchange(request)
    if request.path == path && request.method != .delete {
      attempts.append(request)
      responses.append(response)
      if attempts.count <= drops { throw AccountFailure.transportUnavailable }
    }
    return response
  }
}

private func sessionStatus(_ method: String, bearer: String) async throws -> Int {
  var request = URLRequest(url: FieldLogAccountOwner.origin.appending(path: "v1/account/session"))
  request.httpMethod = method
  request.setValue("Bearer " + bearer, forHTTPHeaderField: "Authorization")
  let configuration = URLSessionConfiguration.ephemeral
  configuration.timeoutIntervalForResource = 5
  let session = URLSession(configuration: configuration)
  defer { session.invalidateAndCancel() }
  let (_, response) = try await session.data(for: request)
  return (response as? HTTPURLResponse)?.statusCode ?? 0
}

private struct CheckFailure: Error {
  let context: String
  init(_ context: String) { self.context = context }
}

private func require(_ pass: Bool, _ context: String) throws {
  if !pass { throw CheckFailure(context) }
}

@MainActor private func admission(_ owner: FieldLogAccountOwner) throws -> AccountAdmission {
  guard case .admitted(let admission) = owner.state else { throw CheckFailure("admission") }
  return admission
}

@main private struct AccountChecks {
  @MainActor static func main() async throws {
    let input = try FileHandle.standardInput.readToEnd() ?? Data()
    let proofs = try JSONDecoder().decode([String].self, from: input)
    let root = URL(filePath: CommandLine.arguments[1], directoryHint: .isDirectory)
    let store = MemoryStore()
    let browser = BrowserDriver()
    func owner(
      exchange: @escaping FieldLogAccountOwner.Exchange = FieldLogAccountApple.exchange,
      now: @escaping @MainActor () -> Date = { Date() }
    ) -> FieldLogAccountOwner {
      FieldLogAccountOwner(platform: .ios, store: store, exchange: exchange,
        makeProof: FieldLogAccountApple.makeProof, now: now)
    }
    func begin(_ owner: FieldLogAccountOwner, proof: String) async throws -> URL {
      try await browser.submit(proof, to: owner.beginSignIn())
    }

    let first = owner()
    let canceledURL = try await first.beginSignIn()
    let canceled = try await browser.submit(proofs[0], to: canceledURL)
    first.cancelBrowserFlow()
    let freshURL = try await first.beginSignIn()
    try require(await !first.acceptCallback(canceled), "superseded callback")
    let callback = try await browser.submit(proofs[0], to: freshURL)
    let cold = owner()
    let forged = URL(string: callback.absoluteString + "&state=duplicate")!
    try require(await !cold.acceptCallback(forged), "duplicate callback field")
    try require(await cold.acceptCallback(callback), "cold callback exchange")
    try require(await !cold.acceptCallback(callback), "duplicate callback delivery")
    let initial = try admission(cold)
    try require(initial.expiresAt.timeIntervalSinceNow > 60, "uses confirmed expiry")

    let directory = AccountWorkspace.directory(for: initial, in: root)
    let legacy = root.appending(path: "FieldLog")
    try FileManager.default.createDirectory(at: legacy, withIntermediateDirectories: true)
    let legacyFile = legacy.appending(path: "workspace.json")
    let legacyBytes = Data("unclaimed legacy sentinel".utf8)
    try legacyBytes.write(to: legacyFile)
    let repository = try await AccountWorkspace.open(at: directory, scope: initial.scope)
    var edit = EntryDraft(projectID: initial.scope.projectID)
    edit.title = "Saved before account retirement"
    edit.note = "Preserve the exact photo, draft and queued task."
    let draft = edit
    let taskID = UUID(uuidString: proofs[2])!
    _ = try await repository.transact {
      $0.tasks.append(.init(id: taskID, projectID: draft.projectID, title: "Synced task",
        responsible: "Field worker", position: 0))
      try $0.saveDraft(draft)
      $0.restoration.openDraftID = draft.id
    }
    let jpeg = Data([0xff, 0xd8, 0xff, 0x12, 0x34, 0xff, 0xd9])
    let withPhoto = try await repository.addPhoto(jpeg: jpeg, to: draft.id)
    let photo = try await repository.photoURL(withPhoto.attachments[0].id)
    let grant = cold.grant(for: initial.scope)!
    let sync = try TaskSyncClient(port: 8765, workspaceID: initial.scope.workspaceID,
      projectID: initial.scope.projectID, token: grant.bearer)
    let synced = try await sync.synchronize(taskID: taskID, in: repository)
    try require(synced.tasks.contains(where: { $0.id == taskID }), "ordinary TaskSync")
    _ = try await repository.transact {
      try $0.saveTask(projectID: draft.projectID, title: "Unsent task", responsible: "")
    }
    let path = directory.appending(path: "workspace.json")
    let before = try Data(contentsOf: path)
    let persisted = try await repository.readCommittedSnapshot()
    try require(!persisted.outbox.isEmpty && persisted.restoration.openDraftID == draft.id,
      "draft restoration and pending changes")
    await repository.close()

    let restored = owner()
    await restored.restore()
    try require(try admission(restored) == initial, "verified restore binding")
    let offline = owner(exchange: { _ in throw AccountFailure.transportUnavailable })
    await offline.restore()
    try require(try !admission(offline).online && offline.grant(for: initial.scope) == nil,
      "offline restoration does not release bearer")
    await restored.signOut()
    try require(restored.state == .welcome && (try store.read()) == nil, "sign-out clears credential")
    let old = owner(exchange: { request in
      try await FieldLogAccountApple.exchange(request)
    })
    await old.restore()
    try require(old.state == .welcome, "signed-out restore")
    let readback = try await AccountWorkspace.open(at: directory, scope: initial.scope)
    do {
      _ = try await sync.synchronize(taskID: taskID, in: readback)
      throw CheckFailure("old task bearer accepted")
    } catch TaskSyncClient.Failure.rejected(401) {}
    await readback.close()

    let otherURL = try await restored.beginSignIn()
    try require(await restored.acceptCallback(try await browser.submit(proofs[1], to: otherURL)), "peer sign-in")
    let otherAdmission = try admission(restored)
    let other = AccountWorkspace.directory(for: otherAdmission, in: root)
    try require(other != directory, "isolated account root")
    let peer = try await AccountWorkspace.open(at: other, scope: otherAdmission.scope)
    let peerSnapshot = try await peer.readCommittedSnapshot()
    try require(peerSnapshot.drafts.isEmpty && peerSnapshot.attachments.isEmpty, "peer account does not see draft")
    await peer.close()
    await restored.signOut()

    let signInAgain = try await restored.beginSignIn()
    try require(await restored.acceptCallback(try await browser.submit(proofs[0], to: signInAgain)),
      "original account signs in again")
    let same = AccountWorkspace.directory(for: try admission(restored), in: root)
    try require(same == directory, "same account directory")
    let reopening = try await AccountWorkspace.open(at: same, scope: initial.scope)
    try require(try await reopening.readCommittedSnapshot() == persisted, "reopened snapshot matches")
    await reopening.close()
    try require(try Data(contentsOf: path) == before && Data(contentsOf: photo) == jpeg
      && Data(contentsOf: legacyFile) == legacyBytes, "snapshot, JPEG and legacy byte parity")
    let expired = owner(now: { Date().addingTimeInterval(32_400) })
    await expired.restore()
    try require(expired.state == .expired && expired.grant(for: initial.scope) == nil, "expired local restore")
    try require(try Data(contentsOf: path) == before, "expiry preserves workspace bytes")

    let gate = ExchangeGate()
    let race = owner(exchange: gate.exchange)
    let raceURL = try await race.beginSignIn()
    let late = try await browser.submit(proofs[0], to: raceURL)
    let task = Task { await race.acceptCallback(late) }
    _ = await gate.awaitHeldResponse()
    await race.signOut()
    await gate.release()
    try require(await task.value == false && race.state == .welcome && (try store.read()) == nil,
      "held successful exchange cannot resurrect a signed-out principal")

    let confirmationGate = ExchangeGate(path: "/v1/account/session")
    let confirming = owner(exchange: confirmationGate.exchange)
    let confirmationCallback = try await begin(confirming, proof: proofs[0])
    let held = Task { await confirming.acceptCallback(confirmationCallback) }
    let provisionalRequest = await confirmationGate.awaitHeldResponse()
    let provisionalBearer = provisionalRequest.bearer!
    try require(provisionalRequest.method == .get && provisionalRequest.body == nil,
      "confirmation is an authenticated GET with no body")
    try require(confirming.state == .working && (try store.read()) == nil
      && confirming.grant(for: initial.scope) == nil, "held confirmation cannot persist or admit")
    try require(await !confirming.acceptCallback(confirmationCallback), "duplicate while confirming")
    await confirming.signOut()
    try require(try await sessionStatus("GET", bearer: provisionalBearer) == 401,
      "sign-out revokes a grant whose confirmation response is held")
    let replacement = try await begin(confirming, proof: proofs[1])
    try require(await confirming.acceptCallback(replacement), "new account before held response releases")
    let replacementGrant = confirming.grant(for: otherAdmission.scope)
    await confirmationGate.release()
    try require(await !held.value && confirming.grant(for: otherAdmission.scope)?.bearer == replacementGrant?.bearer
      && (try admission(confirming)).accountID == otherAdmission.accountID, "held confirmation cannot replace newer admission")
    let replacementRestore = owner()
    await replacementRestore.restore()
    try require(try admission(replacementRestore) == admission(confirming), "held confirmation cannot replace newer stored record")
    await confirming.signOut()

    let beforeConfirmation = owner(exchange: { request in
      if request.method == .get, let bearer = request.bearer {
        let repository = try await AccountWorkspace.open(at: directory, scope: initial.scope)
        let client = try TaskSyncClient(port: 8765, workspaceID: initial.scope.workspaceID,
          projectID: initial.scope.projectID, token: bearer)
        do {
          _ = try await client.synchronize(taskID: taskID, in: repository)
          await repository.close()
          throw CheckFailure("TaskSync authorized a provisional bearer")
        } catch TaskSyncClient.Failure.rejected(401) {
          await repository.close()
        }
      }
      return try await FieldLogAccountApple.exchange(request)
    })
    let beforeConfirmationCallback = try await begin(beforeConfirmation, proof: proofs[0])
    try require(await beforeConfirmation.acceptCallback(beforeConfirmationCallback),
      "backend rejects TaskSync with the provisional bearer before the confirmation GET")
    await beforeConfirmation.signOut()

    for field in ["accountID", "scopes", "token", "bearer", "expiresAt"] {
      let mismatched = owner(exchange: { request in
        let response = try await FieldLogAccountApple.exchange(request)
        guard request.method == .get else { return response }
        var value = try JSONSerialization.jsonObject(with: response.body) as! [String: Any]
        switch field {
        case "accountID": value[field] = UUID().uuidString.lowercased()
        case "scopes":
          value[field] = [["workspaceID": initial.scope.workspaceID.uuidString.lowercased(),
            "projectID": UUID().uuidString.lowercased()]]
        case "expiresAt": value[field] = Int64(Date().timeIntervalSince1970) + 1
        default: value[field] = NSNull()
        }
        return .init(status: 200, body: try JSONSerialization.data(withJSONObject: value))
      })
      let callback = try await begin(mismatched, proof: proofs[0])
      try require(await !mismatched.acceptCallback(callback), "rejects confirmation field \(field)")
      try require(mismatched.state == .unavailable && (try store.read()) == nil
        && mismatched.grant(for: initial.scope) == nil, "invalid confirmation cannot admit")
    }

    let denied = owner(exchange: { request in
      if request.method == .get, let bearer = request.bearer {
        try require(try await sessionStatus("DELETE", bearer: bearer) == 200, "revoke before GET")
      }
      return try await FieldLogAccountApple.exchange(request)
    })
    let deniedCallback = try await begin(denied, proof: proofs[0])
    try require(await !denied.acceptCallback(deniedCallback) && denied.state == .expired,
      "confirmation 401 requires a new browser sign-in")
    try require(await !denied.acceptCallback(deniedCallback) && (try store.read()) == nil,
      "confirmation 401 clears the attempt")

    let loss = ResponseLoss(path: "/v1/account/session", drops: 2)
    let recovering = owner(exchange: loss.exchange)
    let recoveryCallback = try await begin(recovering, proof: proofs[0])
    try require(await !recovering.acceptCallback(recoveryCallback) && recovering.state == .unavailable
      && (try store.read()) == nil && recovering.grant(for: initial.scope) == nil,
      "lost confirmation replies cannot persist or admit")
    let retryGeneration = recovering.generation
    await recovering.restore()
    let retried = await loss.attempts
    let replies = await loss.responses
    try require(recovering.generation == retryGeneration && retried.count == 3
      && retried[0].bearer != nil && retried.allSatisfy { $0.bearer == retried[0].bearer },
      "confirmation retry uses the same bearer and generation")
    try require(replies.allSatisfy { $0.status == 200 && $0.body == replies[0].body },
      "real confirmation replay keeps the exact expiry")
    let recovered = try admission(recovering)
    let fields = try JSONSerialization.jsonObject(with: replies[0].body) as! [String: Any]
    let confirmedExpiry = try JSONDecoder().decode(Int64.self,
      from: JSONSerialization.data(withJSONObject: fields["expiresAt"]!, options: [.fragmentsAllowed]))
    try require(recovered.expiresAt == Date(timeIntervalSince1970: TimeInterval(confirmedExpiry)),
      "admission uses the exact real GET expiry")
    let disk = owner()
    await disk.restore()
    try require(try admission(disk) == recovered, "the confirmed expiry survives a new owner")
    await recovering.signOut()

    let lostExchange = ResponseLoss(path: "/v1/auth/exchange", drops: 1)
    let reentering = owner(exchange: lostExchange.exchange)
    let consumed = try await begin(reentering, proof: proofs[0])
    try require(await !reentering.acceptCallback(consumed) && reentering.state == .welcome,
      "lost exchange returns to the ordinary sign-in action")
    try require(await !reentering.acceptCallback(consumed) && (try store.read()) == nil,
      "lost exchange does not retry a consumed callback")
    let freshlyIssued = try await begin(reentering, proof: proofs[0])
    try require(await !reentering.acceptCallback(consumed), "stale callback cannot consume the fresh attempt")
    try require(await reentering.acceptCallback(freshlyIssued)
      && (try admission(reentering)).accountID == initial.accountID, "fresh browser sign-in after exchange loss")
    let exchanges = await lostExchange.attempts
    try require(exchanges.count == 2 && exchanges[0].body != exchanges[1].body,
      "re-entry issues one new exchange with fresh proof")
    await reentering.signOut()
    let oversize = owner(exchange: { _ in .init(status: 201, body: Data(repeating: 0, count: 1025)) })
    do {
      _ = try await oversize.beginSignIn()
      throw CheckFailure("oversized response accepted")
    } catch AccountFailure.invalidResponse {}
    print("PASS real confirmation and TaskSync, held exchange/confirmation, identity/scope/bearer/expiry rejection, confirmation 401, lost GET replay, lost exchange re-entry, restore/sign-out, isolation, draft/photo/outbox byte parity, 1 KiB cap")
  }
}
