import Foundation
import Crypto
import MixerUpdates
@testable import MixerCapabilityActivation

private struct Failed: Error { let reason: String }
private func need(_ value: @autoclosure () -> Bool, _ reason: String) throws { if !value() { throw Failed(reason: reason) } }
@main struct Review {
    static func main() async throws {
        let fixtureDirectory = URL(fileURLWithPath: CommandLine.arguments[1])
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-independent-concrete-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        let key = try Curve25519.Signing.PrivateKey(rawRepresentation: Data(repeating: 0x79, count: 32)) // Public TESTONLY fixture.
        var json = try JSONSerialization.jsonObject(with: Data(contentsOf: fixtureDirectory.appendingPathComponent("identity.json"))) as! [String: Any]
        json["capabilities"] = []
        let roots = try JSONEncoder().encode([TrustRoot(keyID: "independent", publicKey: key.publicKey.rawRepresentation,
            scope: .init(organization: "material-test", project: "material-test", app: "material-test", environment: "development", platform: "ios"),
            artifact: true, assignment: true, notBeforeUnix: 1, notAfterUnix: 2000)])
        var build = json["build"] as! [String: Any]; build["trust_roots_sha256"] = ReleaseVerifier.sha256(roots); json["build"] = build
        let bridge = try Data(contentsOf: fixtureDirectory.appendingPathComponent("bridge.json"))
        let material = try InstalledCapabilityExecution(identityJSON: JSONSerialization.data(withJSONObject: json, options: [.sortedKeys, .withoutEscapingSlashes]),
            materials: [.init(role: .bridgePolicy, bytes: bridge)], trustRootsJSON: roots, privateContainer: parent).installed
        // Original tiny binary: two defined empty void functions, exact startup
        // and wake exports, no imports. This tests ownership, not native I/O.
        func n(_ s: String) -> [UInt8] { [UInt8(s.utf8.count)] + Array(s.utf8) }
        func section(_ id: UInt8, _ b: [UInt8]) -> [UInt8] { [id, UInt8(b.count)] + b }
        var exports = [UInt8(2)] + n("startup"); exports += [0,0]
        exports += n("mixer_guest_capability_ready_v1"); exports += [0,1]
        var wasm: [UInt8] = [0,97,115,109,1,0,0,0]
        wasm += section(1,[1,0x60,0,0]); wasm += section(3,[2,0,0]); wasm += section(5,[1,0,0])
        wasm += section(7,exports); wasm += section(10,[2,2,0,0x0b,2,0,0x0b])
        let payload = Data(wasm), host = material.identity.installedRuntime, s = host.scope
        let scope = CanonicalValue.object(["organization": .text(s.organization), "project": .text(s.project), "app": .text(s.app), "environment": .text(s.environment), "platform": .text(s.platform)])
        let manifest = CanonicalValue.object(["schema": .uint(3), "scope": scope, "release_id": .text("independent"), "source_commit": .text(String(repeating: "f", count: 40)),
            "provenance_id": .text("independent"), "runtime": .text(host.runtime), "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
            "capability_hashes": .object([:]), "state_min": .uint(0), "state_max": .uint(0), "payload_sha256": .text(ReleaseVerifier.sha256(payload)),
            "compressed_bytes": .uint(UInt64(payload.count)), "expanded_bytes": .uint(UInt64(payload.count)), "compression": .text("none"), "asset_hashes": .object([:]),
            "source_map_sha256": .text(String(repeating: "e", count: 64)), "limits": .object(["memory_bytes": .uint(65_536), "fuel": .uint(1000), "startup_milliseconds": .uint(60_000)]),
            "key_id": .text("independent"), "created_at_unix": .uint(100), "capability_grants": .object(["schema": .uint(1), "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array([])])])
        let assignment = CanonicalValue.object(["schema": .uint(3), "scope": scope, "channel": .text("beta"), "cohort": .text("sha256-v1"), "rollout_basis_points": .uint(10_000),
            "sequence": .uint(1), "release_id": .text("independent"), "artifact_sha256": .text(ReleaseVerifier.sha256(try manifest.canonicalCBOR())), "runtime": .text(host.runtime), "key_id": .text("independent"), "created_at_unix": .uint(100)])
        func signed(_ value: CanonicalValue, _ assignment: Bool) throws -> Data {
            let domain = assignment ? "mixer.assignment.v3\0" : "mixer.artifact.v3\0"
            let signature = try key.signature(for: Data(domain.utf8) + value.canonicalCBOR())
            return try JSONEncoder().encode(CanonicalValue.object([assignment ? "assignment" : "manifest": value, "signature": .text(signature.base64EncodedString())]))
        }
        let baseline = CapabilityAttemptReservation.occupiedSlots
        for iteration in 0..<8 {
            let owner = try CapabilityAttemptReservation.acquire()
            let directory = parent.appendingPathComponent("recovery-\(iteration)")
            let store = try await CapabilityRecoveryStore.open(admission: owner.issueStoreAdmission(), installed: material,
                configuration: .init(directory: directory, channel: "beta", installation: "independent"), environment: .init(wall: { 1000 }))
            try await store.beginDownload(signedManifest: signed(manifest,false), signedAssignment: signed(assignment,true))
            try await store.appendDownload(payload, atOffset: 0); try await store.finishDownload()
            guard let selected = try await store.prepareStartupSelection() else { throw Failed(reason: "No actual signed native selection") }
            let signals = CapabilityAttemptSignals(generation: selected.generation)
            let input = try await store.consume(selected, signals: signals)
            var attempt: CapabilityConcreteAttempt? = try CapabilityConcreteAttempt(consumed: input, installed: material, reservation: owner, signals: signals)
            weak var weakAttempt = attempt
            try await attempt!.construct(); _ = try await attempt!.startup()
            let token = attempt!.retirement
            let others = try (0..<(16 - CapabilityAttemptReservation.occupiedSlots)).map { _ in try CapabilityAttemptReservation.acquire() }
            try need(CapabilityAttemptReservation.occupiedSlots == 16, "Did not fill outer pool")
            owner.beginClosing(); await store.close()
            try need(!owner.isReleased && !token.completed, "Live native attempt was counted free")
            attempt = nil // No explicit attempt.stop: exercise the actual ownership graph.
            try need(weakAttempt == nil, "Reservation/sink retained the concrete attempt")
            let end = ContinuousClock.now.advanced(by: .seconds(5))
            while !token.completed && ContinuousClock.now < end { try await Task.sleep(for: .milliseconds(1)) }
            try need(token.completed && owner.isReleased, "Last-owner drop did not drain actual native resources")
            let waited = await token.wait(); try need(waited, "Actual retirement waiter failed")
            let replacement = try CapabilityAttemptReservation.acquire(); replacement.beginClosing()
            others.forEach { $0.beginClosing() }; signals.finishNotifications()
            try need(CapabilityAttemptReservation.occupiedSlots == baseline, "Outer pool leaked after actual exit")
        }
        print("PASS 8 actual signed/native-selected construct+startup+last-owner-drop cycles; live slot retained until actual drain, outer16 reusable; no effects/native I/O")
    }
}
