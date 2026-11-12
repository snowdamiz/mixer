import Foundation
import Testing
@testable import MixerBuild

private let playToken = "offline-play-status-token"
private func playIdentity(_ app: String = "com.example.Store", _ version: String = "42", _ track: String = "qa") throws -> PlayTestingRequest {
    try .init(applicationID: app, versionCode: version, track: track)
}
private func playPayload(_ state: String = PlayReleaseLifecycle.published.rawValue, track: String = "qa", codes: [Any] = [42]) throws -> Data {
    try JSONSerialization.data(withJSONObject: ["releases": [["releaseName": "Display name is not identity", "track": track,
        "activeArtifacts": codes.map { ["versionCode": $0] }, "releaseLifecycleState": state]]])
}
private struct PlayReply: Sendable {
    var body: Data = Data()
    var status = 200
    var mime = "application/json"
    var responseURL: URL?
    var length: Int?
    var error: URLError?
}
private final class PlayScript: @unchecked Sendable {
    private let lock = NSLock()
    private var replies: [PlayReply] = []
    private var requests: [URLRequest] = []
    func set(_ replies: [PlayReply]) { lock.lock(); defer { lock.unlock() }; self.replies = replies; requests = [] }
    func take(_ request: URLRequest) -> PlayReply? {
        lock.lock(); defer { lock.unlock() }; requests.append(request)
        return replies.isEmpty ? nil : replies.removeFirst()
    }
    func trace() -> [URLRequest] { lock.lock(); defer { lock.unlock() }; return requests }
}
private final class PlayProtocol: URLProtocol, @unchecked Sendable {
    static let script = PlayScript()
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        guard let reply = Self.script.take(request) else { client?.urlProtocol(self, didFailWithError: URLError(.resourceUnavailable)); return }
        if let error = reply.error { client?.urlProtocol(self, didFailWithError: error); return }
        var headers = ["Content-Type": reply.mime]
        if let length = reply.length { headers["Content-Length"] = String(length) }
        let response = HTTPURLResponse(url: reply.responseURL ?? request.url!, statusCode: reply.status, httpVersion: "HTTP/1.1", headerFields: headers)!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: reply.body)
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}
private func playReader() -> PlayReleaseStatus {
    let config = URLSessionConfiguration.ephemeral; config.protocolClasses = [PlayProtocol.self]
    return .init(configuration: config)
}

@Suite(.serialized) struct PlayReleaseStatusTests {
    @Test func publishedIsExactReadButNeverTestingQualification() async throws {
        let identity = try playIdentity()
        PlayProtocol.script.set([.init(body: try playPayload())])
        let report = try await playReader().status(request: identity, token: playToken)
        #expect(report.status == .publishedOnTrack && report.exitCode == 0)
        #expect(report.observation?.identity == identity && report.observation?.lifecycle == .published)
        #expect(report.observationFreshness == "current-provider-observation")
        #expect(report.testingReadiness == "unverified" && report.testLinks == "unverified" && report.productionAvailability == "unverified")
        let trace = PlayProtocol.script.trace(), request = try #require(trace.first)
        #expect(trace.count == 1 && request.httpMethod == "GET" && request.httpBody == nil && request.httpBodyStream == nil)
        #expect(request.url?.absoluteString == "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/com.example.Store/tracks/qa/releases")
        #expect(request.value(forHTTPHeaderField: "Authorization") == "Bearer " + playToken)
        #expect(request.value(forHTTPHeaderField: "Accept") == "application/json" && request.timeoutInterval == 30)
        let object = try #require(JSONSerialization.jsonObject(with: JSONEncoder().encode(report)) as? [String: Any])
        #expect(object["status"] as? String == "published-on-track" && object["testingReadiness"] as? String == "unverified")
        #expect(!String(decoding: try JSONEncoder().encode(report), as: UTF8.self).contains(playToken))
    }

