import Darwin
import Foundation
import MixerUpdates

struct CheckFailure: Error { let reason: String }
struct Fixture: Decodable {
    let test_only: Bool
    let host: InstalledRuntime
    let roots: [TrustRoot]
    let installation: String
    let verification_time_unix: UInt64
    let artifact_sha256: String
    let payload: Data
    let signed_manifest: CanonicalValue
}
final class NoRedirect: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping @Sendable (URLRequest?) -> Void) { completionHandler(nil) }
}
func require(_ condition: Bool, _ reason: String) throws {
    guard condition else { throw CheckFailure(reason: reason) }
}
func object(_ value: CanonicalValue, keys: Set<String>) throws -> [String: CanonicalValue] {
    guard case .object(let fields) = value, Set(fields.keys) == keys else { throw CheckFailure(reason: "Closed HTTP response fields differ") }
    return fields
}
func text(_ value: CanonicalValue?) throws -> String {
    guard case .text(let value) = value else { throw CheckFailure(reason: "Expected HTTP text field") }
    return value
}
func fetch(_ session: URLSession, _ url: URL, maximum: Int) async throws -> Data {
    var request = URLRequest(url: url); request.timeoutInterval = 5
    let (stream, response) = try await session.bytes(for: request)
    guard let http = response as? HTTPURLResponse, http.statusCode == 200 else { throw CheckFailure(reason: "Expected selected protocol HTTP200; no retry or alternate-version fallback") }
    try require(response.expectedContentLength < 0 || response.expectedContentLength <= maximum, "HTTP response header exceeds bound")
    var data = Data()
    for try await byte in stream {
        try require(data.count < maximum, "HTTP response exceeds bound")
        data.append(byte)
    }
    return data
}
func check() async throws -> [String: Any] {
    let args = CommandLine.arguments
    guard args.count == 5, let base = URL(string: args[1]), let selected = UInt64(args[3]), [1, 2].contains(selected),
          let last = UInt64(args[4]), let parts = URLComponents(url: base, resolvingAgainstBaseURL: false),
          parts.scheme == "http", parts.host == "127.0.0.1", let port = parts.port, (1...65535).contains(port),
          parts.user == nil, parts.password == nil, parts.query == nil, parts.fragment == nil, ["", "/"].contains(parts.path)
    else { throw CheckFailure(reason: "usage: http-release-check literal-loopback-base TEST-fixture explicit-protocol last-sequence") }
    let fixture = try StrictJSON.decode(Fixture.self, from: Data(contentsOf: URL(fileURLWithPath: args[2])))
    try require(fixture.test_only && fixture.host.protocolVersion == selected, "Explicit selected version differs from pinned host; refusing version probing")
    // This public-API test consumer uses StrictJSON's metadata string bound.
    // It qualifies small original fixtures, not a production payload fetcher.
    try require(fixture.payload.count <= 96 * 1024, "Test consumer supports only small TEST payloads")
    let verifier = try ReleaseVerifier(host: fixture.host, roots: fixture.roots)
    let config = URLSessionConfiguration.ephemeral
    config.timeoutIntervalForRequest = 5; config.timeoutIntervalForResource = 10
    config.urlCache = nil; config.httpCookieStorage = nil; config.httpShouldSetCookies = false
    let session = URLSession(configuration: config, delegate: NoRedirect(), delegateQueue: nil)
    defer { session.invalidateAndCancel() }
    var offerURL = parts; offerURL.path = "/v\(selected)/updates"
    let scope = fixture.host.scope
    offerURL.queryItems = ["organization": scope.organization, "project": scope.project, "app": scope.app,
                          "environment": scope.environment, "platform": scope.platform, "runtime": fixture.host.runtime,
                          "channel": "beta", "installation": fixture.installation].sorted { $0.key < $1.key }.map { URLQueryItem(name: $0.key, value: $0.value) }
    guard let url = offerURL.url else { throw CheckFailure(reason: "Invalid selected delivery URL") }
    let offer = try object(StrictJSON.decode(CanonicalValue.self, from: try await fetch(session, url, maximum: 65_536)), keys: ["signed_assignment", "artifact_url"])
    let artifactPath = try text(offer["artifact_url"])
    guard let relative = URLComponents(string: artifactPath), relative.scheme == nil, relative.host == nil,
          relative.user == nil, relative.password == nil, relative.fragment == nil,
          relative.path == "/v\(selected)/artifacts/\(fixture.artifact_sha256)",
          let query = relative.queryItems, query.count == 2,
          query.filter({ $0.name == "organization" && $0.value == scope.organization }).count == 1,
          query.filter({ $0.name == "project" && $0.value == scope.project }).count == 1,
          let artifactURL = URL(string: artifactPath, relativeTo: base)?.absoluteURL,
          artifactURL.scheme == base.scheme, artifactURL.host == base.host, artifactURL.port == base.port
    else { throw CheckFailure(reason: "Artifact URL escaped the explicit protocol, content identity or tenant") }
    let download = try object(StrictJSON.decode(CanonicalValue.self, from: try await fetch(session, artifactURL, maximum: 24 * 1_048_576), maximumBytes: 24 * 1_048_576), keys: ["signed_manifest", "payload"])
    let encodedPayload = try text(download["payload"])
    guard let payload = Data(base64Encoded: encodedPayload), payload.base64EncodedString() == encodedPayload else { throw CheckFailure(reason: "Payload is not canonical base64 text") }
    guard let signed = download["signed_manifest"], let assigned = offer["signed_assignment"] else { throw CheckFailure(reason: "Signed transport absent") }
    let encoder = JSONEncoder()
    let artifact = try verifier.verifyArtifact(signedManifest: encoder.encode(signed), payload: payload, now: fixture.verification_time_unix)
    let assignment = try verifier.verifyAssignment(signedAssignment: encoder.encode(assigned), artifact: artifact, channel: "beta", installation: fixture.installation, lastSequence: last, now: fixture.verification_time_unix)
    guard case .object(let expectedEnvelope) = fixture.signed_manifest else { throw CheckFailure(reason: "Expected fixture manifest") }
    try require(artifact.artifactSHA256 == fixture.artifact_sha256 && payload == fixture.payload && artifact.manifest == expectedEnvelope["manifest"], "HTTP changed signed values, content identity or payload")
    let grants: [[String: Any]]
    if selected == 2 {
        guard let verified = artifact.capabilityGrants else { throw CheckFailure(reason: "Verified v2 token lacks typed grants") }
        try require(verified.schema == 1 && verified.schemaSHA256 == VerifiedCapabilityGrants.descriptorSHA256 && verified.entries.count == 2, "Unexpected signed grant descriptor")
        grants = verified.entries.map { ["capabilityID": $0.capabilityID, "schemaSHA256": $0.schemaSHA256, "permissions": $0.permissions, "origins": $0.origins, "methods": $0.methods, "namespaces": $0.namespaces] }
        guard let storage = verified.entries.first(where: { $0.capabilityID == "storage.keyValue.v1" }) else { throw CheckFailure(reason: "Typed signed storage grant absent") }
        try require(storage.namespaces == ["Drafts", "drafts", "outbox"], "Signed case-sensitive namespaces changed")
    } else {
        try require(artifact.capabilityGrants == nil, "V1 hash metadata acquired unsigned capability authority")
        grants = []
    }
    return ["schema": 1, "status": "passed", "scope": "actual loopback HTTP to public Swift signature verifier and typed metadata only; no guest/native import, activation, device or hosted qualification",
            "protocol": selected, "artifactSHA256": artifact.artifactSHA256, "sequence": assignment.sequence,
            "resourceLimits": ["memoryBytes": artifact.resourceLimits.memoryBytes, "fuel": artifact.resourceLimits.fuel, "startupMilliseconds": artifact.resourceLimits.startupMilliseconds], "verifiedGrants": grants,
            "versionFallback": false, "redirects": false]
}
do {
    print(String(decoding: try JSONSerialization.data(withJSONObject: try await check(), options: [.sortedKeys]), as: UTF8.self))
} catch {
    print(String(decoding: try JSONSerialization.data(withJSONObject: ["status": "rejected", "error": String(describing: error)], options: [.sortedKeys]), as: UTF8.self))
    exit(1)
}
