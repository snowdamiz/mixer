import Foundation
import Dispatch
import Crypto
import XCTest
import MixerCapabilities
import MixerUpdates
@testable import MixerExperimentalCapabilityRuntime
@testable import MixerCapabilityActivation

private final class ConcreteQueueGate: @unchecked Sendable {
    private let condition = NSCondition()
    private var began = false, open = false
    var entered: Bool { condition.lock(); defer { condition.unlock() }; return began }
    func hold() {
        condition.lock(); began = true; let cutoff = Date().addingTimeInterval(10)
        while !open { if !condition.wait(until: cutoff) { break } }; condition.unlock()
    }
    func release() { condition.lock(); open = true; condition.broadcast(); condition.unlock() }
}

/// Original public TESTONLY seed, signed enclosing bytes and binary encoder.
/// Inputs are issued by the real private store; no issuer key/proof is spoofed.
private struct ConcreteFixture {
    let installed: InstalledMaterial
    let key: Curve25519.Signing.PrivateKey
    let root: URL
    let payload: Data
    init(root: URL, badInitialData: Bool = false) throws {
        self.root = root; payload = Self.wasm(badInitialData: badInitialData)
        key = try .init(rawRepresentation: Data(repeating: 0x71, count: 32))
        func bytes(_ name: String) throws -> Data {
            try Data(contentsOf: Bundle.module.url(forResource: name, withExtension: nil, subdirectory: "Fixtures")!)
        }
        var identity = try JSONSerialization.jsonObject(with: bytes("identity.json")) as! [String: Any]
        let roots = try JSONEncoder().encode([TrustRoot(keyID: "concrete-test", publicKey: key.publicKey.rawRepresentation,
            scope: .init(organization: "material-test", project: "material-test", app: "material-test", environment: "development", platform: "ios"),
            artifact: true, assignment: true, notBeforeUnix: 1, notAfterUnix: 2000)])
        var build = identity["build"] as! [String: Any]; build["trust_roots_sha256"] = ReleaseVerifier.sha256(roots); identity["build"] = build
        let materials: [CapabilityMaterialFile] = [
            .init(role: .bridgePolicy, bytes: try bytes("bridge.json")),
            .init(role: .configuration(capabilityID: CapabilitySchemas.httpID), bytes: try bytes("http.json")),
            .init(role: .configuration(capabilityID: CapabilitySchemas.storageID), bytes: try bytes("storage.json")),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.httpID), bytes: try bytes("http-grant.json")),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.storageID), bytes: try bytes("storage-grant.json"))]
        installed = try InstalledCapabilityExecution(identityJSON: JSONSerialization.data(withJSONObject: identity, options: [.sortedKeys, .withoutEscapingSlashes]),
            materials: materials, trustRootsJSON: roots, privateContainer: root).installed
    }
    var kvDirectory: URL { root.appendingPathComponent("material_test") }
    var configuration: CapabilityRecoveryConfiguration { .init(directory: root.appendingPathComponent("recovery"), channel: "beta", installation: "concrete") }
    func documents() throws -> (Data,Data) {
        let h = installed.identity.installedRuntime, s = h.scope
        let scope = CanonicalValue.object(["organization": .text(s.organization), "project": .text(s.project), "app": .text(s.app), "environment": .text(s.environment), "platform": .text(s.platform)])
        let grant = CanonicalValue.object(["capability_id": .text(CapabilitySchemas.storageID), "schema_sha256": .text(CapabilitySchemas.storageSHA256),
            "permissions": .array([.text("storage.appPrivate")]), "namespaces": .array([.text("material_test")]), "origins": .array([]), "methods": .array([])])
        let manifest = CanonicalValue.object(["schema": .uint(3), "scope": scope, "release_id": .text("concrete"), "source_commit": .text(String(repeating: "7", count: 40)),
            "provenance_id": .text("concrete"), "runtime": .text(h.runtime), "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
            "capability_hashes": .object(h.capabilityHashes.mapValues(CanonicalValue.text)), "state_min": .uint(0), "state_max": .uint(0),
            "payload_sha256": .text(ReleaseVerifier.sha256(payload)), "compressed_bytes": .uint(UInt64(payload.count)), "expanded_bytes": .uint(UInt64(payload.count)),
            "compression": .text("none"), "asset_hashes": .object([:]), "source_map_sha256": .text(String(repeating: "8", count: 64)),
            "limits": .object(["memory_bytes": .uint(65_536), "fuel": .uint(100_000), "startup_milliseconds": .uint(60_000)]),
            "key_id": .text("concrete-test"), "created_at_unix": .uint(100), "capability_grants": .object(["schema": .uint(1),
                "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array([grant])])])
        let assignment = CanonicalValue.object(["schema": .uint(3), "scope": scope, "channel": .text("beta"), "cohort": .text("sha256-v1"), "rollout_basis_points": .uint(10_000),
            "sequence": .uint(1), "release_id": .text("concrete"), "artifact_sha256": .text(ReleaseVerifier.sha256(try manifest.canonicalCBOR())),
            "runtime": .text(h.runtime), "key_id": .text("concrete-test"), "created_at_unix": .uint(100)])
        func sign(_ value: CanonicalValue, assignment: Bool) throws -> Data {
            let prefix = assignment ? "mixer.assignment.v3\0" : "mixer.artifact.v3\0"
            let signature = try key.signature(for: Data(prefix.utf8) + value.canonicalCBOR())
            return try JSONEncoder().encode(CanonicalValue.object([assignment ? "assignment" : "manifest": value, "signature": .text(signature.base64EncodedString())]))
        }
        return (try sign(manifest,assignment: false), try sign(assignment,assignment: true))
    }
    static func wasm(badInitialData: Bool = false) -> Data {
        func u(_ n: Int) -> [UInt8] { var n = n, out: [UInt8] = []; repeat { let b = UInt8(n & 127); n >>= 7; out.append(b | (n == 0 ? 0 : 128)) } while n != 0; return out }
        func signed(_ n: Int) -> [UInt8] {
            var n = n, out: [UInt8] = []
            while true { var b = UInt8(n & 127); n >>= 7; let done = (n == 0 && b & 64 == 0) || (n == -1 && b & 64 != 0); if !done { b |= 128 }; out.append(b); if done { return out } }
        }
        func i(_ n: Int) -> [UInt8] { [0x41] + signed(n) }
        func name(_ s: String) -> [UInt8] { u(s.utf8.count) + Array(s.utf8) }
        func section(_ id: UInt8, _ bytes: [UInt8]) -> [UInt8] { [id] + u(bytes.count) + bytes }
        func body(_ code: [UInt8]) -> [UInt8] { let c = [UInt8(0)] + code + [0x0b]; return u(c.count) + c }
        let args = Array("{\"namespace\":\"material_test\",\"key\":\"concrete\",\"valueBase64\":\"b2s=\"}".utf8)
        var bytes: [UInt8] = [0,97,115,109,1,0,0,0]
        bytes += section(1,[4,0x60,0,0,0x60,3,0x7f,0x7f,0x7f,1,0x7f,0x60,4,0x7e,0x7f,0x7f,0x7f,1,0x7f,0x60,0,1,0x7f])
        bytes += section(2,[2] + name("mixer.capability.v1") + name("storage_put") + [0,1] + name("mixer.capability.v1") + name("poll") + [0,2])
        bytes += section(3,[4,0,0,0,3]); bytes += section(5,[1,1,1,1])
        bytes += section(7,[4] + name("startup") + [0,2] + name("run") + [0,3] + name("mixer_guest_capability_ready_v1") + [0,4] + name("done") + [0,5])
        let run = i(0) + i(args.count) + i(1024) + [0x10,0,0x1a]
        let wake = i(1024) + [0x29,3,0] + i(2048) + i(1024) + i(4096) + [0x10,1,0x1a]
        bytes += section(10,[4] + body([]) + body(run) + body(wake) + body(i(4096) + [0x28,2,0]))
        var data = [UInt8(badInitialData ? 2 : 1),0] + i(0) + [0x0b] + u(args.count) + args
        if badInitialData { data += [0] + i(65_536) + [0x0b,1,7] }
        bytes += section(11,data); return Data(bytes)
    }
}

final class ConcreteAttemptTests: XCTestCase, @unchecked Sendable {
    private func fixture(badInitialData: Bool = false) throws -> ConcreteFixture {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-concrete-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        addTeardownBlock { try FileManager.default.removeItem(at: root) }
        return try ConcreteFixture(root: root,badInitialData: badInitialData)
    }
    private func selected(_ f: ConcreteFixture, environment: CapabilityRecoveryEnvironment = .init(wall: { 1000 })) async throws
        -> (CapabilityRecoveryStore, CapabilityAttemptReservation, CapabilityConsumedStartup, CapabilityAttemptSignals) {
        let owner = try CapabilityAttemptReservation.acquire()
        do {
            let store = try await CapabilityRecoveryStore.open(admission: owner.issueStoreAdmission(),installed: f.installed,configuration: f.configuration,environment: environment)
            do {
                let (m,a) = try f.documents(); try await store.beginDownload(signedManifest: m,signedAssignment: a)
                try await store.appendDownload(f.payload,atOffset: 0); try await store.finishDownload()
                let prepared = try await store.prepareStartupSelection()
                let selection = try XCTUnwrap(prepared)
                let signals = CapabilityAttemptSignals(generation: selection.generation)
                return (store,owner,try await store.consume(selection,signals: signals),signals)
            } catch { owner.beginClosing(); await store.close(); throw error }
        } catch { owner.beginClosing(); throw error }
    }
    private func eventually(_ label: String, _ predicate: () async throws -> Bool) async throws {
        let cutoff = ContinuousClock.now.advanced(by: .seconds(5))
        while !(try await predicate()) { guard ContinuousClock.now < cutoff else { throw UpdateError("test.timeout",label) }; try await Task.sleep(for: .milliseconds(2)) }
    }
    private func close(_ store: CapabilityRecoveryStore, _ owner: CapabilityAttemptReservation, _ signals: CapabilityAttemptSignals) async {
        signals.finishNotifications(); owner.beginClosing(); await store.close(); XCTAssertTrue(owner.isReleased)
    }
    private func reopen(_ f: ConcreteFixture) async throws {
        let reader = try AppPrivateKeyValueStore(directory: f.kvDirectory,namespaces: ["material_test"]); await reader.close()
    }
    func testIOFreeReservationStopAndOneShotWait() async throws {
        let f = try fixture(), (store,owner,input,signals) = try await selected(f)
        let attempt = try CapabilityConcreteAttempt(consumed: input,installed: f.installed,reservation: owner,signals: signals)
        XCTAssertFalse(FileManager.default.fileExists(atPath: f.kvDirectory.path))
        XCTAssertThrowsError(try owner.reserveAdapterGroup())
        let available = 16 - CapabilityAttemptReservation.occupiedSlots
        let others = try (0..<available).map { _ in try CapabilityAttemptReservation.acquire() }
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots,16); XCTAssertThrowsError(try CapabilityAttemptReservation.acquire())
        let token = attempt.stop(); XCTAssertTrue(token.completed)
        let retired = await token.wait(); XCTAssertTrue(retired)
        let duplicate = await token.wait(); XCTAssertFalse(duplicate)
        do { try await attempt.construct(); XCTFail("stopped construction accepted") } catch {}
        XCTAssertFalse(FileManager.default.fileExists(atPath: f.kvDirectory.path))
        let next = try owner.reserveAdapterGroup(); next.retire()
        others.forEach { $0.beginClosing() }; await close(store,owner,signals)
    }
    func testRealStorageDisabledStartupEnableAndRetirement() async throws {
        let f = try fixture(), (store,owner,input,signals) = try await selected(f)
        let attempt = try CapabilityConcreteAttempt(consumed: input,installed: f.installed,reservation: owner,signals: signals)
        try await attempt.construct(); _ = try await attempt.startup()
        do { try await attempt.construct(); XCTFail("duplicate construction accepted") } catch {}
        try await store.recordEffectsIntent(input,signals: signals)
        try await attempt.enableEffects(); try await store.confirmEffectsEnabled(input,signals: signals)
        _ = try await attempt.invoke("run")
        try await eventually("guest did not consume real storage completion") {
            if case .i32(let length)? = try await attempt.invoke("done").value { return length > 0 }; return false
        }
        let retired = await attempt.stop().wait(); XCTAssertTrue(retired); XCTAssertFalse(owner.isReleased)
        let reader = try AppPrivateKeyValueStore(directory: f.kvDirectory,namespaces: ["material_test"])
        let value = try await reader.get(.init(namespace: "material_test",key: "concrete")); await reader.close()
        XCTAssertTrue(value.found); XCTAssertEqual(value.valueBase64,"b2s="); XCTAssertNil(signals.snapshot.firstBridgeFailure)
        let next = try owner.reserveAdapterGroup(); next.retire(); await close(store,owner,signals)
    }
    func testNativeConstructionRejectionClosesAlreadyOpenedKV() async throws {
        let f = try fixture(badInitialData: true), (store,owner,input,signals) = try await selected(f)
        let attempt = try CapabilityConcreteAttempt(consumed: input,installed: f.installed,reservation: owner,signals: signals)
        do { try await attempt.construct(); XCTFail("invalid active data instantiated") }
        catch let error as ExperimentalCapabilityError { XCTAssertEqual(error.failure.kind,.instantiation(.initialDataBounds)) }
        let retired = await attempt.retirement.wait(); XCTAssertTrue(retired)
        XCTAssertEqual(signals.snapshot.firstBridgeFailure?.operation,.construction)
        XCTAssertTrue(FileManager.default.fileExists(atPath: f.kvDirectory.path)); try await reopen(f)
        let next = try owner.reserveAdapterGroup(); next.retire(); await close(store,owner,signals)
    }
    func testCancelSetupAndCancelledWaitCannotClaimRetirement() async throws {
        let f = try fixture(), (store,owner,input,signals) = try await selected(f)
        let gate = ConcreteQueueGate(); ExperimentalQueues.construction.async { gate.hold() }; defer { gate.release() }
        try await eventually("native construction queue not held") { gate.entered }
        let attempt = try CapabilityConcreteAttempt(consumed: input,installed: f.installed,reservation: owner,signals: signals)
        let pending = Task { try await attempt.construct() }
        try await eventually("KV setup not reached") { FileManager.default.fileExists(atPath: f.kvDirectory.path) }
        pending.cancel(); let token = attempt.stop(cause: .cancelled); token.cancelWait()
        let waited = await token.wait(); XCTAssertFalse(waited)
        // Cancellation may win before group creation or after create is queued.
        // The former can retire inline; neither outcome is inferred from wait's
        // false result. Derived barriers qualify the exact retained schedules.
        if !token.completed { XCTAssertThrowsError(try owner.reserveAdapterGroup()) }
        owner.beginClosing(); signals.finishNotifications(); await store.close()
        if !token.completed { XCTAssertFalse(owner.isReleased) }
        gate.release(); do { try await pending.value; XCTFail("cancelled create returned success") } catch {}
        try await eventually("actual cancelled setup did not retire") { token.completed }
        XCTAssertTrue(owner.isReleased); try await reopen(f)
    }
    func testExpiredOriginalCutoffSkipsAdaptersAndDoesNotLeakSlot() async throws {
        let f = try fixture(), (store,owner,input,signals) = try await selected(f,environment: .init(wall: { 1000 },monotonic: { 1 }))
        let attempt = try CapabilityConcreteAttempt(consumed: input,installed: f.installed,reservation: owner,signals: signals)
        do { try await attempt.construct(); XCTFail("expired startup admitted") }
        catch let error as UpdateError { XCTAssertEqual(error.code,"capability.concrete.deadline") }
        let retired = await attempt.retirement.wait(); XCTAssertTrue(retired)
        XCTAssertFalse(FileManager.default.fileExists(atPath: f.kvDirectory.path)); XCTAssertNil(signals.snapshot.firstBridgeFailure)
        if case .local(.deadline)? = signals.snapshot.firstCause {} else { XCTFail("missing exact local deadline") }
        let next = try owner.reserveAdapterGroup(); next.retire(); await close(store,owner,signals)
    }
    func testGenerationMismatchAndRealPreGroupKVInitializerFailure() async throws {
        let f = try fixture(), (store,owner,input,signals) = try await selected(f)
        XCTAssertThrowsError(try CapabilityConcreteAttempt(consumed: input,installed: f.installed,reservation: owner,signals: CapabilityAttemptSignals(generation: signals.generation+1)))
        try Data([0]).write(to: f.kvDirectory)
        let attempt = try CapabilityConcreteAttempt(consumed: input,installed: f.installed,reservation: owner,signals: signals)
        do { try await attempt.construct(); XCTFail("non-directory KV accepted") } catch {}
        let retired = await attempt.retirement.wait(); XCTAssertTrue(retired)
        XCTAssertNil(signals.snapshot.firstBridgeFailure)
        let next = try owner.reserveAdapterGroup(); next.retire(); await close(store,owner,signals)
    }
}
