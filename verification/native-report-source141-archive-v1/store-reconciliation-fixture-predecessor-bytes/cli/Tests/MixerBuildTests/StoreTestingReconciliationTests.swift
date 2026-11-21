import Darwin
import Foundation
import Testing
@testable import MixerBuild

private let testingToken = "offline-testing-token"
private let testingOptions = ["--provider": "app-store-connect", "--build-id": "build-1", "--app-id": "12345"]
private func testingPayload(internalState: Any = "READY_FOR_BETA_TESTING", externalState: Any = "IN_BETA_TESTING", processing: String = "VALID", expired: Any = false) throws -> Data {
    try JSONSerialization.data(withJSONObject: [
        "data": ["type": "builds", "id": "build-1", "attributes": ["version": "42", "processingState": processing, "expired": expired], "relationships": ["app": ["data": ["type": "apps", "id": "12345"]], "buildBetaDetail": ["data": ["type": "buildBetaDetails", "id": "beta-1"]]]],
        "included": [["type": "apps", "id": "12345", "attributes": ["bundleId": "com.example.Store"]], ["type": "buildBetaDetails", "id": "beta-1", "attributes": ["internalBuildState": internalState, "externalBuildState": externalState], "relationships": ["build": ["data": ["type": "builds", "id": "build-1"]]]]]
    ])
}
private struct TestingReply: Sendable { var body: Data; var status = 200; var mime = "application/json"; var error: URLError?; var gate: TestingGate?; var length: Int? }
private final class TestingGate: @unchecked Sendable { let started = DispatchSemaphore(value: 0); let release = DispatchSemaphore(value: 0) }
private final class TestingScript: @unchecked Sendable {
    private let lock = NSLock(); private var replies: [TestingReply] = []; private var requests: [URLRequest] = []
    func set(_ replies: [TestingReply]) { lock.lock(); defer { lock.unlock() }; self.replies = replies; requests = [] }
    func take(_ request: URLRequest) -> TestingReply? { lock.lock(); defer { lock.unlock() }; requests.append(request); return replies.isEmpty ? nil : replies.removeFirst() }
    func trace() -> [URLRequest] { lock.lock(); defer { lock.unlock() }; return requests }
}
private final class TestingASC: URLProtocol, @unchecked Sendable {
    static let script = TestingScript()
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        guard let reply = Self.script.take(request) else { client?.urlProtocol(self, didFailWithError: URLError(.resourceUnavailable)); return }
        if let gate = reply.gate { gate.started.signal(); DispatchQueue.global().async { [self] in
            guard gate.release.wait(timeout: .now() + 5) == .success else { client?.urlProtocol(self, didFailWithError: URLError(.timedOut)); return }; respond(reply)
        } } else { respond(reply) }
    }
    private func respond(_ reply: TestingReply) {
        if let error = reply.error { client?.urlProtocol(self, didFailWithError: error); return }
        var headers = ["Content-Type": reply.mime]
        if let length = reply.length { headers["Content-Length"] = String(length) }
        let response = HTTPURLResponse(url: request.url!, statusCode: reply.status, httpVersion: "HTTP/1.1", headerFields: headers)!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        for offset in stride(from: 0, to: reply.body.count, by: 8192) { client?.urlProtocol(self, didLoad: reply.body.subdata(in: offset..<min(offset + 8192, reply.body.count))) }
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}
private func testingReader() -> AppStoreConnectBuildStatus {
    let config = URLSessionConfiguration.ephemeral; config.protocolClasses = [TestingASC.self]; return .init(configuration: config)
}
private func testingProject(_ body: (URL) throws -> Void) throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-testing-" + UUID().uuidString)
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
    defer { try? FileManager.default.removeItem(at: root) }
    try JSONFile.write(ApplicationConfiguration(name: "Store", application: "com.example.Store"), to: root.appendingPathComponent("mixer.yml")); try body(root)
}
private func testingQuery(_ root: URL, token: String = testingToken) throws -> StoreTestingReconciliationReport {
    try StoreReconciliation.testingStatus(request: .parse(words: ["submit", "testing-status"], options: testingOptions), directory: root, environment: ["MIXER_ASC_BEARER_TOKEN": token], reader: testingReader())
}
private func processingQuery(_ root: URL, token: String = "") throws -> StoreReconciliationReport {
    try StoreReconciliation.status(request: .parse(words: ["submit", "status"], options: testingOptions), directory: root, environment: ["MIXER_ASC_BEARER_TOKEN": token], reader: testingReader())
}
private func testingRecord(_ root: URL) throws -> URL {
    try #require(FileManager.default.contentsOfDirectory(at: root.appendingPathComponent(".mixer/store"), includingPropertiesForKeys: nil).first { $0.pathExtension == "json" })
}
private func mutatePayload(_ body: Data, _ change: (inout [String: Any]) -> Void) throws -> Data {
    var object = try #require(JSONSerialization.jsonObject(with: body) as? [String: Any]); change(&object); return try JSONSerialization.data(withJSONObject: object)
}
private func processingPayload() throws -> Data {
    try mutatePayload(testingPayload()) { object in object["included"] = [(object["included"] as! [[String: Any]])[0]] }
}
private final class TestingResult: @unchecked Sendable {
    private let lock = NSLock(); private var value: Result<StoreTestingReconciliationReport, Error>?
    func set(_ value: Result<StoreTestingReconciliationReport, Error>) { lock.lock(); defer { lock.unlock() }; self.value = value }
    func get() -> Result<StoreTestingReconciliationReport, Error>? { lock.lock(); defer { lock.unlock() }; return value }
}

