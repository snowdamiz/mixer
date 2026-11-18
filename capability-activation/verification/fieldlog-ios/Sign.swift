import CryptoKit
import Foundation
import MixerRuntimeIdentity
import MixerUpdates

struct SigningInput: Decodable {
    let build: [String: String]
    let engine: [String: String]
    let toolchain: [String: String]
}

struct PairInput: Decodable {
    struct Module: Decodable {
        let bytes: Int
        let sha256: String
    }
    let provenanceID: String
    let modules: [String: Module]
}

let out = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let material = out.appendingPathComponent("Installed")
let input = try JSONDecoder().decode(SigningInput.self, from: Data(contentsOf: out.appendingPathComponent("binding.json")))
let pair = try JSONDecoder().decode(PairInput.self, from: Data(contentsOf: out.appendingPathComponent("pair.json")))
let encoder = JSONEncoder()
encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]

func write<T: Encodable>(_ value: T, _ name: String) throws {
    try encoder.encode(value).write(to: out.appendingPathComponent(name), options: .withoutOverwriting)
}

let rootID = "fieldlog-ios-local"
let key = Curve25519.Signing.PrivateKey()
let scope = UpdateScope(organization: "mixer-local", project: "fieldlog", app: "fieldlog",
                        environment: "development", platform: "ios")
let roots = [TrustRoot(keyID: rootID, publicKey: key.publicKey.rawRepresentation, scope: scope,
                       artifact: true, assignment: true, notBeforeUnix: 1)]
let rootsBytes = try encoder.encode(roots)
try rootsBytes.write(to: material.appendingPathComponent("roots.json"), options: .withoutOverwriting)

let template = try Data(contentsOf: out.appendingPathComponent("identity-template.json"))
var descriptor = try StrictJSON.decode(CanonicalValue.self, from: template).object!
@MainActor func merge(_ section: String, _ values: [String: String]) {
    var fields = descriptor[section]!.object!
    for (key, value) in values { fields[key] = .text(value) }
    descriptor[section] = .object(fields)
}
merge("application", ["bundle_id": "dev.mixer.fieldlog", "organization": scope.organization,
                      "project": scope.project, "app": scope.app, "environment": scope.environment])
merge("platform", ["os": "ios", "architecture": "arm64", "environment": "simulator",
                   "minimum_os": "26.0", "target": "arm64-apple-ios26.0-simulator"])
merge("engine", input.engine)
merge("toolchain", input.toolchain)
merge("build", input.build)
merge("build", ["trust_roots_sha256": ReleaseVerifier.sha256(rootsBytes)])
merge("execution", ["startup_export": "mixer_guest_ui_start_v1"])
descriptor["capabilities"] = .array([])
let identityBytes = try encoder.encode(CanonicalValue.object(descriptor))
try identityBytes.write(to: material.appendingPathComponent("identity.json"), options: .withoutOverwriting)
let host = try CapabilityRuntimeIdentity(json: identityBytes).installedRuntime
try write(host, "host.json")
let verifier = try ReleaseVerifierV3(host: host, roots: roots)
let scopeValue = try StrictJSON.decode(CanonicalValue.self, from: encoder.encode(scope))
let created = UInt64(Date().timeIntervalSince1970)

func signed(_ value: CanonicalValue, _ field: String, _ domain: String) throws -> CanonicalValue {
    let signature = try key.signature(for: Data("mixer.\(domain).v3\0".utf8) + value.canonicalCBOR())
    return .object([field: value, "signature": .text(signature.base64EncodedString())])
}
func release(_ name: String) throws -> (CanonicalValue, VerifiedArtifactV3, String) {
    guard let module = pair.modules[name] else {
        throw UpdateError("fixture.payload", "Missing FieldLog \(name) pair entry")
    }
    let payload = try Data(contentsOf: out.appendingPathComponent("\(name).wasm"))
    guard payload.count == module.bytes, ReleaseVerifier.sha256(payload) == module.sha256 else {
        throw UpdateError("fixture.payload", "Unexpected FieldLog \(name) bytes")
    }
    let manifest = CanonicalValue.object([
        "schema": .uint(3), "scope": scopeValue, "release_id": .text("fieldlog-\(name)"),
        "source_commit": .text("552559d2d3278abb9b1aa7dcf0288102c09a202b"),
        "provenance_id": .text(pair.provenanceID), "runtime": .text(host.runtime),
        "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
        "capability_hashes": .object([:]), "state_min": .uint(0), "state_max": .uint(0),
        "payload_sha256": .text(module.sha256), "compressed_bytes": .uint(UInt64(module.bytes)),
        "expanded_bytes": .uint(UInt64(module.bytes)), "compression": .text("none"), "asset_hashes": .object([:]),
        "source_map_sha256": .text(ReleaseVerifier.sha256(Data("{}".utf8))),
        "limits": .object(["memory_bytes": .uint(65_536), "fuel": .uint(host.limits.fuel),
                           "startup_milliseconds": .uint(5_000)]),
        "key_id": .text(rootID), "created_at_unix": .uint(created),
        "capability_grants": .object(["schema": .uint(1),
            "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array([])]),
    ])
    let envelope = try signed(manifest, "manifest", "artifact")
    try write(envelope, "\(name).manifest.json")
    let verified = try verifier.verifyArtifact(signedManifest: encoder.encode(envelope), payload: payload, now: created)
    return (manifest, verified, ReleaseVerifier.sha256(try manifest.canonicalCBOR()))
}
let baseline = try release("baseline")
let reviewed = try release("reviewed")
for (index, release) in [baseline, reviewed, baseline].enumerated() {
    let sequence = UInt64(index + 1)
    let assignment = CanonicalValue.object([
        "schema": .uint(3), "scope": scopeValue, "channel": .text("beta"), "cohort": .text("sha256-v1"),
        "rollout_basis_points": .uint(10_000), "sequence": .uint(sequence),
        "release_id": release.0.object!["release_id"]!, "artifact_sha256": .text(release.2),
        "runtime": .text(host.runtime), "key_id": .text(rootID), "created_at_unix": .uint(created),
    ])
    let envelope = try signed(assignment, "assignment", "assignment")
    _ = try verifier.verifyAssignment(signedAssignment: encoder.encode(envelope), artifact: release.1,
                                      channel: "beta", installation: "fieldlog-ios-local", lastSequence: sequence - 1,
                                      now: created)
    try write(envelope, "sequence-\(sequence).assignment.json")
}
print(host.runtime)
