import Foundation
import XCTest
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

private actor ReviewLatch {
    private var entered = false
    private var released = false
    private var entry: CheckedContinuation<Void, Never>?
    private var blocked: CheckedContinuation<Void, Never>?
    func hold() async {
        entered = true; entry?.resume(); entry = nil
        if released { return }
        await withCheckedContinuation { blocked = $0 }
    }
    func waitForEntry() async {
        if entered { return }
        await withCheckedContinuation { entry = $0 }
    }
    func release() { released = true; blocked?.resume(); blocked = nil }
}

private actor ReviewFirstResult {
    private var first: CapabilityPresentationJoinStatus?
    private var waiter: CheckedContinuation<CapabilityPresentationJoinStatus, Never>?
    func record(_ result: CapabilityPresentationJoinStatus) {
        if first == nil { first = result; waiter?.resume(returning: result); waiter = nil }
    }
    func read() async -> CapabilityPresentationJoinStatus {
        if let first { return first }
        return await withCheckedContinuation { waiter = $0 }
    }
}

@MainActor
private final class ReviewActorRetirement: CapabilityPresentationRetirement {
    let tail: ReviewLatch
    private(set) var turns = 0
    private(set) var actualMainThread = true
    private let succeeds: Bool
    init(tail: ReviewLatch, succeeds: Bool = true) { self.tail = tail; self.succeeds = succeeds }
    func retireEmptyPresentation() async -> Bool {
        actualMainThread = actualMainThread && Thread.isMainThread
        turns += 1
        await tail.hold()
        return succeeds
    }
}

final class IndependentPresentationLifetimeTests: XCTestCase, @unchecked Sendable {
    private func receipt(_ value: CapabilityPresentationJoinStatus) throws -> CapabilityPresentationLifetimeReceipt {
        guard case .finished(.retired(let result)) = value else {
            XCTFail("Expected retired exact result: \(value)"); throw CancellationError()
        }
        return result
    }

    func testExactTaskAndMainActorReturnFenceGateFallback() async throws {
        let reservation = try CapabilityAttemptReservation.acquire()
        let obligation = try reservation.reservePresentation()
        let actorTail = ReviewLatch(), taskTail = ReviewLatch()
        let retirement = await ReviewActorRetirement(tail: actorTail)
        let gate = CapabilityPresentationBindingGate(obligation: obligation)
        let initial = try gate.initial(retirement: retirement)
        XCTAssertTrue(gate.accept(initial))
        let installation = try gate.beginBind(retirement: retirement)
        let lifetime = try XCTUnwrap(installation.lifetime)
        let exchange = try GuestUIExchangeV1(generation: 5)
        let unrelated = try GuestUIExchangeV1(generation: 6)
        let realTask = Task { await taskTail.hold() }
        XCTAssertTrue(lifetime.attach(realTask, exchange: exchange))
        await taskTail.waitForEntry()
        lifetime.requestStop(.closed)
        XCTAssertNotNil(exchange.snapshot().stop)
        XCTAssertNil(unrelated.snapshot().stop)
        let joined = Task { await installation.finish() }
        for _ in 0..<64 { await Task.yield() }
        XCTAssertEqual(lifetime.status, .pending)
        XCTAssertThrowsError(try gate.beginBind(retirement: retirement))
        let before = await retirement.turns
        XCTAssertEqual(before, 0)
        await taskTail.release()
        await actorTail.waitForEntry()
        XCTAssertEqual(lifetime.status, .pending)
        XCTAssertThrowsError(try gate.beginBind(retirement: retirement))
        XCTAssertFalse(reservation.isReleased)
        await actorTail.release()
        let exact = try receipt(await joined.value)
        XCTAssertEqual(exact.lifetime, lifetime.id)
        XCTAssertEqual(exact.taskJoin, .joined)
        XCTAssertNil(exact.endpoint); XCTAssertNil(exact.facadeCleanup)
        let onMain = await retirement.actualMainThread
        XCTAssertTrue(onMain)
        let replacement = try gate.beginBind(retirement: retirement)
        XCTAssertNotEqual(replacement.lifetime?.id, exact.lifetime)
        XCTAssertEqual(replacement.lifetime?.facade, exact.facade)
        let empty = try receipt(await replacement.finish())
        XCTAssertEqual(empty.taskJoin, .noTaskCreated)
        gate.requestClose(.closed)
        let final = await gate.finish(using: nil)
        XCTAssertEqual(final, .finished(.retired(empty)))
        reservation.beginClosing(); XCTAssertTrue(reservation.isReleased)
        withExtendedLifetime(retirement) {}
    }

    func testManyJoinReentriesAreDataOnlyAndDoNotRetireEarly() async throws {
        let taskTail = ReviewLatch(), actorTail = ReviewLatch()
        let retirement = await ReviewActorRetirement(tail: actorTail)
        let lifetime = CapabilityGuestUIPresentationLifetime(id: try .issue(), retirement: retirement)
        let installation = try lifetime.installation()
        let permit = try XCTUnwrap(installation.takePermit())
        let task = Task { await taskTail.hold() }
        let exchange = try GuestUIExchangeV1(generation: 8)
        XCTAssertTrue(lifetime.attach(task, exchange: exchange))
        await taskTail.waitForEntry()
        let firstResult = ReviewFirstResult()
        let first = Task { let result = await lifetime.finish(using: permit); await firstResult.record(result); return result }
        let second = Task { let result = await lifetime.finish(using: permit); await firstResult.record(result); return result }
        let initialReentry = await firstResult.read()
        XCTAssertEqual(initialReentry, .pending)
        // One reentry must return while the real Task is still held. It cannot
        // be another registered waiter for the join or the retirement turn.
        let returns = await withTaskGroup(of: CapabilityPresentationJoinStatus.self, returning: [CapabilityPresentationJoinStatus].self) { group in
            for _ in 0..<64 { group.addTask { await lifetime.finish(using: permit) } }
            var results: [CapabilityPresentationJoinStatus] = []
            for await value in group { results.append(value) }
            return results
        }
        XCTAssertEqual(returns.count, 64)
        XCTAssertTrue(returns.allSatisfy { $0 == .pending })
        let turns = await retirement.turns
        XCTAssertEqual(turns, 0)
        await taskTail.release(); await actorTail.waitForEntry()
        let duringRetire = await lifetime.finish(using: permit)
        XCTAssertEqual(duringRetire, .pending)
        await actorTail.release()
        let both = await [first.value, second.value]
        let exact = try receipt(try XCTUnwrap(both.first(where: \.isRetired)))
        let repeated = await lifetime.finish(using: permit)
        XCTAssertEqual(repeated, .finished(.retired(exact)))
        let finalTurns = await retirement.turns
        XCTAssertEqual(finalTurns, 1)
    }

