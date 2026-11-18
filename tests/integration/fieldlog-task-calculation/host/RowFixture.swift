#if os(macOS) && canImport(MixerApple)
import Crypto
import Foundation
import MixerCapabilities
import MixerRuntimeIdentity
import MixerUpdates
import XCTest
@testable import MixerCapabilityActivation

// Shares the canonical replay's service client. The names expected by that
// client stay unchanged in this private test package.
struct FieldLogReleaseV3Fixture {
    struct Release {
        let name: String
        let digest: String
        let signedManifest: CanonicalValue
        let payload: Data
    }
    struct SignedPair {
        let baseline: Release
        let reviewed: Release
        let assignments: [CanonicalValue]
        let horizontalRefusal: Release
        let refusalAssignment: CanonicalValue
    }

    static let scope = UpdateScope(organization: "mixer-local", project: "fieldlog", app: "fieldlog",
                                   environment: "development", platform: "ios")
    static let keyID = "fieldlog-row-test"
    static let sourceCommit = "552559d2d3278abb9b1aa7dcf0288102c09a202b"
    static let materials: [(String, CapabilityMaterialFile.Role)] = [
        ("bridge.json", .bridgePolicy),
        ("http.json", .configuration(capabilityID: CapabilitySchemas.httpID)),
        ("storage.json", .configuration(capabilityID: CapabilitySchemas.storageID)),
        ("http-grant.json", .installedGrant(capabilityID: CapabilitySchemas.httpID)),
        ("storage-grant.json", .installedGrant(capabilityID: CapabilitySchemas.storageID))
    ]

    let host: InstalledRuntime
    let execution: InstalledCapabilityExecution
    let configuration: CapabilityColdStartConfiguration
    let signed: SignedPair?
    var baseline: Release { signed!.baseline }
    var reviewed: Release { signed!.reviewed }
    var assignments: [CanonicalValue] { signed!.assignments }

    init(run: URL, storage: RowStorage, archiveSHA256: String? = nil) throws {
        let directory = run.appendingPathComponent("online")
        let bundle = directory.appendingPathComponent("public-fixtures")
        let key = archiveSHA256.map { _ in Curve25519.Signing.PrivateKey() }
        if let key, let archiveSHA256 {
            try Self.prepare(bundle, archiveSHA256: archiveSHA256, signingKey: key)
        }
        let identity = try Self.read(bundle, "identity.json")
        let roots = try Self.read(bundle, "roots.json")
        let files = try Self.materials.map { name, role in
            CapabilityMaterialFile(role: role, bytes: try Self.read(bundle, name))
        }
        host = try CapabilityRuntimeIdentity(json: identity).installedRuntime
        execution = try InstalledCapabilityExecution(identityJSON: identity, materials: files, trustRootsJSON: roots,
            privateContainer: directory, applicationStorage: .init(runtimeFingerprint: host.runtime,
                namespace: RowStorage.namespace, service: storage, allowsDeferredGuestUIStartup: true))
        configuration = .init(directory: directory.appendingPathComponent("recovery"), channel: "beta",
                              installation: "fieldlog-row-local", observationSeconds: 1)
        if let key {
            signed = try Self.releasePair(run: run, bundle: bundle, host: host, signingKey: key)
        } else {
            signed = nil
        }
    }

    private static func prepare(_ bundle: URL, archiveSHA256: String, signingKey: Curve25519.Signing.PrivateKey) throws {
        try FileManager.default.createDirectory(at: bundle, withIntermediateDirectories: false)
        let fixture = try XCTUnwrap(Bundle.module.url(forResource: "Fixtures", withExtension: nil))
        let roots = try encoder.encode([TrustRoot(keyID: keyID, publicKey: signingKey.publicKey.rawRepresentation,
            scope: scope, artifact: true, assignment: true, notBeforeUnix: 1)])
        var identity = try object(read(fixture, "identity.json"))
        identity["application"] = [
            "organization": scope.organization, "project": scope.project, "app": scope.app,
            "environment": scope.environment, "bundle_id": "com.example.fieldlog.signed-row-local",
        ]
        var build = try XCTUnwrap(identity["build"] as? [String: Any])
        build["trust_roots_sha256"] = ReleaseVerifier.sha256(roots)
        identity["build"] = build
        var engine = try XCTUnwrap(identity["engine"] as? [String: Any])
        engine["artifact_sha256"] = archiveSHA256
        engine["version"] = "fieldlog-row-local-host"
        identity["engine"] = engine
        var execution = try XCTUnwrap(identity["execution"] as? [String: Any])
        execution["startup_export"] = CapabilityInstalledExecutionMode.startup
        identity["execution"] = execution
        identity["dependencies"] = [
            (CapabilityInstalledExecutionMode.deferredStartupID, CapabilityInstalledExecutionMode.deferredStartupSHA256),
            (CapabilityInstalledExecutionMode.contractID, CapabilityInstalledExecutionMode.contractSHA256),
            (CapabilityInstalledExecutionMode.headerID, CapabilityInstalledExecutionMode.headerSHA256),
        ].map { ["id": $0.0, "version": "1", "artifact_sha256": $0.1] }
        var storageGrant = try object(read(fixture, "storage-grant.json"))
        storageGrant["namespaces"] = [RowStorage.namespace]
        let storageGrantBytes = try json(storageGrant) + Data([10])
        var capabilities = try XCTUnwrap(identity["capabilities"] as? [[String: Any]])
        let storage = try XCTUnwrap(capabilities.firstIndex { $0["id"] as? String == CapabilitySchemas.storageID })
        capabilities[storage]["grants_sha256"] = ReleaseVerifier.sha256(storageGrantBytes)
        identity["capabilities"] = capabilities
        for (name, _) in materials {
            let data = name == "storage-grant.json" ? storageGrantBytes : try read(fixture, name)
            try data.write(to: bundle.appendingPathComponent(name))
        }
        let identityBytes = try json(identity)
        try identityBytes.write(to: bundle.appendingPathComponent("identity.json"))
        try roots.write(to: bundle.appendingPathComponent("roots.json"))
        let host = try CapabilityRuntimeIdentity(json: identityBytes).installedRuntime
        try encoder.encode(host).write(to: bundle.appendingPathComponent("host.json"))
        try Data("{}".utf8).write(to: bundle.appendingPathComponent("source-map.json"))
    }

