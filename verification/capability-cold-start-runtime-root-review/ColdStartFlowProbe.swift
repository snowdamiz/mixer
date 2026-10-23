// Root independent flow assertions below reuse the original signed-fixture scaffold from transition candidate3.
// Internal openOwned supplies only a controlled wall clock; actual monotonic clocks, native VM, adapters and durable store remain real.
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


private struct RootProbeFailure: Error { let message: String }
@main struct ColdStartFlowProbe {
    static func check(_ value: @autoclosure () -> Bool, _ message: String) throws {
        if !value() { throw RootProbeFailure(message: message) }
    }
    static func eventually(_ message: String, _ predicate: @Sendable () async throws -> Bool) async throws {
        let deadline = ContinuousClock.now.advanced(by: .seconds(8))
        while !(try await predicate()) {
            guard ContinuousClock.now < deadline else { throw RootProbeFailure(message: message) }
            try await Task.sleep(for: .milliseconds(10))
        }
    }
    static func config(_ directory: URL) -> CapabilityColdStartConfiguration {
        .init(directory: directory, channel: "beta", installation: "installation", observationSeconds: 1)
    }
    static func main() async throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-root-coordinator-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        let fixture = try TransitionFixture(directory: parent.appendingPathComponent("recovery")), clock = TransitionTime()
        let environment = CapabilityRecoveryEnvironment(wall: { clock.now() })
        let baseline = CapabilityAttemptReservation.occupiedSlots
        let runtime = try await CapabilityColdStartRuntime.openOwned(configuration: config(fixture.directory), installed: fixture.installed, environment: environment)
        let bytes = TransitionFixture.wasm(), (manifest, assignment) = try fixture.documents(bytes, sequence: 1)
        try await runtime.beginDownload(signedManifest: manifest, signedAssignment: assignment)
        try await runtime.appendDownload(bytes, atOffset: 0); try await runtime.finishDownload()
        let started = try await runtime.start()
        try check(started.phase == .provisionalGuest && started.effectsMayHaveOpened, "Start did not produce a provisional enabled guest")
        try check(!started.requiresReopen && started.acceptedSequence == 1, "Unexpected initial recovery state")
        try await runtime.reportMilestone("feature_started")
        let before = await runtime.recoverySnapshot()
        try check(before.activation.phase == .provisionalGuest && before.healthy == nil, "Missing milestone bypassed health gate")
        try await runtime.reportMilestone("first_screen")
        // No further milestone or external call drives health. The timer must wake
        // the existing consumer when both reports precede the observation window.
        try await eventually("Observation did not promote health") {
            let snapshot = await runtime.recoverySnapshot()
            return snapshot.activation.phase == .healthyGuest && snapshot.healthy == started.candidateID
        }
        let healthyBytes = try Data(contentsOf: fixture.directory.appendingPathComponent("state.json"))
        let healthy = try StrictJSON.decode(CapabilityRecoveryState.self, from: healthyBytes)
        try check(healthy.healthy?.candidateID == started.candidateID && healthy.attempt?.effectsMayHaveOpened == true, "Health lost the live effects attempt")
        await runtime.close()
        try await eventually("Close did not release real owners") {
            !(await runtime.recoverySnapshot()).activation.cleanupPending && CapabilityAttemptReservation.occupiedSlots == baseline
        }
        print("PASS early milestone reports trigger later automatic health and real close retirement")

        clock.set(wall: 3000) // Root expired; only exact real committed healthy evidence is eligible.
        let reopened = try await CapabilityColdStartRuntime.openOwned(configuration: config(fixture.directory), installed: fixture.installed, environment: environment)
        let restarted = try await reopened.start()
        try check(restarted.phase == .provisionalGuest && restarted.candidateID == started.candidateID, "Expired exact healthy candidate did not start provisionally")
        let state = try StrictJSON.decode(CapabilityRecoveryState.self, from: Data(contentsOf: fixture.directory.appendingPathComponent("state.json")))
        try check(state.attempt?.source == "healthy" && state.acceptedSequence == 1, "Reopen laundered retained health as fresh or lowered high-water")
        await reopened.close()
        try await eventually("Retained close did not release owners") { CapabilityAttemptReservation.occupiedSlots == baseline }
        print("PASS real committed healthy provenance survives cold reopen after root expiry")

        var owners: [CapabilityColdStartRuntime] = []
        for index in 0..<(16 - baseline) {
            owners.append(try await CapabilityColdStartRuntime.openOwned(configuration: config(parent.appendingPathComponent("idle-\(index)")), installed: fixture.installed, environment: environment))
        }
        let rejectedPath = parent.appendingPathComponent("must-not-exist")
        var rejected = false
        do {
            let unexpected = try await CapabilityColdStartRuntime.openOwned(configuration: config(rejectedPath), installed: fixture.installed, environment: environment)
            await unexpected.close()
        } catch { rejected = true }
        try check(rejected && !FileManager.default.fileExists(atPath: rejectedPath.path), "Full pool performed directory work")
        for owner in owners { await owner.close() }
        owners.removeAll()
        try await eventually("Idle close did not return capacity") { CapabilityAttemptReservation.occupiedSlots == baseline }
        print("PASS public owner ceiling rejects before directory creation and idle close returns capacity")

        for index in 0..<32 {
            let configuration = config(parent.appendingPathComponent("cancel-\(index)"))
            let task = Task { try await CapabilityColdStartRuntime.openOwned(configuration: configuration, installed: fixture.installed, environment: environment) }
            task.cancel()
            do { let completedBeforeCancellation = try await task.value; await completedBeforeCancellation.close() }
            catch { /* Cancellation may win before store admission or during open. */ }
            try await eventually("Cancelled open leaked a counted owner") { CapabilityAttemptReservation.occupiedSlots == baseline }
        }
        print("PASS 32 cancelled opens preserve capacity after actual cleanup")
        print("PASS 4 coordinator flow cases; synthetic milestone reports are not real UI/FieldLog evidence")
    }
}
