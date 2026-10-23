import Foundation
import Crypto
import MixerCapabilities
import MixerUpdates
@testable import MixerExperimentalCapabilityRuntime
@testable import MixerCapabilityActivation
import XCTest

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
        let original = Bundle.module.url(forResource: "identity.json", withExtension: nil, subdirectory: "Fixtures")!
        var object = try JSONSerialization.jsonObject(with: Data(contentsOf: original)) as! [String: Any]
        object["capabilities"] = []
        let scope = UpdateScope(organization: "material-test", project: "material-test", app: "material-test", environment: "development", platform: "ios")
        let roots = try JSONEncoder().encode([TrustRoot(keyID: "transition", publicKey: key.publicKey.rawRepresentation, scope: scope,
            artifact: true, assignment: true, notBeforeUnix: 1, notAfterUnix: keyEnd)])
        var build = object["build"] as! [String: Any]; build["trust_roots_sha256"] = ReleaseVerifier.sha256(roots); object["build"] = build
        let bridge = try Data(contentsOf: Bundle.module.url(forResource: "bridge.json", withExtension: nil, subdirectory: "Fixtures")!)
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

final class CapabilityRecoveryTransitionTests: XCTestCase, @unchecked Sendable {
    private func fixture() throws -> TransitionFixture {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-transition-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        addTeardownBlock { try FileManager.default.removeItem(at: parent) }
        return try TransitionFixture(directory: parent.appendingPathComponent("private"))
    }
    private func open(_ f: TransitionFixture, _ clock: TransitionTime, environment: CapabilityRecoveryEnvironment? = nil) async throws -> (CapabilityRecoveryStore, CapabilityAttemptReservation) {
        let owner = try CapabilityAttemptReservation.acquire()
        do { return (try await CapabilityRecoveryStore.open(admission: owner.issueStoreAdmission(), installed: f.installed,
            configuration: f.configuration, environment: environment ?? clock.environment), owner) }
        catch { owner.beginClosing(); throw error }
    }
    private func close(_ store: CapabilityRecoveryStore, _ owner: CapabilityAttemptReservation) async {
        owner.beginClosing(); await store.close(); XCTAssertTrue(owner.isReleased)
    }
    private func stage(_ f: TransitionFixture, _ store: CapabilityRecoveryStore, _ payload: Data = TransitionFixture.wasm(), sequence: UInt64 = 1, fuel: UInt64 = 1000) async throws {
        let (m,a) = try f.documents(payload, sequence: sequence, fuel: fuel)
        try await store.beginDownload(signedManifest: m, signedAssignment: a)
        if try await store.downloadOffset() == 0 { try await store.appendDownload(payload, atOffset: 0) }
        try await store.finishDownload()
    }
    private func selected(_ store: CapabilityRecoveryStore) async throws -> (CapabilityConsumedStartup, CapabilityAttemptSignals) {
        let prepared = try await store.prepareStartupSelection()
        let selected = try XCTUnwrap(prepared)
        let signals = CapabilityAttemptSignals(generation: selected.generation)
        return (try await store.consume(selected, signals: signals), signals)
    }
    private func native(_ input: CapabilityConsumedStartup) async throws -> ExperimentalCapabilitySession {
        try await ExperimentalCapabilitySession.prepare(module: input.module, startupExport: input.startupExport,
            configuration: input.policy.native, policy: input.policy.policy, adapters: .init()).create()
    }
    private func earnHealth(_ input: CapabilityConsumedStartup, _ signals: CapabilityAttemptSignals,
                            _ store: CapabilityRecoveryStore, _ clock: TransitionTime) async throws {
        let session = try await native(input); defer { session.close() }
        _ = try await session.startup()
        try await store.recordEffectsIntent(input, signals: signals)
        try await session.enableEffects()
        try await store.confirmEffectsEnabled(input, signals: signals)
        try await store.reportMilestone(input, id: "feature_started")
        try await store.reportMilestone(input, id: "first_screen")
        clock.set(uptime: clock.mono() + 1_000_000_000)
        let committed = try await store.commitHealth(input, signals: signals); XCTAssertTrue(committed)
    }
    private func disk(_ f: TransitionFixture) throws -> CapabilityRecoveryState {
        try StrictJSON.decode(CapabilityRecoveryState.self, from: Data(contentsOf: f.directory.appendingPathComponent("state.json")))
    }
    func testSelectionOneShotForeignStoreSignalsAndDurableAttemptBeforeConstruction() async throws {
        let f = try fixture(), clock = TransitionTime(), (store, owner) = try await open(f, clock)
        try await stage(f, store)
        let prepared = try await store.prepareStartupSelection()
        let selection = try XCTUnwrap(prepared)
        XCTAssertEqual(try disk(f).attempt?.launchID, selection.launchID)
        let wrong = CapabilityAttemptSignals(generation: selection.generation + 1)
        do { _ = try await store.consume(selection, signals: wrong); XCTFail("Foreign generation") } catch {}
        let signals = CapabilityAttemptSignals(generation: selection.generation)
        let input = try await store.consume(selection, signals: signals)
        do { _ = try await store.consume(selection, signals: signals); XCTFail("Consumed twice") } catch {}
        let foreign = CapabilityAttemptSignals(generation: signals.generation)
        do { try await store.recordEffectsIntent(input, signals: foreign); XCTFail("Equal numeric generation accepted") } catch {}
        let other = try fixture(), (store2, owner2) = try await open(other, clock)
        do { _ = try await store2.consume(selection, signals: signals); XCTFail("Foreign store") } catch {}
        do { try await stage(f, store, sequence: 2); XCTFail("Download after selection") } catch {}
        XCTAssertEqual(input.module, TransitionFixture.wasm()); XCTAssertFalse(try disk(f).attempt!.effectsMayHaveOpened)
        await close(store2, owner2); await close(store, owner)
    }
    func testRealStartupEnableMilestonesAndObservationAreSeparate() async throws {
        let f = try fixture(), clock = TransitionTime(), (store, owner) = try await open(f, clock)
        try await stage(f, store); let (input, signals) = try await selected(store), session = try await native(input)
        _ = try await session.startup()
        do { try await store.confirmEffectsEnabled(input, signals: signals); XCTFail("Enable without intent") } catch {}
        do { try await store.reportMilestone(input, id: "first_screen"); XCTFail("Pre-enable milestone") } catch {}
        try await store.recordEffectsIntent(input, signals: signals); XCTAssertTrue(try disk(f).attempt!.effectsMayHaveOpened)
        try await session.enableEffects(); try await store.confirmEffectsEnabled(input, signals: signals)
        do { _ = try await store.commitHealth(input, signals: signals); XCTFail("No milestones") } catch {}
        try await store.reportMilestone(input, id: "feature_started"); try await store.reportMilestone(input, id: "feature_started")
        try await store.reportMilestone(input, id: "first_screen")
        do { try await store.reportMilestone(input, id: "invented"); XCTFail("Uninstalled milestone") } catch {}
        do { try await store.reportMilestone(input, id: String(repeating: "é", count: 600_000)); XCTFail("Unbounded milestone") } catch {}
        do { _ = try await store.commitHealth(input, signals: signals); XCTFail("No observation") } catch {}
        clock.set(uptime: 0)
        do { _ = try await store.commitHealth(input, signals: signals); XCTFail("Backward clock") } catch {}
        clock.set(uptime: 1_001_000_000)
        let health = try await store.commitHealth(input, signals: signals); XCTAssertTrue(health)
        XCTAssertEqual(store.snapshot.healthy, input.candidateID); XCTAssertTrue(store.snapshot.incompleteAttempt)
        session.close(); await close(store, owner)
    }
    func testExactCommittedHealthyCanRevalidateAfterRootExpiryAndRerunObservation() async throws {
        let f = try fixture(), clock = TransitionTime(), (store, owner) = try await open(f, clock)
        try await stage(f, store); let (first, signals) = try await selected(store)
        try await earnHealth(first, signals, store, clock); let original = try disk(f).candidates[first.candidateID]!
        await close(store, owner)
        clock.set(wall: 2000, uptime: 2_000_000_000)
        let (again, next) = try await open(f, clock)
        XCTAssertEqual(try disk(f).lastRecovery, "unknown_interruption_after_effects")
        let (retained, current) = try await selected(again)
        if case .retained = retained.evidence {} else { XCTFail("Expired fresh authority used") }
        XCTAssertEqual(retained.candidateID, first.candidateID)
        XCTAssertEqual(try disk(f).candidates[retained.candidateID]?.signedManifest, original.signedManifest)
        do { _ = try f.installed.verifier.verifyArtifact(signedManifest: original.signedManifest, payload: retained.module, now: clock.now()); XCTFail("Ordinary expiry bypass") } catch {}
        try await earnHealth(retained, current, again, clock)
        XCTAssertNotEqual(try disk(f).healthy?.launchID, first.launchID)
        await close(again, next)
    }
    func testExpiredNeverHealthyAndCorruptPayloadHaveNoAttemptOrRetainedAuthority() async throws {
        for corrupt in [false, true] {
            let f = try fixture(), clock = TransitionTime(), (store, owner) = try await open(f, clock)
            try await stage(f, store)
            if corrupt {
                let hash = ReleaseVerifier.sha256(TransitionFixture.wasm())
                try Data([1]).write(to: f.directory.appendingPathComponent(hash + ".payload"))
            } else { clock.set(wall: 2000) }
            let result = try await store.prepareStartupSelection(); XCTAssertNil(result)
            XCTAssertNil(try disk(f).attempt); XCTAssertNil(try disk(f).healthy)
            XCTAssertEqual(try disk(f).lastRecovery, "selection_rejected"); XCTAssertTrue(try disk(f).failures.isEmpty)
            await close(store, owner)
        }
    }
    func testRealTrapCountsByArtifactAndOnlyOneRetainedFallbackBeforeEffects() async throws {
        let f = try fixture(), clock = TransitionTime(), (seed, seedOwner) = try await open(f, clock)
        try await stage(f, seed); let (healthy, hs) = try await selected(seed); try await earnHealth(healthy, hs, seed, clock)
        await close(seed, seedOwner)
        let (store, owner) = try await open(f, clock), bad = TransitionFixture.wasm(startup: [0])
        try await stage(f, store, bad, sequence: 2)
        let (input, signals) = try await selected(store), session = try await native(input)
        do { _ = try await session.startup(); XCTFail("Trap ignored") }
        catch let error as ExperimentalCapabilityError { signals.recordTerminalFailure(error.failure); XCTAssertEqual(error.failure.kind, .guestTrap(.unreachable)) }
        session.close()
        let result = try await store.failAndPrepareFallback(input, signals: signals)
        guard case .selection(let selection) = result else { XCTFail("No healthy fallback"); await close(store, owner); return }
        XCTAssertEqual(selection.source, .retained); XCTAssertEqual(try disk(f).failures.values.first, 1)
        let secondSignals = CapabilityAttemptSignals(generation: selection.generation), second = try await store.consume(selection, signals: secondSignals)
        secondSignals.recordTerminalFailure(.init(kind: .unknown(.unrecognizedCode), operation: .startup, code: "future", nativeStatus: 2, location: nil))
        guard case .nativeFallback = try await store.failAndPrepareFallback(second, signals: secondSignals) else { XCTFail("Second retained retry"); await close(store, owner); return }
        XCTAssertNil(try disk(f).attempt); XCTAssertEqual(try disk(f).acceptedSequence, 2)
        await close(store, owner)
    }
    func testTerminalAfterEffectsAndAfterHealthNeverSwitchesLiveGuest() async throws {
        for healthy in [false, true] {
            let f = try fixture(), clock = TransitionTime(), (store, owner) = try await open(f, clock)
            try await stage(f, store); let (input, signals) = try await selected(store)
            if healthy { try await earnHealth(input, signals, store, clock) }
            else { try await store.recordEffectsIntent(input, signals: signals) }
            signals.requestStop(.cancelled)
            guard case .recoveryRequired = try await store.failAndPrepareFallback(input, signals: signals) else { XCTFail("Live fallback after effects"); await close(store, owner); return }
            XCTAssertEqual(try disk(f).lastRecovery, "effects_cancelled"); XCTAssertNil(try disk(f).attempt)
            XCTAssertTrue(try disk(f).failures.isEmpty)
            if healthy { XCTAssertNotNil(try disk(f).healthy) }
            do { _ = try await store.prepareStartupSelection(); XCTFail("Recovery escaped") } catch {}
            await close(store, owner)
        }
    }
    func testHealthPostcommitTerminalRereadAndUncertainIntentPoison() async throws {
        for failsWrite in [false, true] {
            let f = try fixture(), clock = TransitionTime(), fault = TransitionFault()
            var env = clock.environment; env.fault = { try fault.check($0) }
            let (store, owner) = try await open(f, clock, environment: env)
            try await stage(f, store); let (input, signals) = try await selected(store)
            if failsWrite {
                fault.arm { throw UpdateError("test.fault", "Intent sync") }
                do { try await store.recordEffectsIntent(input, signals: signals); XCTFail("Uncertain intent enabled") } catch {}
                XCTAssertTrue(signals.snapshot.effectsMayHaveOpened); XCTAssertTrue(store.snapshot.requiresReopen)
            } else {
                let session = try await native(input); _ = try await session.startup()
                try await store.recordEffectsIntent(input, signals: signals); try await session.enableEffects()
                try await store.confirmEffectsEnabled(input, signals: signals)
                try await store.reportMilestone(input, id: "feature_started"); try await store.reportMilestone(input, id: "first_screen")
                clock.set(uptime: clock.mono() + 1_000_000_000)
                fault.arm { signals.requestStop(.deadline) }
                let result = try await store.commitHealth(input, signals: signals)
                XCTAssertFalse(result); XCTAssertNotNil(try disk(f).healthy)
                guard case .recoveryRequired = try await store.failAndPrepareFallback(input, signals: signals) else { XCTFail("Health hid terminal"); session.close(); await close(store, owner); return }
                session.close()
            }
            await close(store, owner)
        }
    }
    func testSelectionValidationCloseKeepsOuterOwnerUntilActualReturn() async throws {
        let f = try fixture(), clock = TransitionTime(), (seed, seedOwner) = try await open(f, clock)
        try await stage(f, seed); await close(seed, seedOwner)
        let gate = TransitionGate(); var env = clock.environment; env.afterValidation = { await gate.pause() }
        let (store, owner) = try await open(f, clock, environment: env)
        let task = Task { try await store.prepareStartupSelection() }
        try await gate.wait(); owner.beginClosing(); await store.close(); XCTAssertFalse(owner.isReleased)
        await gate.release(); do { _ = try await task.value; XCTFail("Closed selection") } catch {}
        XCTAssertTrue(owner.isReleased); XCTAssertNil(try disk(f).attempt)
    }
    func testCheckedDeterministicMapRejectsWrongOperationsStatusCodesAndResources() {
        let deterministic: [(ExperimentalCapabilityFailureKind, String)] = [
            (.guestTrap(.unreachable), "unreachable"), (.guestTrap(.hostAbort), "host_abort"),
            (.resource(.fuel), "fuel_exhausted"), (.resource(.hostCalls), "host_call_limit"),
            (.resource(.callDepth), "call_depth_exceeded"), (.resource(.operandStack), "operand_stack_exceeded")]
        for (kind, code) in deterministic {
            for operation in [ExperimentalCapabilityFailureOperation.startup, .invocation, .wake] {
                for status in [UInt32(1),2,3,4] {
                    let signals = CapabilityAttemptSignals(generation: 1)
                    signals.recordTerminalFailure(.init(kind: kind, operation: operation, code: code, nativeStatus: status, location: nil))
                    XCTAssertEqual(CapabilityRecoveryFailure.classify(signals.snapshot), status == 2 ? .deterministicTrap : .unknownInterruption)
                }
            }
            for operation in [ExperimentalCapabilityFailureOperation.validation, .construction, .post, .enableEffects, .close] {
                let signals = CapabilityAttemptSignals(generation: 1)
                signals.recordTerminalFailure(.init(kind: kind, operation: operation, code: code, nativeStatus: 2, location: nil))
                XCTAssertEqual(CapabilityRecoveryFailure.classify(signals.snapshot), .unknownInterruption)
            }
        }
        for kind in [ExperimentalCapabilityFailureKind.resource(.requestIdentityExhaustion), .resource(.capabilityPayloadAllocation), .resource(.nativeSessionCapacity), .unknown(.unrecognizedCode)] {
            let signals = CapabilityAttemptSignals(generation: 1)
            signals.recordTerminalFailure(.init(kind: kind, operation: .startup, code: "fuel_exhausted", nativeStatus: 2, location: nil))
            XCTAssertEqual(CapabilityRecoveryFailure.classify(signals.snapshot), .unknownInterruption)
        }
        let local = CapabilityAttemptSignals(generation: 1); local.requestStop(.cancelled)
        local.recordTerminalFailure(.init(kind: .resource(.fuel), operation: .startup, code: "fuel_exhausted", nativeStatus: 2, location: nil))
        XCTAssertEqual(CapabilityRecoveryFailure.classify(local.snapshot), .cancelled)
    }
}

