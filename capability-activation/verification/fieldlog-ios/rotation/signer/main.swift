import CryptoKit
import Foundation
import MixerRuntimeIdentity
import MixerUpdates

struct FixtureKey {
    let name: String
    let artifact: Bool
    let revoked: Bool
    let starts: UInt64
    let expires: UInt64
    let key = Curve25519.Signing.PrivateKey()

    func root(_ scope: UpdateScope) -> TrustRoot {
        TrustRoot(keyID: name, publicKey: key.publicKey.rawRepresentation, scope: scope,
                  artifact: artifact, assignment: !artifact, revoked: revoked,
                  notBeforeUnix: starts, notAfterUnix: expires)
    }

    func sign(_ value: CanonicalValue, field: String) throws -> CanonicalValue {
        let domain = Data("mixer.\(artifact ? "artifact" : "assignment").v3\0".utf8)
        let signature = try key.signature(for: domain + value.canonicalCBOR())
        return .object([field: value, "signature": .text(signature.base64EncodedString())])
    }
}

guard CommandLine.arguments.count == 3 else {
    throw UpdateError("fixture.arguments", "Pass a template directory and a new output directory")
}
let template = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let output = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
let files = FileManager.default
try files.createDirectory(at: output, withIntermediateDirectories: false)
let installed = output.appending(path: "Installed", directoryHint: .isDirectory)
try files.createDirectory(at: installed, withIntermediateDirectories: false)
let encoder = JSONEncoder()
encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
func read(_ path: String) throws -> Data {
    try Data(contentsOf: template.appending(path: path))
}
func write<T: Encodable>(_ value: T, to url: URL) throws {
    try encoder.encode(value).write(to: url, options: .withoutOverwriting)
}
func object(_ bytes: Data) throws -> [String: CanonicalValue] {
    guard let values = try StrictJSON.decode(CanonicalValue.self, from: bytes).object else {
        throw UpdateError("fixture.document", "Expected a JSON object")
    }
    return values
}

let created = UInt64(Date().timeIntervalSince1970)
let cutoff = created + 7 * 86_400
let original = try read("Installed/identity.json")
let originalIdentity = try CapabilityRuntimeIdentity(json: original)
let scope = originalIdentity.installedRuntime.scope
let initialArtifact = FixtureKey(name: "ios-initial-artifact", artifact: true, revoked: false, starts: 1, expires: cutoff)
let initialAssignment = FixtureKey(name: "ios-initial-assignment", artifact: false, revoked: false, starts: 1, expires: cutoff)
let replacementArtifact = FixtureKey(name: "ios-replacement-artifact", artifact: true, revoked: false, starts: created - 60, expires: 0)
let replacementAssignment = FixtureKey(name: "ios-replacement-assignment", artifact: false, revoked: false, starts: created - 60, expires: 0)
let revokedArtifact = FixtureKey(name: "ios-revoked-artifact", artifact: true, revoked: true, starts: 1, expires: 0)
let revokedAssignment = FixtureKey(name: "ios-revoked-assignment", artifact: false, revoked: true, starts: 1, expires: 0)
let roots = [initialArtifact, initialAssignment, replacementArtifact, replacementAssignment, revokedArtifact, revokedAssignment]
let rootsJSON = try encoder.encode(roots.map { $0.root(scope) })
try rootsJSON.write(to: installed.appending(path: "roots.json"), options: .withoutOverwriting)
var descriptor = try object(original)
var build = descriptor["build"]!.object!
build["trust_roots_sha256"] = .text(ReleaseVerifier.sha256(rootsJSON))
descriptor["build"] = .object(build)
let identity = try encoder.encode(CanonicalValue.object(descriptor))
let runtime = try CapabilityRuntimeIdentity(json: identity).installedRuntime
try identity.write(to: installed.appending(path: "identity.json"), options: .withoutOverwriting)
try write(runtime, to: output.appending(path: "host.json"))
for name in ["bridge.json", "storage-grant.json", "storage.json", "port.txt"] {
    try read("Installed/\(name)").write(to: installed.appending(path: name), options: .withoutOverwriting)
}
let variants: [(name: String, payload: String, sequence: UInt64, artifact: FixtureKey, assignment: FixtureKey)] = [
    ("baseline", "baseline", 1, initialArtifact, initialAssignment),
    ("replacement", "reviewed", 2, replacementArtifact, replacementAssignment),
    ("revoked-artifact", "reviewed", 2, revokedArtifact, replacementAssignment),
    ("revoked-assignment", "reviewed", 2, replacementArtifact, revokedAssignment),
    ("expired-artifact", "reviewed", 2, initialArtifact, replacementAssignment),
    ("expired-assignment", "reviewed", 2, replacementArtifact, initialAssignment),
    ("wrong-runtime", "reviewed", 2, replacementArtifact, replacementAssignment),
]
var digests: [String: String] = [:]
for variant in variants {
    let directory = output.appending(path: variant.name, directoryHint: .isDirectory)
    try files.createDirectory(at: directory, withIntermediateDirectories: false)
    let data = try read("\(variant.payload).wasm")
    var manifest = try object(read("\(variant.payload).manifest.json"))["manifest"]!.object!
    guard manifest["payload_sha256"] == .text(ReleaseVerifier.sha256(data)),
          manifest["compressed_bytes"] == .uint(UInt64(data.count)),
          manifest["expanded_bytes"] == .uint(UInt64(data.count)) else {
        throw UpdateError("fixture.payload", "Wrong template bytes")
    }
    let fingerprint = variant.name == "wrong-runtime" ? originalIdentity.fingerprint : runtime.runtime
    manifest["runtime"] = .text(fingerprint)
    manifest["key_id"] = .text(variant.artifact.name)
    manifest["created_at_unix"] = .uint(created)
    let value = CanonicalValue.object(manifest)
    let digest = ReleaseVerifier.sha256(try value.canonicalCBOR())
    let assignment: CanonicalValue = .object([
        "schema": .uint(3), "scope": manifest["scope"]!, "channel": .text("beta"), "cohort": .text("sha256-v1"),
        "rollout_basis_points": .uint(10_000), "sequence": .uint(variant.sequence),
        "release_id": manifest["release_id"]!, "artifact_sha256": .text(digest), "runtime": .text(fingerprint),
        "key_id": .text(variant.assignment.name), "created_at_unix": .uint(created),
    ])
    let signedManifest = directory.appending(path: "signed-manifest.json")
    if variant.name == "revoked-assignment" || variant.name == "expired-assignment" {
        guard digest == digests["replacement"] else {
            throw UpdateError("fixture.artifact", "Assignment-only control changed the artifact")
        }
        try files.copyItem(at: output.appending(path: "replacement/signed-manifest.json"), to: signedManifest)
    } else {
        try write(variant.artifact.sign(value, field: "manifest"), to: signedManifest)
    }
    try write(variant.assignment.sign(assignment, field: "assignment"), to: directory.appending(path: "assignment.json"))
    try data.write(to: directory.appending(path: "payload.wasm"), options: .withoutOverwriting)
    digests[variant.name] = digest
}
struct SigningReceipt: Encodable {
    let created: UInt64
    let cutoff: UInt64
    let runtime: String
    let artifactDigests: [String: String]
}
try write(SigningReceipt(created: created, cutoff: cutoff, runtime: runtime.runtime, artifactDigests: digests),
          to: output.appending(path: "signing.json"))
