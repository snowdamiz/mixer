import CryptoKit
import Foundation
import MixerRuntimeIdentity
import MixerUpdates

enum AppleCommitMaterial {
    static func sign(fixtures: URL, guest: URL, output: URL, engineHash: String,
                     sourceHash: String, linkHash: String, revision: String, metadata: URL, draftTools: Bool = false,
                     authorityControl: Bool = false) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        func read(_ name: String) throws -> Data {
            try Data(contentsOf: fixtures.appendingPathComponent(name))
        }
        func write(_ name: String, _ data: Data) throws {
            try data.write(to: output.appendingPathComponent(name), options: .withoutOverwriting)
        }
        let key = Curve25519.Signing.PrivateKey()
        let keyID = draftTools ? "fieldlog-ios-draft-tools-local" : "fieldlog-ios-entry-commit-local"
        let scope = UpdateScope(organization: "mixer-local", project: "fieldlog", app: "fieldlog",
                                environment: "development", platform: "ios")
        let roots = [TrustRoot(keyID: keyID, publicKey: key.publicKey.rawRepresentation, scope: scope,
                               artifact: true, assignment: true, notBeforeUnix: 1)]
        let rootsBytes = try encoder.encode(roots)
        let scopeValue = try StrictJSON.decode(CanonicalValue.self, from: encoder.encode(scope))
        let storageID = "storage.keyValue.v1"
        let provenance = try StrictJSON.decode(CanonicalValue.self, from: Data(contentsOf: metadata)).object
        guard let toolchain = provenance?["toolchain"],
              let settings = provenance?["settings_sha256"],
              let fallback = provenance?["native_fallback_sha256"],
              var identity = try StrictJSON.decode(CanonicalValue.self, from: read("identity.json")).object,
              var application = scopeValue.object, var build = identity["build"]?.object,
              var engine = identity["engine"]?.object, var mode = identity["execution"]?.object,
              var limits = identity["capability_execution"]?.object,
              case .array(let capabilities)? = identity["capabilities"],
              var storage = capabilities.first(where: { $0.object?["id"]?.text == storageID })?.object,
              var grant = try StrictJSON.decode(CanonicalValue.self, from: read("storage-grant.json")).object
        else { throw UpdateError("fixture.material", "Incomplete installed capability template") }
        grant["namespaces"] = .array([.text("fieldlog-task-v1")])
        let grantValue = CanonicalValue.object(grant)
        let grantBytes = try encoder.encode(grantValue) + Data([10])
        storage["grants_sha256"] = .text(ReleaseVerifier.sha256(grantBytes))
        let http = capabilities.filter { $0.object?["id"]?.text == "network.http.v1" }
        identity["capabilities"] = .array(draftTools ? http + [.object(storage)] : [.object(storage)])
        application.removeValue(forKey: "platform")
        application["bundle_id"] = .text("dev.mixer.fieldlog")
        identity["application"] = .object(application)
        identity["platform"] = .object(["os": .text("ios"), "architecture": .text("arm64"),
            "environment": .text("simulator"), "minimum_os": .text("26.0"),
            "target": .text("arm64-apple-ios26.0-simulator")])
        build["trust_roots_sha256"] = .text(ReleaseVerifier.sha256(rootsBytes))
        build["link_inputs_sha256"] = .text(linkHash)
        build["settings_sha256"] = settings
        build["native_fallback_sha256"] = fallback
        build["entitlements_sha256"] = .text(ReleaseVerifier.sha256(Data("{}".utf8)))
        build["permissions_sha256"] = .text(ReleaseVerifier.sha256(Data("local debug, no application entitlements".utf8)))
        build["resource_policy_sha256"] = .text(ReleaseVerifier.sha256(try read("bridge.json")))
        identity["build"] = .object(build)
        identity["toolchain"] = toolchain
        engine["artifact_sha256"] = .text(engineHash)
        engine["source_sha256"] = .text(sourceHash)
        engine["version"] = .text(revision)
        identity["engine"] = .object(engine)
        mode["startup_export"] = .text("mixer_guest_ui_start_v1")
        identity["execution"] = .object(mode)
        if !draftTools {
            limits["maximum_requests"] = .uint(authorityControl ? 4 : 2)
            limits["reservation_bytes"] = .uint(authorityControl ? 4_194_304 : 2_097_152)
        }
        identity["capability_execution"] = .object(limits)
        func dependency(_ id: String, _ hash: String) -> CanonicalValue {
            .object(["id": .text(id), "version": .text("1"), "artifact_sha256": .text(hash)])
        }
        let guestUI = [
            dependency("mixer.guest-ui-event-v1", "34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024"),
            dependency("mixer.guest-ui-native-header-v1", "d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5"),
        ]
        identity["dependencies"] = .array(draftTools ? [
            dependency("mixer.guest-ui-deferred-startup-v1",
                "cdc8e301305ecfd6abe40872df55d90dce86ea816781904c45d1fa119d2da260"),
        ] + guestUI : guestUI)
        let identityBytes = try encoder.encode(CanonicalValue.object(identity))
        let host = try CapabilityRuntimeIdentity(json: identityBytes).installedRuntime
        let verifier = try ReleaseVerifierV3(host: host, roots: roots)
        let created = UInt64(Date().timeIntervalSince1970)
        let variants = draftTools ? Array(InstalledDraftGuest.variants.prefix(3)) : ["entry-commit"]
        let grants = try draftTools ? [
            StrictJSON.decode(CanonicalValue.self, from: read("http-grant.json")), grantValue
        ] : [grantValue]
        func signed(_ value: CanonicalValue, _ field: String, _ domain: String) throws -> Data {
            let signature = try key.signature(for: Data("mixer.\(domain).v3\0".utf8) + value.canonicalCBOR())
            return try encoder.encode(CanonicalValue.object([
                field: value, "signature": .text(signature.base64EncodedString()),
            ]))
        }
        for (index, variant) in variants.enumerated() {
            let payload = try Data(contentsOf: draftTools ? guest.appendingPathComponent("\(variant).wasm") : guest)
            let size = CanonicalValue.uint(UInt64(payload.count))
            let release = "fieldlog-ios-\(variant)"
            let manifest = CanonicalValue.object([
                "schema": .uint(3), "scope": scopeValue, "release_id": .text(release),
                "source_commit": .text(revision),
                "provenance_id": .text("fieldlog-ios-local-" + String(linkHash.prefix(24))),
                "runtime": .text(host.runtime), "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
                "capability_hashes": .object(host.capabilityHashes.mapValues(CanonicalValue.text)),
                "state_min": .uint(0), "state_max": .uint(0), "payload_sha256": .text(ReleaseVerifier.sha256(payload)),
                "compressed_bytes": size, "expanded_bytes": size, "compression": .text("none"),
                "asset_hashes": .object([:]), "source_map_sha256": .text(ReleaseVerifier.sha256(Data("{}".utf8))),
                "limits": .object(["memory_bytes": .uint(65_536), "fuel": .uint(host.limits.fuel),
                                   "startup_milliseconds": .uint(5_000)]),
                "key_id": .text(keyID), "created_at_unix": .uint(created),
                "capability_grants": .object(["schema": .uint(1),
                    "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array(grants)]),
            ])
            let manifestBytes = try signed(manifest, "manifest", "artifact")
            let artifact = try verifier.verifyArtifact(signedManifest: manifestBytes, payload: payload, now: created)
            let assignment = try signed(.object([
                "schema": .uint(3), "scope": scopeValue, "channel": .text("beta"), "cohort": .text("sha256-v1"),
                "rollout_basis_points": .uint(10_000), "sequence": .uint(UInt64(index + 1)), "release_id": .text(release),
                "artifact_sha256": .text(ReleaseVerifier.sha256(try manifest.canonicalCBOR())),
                "runtime": .text(host.runtime), "key_id": .text(keyID), "created_at_unix": .uint(created),
            ]), "assignment", "assignment")
            _ = try verifier.verifyAssignment(signedAssignment: assignment, artifact: artifact, channel: "beta",
                installation: "fieldlog-ios-local", lastSequence: UInt64(index), now: created)
            try write("\(variant).manifest.json", manifestBytes)
            try write(draftTools ? "sequence-\(index + 1).assignment.json" : "entry-commit.assignment.json", assignment)
            try write("\(variant).wasm", payload)
            print("signedRuntime=\(host.runtime) engine=\(engineHash) variant=\(variant) payload=\(ReleaseVerifier.sha256(payload))")
        }
        for (name, data) in [
            ("identity.json", identityBytes), ("roots.json", rootsBytes),
            ("bridge.json", try read("bridge.json")), ("storage.json", try read("storage.json")),
            ("storage-grant.json", grantBytes),
        ] {
            try write(name, data)
        }
        if draftTools {
            for name in ["http.json", "http-grant.json"] { try write(name, read(name)) }
        }
    }
}