extension CapabilityRecoveryTransitionTests {
    func testPreparedExpirySafelyDiscardsButForeignConsumeCannotDiscard() async throws {
        for authority in [false, true] {
            let f = try fixture(), clock = TransitionTime(), (store, owner) = try await open(f, clock)
            try await stage(f, store)
            let value = try await store.prepareStartupSelection(), selection = try XCTUnwrap(value)
            let bad = CapabilityAttemptSignals(generation: selection.generation + 1)
            do { _ = try await store.consume(selection, signals: bad); XCTFail("Wrong generation") } catch {}
            XCTAssertNotNil(try disk(f).attempt)
            if authority { clock.set(wall: 2000) } else { clock.set(uptime: selection.startupCutoffUptimeNanoseconds) }
            do { _ = try await store.consume(selection, signals: .init(generation: selection.generation)); XCTFail("Expired consumed") }
            catch CapabilitySelectionConsumeError.rejected {} catch { XCTFail("Wrong rejection \(error)") }
            XCTAssertNil(try disk(f).attempt); XCTAssertFalse(store.snapshot.requiresReopen)
            XCTAssertEqual(try disk(f).lastRecovery, "selection_rejected")
            await close(store, owner)
        }
    }
    func testPreparedDiscardUncertaintyIsTypedReopenNotSafeFallback() async throws {
        let f = try fixture(), clock = TransitionTime(), fault = TransitionFault()
        var env = clock.environment; env.fault = { try fault.check($0) }
        let (store, owner) = try await open(f, clock, environment: env)
        try await stage(f, store)
        let value = try await store.prepareStartupSelection(), selection = try XCTUnwrap(value)
        clock.set(wall: 2000)
        fault.arm { throw UpdateError("test.fault", "Discard uncertainty") }
        do { _ = try await store.consume(selection, signals: .init(generation: selection.generation)); XCTFail("Uncertain discard") }
        catch CapabilitySelectionConsumeError.cleanupRequiresReopen {} catch { XCTFail("Wrong rejection \(error)") }
        XCTAssertTrue(store.snapshot.requiresReopen); await close(store, owner)
    }
    func testSelectionCommitCutoffDiscardsAttemptBeforePublication() async throws {
        let f = try fixture(), clock = TransitionTime(), fault = TransitionFault()
        var env = clock.environment; env.fault = { try fault.check($0) }
        let (store, owner) = try await open(f, clock, environment: env)
        try await stage(f, store)
        fault.arm { clock.set(uptime: 60_001_000_000) }
        let value = try await store.prepareStartupSelection()
        XCTAssertNil(value); XCTAssertNil(try disk(f).attempt); XCTAssertFalse(store.snapshot.requiresReopen)
        await close(store, owner)
    }
    func testArtifactQuarantineSurvivesGreaterAssignmentAndColdReopen() async throws {
        let f = try fixture(), clock = TransitionTime(), bad = TransitionFixture.wasm(startup: [0])
        var digest: String?
        for sequence in [UInt64(1),2] {
            let (store, owner) = try await open(f, clock)
            try await stage(f, store, bad, sequence: sequence)
            let (input, signals) = try await selected(store), session = try await native(input)
            do { _ = try await session.startup(); XCTFail("Unreachable accepted") }
            catch let e as ExperimentalCapabilityError { signals.recordTerminalFailure(e.failure) }
            session.close()
            guard case .nativeFallback = try await store.failAndPrepareFallback(input, signals: signals) else { XCTFail("No healthy existed"); await close(store, owner); return }
            let state = try disk(f); digest = state.candidates[input.candidateID]!.artifactSHA256
            XCTAssertEqual(state.failures[digest!], sequence); XCTAssertNil(state.attempt)
            if sequence == 2 { XCTAssertEqual(state.quarantine[digest!], "deterministic_trap") }
            await close(store, owner)
        }
        let (store, owner) = try await open(f, clock), (m,a) = try f.documents(bad, sequence: 3)
        do { try await store.beginDownload(signedManifest: m, signedAssignment: a); XCTFail("New assignment erased deny history") } catch {}
        XCTAssertEqual(try disk(f).acceptedSequence, 2); XCTAssertNotNil(try disk(f).quarantine[digest!])
        let result = try await store.prepareStartupSelection(); XCTAssertNil(result)
        await close(store, owner)
    }
    func testRealFuelTrapAndRuntimeTrapAfterHealthRemainDeterministic() async throws {
        for fuelLoop in [false, true] {
            let f = try fixture(), clock = TransitionTime(), (store, owner) = try await open(f, clock)
            let program = fuelLoop ? TransitionFixture.wasm(startup: [0x03,0x40,0x0c,0,0x0b]) : TransitionFixture.wasm(wake: [0])
            try await stage(f, store, program, fuel: 100)
            let (input, signals) = try await selected(store), session = try await native(input)
            if fuelLoop {
                do { _ = try await session.startup(); XCTFail("Loop completed") }
                catch let e as ExperimentalCapabilityError { XCTAssertEqual(e.failure.kind, .resource(.fuel)); signals.recordTerminalFailure(e.failure) }
            } else {
                _ = try await session.startup(); try await store.recordEffectsIntent(input, signals: signals)
                try await session.enableEffects(); try await store.confirmEffectsEnabled(input, signals: signals)
                try await store.reportMilestone(input, id: "feature_started"); try await store.reportMilestone(input, id: "first_screen")
                clock.set(uptime: clock.mono() + 1_000_000_000)
                let health = try await store.commitHealth(input, signals: signals); XCTAssertTrue(health)
                do { _ = try await session.invoke("mixer_guest_capability_ready_v1"); XCTFail("Runtime trap completed") }
                catch let e as ExperimentalCapabilityError { signals.recordTerminalFailure(e.failure); XCTAssertEqual(e.failure.operation, .invocation) }
            }
            session.close(); let result = try await store.failAndPrepareFallback(input, signals: signals)
            if fuelLoop { guard case .nativeFallback = result else { XCTFail("Unexpected recovery"); await close(store, owner); return } }
            else { guard case .recoveryRequired = result else { XCTFail("Live switch"); await close(store, owner); return } }
            XCTAssertEqual(try disk(f).failures.values.first, 1)
            XCTAssertEqual(try disk(f).lastRecovery, fuelLoop ? "deterministic_trap" : "effects_deterministic_trap")
            await close(store, owner)
        }
    }
    func testFreshAuthorityRevalidatedAtIntentAndHealthEntry() async throws {
        for atHealth in [false, true] {
            let f = try fixture(), clock = TransitionTime(), (store, owner) = try await open(f, clock)
            try await stage(f, store); let (input, signals) = try await selected(store)
            if atHealth {
                try await store.recordEffectsIntent(input, signals: signals)
                try await store.confirmEffectsEnabled(input, signals: signals)
                try await store.reportMilestone(input, id: "feature_started"); try await store.reportMilestone(input, id: "first_screen")
                clock.set(uptime: clock.mono() + 1_000_000_000)
            }
            clock.set(wall: 2000)
            if atHealth { do { _ = try await store.commitHealth(input, signals: signals); XCTFail("Expired promoted") } catch {} }
            else { do { try await store.recordEffectsIntent(input, signals: signals); XCTFail("Expired enabled") } catch {} }
            XCTAssertNil(try disk(f).healthy)
            XCTAssertEqual(try disk(f).attempt?.effectsMayHaveOpened, atHealth)
            await close(store, owner)
        }
    }
    func testFallbackBudgetBeginsBeforeFailureCommit() async throws {
        let f = try fixture(), clock = TransitionTime(), fault = TransitionFault()
        let (seed, seedOwner) = try await open(f, clock)
        try await stage(f, seed); let (healthy, hs) = try await selected(seed); try await earnHealth(healthy, hs, seed, clock)
        await close(seed, seedOwner)
        var env = clock.environment; env.fault = { try fault.check($0) }
        let (store, owner) = try await open(f, clock, environment: env)
        try await stage(f, store, TransitionFixture.wasm(startup: [0]), sequence: 2)
        let (input, signals) = try await selected(store)
        signals.recordTerminalFailure(.init(kind: .guestTrap(.unreachable), operation: .startup, code: "unreachable", nativeStatus: 2, location: nil))
        fault.arm { clock.set(uptime: clock.mono() + 60_000_000_000) }
        guard case .nativeFallback = try await store.failAndPrepareFallback(input, signals: signals) else { XCTFail("Failure fsync time omitted"); await close(store, owner); return }
        XCTAssertNil(try disk(f).attempt); XCTAssertEqual(try disk(f).failures.values.first, 1)
        await close(store, owner)
    }
    func testColdIncompleteAttemptNeverInventsDeterministicFailure() async throws {
        let f = try fixture(), clock = TransitionTime(), (store, owner) = try await open(f, clock)
        try await stage(f, store); _ = try await selected(store)
        await close(store, owner)
        let (again, second) = try await open(f, clock)
        XCTAssertNil(try disk(f).attempt); XCTAssertEqual(try disk(f).lastRecovery, "unknown_interruption")
        XCTAssertTrue(try disk(f).failures.isEmpty); XCTAssertTrue(try disk(f).quarantine.isEmpty)
        await close(again, second)
    }
}

