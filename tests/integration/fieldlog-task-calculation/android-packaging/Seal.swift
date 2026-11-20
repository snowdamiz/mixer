import CryptoKit
import Foundation
@_spi(CapabilityDurableV3) import MixerUpdates
import MixerRuntimeIdentity

@main struct SealDraftScenario {
    static func main() throws {
        guard CommandLine.arguments.count == 4 else {
            throw UpdateError("fieldlog.arguments", "Expected public templates, new delivery and rebuilt guest paths")
        }
        let previous = URL(fileURLWithPath: CommandLine.arguments[1])
        let delivery = URL(fileURLWithPath: CommandLine.arguments[2])
        let guests = URL(fileURLWithPath: CommandLine.arguments[3])
        let installed = delivery.appendingPathComponent("Installed")
        let sourceMap = Data("{}".utf8)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let priorIdentity = try CapabilityRuntimeIdentity(json: read(previous, "identity-template.json"))
        let scope = priorIdentity.installedRuntime.scope
        let scopeValue = try StrictJSON.decode(CanonicalValue.self, from: encoder.encode(scope))
        guard scope.environment == "development", scope.platform == "android",
              var identity = priorIdentity.descriptor.object,
              var build = identity["build"]?.object, var engine = identity["engine"]?.object
        else { throw UpdateError("fieldlog.identity", "Expected the Android development identity") }

        let grant = try read(installed, "storage-grant.json")
        let grantValue = try StrictJSON.decode(CanonicalValue.self, from: grant)
        let template = try object(read(previous, "manifest.json"))
        guard case let .array(entries)? = template["capability_grants"]?.object?["entries"],
              entries == [grantValue], grantValue.object?["namespaces"] == .array([.text("fieldlog-task-v1")]),
              template["source_map_sha256"] == .text(ReleaseVerifier.sha256(sourceMap))
        else { throw UpdateError("fieldlog.grants", "Expected the same reviewed grant and source map") }

        let secret = Curve25519.Signing.PrivateKey()
        let keyID = "fieldlog-android-calculation-source-local"
        let roots = [TrustRoot(keyID: keyID, publicKey: secret.publicKey.rawRepresentation,
            scope: scope, artifact: true, assignment: true, notBeforeUnix: 1)]
        let rootsBytes = try encoder.encode(roots)
        let binding = try object(read(delivery, "binding.json"))
        guard let buildBinding = binding["build"]?.object, let engineBinding = binding["engine"]?.object, let toolchain = binding["toolchain"]?.object
        else { throw UpdateError("fieldlog.binding", "Missing link inputs or engine") }
        for (key, value) in buildBinding { build[key] = value }
        for (key, value) in engineBinding { engine[key] = value }
        build["trust_roots_sha256"] = .text(ReleaseVerifier.sha256(rootsBytes))
        identity["build"] = .object(build)
        identity["engine"] = .object(engine)
        identity["toolchain"] = .object(toolchain)
        let identityBytes = try encoder.encode(CanonicalValue.object(identity))
        let current = try CapabilityRuntimeIdentity(json: identityBytes).installedRuntime
        let verifier = try ReleaseVerifierV3(host: current, roots: roots)

        try write(identityBytes, installed, "identity.json")
        try write(rootsBytes, installed, "roots.json")
        try write(try encoder.encode(current), delivery, "host.json")
        try write(sourceMap, delivery, "source-map.json")

        func sign(_ body: [String: CanonicalValue], field: String, domain: String) throws -> Data {
            let value = CanonicalValue.object(body)
            let signature = try secret.signature(for: Data("mixer.\(domain).v3\0".utf8) + value.canonicalCBOR())
            return try encoder.encode(CanonicalValue.object([field: value, "signature": .text(signature.base64EncodedString())]))
        }

        let now = UInt64(Date().timeIntervalSince1970)
        var artifacts: [String: VerifiedArtifactV3] = [:]
        for variant in ["baseline", "reviewed"] {
            let payload = try read(guests, "\(variant).wasm")
            guard payload.count == 10_540 else {
                throw UpdateError("fieldlog.payload", "Payload exceeds Android delivery bounds")
            }
            let count = CanonicalValue.uint(UInt64(payload.count))
            var manifest = template
            manifest["release_id"] = .text("fieldlog-calculation-" + variant)
            manifest["source_commit"] = .text("552559d2d3278abb9b1aa7dcf0288102c09a202b")
            manifest["provenance_id"] = .text("fieldlog-l08-android-" + String(current.runtime.prefix(24)))
            manifest["runtime"] = .text(current.runtime)
            manifest["payload_sha256"] = .text(ReleaseVerifier.sha256(payload))
            manifest["compressed_bytes"] = count
            manifest["expanded_bytes"] = count
            manifest["key_id"] = .text(keyID)
            manifest["created_at_unix"] = .uint(now)
            let signed = try sign(manifest, field: "manifest", domain: "artifact")
            artifacts[variant] = try verifier.verifyArtifact(signedManifest: signed, payload: payload, now: now)
            try write(signed, delivery, "\(variant).manifest.json")
            try write(payload, delivery, "\(variant).wasm")
        }

        for (index, variant) in ["baseline", "reviewed", "baseline"].enumerated() {
            guard let artifact = artifacts[variant] else { throw UpdateError("fieldlog.artifact", "Missing release") }
            let sequence = UInt64(index + 1)
            let assignment: [String: CanonicalValue] = [
                "schema": .uint(3), "scope": scopeValue, "channel": .text("beta"), "cohort": .text("sha256-v1"),
                "rollout_basis_points": .uint(10000), "sequence": .uint(sequence),
                "release_id": .text(artifact.releaseID), "artifact_sha256": .text(artifact.artifactSHA256),
                "runtime": .text(current.runtime), "key_id": .text(keyID), "created_at_unix": .uint(now),
            ]
            let signed = try sign(assignment, field: "assignment", domain: "assignment")
            _ = try verifier.verifyAssignment(signedAssignment: signed, artifact: artifact, channel: "beta",
                installation: "1f0d30b5-6e05-4e49-b928-a40bc95cb7ce", lastSequence: sequence - 1, now: now)
            try write(signed, delivery, "sequence-\(sequence).assignment.json")
        }
        print(current.runtime)
    }

    private static func object(_ bytes: Data) throws -> [String: CanonicalValue] {
        guard let value = try StrictJSON.decode(CanonicalValue.self, from: bytes).object else {
            throw UpdateError("fieldlog.object", "Expected a JSON object")
        }
        return value
    }

    private static func read(_ directory: URL, _ name: String) throws -> Data {
        try Data(contentsOf: directory.appendingPathComponent(name))
    }

    private static func write(_ data: Data, _ directory: URL, _ name: String) throws {
        try data.write(to: directory.appendingPathComponent(name), options: .withoutOverwriting)
    }
}
