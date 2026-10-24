import Foundation
import Dispatch
import Testing
import MixerCapabilities
@_spi(CapabilityLifecycle) @testable import MixerExperimentalCapabilityRuntime

extension ExperimentalBridgeTests {
    @Test func queuedOwnedEnableExpiresNormallyWithoutOpeningEffects() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-enable-deadline-" + UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let observer = LifecycleRecorder()
        let group = OwnedCapabilityAdapterGroup(storage: try lifecycleStore(directory), terminal: observer, retirement: observer)
        let session = try await lifecyclePrepare(group).create()
        _ = try await session.startup()
        let gate = EnableQueueGate()
        ExperimentalQueues.guest.async { gate.hold() }
        defer { gate.release(); session.close() }
        try await bridgeEventually { gate.entered }
        let cutoff = DispatchTime.now().uptimeNanoseconds + 20_000_000
        let pending = Task { try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: cutoff) }
        try await Task.sleep(for: .milliseconds(60))
        #expect(DispatchTime.now().uptimeNanoseconds >= cutoff)
        #expect(observer.failures.isEmpty && observer.retired == 0)
        gate.release()
        do { try await pending.value; Issue.record("expired queued enable succeeded") }
        catch let error as ExperimentalCapabilityError {
            #expect(error.failure.kind == .deadlineExceeded && error.failure.operation == .enableEffects)
            #expect(error.nativeStatus == nil)
        }
        try await bridgeEventually { observer.retired == 1 && session.status.drained }
        #expect(observer.failures.count == 1 && observer.failures[0].kind == .deadlineExceeded)
        #expect(group.core.cleanupJobCount == 1)
        try await lifecycleReopens(directory)
        // Ordinary expiry must not quarantine a construction/native permit.
        var held: [ExperimentalCapabilityConstruction] = []
        for _ in 0..<16 { held.append(try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: bridgePolicy(), adapters: .init())) }
        #expect(held.count == 16); held.removeAll()
    }

    @Test func futureOwnedEnableUsesConcreteStorageAndExpiredFollowupStaysTerminal() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-enable-future-" + UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let observer = LifecycleRecorder()
        let group = OwnedCapabilityAdapterGroup(storage: try lifecycleStore(directory), terminal: observer, retirement: observer)
        let session = try await lifecyclePrepare(group).create()
        defer { session.close() }
        _ = try await session.startup()
        try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: DispatchTime.now().uptimeNanoseconds + 5_000_000_000)
        _ = try await session.invoke("run")
        try await bridgeEventually { try await session.invoke("stage").value == .i32(5) }
        await #expect(throws: ExperimentalCapabilityError.self) { try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: 0) }
        try await bridgeEventually { observer.retired == 1 }
        #expect(observer.failures.count == 1 && observer.failures[0].kind == .deadlineExceeded)
        try await lifecycleReopens(directory)
    }

    @Test func ownedEnableRejectsDevelopmentOwnerWithoutChangingLegacyEnable() async throws {
        let session = try await ExperimentalCapabilitySession.prepare(module: GuestProgram.build(), startupExport: "boot", policy: bridgePolicy(), adapters: .init()).create()
        defer { session.close() }
        _ = try await session.startup()
        do { try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: .max); Issue.record("non-owned SPI accepted") }
        catch let error as ExperimentalCapabilityError { #expect(error.failure.kind == .callerAPI(.invalidLifecycleState)) }
        #expect(!session.status.closed && session.status.failure == nil)
        try await session.enableEffects()
        #expect(!session.status.closed)
        session.close(); try await bridgeEventually { session.status.drained }
    }
}

private final class EnableQueueGate: @unchecked Sendable {
    private let condition = NSCondition()
    private var open = false
    private var began = false
    var entered: Bool { condition.lock(); defer { condition.unlock() }; return began }
    func hold() {
        condition.lock(); began = true
        let end = Date().addingTimeInterval(5)
        while !open { if !condition.wait(until: end) { break } }
        condition.unlock()
    }
    func release() { condition.lock(); open = true; condition.broadcast(); condition.unlock() }
}
