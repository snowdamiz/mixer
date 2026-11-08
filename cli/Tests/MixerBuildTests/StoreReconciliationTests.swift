import Darwin
import CryptoKit
import Foundation
import Testing
@testable import MixerBuild

private let dummyToken = "dummy-token-for-offline-test"
private let validOptions = ["--provider": "app-store-connect", "--build-id": "build-1", "--app-id": "12345"]
private func payload(_ state: String = "PROCESSING", build: String = "build-1", app: String = "12345", bundle: String = "com.example.Store", version: String = "42") -> Data {
    Data("""
    {"data":{"type":"builds","id":"\(build)","attributes":{"version":"\(version)","processingState":"\(state)"},"relationships":{"app":{"data":{"type":"apps","id":"\(app)"}}}},"included":[{"type":"apps","id":"\(app)","attributes":{"bundleId":"\(bundle)"}}]}
    """.utf8)
}

private final class Gate: @unchecked Sendable {
    let started = DispatchSemaphore(value: 0)
    let release = DispatchSemaphore(value: 0)
}
private struct Reply: Sendable {
    var body: Data = payload()
    var status: Int = 200
    var headers: [String: String] = ["Content-Type": "application/json"]
    var error: URLError?
    var redirect = false
    var gate: Gate?
}
private final class Script: @unchecked Sendable {
    let lock = NSLock()
    var replies: [Reply] = []
    var trace: [URLRequest] = []
    func set(_ replies: [Reply]) { lock.lock(); defer { lock.unlock() }; self.replies = replies; trace = [] }
    func take(_ request: URLRequest) -> Reply? { lock.lock(); defer { lock.unlock() }; trace.append(request); return replies.isEmpty ? nil : replies.removeFirst() }
    func requests() -> [URLRequest] { lock.lock(); defer { lock.unlock() }; return trace }
}
private final class ScriptedASC: URLProtocol, @unchecked Sendable {
    static let script = Script()
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        guard let reply = Self.script.take(request) else { client?.urlProtocol(self, didFailWithError: URLError(.resourceUnavailable)); return }
        if let gate = reply.gate {
            gate.started.signal()
            DispatchQueue.global().async { [self] in
                guard gate.release.wait(timeout: .now() + 5) == .success else { client?.urlProtocol(self, didFailWithError: URLError(.timedOut)); return }
                respond(reply)
            }
        } else { respond(reply) }
    }
    private func respond(_ reply: Reply) {
        if let error = reply.error { client?.urlProtocol(self, didFailWithError: error); return }
        let response = HTTPURLResponse(url: request.url!, statusCode: reply.status, httpVersion: "HTTP/1.1", headerFields: reply.headers)!
        if reply.redirect {
            client?.urlProtocol(self, wasRedirectedTo: URLRequest(url: URL(string: "https://untrusted.invalid/leak")!), redirectResponse: response)
            client?.urlProtocolDidFinishLoading(self)
            return
        }
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        // Separate chunks exercise the production streaming size bound.
        for offset in stride(from: 0, to: reply.body.count, by: 8192) {
            client?.urlProtocol(self, didLoad: reply.body.subdata(in: offset..<min(offset + 8192, reply.body.count)))
        }
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}
private func reader() -> AppStoreConnectBuildStatus {
    let config = URLSessionConfiguration.ephemeral
    config.protocolClasses = [ScriptedASC.self]
    return AppStoreConnectBuildStatus(configuration: config)
}
private func project(_ body: (URL) throws -> Void) throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-store-test-" + UUID().uuidString)
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
    defer { try? FileManager.default.removeItem(at: root) }
    try JSONFile.write(ApplicationConfiguration(name: "Store", application: "com.example.Store"), to: root.appendingPathComponent("mixer.yml"))
    try body(root)
}
private func query(_ root: URL, token: String = dummyToken) throws -> StoreReconciliationReport {
    try StoreReconciliation.status(request: StoreStatusRequest.parse(words: ["submit", "status"], options: validOptions), directory: root, environment: ["MIXER_ASC_BEARER_TOKEN": token], reader: reader())
}
private func record(_ root: URL) throws -> Data {
    let dir = root.appendingPathComponent(".mixer/store")
    let files = try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil).filter { $0.pathExtension == "json" }
    #expect(files.count == 1)
    return try Data(contentsOf: #require(files.first))
}
private func assertReads(_ count: Int) throws {
    let trace = ScriptedASC.script.requests()
    #expect(trace.count == count)
    for r in trace {
        #expect(r.httpMethod == "GET" && r.httpBody == nil && r.httpBodyStream == nil)
        #expect(r.url?.scheme == "https" && r.url?.host == "api.appstoreconnect.apple.com")
        #expect(r.url?.path == "/v1/builds/build-1")
        let url = try #require(r.url)
        let items = try #require(URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems)
        #expect(Dictionary(uniqueKeysWithValues: items.map { ($0.name, $0.value ?? "") }) == ["fields[builds]": "version,processingState,app", "include": "app", "fields[apps]": "bundleId"])
        #expect(r.value(forHTTPHeaderField: "Authorization") == "Bearer " + dummyToken)
        #expect(r.value(forHTTPHeaderField: "Accept") == "application/json")
        #expect(r.timeoutInterval == 30)
    }
}

