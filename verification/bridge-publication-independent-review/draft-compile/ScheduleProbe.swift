import Foundation
import Dispatch
import Testing
import MixerCapabilities
@_spi(CapabilityLifecycle) @testable import MixerExperimentalCapabilityRuntime

// Verification-only scheduler: it controls real Swift task jobs; no product
// source is instrumented and the actual C construction/lifecycle executes.
@available(macOS 15.0, *)
private final class ReviewTaskExecutor: TaskExecutor, @unchecked Sendable {
    private let jobs = Locked<[UnownedJob]>([])
    func enqueue(_ job: consuming ExecutorJob) { jobs.withLock { $0.append(UnownedJob(job)) } }
    var pending: Int { jobs.withLock { $0.count } }
    @discardableResult func runOne() -> Bool {
        let job = jobs.withLock { values -> UnownedJob? in
            values.isEmpty ? nil : values.removeFirst()
        }
        guard let job else { return false }
        job.runSynchronously(on: asUnownedTaskExecutor())
        return true
    }
    func runAvailable() { while runOne() {} }
}

private final class ReviewQueueGate: @unchecked Sendable {
    private let condition = NSCondition()
    private var open = false
    private var began = false
    private var expired = false
    func hold() {
        condition.lock(); began = true
        let limit = Date().addingTimeInterval(5)
        while !open { if !condition.wait(until: limit) { expired = true; break } }
        condition.unlock()
    }
    func release() { condition.lock(); open = true; condition.broadcast(); condition.unlock() }
    var entered: Bool { condition.lock(); defer { condition.unlock() }; return began }
    var timedOut: Bool { condition.lock(); defer { condition.unlock() }; return expired }
}

private struct ReviewResult {
    var count = 0
    var session: ExperimentalCapabilitySession?
    var error: (any Error)?
}
private final class ReviewWeakSession {
    weak var value: ExperimentalCapabilitySession?
    init(_ value: ExperimentalCapabilitySession?) { self.value = value }
}
private func reviewConstructionFence() async {
    await withCheckedContinuation { continuation in
        ExperimentalQueues.construction.async { continuation.resume() }
    }
}
private func reviewAllPermitsReturn(_ policy: CapabilityPolicy) throws {
    let all = try (0..<16).map { _ in
        try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
    }
    #expect(throws: ExperimentalCapabilityError("construction_busy")) {
        try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
    }
    for construction in all { construction.cancel() }
}

@available(macOS 15.0, *)
private func reviewTask(_ construction: ExperimentalCapabilityConstruction, executor: ReviewTaskExecutor,
                        result: Locked<ReviewResult>) -> Task<Void, Never> {
    Task(executorPreference: executor) {
        do {
            let session = try await construction.create()
            result.withLock { $0.count += 1; $0.session = session }
        } catch { result.withLock { $0.count += 1; $0.error = error } }
    }
}