extension CapabilityRecoveryTransitionTests {
    func testEveryStateFaultStopsAttemptIntentAndHealthPublicationAndReopenPreservesActualBytes() async throws {
        let points: [CapabilityDurabilityFaultPoint] = [.beforeStateWrite, .beforeStateFileSync, .beforeStateRename, .afterStateRename, .afterStateDirectorySync]
        for phase in 0...2 {
            for point in points {
                let f = try fixture(), clock = TransitionTime()
                let switcher = TransitionStateFault()
                var env = clock.environment; env.fault = { try switcher.check($0) }
                let (store, owner) = try await open(f, clock, environment: env)
                try await stage(f, store)
                var active: CapabilityConsumedStartup?, signals: CapabilityAttemptSignals?, session: ExperimentalCapabilitySession?
                if phase > 0 {
                    let pair = try await selected(store); active = pair.0; signals = pair.1
                    session = try await native(pair.0); _ = try await session!.startup()
                    if phase == 2 {
                        try await store.recordEffectsIntent(pair.0, signals: pair.1); try await session!.enableEffects()
                        try await store.confirmEffectsEnabled(pair.0, signals: pair.1)
                        try await store.reportMilestone(pair.0, id: "feature_started"); try await store.reportMilestone(pair.0, id: "first_screen")
                        clock.set(uptime: clock.mono() + 1_000_000_000)
                    }
                }
                switcher.arm(point)
                do {
                    if phase == 0 { _ = try await store.prepareStartupSelection() }
                    else if phase == 1 { try await store.recordEffectsIntent(active!, signals: signals!) }
                    else { _ = try await store.commitHealth(active!, signals: signals!) }
                    XCTFail("Durability fault ignored \(phase) \(point)")
                } catch {}
                XCTAssertTrue(store.snapshot.requiresReopen)
                if phase == 1 { XCTAssertTrue(signals!.snapshot.effectsMayHaveOpened) }
                let committed = [.afterStateRename, .afterStateDirectorySync].contains(point)
                let saved = try disk(f)
                if phase == 0 { XCTAssertEqual(saved.attempt != nil, committed) }
                if phase == 1 { XCTAssertEqual(saved.attempt?.effectsMayHaveOpened, committed) }
                if phase == 2 { XCTAssertEqual(saved.healthy != nil, committed) }
                session?.close(); await close(store, owner)
                let (again, next) = try await open(f, clock)
                XCTAssertNil(try disk(f).attempt); XCTAssertEqual(try disk(f).acceptedSequence, 1)
                XCTAssertTrue(try disk(f).failures.isEmpty)
                if phase == 2 { XCTAssertEqual(try disk(f).healthy != nil, committed) }
                await close(again, next)
            }
        }
    }
    func testCancelledSelectionValidationAndStoppedIntentCannotPublish() async throws {
        let f = try fixture(), clock = TransitionTime(), (seed, so) = try await open(f, clock)
        try await stage(f, seed); await close(seed, so)
        let gate = TransitionGate(); var env = clock.environment; env.afterValidation = { await gate.pause() }
        let (store, owner) = try await open(f, clock, environment: env)
        let task = Task { try await store.prepareStartupSelection() }
        try await gate.wait(); task.cancel(); await gate.release()
        do { _ = try await task.value; XCTFail("Cancelled selected") } catch {}
        XCTAssertNil(try disk(f).attempt); await close(store, owner)
        let (again, next) = try await open(f, clock)
        let (input, signals) = try await selected(again)
        signals.requestStop(.cancelled)
        do { try await again.recordEffectsIntent(input, signals: signals); XCTFail("Stopped intent entered") } catch {}
        XCTAssertFalse(signals.snapshot.effectsMayHaveOpened); XCTAssertFalse(try disk(f).attempt!.effectsMayHaveOpened)
        await close(again, next)
    }
    func testFailureCommitRequiresRealTerminalLatchAndRetainedCorruptionCannotBecomeFreshProof() async throws {
        let f = try fixture(), clock = TransitionTime(), (store, owner) = try await open(f, clock)
        try await stage(f, store); let (input, signals) = try await selected(store)
        do { _ = try await store.failAndPrepareFallback(input, signals: signals); XCTFail("Invented terminal") } catch {}
        XCTAssertTrue(try disk(f).failures.isEmpty); XCTAssertNotNil(try disk(f).attempt)
        try await earnHealth(input, signals, store, clock); await close(store, owner)
        // Exact signed candidate bytes remain bound even in retained mode. The
        // private-file fixture mutation is corruption, not a health provenance API.
        var state = try disk(f), object = try JSONSerialization.jsonObject(with: JSONEncoder().encode(state)) as! [String: Any]
        var candidates = object["candidates"] as! [String: Any], record = candidates[input.candidateID] as! [String: Any]
        record["signedAssignment"] = Data("{}".utf8).base64EncodedString(); candidates[input.candidateID] = record; object["candidates"] = candidates
        let corrupt = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys]); try corrupt.write(to: f.directory.appendingPathComponent("state.json"))
        do { _ = try await open(f, clock); XCTFail("Retargeted retained record opened") } catch {}
        XCTAssertEqual(try Data(contentsOf: f.directory.appendingPathComponent("state.json")), corrupt)
        state.attempt = nil // Keep the local value visibly unused for execution.
        XCTAssertNotNil(state.healthy)
    }
}
private final class TransitionStateFault: @unchecked Sendable {
    private let lock = NSLock(); private var point: CapabilityDurabilityFaultPoint?
    func arm(_ p: CapabilityDurabilityFaultPoint) { lock.lock(); point = p; lock.unlock() }
    func check(_ p: CapabilityDurabilityFaultPoint) throws {
        lock.lock(); let fail = point == p; if fail { point = nil }; lock.unlock()
        if fail { throw UpdateError("test.fault", p.rawValue) }
    }
}