    @MainActor
    func testFailedTransferKeepsGuardAuthorityAndConcurrentCleanupHasOneOwner() async throws {
        let reservation = try CapabilityAttemptReservation.acquire()
        let other = try CapabilityAttemptReservation.acquire()
        let prepared = try await CapabilityGuestUIPresentationBinding.prepare(reservation: reservation)
        let publicModel = prepared.binding.presentation
        XCTAssertThrowsError(try prepared.transfer(to: CapabilityColdStartControl(reservation: other)))
        let closedControl = CapabilityColdStartControl(reservation: reservation)
        closedControl.requestClose(.closed)
        XCTAssertThrowsError(try prepared.transfer(to: closedControl))
        async let one = prepared.cleanupAfterFailure()
        async let two = prepared.cleanupAfterFailure()
        let results = await [one, two]
        XCTAssertTrue(results.contains(where: \.isRetired))
        XCTAssertTrue(results.allSatisfy { $0.isRetired || $0 == .pending })
        let final = try receipt(prepared.binding.finalStatus)
        XCTAssertEqual(final.taskJoin, .noTaskCreated)
        XCTAssertEqual(publicModel.state, .stopped)
        let repeated = await prepared.cleanupAfterFailure()
        XCTAssertEqual(repeated, .finished(.retired(final)))
        reservation.beginClosing(); other.beginClosing()
        XCTAssertTrue(reservation.isReleased); XCTAssertTrue(other.isReleased)
        withExtendedLifetime(publicModel) {}
    }

    @MainActor
    func testRaceBindWithCoreClosePreservesLocalOrObservationOwner() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-independent-lifetime-\(UUID())")
        defer { try? FileManager.default.removeItem(at: directory) }
        let fixture = try ColdStartFixture(root: directory)
        let configuration = try fixture.configuration.checked()
        for index in 1...64 {
            let reservation = try CapabilityAttemptReservation.acquire()
            let prepared = try await CapabilityGuestUIPresentationBinding.prepare(reservation: reservation)
            let publicModel = prepared.binding.presentation
            let core = try CapabilityColdStartCloseCore(configuration: configuration, installed: fixture.execution.installed,
                environment: .init(), reservation: reservation, guestUIBinding: prepared.binding)
            try prepared.transfer(to: core)
            let operation = try core.control.admit(.start)
            let exchange = try GuestUIExchangeV1(generation: UInt64(index))
            let signals = CapabilityAttemptSignals(generation: UInt64(index), guestUI: exchange)
            try core.control.installObservation(signals, worker: core.worker, candidate: "review", launch: "review", op: operation)
            let closing = Task.detached { core.requestClose(.closed) }
            do {
                let local = try await prepared.binding.bind(exchange)
                if !core.control.installPresentationLifetime(local, signals: signals, op: operation) {
                    exchange.stop(.closed)
                    let result = await local.finish()
                    XCTAssertTrue(result.isRetired)
                }
            } catch { /* Close may win before beginBind; the core then owns pre-bind. */ }
            await closing.value
            XCTAssertFalse(reservation.isReleased)
            core.control.finish(operation)
            await core.waitForClose()
            XCTAssertTrue(prepared.binding.finalStatus.isRetired)
            XCTAssertFalse(reservation.isQuarantined)
            XCTAssertTrue(reservation.isReleased)
            XCTAssertEqual(publicModel.state, .stopped)
        }
    }
}

// Deliberate quarantine remains isolated in a final test class and never reset.
final class IndependentPresentationQuarantineTests: XCTestCase, @unchecked Sendable {
    func testFailedMainActorRetirementNeverAuthorizesFallbackOrCapacityReuse() async throws {
        let reservation = try CapabilityAttemptReservation.acquire()
        let actorTail = ReviewLatch()
        await actorTail.release()
        let retirement = await ReviewActorRetirement(tail: actorTail, succeeds: false)
        let gate = CapabilityPresentationBindingGate(obligation: try reservation.reservePresentation())
        let initial = try gate.initial(retirement: retirement)
        XCTAssertTrue(gate.accept(initial))
        let local = try gate.beginBind(retirement: retirement)
        let failure = await local.finish()
        guard case .finished(.quarantined(let exact)) = failure else { return XCTFail("Expected quarantine") }
        XCTAssertEqual(exact.code, .invalidState)
        XCTAssertThrowsError(try gate.beginBind(retirement: retirement))
        gate.requestClose(.closed)
        let final = await gate.finish(using: nil)
        XCTAssertEqual(final, .invariant(.wrongJoinOwner))
        reservation.beginClosing()
        XCTAssertTrue(reservation.isQuarantined); XCTAssertFalse(reservation.isReleased)
        withExtendedLifetime(retirement) {}
    }
}