    @Test func lifecycleTransitionsKeepHumanActionsAndRejectionsVisible() async throws {
        let states: [(PlayReleaseLifecycle, PlayTestingReport.Status, Int32)] = [
            (.draft, .draft, 2), (.notSentForReview, .awaitingReviewSubmission, 2), (.inReview, .inReview, 2),
            (.approvedNotPublished, .awaitingPublication, 2), (.notApproved, .rejected, 1), (.published, .publishedOnTrack, 0)
        ]
        let identity = try playIdentity()
        var previous: PlayReleaseObservation?
        PlayProtocol.script.set(try states.map { .init(body: try playPayload($0.0.rawValue)) })
        for (lifecycle, status, exit) in states {
            let result = try await playReader().status(request: identity, token: playToken, previous: previous)
            #expect(result.status == status && result.exitCode == exit && result.code == nil)
            #expect(result.observation?.lifecycle == lifecycle && result.testingReadiness == "unverified")
            previous = result.observation
        }
        #expect(PlayProtocol.script.trace().count == states.count)
    }

    @Test func timeoutRetainsHistoryWithoutRetryAndRecoveryUsesSameIdentity() async throws {
        let identity = try playIdentity()
        PlayProtocol.script.set([.init(body: try playPayload()), .init(error: URLError(.timedOut)), .init(body: try playPayload(PlayReleaseLifecycle.notApproved.rawValue))])
        let reader = playReader(), initial = try await reader.status(request: identity, token: playToken)
        let timedOut = try await reader.status(request: identity, token: playToken, previous: initial.observation)
        #expect(timedOut.status == .unresolved && timedOut.code == .timeout && timedOut.exitCode == 1)
        #expect(timedOut.observation?.lifecycle == .published && timedOut.observationFreshness == "retained-previous-observation")
        #expect(timedOut.testingReadiness == "unverified" && PlayProtocol.script.trace().count == 2)
        let recovered = try await reader.status(request: identity, token: playToken, previous: timedOut.observation)
        #expect(recovered.status == .rejected && recovered.observationFreshness == "current-provider-observation")
        #expect(PlayProtocol.script.trace().count == 3 && PlayProtocol.script.trace().allSatisfy { $0.url == identity.url && $0.httpMethod == "GET" })
    }

    @Test func previousObservationsCannotCrossAppVersionOrTrack() async throws {
        PlayProtocol.script.set([.init(body: try playPayload())])
        let initial = try await playReader().status(request: playIdentity(), token: playToken)
        let others = [try playIdentity("com.other.Store"), try playIdentity("com.example.Store", "43"), try playIdentity("com.example.Store", "42", "production")]
        for identity in others {
            PlayProtocol.script.set([.init(error: URLError(.timedOut))])
            let result = try await playReader().status(request: identity, token: playToken, previous: initial.observation)
            #expect(result.status == .unresolved && result.observation == nil && result.observationFreshness == "no-observation")
        }
    }

    @Test func wrongResponseContextAndWrongTrackRefuse() async throws {
        let identity = try playIdentity()
        let replies = [PlayReply(body: try playPayload(), responseURL: try playIdentity("com.other.Store").url),
                       PlayReply(body: try playPayload(), responseURL: try playIdentity("com.example.Store", "42", "production").url),
                       PlayReply(body: try playPayload(track: "production"))]
        for reply in replies {
            PlayProtocol.script.set([reply])
            let result = try await playReader().status(request: identity, token: playToken)
            #expect(result.code == .identityMismatch && result.status == .unresolved && result.observation == nil)
        }
        PlayProtocol.script.set([.init(body: try playPayload(codes: [142]))])
        let absent = try await playReader().status(request: identity, token: playToken)
        #expect(absent.status == .notObserved && absent.observation == nil && absent.exitCode == 2)
    }

