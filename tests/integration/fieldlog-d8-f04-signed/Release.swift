import CryptoKit
import Foundation
import MixerCapabilities
@testable import MixerCapabilityActivation
import MixerRuntimeIdentity
import MixerUpdates

enum Release {
    static let scope = UpdateScope(organization: "mixer-local", project: "fieldlog",
        app: "fieldlog-d8-f04", environment: "development", platform: "ios")
    static let installation = "fieldlog-d8-f04-host"
    static let materials: [(String, CapabilityMaterialFile.Role)] = [
        ("bridge.json", .bridgePolicy),
        ("http.json", .configuration(capabilityID: CapabilitySchemas.httpID)),
        ("storage.json", .configuration(capabilityID: CapabilitySchemas.storageID)),
        ("http-grant.json", .installedGrant(capabilityID: CapabilitySchemas.httpID)),
        ("storage-grant.json", .installedGrant(capabilityID: CapabilitySchemas.storageID)),
    ]

    static func prepare(_ work: URL, fixtures: URL, guests: URL, vm: URL) throws {
        let key = Curve25519.Signing.PrivateKey()
        let keyID = "fieldlog-d8-f04-local"
        let now = UInt64(Date().timeIntervalSince1970)
        let roots = try encode([TrustRoot(keyID: keyID, publicKey: key.publicKey.rawRepresentation,
            scope: scope, artifact: true, assignment: true, notBeforeUnix: now - 60,
            notAfterUnix: now + 900)])
        try roots.write(to: work.appendingPathComponent("roots.json"))
        var identity = try object(read(fixtures, "identity.json"))
        identity["application"] = [
            "organization": scope.organization, "project": scope.project, "app": scope.app,
            "environment": scope.environment, "bundle_id": "com.example.fieldlog.d8-f04",
        ]
        var build = try need(identity["build"] as? [String: Any], "build identity")
        build["trust_roots_sha256"] = ReleaseVerifier.sha256(roots)
        identity["build"] = build
        var engine = try need(identity["engine"] as? [String: Any], "engine identity")
        engine["artifact_sha256"] = ReleaseVerifier.sha256(try Data(contentsOf: vm))
        engine["version"] = "fieldlog-d8-f04-local"
        identity["engine"] = engine
        var execution = try need(identity["execution"] as? [String: Any], "execution identity")
        execution["startup_export"] = CapabilityInstalledExecutionMode.startup
        identity["execution"] = execution
        identity["dependencies"] = [
            (CapabilityInstalledExecutionMode.deferredStartupID, CapabilityInstalledExecutionMode.deferredStartupSHA256),
            (CapabilityInstalledExecutionMode.contractID, CapabilityInstalledExecutionMode.contractSHA256),
            (CapabilityInstalledExecutionMode.headerID, CapabilityInstalledExecutionMode.headerSHA256),
            ("fieldlog-pair25-repository", "db9e4e490263d4b0779b03fadfdc07cfca5d23df2501c5c900b54abb904b86fb"),
        ].sorted { $0.0 < $1.0 }.map { ["id": $0.0, "version": "1", "artifact_sha256": $0.1] }
        var grant = try object(read(fixtures, "storage-grant.json"))
        grant["namespaces"] = [TaskStorage.namespace]
        let grantBytes = try MaterialJSON.canonical(MaterialJSON.decode(JSONSerialization.data(withJSONObject: grant)))
        var caps = try need(identity["capabilities"] as? [[String: Any]], "capability identity")
        let storage = try need(caps.firstIndex { $0["id"] as? String == CapabilitySchemas.storageID }, "storage identity")
        caps[storage]["grants_sha256"] = ReleaseVerifier.sha256(grantBytes)
        identity["capabilities"] = caps
        for (name, _) in materials {
            let data = name == "storage-grant.json" ? grantBytes : try read(fixtures, name)
            try data.write(to: work.appendingPathComponent(name))
        }
        let identityBytes = try JSONSerialization.data(withJSONObject: identity, options: [.sortedKeys])
        try identityBytes.write(to: work.appendingPathComponent("identity.json"))
        let host = try CapabilityRuntimeIdentity(json: identityBytes).installedRuntime
        try encode(host).write(to: work.appendingPathComponent("host.json"))
        let verifier = try ReleaseVerifierV3(host: host, roots: StrictJSON.decode([TrustRoot].self, from: roots))
        let scopeValue = try StrictJSON.decode(CanonicalValue.self, from: encode(scope))
        let capability = CanonicalValue.object([
            "capability_id": .text(CapabilitySchemas.storageID), "schema_sha256": .text(CapabilitySchemas.storageSHA256),
            "permissions": .array([.text("storage.appPrivate")]), "namespaces": .array([.text(TaskStorage.namespace)]),
            "origins": .array([]), "methods": .array([]),
        ])
        let sourceMap = Data("{}".utf8)
        var products: [String: (artifact: VerifiedArtifactV3, payload: Data, signed: Data)] = [:]
        for (name, source) in [
            ("prior", "9a69cb9d97728f5f8f85f78193e1ed5d09059b54"),
            ("successor", "d51adf50de7e20549e87062e4569609342cdfe25"),
        ] {
            let payload = try read(guests, name + ".wasm")
            let count = CanonicalValue.uint(UInt64(payload.count))
            let manifest = CanonicalValue.object([
                "schema": .uint(3), "scope": scopeValue, "release_id": .text("fieldlog-f04-" + name),
                "source_commit": .text(source), "provenance_id": .text("fieldlog-f04-host-behavior-projection"),
                "runtime": .text(host.runtime), "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
                "capability_hashes": .object(host.capabilityHashes.mapValues(CanonicalValue.text)),
                "state_min": .uint(0), "state_max": .uint(0), "payload_sha256": .text(ReleaseVerifier.sha256(payload)),
                "compressed_bytes": count, "expanded_bytes": count, "compression": .text("none"),
                "asset_hashes": .object([:]), "source_map_sha256": .text(ReleaseVerifier.sha256(sourceMap)),
                "limits": .object(["memory_bytes": .uint(65_536), "fuel": .uint(host.limits.fuel),
                                  "startup_milliseconds": .uint(5_000)]),
                "key_id": .text(keyID), "created_at_unix": .uint(now),
                "capability_grants": .object(["schema": .uint(1),
                    "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array([capability])]),
            ])
            let signed = try sign(manifest, field: "manifest", domain: "artifact", key: key)
            let artifact = try verifier.verifyArtifact(signedManifest: signed, payload: payload, now: now)
            products[name] = (artifact, payload, signed)
        }
        for (index, phase) in ["prior", "successor", "rollback"].enumerated() {
            let name = phase == "rollback" ? "prior" : phase
            let product = try need(products[name], "release product")
            let assignment = CanonicalValue.object([
                "schema": .uint(3), "scope": scopeValue, "channel": .text("beta"), "cohort": .text("sha256-v1"),
                "rollout_basis_points": .uint(10_000), "sequence": .uint(UInt64(index + 1)),
                "release_id": .text("fieldlog-f04-" + name), "artifact_sha256": .text(product.artifact.artifactSHA256),
                "runtime": .text(host.runtime), "key_id": .text(keyID), "created_at_unix": .uint(now),
            ])
            let path = work.appendingPathComponent(phase)
            try FileManager.default.createDirectory(at: path, withIntermediateDirectories: false)
            try sign(assignment, field: "assignment", domain: "assignment", key: key)
                .write(to: path.appendingPathComponent("assignment.json"))
            try product.signed.write(to: path.appendingPathComponent("signed-manifest.json"))
            try product.payload.write(to: path.appendingPathComponent("payload.wasm"))
            try sourceMap.write(to: path.appendingPathComponent("source-map.json"))
        }
    }

    private static func sign(_ value: CanonicalValue, field: String, domain: String,
                             key: Curve25519.Signing.PrivateKey) throws -> Data {
        let signature = try key.signature(for: Data("mixer.\(domain).v3\0".utf8) + value.canonicalCBOR())
        return try encode(CanonicalValue.object([field: value, "signature": .text(signature.base64EncodedString())]))
    }
}

func encode<T: Encodable>(_ value: T) throws -> Data {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
    return try encoder.encode(value)
}

func read(_ folder: URL, _ name: String) throws -> Data {
    try Data(contentsOf: folder.appendingPathComponent(name))
}

func object(_ data: Data) throws -> [String: Any] {
    try need(JSONSerialization.jsonObject(with: data) as? [String: Any], "JSON object")
}

func need<T>(_ value: T?, _ reason: String) throws -> T {
    guard let value else { throw UpdateError("f04.control", reason) }
    return value
}

func check(_ condition: Bool, _ reason: String) throws {
    if !condition { throw UpdateError("f04.control", reason) }
}
