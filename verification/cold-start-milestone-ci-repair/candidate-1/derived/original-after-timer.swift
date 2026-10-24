import Foundation
import Crypto
import XCTest
import MixerCapabilities
import MixerUpdates
@testable import MixerCapabilityActivation
@testable import MixerExperimentalCapabilityRuntime

private final class ColdStartQueueGate: @unchecked Sendable {
    private let condition = NSCondition(); private var started = false, released = false
    var entered: Bool { condition.lock(); defer { condition.unlock() }; return started }
    func hold() {
        condition.lock(); started = true
        while !released { condition.wait() }
        condition.unlock()
    }
    func release() { condition.lock(); released = true; condition.broadcast(); condition.unlock() }
}

private final class ColdStartReturnObservation: @unchecked Sendable {
    private let lock = NSLock()
    private var returned = false
    var didReturn: Bool { lock.lock(); defer { lock.unlock() }; return returned }
    func recordReturn() { lock.lock(); returned = true; lock.unlock() }
}

private actor ColdStartGate {
    private var entered = false, released = false, armed = false
    func arm() { armed = true }
    func hold() async {
        guard armed else { return }
        entered = true
        while !released { await Task.yield() }
    }
    func wait() async throws {
        let cutoff = ContinuousClock.now.advanced(by: .seconds(5))
        while !entered {
            guard ContinuousClock.now < cutoff else { throw UpdateError("test.timeout", "Validation gate not reached") }
            await Task.yield()
        }
    }
    func release() { released = true }
}

