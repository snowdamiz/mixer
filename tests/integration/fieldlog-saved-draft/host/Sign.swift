import Crypto
import Foundation
import MixerCapabilities
#if FIELDLOG_ENTRY_SAVE_REPLAY
import FieldLogInstalledGuest
#else
import FieldLogDraftIntegration
#endif
import MixerRuntimeIdentity
import MixerUpdates

// All documents are scoped to this local replay. The signing key stays in memory.
func signReleases(fixtures: URL, guests: URL, output: URL, archive: String, binary: String,
                  variants: [String] = Host.variants, deferredStartup: Bool = true,
                  limits: (requests: UInt64, reservationBytes: UInt64)? = nil,
                  storageOnly: Bool = false, sourceCommit: String = Host.fieldLogRevision) throws {
    let key = Curve25519.Signing.PrivateKey()
    let keyID = "fieldlog-saved-draft-development"
    let scope = UpdateScope(organization: "mixer-local", project: "fieldlog", app: "fieldlog",
                            environment: "development", platform: "android")
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
    let scopeValue = try StrictJSON.decode(CanonicalValue.self, from: encoder.encode(scope))
    let roots = try encoder.encode([TrustRoot(keyID: keyID, publicKey: key.publicKey.rawRepresentation,
        scope: scope, artifact: true, assignment: true, notBeforeUnix: 1)])
    func write(_ name: String, _ bytes: Data) throws {
        try bytes.write(to: output.appendingPathComponent(name), options: .withoutOverwriting)
    }
    func signed(_ name: String, field: String, domain: String, value: CanonicalValue) throws {
        let signature = try key.signature(for: Data("mixer.\(domain).v3\0".utf8) + value.canonicalCBOR())
        try write(name, encoder.encode(CanonicalValue.object([field: value, "signature": .text(signature.base64EncodedString())])))
    }

    guard var identity = try StrictJSON.decode(CanonicalValue.self, from: Trial.read(fixtures, "identity.json")).object,
          var build = identity["build"]?.object, var engine = identity["engine"]?.object,
          var mode = identity["execution"]?.object, case .array(let capabilities)? = identity["capabilities"],
          var grant = try StrictJSON.decode(CanonicalValue.self, from: Trial.read(fixtures, "storage-grant.json")).object
    else { throw TrialError("Incomplete installed material template") }
    grant["namespaces"] = .array([.text(FieldLogDraftStorage.namespace)])
    let grantValue = CanonicalValue.object(grant)
    let grantBytes = try encoder.encode(grantValue) + Data([10])
    var httpConfiguration = try Trial.read(fixtures, "http.json")
    if let limits {
        guard var policy = identity["capability_execution"]?.object,
              var http = try StrictJSON.decode(CanonicalValue.self, from: httpConfiguration).object else {
            throw TrialError("Incomplete capability limits template")
        }
        policy["maximum_requests"] = .uint(limits.requests)
        policy["reservation_bytes"] = .uint(limits.reservationBytes)
        identity["capability_execution"] = .object(policy)
        http["maximum_concurrent_requests"] = .uint(limits.requests)
        httpConfiguration = try encoder.encode(CanonicalValue.object(http)) + Data([10])
    }
    let installedCapabilities = storageOnly ? capabilities.filter { $0.object?["id"]?.text == CapabilitySchemas.storageID } : capabilities
    identity["capabilities"] = .array(installedCapabilities.map {
        guard var capability = $0.object else { return $0 }
        switch capability["id"]?.text {
        case CapabilitySchemas.storageID:
            capability["grants_sha256"] = .text(ReleaseVerifier.sha256(grantBytes))
        case CapabilitySchemas.httpID:
            capability["configuration_sha256"] = .text(ReleaseVerifier.sha256(httpConfiguration))
        default: break
        }
        return .object(capability)
    })
    guard var application = scopeValue.object else { throw TrialError("Invalid test scope") }
    application.removeValue(forKey: "platform")
    application["bundle_id"] = .text("dev.mixer.fieldlog.saveddraft")
    identity["application"] = .object(application)
    identity["platform"] = .object(["os": .text("android"), "architecture": .text("arm64"),
        "environment": .text("device"), "minimum_os": .text("28"), "target": .text("aarch64-unknown-linux-android28")])
    build["trust_roots_sha256"] = .text(ReleaseVerifier.sha256(roots))
    build["link_inputs_sha256"] = .text(binary)
    identity["build"] = .object(build)
    engine["artifact_sha256"] = .text(archive)
    engine["version"] = .text("fieldlog-saved-draft-host")
    identity["engine"] = .object(engine)
    mode["startup_export"] = .text("mixer_guest_ui_start_v1")
    identity["execution"] = .object(mode)
    let guestUI = [
        dependency("mixer.guest-ui-event-v1", "34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024"),
        dependency("mixer.guest-ui-native-header-v1", "d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5"),
    ]
    identity["dependencies"] = .array(deferredStartup ? [
        dependency("mixer.guest-ui-deferred-startup-v1", "cdc8e301305ecfd6abe40872df55d90dce86ea816781904c45d1fa119d2da260"),
    ] + guestUI : guestUI)
    let identityBytes = try encoder.encode(CanonicalValue.object(identity))
    let host = try CapabilityRuntimeIdentity(json: identityBytes).installedRuntime
    try write("identity.json", identityBytes)
    try write("roots.json", roots)
    try write("storage-grant.json", grantBytes)
    if !storageOnly { try write("http.json", httpConfiguration) }
    for name in Trial.materials.map(\.0)
        where name != "storage-grant.json" && name != "http.json" && (!storageOnly || name != "http-grant.json") {
        try write(name, Trial.read(fixtures, name))
    }

    let created = UInt64(Date().timeIntervalSince1970)
    let sourceMap = Data("{}".utf8)
    var digests: [String: String] = [:]
    for variant in Set(variants).sorted() {
        let payload = try Trial.read(guests, variant + ".wasm")
        let length = CanonicalValue.uint(UInt64(payload.count))
        let manifest = CanonicalValue.object([
            "schema": .uint(3), "scope": scopeValue, "release_id": .text("fieldlog-draft-" + variant),
            "source_commit": .text(sourceCommit), "provenance_id": .text("fieldlog-local-" + String(binary.prefix(24))),
            "runtime": .text(host.runtime), "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
            "capability_hashes": .object(host.capabilityHashes.mapValues(CanonicalValue.text)),
            "state_min": .uint(0), "state_max": .uint(0), "payload_sha256": .text(ReleaseVerifier.sha256(payload)),
            "compressed_bytes": length, "expanded_bytes": length, "compression": .text("none"),
            "asset_hashes": .object([:]), "source_map_sha256": .text(ReleaseVerifier.sha256(sourceMap)),
            "limits": .object(["memory_bytes": .uint(65536), "fuel": .uint(host.limits.fuel),
                               "startup_milliseconds": .uint(5000)]),
            "key_id": .text(keyID), "created_at_unix": .uint(created),
            "capability_grants": .object(["schema": .uint(1),
                "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array([grantValue])]),
        ])
        digests[variant] = ReleaseVerifier.sha256(try manifest.canonicalCBOR())
        try signed(variant + ".manifest.json", field: "manifest", domain: "artifact", value: manifest)
        try write(variant + ".wasm", payload)
    }
    for (index, variant) in variants.enumerated() {
        guard let digest = digests[variant] else { throw TrialError("Missing release digest") }
        let assignment = CanonicalValue.object([
            "schema": .uint(3), "scope": scopeValue, "channel": .text(Trial.channel), "cohort": .text("sha256-v1"),
            "rollout_basis_points": .uint(10000), "sequence": .uint(UInt64(index + 1)),
            "release_id": .text("fieldlog-draft-" + variant), "artifact_sha256": .text(digest),
            "runtime": .text(host.runtime), "key_id": .text(keyID), "created_at_unix": .uint(created),
        ])
        try signed("sequence-\(index + 1).assignment.json", field: "assignment", domain: "assignment", value: assignment)
    }
}

private func dependency(_ id: String, _ digest: String) -> CanonicalValue {
    .object(["id": .text(id), "version": .text("1"), "artifact_sha256": .text(digest)])
}