@Suite(.serialized) struct StoreSubmissionReconciliationTests {
    @Test func referencedLeafAndBranchLossRefusesAndExactRestorationRecovers() throws {
        for branch in [false, true] {
            try project { root in
                let secret = "deleted-history-secret", other = "another-history-secret"
                ScriptedASC.script.set([Reply(status: 401), Reply(status: 401)])
                _ = try query(root, token: secret)
                if branch { _ = try query(root, token: other) }
                let index = try indexPath(root)
                let header = try String(contentsOf: index.appendingPathComponent("roots"), encoding: .utf8).components(separatedBy: "\n")
                let victim = index.appendingPathComponent(branch ? header[secret.utf8.count] + ".node" : fingerprintName(secret))
                let backup = try Data(contentsOf: victim), before = try record(root)
                if branch { #expect(String(decoding: backup, as: UTF8.self).hasPrefix("B\n")) }
                for malformed in [false, true] {
                    if malformed { try Data("broken".utf8).write(to: victim) }
                    else { try FileManager.default.removeItem(at: victim) }
                    ScriptedASC.script.set([Reply(body: payload("VALID", version: secret))])
                    expectStorageError { _ = try query(root) }
                    #expect(try record(root) == before || !String(decoding: try record(root), as: UTF8.self).contains(secret))
                    try backup.write(to: victim)
                    ScriptedASC.script.set([Reply(body: payload("VALID", version: secret))])
                    #expect(try query(root).code == .redactedResponse)
                    #expect(try query(root, token: "").observation == nil)
                }
                print("TREE referenced deletion/malformed branch=\(branch) refused; exact restoration recovers")
            }
        }
    }
    @Test func recognizedCredentialIsRemovedBefore401AndMissingToken() throws {
        for inState in [false, true] {
            try project { root in
                let futureToken = "newly-supplied-offline-token"
                let reflected = "prefix-" + futureToken + "-suffix"
                ScriptedASC.script.set([Reply(body: payload(inState ? reflected : "VALID", version: inState ? "42" : reflected)), Reply(status: 401)])
                let admitted = try query(root)
                #expect(admitted.observationUpdated && admitted.observation != nil)
                #expect(String(decoding: try record(root), as: UTF8.self).contains(futureToken))
                let rejected = try query(root, token: futureToken)
                #expect(rejected.code == .authenticationRejected && rejected.observation == nil && !rejected.observationUpdated)
                #expect(!String(decoding: try record(root), as: UTF8.self).contains(futureToken))
                #expect(!String(decoding: try JSONFile.data(rejected), as: UTF8.self).contains(futureToken))
                let missing = try query(root, token: "")
                #expect(missing.code == .credentialRequired && missing.observation == nil)
                #expect(!String(decoding: try record(root), as: UTF8.self).contains(futureToken))
                #expect(!String(decoding: try JSONFile.data(missing), as: UTF8.self).contains(futureToken))
                let stored = try #require(JSONSerialization.jsonObject(with: record(root)) as? [String: Any])
                let identity = try #require(stored["identity"] as? [String: String])
                #expect(identity == ["buildID": "build-1", "appID": "12345", "bundleID": "com.example.Store"])
                #expect((stored["issued"] as? NSNumber)?.uint64Value == 3)
                #expect(ScriptedASC.script.requests().count == 2)
                let executable = try #require(ProcessInfo.processInfo.environment["MIXER_STORE_TEST_CLI"])
                let cli = try runCLI(executable, ["submit", "status", "--provider", "app-store-connect", "--build-id", "build-1", "--app-id", "12345", "--directory", root.path])
                #expect(cli.0 == 1 && cli.1.contains("store.credential-required") && !cli.1.contains(futureToken))
            }
        }
    }
    @Test func inFlightAndRotatedWritersCannotRestoreRecognizedCredential() throws {
        for inState in [false, true] {
            try project { root in
                let futureToken = "newly-supplied-offline-token", gate = Gate(), done = DispatchSemaphore(value: 0)
                let result = ResultBox()
                let body = payload(inState ? futureToken : "VALID", version: inState ? "42" : futureToken)
                ScriptedASC.script.set([Reply(body: body, gate: gate), Reply(status: 401), Reply(body: body), Reply(body: payload("VALID", version: "43"))])
                DispatchQueue.global().async { result.set(Result { try query(root) }); done.signal() }
                guard gate.started.wait(timeout: .now() + 5) == .success else { gate.release.signal(); Issue.record("Old request did not start"); return }
                defer { gate.release.signal() }
                let rejected = try query(root, token: futureToken)
                #expect(rejected.code == .authenticationRejected && rejected.observation == nil)
                gate.release.signal()
                #expect(done.wait(timeout: .now() + 5) == .success)
                let old = try #require(result.get()).get()
                #expect(old.code == .redactedResponse && !old.observationUpdated && old.observation == nil)
                let rotated = try query(root, token: "third-offline-token")
                #expect(rotated.code == .redactedResponse && rotated.observation == nil)
                let missing = try query(root, token: "")
                for report in [old, rotated, missing] {
                    #expect(!String(decoding: try JSONFile.data(report), as: UTF8.self).contains(futureToken))
                }
                #expect(!String(decoding: try record(root), as: UTF8.self).contains(futureToken))
                let recovered = try query(root, token: "third-offline-token")
                #expect(recovered.observationUpdated && recovered.observation?.version == "43" && recovered.observation?.generation == 5)
                #expect(ScriptedASC.script.requests().count == 4)
            }
        }
    }
    @Test func invalidationRetainsGenerationOrderingAgainstOlderSafeWriter() throws {
        try project { root in
            let futureToken = "newly-supplied-offline-token", gate = Gate(), done = DispatchSemaphore(value: 0)
            let result = ResultBox()
            ScriptedASC.script.set([Reply(body: payload("VALID")), Reply(body: payload("VALID", version: "old-safe"), gate: gate), Reply(body: payload("VALID", version: futureToken)), Reply(status: 401), Reply(body: payload("VALID", version: "new-safe"))])
            _ = try query(root)
            DispatchQueue.global().async { result.set(Result { try query(root) }); done.signal() }
            guard gate.started.wait(timeout: .now() + 5) == .success else { gate.release.signal(); Issue.record("Old request did not start"); return }
            defer { gate.release.signal() }
            #expect(try query(root).observation?.generation == 3)
            #expect(try query(root, token: futureToken).observation == nil)
            gate.release.signal()
            #expect(done.wait(timeout: .now() + 5) == .success)
            let old = try #require(result.get()).get()
            #expect(old.query == "superseded" && !old.observationUpdated && old.observation == nil)
            #expect(try query(root, token: "").observation == nil)
            let recovered = try query(root)
            #expect(recovered.observation?.version == "new-safe" && recovered.observation?.generation == 6)
            #expect(!String(decoding: try record(root), as: UTF8.self).contains(futureToken))
        }
    }
    @Test func rotatedCredentialFailurePreservesSafeObservationBytes() throws {
        try project { root in
            ScriptedASC.script.set([Reply(body: payload("VALID")), Reply(status: 401)])
            _ = try query(root)
            func observationBytes() throws -> Data {
                let stored = try #require(JSONSerialization.jsonObject(with: record(root)) as? [String: Any])
                return try JSONSerialization.data(withJSONObject: #require(stored["observation"]), options: [.sortedKeys])
            }
            let before = try observationBytes()
            let rejected = try query(root, token: "newly-supplied-offline-token")
            #expect(rejected.code == .authenticationRejected && rejected.observation?.version == "42")
            #expect(try observationBytes() == before)
            #expect(try query(root, token: "").observation?.version == "42")
            #expect(try observationBytes() == before)
        }
    }
    private func compact(_ data: Data) -> String {
        data.base64EncodedString().replacingOccurrences(of: "+", with: "-").replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "=", with: "")
    }
    private func jwt(_ index: Int, key: P256.Signing.PrivateKey, team: Bool = false) throws -> String {
        let header = Data(#"{"alg":"ES256","kid":"TESTKEY123","typ":"JWT"}"#.utf8)
        let identity = team ? #""iss":"00000000-0000-0000-0000-000000000000""# : #""sub":"user""#
        let body = Data("{\(identity),\"iat\":\(1794099600 + index),\"exp\":\(1794100800 + index),\"aud\":\"appstoreconnect-v1\"}".utf8)
        let message = compact(header) + "." + compact(body)
        let signature = try key.signature(for: Data(message.utf8))
        #expect(key.publicKey.isValidSignature(signature, for: Data(message.utf8)))
        return message + "." + compact(signature.rawRepresentation)
    }
    private func recordPath(_ root: URL) throws -> URL {
        try #require(FileManager.default.contentsOfDirectory(at: root.appendingPathComponent(".mixer/store"), includingPropertiesForKeys: nil).first { $0.pathExtension == "json" })
    }
    private func indexPath(_ root: URL) throws -> URL {
        URL(fileURLWithPath: try recordPath(root).path + ".credentials", isDirectory: true)
    }
    private func fingerprintName(_ token: String) -> String {
        SourceDigest.sha256(Data(("L\n" + SourceDigest.sha256(Data(token.utf8)) + "\n").utf8)) + ".node"
    }
    private func indexEntries(_ root: URL) throws -> [URL] {
        try FileManager.default.contentsOfDirectory(at: indexPath(root), includingPropertiesForKeys: nil).filter { url in
            guard url.pathExtension == "node" else { return false }
            return try Data(contentsOf: url).starts(with: Data("L\n".utf8))
        }
    }
    private func expectStorageError(_ operation: () throws -> Void) {
        do { try operation(); Issue.record("Expected recoverable credential storage refusal") }
        catch let error as MixerFailure { #expect(error.code == "store.credential-index") }
        catch { Issue.record("Unexpected error type") }
    }
    @Test func credentialHistoryRotationContinuesBeyond32AndRetainsEverySecret() throws {
        try project { root in
            let key = P256.Signing.PrivateKey()
            var tokens: [String] = []
            for i in 0..<40 { tokens.append(try jwt(i, key: key)) }
            tokens += (0..<40).map { "offline-rotation-token-\($0)" }
            #expect(tokens.prefix(40).allSatisfy { $0.utf8.count == 250 })
            #expect(Set(tokens).count == 80)
            for (i, token) in tokens.enumerated() {
                ScriptedASC.script.set([Reply(body: payload(i == 79 ? "VALID" : "PROCESSING", version: "\(i)"))])
                let result = try query(root, token: token)
                try #require(result.observationUpdated && result.observation?.version == "\(i)")
            }
            // The original R2 failure used rejected credentials. They also cannot
            // impose a lifetime quota on later successful observations.
            for i in 0..<40 {
                ScriptedASC.script.set([Reply(status: 401)])
                #expect(try query(root, token: "rejected-rotation-token-\(i)").code == .authenticationRejected)
            }
            let entries = try indexEntries(root)
            #expect(entries.count == 120)
            for old in [tokens[0], tokens[39], tokens[40], tokens[79], "rejected-rotation-token-0"] {
                ScriptedASC.script.set([Reply(body: payload("VALID", version: old))])
                let result = try query(root, token: tokens[1])
                #expect(result.code == .redactedResponse && !result.observationUpdated && result.observation?.version == "79")
            }
            let team = try jwt(90, key: key, team: true)
            #expect(team.utf8.count == 293)
            for token in [tokens[0], tokens[0], team] {
                ScriptedASC.script.set([Reply(body: payload("VALID", version: "continued"))])
                #expect(try query(root, token: token).observationUpdated)
            }
            #expect(try indexEntries(root).count == 120)
            #expect(try query(root, token: "").observation?.version == "continued")
            let data = try record(root)
            #expect(data.count <= 16_384)
            let saved = try #require(JSONSerialization.jsonObject(with: data) as? [String: Any])
            #expect((saved["schema"] as? NSNumber)?.intValue == 2 && saved["redactions"] == nil && saved["redactionsExhausted"] == nil)
            for entry in entries {
                let bytes = try Data(contentsOf: entry)
                #expect(bytes.count <= 128)
                #expect(!tokens.contains { String(decoding: bytes, as: UTF8.self).contains($0) })
            }
            let nodes = try FileManager.default.contentsOfDirectory(at: indexPath(root), includingPropertiesForKeys: nil).filter { $0.pathExtension == "node" }
            #expect(nodes.count < 120 * 16)
            print("TREE rotation successfulDistinct=80 individuallySigned250ByteJWTs=40 rejectedDistinct=40 deduplicatedLeaves=120 totalImmutableNodes=\(nodes.count) progress=true")
        }
    }
    @Test func storageCorruptionUnavailabilityAndWriteFailureRecoverWithoutPoison() throws {
        try project { root in
            ScriptedASC.script.set([Reply(body: payload("VALID"))])
            _ = try query(root)
            let index = try indexPath(root), before = try record(root)
            let header = index.appendingPathComponent("roots"), originalHeader = try Data(contentsOf: header)
            let entry = index.appendingPathComponent(fingerprintName(dummyToken)), originalEntry = try Data(contentsOf: entry)
            ScriptedASC.script.set([])
            for path in [header, entry] {
                let good = try Data(contentsOf: path)
                try Data("partial".utf8).write(to: path)
                expectStorageError { _ = try query(root) }
                #expect(try record(root) == before)
                try good.write(to: path)
            }
            let parked = index.appendingPathExtension("parked")
            try FileManager.default.moveItem(at: index, to: parked)
            expectStorageError { _ = try query(root, token: "") }
            #expect(!FileManager.default.fileExists(atPath: index.path))
            try FileManager.default.moveItem(at: parked, to: index)
            try FileManager.default.setAttributes([.posixPermissions: 0o500], ofItemAtPath: index.path)
            expectStorageError { _ = try query(root, token: "new-storage-failure-token") }
            try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: index.path)
            #expect(try record(root) == before)
            #expect(ScriptedASC.script.requests().isEmpty)
            #expect(try Data(contentsOf: header) == originalHeader)
            #expect(try Data(contentsOf: entry) == originalEntry)
            ScriptedASC.script.set([Reply(body: payload("VALID", version: "recovered"))])
            #expect(try query(root, token: "new-storage-failure-token").observationUpdated)
            #expect(try query(root, token: "").observation?.version == "recovered")
            #expect(try indexEntries(root).allSatisfy { !$0.lastPathComponent.hasPrefix(".") && $0.lastPathComponent != "pending" })
        }
    }
    @Test func indexRejectsSymlinksHardlinksAndCorruptPendingWithoutChangingOutside() throws {
        try project { root in
            ScriptedASC.script.set([Reply(body: payload("VALID"))]); _ = try query(root)
            let index = try indexPath(root), entry = index.appendingPathComponent(fingerprintName(dummyToken))
            let bytes = try Data(contentsOf: entry), outside = root.appendingPathComponent("outside")
            try bytes.write(to: outside)
            try FileManager.default.removeItem(at: entry)
            try FileManager.default.createSymbolicLink(at: entry, withDestinationURL: outside)
            ScriptedASC.script.set([])
            expectStorageError { _ = try query(root) }
            try FileManager.default.removeItem(at: entry)
            try FileManager.default.linkItem(at: outside, to: entry)
            expectStorageError { _ = try query(root) }
            #expect(try Data(contentsOf: outside) == bytes)
            try FileManager.default.removeItem(at: entry); try bytes.write(to: entry)
            let pending = index.appendingPathComponent("pending")
            try Data("partial".utf8).write(to: pending)
            expectStorageError { _ = try query(root, token: "") }
            #expect(ScriptedASC.script.requests().isEmpty)
            try FileManager.default.removeItem(at: pending)
            #expect(try query(root, token: "").observation?.version == "42")
        }
    }
    @Test func interruptedRecognitionReplaysBeforeCredentialFreeOutput() throws {
        for stage in 0..<3 {
            try project { root in
                let future = "journal-recovery-secret"
                ScriptedASC.script.set([Reply(body: payload("VALID", version: future))])
                _ = try query(root)
                let index = try indexPath(root), name = fingerprintName(future)
                let digest = SourceDigest.sha256(Data(future.utf8))
                let pending = reviewPendingData(future)
                try pending.write(to: index.appendingPathComponent("pending"))
                if stage >= 1 { try Data(("L\n" + digest + "\n").utf8).write(to: index.appendingPathComponent(name)) }
                if stage >= 2 {
                    let header = index.appendingPathComponent("roots")
                    var lines = try String(contentsOf: header, encoding: .utf8).components(separatedBy: "\n")
                    lines[future.utf8.count] = String(name.dropLast(5))
                    let body = Data((lines.prefix(257).joined(separator: "\n") + "\n").utf8)
                    try (body + Data((SourceDigest.sha256(body) + "\n").utf8)).write(to: header)
                }
                let report = try query(root, token: "")
                #expect(report.code == .credentialRequired && report.observation == nil)
                #expect(!String(decoding: try record(root), as: UTF8.self).contains(future))
                #expect(!FileManager.default.fileExists(atPath: index.appendingPathComponent("pending").path))
                #expect(try indexEntries(root).count == 2)
                ScriptedASC.script.set([Reply(body: payload("VALID", version: future)), Reply(body: payload("VALID", version: "after-replay"))])
                #expect(try query(root).code == .redactedResponse)
                #expect(try query(root).observation?.version == "after-replay")
            }
        }
    }
    @Test func legacyAndUnsaturatedR2MigrateButExhaustedR2IsExplicitlyRefused() throws {
        for mode in ["r1", "r2", "exhausted"] {
            try project { root in
                let future = String(repeating: "Z", count: 256)
                ScriptedASC.script.set([Reply(body: payload("VALID", version: future))]); _ = try query(root)
                var old = try #require(JSONSerialization.jsonObject(with: record(root)) as? [String: Any])
                old["schema"] = 1
                if mode != "r1" {
                    old["redactions"] = [["bytes": future.utf8.count, "sha256": SourceDigest.sha256(Data(future.utf8))]]
                    old["redactionsExhausted"] = mode == "exhausted"
                }
                try JSONSerialization.data(withJSONObject: old, options: [.sortedKeys]).write(to: recordPath(root))
                try FileManager.default.removeItem(at: indexPath(root))
                let before = try record(root)
                ScriptedASC.script.set([])
                if mode == "exhausted" {
                    do { _ = try query(root, token: ""); Issue.record("Lossy R2 migration admitted") }
                    catch let error as MixerFailure { #expect(error.code == "store.credential-history-incomplete") }
                    #expect(try record(root) == before)
                    #expect(!FileManager.default.fileExists(atPath: try indexPath(root).path))
                } else {
                    if mode == "r1" { ScriptedASC.script.set([Reply(status: 401)]) }
                    #expect(try query(root, token: mode == "r1" ? future : "").observation == nil)
                    #expect(try query(root, token: "").observation == nil)
                    let migrated = try #require(JSONSerialization.jsonObject(with: record(root)) as? [String: Any])
                    #expect((migrated["schema"] as? NSNumber)?.intValue == 2)
                    #expect((migrated["discardedThrough"] as? NSNumber)?.intValue == 1)
                    #expect(try indexEntries(root).count == 1)
                    ScriptedASC.script.set([Reply(body: payload("VALID", version: future))])
                    #expect(try query(root).code == .redactedResponse)
                }
            }
        }
    }
    @Test func concurrentWritersRetainAllGenerationsWithoutDuplicateIndexEntries() throws {
        for _ in 0..<5 {
        try project { root in
            let results = (0..<24).map { _ in ResultBox() }
            ScriptedASC.script.set([])
            DispatchQueue.concurrentPerform(iterations: 24) { i in
                results[i].set(Result { try query(root, token: "invalid offline token \(i % 8)") })
            }
            for result in results {
                do { #expect(try #require(result.get()).get().code == .credentialRequired) }
                catch { print("PREMISE writer failure: \(error)"); Issue.record("writer failed") }
            }
            let stored = try #require(JSONSerialization.jsonObject(with: record(root)) as? [String: Any])
            #expect((stored["issued"] as? NSNumber)?.intValue == 24)
            let entries = try indexEntries(root)
            #expect(entries.count == 8 && Set(entries.map { $0.lastPathComponent }).count == 8)
            #expect(ScriptedASC.script.requests().isEmpty)
            ScriptedASC.script.set([Reply(body: payload("VALID", version: "invalid offline token 0")), Reply(body: payload("VALID", version: "concurrent-progress"))])
            #expect(try query(root).code == .redactedResponse)
            #expect(try query(root).observation?.version == "concurrent-progress")
        }
        }
    }
    @Test func all256CredentialLengthsKeepLookupBoundedByFieldSizes() throws {
        try project { (root: URL) throws -> Void in
            for length in 1...256 {
                ScriptedASC.script.set([Reply(status: 401)])
                #expect(try query(root, token: String(repeating: "~", count: length)).code == .authenticationRejected)
            }
            let version = String(repeating: "X", count: 256), state = String(repeating: "Y", count: 128)
            ScriptedASC.script.set([Reply(body: payload(state, version: version))])
            #expect(try query(root).observationUpdated)
            #expect(try query(root, token: "").observation?.version == version)
            #expect(try indexEntries(root).count == 257)
            #expect(try record(root).count < 16_384)
            let index = try indexPath(root)
            let roots = try String(contentsOf: index.appendingPathComponent("roots"), encoding: .utf8).components(separatedBy: "\n")
            #expect(try Data(contentsOf: index.appendingPathComponent("roots")).count <= 17_000)
            func depth(_ reference: String) throws -> Int {
                let data = try Data(contentsOf: index.appendingPathComponent(reference + ".node"))
                #expect(data.count <= 256 && SourceDigest.sha256(data) == reference)
                let lines = String(decoding: data, as: UTF8.self).components(separatedBy: "\n")
                if lines[0] == "L" { return 1 }
                return 1 + max(try depth(lines[3]), try depth(lines[4]))
            }
            let maximumDepth = try roots[1...256].filter { !$0.isEmpty }.map { try depth($0) }.max() ?? 0
            #expect(maximumDepth <= 257)
            print("TREE allLengths=256 maximumFieldBytes=256+128 maximumObservedDepth=\(maximumDepth) progress=true")
        }
    }
    @Test func heldLockAdmissionIsBoundedAndLeavesObservationUnchanged() throws {
        try project { (root: URL) throws -> Void in
            ScriptedASC.script.set([Reply(body: payload("VALID"))]); _ = try query(root)
            let before = try record(root), path = try recordPath(root).path + ".lock"
            let descriptor = Darwin.open(path, O_RDWR | O_NOFOLLOW | O_CLOEXEC)
            try #require(descriptor >= 0)
            defer { flock(descriptor, LOCK_UN); Darwin.close(descriptor) }
            try #require(flock(descriptor, LOCK_EX | LOCK_NB) == 0)
            ScriptedASC.script.set([])
            let start = DispatchTime.now().uptimeNanoseconds
            do { _ = try query(root); Issue.record("Held identity lock admitted") }
            catch let error as MixerFailure { #expect(error.code == "store.local-record") }
            let elapsed = Double(DispatchTime.now().uptimeNanoseconds - start) / 1_000_000_000
            #expect(elapsed >= 1.9 && elapsed < 5)
            #expect(try record(root) == before)
            #expect(ScriptedASC.script.requests().isEmpty)
            print("TREE heldLock admissionSeconds=\(elapsed) observationUnchanged=true")
        }
    }
    @Test func maximum256BitPathFindsRecognizedLeafAndDetectsLoss() throws {
        try project { (root: URL) throws -> Void in
            let secret = "maximum-path-secret"
            ScriptedASC.script.set([Reply(status: 401)]); _ = try query(root, token: secret)
            let index = try indexPath(root), digest = SourceDigest.sha256(Data(secret.utf8))
            func writeNode(_ body: String) throws -> String {
                let data = Data(body.utf8), reference = SourceDigest.sha256(Data(body.utf8))
                try data.write(to: index.appendingPathComponent(reference + ".node"))
                return reference
            }
            let leaf = try writeNode("L\n\(digest)\n")
            var reference = leaf
            let hex = Array("0123456789abcdef".utf8), target = Array(digest.utf8)
            for position in (0..<256).reversed() {
                var sibling = target
                let value = Int(try #require(hex.firstIndex(of: target[position / 4])))
                let mask = 1 << (3 - position % 4)
                sibling[position / 4] = hex[value ^ mask]
                let other = try writeNode("L\n\(String(decoding: sibling, as: UTF8.self))\n")
                let zero = value & mask == 0
                reference = try writeNode("B\n\(position)\n\(digest)\n\(zero ? reference : other)\n\(zero ? other : reference)\n")
            }
            let rootFile = index.appendingPathComponent("roots")
            var lines = try String(contentsOf: rootFile, encoding: .utf8).components(separatedBy: "\n")
            lines[secret.utf8.count] = reference
            let body = Data((lines.prefix(257).joined(separator: "\n") + "\n").utf8)
            try (body + Data((SourceDigest.sha256(body) + "\n").utf8)).write(to: rootFile)
            ScriptedASC.script.set([Reply(body: payload("VALID", version: secret))])
            #expect(try query(root).code == .redactedResponse)
            let leafFile = index.appendingPathComponent(leaf + ".node"), intact = try Data(contentsOf: leafFile)
            try FileManager.default.removeItem(at: leafFile)
            ScriptedASC.script.set([Reply(body: payload("VALID", version: secret))])
            expectStorageError { _ = try query(root) }
            try intact.write(to: leafFile)
            ScriptedASC.script.set([Reply(body: payload("VALID", version: secret))])
            #expect(try query(root).code == .redactedResponse)
            #expect(try query(root, token: "").observation == nil)
            print("TREE maximumConstructedPathNodes=257 lookupAndMissingLeafRefusal=true")
        }
    }
    @Test func crossProcessCredentialRecognitionFencesOlderWriter() throws {
        try project { root in
            let secret = "synthetic credential with spaces", gate = Gate(), done = DispatchSemaphore(value: 0), result = ResultBox()
            ScriptedASC.script.set([Reply(body: payload("VALID", version: secret), gate: gate)])
            DispatchQueue.global().async { result.set(Result { try query(root) }); done.signal() }
            guard gate.started.wait(timeout: .now() + 5) == .success else { gate.release.signal(); Issue.record("Old request did not start"); return }
            defer { gate.release.signal() }
            let process = Process(), pipe = Pipe()
            process.executableURL = URL(fileURLWithPath: try #require(ProcessInfo.processInfo.environment["MIXER_STORE_TEST_CLI"]))
            process.arguments = ["submit", "status", "--provider", "app-store-connect", "--build-id", "build-1", "--app-id", "12345", "--directory", root.path]
            var environment = ProcessInfo.processInfo.environment
            environment["MIXER_ASC_BEARER_TOKEN"] = secret
            process.environment = environment; process.standardOutput = pipe; process.standardError = pipe
            try process.run()
            let data = pipe.fileHandleForReading.readDataToEndOfFile(); process.waitUntilExit()
            #expect(process.terminationStatus == 1 && String(decoding: data, as: UTF8.self).contains("store.credential-required"))
            gate.release.signal()
            try #require(done.wait(timeout: .now() + 5) == .success)
            let older = try #require(result.get()).get()
            #expect(older.code == .redactedResponse && older.observation == nil)
            #expect(try query(root, token: "").observation == nil)
            #expect(!String(decoding: try record(root), as: UTF8.self).contains(secret))
            print("REVIEW crossProcess childExit=\(process.terminationStatus) oldWriter=\(older.code?.rawValue ?? "nil") noReemission=true")
        }
    }
    @Test func processingStatesAndRepeatedInvocationPreserveVersionWithoutReadiness() throws {
        try project { root in
            ScriptedASC.script.set([Reply(body: payload()), Reply(body: payload("FAILED")), Reply(body: payload("INVALID")), Reply(body: payload("VALID")), Reply(body: payload("NEW_STATE"))])
            for (state, outcome) in [("PROCESSING", "processing-pending"), ("FAILED", "processing-failed"), ("INVALID", "processing-failed"), ("VALID", "processing-succeeded"), ("NEW_STATE", "unresolved")] {
                let result = try query(root)
                #expect(result.status == outcome && result.observation?.processingState == state)
                #expect(result.observation?.version == "42" && result.observationUpdated)
                #expect(result.testFlightReadiness == "unverified" && result.reviewApproval == "unverified" && result.availability == "unverified")
                #expect(!String(decoding: try JSONFile.data(result), as: UTF8.self).contains(dummyToken))
                #expect(!String(decoding: try record(root), as: UTF8.self).contains(dummyToken))
            }
            try assertReads(5)
        }
    }
    @Test func timeoutMalformedAndAuthenticationAfterValidRetainObservation() throws {
        try project { root in
            ScriptedASC.script.set([Reply(body: payload("VALID")), Reply(error: URLError(.timedOut, userInfo: [NSLocalizedDescriptionKey: dummyToken])), Reply(body: Data("{".utf8)), Reply(body: Data(dummyToken.utf8), status: 401), Reply(body: Data(dummyToken.utf8), status: 403)])
            let first = try query(root)
            for code in [StoreQueryFailure.timeout, .malformedResponse, .authenticationRejected, .accessForbidden] {
                let result = try query(root)
                #expect(result.status == "unresolved" && result.code == code && !result.observationUpdated)
                #expect(result.observation?.observedAt == first.observation?.observedAt)
                #expect(result.observation?.processingState == "VALID")
                let bytes = try record(root)
                #expect(!String(decoding: bytes, as: UTF8.self).contains(dummyToken))
                #expect(!String(decoding: try JSONFile.data(result), as: UTF8.self).contains(dummyToken))
            }
            try assertReads(5)
        }
    }
    @Test func identityAndAmbiguousJSONCannotProduceObservation() throws {
        let mismatches = [payload(build: "other"), payload(app: "9999"), payload(bundle: "com.other.App"), payload().replacing(Data("\"version\":\"42\"".utf8), with: Data("\"version\":\"42\",\"version\":\"43\"".utf8)), Data("{bad}".utf8), payload().replacing(Data("\"included\":[".utf8), with: Data("\"included\":null,\"ignored\":[".utf8))]
        for (index, bytes) in mismatches.enumerated() {
            try project { root in
                ScriptedASC.script.set([Reply(body: bytes)])
                let result = try query(root)
                #expect(result.status == "unresolved" && result.observation == nil)
                #expect(result.code == (index < 3 ? .identityMismatch : .malformedResponse))
                try assertReads(1)
            }
        }
    }
    @Test func boundsRedirectsErrorsAndReflectedTokenAreRedacted() throws {
        let cases: [(Reply, StoreQueryFailure)] = [
            (Reply(body: Data(repeating: 65, count: 262_145)), .responseTooLarge),
            (Reply(headers: ["Content-Type": "application/json", "Content-Length": "262145"]), .responseTooLarge),
            (Reply(status: 302, headers: ["Location": "https://untrusted.invalid/"], redirect: true), .redirectRefused),
            (Reply(status: 307), .redirectRefused),
            (Reply(status: 404), .notFound), (Reply(status: 429), .rateLimited), (Reply(status: 500), .providerRejected),
            (Reply(headers: ["Content-Type": "text/html"]), .invalidResponse),
            (Reply(body: payload(version: dummyToken)), .redactedResponse),
            (Reply(error: URLError(.cannotConnectToHost, userInfo: [NSLocalizedDescriptionKey: "Authorization: Bearer " + dummyToken])), .transportFailed)
        ]
        for (reply, code) in cases {
            try project { root in
                ScriptedASC.script.set([reply])
                let result = try query(root)
                #expect(result.code == code && result.observation == nil)
                #expect(!String(decoding: try JSONFile.data(result), as: UTF8.self).contains(dummyToken))
                #expect(!String(decoding: try record(root), as: UTF8.self).contains(dummyToken))
                try assertReads(1)
            }
        }
    }
    @Test func missingOrInvalidCredentialNeverSendsARequest() throws {
        try project { root in
            ScriptedASC.script.set([])
            for token in ["", "x\r\nInjected: yes"] {
                let result = try query(root, token: token)
                #expect(result.code == .credentialRequired && result.observation == nil)
            }
            #expect(ScriptedASC.script.requests().isEmpty)
        }
    }
    @Test func olderConcurrentResponseCannotOverwriteNewerObservation() throws {
        try project { root in
            let gate = Gate(), done = DispatchSemaphore(value: 0)
            let result = ResultBox()
            ScriptedASC.script.set([Reply(body: payload("PROCESSING"), gate: gate), Reply(body: payload("VALID", version: "43"))])
            DispatchQueue.global().async {
                result.set(Result { try query(root) }); done.signal()
            }
            guard gate.started.wait(timeout: .now() + 5) == .success else { gate.release.signal(); Issue.record("Old request did not start"); return }
            let newer = try query(root)
            gate.release.signal()
            #expect(done.wait(timeout: .now() + 5) == .success)
            let older = try #require(result.get()).get()
            #expect(newer.status == "processing-succeeded")
            #expect(older.query == "superseded" && !older.observationUpdated)
            #expect(older.observation?.version == "43")
            let persisted = String(decoding: try record(root), as: UTF8.self)
            #expect(persisted.contains("VALID") && !persisted.contains("PROCESSING"))
            try assertReads(2)
        }
    }
    @Test func localRecordRejectsSymlinkAndRebindsProjectIdentity() throws {
        try project { root in
            let outside = root.appendingPathComponent("outside")
            try FileManager.default.createDirectory(at: outside, withIntermediateDirectories: false)
            try FileManager.default.createSymbolicLink(at: root.appendingPathComponent(".mixer"), withDestinationURL: outside)
            ScriptedASC.script.set([])
            #expect(throws: MixerFailure.self) { try query(root) }
            #expect(ScriptedASC.script.requests().isEmpty)
        }
        try project { root in
            ScriptedASC.script.set([Reply(body: payload("VALID")), Reply(body: payload("VALID"))])
            _ = try query(root)
            try JSONFile.write(ApplicationConfiguration(name: "Store", application: "com.changed.Store"), to: root.appendingPathComponent("mixer.yml"))
            let result = try query(root)
            #expect(result.code == .identityMismatch && result.observation == nil)
            try assertReads(2)
        }
    }
    @Test func argumentAdmissionAndActualCLIRefusals() throws {
        for words in [["submit"], ["submit", "upload"], ["submit", "status", "extra"]] {
            do { _ = try StoreStatusRequest.parse(words: words, options: validOptions); Issue.record("Unexpected admission") }
            catch let error as MixerFailure { #expect(error.code == "workflow.not-qualified") }
        }
        for options in [[:], ["--provider": "play"], validOptions.merging(["--build-id": "../escape"]) { _, new in new }, validOptions.merging(["--output": "x"]) { _, new in new }] {
            #expect(throws: MixerFailure.self) { try StoreStatusRequest.parse(words: ["submit", "status"], options: options) }
        }
        let executable = try #require(ProcessInfo.processInfo.environment["MIXER_STORE_TEST_CLI"])
        try project { root in
            for (arguments, code) in [(["submit"], "workflow.not-qualified"), (["submit", "upload"], "workflow.not-qualified"), (["submit", "status"], "arguments.submit-status"), (["submit", "status", "--provider", "app-store-connect", "--build-id", "build-1", "--app-id", "12345", "--build-id", "duplicate"], "arguments.option"), (["config", "validate", "--build-id", "build-1"], "arguments.unused-option")] {
                let result = try runCLI(executable, arguments)
                #expect(result.0 == 1 && result.1.contains(code))
            }
            let args = ["submit", "status", "--provider", "app-store-connect", "--build-id", "build-1", "--app-id", "12345", "--directory", root.path]
            for _ in 0..<2 {
                let result = try runCLI(executable, args)
                #expect(result.0 == 1 && result.1.contains("store.credential-required"))
            }
            let help = try runCLI(executable, ["help"])
            #expect(help.0 == 0 && help.1.contains("mixer submit status"))
        }
    }
}
private final class ResultBox: @unchecked Sendable {
    private let lock = NSLock()
    private var value: Result<StoreReconciliationReport, Error>?
    func set(_ value: Result<StoreReconciliationReport, Error>) { lock.lock(); defer { lock.unlock() }; self.value = value }
    func get() -> Result<StoreReconciliationReport, Error>? { lock.lock(); defer { lock.unlock() }; return value }
}
private func runCLI(_ executable: String, _ arguments: [String]) throws -> (Int32, String) {
    let process = Process(), pipe = Pipe()
    process.executableURL = URL(fileURLWithPath: executable); process.arguments = arguments
    process.environment = ProcessInfo.processInfo.environment.filter { $0.key != "MIXER_ASC_BEARER_TOKEN" }
    process.standardOutput = pipe; process.standardError = pipe
    try process.run()
    let data = pipe.fileHandleForReading.readDataToEndOfFile(); process.waitUntilExit()
    return (process.terminationStatus, String(decoding: data, as: UTF8.self))
}
private extension Data {
    func replacing(_ search: Data, with replacement: Data) -> Data {
        guard let range = range(of: search) else { return self }
        var result = self; result.replaceSubrange(range, with: replacement); return result
    }
}

private let reviewIdentity = StoreObservationFile.Identity(buildID: "build-1", appID: "12345", bundleID: "com.example.Store")
private func reviewProject(_ body: (URL) throws -> Void) throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("independent-store-" + UUID().uuidString)
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
    defer { try? FileManager.default.removeItem(at: root) }
    try JSONFile.write(ApplicationConfiguration(name: "Store", application: reviewIdentity.bundleID), to: root.appendingPathComponent("mixer.yml"))
    try body(root)
}
private func reviewFile(_ root: URL, _ token: String = "") throws -> StoreObservationFile {
    try StoreObservationFile(root: root, identity: reviewIdentity, token: token)
}
private func reviewRecord(_ root: URL) -> URL {
    let key = SourceDigest.sha256(Data((reviewIdentity.bundleID + "\u{0}" + reviewIdentity.appID + "\u{0}" + reviewIdentity.buildID).utf8))
    return root.appendingPathComponent(".mixer/store/" + key + ".json")
}
private func reviewIndex(_ root: URL) -> URL { URL(fileURLWithPath: reviewRecord(root).path + ".credentials", isDirectory: true) }
private func reviewRecognize(_ root: URL, _ token: String) throws {
    let file = try reviewFile(root, token); defer { file.close() }; _ = try file.reserve()
}
private func reviewValue(_ generation: UInt64, _ value: String) -> StoreBuildObservation {
    .init(generation: generation, observedAt: Date(timeIntervalSince1970: 1), providerValue: .init(version: value, processingState: "VALID"))
}
private func reviewReject(_ file: StoreObservationFile, _ value: String) throws {
    let generation = try file.reserve()
    do { _ = try file.commit(reviewValue(generation, value)); Issue.record("Recognized credential admitted") }
    catch let failure as StoreQueryFailure { #expect(failure == .redactedResponse) }
}
private func reviewNode(_ index: URL, _ text: String) throws -> String {
    let bytes = Data(text.utf8), hash = SourceDigest.sha256(Data(text.utf8))
    try bytes.write(to: index.appendingPathComponent(hash + ".node")); return hash
}
private func reviewRoots(_ index: URL, length: Int, reference: String) throws {
    let path = index.appendingPathComponent("roots")
    var lines = try String(contentsOf: path, encoding: .utf8).components(separatedBy: "\n")
    lines[length] = reference
    let body = Data((lines.prefix(257).joined(separator: "\n") + "\n").utf8)
    try (body + Data((SourceDigest.sha256(body) + "\n").utf8)).write(to: path)
}
private func reviewPendingData(_ token: String) -> Data {
    let hash = SourceDigest.sha256(Data(token.utf8))
    let body = Data("mixer-credential-v2\n\(token.utf8.count)-\(hash)\n".utf8)
    return body + Data((SourceDigest.sha256(body) + "\n").utf8)
}
private func reviewPending(_ index: URL, _ token: String) throws {
    try reviewPendingData(token).write(to: index.appendingPathComponent("pending"))
}

extension StoreSubmissionReconciliationTests {
    @Test func independentSingleBytePendingCorruptionMustNotReemitCredential() throws {
        try reviewProject { root in
            let secret = "pending-integrity-secret"
            let file = try reviewFile(root); defer { file.close() }
            let generation = try file.reserve()
            _ = try file.commit(reviewValue(generation, secret))
            let index = reviewIndex(root)
            try reviewPending(index, secret)
            let pending = index.appendingPathComponent("pending")
            let intact = try Data(contentsOf: pending), priorRecord = try Data(contentsOf: reviewRecord(root))
            let priorRoots = try Data(contentsOf: index.appendingPathComponent("roots"))
            var bytes = Array(intact)
            let prefixCount = "mixer-credential-v2\n\(secret.utf8.count)-".utf8.count
            let original = bytes[prefixCount]
            bytes[prefixCount] = original == 48 ? 49 : 48
            try Data(bytes).write(to: pending)
            do {
                let observation = try file.observation()
                let leaked = observation?.version == secret
                let journalRemoved = !FileManager.default.fileExists(atPath: pending.path)
                print("INDEPENDENT pendingSingleHexByteCorruption reemitted=\(leaked) journalRemoved=\(journalRemoved)")
                #expect(!leaked, "A one-byte corrupt pending fingerprint must not permit old credential output")
                Issue.record("Corrupt pending fingerprint was accepted instead of refusing")
            } catch let failure as MixerFailure {
                #expect(failure.code == "store.credential-index")
            }
            #expect(try Data(contentsOf: pending) == Data(bytes))
            #expect(try Data(contentsOf: reviewRecord(root)) == priorRecord)
            #expect(try Data(contentsOf: index.appendingPathComponent("roots")) == priorRoots)
            try intact.write(to: pending)
            #expect(try file.observation() == nil)
            #expect(!FileManager.default.fileExists(atPath: pending.path))
            try reviewReject(file, secret)
            print("INDEPENDENT pendingSingleHexByteCorruption refused=true journalPreserved=true exactRecovery=true")
        }
    }

    @Test func independentMembershipMatchesDirectSetAcrossInsertionOrders() throws {
        let tokens = (0..<48).map { "review-" + String(SourceDigest.sha256(Data("credential-\($0)".utf8)).prefix(24)) }
        let orders = [Array(0..<48), Array((0..<48).reversed()), (0..<48).map { ($0 * 17) % 48 }]
        for order in orders {
            try reviewProject { root in
                let reader = try reviewFile(root); defer { reader.close() }
                for i in order { try reviewRecognize(root, tokens[i]) }
                for i in order.prefix(8) { try reviewRecognize(root, tokens[i]) }
                let values = tokens.map { "α[" + $0 + "]ω" } + (0..<48).map { "review-" + String(SourceDigest.sha256(Data("absent-\($0)".utf8)).prefix(24)) }
                var rejected = 0, accepted = 0
                for value in values {
                    let expected = tokens.contains { value.contains($0) }
                    let generation = try reader.reserve()
                    do {
                        let result = try reader.commit(reviewValue(generation, value))
                        #expect(!expected && result.1 && result.0?.version == value); accepted += 1
                    } catch let failure as StoreQueryFailure {
                        #expect(expected && failure == .redactedResponse); rejected += 1
                    }
                }
                #expect(rejected == 48 && accepted == 48)
            }
        }
        print("INDEPENDENT directSet orders=3 recognized=144 negative=144 duplicates=24 staleReaderReread=true")
    }

    @Test func independentBranchingJournalReplayPreservesTombstone() throws {
        for stage in 0..<3 {
            try reviewProject { root in
                let prior = (0..<12).map { String(format: "journal-secret-%04d", $0) }
                let future = "journal-secret-9999"
                for token in prior { try reviewRecognize(root, token) }
                let old = try reviewFile(root); defer { old.close() }
                let staleGeneration = try old.reserve()
                let newer = try old.reserve()
                _ = try old.commit(reviewValue(newer, future))
                let index = reviewIndex(root), record = reviewRecord(root)
                let beforeRecord = try Data(contentsOf: record), beforeRoots = try Data(contentsOf: index.appendingPathComponent("roots"))
                let beforeNames = Set(try FileManager.default.contentsOfDirectory(atPath: index.path))
                try reviewRecognize(root, future)
                try beforeRecord.write(to: record)
                if stage < 2 { try beforeRoots.write(to: index.appendingPathComponent("roots")) }
                if stage == 0 {
                    for name in try FileManager.default.contentsOfDirectory(atPath: index.path) where !beforeNames.contains(name) {
                        try FileManager.default.removeItem(at: index.appendingPathComponent(name))
                    }
                }
                try reviewPending(index, future)
                let reopened = try reviewFile(root); defer { reopened.close() }
                #expect(try reopened.observation() == nil)
                #expect(!FileManager.default.fileExists(atPath: index.appendingPathComponent("pending").path))
                let stale = try old.commit(reviewValue(staleGeneration, "older-safe-value"))
                #expect(!stale.1 && stale.0 == nil)
                for secret in prior + [future] { try reviewReject(reopened, secret) }
                let generation = try reopened.reserve()
                #expect(try reopened.commit(reviewValue(generation, "replay-progress")).1)
                let final = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: record)) as? [String: Any])
                #expect((final["discardedThrough"] as? NSNumber)?.uint64Value == newer)
            }
        }
        print("INDEPENDENT nonemptyTreeReplay stages=3 retainedMembers=39 staleGenerationFenced=3")
    }

    @Test func independentFullR2MigrationResumesPartialIndexAndMaxGeneration() throws {
        try reviewProject { root in
            let tokens = (0..<16).map { String(format: "migration-secret-%04d", $0) }
            for token in tokens.prefix(8) { try reviewRecognize(root, token) }
            let file = try reviewFile(root); defer { file.close() }
            let generation = try file.reserve()
            _ = try file.commit(reviewValue(generation, tokens[15]))
            let path = reviewRecord(root)
            var record = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: path)) as? [String: Any])
            record["schema"] = 1
            record["redactions"] = tokens.map { ["bytes": $0.utf8.count, "sha256": SourceDigest.sha256(Data($0.utf8))] as [String: Any] }
            record["redactionsExhausted"] = false
            try JSONSerialization.data(withJSONObject: record, options: [.sortedKeys]).write(to: path)
            try reviewPending(reviewIndex(root), tokens[8])
            #expect(try file.observation() == nil)
            for secret in tokens { try reviewReject(file, secret) }
            try reviewRecognize(root, "migration-secret-0017")
            let future = "max-generation-secret"
            let fresh = try file.reserve(); _ = try file.commit(reviewValue(fresh, future))
            record = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: path)) as? [String: Any])
            record["issued"] = NSNumber(value: UInt64.max)
            try JSONSerialization.data(withJSONObject: record, options: [.sortedKeys]).write(to: path)
            let exhausted = try reviewFile(root, future); defer { exhausted.close() }
            do { _ = try exhausted.reserve(); Issue.record("Generation overflow admitted") }
            catch let failure as MixerFailure { #expect(failure.code == "store.local-record") }
            #expect(try file.observation() == nil)
            let final = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: path)) as? [String: Any])
            #expect((final["discardedThrough"] as? NSNumber)?.uint64Value == fresh)
        }
        print("INDEPENDENT R2migration full16 partial8 pendingReplay=true rotation17=true overflowSanitizes=true")
    }

    @Test func independentHashConsistentMalformedEdgesRefuse() throws {
        try reviewProject { root in
            let token = "edge-validation-secret", hash = SourceDigest.sha256(Data(token.utf8))
            try reviewRecognize(root, token)
            let file = try reviewFile(root); defer { file.close() }
            let index = reviewIndex(root), roots = index.appendingPathComponent("roots"), original = try Data(contentsOf: roots)
            let hex = Array("0123456789abcdef")
            let first = try #require(hex.firstIndex(of: hash.first!))
            let opposite = String(hex[first ^ 8]) + hash.dropFirst()
            let leaf = try reviewNode(index, "L\n\(hash)\n")
            let wrong = try reviewNode(index, "L\n\(opposite)\n")
            for mode in 0..<3 {
                let bit = mode == 2 ? 4 : 0
                let nibble = try #require(hex.firstIndex(of: Array(hash)[bit / 4]))
                let direction = (nibble >> (3 - bit % 4)) & 1
                let bad = mode == 1 ? try reviewNode(index, "B\n0\n\(hash)\n\(leaf)\n\(wrong)\n") : wrong
                let rootRef = try reviewNode(index, "B\n\(bit)\n\(hash)\n\(direction == 0 ? bad : leaf)\n\(direction == 1 ? bad : leaf)\n")
                try reviewRoots(index, length: token.utf8.count, reference: rootRef)
                let generation = try file.reserve()
                do { _ = try file.commit(reviewValue(generation, token)); Issue.record("Malformed consulted edge admitted") }
                catch let failure as MixerFailure { #expect(failure.code == "store.credential-index") }
                try original.write(to: roots)
                try reviewReject(file, token)
            }
        }
        print("INDEPENDENT hashConsistentBadEdges wrongDirection=1 nonIncreasingBit=1 wrongPrefix=1 exactRecovery=3")
    }

    @Test func independentConcurrentCLIConstructorsRetainEveryGeneration() throws {
        let executable = try #require(ProcessInfo.processInfo.environment["MIXER_STORE_TEST_CLI"])
        for _ in 0..<2 {
            try reviewProject { root in
                let results = (0..<24).map { _ in ReviewCLIResult() }
                DispatchQueue.concurrentPerform(iterations: 24) { i in
                    results[i].result = Result {
                        let process = Process(), pipe = Pipe()
                        process.executableURL = URL(fileURLWithPath: executable)
                        process.arguments = ["submit", "status", "--provider", "app-store-connect", "--build-id", "build-1", "--app-id", "12345", "--directory", root.path]
                        var environment = ProcessInfo.processInfo.environment
                        environment["MIXER_ASC_BEARER_TOKEN"] = "invalid process credential \(i)"
                        process.environment = environment; process.standardOutput = pipe; process.standardError = pipe
                        try process.run()
                        let data = pipe.fileHandleForReading.readDataToEndOfFile(); process.waitUntilExit()
                        return (process.terminationStatus, String(decoding: data, as: UTF8.self))
                    }
                }
                for box in results {
                    let result = try #require(box.result).get()
                    #expect(result.0 == 1 && result.1.contains("store.credential-required"))
                }
                let record = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: reviewRecord(root))) as? [String: Any])
                #expect((record["issued"] as? NSNumber)?.intValue == 24)
                let reader = try reviewFile(root); defer { reader.close() }
                for i in 0..<24 { try reviewReject(reader, "invalid process credential \(i)") }
            }
        }
        print("INDEPENDENT concurrentRealCLI rounds=2 processes=48 issued=48 retainedCredentials=48")
    }
}
private final class ReviewCLIResult: @unchecked Sendable {
    var result: Result<(Int32, String), Error>?
}