extension ExperimentalBridgeTests {
    @available(macOS 15.0, *)
    @Test func independentPublicationQueuedCancellationRetiresExactlyOnce() async throws {
        let policy = try CapabilityPolicy(installed: [], manifest: [])
        let recorder = LifecycleRecorder()
        let group = OwnedCapabilityAdapterGroup(terminal: recorder, retirement: recorder)
        let construction = try ExperimentalCapabilitySession.prepareOwned(module: GuestProgram.build(), startupExport: "boot", policy: policy, adapterGroup: group)
        let gate = ReviewQueueGate(); defer { gate.release() }
        ExperimentalQueues.construction.async { gate.hold() }
        try await bridgeEventually { gate.entered }
        let executor = ReviewTaskExecutor(), result = Locked(ReviewResult())
        let task = reviewTask(construction, executor: executor, result: result)
        try await bridgeEventually { executor.pending > 0 }
        #expect(executor.runOne()) // Enqueues actual create behind the held queue.
        #expect(result.withLock { $0.count } == 0 && executor.pending == 0)
        task.cancel()
        #expect(recorder.retired == 0 && group.core.cleanupJobCount == 0 && !group.core.constructorTailObserved)
        var held = try (0..<15).map { _ in
            try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
        }
        #expect(throws: ExperimentalCapabilityError("construction_busy")) {
            try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
        }
        gate.release(); await reviewConstructionFence()
        try await bridgeEventually { executor.runAvailable(); return result.withLock { $0.count == 1 } && recorder.retired == 1 }
        await task.value
        #expect(result.withLock { $0.session == nil && $0.error is CancellationError && $0.count == 1 })
        #expect(!gate.timedOut && group.core.constructorTailObserved && group.core.cleanupJobCount == 1 && recorder.failures.isEmpty)
        construction.cancel()
        await #expect(throws: ExperimentalCapabilityError("construction_consumed")) { try await construction.create() }
        #expect(recorder.retired == 1 && group.core.cleanupJobCount == 1)
        held.removeAll(); try reviewAllPermitsReturn(policy)
        print("INDEPENDENT_SCHEDULE queuedCancellation completion=1 retirement=1 cleanup=1 tail=true permits=16")
    }

    @available(macOS 15.0, *)
    @Test func independentPublicationFinishedCancellationLeavesReturnedSessionAliveThenDeinitRetires() async throws {
        let policy = try CapabilityPolicy(installed: [], manifest: [])
        let recorder = LifecycleRecorder()
        let group = OwnedCapabilityAdapterGroup(terminal: recorder, retirement: recorder)
        let construction = try ExperimentalCapabilitySession.prepareOwned(module: GuestProgram.build(), startupExport: "boot", policy: policy, adapterGroup: group)
        let gate = ReviewQueueGate(); defer { gate.release() }
        ExperimentalQueues.construction.async { gate.hold() }
        try await bridgeEventually { gate.entered }
        let executor = ReviewTaskExecutor(), result = Locked(ReviewResult())
        let task = reviewTask(construction, executor: executor, result: result)
        try await bridgeEventually { executor.pending > 0 }
        #expect(executor.runOne())
        #expect(result.withLock { $0.count } == 0 && executor.pending == 0)
        gate.release(); await reviewConstructionFence()
        // Real owner is started, the slot is published and state.finished is true;
        // the resumed task has deliberately not taken the slot yet.
        #expect(executor.pending > 0 && result.withLock { $0.count } == 0 && group.core.constructorTailObserved)
        task.cancel(); construction.cancel(); group.closeIfUntransferred()
        #expect(recorder.retired == 0 && group.core.cleanupJobCount == 0)
        var held = try (0..<15).map { _ in
            try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
        }
        #expect(throws: ExperimentalCapabilityError("construction_busy")) {
            try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
        }
        try await bridgeEventually { executor.runAvailable(); return result.withLock { $0.count == 1 } }
        await task.value // Void result cannot retain the public session.
        var session = result.withLock { state -> ExperimentalCapabilitySession? in
            let session = state.session; state.session = nil; return session
        }
        #expect(result.withLock { $0.count == 1 && $0.error == nil })
        try #require(session != nil)
        #expect(!session!.status.closed)
        _ = try await session!.startup()
        construction.cancel(); #expect(!session!.status.closed)
        let weak = ReviewWeakSession(session)
        session = nil
        withExtendedLifetime(construction) { #expect(weak.value == nil) }
        try await bridgeEventually { recorder.retired == 1 }
        #expect(!gate.timedOut && group.core.constructorTailObserved && group.core.cleanupJobCount == 1 && recorder.failures.isEmpty)
        held.removeAll(); try reviewAllPermitsReturn(policy)
        print("INDEPENDENT_SCHEDULE finishedCancellation completion=1 publicDeinit=true retirement=1 cleanup=1 tail=true permits=16")
    }

    @available(macOS 15.0, *)
    @Test func independentPublicationFailedCreationHasOneErrorAndOneRetirement() async throws {
        let policy = try CapabilityPolicy(installed: [], manifest: [])
        let recorder = LifecycleRecorder()
        let group = OwnedCapabilityAdapterGroup(terminal: recorder, retirement: recorder)
        let construction = try ExperimentalCapabilitySession.prepareOwned(module: Data([0]), startupExport: "boot", policy: policy, adapterGroup: group)
        let executor = ReviewTaskExecutor(), result = Locked(ReviewResult())
        let task = reviewTask(construction, executor: executor, result: result)
        try await bridgeEventually { executor.pending > 0 }
        #expect(executor.runOne()); await reviewConstructionFence()
        try await bridgeEventually { executor.runAvailable(); return result.withLock { $0.count == 1 } && recorder.retired == 1 }
        await task.value
        #expect(result.withLock { $0.count == 1 && $0.session == nil && $0.error is ExperimentalCapabilityError })
        #expect(recorder.failures.count == 1 && recorder.failures[0].operation == .construction)
        #expect(group.core.constructorTailObserved && group.core.cleanupJobCount == 1)
        task.cancel(); construction.cancel(); group.closeIfUntransferred()
        await #expect(throws: ExperimentalCapabilityError("construction_consumed")) { try await construction.create() }
        #expect(recorder.retired == 1 && group.core.cleanupJobCount == 1)
        try reviewAllPermitsReturn(policy)
        print("INDEPENDENT_SCHEDULE failedCreation completion=1 error=1 retirement=1 cleanup=1 tail=true permits=16")
    }
}
