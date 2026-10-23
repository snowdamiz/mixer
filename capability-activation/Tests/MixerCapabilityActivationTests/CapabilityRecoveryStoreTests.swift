import Foundation
import Crypto
import XCTest
import MixerUpdates
import MixerExperimentalCapabilityRuntime
@testable import MixerCapabilityActivation

private final class StoreClock: @unchecked Sendable {
    private let lock = NSLock(); private var time: UInt64 = 1_000_000
    func now() -> UInt64 { lock.lock(); defer { lock.unlock() }; return time }
    func set(_ value: UInt64) { lock.lock(); time = value; lock.unlock() }
}
private actor StoreGate {
    private var entered = false, released = false
    func pause() async {
        entered = true
        let end = ContinuousClock.now.advanced(by: .seconds(10))
        while !released && ContinuousClock.now < end { await Task.yield() }
    }
    func waitUntilEntered() async throws {
        let end = ContinuousClock.now.advanced(by: .seconds(10))
        while !entered && ContinuousClock.now < end { await Task.yield() }
        guard entered else { throw UpdateError("test.gate", "Fixture did not reach validation gate") }
    }
    func release() { released = true }
}
private final class StoreFault: @unchecked Sendable {
    private let lock = NSLock(); private var selected: CapabilityDurabilityFaultPoint?
    func arm(_ p: CapabilityDurabilityFaultPoint) { lock.lock(); selected = p; lock.unlock() }
    func check(_ p: CapabilityDurabilityFaultPoint) throws {
        lock.lock(); let fail = selected == p; lock.unlock()
        if fail { throw UpdateError("test.fault", p.rawValue) }
    }
}
private struct StoreFixture {
    let execution: InstalledCapabilityExecution
    let key: Curve25519.Signing.PrivateKey
    let payload: Data
    let root: URL
    init(root: URL, payload: Data = Self.wasm(), memory: UInt64 = 4_194_304) throws {
        self.root = root; self.payload = payload
        key = try .init(rawRepresentation: Data(repeating: 0x53, count: 32)) // Original public TESTONLY seed.
        let url = Bundle.module.url(forResource: "identity.json", withExtension: nil, subdirectory: "Fixtures")!
        var identity = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
        identity["capabilities"] = []
        var fields = identity["execution"] as! [String: Any]; fields["memory_bytes"] = memory; identity["execution"] = fields
        let roots = [TrustRoot(keyID: "store-test", publicKey: key.publicKey.rawRepresentation,
            scope: .init(organization: "material-test", project: "material-test", app: "material-test", environment: "development", platform: "ios"),
            artifact: true, assignment: true, notBeforeUnix: 1, notAfterUnix: 20_000)]
        let rootsBytes = try JSONEncoder().encode(roots)
        var build = identity["build"] as! [String: Any]; build["trust_roots_sha256"] = ReleaseVerifier.sha256(rootsBytes); identity["build"] = build
        let bridge = try Data(contentsOf: Bundle.module.url(forResource: "bridge.json", withExtension: nil, subdirectory: "Fixtures")!)
        execution = try .init(identityJSON: JSONSerialization.data(withJSONObject: identity, options: [.sortedKeys, .withoutEscapingSlashes]),
            materials: [.init(role: .bridgePolicy, bytes: bridge)], trustRootsJSON: rootsBytes, privateContainer: root)
    }
    var configuration: CapabilityRecoveryConfiguration { .init(directory: root, channel: "beta", installation: "installation") }
    func signed(_ value: CanonicalValue, assignment: Bool) throws -> Data {
        let signature = try key.signature(for: Data((assignment ? "mixer.assignment.v3\0" : "mixer.artifact.v3\0").utf8) + value.canonicalCBOR())
        return try JSONEncoder().encode(CanonicalValue.object([assignment ? "assignment" : "manifest": value, "signature": .text(signature.base64EncodedString())]))
    }
    func offer(sequence: UInt64 = 1, fuel: UInt64 = 1000, memory: UInt64 = 65_536) throws -> (Data, Data) {
        let h = execution.installed.identity.installedRuntime, s = h.scope
        let scope = CanonicalValue.object(["organization": .text(s.organization), "project": .text(s.project), "app": .text(s.app), "environment": .text(s.environment), "platform": .text(s.platform)])
        let m = CanonicalValue.object(["schema": .uint(3), "scope": scope, "release_id": .text("store-test"), "source_commit": .text(String(repeating: "a", count: 40)),
            "provenance_id": .text("store-test"), "runtime": .text(h.runtime), "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
            "capability_hashes": .object([:]), "state_min": .uint(0), "state_max": .uint(0), "payload_sha256": .text(ReleaseVerifier.sha256(payload)),
            "compressed_bytes": .uint(UInt64(payload.count)), "expanded_bytes": .uint(UInt64(payload.count)), "compression": .text("none"), "asset_hashes": .object([:]),
            "source_map_sha256": .text(String(repeating: "b", count: 64)), "limits": .object(["memory_bytes": .uint(memory), "fuel": .uint(fuel), "startup_milliseconds": .uint(60_000)]),
            "key_id": .text("store-test"), "created_at_unix": .uint(100), "capability_grants": .object(["schema": .uint(1), "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array([])])])
        let a = CanonicalValue.object(["schema": .uint(3), "scope": scope, "channel": .text("beta"), "cohort": .text("sha256-v1"), "rollout_basis_points": .uint(10_000),
            "sequence": .uint(sequence), "release_id": .text("store-test"), "artifact_sha256": .text(ReleaseVerifier.sha256(try m.canonicalCBOR())), "runtime": .text(h.runtime), "key_id": .text("store-test"), "created_at_unix": .uint(100)])
        return (try signed(m, assignment: false) + Data(" \n".utf8), try signed(a, assignment: true) + Data("\t".utf8))
    }
    /// Independently written binary fixture builder; no copied runtime fixtures.
    static func wasm(invalidUncalled: Bool = false, memoryPages: UInt8 = 0) -> Data {
        func name(_ value: String) -> [UInt8] { [UInt8(value.utf8.count)] + Array(value.utf8) }
        func section(_ id: UInt8, _ bytes: [UInt8]) -> [UInt8] { [id, UInt8(bytes.count)] + bytes }
        let exports: [UInt8] = [2] + name("startup") + [0,0] + name("mixer_guest_capability_ready_v1") + [0,1]
        let code: [UInt8] = invalidUncalled ? [3,2,0,0x0b,2,0,0x0b,3,0,0xff,0x0b] : [2,2,0,0x0b,2,0,0x0b]
        var bytes: [UInt8] = [0,97,115,109,1,0,0,0]
        bytes += section(1,[1,0x60,0,0])
        bytes += section(3,invalidUncalled ? [3,0,0,0] : [2,0,0])
        bytes += section(5,[1,0,memoryPages])
        bytes += section(7,exports)
        bytes += section(10,code)
        return Data(bytes)
    }
}

final class CapabilityRecoveryStoreTests: XCTestCase, @unchecked Sendable {
    private func root() throws -> URL {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-store-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        addTeardownBlock { try FileManager.default.removeItem(at: parent) }
        return parent.appendingPathComponent("private")
    }
    private func open(_ f: StoreFixture, environment: CapabilityRecoveryEnvironment = .init(wall: { 1000 })) async throws -> (CapabilityRecoveryStore, CapabilityAttemptReservation) {
        let owner = try CapabilityAttemptReservation.acquire()
        do { return (try await CapabilityRecoveryStore.open(admission: owner.issueStoreAdmission(), installed: f.execution.installed, configuration: f.configuration, environment: environment), owner) }
        catch { owner.beginClosing(); throw error }
    }
    private func assertOffset(_ store: CapabilityRecoveryStore, _ expected: UInt64) async throws {
        let value = try await store.downloadOffset(); XCTAssertEqual(value, expected)
    }
    private func close(_ store: CapabilityRecoveryStore, _ owner: CapabilityAttemptReservation) async {
        owner.beginClosing(); await store.close(); XCTAssertTrue(owner.isReleased)
    }
    func testReserveResumeExactBytesRealValidationAndReopen() async throws {
        let f = try StoreFixture(root: root()), (m,a) = try f.offer()
        let (store, owner) = try await open(f)
        try await store.beginDownload(signedManifest: m, signedAssignment: a)
        XCTAssertEqual(store.snapshot.acceptedSequence, 1)
        try await assertOffset(store, 0)
        let half = f.payload.count / 2
        try await store.appendDownload(f.payload.prefix(half), atOffset: 0)
        await close(store, owner)
        let (reopened, second) = try await open(f)
        try await assertOffset(reopened, UInt64(half))
        try await reopened.appendDownload(f.payload.dropFirst(half), atOffset: UInt64(half))
        try await reopened.finishDownload()
        XCTAssertNotNil(reopened.snapshot.staged); XCTAssertNil(reopened.snapshot.downloading)
        let state = try StrictJSON.decode(CapabilityRecoveryState.self, from: Data(contentsOf: f.root.appendingPathComponent("state.json")))
        let c = try XCTUnwrap(state.candidates.values.first)
        XCTAssertEqual(c.signedManifest, m); XCTAssertEqual(c.signedAssignment, a)
        XCTAssertEqual(c.candidateID, try CapabilityRecoveryCandidate.id(artifact: c.artifactSHA256, sequence: 1, manifest: m, assignment: a))
        XCTAssertEqual(try Data(contentsOf: f.root.appendingPathComponent(c.payloadSHA256 + ".payload")), f.payload)
        await close(reopened, second)
    }
    func testMalformedUncalledBodyNeverStagesAndSequenceStaysReserved() async throws {
        let f = try StoreFixture(root: root(), payload: StoreFixture.wasm(invalidUncalled: true)), (m,a) = try f.offer()
        let (store, owner) = try await open(f)
        try await store.beginDownload(signedManifest: m, signedAssignment: a); try await store.appendDownload(f.payload, atOffset: 0)
        do { try await store.finishDownload(); XCTFail("Malformed body accepted") }
        catch let e as ExperimentalCapabilityError { XCTAssertEqual(e.failure.operation, .validation) }
        XCTAssertNil(store.snapshot.staged); XCTAssertEqual(store.snapshot.acceptedSequence, 1)
        await close(store, owner)
        let (again, second) = try await open(f)
        do { try await again.beginDownload(signedManifest: m, signedAssignment: a); XCTFail("Replay accepted") } catch {}
        XCTAssertEqual(again.snapshot.acceptedSequence, 1); await close(again, second)
    }
    func testZeroPageSignedLimitIsNotRoundedUpAndWasmShapeIsChecked() async throws {
        for pages: UInt8 in [0,1] {
            let f = try StoreFixture(root: root(), payload: StoreFixture.wasm(memoryPages: pages), memory: 1), (m,a) = try f.offer(memory: 1)
            let (store, owner) = try await open(f)
            try await store.beginDownload(signedManifest: m, signedAssignment: a); try await store.appendDownload(f.payload, atOffset: 0)
            if pages == 0 { try await store.finishDownload(); XCTAssertNotNil(store.snapshot.staged) }
            else { do { try await store.finishDownload(); XCTFail("Rounded upward") } catch {} ; XCTAssertNil(store.snapshot.staged) }
            await close(store, owner)
        }
    }
    func testCancelValidationBlocksReplacementAndNeverPublishesLateSuccess() async throws {
        let f = try StoreFixture(root: root()), (m,a) = try f.offer(), gate = StoreGate()
        let (store, owner) = try await open(f, environment: .init(wall: { 1000 }, afterValidation: { await gate.pause() }))
        try await store.beginDownload(signedManifest: m, signedAssignment: a); try await store.appendDownload(f.payload, atOffset: 0)
        let finish = Task { try await store.finishDownload() }
        try await gate.waitUntilEntered(); try await store.cancelDownload()
        XCTAssertNil(store.snapshot.downloading); XCTAssertEqual(store.snapshot.acceptedSequence, 1)
        do { try await store.beginDownload(signedManifest: m, signedAssignment: a); XCTFail("Retired worker counted free") } catch {}
        await gate.release()
        do { try await finish.value; XCTFail("Late success published") } catch {}
        XCTAssertNil(store.snapshot.staged); await close(store, owner)
    }
    func testCloseRetainsOuterSlotUntilValidatorFrameActuallyRetires() async throws {
        let f = try StoreFixture(root: root()), (m,a) = try f.offer(), gate = StoreGate()
        let (store, owner) = try await open(f, environment: .init(wall: { 1000 }, beforeValidation: { await gate.pause() }))
        try await store.beginDownload(signedManifest: m, signedAssignment: a); try await store.appendDownload(f.payload, atOffset: 0)
        let finish = Task { try await store.finishDownload() }
        try await gate.waitUntilEntered(); owner.beginClosing(); await store.close()
        XCTAssertFalse(owner.isReleased); XCTAssertTrue(store.snapshot.closed)
        XCTAssertThrowsError(try owner.issueStoreAdmission()); XCTAssertThrowsError(try owner.reserveAdapterGroup())
        await gate.release(); do { try await finish.value; XCTFail("Closed success") } catch {}
        XCTAssertTrue(owner.isReleased); XCTAssertNil(store.snapshot.staged)
    }
    func testDeadlineAndBackwardClockDiscardValidatedResult() async throws {
        for backwards in [false, true] {
            let f = try StoreFixture(root: root()), (m,a) = try f.offer(), clock = StoreClock(), gate = StoreGate()
            let (store, owner) = try await open(f, environment: .init(wall: { 1000 }, monotonic: { clock.now() }, afterValidation: { await gate.pause() }))
            try await store.beginDownload(signedManifest: m, signedAssignment: a); try await store.appendDownload(f.payload, atOffset: 0)
            let finish = Task { try await store.finishDownload() }
            try await gate.waitUntilEntered(); clock.set(backwards ? 0 : 60_001_000_000); await gate.release()
            do { try await finish.value; XCTFail("Invalid clock result staged") } catch {}
            XCTAssertNil(store.snapshot.staged); XCTAssertEqual(store.snapshot.acceptedSequence, 1); await close(store, owner)
        }
    }
    func testCommitFaultPoisonAndReopenObserveActualHighWater() async throws {
        for point in [CapabilityDurabilityFaultPoint.beforeStateWrite, .beforeStateFileSync, .beforeStateRename, .afterStateRename, .afterStateDirectorySync] {
            let f = try StoreFixture(root: root()), (m,a) = try f.offer(), fault = StoreFault()
            let (store, owner) = try await open(f, environment: .init(wall: { 1000 }, fault: { try fault.check($0) }))
            fault.arm(point)
            do { try await store.beginDownload(signedManifest: m, signedAssignment: a); XCTFail("Fault ignored") } catch {}
            XCTAssertTrue(store.snapshot.requiresReopen)
            do { _ = try await store.downloadOffset(); XCTFail("Poison usable") } catch {}
            await close(store, owner)
            let (again, second) = try await open(f)
            let committed = [CapabilityDurabilityFaultPoint.afterStateRename, .afterStateDirectorySync].contains(point)
            XCTAssertEqual(again.snapshot.acceptedSequence, committed ? 1 : 0)
            await close(again, second)
        }
    }
    func testPartialWriteAndPublishFaultsPreserveActualBytesWithoutStagedClaim() async throws {
        for point in [CapabilityDurabilityFaultPoint.beforePayloadWrite, .beforePayloadSync, .beforePayloadRename, .afterPayloadRename, .afterPayloadDirectorySync] {
            let f = try StoreFixture(root: root()), (m,a) = try f.offer(), fault = StoreFault()
            let (store, owner) = try await open(f, environment: .init(wall: { 1000 }, fault: { try fault.check($0) }))
            try await store.beginDownload(signedManifest: m, signedAssignment: a)
            if [.beforePayloadWrite, .beforePayloadSync].contains(point) {
                fault.arm(point); do { try await store.appendDownload(f.payload, atOffset: 0); XCTFail("Fault ignored") } catch {}
            } else {
                try await store.appendDownload(f.payload, atOffset: 0); fault.arm(point)
                do { try await store.finishDownload(); XCTFail("Fault ignored") } catch {}
            }
            XCTAssertTrue(store.snapshot.requiresReopen); await close(store, owner)
            let (again, second) = try await open(f)
            XCTAssertNil(again.snapshot.staged); XCTAssertEqual(again.snapshot.acceptedSequence, 1)
            if point != .beforePayloadWrite { try await assertOffset(again, UInt64(f.payload.count)); try await again.finishDownload(); XCTAssertNotNil(again.snapshot.staged) }
            else { try await assertOffset(again, 0) }
            await close(again, second)
        }
    }
    func testClosedStateRejectsOldUnknownDuplicateWrongIdentityAndNoReset() async throws {
        let f = try StoreFixture(root: root()), (store, owner) = try await open(f)
        await close(store, owner)
        let url = f.root.appendingPathComponent("state.json"), good = try Data(contentsOf: url)
        var mutations: [Data] = []
        for (field, value) in ["kind": "old", "schemaVersion": 1, "fingerprint": String(repeating: "0", count: 64), "installation": "other", "channel": "other"] as [String: Any] {
            var object = try JSONSerialization.jsonObject(with: good) as! [String: Any]; object[field] = value
            mutations.append(try JSONSerialization.data(withJSONObject: object))
        }
        var object = try JSONSerialization.jsonObject(with: good) as! [String: Any]; object["extra"] = 0
        mutations.append(try JSONSerialization.data(withJSONObject: object))
        let text = String(decoding: good, as: UTF8.self)
        mutations.append(Data(text.replacingOccurrences(of: "\"schemaVersion\":3", with: "\"schemaVersion\":3,\"schemaVersion\":3").utf8))
        for bytes in mutations {
            try bytes.write(to: url)
            do { _ = try await open(f); XCTFail("Bad state reopened") } catch {}
            XCTAssertEqual(try Data(contentsOf: url), bytes)
        }
        try FileManager.default.removeItem(at: url)
        do { _ = try await open(f); XCTFail("Missing existing state reset") } catch {}
        XCTAssertFalse(FileManager.default.fileExists(atPath: url.path))
    }
    func testNewAssignmentHasNewRecordIdentityAndCandidateBound() async throws {
        let f = try StoreFixture(root: root()), (store, owner) = try await open(f)
        var ids = Set<String>()
        for sequence in 1...6 {
            let (m,a) = try f.offer(sequence: UInt64(sequence))
            try await store.beginDownload(signedManifest: m, signedAssignment: a)
            // Content-addressed payload can be reused only after rehashing and
            // repeating real validation; the exact new signed record stays unique.
            if try await store.downloadOffset() == 0 { try await store.appendDownload(f.payload, atOffset: 0) }
            try await store.finishDownload(); ids.insert(try XCTUnwrap(store.snapshot.staged))
            XCTAssertLessThanOrEqual(store.snapshot.retainedCandidates, 4)
        }
        XCTAssertEqual(ids.count, 6); XCTAssertEqual(store.snapshot.acceptedSequence, 6)
        XCTAssertLessThanOrEqual(try FileManager.default.contentsOfDirectory(atPath: f.root.path).filter { $0.hasSuffix(".payload") }.count, 1)
        await close(store, owner)
    }
}

extension CapabilityRecoveryStoreTests {
    func testFourMiBPayloadExactHeadersAndChunkBounds() async throws {
        let base = StoreFixture.wasm(), target = 4_194_304
        let contentLength = target - base.count - 5 // custom id + four-byte u32 length.
        func leb(_ n: Int) -> [UInt8] {
            var n = n, bytes: [UInt8] = []
            repeat { var b = UInt8(n & 127); n >>= 7; if n != 0 { b |= 128 }; bytes.append(b) } while n != 0
            return bytes
        }
        let bytes = base + Data([0] + leb(contentLength)) + Data(repeating: 0, count: contentLength)
        XCTAssertEqual(bytes.count, target)
        let f = try StoreFixture(root: root(), payload: bytes), (m0,a0) = try f.offer()
        let m = m0 + Data(repeating: 32, count: 65_536-m0.count), a = a0 + Data(repeating: 32, count: 65_536-a0.count)
        let (store, owner) = try await open(f)
        do { try await store.beginDownload(signedManifest: m + Data([32]), signedAssignment: a); XCTFail("Oversize header") } catch {}
        XCTAssertEqual(store.snapshot.acceptedSequence, 0)
        try await store.beginDownload(signedManifest: m, signedAssignment: a)
        do { try await store.appendDownload(Data(repeating: 0, count: 1_048_577), atOffset: 0); XCTFail("Oversize chunk") } catch {}
        do { try await store.appendDownload(Data([0]), atOffset: .max); XCTFail("Overflow offset") } catch {}
        try await assertOffset(store, 0)
        for offset in stride(from: 0, to: bytes.count, by: 1_048_576) {
            try await store.appendDownload(bytes.subdata(in: offset..<(offset+1_048_576)), atOffset: UInt64(offset))
        }
        try await store.finishDownload(); XCTAssertNotNil(store.snapshot.staged)
        await close(store, owner)
    }
    func testTaskCancellationAndCurrentAuthorityExpiryCannotStage() async throws {
        for expires in [false, true] {
            let f = try StoreFixture(root: root()), (m,a) = try f.offer(), clock = StoreClock(), gate = StoreGate()
            clock.set(1000)
            let (store, owner) = try await open(f, environment: .init(wall: { clock.now() }, afterValidation: { await gate.pause() }))
            try await store.beginDownload(signedManifest: m, signedAssignment: a); try await store.appendDownload(f.payload, atOffset: 0)
            let finish = Task { try await store.finishDownload() }
            try await gate.waitUntilEntered()
            if expires { clock.set(20_000) } else { finish.cancel() }
            await gate.release()
            do { try await finish.value; XCTFail("Cancelled/expired result published") } catch {}
            XCTAssertNil(store.snapshot.staged); XCTAssertEqual(store.snapshot.acceptedSequence, 1)
            await close(store, owner)
        }
    }
    func testCorruptCachedPayloadCannotBeReusedOrOverwriteReferencedBytes() async throws {
        let f = try StoreFixture(root: root()), (store, owner) = try await open(f)
        let (m,a) = try f.offer()
        try await store.beginDownload(signedManifest: m, signedAssignment: a); try await store.appendDownload(f.payload, atOffset: 0)
        try await store.finishDownload()
        let path = f.root.appendingPathComponent(ReleaseVerifier.sha256(f.payload) + ".payload")
        let corrupt = Data(repeating: 0, count: f.payload.count); try corrupt.write(to: path)
        let (m2,a2) = try f.offer(sequence: 2)
        try await store.beginDownload(signedManifest: m2, signedAssignment: a2)
        do { _ = try await store.downloadOffset(); XCTFail("Corrupt cache treated as complete") } catch {}
        try await store.appendDownload(f.payload, atOffset: 0)
        do { try await store.finishDownload(); XCTFail("Bad destination overwritten") } catch {}
        XCTAssertTrue(store.snapshot.requiresReopen); XCTAssertEqual(try Data(contentsOf: path), corrupt)
        XCTAssertEqual(store.snapshot.acceptedSequence, 2); await close(store, owner)
    }
    func testDiskReserveAndFailedOpenDoNotResetOrLeakObligations() async throws {
        let f = try StoreFixture(root: root()), (m,a) = try f.offer()
        let owner = try CapabilityAttemptReservation.acquire()
        var config = f.configuration; config.reserveDiskBytes = .max
        let store = try await CapabilityRecoveryStore.open(admission: owner.issueStoreAdmission(), installed: f.execution.installed,
            configuration: config, environment: .init(wall: { 1000 }))
        do { try await store.beginDownload(signedManifest: m, signedAssignment: a); XCTFail("Reserve ignored") } catch {}
        XCTAssertEqual(store.snapshot.acceptedSequence, 0); await close(store, owner)
        let failed = try CapabilityAttemptReservation.acquire()
        let invalid = CapabilityRecoveryConfiguration(directory: f.root, channel: String(repeating: "x", count: 129), installation: "installation")
        do {
            _ = try await CapabilityRecoveryStore.open(admission: failed.issueStoreAdmission(), installed: f.execution.installed, configuration: invalid)
            XCTFail("Bad configuration accepted")
        } catch {}
        failed.beginClosing(); XCTAssertTrue(failed.isReleased)
    }
}

private final class StoreCommitGate: @unchecked Sendable {
    let entered = DispatchSemaphore(value: 0), release = DispatchSemaphore(value: 0)
    private let lock = NSLock(); private var point: CapabilityDurabilityFaultPoint?
    func arm(_ point: CapabilityDurabilityFaultPoint) { lock.lock(); self.point = point; lock.unlock() }
    func check(_ current: CapabilityDurabilityFaultPoint) {
        lock.lock(); let pauses = point == current; if pauses { point = nil }; lock.unlock()
        if pauses { entered.signal(); _ = release.wait(timeout: .now() + 10) }
    }
}
extension CapabilityRecoveryStoreTests {
    func testOwnedInputSnapshotsSurviveExternalMutationBeforeFilesystemWrite() async throws {
        let f = try StoreFixture(root: root()), (m,a) = try f.offer(), gate = StoreCommitGate()
        let (store, owner) = try await open(f, environment: .init(wall: { 1000 }, fault: { gate.check($0) }))
        let mp = UnsafeMutableRawPointer.allocate(byteCount: m.count, alignment: 1), ap = UnsafeMutableRawPointer.allocate(byteCount: a.count, alignment: 1)
        defer { mp.deallocate(); ap.deallocate() }
        m.copyBytes(to: mp.assumingMemoryBound(to: UInt8.self), count: m.count); a.copyBytes(to: ap.assumingMemoryBound(to: UInt8.self), count: a.count)
        let md = Data(bytesNoCopy: mp, count: m.count, deallocator: .none), ad = Data(bytesNoCopy: ap, count: a.count, deallocator: .none)
        gate.arm(.beforeStateWrite)
        let begin = Task { try await store.beginDownload(signedManifest: md, signedAssignment: ad) }
        XCTAssertEqual(gate.entered.wait(timeout: .now() + 10), .success)
        mp.initializeMemory(as: UInt8.self, repeating: 0x21, count: m.count); ap.initializeMemory(as: UInt8.self, repeating: 0x21, count: a.count)
        gate.release.signal(); try await begin.value
        let decoded = try StrictJSON.decode(CapabilityRecoveryState.self, from: Data(contentsOf: f.root.appendingPathComponent("state.json")))
        XCTAssertEqual(decoded.pending?.signedManifest, m); XCTAssertEqual(decoded.pending?.signedAssignment, a)
        try await store.appendDownload(f.payload, atOffset: 0); try await store.finishDownload()
        await close(store, owner)
    }
    func testCancellationAfterCommitEntryReportsActualDurableReservation() async throws {
        let f = try StoreFixture(root: root()), (m,a) = try f.offer(), gate = StoreCommitGate()
        let (store, owner) = try await open(f, environment: .init(wall: { 1000 }, fault: { gate.check($0) }))
        gate.arm(.beforeStateFileSync)
        let begin = Task { try await store.beginDownload(signedManifest: m, signedAssignment: a) }
        XCTAssertEqual(gate.entered.wait(timeout: .now() + 10), .success)
        begin.cancel(); gate.release.signal()
        do { try await begin.value; XCTFail("Cancellation hidden") } catch {}
        XCTAssertEqual(store.snapshot.acceptedSequence, 1); XCTAssertFalse(store.snapshot.requiresReopen)
        await close(store, owner)
        let (again, second) = try await open(f)
        XCTAssertEqual(again.snapshot.acceptedSequence, 1); XCTAssertNotNil(again.snapshot.downloading)
        await close(again, second)
    }
    func testZZAbandonedOpenFacadePinsOwnerAndDoesNotCloseDirectoryOnCaller() async throws {
        let f = try StoreFixture(root: root())
        let owner = try CapabilityAttemptReservation.acquire()
        var store: CapabilityRecoveryStore? = try await CapabilityRecoveryStore.open(admission: owner.issueStoreAdmission(),
            installed: f.execution.installed, configuration: f.configuration, environment: .init(wall: { 1000 }))
        weak var weakStore = store
        XCTAssertNotNil(store); store = nil; XCTAssertNil(weakStore); weakStore = nil; XCTAssertNil(weakStore)
        owner.beginClosing(); XCTAssertTrue(owner.isQuarantined); XCTAssertFalse(owner.isReleased)
        // If the actor/directory had been destroyed by façade deinit, this would
        // acquire the flock. The counted retained actor keeps its actual FD open.
        do { _ = try await open(f); XCTFail("Abandoned directory was implicitly closed") } catch {}
    }
}
