import Foundation
import MixerUpdates

struct Fixture: Decodable {
    let host: InstalledRuntime
    let roots: [TrustRoot]
    let artifact: String
    let payload: Data
}
struct Offer: Decodable { let signed_assignment: CanonicalValue; let artifact_url: String }
struct Download: Decodable { let signed_manifest: CanonicalValue; let payload: Data }
struct Failure: Error {}
func require(_ condition: Bool) throws { if !condition { throw Failure() } }
func reject(_ body: () throws -> Void) throws {
    do { try body() } catch { return }
    throw Failure()
}
let base = URL(string: CommandLine.arguments[1])!
try require(base.scheme == "http" && base.host == "127.0.0.1")
let fixture = try StrictJSON.decode(Fixture.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[2])))
let config = URLSessionConfiguration.ephemeral
config.timeoutIntervalForRequest = 5
config.timeoutIntervalForResource = 10
config.urlCache = nil; config.httpCookieStorage = nil
let session = URLSession(configuration: config)
defer { session.invalidateAndCancel() }
func fetch(_ path: String, maximum: Int) async throws -> Data {
    let (data, response) = try await session.data(from: URL(string: path, relativeTo: base)!)
    try require((response as? HTTPURLResponse)?.statusCode == 200 && data.count <= maximum)
    return data
}
// Small original fixture consumer only; data(for:) is not a production bounded
// streaming downloader. Server owns only literal-loopback fixture responses.
let query = "/v3/updates?organization=root-review&project=service&app=probe&environment=test&platform=ios&runtime=\(fixture.host.runtime)&channel=beta&installation=root-install"
let offer = try StrictJSON.decode(Offer.self, from: try await fetch(query, maximum: 65_536))
try require(offer.artifact_url == "/v3/artifacts/\(fixture.artifact)?organization=root-review&project=service")
let download = try StrictJSON.decode(Download.self, from: try await fetch(offer.artifact_url, maximum: 65_536))
let encoder = JSONEncoder()
let manifest = try encoder.encode(download.signed_manifest), assignment = try encoder.encode(offer.signed_assignment)
let verifier = try ReleaseVerifierV3(host: fixture.host, roots: fixture.roots)
let artifact = try verifier.verifyArtifact(signedManifest: manifest, payload: download.payload, now: 500)
let selected = try verifier.verifyAssignment(signedAssignment: assignment, artifact: artifact, channel: "beta", installation: "root-install", lastSequence: 6, now: 500)
try require(artifact.artifactSHA256 == fixture.artifact && download.payload == fixture.payload && selected.sequence == 7)
try require(artifact.resourceLimits.memoryBytes == 1 && artifact.resourceLimits.fuel == 777)
try require(artifact.capabilityGrants.entries.count == 1 && artifact.capabilityGrants.entries[0].namespaces == ["Drafts", "drafts"])
try reject { _ = try verifier.verifyAssignment(signedAssignment: assignment, artifact: artifact, channel: "beta", installation: "root-install", lastSequence: 7, now: 500) }
try reject { _ = try verifier.verifyAssignment(signedAssignment: assignment, artifact: artifact, channel: "wrong", installation: "root-install", lastSequence: 0, now: 500) }
let foreign = try ReleaseVerifierV3(host: fixture.host, roots: fixture.roots)
try reject { _ = try foreign.verifyAssignment(signedAssignment: assignment, artifact: artifact, channel: "beta", installation: "root-install", lastSequence: 0, now: 500) }
try reject { _ = try verifier.verifyArtifact(signedManifest: manifest, payload: Data([0]), now: 500) }
try reject {
    let legacy = try ReleaseVerifier(host: fixture.host, roots: fixture.roots)
    _ = try legacy.verifyArtifact(signedManifest: manifest, payload: download.payload, now: 500)
}
print("PASS actual loopback service3 to public Swift verifier: selected sequence7, signed limits/grants, replay/channel/foreign-context/tamper/legacy rejection; metadata only")
