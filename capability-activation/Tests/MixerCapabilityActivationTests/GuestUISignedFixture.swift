import Foundation
import Crypto
import MixerCapabilities
import MixerUpdates
@testable import MixerCapabilityActivation

// TESTONLY signer and installed fixture material; no production trust roots.
// This exercises the real signed ingress, not linked build graph attestation.
struct GuestUISignedFixture {
    let root: URL
    let execution: InstalledCapabilityExecution
    let key: Curve25519.Signing.PrivateKey
    var configuration: CapabilityColdStartConfiguration {
        .init(directory: root.appendingPathComponent("recovery"), channel: "beta", installation: "guest-ui-signed", observationSeconds: 1)
    }
    init(root: URL) throws {
        self.root = root
        key = try .init(rawRepresentation: Data(repeating: 0x53, count: 32))
        func resource(_ name: String) throws -> Data {
            try Data(contentsOf: Bundle.module.url(forResource: name, withExtension: nil, subdirectory: "Fixtures")!)
        }
        let scope = UpdateScope(organization: "material-test", project: "material-test", app: "material-test", environment: "development", platform: "ios")
        let roots = try JSONEncoder().encode([TrustRoot(keyID: "guest-ui-signed-test", publicKey: key.publicKey.rawRepresentation,
            scope: scope, artifact: true, assignment: true, notBeforeUnix: 1, notAfterUnix: UInt64.max)])
        var identity = try JSONSerialization.jsonObject(with: resource("identity.json")) as! [String: Any]
        var build = identity["build"] as! [String: Any]
        build["trust_roots_sha256"] = ReleaseVerifier.sha256(roots); identity["build"] = build
        var mode = identity["execution"] as! [String: Any]
        mode["startup_export"] = "mixer_guest_ui_start_v1"; identity["execution"] = mode
        var dependencies = identity["dependencies"] as! [[String: Any]]
        dependencies.append(["id":"mixer.guest-ui-event-v1", "version":"1", "artifact_sha256":"34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024"])
        dependencies.append(["id":"mixer.guest-ui-native-header-v1", "version":"1", "artifact_sha256":"d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5"])
        identity["dependencies"] = dependencies.sorted { ($0["id"] as! String) < ($1["id"] as! String) }
        let materials: [CapabilityMaterialFile] = [
            .init(role: .bridgePolicy, bytes: try resource("bridge.json")),
            .init(role: .configuration(capabilityID: CapabilitySchemas.httpID), bytes: try resource("http.json")),
            .init(role: .configuration(capabilityID: CapabilitySchemas.storageID), bytes: try resource("storage.json")),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.httpID), bytes: try resource("http-grant.json")),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.storageID), bytes: try resource("storage-grant.json"))]
        execution = try InstalledCapabilityExecution(identityJSON: JSONSerialization.data(withJSONObject: identity, options: [.sortedKeys, .withoutEscapingSlashes]),
            materials: materials, trustRootsJSON: roots, privateContainer: root)
    }
    func documents(_ bytes: Data, sequence: UInt64 = 1, startupMilliseconds: UInt64 = 60_000, storage: Bool = false) throws -> (Data, Data) {
        let host = execution.installed.identity.installedRuntime, s = host.scope
        let scope = CanonicalValue.object(["organization": .text(s.organization), "project": .text(s.project), "app": .text(s.app), "environment": .text(s.environment), "platform": .text(s.platform)])
        let entries: [CanonicalValue] = storage ? [.object(["capability_id": .text(CapabilitySchemas.storageID), "schema_sha256": .text(CapabilitySchemas.storageSHA256),
            "permissions": .array([.text("storage.appPrivate")]), "namespaces": .array([.text("material_test")]), "origins": .array([]), "methods": .array([])])] : []
        let manifest = CanonicalValue.object([
            "schema": .uint(3), "scope": scope, "release_id": .text("guest-ui-signed"), "source_commit": .text(String(repeating: "5", count: 40)),
            "provenance_id": .text("guest-ui-signed-test"), "runtime": .text(host.runtime), "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
            "capability_hashes": .object(host.capabilityHashes.mapValues(CanonicalValue.text)), "state_min": .uint(0), "state_max": .uint(0),
            "payload_sha256": .text(ReleaseVerifier.sha256(bytes)), "compressed_bytes": .uint(UInt64(bytes.count)), "expanded_bytes": .uint(UInt64(bytes.count)),
            "compression": .text("none"), "asset_hashes": .object([:]), "source_map_sha256": .text(String(repeating: "6", count: 64)),
            "limits": .object(["memory_bytes": .uint(65_536), "fuel": .uint(100_000), "startup_milliseconds": .uint(startupMilliseconds)]),
            "key_id": .text("guest-ui-signed-test"), "created_at_unix": .uint(100), "capability_grants": .object(["schema": .uint(1),
                "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array(entries)])])
        let assignment = CanonicalValue.object(["schema": .uint(3), "scope": scope, "channel": .text("beta"), "cohort": .text("sha256-v1"),
            "rollout_basis_points": .uint(10_000), "sequence": .uint(sequence), "release_id": .text("guest-ui-signed"),
            "artifact_sha256": .text(ReleaseVerifier.sha256(try manifest.canonicalCBOR())), "runtime": .text(host.runtime), "key_id": .text("guest-ui-signed-test"), "created_at_unix": .uint(100)])
        func signed(_ value: CanonicalValue, assignment: Bool) throws -> Data {
            let prefix = assignment ? "mixer.assignment.v3\0" : "mixer.artifact.v3\0"
            let signature = try key.signature(for: Data(prefix.utf8) + value.canonicalCBOR())
            return try JSONEncoder().encode(CanonicalValue.object([assignment ? "assignment" : "manifest": value, "signature": .text(signature.base64EncodedString())]))
        }
        return (try signed(manifest, assignment: false) + Data(" \n".utf8), try signed(assignment, assignment: true) + Data("\t".utf8))
    }
}
