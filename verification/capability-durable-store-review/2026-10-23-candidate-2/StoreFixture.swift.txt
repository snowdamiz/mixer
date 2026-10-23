import Foundation
import Crypto
import MixerUpdates
@testable import MixerCapabilityActivation

/// Original review signing context and Wasm. Only the inert installed descriptor
/// and bridge material template are reused as explicitly pinned input files.
struct ReviewStoreFixture {
    let installed: InstalledMaterial
    let payload: Data
    let root: URL
    private let key: Curve25519.Signing.PrivateKey
    init(templates: URL, root: URL) throws {
        self.root = root
        key = try .init(rawRepresentation: Data(repeating: 0x79, count: 32)) // Public TEST ONLY key.
        func uleb(_ value: Int) -> [UInt8] {
            var value = value, out: [UInt8] = []
            repeat { var byte = UInt8(value & 127); value >>= 7; if value != 0 { byte |= 128 }; out.append(byte) } while value != 0
            return out
        }
        func section(_ id: UInt8, _ contents: [UInt8]) -> [UInt8] { [id] + uleb(contents.count) + contents }
        func name(_ value: String) -> [UInt8] { uleb(value.utf8.count) + value.utf8 }
        var wasm: [UInt8] = [0,97,115,109,1,0,0,0]
        wasm += section(1, [1,0x60,0,0])
        wasm += section(3, [2,0,0])
        wasm += section(5, [1,0,0])
        var exports: [UInt8] = [2]
        exports += name("startup") + [0,0]
        exports += name("mixer_guest_capability_ready_v1") + [0,1]
        wasm += section(7, exports)
        wasm += section(10, [2,2,0,0x0b,2,0,0x0b])
        wasm += section(0, [0] + [UInt8](repeating: 0x35, count: 1_048_000))
        payload = Data(wasm)
        var identity = try JSONSerialization.jsonObject(with: Data(contentsOf: templates.appendingPathComponent("identity.json"))) as! [String: Any]
        identity["capabilities"] = []
        let roots = try JSONEncoder().encode([TrustRoot(keyID: "review-root", publicKey: key.publicKey.rawRepresentation,
            scope: .init(organization: "material-test", project: "material-test", app: "material-test", environment: "development", platform: "ios"),
            artifact: true, assignment: true, notBeforeUnix: 1, notAfterUnix: 10_000)])
        var build = identity["build"] as! [String: Any]
        build["trust_roots_sha256"] = ReleaseVerifier.sha256(roots); identity["build"] = build
        let bridge = try Data(contentsOf: templates.appendingPathComponent("bridge.json"))
        let execution = try InstalledCapabilityExecution(identityJSON: JSONSerialization.data(withJSONObject: identity, options: [.sortedKeys, .withoutEscapingSlashes]),
            materials: [.init(role: .bridgePolicy, bytes: bridge)], trustRootsJSON: roots, privateContainer: root)
        installed = execution.installed
    }
    var configuration: CapabilityRecoveryConfiguration { .init(directory: root, channel: "review", installation: "review-installation", reserveDiskBytes: 0) }
    func offer(_ sequence: UInt64) throws -> (Data, Data) {
        let host = installed.identity.installedRuntime
        let scope = try JSONDecoder().decode(CanonicalValue.self, from: JSONEncoder().encode(host.scope))
        let manifest: CanonicalValue = .object([
            "schema": .uint(3), "scope": scope, "release_id": .text("review-\(sequence)"),
            "source_commit": .text(String(repeating: "c", count: 40)), "provenance_id": .text("independent-review"),
            "runtime": .text(host.runtime), "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
            "capability_hashes": .object([:]), "capability_grants": .object([
                "schema": .uint(1), "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array([])]),
            "state_min": .uint(host.stateVersion), "state_max": .uint(host.stateVersion),
            "payload_sha256": .text(ReleaseVerifier.sha256(payload)), "compressed_bytes": .uint(UInt64(payload.count)),
            "expanded_bytes": .uint(UInt64(payload.count)), "compression": .text("none"), "asset_hashes": .object([:]),
            "source_map_sha256": .text(ReleaseVerifier.sha256(Data())), "limits": .object([
                "memory_bytes": .uint(1), "fuel": .uint(10_000), "startup_milliseconds": .uint(60_000)]),
            "key_id": .text("review-root"), "created_at_unix": .uint(10)])
        let assignment: CanonicalValue = .object([
            "schema": .uint(3), "scope": scope, "channel": .text("review"), "cohort": .text("sha256-v1"),
            "rollout_basis_points": .uint(10_000), "sequence": .uint(sequence), "release_id": .text("review-\(sequence)"),
            "artifact_sha256": .text(ReleaseVerifier.sha256(try manifest.canonicalCBOR())), "runtime": .text(host.runtime),
            "key_id": .text("review-root"), "created_at_unix": .uint(10)])
        func envelope(_ body: CanonicalValue, _ kind: String) throws -> Data {
            let signature = try key.signature(for: Data(("mixer.\(kind).v3\0").utf8) + body.canonicalCBOR())
            let name = kind == "artifact" ? "manifest" : "assignment"
            return try JSONEncoder().encode(CanonicalValue.object([name: body, "signature": .text(signature.base64EncodedString())]))
        }
        return (try envelope(manifest, "artifact") + Data(" \n\t".utf8), try envelope(assignment, "assignment") + Data("\r\n ".utf8))
    }
}

func reviewRequire(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    guard condition() else { throw UpdateError("review.failure", message) }
}
