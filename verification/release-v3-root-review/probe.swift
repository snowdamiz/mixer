import Foundation
import Crypto
import MixerUpdates

// Original public-client review probes. The fixture's reproducible keys are
// test-only; this executable does not authorize or execute a Wasm module.
struct Fixture: Decodable {
    let host: InstalledRuntime
    let roots: [TrustRoot]
    let payload: Data
    let signedManifest: CanonicalValue
    let signedAssignment: CanonicalValue
    let now: UInt64
    let installation: String
    enum CodingKeys: String, CodingKey {
        case host, roots, payload, installation
        case signedManifest = "signed_manifest", signedAssignment = "signed_assignment"
        case now = "verification_time_unix"
    }
}

var checks = 0
@MainActor func require(_ value: Bool, _ context: String) throws {
    checks += 1
    if !value { throw NSError(domain: "RootV3Review", code: 1, userInfo: [NSLocalizedDescriptionKey: context]) }
}
@MainActor func denied(_ context: String, _ body: () throws -> Void) throws {
    do { try body() } catch { checks += 1; return }
    try require(false, context)
}
func encode(_ value: CanonicalValue) throws -> Data { try JSONEncoder().encode(value) }
func variants(_ value: CanonicalValue, path: String = "") -> [(String, CanonicalValue)] {
    switch value {
    case .object(let fields):
        return fields.keys.sorted().flatMap { key in
            variants(fields[key]!, path: path + "/" + key).map { name, child in
                var changed = fields; changed[key] = child; return (name, .object(changed))
            }
        }
    case .array(let items):
        return items.enumerated().flatMap { index, item in
            variants(item, path: path + "/" + String(index)).map { name, child in
                var changed = items; changed[index] = child; return (name, .array(changed))
            }
        }
    case .text(let text): return [(path, .text(text + "x"))]
    case .uint(let n): return [(path, .uint(n == UInt64.max ? 0 : n + 1))]
    case .boolean(let b): return [(path, .boolean(!b))]
    }
}

let fixture = try JSONDecoder().decode(Fixture.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
let verifier = try ReleaseVerifierV3(host: fixture.host, roots: fixture.roots)
let manifestBytes = try encode(fixture.signedManifest)
let assignmentBytes = try encode(fixture.signedAssignment)
let artifact = try verifier.verifyArtifact(signedManifest: manifestBytes, payload: fixture.payload, now: fixture.now)
let accepted = try verifier.verifyAssignment(signedAssignment: assignmentBytes, artifact: artifact, channel: "beta", installation: fixture.installation, lastSequence: 6, now: fixture.now)
try require(accepted.sequence == 7 && artifact.capabilityGrants.entries.count == 2, "positive control")

for (path, changed) in variants(fixture.signedManifest) {
    try denied("unresigned manifest leaf " + path) {
        _ = try verifier.verifyArtifact(signedManifest: encode(changed), payload: fixture.payload, now: fixture.now)
    }
}
for (path, changed) in variants(fixture.signedAssignment) {
    try denied("unresigned assignment leaf " + path) {
        _ = try verifier.verifyAssignment(signedAssignment: encode(changed), artifact: artifact, channel: "beta", installation: fixture.installation, lastSequence: 6, now: fixture.now)
    }
}

let seed = Data(SHA256.hash(data: Data("Mixer publicly reproducible TEST ONLY release-v3 fixture / artifact".utf8)))
let testKey = try Curve25519.Signing.PrivateKey(rawRepresentation: seed)
func signed(_ manifest: CanonicalValue) throws -> Data {
    let signature = try testKey.signature(for: Data("mixer.artifact.v3\0".utf8) + manifest.canonicalCBOR())
    return try encode(.object(["manifest": manifest, "signature": .text(signature.base64EncodedString())]))
}
let base = fixture.signedManifest.object!["manifest"]!.object!
for target in ["scope", "limits", "capability_grants"] {
    var manifest = base, nested = base[target]!.object!
    nested["extra"] = .boolean(false); manifest[target] = .object(nested)
    try denied("validly signed unknown nested field " + target) {
        _ = try verifier.verifyArtifact(signedManifest: signed(.object(manifest)), payload: fixture.payload, now: fixture.now)
    }
}
for key in base.keys.sorted() {
    var changed = base; changed[key] = nil
    try denied("validly signed omitted field " + key) {
        _ = try verifier.verifyArtifact(signedManifest: signed(.object(changed)), payload: fixture.payload, now: fixture.now)
    }
}

// Neither identical raw configuration nor the same signed content retargets an
// existing proof into a separately initialized verifier's private authority.
let other = try ReleaseVerifierV3(host: fixture.host, roots: fixture.roots)
try denied("foreign context") {
    _ = try other.verifyAssignment(signedAssignment: assignmentBytes, artifact: artifact, channel: "beta", installation: fixture.installation, lastSequence: 6, now: fixture.now)
}
let copy = verifier
_ = try copy.verifyAssignment(signedAssignment: assignmentBytes, artifact: artifact, channel: "beta", installation: fixture.installation, lastSequence: 6, now: fixture.now)
checks += 1
try denied("payload substitution on revalidation") {
    _ = try copy.revalidateArtifact(artifact, payload: Data(repeating: 0, count: fixture.payload.count), now: fixture.now)
}
try denied("legacy verifier cannot select v3") { _ = try ReleaseVerifier(host: fixture.host, roots: fixture.roots) }
print("Root public Swift v3 review passed \(checks) checks; no execution or durable selection")
