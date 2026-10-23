import Foundation
import Testing
import MixerCapabilities
@testable import MixerExperimentalCapabilityRuntime

extension ExperimentalBridgeTests {
    @Test func constructionDoubleCancelAndFailureCannotLosePermits() async throws {
        let policy = try bridgePolicy()
        let construction = try ExperimentalCapabilitySession.prepare(module: GuestProgram.build(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
        let session = try await construction.create()
        await #expect(throws: ExperimentalCapabilityError("construction_consumed")) { try await construction.create() }
        construction.cancel() // Finished construction cannot close its returned owner.
        _ = try await session.startup()
        #expect(!session.status.closed)
        session.close(); try await bridgeEventually { session.status.drained }
        let unused = try ExperimentalCapabilitySession.prepare(module: GuestProgram.build(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
        unused.cancel()
        await #expect(throws: ExperimentalCapabilityError("construction_consumed")) { try await unused.create() }
        let invalid = try ExperimentalCapabilitySession.prepare(module: Data([0]), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
        await #expect(throws: ExperimentalCapabilityError.self) { try await invalid.create() }
        var held: [ExperimentalCapabilityConstruction] = []
        for _ in 0..<16 { held.append(try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())) }
        #expect(held.count == 16)
        held.removeAll()
    }
    @Test func rateRejectionIsLocalBoundedAndNeverRetried() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-rate-wasm-" + UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = try AppPrivateKeyValueStore(directory: directory, namespaces: ["entries"])
        let session = try await bridgeSession(GuestProgram.build(.burst(8)), store: store,
            configuration: .init(dispatchBurst: 1, dispatchesPerSecond: 1))
        defer { session.close() }
        _ = try await session.startup(); try await session.enableEffects()
        let beginning = ContinuousClock.now
        _ = try await session.invoke("run")
        try await bridgeEventually { try await session.invoke("stage").value == .i32(8) }
        #expect(ContinuousClock.now < beginning.advanced(by: .seconds(1)))
        var successes = 0, quotas = 0
        for index in 0..<8 {
            let word = try await session.readMemory(offset: UInt32(128 + index*4), count: 4)
            let count = word.enumerated().reduce(UInt32(0)) { $0 | UInt32($1.element) << UInt32($1.offset*8) }
            let bytes = try await session.readMemory(offset: UInt32(4096*(index+1)), count: Int(count))
            switch try GuestCapabilityTransportCodecV1.decodeCompletion(bytes, expectedOperation: .storagePut) {
            case .success(.put(let result)): #expect(result.committed); successes += 1
            case .failure(.quotaExceeded): quotas += 1
            default: Issue.record("unexpected burst result")
            }
        }
        #expect(successes == 1 && quotas == 7)
        session.close(); try await bridgeEventually { session.status.drained }
        #expect(session.status.acknowledgements == 8)
        await store.close()
    }
    @Test func nonconsumingWakeYieldsAndIdleSessionParks() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-fair-wasm-" + UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = try AppPrivateKeyValueStore(directory: directory, namespaces: ["entries"])
        let noisy = try await bridgeSession(GuestProgram.build(.unconsumed), store: store)
        _ = try await noisy.startup(); try await noisy.enableEffects(); _ = try await noisy.invoke("run")
        try await bridgeEventually { noisy.status.yields >= 3 }
        #expect(noisy.status.maximumBatchTurns <= 4)
        let quiet = try await bridgeSession(GuestProgram.build(.single(1,GuestProgram.get)), store: store)
        _ = try await quiet.startup(); try await quiet.enableEffects(); _ = try await quiet.invoke("run")
        try await bridgeEventually { try await quiet.invoke("stage").value == .i32(5) }
        try await Task.sleep(for: .milliseconds(30))
        let ticks = quiet.status.timerTicks
        try await Task.sleep(for: .milliseconds(100))
        #expect(quiet.status.timerTicks <= ticks + 1)
        noisy.close(); quiet.close()
        try await bridgeEventually { noisy.status.drained && quiet.status.drained }
        await store.close()
    }
    @Test func commandBoundsRejectBeforeAllocationAndKeepOwnerUsable() async throws {
        let policy = try bridgePolicy()
        let session = try await ExperimentalCapabilitySession.prepare(module: GuestProgram.build(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters()).create()
        _ = try await session.startup()
        await #expect(throws: ExperimentalCapabilityError("invalid_read_length")) { try await session.readMemory(offset: 0, count: -1) }
        await #expect(throws: ExperimentalCapabilityError("invalid_read_length")) { try await session.readMemory(offset: 0, count: 1_048_577) }
        await #expect(throws: ExperimentalCapabilityError("invalid_write_length")) { try await session.writeMemory(offset: 0, bytes: Data(count: 1_048_577)) }
        await #expect(throws: ExperimentalCapabilityError("invalid_invoke_arguments")) { try await session.invoke(String(repeating: "x", count: 4097)) }
        // Checked ordinary C status3 range rejection is recoverable.
        do { _ = try await session.readMemory(offset: .max, count: 1); Issue.record("range accepted") }
        catch { #expect((error as? ExperimentalCapabilityError)?.nativeStatus == 3) }
        #expect(try await session.invoke("stage").value == .i32(0))
        session.close(); try await bridgeEventually { session.status.drained }
    }
}