    @Test func unknownUnspecifiedAmbiguousAndMalformedRefuse() async throws {
        let base = try playPayload(), parsed = try #require(JSONSerialization.jsonObject(with: base) as? [String: Any])
        let releases = try #require(parsed["releases"] as? [[String: Any]])
        let cases: [(Data, PlayStatusFailure)] = [
            (try playPayload("FUTURE_STATE"), .unknownState),
            (try playPayload("RELEASE_LIFECYCLE_STATE_UNSPECIFIED"), .unknownState),
            (try JSONSerialization.data(withJSONObject: ["releases": releases + releases]), .contradictoryResponse),
            (try playPayload(codes: [42, 42]), .contradictoryResponse),
            (try playPayload(codes: ["42"]), .malformedResponse),
            (try playPayload(codes: [42.5]), .malformedResponse),
            (try playPayload(codes: [0]), .contradictoryResponse),
            (Data("{\"releases\":[],\"releases\":[]}".utf8), .malformedResponse),
            (Data("{\"releases\":[{\"track\":\"qa\",\"activeArtifacts\":[{\"versionCode\":42}]}]}".utf8), .malformedResponse),
            (try JSONSerialization.data(withJSONObject: ["releases": Array(repeating: releases[0], count: 21)]), .malformedResponse)
        ]
        for (bytes, failure) in cases {
            PlayProtocol.script.set([.init(body: bytes)])
            let report = try await playReader().status(request: playIdentity(), token: playToken)
            #expect(report.status == .unresolved && report.code == failure && report.observation == nil && report.exitCode == 1)
        }
    }

    @Test func uploadSuccessAndEmptyReleaseListCannotProveTestingReady() async throws {
        for bytes in [Data("{\"versionCode\":42,\"sha256\":\"uploaded\"}".utf8), Data("{}".utf8), Data("{\"releases\":[]}".utf8)] {
            PlayProtocol.script.set([.init(body: bytes)])
            let result = try await playReader().status(request: playIdentity(), token: playToken)
            #expect(result.status != .publishedOnTrack && result.testingReadiness == "unverified" && result.exitCode != 0)
        }
    }

    @Test func authRedirectMimeAndResponseBoundsAreExplicit() async throws {
        let cases: [(PlayReply, PlayStatusFailure)] = [
            (.init(status: 401), .authenticationRejected), (.init(status: 403), .accessForbidden),
            (.init(status: 404), .notFound), (.init(status: 429), .rateLimited), (.init(status: 503), .providerRejected),
            (.init(status: 302), .redirectRefused), (.init(mime: "text/html"), .malformedResponse),
            (.init(length: PlayReleaseStatus.maximumResponseBytes + 1), .responseTooLarge),
            (.init(body: Data(repeating: 32, count: PlayReleaseStatus.maximumResponseBytes + 1)), .responseTooLarge),
            (.init(error: URLError(.notConnectedToInternet)), .transportFailed)
        ]
        for (reply, failure) in cases {
            PlayProtocol.script.set([reply])
            let result = try await playReader().status(request: playIdentity(), token: playToken)
            #expect(result.status == .unresolved && result.code == failure && result.exitCode == 1)
            #expect(PlayProtocol.script.trace().count == 1)
        }
    }

    @Test func invalidIdentitiesAndCredentialsNeverStartAQuery() async throws {
        for (app, code, track) in [("com.example/other", "42", "qa"), ("com..example", "42", "qa"), ("com.example", "042", "qa"),
                                  ("com.example", "0", "qa"), ("com.example", "2147483648", "qa"), ("com.example", "42", "../production")] {
            #expect(throws: PlayStatusFailure.invalidRequest) { try PlayTestingRequest(applicationID: app, versionCode: code, track: track) }
        }
        PlayProtocol.script.set([])
        for token in ["", "bad\r\nheader"] {
            let result = try await playReader().status(request: playIdentity(), token: token)
            #expect(result.code == .credentialRequired)
        }
        do {
            _ = try await playReader().status(request: playIdentity(), token: "example")
            Issue.record("Reflected credential admitted")
        } catch let failure as PlayStatusFailure { #expect(failure == .redactedResponse) }
        #expect(PlayProtocol.script.trace().isEmpty)
        let request = try PlayTestingRequest.parse(words: ["submit", "testing-status"], options: ["--provider": "play", "--version-code": "42", "--track": "wear:qa"], applicationID: "com.example.Store")
        #expect(request.track == "wear:qa" && request.url.absoluteString.contains("/tracks/wear:qa/releases"))
        #expect(throws: PlayStatusFailure.invalidRequest) {
            try PlayTestingRequest.parse(words: ["submit", "testing-status"], options: ["--provider": "play", "--version-code": "42", "--track": "qa", "--upload": "yes"], applicationID: "com.example.Store")
        }
    }
}