/// Independently signed TESTONLY documents and a small original binary encoder.
/// Installed descriptor/configuration bytes reuse this target's trusted fixture
/// material; neither evidence issuance nor the native validator is replaced.
struct ColdStartFixture {
    let root: URL
    let execution: InstalledCapabilityExecution
    let key: Curve25519.Signing.PrivateKey
    var configuration: CapabilityColdStartConfiguration {
        .init(directory: root.appendingPathComponent("recovery"), channel: "beta", installation: "cold-start", observationSeconds: 1)
    }
    init(root: URL) throws {
        self.root = root
        key = try .init(rawRepresentation: Data(repeating: 0x53, count: 32))
        func resource(_ name: String) throws -> Data {
            try Data(contentsOf: Bundle.module.url(forResource: name, withExtension: nil, subdirectory: "Fixtures")!)
        }
        let scope = UpdateScope(organization: "material-test", project: "material-test", app: "material-test", environment: "development", platform: "ios")
        let roots = try JSONEncoder().encode([TrustRoot(keyID: "cold-start-test", publicKey: key.publicKey.rawRepresentation,
            scope: scope, artifact: true, assignment: true, notBeforeUnix: 1, notAfterUnix: 2000)])
        var identity = try JSONSerialization.jsonObject(with: resource("identity.json")) as! [String: Any]
        var build = identity["build"] as! [String: Any]
        build["trust_roots_sha256"] = ReleaseVerifier.sha256(roots); identity["build"] = build
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
            "schema": .uint(3), "scope": scope, "release_id": .text("cold-start"), "source_commit": .text(String(repeating: "5", count: 40)),
            "provenance_id": .text("cold-start-test"), "runtime": .text(host.runtime), "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
            "capability_hashes": .object(host.capabilityHashes.mapValues(CanonicalValue.text)), "state_min": .uint(0), "state_max": .uint(0),
            "payload_sha256": .text(ReleaseVerifier.sha256(bytes)), "compressed_bytes": .uint(UInt64(bytes.count)), "expanded_bytes": .uint(UInt64(bytes.count)),
            "compression": .text("none"), "asset_hashes": .object([:]), "source_map_sha256": .text(String(repeating: "6", count: 64)),
            "limits": .object(["memory_bytes": .uint(65_536), "fuel": .uint(100_000), "startup_milliseconds": .uint(startupMilliseconds)]),
            "key_id": .text("cold-start-test"), "created_at_unix": .uint(100), "capability_grants": .object(["schema": .uint(1),
                "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array(entries)])])
        let assignment = CanonicalValue.object(["schema": .uint(3), "scope": scope, "channel": .text("beta"), "cohort": .text("sha256-v1"),
            "rollout_basis_points": .uint(10_000), "sequence": .uint(sequence), "release_id": .text("cold-start"),
            "artifact_sha256": .text(ReleaseVerifier.sha256(try manifest.canonicalCBOR())), "runtime": .text(host.runtime), "key_id": .text("cold-start-test"), "created_at_unix": .uint(100)])
        func signed(_ value: CanonicalValue, assignment: Bool) throws -> Data {
            let prefix = assignment ? "mixer.assignment.v3\0" : "mixer.artifact.v3\0"
            let signature = try key.signature(for: Data(prefix.utf8) + value.canonicalCBOR())
            return try JSONEncoder().encode(CanonicalValue.object([assignment ? "assignment" : "manifest": value, "signature": .text(signature.base64EncodedString())]))
        }
        return (try signed(manifest, assignment: false) + Data(" \n".utf8), try signed(assignment, assignment: true) + Data("\t".utf8))
    }
    static func wasm(trap: Bool = false) -> Data {
        func u(_ value: Int) -> [UInt8] {
            var n = value, result: [UInt8] = []
            repeat { let b = UInt8(n & 127); n >>= 7; result.append(b | (n == 0 ? 0 : 128)) } while n != 0
            return result
        }
        func name(_ text: String) -> [UInt8] { u(text.utf8.count) + Array(text.utf8) }
        func section(_ id: UInt8, _ contents: [UInt8]) -> [UInt8] { [id] + u(contents.count) + contents }
        let startup: [UInt8] = trap ? [0,0,0x0b] : [0,0x0b]
        var exports: [UInt8] = [2]; exports += name("startup"); exports += [0,0]
        exports += name("mixer_guest_capability_ready_v1"); exports += [0,1]
        var bytes: [UInt8] = [0,97,115,109,1,0,0,0]
        bytes += section(1,[1,0x60,0,0]); bytes += section(3,[2,0,0]); bytes += section(5,[1,0,0])
        bytes += section(7,exports); bytes += section(10,[2] + u(startup.count) + startup + [2,0,0x0b])
        return Data(bytes)
    }
}

final class CapabilityColdStartRuntimeTests: XCTestCase, @unchecked Sendable {
    private func fixture() throws -> ColdStartFixture {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-cold-start-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        addTeardownBlock { try FileManager.default.removeItem(at: root) }
        return try ColdStartFixture(root: root)
    }
    private func opened(_ f: ColdStartFixture, environment: CapabilityRecoveryEnvironment = .init(wall: { 1000 })) async throws -> CapabilityColdStartRuntime {
        try await CapabilityColdStartRuntime.openOwned(configuration: f.configuration, installed: f.execution.installed, environment: environment)
    }
    private func stage(_ f: ColdStartFixture, _ runtime: CapabilityColdStartRuntime, trap: Bool = false, storage: Bool = false) async throws {
        let bytes = ColdStartFixture.wasm(trap: trap), (manifest, assignment) = try f.documents(bytes,storage: storage)
        try await runtime.beginDownload(signedManifest: manifest, signedAssignment: assignment)
        try await runtime.appendDownload(bytes, atOffset: 0); try await runtime.finishDownload()
    }
    private func eventually(_ label: String, _ predicate: () async throws -> Bool) async throws {
        let cutoff = ContinuousClock.now.advanced(by: .seconds(8))
        while !(try await predicate()) {
            guard ContinuousClock.now < cutoff else { throw UpdateError("test.timeout", label) }
            try await Task.sleep(for: .milliseconds(2))
        }
    }
    private func close(_ runtime: CapabilityColdStartRuntime, baseline: Int) async throws {
        await runtime.close()
        try await eventually("real cleanup did not return capacity") { CapabilityAttemptReservation.occupiedSlots == baseline }
    }
    func testEarlyInstalledMilestonesWakeAutomaticHealthAndStartupAloneDoesNot() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await opened(f)
        let probe = MilestoneCIProbe.shared
        addTeardownBlock { probe.release(); await runtime.close(); probe.reset() }
        try await stage(f,runtime); let initial = try await runtime.start()
        XCTAssertEqual(initial.phase,.provisionalGuest); XCTAssertTrue(initial.effectsMayHaveOpened)
        let noHealth = await runtime.recoverySnapshot(); XCTAssertNil(noHealth.healthy)
        do { try await runtime.reportMilestone("guest_supplied"); XCTFail("Unknown native milestone accepted") } catch {}
        try await runtime.reportMilestone("feature_started")
        probe.arm()
        try await Task.sleep(for: .milliseconds(1100))
        try await eventually("timer notification not admitted") { probe.isEntered }
        XCTAssertTrue(probe.timerFired)
        let stillNoHealth = await runtime.recoverySnapshot(); XCTAssertNil(stillNoHealth.healthy)
        print("MILESTONE_CI original-call notificationHeld=\(probe.isEntered) timerFired=\(probe.timerFired)")
        try await runtime.reportMilestone("first_screen")
        try await eventually("health missing after actual reports and interval") { (await runtime.recoverySnapshot()).activation.phase == .healthyGuest }
        let snapshot = await runtime.recoverySnapshot(); XCTAssertEqual(snapshot.healthy,initial.candidateID)
        try await close(runtime,baseline: baseline)
    }
    func testBothReportsBeforeTimerPromoteWithoutFurtherPublicCalls() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await opened(f)
        try await stage(f,runtime); _ = try await runtime.start()
        try await runtime.reportMilestone("feature_started"); try await runtime.reportMilestone("first_screen")
        let before = await runtime.recoverySnapshot(); XCTAssertNil(before.healthy)
        try await eventually("one-shot timer failed to re-poke existing consumer") { (await runtime.recoverySnapshot()).healthy != nil }
        try await close(runtime,baseline: baseline)
    }
    func testCheckedStartupTrapRecordsOnceAndReturnsStableNativeFallback() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await opened(f)
        try await stage(f,runtime,trap: true); let result = try await runtime.start()
        XCTAssertEqual(result.phase,.nativeFallback); XCTAssertFalse(result.effectsMayHaveOpened)
        XCTAssertNotNil(result.firstBridgeFailure); XCTAssertFalse(result.cleanupPending)
        let state = try StrictJSON.decode(CapabilityRecoveryState.self,from: Data(contentsOf: f.configuration.directory.appendingPathComponent("state.json")))
        XCTAssertEqual(state.failures[state.candidates[result.candidateID!]!.artifactSHA256],1); XCTAssertNil(state.attempt)
        let stable = await runtime.recoverySnapshot(); XCTAssertEqual(stable.activation.phase,.nativeFallback)
        try await close(runtime,baseline: baseline)
    }
    func testBoundsAndOneShotSelectionRejectWithoutNewWork() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await opened(f)
        do { try await runtime.beginDownload(signedManifest: Data(repeating: 0,count: 65_537),signedAssignment: Data()); XCTFail("Oversized document") } catch {}
        do { try await runtime.appendDownload(Data(repeating: 0,count: 1_048_577),atOffset: 0); XCTFail("Oversized chunk") } catch {}
        let result = try await runtime.start(); XCTAssertEqual(result.phase,.nativeFallback)
        do { _ = try await runtime.start(); XCTFail("Duplicate start") } catch {}
        do { try await runtime.beginDownload(signedManifest: Data(),signedAssignment: Data()); XCTFail("Download after selection") } catch {}
        let noSequence = await runtime.recoverySnapshot(); XCTAssertEqual(noSequence.acceptedSequence,0)
        try await close(runtime,baseline: baseline)
    }
    func testCloseDuringRealValidationJoinsWithoutAdapterCreation() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), gate = ColdStartGate()
        let runtime = try await opened(f,environment: .init(wall: { 1000 },beforeValidation: { await gate.hold() }))
        try await stage(f,runtime); await gate.arm()
        let start = Task { try await runtime.start() }; try await gate.wait()
        let closing = Task { await runtime.close() }
        try await eventually("close admission not latched") { (await runtime.recoverySnapshot()).activation.phase == .closed }
        XCTAssertFalse(FileManager.default.fileExists(atPath: f.root.appendingPathComponent("material_test").path))
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots,baseline+1)
        await gate.release(); do { _ = try await start.value; XCTFail("Closed validation returned live") } catch {}
        await closing.value; try await eventually("validation tail not retired") { CapabilityAttemptReservation.occupiedSlots == baseline }
    }
    func testSixteenOwnersRejectSeventeenthBeforeIOAndRepeatedCloseIsCoalesced() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        var owners: [CapabilityColdStartRuntime] = []
        for index in 0..<(16-baseline) {
            let c = CapabilityColdStartConfiguration(directory: f.root.appendingPathComponent("owner-\(index)"),channel: "beta",installation: "cold-start")
            owners.append(try await CapabilityColdStartRuntime.openOwned(configuration: c,installed: f.execution.installed,environment: .init(wall: { 1000 })))
        }
        let rejected = f.root.appendingPathComponent("rejected")
        do {
            let unexpected = try await CapabilityColdStartRuntime.openOwned(configuration: .init(directory: rejected,channel: "beta",installation: "cold-start"),installed: f.execution.installed,environment: .init(wall: { 1000 }))
            await unexpected.close(); XCTFail("17th owner admitted")
        } catch {}
        XCTAssertFalse(FileManager.default.fileExists(atPath: rejected.path))
        for owner in owners { async let a: Void = owner.close(); async let b: Void = owner.close(); _ = await (a,b) }
        owners.removeAll(); try await eventually("owner ceiling not reclaimed") { CapabilityAttemptReservation.occupiedSlots == baseline }
    }
    func testCloseDuringQueuedNativeCreationKeepsCountedOrdinaryAndAdapterTails() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await opened(f), gate = ColdStartQueueGate()
        let startupReturn = ColdStartReturnObservation(), closeReturn = ColdStartReturnObservation()
        try await stage(f,runtime,storage: true)
        ExperimentalQueues.construction.async { gate.hold() }; defer { gate.release() }
        try await eventually("construction worker gate not entered") { gate.entered }
        let startup = Task { defer { startupReturn.recordReturn() }; return try await runtime.start() }
        try await eventually("concrete setup never opened KV") { FileManager.default.fileExists(atPath: f.root.appendingPathComponent("material_test").path) }
        let closing = Task { defer { closeReturn.recordReturn() }; await runtime.close() }
        try await eventually("close did not synchronously stop admission") { (await runtime.recoverySnapshot()).activation.phase == .closed }
        // Directory creation precedes native construction admission. Close may
        // win in between and finish without ever entering the held native queue.
        // Returned capacity is valid only if both actual async tails can return
        // while that queue remains blocked. A queued tail cannot satisfy this.
        let pending = await runtime.recoverySnapshot()
        let occupied = CapabilityAttemptReservation.occupiedSlots
        if !pending.activation.cleanupPending || occupied != baseline + 1 {
            try await eventually("capacity returned before blocked startup/close tails") {
                startupReturn.didReturn && closeReturn.didReturn
            }
            XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots,baseline)
            let completed = await runtime.recoverySnapshot()
            XCTAssertFalse(completed.activation.cleanupPending)
        }
        gate.release(); do { _ = try await startup.value; XCTFail("Cancelled queued creation returned live") } catch {}
        await closing.value; try await eventually("actual create/adapter cleanup tail leaked") { CapabilityAttemptReservation.occupiedSlots == baseline }
    }
    func testFacadeDeinitAndCancelledOpenReleaseOnlyAfterCleanup() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        var runtime: CapabilityColdStartRuntime? = try await opened(f)
        weak var observed = runtime; XCTAssertNotNil(observed); runtime = nil; XCTAssertNil(observed); observed = nil
        try await eventually("deinit cleanup parked") { CapabilityAttemptReservation.occupiedSlots == baseline }
        for index in 0..<16 {
            let c = CapabilityColdStartConfiguration(directory: f.root.appendingPathComponent("cancel-\(index)"),channel: "beta",installation: "cold-start")
            let task = Task { try await CapabilityColdStartRuntime.openOwned(configuration: c,installed: f.execution.installed,environment: .init(wall: { 1000 })) }
            task.cancel(); do { let completed = try await task.value; await completed.close() } catch {}
            try await eventually("cancelled open leaked") { CapabilityAttemptReservation.occupiedSlots == baseline }
        }
    }
}
