import CryptoKit
import Foundation
import MixerCapabilities
import MixerCapabilityActivation
import MixerRuntimeIdentity
import MixerUpdates

struct S4SignedFixture {
    let execution: InstalledCapabilityExecution
    let configuration: CapabilityColdStartConfiguration
    let root: URL
    private let host: InstalledRuntime
    private let key: Curve25519.Signing.PrivateKey

    init(root: URL) throws {
        self.root = root
        configuration = .init(directory: root.appendingPathComponent("recovery"), channel: "beta",
                              installation: "s4-ios-native", observationSeconds: 1)
        // Matches the original TESTONLY host fixture. All signatures are development fixtures.
        key = try .init(rawRepresentation: Data(repeating: 0x53, count: 32))
        let scope = UpdateScope(organization: "material-test", project: "material-test", app: "material-test",
                                environment: "development", platform: "ios")
        let roots = try Self.encoder().encode([TrustRoot(keyID: "s4-native-test", publicKey: key.publicKey.rawRepresentation,
            scope: scope, artifact: true, assignment: true, notBeforeUnix: 1, notAfterUnix: UInt64.max)])
        func resource(_ name: String) throws -> Data {
            let directory = try require(Bundle.main.resourceURL, "bundle resources")
            return try Data(contentsOf: directory.appendingPathComponent("Fixtures").appendingPathComponent(name))
        }
        var fields = try require(StrictJSON.decode(CanonicalValue.self, from: resource("identity.json")).object, "identity")
        var build = try require(fields["build"]?.object, "build")
        build["trust_roots_sha256"] = .text(ReleaseVerifier.sha256(roots))
        fields["build"] = .object(build)
        let identity = try Self.encoder().encode(CanonicalValue.object(fields))
        host = try CapabilityRuntimeIdentity(json: identity).installedRuntime
        let materials: [CapabilityMaterialFile] = [
            .init(role: .bridgePolicy, bytes: try resource("bridge.json")),
            .init(role: .configuration(capabilityID: CapabilitySchemas.httpID), bytes: try resource("http.json")),
            .init(role: .configuration(capabilityID: CapabilitySchemas.storageID), bytes: try resource("storage.json")),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.httpID), bytes: try resource("http-grant.json")),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.storageID), bytes: try resource("storage-grant.json")),
        ]
        execution = try InstalledCapabilityExecution(identityJSON: identity, materials: materials,
                                                      trustRootsJSON: roots, privateContainer: root)
    }

    func offer(_ bytes: Data, sequence: UInt64) throws -> (manifest: Data, assignment: Data) {
        let scope = try StrictJSON.decode(CanonicalValue.self, from: Self.encoder().encode(host.scope))
        let created = UInt64(100)
        let manifest = CanonicalValue.object([
            "schema": .uint(3), "scope": scope, "release_id": .text("s4-native"),
            "source_commit": .text("692f05cd2d31f218ae9b3cef7253a4e7397f8e17"),
            "provenance_id": .text("s4-native-test"), "runtime": .text(host.runtime), "protocol": .uint(3),
            "guest_abi": .uint(2), "ui_schema": .uint(host.uiSchema),
            "capability_hashes": .object(host.capabilityHashes.mapValues(CanonicalValue.text)),
            "state_min": .uint(0), "state_max": .uint(0), "payload_sha256": .text(ReleaseVerifier.sha256(bytes)),
            "compressed_bytes": .uint(UInt64(bytes.count)), "expanded_bytes": .uint(UInt64(bytes.count)),
            "compression": .text("none"), "asset_hashes": .object([:]),
            "source_map_sha256": .text(ReleaseVerifier.sha256(Data("{}".utf8))),
            "limits": .object(["memory_bytes": .uint(65_536), "fuel": .uint(100_000), "startup_milliseconds": .uint(60_000)]),
            "key_id": .text("s4-native-test"), "created_at_unix": .uint(created),
            "capability_grants": .object(["schema": .uint(1),
                "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256),
                "entries": .array([.object([
                    "capability_id": .text(CapabilitySchemas.storageID), "schema_sha256": .text(CapabilitySchemas.storageSHA256),
                    "permissions": .array([.text("storage.appPrivate")]), "namespaces": .array([.text("material_test")]),
                    "origins": .array([]), "methods": .array([])
                ])])])
        ])
        let assignment = CanonicalValue.object([
            "schema": .uint(3), "scope": scope, "channel": .text("beta"), "cohort": .text("sha256-v1"),
            "rollout_basis_points": .uint(10_000), "sequence": .uint(sequence), "release_id": .text("s4-native"),
            "artifact_sha256": .text(ReleaseVerifier.sha256(try manifest.canonicalCBOR())), "runtime": .text(host.runtime),
            "key_id": .text("s4-native-test"), "created_at_unix": .uint(created)
        ])
        func sign(_ body: CanonicalValue, domain: String, field: String) throws -> Data {
            let signature = try key.signature(for: Data("mixer.\(domain).v3\0".utf8) + body.canonicalCBOR())
            return try Self.encoder().encode(CanonicalValue.object([field: body, "signature": .text(signature.base64EncodedString())]))
        }
        return (try sign(manifest, domain: "artifact", field: "manifest"),
                try sign(assignment, domain: "assignment", field: "assignment"))
    }

    private static func encoder() -> JSONEncoder {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return encoder
    }

    // Read the fixture's known storage file while the owner holds the store lock.
    // These are the base32 filenames for the signed material_test/binary grant.
    func liveSavedValue() throws -> String {
        let value = root.appendingPathComponent("material_test/v1-nvqxizlsnfqwyx3umvzxi/v1-mjuw4ylspe")
        do { return try Data(contentsOf: value).base64EncodedString() }
        catch let error as CocoaError where error.code == .fileReadNoSuchFile { return "empty" }
    }

    func savedValue() async throws -> String {
        let reader = try AppPrivateKeyValueStore(directory: root.appendingPathComponent("material_test"),
                                                namespaces: ["material_test"])
        do {
            let value = try await reader.get(.init(namespace: "material_test", key: "binary"))
            await reader.close()
            return value.found ? value.valueBase64 : "empty"
        } catch {
            await reader.close()
            throw error
        }
    }
}

func require<T>(_ value: T?, _ description: String) throws -> T {
    guard let value else { throw UpdateError("s4.fixture", "Missing \(description)") }
    return value
}

func check(_ condition: Bool, _ description: String) throws {
    guard condition else { throw UpdateError("s4.fixture", description) }
}
