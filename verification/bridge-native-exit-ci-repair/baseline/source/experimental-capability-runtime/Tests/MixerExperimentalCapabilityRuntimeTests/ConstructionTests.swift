import Foundation
import Dispatch
import Testing
import MixerCapabilities
@testable import MixerExperimentalCapabilityRuntime

@Suite(.serialized)
struct ExperimentalBridgeTests {
    @Test func cancelledQueuedCreateKeepsPermitUntilItsCleanupRuns() async throws {
        let gate = ConstructionGate()
        ExperimentalQueues.construction.async { gate.hold() }
        defer { gate.release() }
        try await bridgeEventually { gate.entered }
        let policy = try CapabilityPolicy(installed: [], manifest: [])
        let construction = try ExperimentalCapabilitySession.prepare(module: GuestProgram.build(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
        let task = Task { try await construction.create() }
        try await Task.sleep(for: .milliseconds(10))
        task.cancel()
        var held: [ExperimentalCapabilityConstruction] = []
        for _ in 0..<15 { held.append(try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())) }
        #expect(throws: ExperimentalCapabilityError("construction_busy")) {
            try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
        }
        gate.release()
        await #expect(throws: CancellationError.self) { try await task.value }
        let last = try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
        last.cancel(); held.removeAll()
    }
    @Test func concurrentPrepareRejectsBeforeMoreThanSixteenModuleCaptures() throws {
        let policy = try CapabilityPolicy(installed: [], manifest: [])
        let held = Locked<[ExperimentalCapabilityConstruction]>([]), rejected = Locked(0)
        DispatchQueue.concurrentPerform(iterations: 32) { _ in
            do {
                let item = try ExperimentalCapabilitySession.prepare(module: Data(count: 4_194_304), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
                held.withLock { $0.append(item) }
            } catch {
                #expect(error as? ExperimentalCapabilityError == ExperimentalCapabilityError("construction_busy"))
                rejected.withLock { $0 += 1 }
            }
        }
        #expect(held.withLock { $0.count } == 16 && rejected.withLock { $0 } == 16)
        held.withLock { $0.removeAll() }
    }
    @Test func unusedConstructionPermitsBoundCapturesAndRelease() throws {
        let policy = try CapabilityPolicy(installed: [], manifest: [])
        func prepare() throws -> ExperimentalCapabilityConstruction {
            try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
        }
        var held: [ExperimentalCapabilityConstruction?] = try (0..<16).map { _ in try prepare() }
        #expect(throws: ExperimentalCapabilityError("construction_busy")) { try prepare() }
        held[0] = nil
        let replacement = try prepare()
        #expect(throws: ExperimentalCapabilityError("construction_busy")) { try prepare() }
        replacement.cancel()
        held[0] = try prepare()
        held.removeAll()
    }
}

private final class ConstructionGate: @unchecked Sendable {
    private let condition = NSCondition()
    private var open = false
    private var began = false
    func hold() {
        condition.lock(); began = true
        let limit = Date().addingTimeInterval(5)
        while !open { if !condition.wait(until: limit) { break } }
        condition.unlock()
    }
    func release() { condition.lock(); open = true; condition.broadcast(); condition.unlock() }
    var entered: Bool { condition.lock(); defer { condition.unlock() }; return began }
}
