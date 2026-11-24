import Crypto
import Foundation
import MixerCapabilities
import MixerRuntimeIdentity
import MixerUpdates

struct LocalReleases {
    struct Release {
        let id: String
        let bytes: Data
        let manifest: Data
        let manifestDigest: String
    }

    static let channel = "beta"
    static let namespace = "material_test"
    private static let keyID = "s5-disposable-development"
    private static let scope = UpdateScope(organization: "mixer-local", project: "s5", app: "signed-compose-v2",
                                           environment: "development", platform: "android")
    private let key = Curve25519.Signing.PrivateKey()
    private let encoder = JSONEncoder()
    private let created = UInt64(Date().timeIntervalSince1970)
    let identity: Data
    let roots: Data
    private let scopeValue: CanonicalValue
    private let runtime: InstalledRuntime
    private let grant: CanonicalValue
    private let sourceCommit: String

    init(templates: URL, sourceCommit: String, vm: String, binary: String) throws {
        self.sourceCommit = sourceCommit
        func read(_ name: String) throws -> Data {
            try Data(contentsOf: templates.appendingPathComponent(name))
        }
        scopeValue = try StrictJSON.decode(CanonicalValue.self, from: encoder.encode(Self.scope))
        roots = try encoder.encode([TrustRoot(keyID: Self.keyID, publicKey: key.publicKey.rawRepresentation,
            scope: Self.scope, artifact: true, assignment: true, notBeforeUnix: created - 1,
            notAfterUnix: created + 86_400)])
        let grantBytes = try read("storage-grant.json")
        grant = try StrictJSON.decode(CanonicalValue.self, from: grantBytes)
        guard var template = try StrictJSON.decode(CanonicalValue.self, from: read("identity.json")).object,
              var build = template["build"]?.object, var engine = template["engine"]?.object,
              var execution = template["execution"]?.object, var application = scopeValue.object,
              case let .array(capabilities)? = template["capabilities"],
              let storage = capabilities.first(where: { $0.object?["id"]?.text == CapabilitySchemas.storageID })
        else { throw FixtureError("Missing installed identity template material") }
        application.removeValue(forKey: "platform")
        application["bundle_id"] = .text("dev.mixer.compose.s5.signed.v2")
        template["application"] = .object(application)
        template["platform"] = .object(["os": .text("android"), "architecture": .text("arm64"),
            "environment": .text("device"), "minimum_os": .text("28"), "target": .text("aarch64-unknown-linux-android28")])
        template["capabilities"] = .array([storage])
        build["trust_roots_sha256"] = .text(ReleaseVerifier.sha256(roots))
        build["link_inputs_sha256"] = .text(binary)
        template["build"] = .object(build)
        engine["artifact_sha256"] = .text(vm)
        engine["version"] = .text("s5-signed-compose-v2-development")
        template["engine"] = .object(engine)
        execution["startup_export"] = .text("mixer_guest_ui_start_v2")
        template["execution"] = .object(execution)
        template["dependencies"] = .array([
            Self.dependency("mixer.guest-ui-event-v2", "0dfb6a99a9d06235739f5735c32d39ee1494147bedafc88bba49bbb7d3b48106"),
            Self.dependency("mixer.guest-ui-native-header-v2", "be7ebb2da4836351c54b7f431a34722c35aed5ef003e806cd5b0607d48b54ea0"),
        ])
        identity = try encoder.encode(CanonicalValue.object(template))
        runtime = try CapabilityRuntimeIdentity(json: identity).installedRuntime
    }

