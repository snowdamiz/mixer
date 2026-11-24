import Crypto
import Foundation
import MixerUpdates

@main
enum CheckSignedAdmission {
    static func main() {
        do {
            try run()
        } catch let error as UpdateError {
            FileHandle.standardError.write(Data("\(error.code): \(error)\n".utf8))
            exit(1)
        } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(1)
        }
    }

    private static func run() throws {
        let arguments = CommandLine.arguments
        precondition(arguments.count == 4)
        let module = try Data(contentsOf: URL(fileURLWithPath: arguments[1]))
        let patch = try Data(contentsOf: URL(fileURLWithPath: arguments[2]))
        let source = arguments[3]
        for platform in ["ios", "android"] {
            try check(platform: platform, source: source, module: module, patch: patch)
        }
    }

    private static func check(platform: String, source: String, module: Data, patch: Data) throws {
        let scope = UpdateScope(organization: "mixer-local", project: "s2", app: "full-swift",
                                environment: "development", platform: platform)
        let host = InstalledRuntime(scope: scope, runtime: ReleaseVerifier.sha256(Data(platform.utf8)),
                                    protocolVersion: 3, guestABI: 2, capabilityHashes: [:],
                                    stateVersion: 0, maxPayloadBytes: 4_194_304,
                                    limits: .init(memoryBytes: 4_194_304, fuel: 1_000_000, startupMilliseconds: 30_000))
        let key = Curve25519.Signing.PrivateKey()
        let keyID = "s2-disposable-development"
        let verifier = try ReleaseVerifierV3(host: host, roots: [
            TrustRoot(keyID: keyID, publicKey: key.publicKey.rawRepresentation, scope: scope,
                      artifact: true, assignment: true, notBeforeUnix: 1, notAfterUnix: 3)
        ])
        let encoder = JSONEncoder()
        let scopeValue = try StrictJSON.decode(CanonicalValue.self, from: encoder.encode(scope))

        func sign(_ value: CanonicalValue, field: String, domain: String) throws -> Data {
            let signature = try key.signature(for: Data("mixer.\(domain).v3\0".utf8) + value.canonicalCBOR())
            return try encoder.encode(CanonicalValue.object([
                field: value, "signature": .text(signature.base64EncodedString())
            ]))
        }

        func manifest(_ payload: Data, expanded: Int, compression: String) -> CanonicalValue {
            .object([
                "schema": .uint(3), "scope": scopeValue, "release_id": .text("s2-host"),
                "source_commit": .text(source), "provenance_id": .text("s2-development"),
                "runtime": .text(host.runtime), "protocol": .uint(3), "guest_abi": .uint(2),
                "ui_schema": .uint(host.uiSchema), "capability_hashes": .object([:]),
                "state_min": .uint(0), "state_max": .uint(0),
                "payload_sha256": .text(ReleaseVerifier.sha256(payload)),
                "compressed_bytes": .uint(UInt64(payload.count)), "expanded_bytes": .uint(UInt64(expanded)),
                "compression": .text(compression), "asset_hashes": .object([:]),
                "source_map_sha256": .text(ReleaseVerifier.sha256(Data("{}".utf8))),
                "limits": .object(["memory_bytes": .uint(host.limits.memoryBytes), "fuel": .uint(host.limits.fuel),
                                  "startup_milliseconds": .uint(host.limits.startupMilliseconds)]),
                "key_id": .text(keyID), "created_at_unix": .uint(2),
                "capability_grants": .object(["schema": .uint(1),
                    "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array([])])
            ])
        }

        func refusal(_ label: String, payload: Data, expanded: Int, compression: String, code: String) throws {
            let signed = try sign(manifest(payload, expanded: expanded, compression: compression),
                                  field: "manifest", domain: "artifact")
            do {
                _ = try verifier.verifyArtifact(signedManifest: signed, payload: payload, now: 2)
                throw UpdateError("check.unexpected_acceptance", label)
            } catch let error as UpdateError where error.code == code {
                print("\(platform) \(label): \(error.code)")
            }
        }

        let control = Data("S2 verifier positive control".utf8)
        let signedControl = try sign(manifest(control, expanded: control.count, compression: "none"),
                                     field: "manifest", domain: "artifact")
        let artifact = try verifier.verifyArtifact(signedManifest: signedControl, payload: control, now: 2)
        let assignment: CanonicalValue = .object([
            "schema": .uint(3), "scope": scopeValue, "channel": .text("beta"), "cohort": .text("sha256-v1"),
            "rollout_basis_points": .uint(10_000), "sequence": .uint(1), "release_id": .text(artifact.releaseID),
            "artifact_sha256": .text(artifact.artifactSHA256), "runtime": .text(host.runtime),
            "key_id": .text(keyID), "created_at_unix": .uint(2)
        ])
        let accepted = try verifier.verifyAssignment(
            signedAssignment: sign(assignment, field: "assignment", domain: "assignment"),
            artifact: artifact, channel: "beta", installation: "s2-local", lastSequence: 0, now: 2)
        precondition(accepted.sequence == 1)
        print("\(platform) signed artifact and assignment control: accepted")
        try refusal("raw module", payload: module, expanded: module.count, compression: "none", code: "v3.payload.size")
        try refusal("delta", payload: patch, expanded: module.count, compression: "zstd-delta", code: "v3.manifest.payload")
        try refusal("codec only", payload: patch, expanded: patch.count, compression: "zstd-delta", code: "v3.manifest.payload")
    }
}
