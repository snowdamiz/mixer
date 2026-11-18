#if os(macOS) && canImport(MixerApple)
import Crypto
import Foundation
import MixerCapabilities
import MixerRuntimeIdentity
import MixerUpdates
import XCTest
@testable import MixerCapabilityActivation

struct FieldLogReleaseV3Fixture {
    struct Release {
        let name: String
        let digest: String
        let signedManifest: CanonicalValue
        let payload: Data
    }

    let host: InstalledRuntime
    let execution: InstalledCapabilityExecution
    let configuration: CapabilityColdStartConfiguration
    let baseline: Release
    let reviewed: Release
    let assignments: [CanonicalValue]
    static let keyID = "fieldlog-local-development"
    private static let fieldLogRevision = "552559d2d3278abb9b1aa7dcf0288102c09a202b"

    init(repository: URL, directory: URL, archiveSHA256: String) throws {
        let bundle = directory.appendingPathComponent("public-fixtures")
        try FileManager.default.createDirectory(at: bundle, withIntermediateDirectories: false)
        let key = Curve25519.Signing.PrivateKey()
        let sourceMap = Data("{}".utf8)
        try sourceMap.write(to: bundle.appendingPathComponent("source-map.json"))
        let scope = UpdateScope(organization: "mixer-local", project: "fieldlog", app: "fieldlog",
                                environment: "development", platform: "ios")
        let roots = try Self.encoder.encode([TrustRoot(keyID: Self.keyID, publicKey: key.publicKey.rawRepresentation,
            scope: scope, artifact: true, assignment: true, notBeforeUnix: 1)])
        let resource = try XCTUnwrap(Bundle.module.url(forResource: "Fixtures", withExtension: nil))
        var identity = try Self.object(Data(contentsOf: resource.appendingPathComponent("identity.json")))
        identity["application"] = [
            "organization": scope.organization, "project": scope.project, "app": scope.app,
            "environment": scope.environment, "bundle_id": "com.example.fieldlog.signed-local",
        ]
        var build = try XCTUnwrap(identity["build"] as? [String: Any])
        build["trust_roots_sha256"] = ReleaseVerifier.sha256(roots)
        identity["build"] = build
        var engine = try XCTUnwrap(identity["engine"] as? [String: Any])
        engine["artifact_sha256"] = archiveSHA256
        engine["version"] = "fieldlog-local-host-test"
        identity["engine"] = engine
        var mode = try XCTUnwrap(identity["execution"] as? [String: Any])
        mode["startup_export"] = "mixer_guest_ui_start_v1"
        identity["execution"] = mode
        identity["dependencies"] = [
            ["id": "mixer.guest-ui-event-v1", "version": "1",
             "artifact_sha256": "34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024"],
            ["id": "mixer.guest-ui-native-header-v1", "version": "1",
             "artifact_sha256": "d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5"],
        ]
        let identityBytes = try JSONSerialization.data(withJSONObject: identity, options: [.sortedKeys, .withoutEscapingSlashes])
        let inputs: [(String, CapabilityMaterialFile.Role)] = [
            ("bridge.json", .bridgePolicy),
            ("http.json", .configuration(capabilityID: CapabilitySchemas.httpID)),
            ("storage.json", .configuration(capabilityID: CapabilitySchemas.storageID)),
            ("http-grant.json", .installedGrant(capabilityID: CapabilitySchemas.httpID)),
            ("storage-grant.json", .installedGrant(capabilityID: CapabilitySchemas.storageID)),
        ]
        let materials = try inputs.map { name, role in
            let bytes = try Data(contentsOf: resource.appendingPathComponent(name))
            try bytes.write(to: bundle.appendingPathComponent(name))
            return CapabilityMaterialFile(role: role, bytes: bytes)
        }
        try roots.write(to: bundle.appendingPathComponent("roots.json"))
        try identityBytes.write(to: bundle.appendingPathComponent("identity.json"))
        host = try CapabilityRuntimeIdentity(json: identityBytes).installedRuntime
        try Self.encoder.encode(host).write(to: bundle.appendingPathComponent("host.json"))
        execution = try InstalledCapabilityExecution(identityJSON: identityBytes, materials: materials,
            trustRootsJSON: roots, privateContainer: directory)
        XCTAssertEqual(execution.runtimeFingerprint, host.runtime)
        configuration = .init(directory: directory.appendingPathComponent("recovery"),
                              channel: "beta", installation: "fieldlog-local-1", observationSeconds: 1)
        let modules = repository.appendingPathComponent("verification/local/fieldlog-installed-guest-proof-41a05264")
        let scopeValue = try StrictJSON.decode(CanonicalValue.self, from: Self.encoder.encode(scope))
        let created = UInt64(Date().timeIntervalSince1970)
        let installed = host
        func release(_ variant: String, _ length: Int, _ sha256: String) throws -> Release {
            let payload = try Data(contentsOf: modules.appendingPathComponent("\(variant).wasm"))
            guard payload.count == length, ReleaseVerifier.sha256(payload) == sha256 else {
                throw UpdateError("test.fixture", "FieldLog \(variant) differs from fieldlog-compact-abi2-41a05264")
            }
            let name = "fieldlog-\(variant)"
            let manifest = CanonicalValue.object([
                "schema": .uint(3), "scope": scopeValue, "release_id": .text(name),
                "source_commit": .text(Self.fieldLogRevision), "provenance_id": .text("fieldlog-compact-abi2-41a05264"),
                "runtime": .text(installed.runtime), "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
                "capability_hashes": .object(installed.capabilityHashes.mapValues(CanonicalValue.text)),
                "state_min": .uint(0), "state_max": .uint(0), "payload_sha256": .text(sha256),
                "compressed_bytes": .uint(UInt64(length)), "expanded_bytes": .uint(UInt64(length)),
                "compression": .text("none"), "asset_hashes": .object([:]),
                "source_map_sha256": .text(ReleaseVerifier.sha256(sourceMap)),
                "limits": .object(["memory_bytes": .uint(65_536), "fuel": .uint(installed.limits.fuel),
                                  "startup_milliseconds": .uint(5_000)]),
                "key_id": .text(Self.keyID), "created_at_unix": .uint(created),
                "capability_grants": .object(["schema": .uint(1),
                    "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array([])]),
            ])
            let digest = ReleaseVerifier.sha256(try manifest.canonicalCBOR())
            let signed = try Self.sign(manifest, field: "manifest", domain: "artifact", key: key)
            try Self.encoder.encode(signed).write(to: bundle.appendingPathComponent("\(variant).manifest.json"))
            try payload.write(to: bundle.appendingPathComponent("\(variant).wasm"))
            return Release(name: name, digest: digest, signedManifest: signed, payload: payload)
        }
        baseline = try release("baseline", 2757, "7429ae900e0624570b8a0e4f024098fda79e8cb25bfa27132933e2a7939f0dfb")
        reviewed = try release("reviewed", 2790, "eff19ec5956886c919f5ec00b1a3bd123a491ed4c7623ceed7bec7991595389d")
        let channel = configuration.channel
        assignments = try [baseline, reviewed, baseline, reviewed].enumerated().map { index, release in
            let sequence = UInt64(index + 1)
            let assignment = CanonicalValue.object([
                "schema": .uint(3), "scope": scopeValue, "channel": .text(channel), "cohort": .text("sha256-v1"),
                "rollout_basis_points": .uint(10_000), "sequence": .uint(sequence), "release_id": .text(release.name),
                "artifact_sha256": .text(release.digest), "runtime": .text(installed.runtime),
                "key_id": .text(Self.keyID), "created_at_unix": .uint(created),
            ])
            let signed = try Self.sign(assignment, field: "assignment", domain: "assignment", key: key)
            try Self.encoder.encode(signed).write(to: bundle.appendingPathComponent("sequence-\(sequence).assignment.json"))
            return signed
        }
    }

    private static func sign(_ value: CanonicalValue, field: String, domain: String,
                             key: Curve25519.Signing.PrivateKey) throws -> CanonicalValue {
        let signature = try key.signature(for: Data("mixer.\(domain).v3\0".utf8) + value.canonicalCBOR())
        return .object([field: value, "signature": .text(signature.base64EncodedString())])
    }

    static var encoder: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return encoder
    }

    static func object(_ data: Data) throws -> [String: Any] {
        try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }
}
#endif
