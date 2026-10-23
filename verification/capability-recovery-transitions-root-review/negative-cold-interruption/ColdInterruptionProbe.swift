// Root review: signed fixture scaffold reused from candidate1 owner test; main below is original root probe.
import Foundation
import Crypto
import MixerCapabilities
import MixerUpdates
@testable import MixerExperimentalCapabilityRuntime
@testable import MixerCapabilityActivation

private final class TransitionTime: @unchecked Sendable {
    private let lock = NSLock()
    private var wall: UInt64 = 1000
    private var uptime: UInt64 = 1_000_000
    func now() -> UInt64 { lock.lock(); defer { lock.unlock() }; return wall }
    func mono() -> UInt64 { lock.lock(); defer { lock.unlock() }; return uptime }
    func set(wall: UInt64? = nil, uptime: UInt64? = nil) {
        lock.lock(); if let wall { self.wall = wall }; if let uptime { self.uptime = uptime }; lock.unlock()
    }
    var environment: CapabilityRecoveryEnvironment { .init(wall: { self.now() }, monotonic: { self.mono() }) }
}
private final class TransitionFault: @unchecked Sendable {
    private let lock = NSLock()
    private var action: (@Sendable () throws -> Void)?
    func arm(_ action: @escaping @Sendable () throws -> Void) { lock.lock(); self.action = action; lock.unlock() }
    func check(_ point: CapabilityDurabilityFaultPoint) throws {
        guard point == .beforeStateFileSync else { return }
        lock.lock(); let action = action; self.action = nil; lock.unlock(); try action?()
    }
}
private actor TransitionGate {
    private var reached = false, open = false
    func pause() async {
        reached = true
        let end = ContinuousClock.now.advanced(by: .seconds(10))
        while !open && ContinuousClock.now < end { await Task.yield() }
    }
    func wait() async throws {
        let end = ContinuousClock.now.advanced(by: .seconds(10))
        while !reached && ContinuousClock.now < end { await Task.yield() }
        guard reached else { throw UpdateError("test.gate", "No validation boundary") }
    }
    func release() { open = true }
}
/// Original signed fixtures and original binary writer. The key is public TESTONLY.
private struct TransitionFixture {
    let installed: InstalledMaterial
    let key: Curve25519.Signing.PrivateKey
    let directory: URL
    init(directory: URL, keyEnd: UInt64 = 2000) throws {
        self.directory = directory
        key = try .init(rawRepresentation: Data(repeating: 0x67, count: 32))
        let original = URL(fileURLWithPath: CommandLine.arguments[1]).appendingPathComponent("identity.json")
        var object = try JSONSerialization.jsonObject(with: Data(contentsOf: original)) as! [String: Any]
        object["capabilities"] = []
        let scope = UpdateScope(organization: "material-test", project: "material-test", app: "material-test", environment: "development", platform: "ios")
        let roots = try JSONEncoder().encode([TrustRoot(keyID: "transition", publicKey: key.publicKey.rawRepresentation, scope: scope,
            artifact: true, assignment: true, notBeforeUnix: 1, notAfterUnix: keyEnd)])
        var build = object["build"] as! [String: Any]; build["trust_roots_sha256"] = ReleaseVerifier.sha256(roots); object["build"] = build
        let bridge = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]).appendingPathComponent("bridge.json"))
        let identity = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys, .withoutEscapingSlashes])
        installed = try InstalledCapabilityExecution(identityJSON: identity, materials: [.init(role: .bridgePolicy, bytes: bridge)],
            trustRootsJSON: roots, privateContainer: directory).installed
    }
    var configuration: CapabilityRecoveryConfiguration {
        var c = CapabilityRecoveryConfiguration(directory: directory, channel: "beta", installation: "installation")
        c.observationSeconds = 1; c.requiredMilestones = ["feature_started", "first_screen"]; return c
    }
    func documents(_ payload: Data, sequence: UInt64, fuel: UInt64 = 1000, startup: UInt64 = 60_000) throws -> (Data, Data) {
        let h = installed.identity.installedRuntime, s = h.scope
        let scope = CanonicalValue.object(["organization": .text(s.organization), "project": .text(s.project), "app": .text(s.app), "environment": .text(s.environment), "platform": .text(s.platform)])
        let m = CanonicalValue.object([
            "schema": .uint(3), "scope": scope, "release_id": .text("transition"), "source_commit": .text(String(repeating: "c", count: 40)),
            "provenance_id": .text("transition"), "runtime": .text(h.runtime), "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
            "capability_hashes": .object([:]), "state_min": .uint(0), "state_max": .uint(0), "payload_sha256": .text(ReleaseVerifier.sha256(payload)),
            "compressed_bytes": .uint(UInt64(payload.count)), "expanded_bytes": .uint(UInt64(payload.count)), "compression": .text("none"), "asset_hashes": .object([:]),
            "source_map_sha256": .text(String(repeating: "d", count: 64)), "limits": .object(["memory_bytes": .uint(65_536), "fuel": .uint(fuel), "startup_milliseconds": .uint(startup)]),
            "key_id": .text("transition"), "created_at_unix": .uint(100), "capability_grants": .object(["schema": .uint(1), "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array([])])])
        let a = CanonicalValue.object(["schema": .uint(3), "scope": scope, "channel": .text("beta"), "cohort": .text("sha256-v1"), "rollout_basis_points": .uint(10_000),
            "sequence": .uint(sequence), "release_id": .text("transition"), "artifact_sha256": .text(ReleaseVerifier.sha256(try m.canonicalCBOR())), "runtime": .text(h.runtime), "key_id": .text("transition"), "created_at_unix": .uint(100)])
        func sign(_ value: CanonicalValue, assignment: Bool) throws -> Data {
            let prefix = assignment ? "mixer.assignment.v3\0" : "mixer.artifact.v3\0"
            let signature = try key.signature(for: Data(prefix.utf8) + value.canonicalCBOR())
            let encoded = CanonicalValue.object([assignment ? "assignment" : "manifest": value, "signature": .text(signature.base64EncodedString())])
            return try JSONEncoder().encode(encoded)
        }
        return (try sign(m, assignment: false) + Data(" \n".utf8), try sign(a, assignment: true) + Data("\t".utf8))
    }
    static func wasm(startup: [UInt8] = [], wake: [UInt8] = []) -> Data {
        func leb(_ value: Int) -> [UInt8] {
            var n = value, out: [UInt8] = []
            repeat { var b = UInt8(n & 127); n >>= 7; if n != 0 { b |= 128 }; out.append(b) } while n != 0
            return out
        }
        func section(_ id: UInt8, _ bytes: [UInt8]) -> [UInt8] { [id] + leb(bytes.count) + bytes }
        func name(_ s: String) -> [UInt8] { leb(s.utf8.count) + Array(s.utf8) }
        let boot = [UInt8(0)] + startup + [0x0b], ready = [UInt8(0)] + wake + [0x0b]
        var exports = [UInt8(2)] + name("startup"); exports += [0,0]
        exports += name("mixer_guest_capability_ready_v1"); exports += [0,1]
        var module: [UInt8] = [0,97,115,109,1,0,0,0]
        module += section(1,[1,0x60,0,0]); module += section(3,[2,0,0]); module += section(5,[1,0,0])
        module += section(7,exports); module += section(10,[2] + leb(boot.count) + boot + leb(ready.count) + ready)
        return Data(module)
    }
}


@main struct ColdInterruptionProbe {
    static func main() async throws {
        let mode = CommandLine.arguments[2]
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-root-cold-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        let fixture = try TransitionFixture(directory: parent.appendingPathComponent("private")), clock = TransitionTime()
        let owner = try CapabilityAttemptReservation.acquire()
        let store = try await CapabilityRecoveryStore.open(admission: owner.issueStoreAdmission(), installed: fixture.installed,
            configuration: fixture.configuration, environment: clock.environment)
        let module = TransitionFixture.wasm(), (manifest, assignment) = try fixture.documents(module, sequence: 1)
        try await store.beginDownload(signedManifest: manifest, signedAssignment: assignment)
        try await store.appendDownload(module, atOffset: 0); try await store.finishDownload()
        guard let selected = try await store.prepareStartupSelection() else { fatalError("No initial selection") }
        let signals = CapabilityAttemptSignals(generation: selected.generation)
        let input = try await store.consume(selected, signals: signals)
        let session = try await ExperimentalCapabilitySession.prepare(module: input.module, startupExport: input.startupExport,
            configuration: input.policy.native, policy: input.policy.policy, adapters: .init()).create()
        _ = try await session.startup()
        if mode != "incomplete-before-effects" {
            try await store.recordEffectsIntent(input, signals: signals)
            try await session.enableEffects()
            try await store.confirmEffectsEnabled(input, signals: signals)
        }
        if mode == "recorded-after-effects" {
            signals.requestStop(.closed)
            guard case .recoveryRequired = try await store.failAndPrepareFallback(input, signals: signals) else { fatalError("Missing recovery requirement") }
        }
        session.close(); signals.finishNotifications()
        owner.beginClosing(); await store.close()
        precondition(owner.isReleased)
        let reopenedOwner = try CapabilityAttemptReservation.acquire()
        let reopened = try await CapabilityRecoveryStore.open(admission: reopenedOwner.issueStoreAdmission(), installed: fixture.installed,
            configuration: fixture.configuration, environment: clock.environment)
        let state = try StrictJSON.decode(CapabilityRecoveryState.self, from: Data(contentsOf: fixture.directory.appendingPathComponent("state.json")))
        precondition(state.healthy == nil && state.acceptedSequence == 1 && state.failures.isEmpty && state.quarantine.isEmpty)
        let next = try await reopened.prepareStartupSelection()
        print("mode=\(mode) recovery=\(state.lastRecovery) healthy=nil accepted=\(state.acceptedSequence) staged=\(state.staged != nil) next=\(next.map { String(describing: $0.source) } ?? "native")")
        reopenedOwner.beginClosing(); await reopened.close(); precondition(reopenedOwner.isReleased)
        guard next == nil else { print("FAIL: unhealthy failed/interrupted candidate retried on cold reopen"); exit(42) }
        print("PASS: native fallback after interrupted/failed never-healthy candidate")
    }
}
