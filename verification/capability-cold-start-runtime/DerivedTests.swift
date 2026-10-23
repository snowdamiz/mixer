import Foundation
import XCTest
import MixerCapabilities
import MixerUpdates
@testable import MixerCapabilityActivation

private final class ColdStartValidationCounter: @unchecked Sendable {
    private let lock = NSLock(); private var value = 0
    func increment() { lock.lock(); value += 1; lock.unlock() }
    var count: Int { lock.lock(); defer { lock.unlock() }; return value }
}

/// These tests run only against a captured source copy. The small export driver
/// is absent from production and does not qualify public post-enable event/UI
/// ingress. All signed verification, native VM, durable store and KV are real.
final class CapabilityColdStartDerivedTests: XCTestCase, @unchecked Sendable {
    private func fixture() throws -> ColdStartFixture {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-cold-derived-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root,withIntermediateDirectories: false)
        addTeardownBlock { try FileManager.default.removeItem(at: root) }; return try ColdStartFixture(root: root)
    }
    private func eventually(_ predicate: () async throws -> Bool) async throws {
        let cutoff = ContinuousClock.now.advanced(by: .seconds(8))
        while !(try await predicate()) {
            guard ContinuousClock.now < cutoff else { throw UpdateError("derived.timeout","Predicate did not become true") }
            try await Task.sleep(for: .milliseconds(2))
        }
    }
    private func stage(_ f: ColdStartFixture,_ runtime: CapabilityColdStartRuntime,_ bytes: Data,storage: Bool = false) async throws {
        let (m,a) = try f.documents(bytes,storage: storage)
        try await runtime.beginDownload(signedManifest: m,signedAssignment: a); try await runtime.appendDownload(bytes,atOffset: 0); try await runtime.finishDownload()
    }
    func testCheckedStartupFailureCloseBeforeUnwindPersistsExactlyOnce() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), validations = ColdStartValidationCounter()
        let runtime = try await CapabilityColdStartRuntime.openOwned(configuration: f.configuration,installed: f.execution.installed,
            environment: .init(wall: { 1000 },beforeValidation: { validations.increment() }))
        try await stage(f,runtime,ColdStartFixture.wasm(trap: true))
        await ColdStartDerivedHooks.startupFailure.arm()
        let startup = Task { try await runtime.start() }; try await ColdStartDerivedHooks.startupFailure.wait()
        let before = validations.count
        let checked = await runtime.recoverySnapshot(); XCTAssertNotNil(checked.activation.firstBridgeFailure)
        let closing = Task { await runtime.close() }
        try await eventually { (await runtime.recoverySnapshot()).activation.phase == .closed }
        await ColdStartDerivedHooks.startupFailure.release()
        do { _ = try await startup.value; XCTFail("Closed startup returned live") } catch {}
        await closing.value
        let state = try StrictJSON.decode(CapabilityRecoveryState.self,from: Data(contentsOf: f.configuration.directory.appendingPathComponent("state.json")))
        XCTAssertEqual(Array(state.failures.values),[1]); XCTAssertNil(state.attempt); XCTAssertNil(state.staged)
        XCTAssertEqual(state.lastRecovery,"deterministic_trap"); XCTAssertEqual(validations.count,before)
        try await eventually { CapabilityAttemptReservation.occupiedSlots == baseline }
    }
    func testBusyOrdinaryTailRepokesTerminalAndRetainsOpenCleanupDiagnostic() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        let runtime = try await CapabilityColdStartRuntime.openOwned(configuration: f.configuration,installed: f.execution.installed,environment: .init(wall: { 1000 }))
        try await stage(f,runtime,storageWasm(wakeTrap: true),storage: true); _ = try await runtime.start()
        await ColdStartDerivedHooks.ordinaryTail.arm()
        let event = Task { try await runtime.derivedInvoke("write") }
        try await ColdStartDerivedHooks.ordinaryTail.wait()
        try await eventually { (await runtime.recoverySnapshot()).activation.firstBridgeFailure != nil }
        let stopped = await runtime.recoverySnapshot(); XCTAssertEqual(stopped.activation.phase,.recoveryRequired)
        await ColdStartDerivedHooks.ordinaryTail.release(); _ = try await event.value
        try await eventually { !(await runtime.recoverySnapshot()).incompleteAttempt }
        let state = try StrictJSON.decode(CapabilityRecoveryState.self,from: Data(contentsOf: f.configuration.directory.appendingPathComponent("state.json")))
        XCTAssertEqual(Array(state.failures.values),[1]); XCTAssertTrue(state.lastRecovery.hasPrefix("effects_")); XCTAssertNil(state.staged)
        await runtime.close(); try await eventually { CapabilityAttemptReservation.occupiedSlots == baseline }
    }
    func testRealKVWriteAfterEnableAndActualExitBeforeReopen() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        let runtime = try await CapabilityColdStartRuntime.openOwned(configuration: f.configuration,installed: f.execution.installed,environment: .init(wall: { 1000 }))
        try await stage(f,runtime,storageWasm(),storage: true); let result = try await runtime.start()
        XCTAssertEqual(result.phase,.provisionalGuest)
        _ = try await runtime.derivedInvoke("write")
        try await eventually {
            if case .i32(let length)? = try await runtime.derivedInvoke("done").value { return length > 0 }; return false
        }
        await runtime.close(); try await eventually { CapabilityAttemptReservation.occupiedSlots == baseline }
        let reader = try AppPrivateKeyValueStore(directory: f.root.appendingPathComponent("material_test"),namespaces: ["material_test"])
        let value = try await reader.get(.init(namespace: "material_test",key: "cold-coordinator")); await reader.close()
        XCTAssertTrue(value.found); XCTAssertEqual(value.valueBase64,"AAH+/w==")
    }
    func testObservationWakeWhileOrdinaryBusyIsReconciledOnLogicalTail() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        let runtime = try await CapabilityColdStartRuntime.openOwned(configuration: f.configuration,installed: f.execution.installed,environment: .init(wall: { 1000 }))
        try await stage(f,runtime,ColdStartFixture.wasm()); _ = try await runtime.start()
        try await runtime.reportMilestone("feature_started"); try await runtime.reportMilestone("first_screen")
        await ColdStartDerivedHooks.ordinaryTail.arm()
        let event = Task { try await runtime.derivedInvoke("startup") }; try await ColdStartDerivedHooks.ordinaryTail.wait()
        try await Task.sleep(for: .milliseconds(1100))
        let busy = await runtime.recoverySnapshot(); XCTAssertNil(busy.healthy)
        await ColdStartDerivedHooks.ordinaryTail.release(); _ = try await event.value
        try await eventually { (await runtime.recoverySnapshot()).activation.phase == .healthyGuest }
        await runtime.close(); try await eventually { CapabilityAttemptReservation.occupiedSlots == baseline }
    }
    func testCloseDoesNotAwaitAdapterRetirementAndOpenFailureShowsPendingCleanup() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        let runtime = try await CapabilityColdStartRuntime.openOwned(configuration: f.configuration,installed: f.execution.installed,environment: .init(wall: { 1000 }))
        try await stage(f,runtime,storageWasm(wakeTrap: true),storage: true); _ = try await runtime.start()
        ColdStartDerivedHooks.adapterRetirement.arm(); defer { ColdStartDerivedHooks.adapterRetirement.release() }
        _ = try await runtime.derivedInvoke("write")
        try await eventually { ColdStartDerivedHooks.adapterRetirement.reached }
        let stopping = await runtime.recoverySnapshot()
        XCTAssertEqual(stopping.activation.phase,.recoveryRequired); XCTAssertTrue(stopping.activation.cleanupPending)
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots,baseline+1)
        // This barrier is AFTER actual bridge/KV close, before the data-only
        // observer publishes its logical retirement. It is not a hung native-I/O reproduction.
        await runtime.close(); let closed = await runtime.recoverySnapshot(); XCTAssertTrue(closed.activation.cleanupPending)
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots,baseline+1)
        ColdStartDerivedHooks.adapterRetirement.release()
        try await eventually { CapabilityAttemptReservation.occupiedSlots == baseline }
        let retired = await runtime.recoverySnapshot(); XCTAssertFalse(retired.activation.cleanupPending)
    }
    private func storageWasm(wakeTrap: Bool = false) -> Data {
        func u(_ n: Int) -> [UInt8] { var n=n, b:[UInt8]=[]; repeat { let x=UInt8(n&127); n >>= 7; b.append(x | (n == 0 ? 0 : 128)) } while n != 0; return b }
        func s(_ n: Int) -> [UInt8] { var n=n,b:[UInt8]=[]; while true { var x=UInt8(n&127); n >>= 7; let end=(n == 0 && x&64 == 0)||(n == -1 && x&64 != 0); if !end { x |= 128 }; b.append(x); if end { return b } } }
        func i(_ n: Int) -> [UInt8] { [0x41]+s(n) }
        func name(_ text: String) -> [UInt8] { u(text.utf8.count)+Array(text.utf8) }
        func section(_ id: UInt8,_ bytes: [UInt8]) -> [UInt8] { [id]+u(bytes.count)+bytes }
        func body(_ code: [UInt8]) -> [UInt8] { let value=[UInt8(0)]+code+[0x0b]; return u(value.count)+value }
        let args=Array("{\"namespace\":\"material_test\",\"key\":\"cold-coordinator\",\"valueBase64\":\"AAH+/w==\"}".utf8)
        var bytes:[UInt8]=[0,97,115,109,1,0,0,0]
        bytes += section(1,[4,0x60,0,0,0x60,3,0x7f,0x7f,0x7f,1,0x7f,0x60,4,0x7e,0x7f,0x7f,0x7f,1,0x7f,0x60,0,1,0x7f])
        var imports:[UInt8]=[2]; imports += name("mixer.capability.v1"); imports += name("storage_put"); imports += [0,1]
        imports += name("mixer.capability.v1"); imports += name("poll"); imports += [0,2]; bytes += section(2,imports)
        bytes += section(3,[4,0,0,0,3]); bytes += section(5,[1,1,1,1])
        var exports:[UInt8]=[4]; exports += name("startup"); exports += [0,2]; exports += name("write"); exports += [0,3]
        exports += name("mixer_guest_capability_ready_v1"); exports += [0,4]; exports += name("done"); exports += [0,5]; bytes += section(7,exports)
        let write=i(64)+i(args.count)+i(0)+[0x10,0,0x1a]
        var wake=i(0)+[0x29,3,0]+i(4096)+i(2048)+i(2048)+[0x10,1,0x1a]
        if wakeTrap { wake += [0] }
        bytes += section(10,[4]+body([])+body(write)+body(wake)+body(i(2048)+[0x28,2,0]))
        bytes += section(11,[1,0]+i(64)+[0x0b]+u(args.count)+args); return Data(bytes)
    }
}