@Suite(.serialized) struct StoreTestingReconciliationTests {
    @Test func exactSparseReadAndSeparateProviderReadiness() throws {
        try testingProject { root in
            TestingASC.script.set([.init(body: try testingPayload())]); let result = try testingQuery(root)
            #expect(result.internalReadiness == "ready-for-testing" && result.externalReadiness == "in-testing" && result.exitCode == 0)
            #expect(result.testLinks == "unverified" && result.appStoreReviewApproval == "unverified" && result.releasedAvailability == "unverified")
            let trace = TestingASC.script.trace(); #expect(trace.count == 1); let request = try #require(trace.first)
            #expect(request.httpMethod == "GET" && request.httpBody == nil && request.httpBodyStream == nil)
            #expect(request.url?.absoluteString == "https://api.appstoreconnect.apple.com/v1/builds/build-1?fields%5Bbuilds%5D=version,processingState,expired,app,buildBetaDetail&include=app,buildBetaDetail&fields%5Bapps%5D=bundleId&fields%5BbuildBetaDetails%5D=internalBuildState,externalBuildState,build")
            #expect(request.value(forHTTPHeaderField: "Authorization") == "Bearer " + testingToken && request.value(forHTTPHeaderField: "Accept") == "application/json" && request.timeoutInterval == 30)
            #expect(result.reconciliation.observation?.providerValue.testing?.externalBuildState == "IN_BETA_TESTING")
        }
    }
    @Test func officialInternalAndExternalStatesAreConservativelyMapped() throws {
        let internalStates = ["PROCESSING", "PROCESSING_EXCEPTION", "MISSING_EXPORT_COMPLIANCE", "READY_FOR_BETA_TESTING", "IN_BETA_TESTING", "EXPIRED", "IN_EXPORT_COMPLIANCE_REVIEW"]
        let externalStates = internalStates + ["READY_FOR_BETA_SUBMISSION", "WAITING_FOR_BETA_REVIEW", "IN_BETA_REVIEW", "BETA_REJECTED", "BETA_APPROVED", "NOT_APPLICABLE"]
        try testingProject { root in
            for external in [false, true] {
                for state in external ? externalStates : internalStates {
                    TestingASC.script.set([.init(body: try testingPayload(internalState: external ? (state == "BETA_APPROVED" ? "READY_FOR_BETA_TESTING" : "MISSING_EXPORT_COMPLIANCE") : state, externalState: external ? state : "READY_FOR_BETA_SUBMISSION", expired: state == "EXPIRED"))])
                    let result = try testingQuery(root), readiness = external ? result.externalReadiness : result.internalReadiness
                    let expected = state == "EXPIRED" ? "expired" : state == "IN_BETA_TESTING" ? "in-testing" : state == "READY_FOR_BETA_TESTING" ? "ready-for-testing" : "not-ready"
                    #expect(readiness == expected)
                    if state == "BETA_APPROVED" { #expect(result.nextStep.contains("Beta review approval alone") && result.appStoreReviewApproval == "unverified") }
                }
            }
        }
    }
    @Test func missingNullUnknownAndProcessingOnlyCannotInventReadiness() throws {
        try testingProject { root in
            let base = try testingPayload()
            var bodies = [try testingPayload(internalState: NSNull(), externalState: NSNull()), try testingPayload(internalState: "FUTURE_STATE", externalState: "FUTURE_STATE"), try testingPayload(expired: NSNull())]
            bodies.append(try mutatePayload(base) { o in var i = o["included"] as! [[String: Any]]; i[1].removeValue(forKey: "attributes"); o["included"] = i })
            bodies.append(try mutatePayload(base) { o in var i = o["included"] as! [[String: Any]]; i[1]["attributes"] = [:]; o["included"] = i })
            for null in [false, true] { bodies.append(try mutatePayload(base) { o in var d = o["data"] as! [String: Any]; var r = d["relationships"] as! [String: Any]; if null { r["buildBetaDetail"] = ["data": NSNull()] } else { r.removeValue(forKey: "buildBetaDetail") }; d["relationships"] = r; o["data"] = d; o["included"] = [(o["included"] as! [[String: Any]])[0]] }) }
            for body in bodies { TestingASC.script.set([.init(body: body)]); let r = try testingQuery(root); #expect(r.reconciliation.query == "observed" && r.internalReadiness == "unresolved" && r.externalReadiness == "unresolved") }
            TestingASC.script.set([.init(body: base)]); _ = try testingQuery(root)
            let old = try processingQuery(root); let json = String(decoding: try JSONFile.data(old), as: UTF8.self)
            #expect(old.code == .credentialRequired && old.testFlightReadiness == "unverified" && !json.contains("internalBuildState") && !json.contains("testing"))
            TestingASC.script.set([.init(body: try processingPayload())]); let processing = try processingQuery(root, token: testingToken)
            #expect(processing.status == "processing-succeeded")
            TestingASC.script.set([.init(body: Data(), status: 401)]); let failed = try testingQuery(root)
            #expect(failed.internalReadiness == "unresolved" && failed.reconciliation.observation?.providerValue.testing == nil)
        }
    }
    @Test func expiryAndContradictoryProcessingDenyPositiveClaims() throws {
        try testingProject { root in
            for state in ["PROCESSING", "FAILED", "INVALID", "FUTURE"] {
                TestingASC.script.set([.init(body: try testingPayload(processing: state))]); let r = try testingQuery(root)
                #expect(r.internalReadiness == "contradictory" && r.externalReadiness == "contradictory" && r.exitCode == 1)
            }
            TestingASC.script.set([.init(body: try testingPayload(internalState: "PROCESSING"))]); let crossed = try testingQuery(root)
            #expect(crossed.internalReadiness == "contradictory" && crossed.externalReadiness == "contradictory")
            TestingASC.script.set([.init(body: try testingPayload(expired: true))]); #expect(try testingQuery(root).internalReadiness == "expired")
            TestingASC.script.set([.init(body: try testingPayload(externalState: "EXPIRED"))]); let r = try testingQuery(root)
            #expect(r.internalReadiness == "contradictory" && r.externalReadiness == "contradictory")
        }
    }
    @Test func malformedIdentityAndLinkageRefuseWithoutReplacingPriorObservation() throws {
        try testingProject { root in
            let body = try testingPayload(); TestingASC.script.set([.init(body: body)]); _ = try testingQuery(root)
            let replacements = [("build-1", "other-build"), ("12345", "other-app"), ("com.example.Store", "com.example.Other"), ("beta-1", "other-beta")]
            var invalid: [Data] = []
            for (needle, replacement) in replacements { let text = String(decoding: body, as: UTF8.self); if let range = text.range(of: needle) { var changed = text; changed.replaceSubrange(range, with: replacement); invalid.append(Data(changed.utf8)) } }
            for mode in 0..<6 { invalid.append(try mutatePayload(body) { o in
                var included = o["included"] as! [[String: Any]]
                switch mode {
                case 0: included.append(included[1])
                case 1: included.append(included[0])
                case 2: included[1].removeValue(forKey: "relationships")
                case 3: included[1]["relationships"] = ["build": ["data": ["type": "builds", "id": "wrong"]]]
                case 4: var d = o["data"] as! [String: Any]; var rel = d["relationships"] as! [String: Any]; rel["buildBetaDetail"] = ["data": NSNull()]; d["relationships"] = rel; o["data"] = d
                default: included[1]["id"] = ""
                }; o["included"] = included
            }) }
            for body in invalid { TestingASC.script.set([.init(body: body)]); let r = try testingQuery(root); #expect(r.reconciliation.code == .identityMismatch && !r.reconciliation.observationUpdated && r.observationFreshness == "retained-previous-observation" && r.internalReadiness == "unresolved") }
        }
    }
    @Test func httpRefusalsRetainOldTimestampWithoutFreshSuccess() throws {
        try testingProject { root in
            TestingASC.script.set([.init(body: try testingPayload())]); let first = try testingQuery(root)
            let states: [(Int, StoreQueryFailure)] = [(301, .redirectRefused), (401, .authenticationRejected), (403, .accessForbidden), (404, .notFound), (429, .rateLimited), (500, .providerRejected)]
            for (status, code) in states { TestingASC.script.set([.init(body: Data(), status: status)]); let r = try testingQuery(root); #expect(r.reconciliation.code == code && r.internalReadiness == "unresolved" && r.externalReadiness == "unresolved" && r.observationFreshness == "retained-previous-observation" && r.reconciliation.observation?.observedAt == first.reconciliation.observation?.observedAt) }
            TestingASC.script.set([.init(body: Data(), error: URLError(.timedOut))]); #expect(try testingQuery(root).reconciliation.code == .timeout)
            TestingASC.script.set([.init(body: Data(), mime: "text/html")]); #expect(try testingQuery(root).reconciliation.code == .invalidResponse)
        }
    }
    @Test func optionalFieldsRejectMalformedTypesBudgetsControlsAndReflection() throws {
        try testingProject { root in
            for body in [try testingPayload(internalState: 7), try testingPayload(externalState: ["state": "READY_FOR_BETA_TESTING"]), try testingPayload(expired: "false"), try testingPayload(internalState: ""), try testingPayload(externalState: String(repeating: "x", count: 129)), try testingPayload(internalState: "bad\nstate"), Data(#"{"data":null,"data":null}"#.utf8), Data(String(repeating: "[", count: 17).utf8)] {
                TestingASC.script.set([.init(body: body)]); #expect(try testingQuery(root).reconciliation.code == .malformedResponse)
            }
            for field in [false, true] { TestingASC.script.set([.init(body: try testingPayload(internalState: field ? "SAFE" : testingToken, externalState: field ? testingToken : "SAFE"))]); let r = try testingQuery(root); let encoded = try JSONFile.data(r); #expect(r.reconciliation.code == .redactedResponse && !String(decoding: encoded, as: UTF8.self).contains(testingToken)) }
            for declared in [false, true] { TestingASC.script.set([.init(body: declared ? Data() : Data(repeating: 32, count: 262145), length: declared ? 262145 : nil)]); #expect(try testingQuery(root).reconciliation.code == .responseTooLarge) }
            TestingASC.script.set([.init(body: try testingPayload(internalState: String(repeating: "α", count: 64), externalState: "FUTURE_UNKNOWN"))]); let unknown = try testingQuery(root)
            #expect(unknown.reconciliation.observationUpdated && unknown.internalReadiness == "unresolved" && unknown.reconciliation.observation?.providerValue.testing?.externalBuildState == "FUTURE_UNKNOWN")
        }
    }
    @Test func credentialRecognitionSanitizesEachNewFieldAtCommitAndLaterRead() throws {
        for external in [false, true] { try testingProject { root in
            let secret = "future-testing-secret", body = try testingPayload(internalState: external ? "SAFE" : "prefix-" + secret, externalState: external ? "prefix-" + secret : "SAFE")
            TestingASC.script.set([.init(body: body), .init(body: Data(), status: 401), .init(body: body)])
            #expect(try testingQuery(root).reconciliation.observationUpdated)
            #expect(String(decoding: try Data(contentsOf: testingRecord(root)), as: UTF8.self).contains(secret))
            let erased = try testingQuery(root, token: secret)
            #expect(erased.reconciliation.code == .authenticationRejected && erased.reconciliation.observation == nil)
            let rotated = try testingQuery(root, token: "rotated-testing-token")
            #expect(rotated.reconciliation.code == .redactedResponse && rotated.reconciliation.observation == nil)
            let noToken = try testingQuery(root, token: "")
            let encoded = try JSONFile.data(noToken)
            #expect(noToken.reconciliation.observation == nil && !String(decoding: encoded, as: UTF8.self).contains(secret))
            #expect(!String(decoding: try Data(contentsOf: testingRecord(root)), as: UTF8.self).contains(secret))
        } }
    }
    @Test func concurrentCredentialWriterFencesInflightNewFields() throws {
        for external in [false, true] { try testingProject { root in
            let secret = "future-concurrent-secret", gate = TestingGate(), done = DispatchSemaphore(value: 0), box = TestingResult()
            let body = try testingPayload(internalState: external ? "SAFE" : secret, externalState: external ? secret : "SAFE")
            TestingASC.script.set([.init(body: body, gate: gate), .init(body: Data(), status: 401)])
            DispatchQueue.global().async { box.set(Result { try testingQuery(root) }); done.signal() }
            guard gate.started.wait(timeout: .now() + 5) == .success else { gate.release.signal(); Issue.record("request did not start"); return }; defer { gate.release.signal() }
            _ = try testingQuery(root, token: secret); gate.release.signal(); try #require(done.wait(timeout: .now() + 5) == .success)
            let old = try #require(box.get()).get(); #expect(old.reconciliation.code == .redactedResponse && old.reconciliation.observation == nil)
        } }
    }
    @Test func mixedGenerationsDoNotRestoreStaleTestingAfterProcessingQuery() throws {
        try testingProject { root in
            let gate = TestingGate(), done = DispatchSemaphore(value: 0), box = TestingResult(), body = try testingPayload()
            TestingASC.script.set([.init(body: body, gate: gate), .init(body: try processingPayload())])
            DispatchQueue.global().async { box.set(Result { try testingQuery(root) }); done.signal() }
            guard gate.started.wait(timeout: .now() + 5) == .success else { gate.release.signal(); Issue.record("request did not start"); return }; defer { gate.release.signal() }
            let newer = try processingQuery(root, token: testingToken); #expect(newer.observation?.generation == 2 && newer.status == "processing-succeeded")
            gate.release.signal(); try #require(done.wait(timeout: .now() + 5) == .success); let older = try #require(box.get()).get()
            #expect(older.reconciliation.query == "superseded" && older.internalReadiness == "unresolved" && older.reconciliation.observation?.providerValue.testing == nil)
        }
    }
    @Test func legacyRecordsDecodeSafelyAndCorruptNewFieldsRefuseBeforeDispatch() throws {
        try testingProject { root in
            TestingASC.script.set([.init(body: try testingPayload())]); _ = try testingQuery(root); let path = try testingRecord(root), saved = try Data(contentsOf: path)
            for schema in [1, 2] {
                var object = try #require(JSONSerialization.jsonObject(with: saved) as? [String: Any]); object["schema"] = schema
                var observation = object["observation"] as! [String: Any], value = observation["providerValue"] as! [String: Any]; value.removeValue(forKey: "testing"); observation["providerValue"] = value; object["observation"] = observation
                try JSONSerialization.data(withJSONObject: object).write(to: path); let result = try testingQuery(root, token: "")
                #expect(result.reconciliation.code == .credentialRequired && result.reconciliation.observation?.version == "42" && result.internalReadiness == "unresolved")
            }
            for mode in 0..<4 {
                var object = try #require(JSONSerialization.jsonObject(with: saved) as? [String: Any])
                if mode == 0 { object["schema"] = 99 } else { var observation = object["observation"] as! [String: Any], value = observation["providerValue"] as! [String: Any], testing = value["testing"] as! [String: Any]; testing["internalBuildState"] = mode == 1 ? String(repeating: "x", count: 129) : mode == 2 ? "bad\nstate" : 12 as Any; value["testing"] = testing; observation["providerValue"] = value; object["observation"] = observation }
                try JSONSerialization.data(withJSONObject: object).write(to: path); TestingASC.script.set([])
                do { _ = try testingQuery(root); Issue.record("corrupt record admitted") } catch let e as MixerFailure { #expect(e.code == "store.local-record") }
                #expect(TestingASC.script.trace().isEmpty)
            }
        }
    }
    @Test func newFieldRotationBeyond16DoesNotLockOutObservations() throws {
        try testingProject { root in
            for index in 0..<24 { TestingASC.script.set([.init(body: try testingPayload())]); #expect(try testingQuery(root, token: "testing-rotation-\(index)").reconciliation.observationUpdated) }
            TestingASC.script.set([.init(body: try testingPayload(externalState: "testing-rotation-0"))]); #expect(try testingQuery(root).reconciliation.code == .redactedResponse)
        }
    }
    @Test func argumentScopeAndMissingTokenNeverDispatch() throws {
        for options in [[:], testingOptions.merging(["--build-id": "../escape"]) { _, b in b }, testingOptions.merging(["--invite": "yes"]) { _, b in b }] { #expect(throws: MixerFailure.self) { try StoreStatusRequest.parse(words: ["submit", "testing-status"], options: options) } }
        try testingProject { root in TestingASC.script.set([]); let r = try testingQuery(root, token: ""); #expect(r.reconciliation.code == .credentialRequired && r.internalReadiness == "unresolved" && TestingASC.script.trace().isEmpty) }
    }
}
