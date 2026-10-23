import Foundation
import Crypto
@_spi(CapabilityDurableV3) import MixerUpdates

struct Fixture: Decodable {
    let host: InstalledRuntime
    let roots: [TrustRoot]
    let payload: Data
    let signed_manifest: CanonicalValue
    let signed_assignment: CanonicalValue
    let installation: String
    let verification_time_unix: UInt64
}
struct ManifestCase: Decodable { let name: String; let accepted: Bool; let signed_manifest_json: String }
struct AssignmentCase: Decodable { let name: String; let accepted: Bool; let signed_assignment_json: String }
struct Cases: Decodable { let cases: [ManifestCase]; let assignment_cases: [AssignmentCase] }
struct Failure: Error { let message: String }
var checks = 0
@MainActor func require(_ condition: Bool, _ message: String) throws {
    checks += 1; if !condition { throw Failure(message: message) }
}
func accepts(_ body: () throws -> Void) -> Bool { do { try body(); return true } catch { return false } }
func encoded(_ value: CanonicalValue) throws -> Data { try JSONEncoder().encode(value) }
let f = try JSONDecoder().decode(Fixture.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
let corpus = try JSONDecoder().decode(Cases.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[2])))
let verifier = try ReleaseVerifierV3(host: f.host, roots: f.roots)
let manifest = try encoded(f.signed_manifest), assignment = try encoded(f.signed_assignment)
let offered = try verifier._authorizeOfferV3(exactManifest: manifest, exactAssignment: assignment, channel: "beta", installation: f.installation, lastSequence: 6, now: f.verification_time_unix)
try require(offered.sequence == 7 && offered.signedManifest == manifest && offered.signedAssignment == assignment, "exact offer snapshots")
let retained = try verifier._verifyRetainedHealthySnapshotV3(exactManifest: manifest, exactAssignment: assignment, payload: f.payload, channel: "beta", installation: f.installation, storedSequence: 7, acceptedSequence: 99)
try require(retained.artifactSHA256 == offered.artifactSHA256 && retained.capabilityGrants.entries.count == 2, "retained baseline")
let copiedVerifier = verifier
let repeated = try copiedVerifier._revalidateRetainedHealthyV3(retained, payload: f.payload)
try require(repeated.artifactSHA256 == retained.artifactSHA256, "copied context")
let foreign = try ReleaseVerifierV3(host: f.host, roots: f.roots)
try require(!accepts { _ = try foreign._revalidateRetainedHealthyV3(retained, payload: f.payload) }, "foreign context rejected")
try require(!accepts { _ = try verifier._revalidateRetainedHealthyV3(retained, payload: Data()) }, "retained tamper rejected")
for pair: (UInt64, UInt64) in [(0, 99), (6, 99), (7, 6), (8, 99)] {
    try require(!accepts { _ = try verifier._verifyRetainedHealthySnapshotV3(exactManifest: manifest, exactAssignment: assignment, payload: f.payload, channel: "beta", installation: f.installation, storedSequence: pair.0, acceptedSequence: pair.1) }, "exact stored sequence")
}

// The repository's public deterministic fixture key is TEST ONLY. Rebinding the
// assignment to each validly signed manifest isolates the retained manifest
// checker; it avoids rejecting every variant just for an old artifact digest.
let seed = Data(SHA256.hash(data: Data("Mixer publicly reproducible TEST ONLY release-v3 fixture / assignment".utf8)))
let key = try Curve25519.Signing.PrivateKey(rawRepresentation: seed)
func boundAssignment(_ rawManifest: Data) throws -> Data {
    let envelope = try JSONDecoder().decode(CanonicalValue.self, from: rawManifest)
    guard let value = envelope.object?["manifest"], let release = value.object?["release_id"], var fields = f.signed_assignment.object?["assignment"]?.object else { throw Failure(message: "shape") }
    fields["artifact_sha256"] = .text(ReleaseVerifier.sha256(try value.canonicalCBOR()))
    fields["release_id"] = release
    let assigned = CanonicalValue.object(fields)
    let signature = try key.signature(for: Data("mixer.assignment.v3\0".utf8) + assigned.canonicalCBOR())
    return try encoded(.object(["assignment": assigned, "signature": .text(signature.base64EncodedString())]))
}
for test in corpus.cases {
    let bytes = Data(test.signed_manifest_json.utf8)
    let actual = accepts {
        _ = try verifier._verifyRetainedHealthySnapshotV3(exactManifest: bytes, exactAssignment: boundAssignment(bytes), payload: f.payload, channel: "beta", installation: f.installation, storedSequence: 7, acceptedSequence: 7)
    }
    try require(actual == test.accepted, "shared retained manifest: " + test.name)
}
for test in corpus.assignment_cases {
    let actual = accepts {
        _ = try verifier._authorizeOfferV3(exactManifest: manifest, exactAssignment: Data(test.signed_assignment_json.utf8), channel: "beta", installation: f.installation, lastSequence: 6, now: f.verification_time_unix)
    }
    try require(actual == test.accepted, "shared offered assignment: " + test.name)
}

func changedRoots(expired: Bool = false, revokedIndex: Int? = nil) -> [TrustRoot] {
    f.roots.enumerated().map { index, root in
        TrustRoot(keyID: root.keyID, publicKey: root.publicKey, scope: root.scope, artifact: root.artifact,
            assignment: root.assignment, revoked: revokedIndex == index,
            notBeforeUnix: root.notBeforeUnix, notAfterUnix: expired ? f.verification_time_unix - 1 : root.notAfterUnix)
    }
}
let expired = try ReleaseVerifierV3(host: f.host, roots: changedRoots(expired: true))
try require(!accepts { _ = try expired.verifyArtifact(signedManifest: manifest, payload: f.payload, now: f.verification_time_unix) }, "ordinary expiry remains strict")
try require(!accepts { _ = try expired._authorizeOfferV3(exactManifest: manifest, exactAssignment: assignment, channel: "beta", installation: f.installation, lastSequence: 6, now: f.verification_time_unix) }, "offer expiry remains strict")
let offline = try expired._verifyRetainedHealthySnapshotV3(exactManifest: manifest, exactAssignment: assignment, payload: f.payload, channel: "beta", installation: f.installation, storedSequence: 7, acceptedSequence: 7)
try require(offline.artifactSHA256 == retained.artifactSHA256, "retained metadata time exception only")
for index in f.roots.indices {
    let revoked = try ReleaseVerifierV3(host: f.host, roots: changedRoots(expired: true, revokedIndex: index))
    try require(!accepts { _ = try revoked._verifyRetainedHealthySnapshotV3(exactManifest: manifest, exactAssignment: assignment, payload: f.payload, channel: "beta", installation: f.installation, storedSequence: 7, acceptedSequence: 7) }, "revoked root still denied")
}
print("PASS \(checks) independent SPI metadata checks, including \(corpus.cases.count) shared retained-manifest and \(corpus.assignment_cases.count) offer-assignment cases; no durable-health or execution proof")