private func reviewIndexSnapshot(_ index: URL) throws -> [String: Data] {
    var snapshot: [String: Data] = [:]
    for name in try FileManager.default.contentsOfDirectory(atPath: index.path) {
        snapshot[name] = try Data(contentsOf: index.appendingPathComponent(name))
    }
    return snapshot
}

extension StoreSubmissionReconciliationTests {
    @Test func pendingIntegrityRefusesEveryDamagedLayoutAndRestoresExactly() throws {
        for stage in 0..<3 {
            try reviewProject { root in
                let prior = (0..<12).map { String(format: "integrity-prior-%04d", $0) }
                let secret = "pending-integrity-secret"
                for token in prior { try reviewRecognize(root, token) }
                let old = try reviewFile(root); defer { old.close() }
                let stale = try old.reserve(), retained = try old.reserve()
                _ = try old.commit(reviewValue(retained, secret))
                let index = reviewIndex(root), record = reviewRecord(root)
                let priorRecord = try Data(contentsOf: record)
                let before = try reviewIndexSnapshot(index)
                try reviewRecognize(root, secret)
                try priorRecord.write(to: record)
                if stage < 2 { try #require(before["roots"]).write(to: index.appendingPathComponent("roots")) }
                if stage == 0 {
                    for name in try FileManager.default.contentsOfDirectory(atPath: index.path) where before[name] == nil {
                        try FileManager.default.removeItem(at: index.appendingPathComponent(name))
                    }
                }
                let pending = index.appendingPathComponent("pending"), intact = reviewPendingData(secret)
                let headerCount = "mixer-credential-v2\n".utf8.count
                let fingerprintStart = headerCount + String(secret.utf8.count).utf8.count + 1
                let checksumStart = fingerprintStart + 65
                var changes: [(String, Data)] = []
                for (name, offset) in [("fingerprint", fingerprintStart), ("length", headerCount + 1), ("checksum", checksumStart), ("framing", headerCount - 2)] {
                    var bytes = Array(intact)
                    bytes[offset] = bytes[offset] == 48 ? 49 : 48
                    #expect(zip(bytes, intact).filter { $0.0 != $0.1 }.count == 1)
                    changes.append((name, Data(bytes)))
                }
                var malformed = Array(intact); malformed[checksumStart] = 122
                changes.append(("malformed-checksum", Data(malformed)))
                changes.append(("trailing", intact + Data([10])))
                changes.append(("truncated", Data(intact.dropLast())))
                changes.append(("oversize", intact + Data(repeating: 48, count: 155 - intact.count)))
                let unchecked = Data("mixer-credential-v1\n\(secret.utf8.count)-\(SourceDigest.sha256(Data(secret.utf8)))\n".utf8)
                changes.append(("unchecked-v1", unchecked))
                var uncheckedCorrupt = Array(unchecked)
                uncheckedCorrupt[fingerprintStart] = uncheckedCorrupt[fingerprintStart] == 48 ? 49 : 48
                changes.append(("unchecked-v1-corrupt", Data(uncheckedCorrupt)))
                for (name, corrupt) in changes {
                    try corrupt.write(to: pending)
                    let snapshot = try reviewIndexSnapshot(index)
                    let reopened = try reviewFile(root); defer { reopened.close() }
                    for operation in 0..<3 {
                        do {
                            switch operation {
                            case 0: _ = try reopened.observation()
                            case 1: _ = try reopened.reserve()
                            default: _ = try reopened.commit(reviewValue(stale, "older-safe-value"))
                            }
                            Issue.record("Damaged journal admitted: \(name), stage \(stage), operation \(operation)")
                        } catch let failure as MixerFailure {
                            #expect(failure.code == "store.credential-index")
                            #expect(!String(describing: failure).contains(secret))
                        }
                        #expect(try Data(contentsOf: record) == priorRecord)
                        #expect(try reviewIndexSnapshot(index) == snapshot)
                        #expect(!String(decoding: corrupt, as: UTF8.self).contains(secret))
                    }
                }
                try intact.write(to: pending)
                let restored = try reviewFile(root); defer { restored.close() }
                #expect(try restored.observation() == nil)
                #expect(!FileManager.default.fileExists(atPath: pending.path))
                #expect(!String(decoding: try Data(contentsOf: record), as: UTF8.self).contains(secret))
                let result = try old.commit(reviewValue(stale, "older-safe-value"))
                #expect(!result.1 && result.0 == nil)
                for token in prior + [secret] { try reviewReject(restored, token) }
                let final = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: record)) as? [String: Any])
                #expect((final["discardedThrough"] as? NSNumber)?.uint64Value == retained)
            }
        }
        print("JOURNAL integrity stages=3 variants=10 operations=90 unchangedOnRefusal=true exactReplayAndFence=3")
    }

    @Test func checkedPendingMaximumAndCanonicalEncoding() throws {
        for length in [1, 99, 100, 256] {
            try reviewProject { root in
                let secret = String(repeating: "q", count: length)
                let file = try reviewFile(root); defer { file.close() }
                let generation = try file.reserve()
                _ = try file.commit(reviewValue(generation, secret))
                let index = reviewIndex(root), pending = index.appendingPathComponent("pending")
                let intact = reviewPendingData(secret)
                #expect(intact.count <= 154)
                if length == 256 { #expect(intact.count == 154) }
                try intact.write(to: pending)
                #expect(try file.observation() == nil)
                #expect(!FileManager.default.fileExists(atPath: pending.path))
                try reviewReject(file, secret)
            }
        }
        try reviewProject { root in
            let file = try reviewFile(root); defer { file.close() }; _ = try file.reserve()
            let index = reviewIndex(root), pending = index.appendingPathComponent("pending")
            let hash = SourceDigest.sha256(Data("x".utf8))
            for body in ["mixer-credential-v2\n01-\(hash)\n", "mixer-credential-v2\n0-\(hash)\n", "mixer-credential-v2\n257-\(hash)\n", "mixer-credential-v3\n1-\(hash)\n", "mixer-credential-v2\n1-\(hash.uppercased())\n"] {
                let data = Data(body.utf8)
                let checked = data + Data((SourceDigest.sha256(data) + "\n").utf8)
                try checked.write(to: pending)
                let record = try Data(contentsOf: reviewRecord(root)), snapshot = try reviewIndexSnapshot(index)
                do { _ = try file.observation(); Issue.record("Noncanonical checked journal admitted") }
                catch let failure as MixerFailure { #expect(failure.code == "store.credential-index") }
                #expect(try Data(contentsOf: reviewRecord(root)) == record)
                #expect(try reviewIndexSnapshot(index) == snapshot)
            }
        }
        print("JOURNAL maximumBytes=154 boundaryLengths=1,99,100,256 noncanonicalCheckedRefusals=5")
    }
}