    private static func releasePair(run: URL, bundle: URL, host: InstalledRuntime,
                                    signingKey: Curve25519.Signing.PrivateKey) throws -> SignedPair {
        let scopeValue = try StrictJSON.decode(CanonicalValue.self, from: encoder.encode(scope))
        let sourceMap = try read(bundle, "source-map.json")
        let created = UInt64(Date().timeIntervalSince1970)
        func release(_ name: String) throws -> Release {
            let payload = try read(run, "\(name).wasm")
            let releaseID = "fieldlog-row-" + name
            let grant = CanonicalValue.object([
                "capability_id": .text(CapabilitySchemas.storageID), "schema_sha256": .text(CapabilitySchemas.storageSHA256),
                "permissions": .array([.text("storage.appPrivate")]), "namespaces": .array([.text(RowStorage.namespace)]),
                "origins": .array([]), "methods": .array([]),
            ])
            let length = UInt64(payload.count)
            let manifest = CanonicalValue.object([
                "schema": .uint(3), "scope": scopeValue, "release_id": .text(releaseID),
                "source_commit": .text(sourceCommit), "provenance_id": .text("fieldlog-f02-f08-local"),
                "runtime": .text(host.runtime), "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
                "capability_hashes": .object(host.capabilityHashes.mapValues(CanonicalValue.text)),
                "state_min": .uint(0), "state_max": .uint(0), "payload_sha256": .text(ReleaseVerifier.sha256(payload)),
                "compressed_bytes": .uint(length), "expanded_bytes": .uint(length), "compression": .text("none"),
                "asset_hashes": .object([:]), "source_map_sha256": .text(ReleaseVerifier.sha256(sourceMap)),
                "limits": .object(["memory_bytes": .uint(65_536), "fuel": .uint(host.limits.fuel),
                                  "startup_milliseconds": .uint(5_000)]),
                "key_id": .text(keyID), "created_at_unix": .uint(created),
                "capability_grants": .object(["schema": .uint(1), "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256),
                                             "entries": .array([grant])]),
            ])
            let digest = ReleaseVerifier.sha256(try manifest.canonicalCBOR())
            let signed = try sign(manifest, field: "manifest", domain: "artifact", key: signingKey)
            try encoder.encode(signed).write(to: bundle.appendingPathComponent("\(name).manifest.json"))
            return .init(name: releaseID, digest: digest, signedManifest: signed, payload: payload)
        }
        let baseline = try release("baseline"), reviewed = try release("reviewed")
        let horizontalRefusal = try release("hstack-refusal")
        func assign(_ release: Release, sequence: UInt64) throws -> CanonicalValue {
            let assignment = CanonicalValue.object([
                "schema": .uint(3), "scope": scopeValue, "channel": .text("beta"), "cohort": .text("sha256-v1"),
                "rollout_basis_points": .uint(10_000), "sequence": .uint(sequence), "release_id": .text(release.name),
                "artifact_sha256": .text(release.digest), "runtime": .text(host.runtime),
                "key_id": .text(keyID), "created_at_unix": .uint(created),
            ])
            let signed = try sign(assignment, field: "assignment", domain: "assignment", key: signingKey)
            try encoder.encode(signed).write(to: bundle.appendingPathComponent("sequence-\(sequence).assignment.json"))
            return signed
        }
        let assignments = try [baseline, reviewed, baseline].enumerated().map {
            try assign($0.element, sequence: UInt64($0.offset + 1))
        }
        return try .init(baseline: baseline, reviewed: reviewed, assignments: assignments,
                         horizontalRefusal: horizontalRefusal, refusalAssignment: assign(horizontalRefusal, sequence: 1))
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

    static func json(_ value: [String: Any]) throws -> Data {
        try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes])
    }

    static func read(_ directory: URL, _ name: String) throws -> Data {
        try Data(contentsOf: directory.appendingPathComponent(name))
    }

    static func object(_ data: Data) throws -> [String: Any] {
        try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }
}
#endif