    func release(_ variant: String, at guests: URL) throws -> Release {
        let bytes = try Data(contentsOf: guests.appendingPathComponent(variant + ".wasm"))
        let id = "s5-" + variant
        let length = CanonicalValue.uint(UInt64(bytes.count))
        let manifest = CanonicalValue.object([
            "schema": .uint(3), "scope": scopeValue, "release_id": .text(id), "source_commit": .text(sourceCommit),
            "provenance_id": .text("s5-local-development"), "runtime": .text(runtime.runtime), "protocol": .uint(3),
            "guest_abi": .uint(2), "ui_schema": .uint(runtime.uiSchema),
            "capability_hashes": .object(runtime.capabilityHashes.mapValues(CanonicalValue.text)),
            "state_min": .uint(0), "state_max": .uint(0), "payload_sha256": .text(ReleaseVerifier.sha256(bytes)),
            "compressed_bytes": length, "expanded_bytes": length, "compression": .text("none"), "asset_hashes": .object([:]),
            "source_map_sha256": .text(ReleaseVerifier.sha256(Data("{}".utf8))),
            "limits": .object(["memory_bytes": .uint(1_179_648), "fuel": .uint(runtime.limits.fuel),
                               "startup_milliseconds": .uint(10_000)]),
            "key_id": .text(Self.keyID), "created_at_unix": .uint(created),
            "capability_grants": .object(["schema": .uint(1),
                "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array([grant])]),
        ])
        return .init(id: id, bytes: bytes, manifest: try signed(manifest, field: "manifest", domain: "artifact"),
                     manifestDigest: ReleaseVerifier.sha256(try manifest.canonicalCBOR()))
    }

    func assignment(_ release: Release, sequence: UInt64) throws -> Data {
        let assignment = CanonicalValue.object([
            "schema": .uint(3), "scope": scopeValue, "channel": .text(Self.channel), "cohort": .text("sha256-v1"),
            "rollout_basis_points": .uint(10_000), "sequence": .uint(sequence),
            "release_id": .text(release.id), "artifact_sha256": .text(release.manifestDigest),
            "runtime": .text(runtime.runtime), "key_id": .text(Self.keyID), "created_at_unix": .uint(created),
        ])
        return try signed(assignment, field: "assignment", domain: "assignment")
    }

    private func signed(_ value: CanonicalValue, field: String, domain: String) throws -> Data {
        let signature = try key.signature(for: Data("mixer.\(domain).v3\0".utf8) + value.canonicalCBOR())
        return try encoder.encode(CanonicalValue.object([field: value, "signature": .text(signature.base64EncodedString())]))
    }

    private static func dependency(_ id: String, _ hash: String) -> CanonicalValue {
        .object(["id": .text(id), "version": .text("2"), "artifact_sha256": .text(hash)])
    }
}

private struct FixtureError: Error {
    let message: String
    init(_ message: String) { self.message = message }
}

@main enum SignFixture {
    static func main() throws {
        let args = CommandLine.arguments
        guard args.count == 7 else { throw FixtureError("Expected templates, guests, output, source commit, VM and link digests") }
        let templates = URL(fileURLWithPath: args[1], isDirectory: true)
        let guests = URL(fileURLWithPath: args[2], isDirectory: true)
        let out = URL(fileURLWithPath: args[3], isDirectory: true)
        let signer = try LocalReleases(templates: templates, sourceCommit: args[4], vm: args[5], binary: args[6])
        try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
        func write(_ name: String, _ bytes: Data) throws { try bytes.write(to: out.appendingPathComponent(name)) }
        try write("identity.json", signer.identity)
        try write("roots.json", signer.roots)
        for name in ["bridge.json", "storage.json", "storage-grant.json"] {
            try FileManager.default.copyItem(at: templates.appendingPathComponent(name), to: out.appendingPathComponent(name))
        }
        let prior = try signer.release("prior", at: guests)
        let candidate = try signer.release("candidate", at: guests)
        for (name, release, sequence): (String, LocalReleases.Release, UInt64) in
            [("prior", prior, 1), ("candidate", candidate, 2), ("rollback", prior, 3)] {
            try write(name + ".manifest", release.manifest)
            try write(name + ".assignment", signer.assignment(release, sequence: sequence))
            if name != "rollback" { try write(name + ".wasm", release.bytes) }
        }
    }
}
