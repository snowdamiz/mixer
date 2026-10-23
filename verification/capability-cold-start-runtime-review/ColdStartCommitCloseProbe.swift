// The signed TESTONLY fixture scaffold below is credited to the root review and transition candidate3.
// Independent review assertions follow; no executable acceptance, adapter, native or store implementation is substituted.
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



private struct ReviewFailure: Error { let message: String }
private final class CompletedCloses: @unchecked Sendable {
    private let lock = NSLock(); private var value = 0
    func increment() { lock.lock(); value += 1; lock.unlock() }
    var count: Int { lock.lock(); defer { lock.unlock() }; return value }
}
/// Holds exactly one real store transaction, then optionally injects an error.
/// It cannot replace bytes, validation, adapters, native execution or selection.
private final class HealthCommitGate: @unchecked Sendable {
    private let condition = NSCondition()
    private var armed = false, entered = false, released = false
    let point: CapabilityDurabilityFaultPoint
    let failAfterRelease: Bool
    init(_ point: CapabilityDurabilityFaultPoint, failAfterRelease: Bool) {
        self.point = point; self.failAfterRelease = failAfterRelease
    }
    func arm() { condition.lock(); armed = true; condition.unlock() }
    var reached: Bool { condition.lock(); defer { condition.unlock() }; return entered }
    func check(_ point: CapabilityDurabilityFaultPoint) throws {
        condition.lock()
        guard self.point == point, armed else { condition.unlock(); return }
        armed = false; entered = true
        let cutoff = Date().addingTimeInterval(12)
        while !released {
            if !condition.wait(until: cutoff) { condition.unlock(); throw ReviewFailure(message: "gate release timed out") }
        }
        condition.unlock()
        if failAfterRelease { throw ReviewFailure(message: "injected post-rename health error") }
    }
    func release() { condition.lock(); released = true; condition.broadcast(); condition.unlock() }
}
@main struct ColdStartCommitCloseProbe {
    static func check(_ value: @autoclosure () -> Bool, _ message: String) throws {
        if !value() { throw ReviewFailure(message: message) }
    }
    static func eventually(_ message: String, _ predicate: @Sendable () async throws -> Bool) async throws {
        let end = ContinuousClock.now.advanced(by: .seconds(8))
        while !(try await predicate()) {
            guard ContinuousClock.now < end else { throw ReviewFailure(message: message) }
            try await Task.sleep(for: .milliseconds(2))
        }
    }
    static func one(_ label: String, point: CapabilityDurabilityFaultPoint, fail: Bool) async throws {
        let parent = URL(fileURLWithPath: CommandLine.arguments[2]).appendingPathComponent(label)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: true)
        let fixture = try TransitionFixture(directory: parent.appendingPathComponent("store"))
        let gate = HealthCommitGate(point, failAfterRelease: fail)
        defer { gate.release() }
        let config = CapabilityColdStartConfiguration(directory: fixture.directory, channel: "beta", installation: "installation", observationSeconds: 1)
        let baseline = CapabilityAttemptReservation.occupiedSlots
        let runtime = try await CapabilityColdStartRuntime.openOwned(configuration: config, installed: fixture.installed,
            environment: .init(wall: { 1000 }, fault: { try gate.check($0) }))
        let bytes = TransitionFixture.wasm(), (manifest, assignment) = try fixture.documents(bytes, sequence: 1)
        try await runtime.beginDownload(signedManifest: manifest, signedAssignment: assignment)
        try await runtime.appendDownload(bytes, atOffset: 0); try await runtime.finishDownload()
        let started = try await runtime.start()
        try check(started.phase == .provisionalGuest && started.effectsMayHaveOpened, "start was not provisional after enable")
        gate.arm()
        try await runtime.reportMilestone("feature_started")
        try await runtime.reportMilestone("first_screen")
        try await eventually("real health transaction did not reach gate") { gate.reached }
        let completed = CompletedCloses()
        var closes: [Task<Void, Never>] = []
        for _ in 0..<24 { closes.append(Task { await runtime.close(); completed.increment() }) }
        try await eventually("close failed to synchronously close public admission") {
            (await runtime.recoverySnapshot()).activation.phase == .closed
        }
        let during = await runtime.recoverySnapshot()
        try check(during.activation.cleanupPending && during.activation.effectsMayHaveOpened,
                  "blocked actual store commit was counted as retired or lost effects")
        try check(during.activation.terminalCause == .closed, "first close cause not retained")
        try check(completed.count == 0 && CapabilityAttemptReservation.occupiedSlots == baseline + 1,
                  "close returned or capacity released before held filesystem transaction returned")
        do { _ = try await runtime.start(); throw ReviewFailure(message: "start admitted after close") }
        catch let e as ReviewFailure { throw e } catch {}
        do { try await runtime.reportMilestone("first_screen"); throw ReviewFailure(message: "milestone admitted after close") }
        catch let e as ReviewFailure { throw e } catch {}
        do { try await runtime.appendDownload(Data([0]), atOffset: 0); throw ReviewFailure(message: "append admitted after close") }
        catch let e as ReviewFailure { throw e } catch {}
        gate.release()
        for close in closes { await close.value }
        try await eventually("actual close did not retire capacity") {
            !(await runtime.recoverySnapshot()).activation.cleanupPending && CapabilityAttemptReservation.occupiedSlots == baseline
        }
        let final = await runtime.recoverySnapshot()
        try check(completed.count == 24 && final.activation.phase == .closed,
                  "coalesced close lost a waiter or republished guest health")
        try check(final.activation.terminalCause == .closed && final.activation.firstBridgeFailure == nil,
                  "ordinary close fabricated a bridge failure")
        let stateURL = fixture.directory.appendingPathComponent("state.json")
        let state = try StrictJSON.decode(CapabilityRecoveryState.self, from: Data(contentsOf: stateURL))
        try check(state.healthy?.candidateID == started.candidateID && state.acceptedSequence == 1,
                  "entered actual health commit was rolled back or sequence lost")
        try check(state.failures.isEmpty && state.quarantine.isEmpty, "close counted as deterministic guest failure")
        if fail {
            try check(final.requiresReopen && state.attempt?.effectsMayHaveOpened == true,
                      "uncertain post-rename commit lost poison or active recovery linkage")
            let reopened = try await CapabilityColdStartRuntime.openOwned(configuration: config, installed: fixture.installed,
                environment: .init(wall: { 1000 }))
            let recovered = try StrictJSON.decode(CapabilityRecoveryState.self, from: Data(contentsOf: stateURL))
            try check(recovered.lastRecovery == "unknown_interruption_after_effects" && recovered.attempt == nil && recovered.staged == nil,
                      "cold reopen did not conservatively reconcile entered uncertain effects")
            try check(recovered.healthy?.candidateID == started.candidateID && recovered.acceptedSequence == 1,
                      "cold reconciliation discarded actual health or high water")
            await reopened.close()
            try await eventually("reopened cleanup leaked capacity") { CapabilityAttemptReservation.occupiedSlots == baseline }
        } else {
            try check(!final.requiresReopen && state.attempt == nil && state.lastRecovery == "effects_closed",
                      "successful entered commit did not persist closed effects linkage")
        }
        print("PASS \(label): 24 coalesced close waiters; immediate closed admission; held I/O remained counted; exact actual/uncertain recovery")
    }
    static func main() async throws {
        try await one("close-during-health-fsync", point: .beforeStateFileSync, fail: false)
        try await one("close-during-uncertain-health-rename", point: .afterStateRename, fail: true)
        print("PASS 2 original control/close race cases; synthetic milestone reports do not qualify real UI/FieldLog health")
    }
}
