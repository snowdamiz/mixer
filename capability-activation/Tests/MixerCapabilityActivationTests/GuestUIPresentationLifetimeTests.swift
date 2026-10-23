import Foundation
import XCTest
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

private actor PresentationTaskTail {
    private var entered = false
    private var entry: CheckedContinuation<Void, Never>?
    private var tail: CheckedContinuation<Void, Never>?
    func hold() async {
        entered = true; entry?.resume(); entry = nil
        await withCheckedContinuation { tail = $0 }
    }
    func waitForEntry() async {
        if entered { return }
        await withCheckedContinuation { entry = $0 }
    }
    func release() { tail?.resume(); tail = nil }
}

private actor PresentationRetirementProbe: CapabilityPresentationRetirement {
    private(set) var turns = 0
    func retireEmptyPresentation() async -> Bool { turns += 1; return true }
}

private actor PresentationJoinOutcomes {
    private var first: CapabilityPresentationJoinStatus?
    private var waiter: CheckedContinuation<CapabilityPresentationJoinStatus, Never>?
    func record(_ value: CapabilityPresentationJoinStatus) {
        if first == nil { first = value; waiter?.resume(returning: value); waiter = nil }
    }
    func firstResult() async -> CapabilityPresentationJoinStatus {
        if let first { return first }
        return await withCheckedContinuation { waiter = $0 }
    }
}

/// These tests exercise real host Tasks and the real common/core ownership
/// graph. They are not iOS/Android native return or model destruction receipts.
final class GuestUIPresentationLifetimeTests: XCTestCase, @unchecked Sendable {
    private func receipt(_ value: CapabilityPresentationJoinStatus, file: StaticString = #filePath, line: UInt = #line) throws -> CapabilityPresentationLifetimeReceipt {
        guard case .finished(.retired(let receipt)) = value else {
            XCTFail("Expected exact retired receipt, got \(value)", file: file, line: line)
            throw CancellationError()
        }
        return receipt
    }

    func testMovesAndActualTaskJoinHaveOneAuthority() async throws {
        let retirement = PresentationRetirementProbe()
        let lifetime = CapabilityGuestUIPresentationLifetime(id: try .issue(), retirement: retirement)
        let installation = try lifetime.installation()
        XCTAssertThrowsError(try lifetime.installation())
        let moved = try XCTUnwrap(installation.move())
        XCTAssertNil(installation.move())
        let invalid = await installation.finish()
        XCTAssertEqual(invalid, .invariant(.wrongJoinOwner))
        let permit = try XCTUnwrap(moved.takePermit())
        XCTAssertNil(moved.takePermit())
        let wrongLifetime = CapabilityGuestUIPresentationLifetime(id: try .issue(), retirement: retirement)
        let wrong = try XCTUnwrap(try wrongLifetime.installation().takePermit())
        let rejected = await lifetime.finish(using: wrong)
        XCTAssertEqual(rejected, .invariant(.wrongJoinOwner))
        _ = try receipt(await wrongLifetime.finish(using: wrong))

        let tail = PresentationTaskTail(), outcomes = PresentationJoinOutcomes()
        let task = Task { await tail.hold() }
        let exchange = try GuestUIExchangeV1(generation: 1)
        XCTAssertTrue(lifetime.attach(task, exchange: exchange))
        await tail.waitForEntry()
        let first = Task { let value = await lifetime.finish(using: permit); await outcomes.record(value); return value }
        let second = Task { let value = await lifetime.finish(using: permit); await outcomes.record(value); return value }
        let early = await outcomes.firstResult()
        XCTAssertEqual(early, .pending)
        XCTAssertEqual(lifetime.status, .pending)
        let turnsBeforeReturn = await retirement.turns
        XCTAssertEqual(turnsBeforeReturn, 1) // Only the unrelated empty lifetime retired.
        await tail.release()
        let results = await [first.value, second.value]
        XCTAssertEqual(results.filter(\.isRetired).count, 1)
        let joined = try receipt(try XCTUnwrap(results.first(where: \.isRetired)))
        XCTAssertEqual(joined.lifetime, lifetime.id)
        XCTAssertEqual(joined.taskJoin, .joined)
        XCTAssertNil(joined.endpoint); XCTAssertNil(joined.facadeCleanup)
        let turnsAfterReturn = await retirement.turns
        XCTAssertEqual(turnsAfterReturn, 2)
        XCTAssertEqual(lifetime.status, .finished(.retired(joined)))
        let repeated = await lifetime.finish(using: permit)
        XCTAssertEqual(repeated, lifetime.status)
    }

    func testObservationMoveJoinsCoordinatorBeforePresentationAndReentryIsDataOnly() async throws {
        let retirement = PresentationRetirementProbe()
        let lifetime = CapabilityGuestUIPresentationLifetime(id: try .issue(), retirement: retirement)
        let installation = try lifetime.installation()
        let exchange = try GuestUIExchangeV1(generation: 1)
        XCTAssertTrue(lifetime.attach(Task {}, exchange: exchange))
        let coordinatorTail = PresentationTaskTail()
        let consumer = Task { await coordinatorTail.hold() }
        await coordinatorTail.waitForEntry()
        let observation = CapabilityColdStartObservation(signals: CapabilityAttemptSignals(generation: 1, guestUI: exchange), consumer: consumer)
        XCTAssertTrue(observation.install(installation))
        XCTAssertNil(installation.move())
        let outcomes = PresentationJoinOutcomes()
        let first = Task {
            let result = await observation.finish() ?? .invariant(.invalidState)
            await outcomes.record(result); return result
        }
        let second = Task {
            let result = await observation.finish() ?? .invariant(.invalidState)
            await outcomes.record(result); return result
        }
        let reentry = await outcomes.firstResult()
        XCTAssertEqual(reentry, .pending)
        let beforeCoordinatorReturn = await retirement.turns
        XCTAssertEqual(beforeCoordinatorReturn, 0)
        XCTAssertEqual(lifetime.status, .pending)
        await coordinatorTail.release()
        let results = await [first.value, second.value]
        XCTAssertEqual(results.filter(\.isRetired).count, 1)
        let joined = try receipt(try XCTUnwrap(results.first(where: \.isRetired)))
        XCTAssertEqual(joined.taskJoin, .joined)
        let repeated = await observation.finish()
        XCTAssertEqual(repeated, .finished(.retired(joined)))
        let turns = await retirement.turns
        XCTAssertEqual(turns, 1)
    }

    @MainActor
    func testPreparedGuardTransferAndCloseBeforeBindUseNoTaskReceipt() async throws {
        let reservation = try CapabilityAttemptReservation.acquire()
        let prepared = try await CapabilityGuestUIPresentationBinding.prepare(reservation: reservation)
        let publicModel = prepared.binding.presentation
        let cleaned = try receipt(await prepared.cleanupAfterFailure())
        XCTAssertEqual(cleaned.taskJoin, .noTaskCreated)
        XCTAssertEqual(publicModel.state, .stopped)
        let repeated = await prepared.cleanupAfterFailure()
        XCTAssertEqual(repeated, .finished(.retired(cleaned)))
        reservation.beginClosing(); XCTAssertTrue(reservation.isReleased)

        let transferredReservation = try CapabilityAttemptReservation.acquire()
        let transferred = try await CapabilityGuestUIPresentationBinding.prepare(reservation: transferredReservation)
        let control = CapabilityColdStartControl(reservation: transferredReservation)
        try transferred.transfer(to: control)
        XCTAssertThrowsError(try transferred.transfer(to: control))
        // A disarmed setup guard cannot steal the core's initial permit.
        let disarmed = await transferred.cleanupAfterFailure()
        XCTAssertEqual(disarmed, .pending)
        let binding = transferred.binding
        binding.requestFinalClose(.closed)
        let permit = binding.takeFinalJoinPermit()
        XCTAssertNotNil(permit); XCTAssertNil(binding.takeFinalJoinPermit())
        let final = try receipt(await binding.finishFinalClose(using: permit))
        XCTAssertEqual(final.taskJoin, .noTaskCreated)
        let exchange = try GuestUIExchangeV1(generation: 1)
        do { _ = try await binding.bind(exchange); XCTFail("Closed binding reopened") } catch {}
        XCTAssertEqual(exchange.snapshot().counters.producedFrames, 0)
        transferredReservation.beginClosing(); XCTAssertTrue(transferredReservation.isReleased)

        let cancelledReservation = try CapabilityAttemptReservation.acquire()
        let cancelled = Task { try await CapabilityGuestUIPresentationBinding.prepare(reservation: cancelledReservation) }
        cancelled.cancel()
        do { _ = try await cancelled.value; XCTFail("Cancelled prepare returned an armed guard") }
        catch is CancellationError {}
        cancelledReservation.beginClosing(); XCTAssertTrue(cancelledReservation.isReleased)
    }

    @MainActor
    func testBindFailureRetiresMovedPermitAndFallbackRequiresExactJoin() async throws {
        let reservation = try CapabilityAttemptReservation.acquire()
        let prepared = try await CapabilityGuestUIPresentationBinding.prepare(reservation: reservation)
        try prepared.transfer(to: CapabilityColdStartControl(reservation: reservation))
        let binding = prepared.binding
        let rejected = try GuestUIExchangeV1(generation: 1)
        let existingReader = try rejected.deliveryWake.takeConsumer()
        do { _ = try await binding.bind(rejected); XCTFail("Second reader admitted") } catch {}
        // The throwing bind relinquished its moved pre-bind authority itself.
        XCTAssertEqual(binding.presentation.state, .stopped)
        withExtendedLifetime(existingReader) {}
        let old = try GuestUIExchangeV1(generation: 2)
        let oldInstallation = try await binding.bind(old)
        old.stop(.closed)
        let replacement = try GuestUIExchangeV1(generation: 3)
        do { _ = try await binding.bind(replacement); XCTFail("Fallback admitted before actual authoritative join") }
        catch GuestUIControlRejectionV1.busy {}
        let oldReceipt = try receipt(await oldInstallation.finish())
        XCTAssertEqual(oldReceipt.taskJoin, .joined)
        let next = try await binding.bind(replacement)
        XCTAssertNotEqual(next.lifetime?.id, oldReceipt.lifetime)
        XCTAssertEqual(next.lifetime?.facade, oldReceipt.facade)
        let moved = await oldInstallation.finish()
        XCTAssertEqual(moved, .invariant(.wrongJoinOwner))
        replacement.stop(.closed)
        let nextReceipt = try receipt(await next.finish())
        XCTAssertEqual(nextReceipt.taskJoin, .joined)
        XCTAssertNotEqual(nextReceipt.lifetime, oldReceipt.lifetime)
        binding.requestFinalClose(.closed)
        XCTAssertNil(binding.takeFinalJoinPermit())
        let final = await binding.finishFinalClose(using: nil)
        XCTAssertEqual(final, .finished(.retired(nextReceipt)))
        reservation.beginClosing(); XCTAssertTrue(reservation.isReleased)
    }

    @MainActor
    func testConstructorOpeningAdmissionAndFailedInstallCleanupUseExistingCoreJob() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-presentation-core-\(UUID().uuidString)")
        defer { try? FileManager.default.removeItem(at: root) }
        let fixture = try ColdStartFixture(root: root)
        let configuration = try fixture.configuration.checked()

        let failedReservation = try CapabilityAttemptReservation.acquire()
        let prepared = try await CapabilityGuestUIPresentationBinding.prepare(reservation: failedReservation)
        var priorAdmission: CapabilityRecoveryStoreAdmission? = try failedReservation.issueStoreAdmission()
        XCTAssertNotNil(priorAdmission)
        XCTAssertThrowsError(try CapabilityColdStartCloseCore(configuration: configuration, installed: fixture.execution.installed,
            environment: .init(), reservation: failedReservation, guestUIBinding: prepared.binding))
        let constructorCleanup = try receipt(await prepared.cleanupAfterFailure())
        XCTAssertEqual(constructorCleanup.taskJoin, .noTaskCreated)
        priorAdmission = nil
        failedReservation.beginClosing(); XCTAssertTrue(failedReservation.isReleased)

        let emptyReservation = try CapabilityAttemptReservation.acquire()
        let emptyPrepared = try await CapabilityGuestUIPresentationBinding.prepare(reservation: emptyReservation)
        let emptyCore = try CapabilityColdStartCloseCore(configuration: configuration, installed: fixture.execution.installed,
            environment: .init(), reservation: emptyReservation, guestUIBinding: emptyPrepared.binding)
        try emptyPrepared.transfer(to: emptyCore)
        emptyCore.requestClose(.closed)
        XCTAssertThrowsError(try emptyCore.control.admit(.opening))
        await emptyCore.waitForClose()
        XCTAssertEqual(try receipt(emptyPrepared.binding.finalStatus).taskJoin, .noTaskCreated)
        XCTAssertTrue(emptyReservation.isReleased) // Core and public model are still retained.

        let reservation = try CapabilityAttemptReservation.acquire()
        let installed = try await CapabilityGuestUIPresentationBinding.prepare(reservation: reservation)
        let core = try CapabilityColdStartCloseCore(configuration: configuration, installed: fixture.execution.installed,
            environment: .init(), reservation: reservation, guestUIBinding: installed.binding)
        try installed.transfer(to: core)
        let op = try core.control.admit(.start)
        let exchange = try GuestUIExchangeV1(generation: 1)
        let signals = CapabilityAttemptSignals(generation: 1, guestUI: exchange)
        try core.control.installObservation(signals, worker: core.worker, candidate: "test", launch: "test", op: op)
        let localInstallation = try await installed.binding.bind(exchange)
        core.requestClose(.closed)
        XCTAssertFalse(core.control.installPresentationLifetime(localInstallation, signals: signals, op: op))
        XCTAssertFalse(reservation.isReleased)
        exchange.stop(.closed)
        let joined = try receipt(await localInstallation.finish())
        XCTAssertEqual(joined.taskJoin, .joined)
        XCTAssertFalse(reservation.isReleased) // Existing cleanup still waits ordinary tail.
        core.control.finish(op)
        await core.waitForClose()
        XCTAssertEqual(installed.binding.finalStatus, .finished(.retired(joined)))
        XCTAssertTrue(reservation.isReleased)

        let observationReservation = try CapabilityAttemptReservation.acquire()
        let observed = try await CapabilityGuestUIPresentationBinding.prepare(reservation: observationReservation)
        let observationCore = try CapabilityColdStartCloseCore(configuration: configuration, installed: fixture.execution.installed,
            environment: .init(), reservation: observationReservation, guestUIBinding: observed.binding)
        try observed.transfer(to: observationCore)
        let operation = try observationCore.control.admit(.start)
        let observedExchange = try GuestUIExchangeV1(generation: 2)
        let observedSignals = CapabilityAttemptSignals(generation: 2, guestUI: observedExchange)
        try observationCore.control.installObservation(observedSignals, worker: observationCore.worker, candidate: "observed", launch: "observed", op: operation)
        let observedInstallation = try await observed.binding.bind(observedExchange)
        let wrongSignals = CapabilityAttemptSignals(generation: 3, guestUI: try GuestUIExchangeV1(generation: 3))
        XCTAssertFalse(observationCore.control.installPresentationLifetime(observedInstallation, signals: wrongSignals, op: operation))
        XCTAssertTrue(observationCore.control.installPresentationLifetime(observedInstallation, signals: observedSignals, op: operation))
        let moved = await observedInstallation.finish()
        XCTAssertEqual(moved, .invariant(.wrongJoinOwner))
        observationCore.control.endObservationFromConsumer()
        let ending = try XCTUnwrap(observationCore.control.detachObservation())
        XCTAssertNil(observationCore.control.detachObservation())
        let endingStatus = await ending.finish()
        let observedReceipt = try receipt(try XCTUnwrap(endingStatus))
        XCTAssertEqual(observedReceipt.taskJoin, .joined)
        observationCore.control.finish(operation)
        observationCore.requestClose(.closed); await observationCore.waitForClose()
        XCTAssertEqual(observed.binding.finalStatus, .finished(.retired(observedReceipt)))
        XCTAssertTrue(observationReservation.isReleased)
    }
}

/// Permanent quarantine is intentionally isolated after ordinary lifecycle
/// tests. It is never reset to manufacture reservation capacity in this process.
final class GuestUIPresentationQuarantineTests: XCTestCase, @unchecked Sendable {
    @MainActor
    func testAbandonedGuardAndMissingAuthorityNeverReleaseCapacity() async throws {
        let abandoned = try CapabilityAttemptReservation.acquire()
        var guardOwner: CapabilityPreparedPresentation? = try await CapabilityGuestUIPresentationBinding.prepare(reservation: abandoned)
        XCTAssertNotNil(guardOwner)
        guardOwner = nil
        abandoned.beginClosing()
        XCTAssertTrue(abandoned.isQuarantined); XCTAssertFalse(abandoned.isReleased)

        let reservation = try CapabilityAttemptReservation.acquire()
        let prepared = try await CapabilityGuestUIPresentationBinding.prepare(reservation: reservation)
        try prepared.transfer(to: CapabilityColdStartControl(reservation: reservation))
        let exchange = try GuestUIExchangeV1(generation: 1)
        let installation = try await prepared.binding.bind(exchange)
        prepared.binding.requestFinalClose(.closed)
        let missing = await prepared.binding.finishFinalClose(using: nil)
        XCTAssertEqual(missing, .invariant(.wrongJoinOwner))
        XCTAssertTrue(reservation.isQuarantined)
        let joined = await installation.finish()
        XCTAssertTrue(joined.isRetired)
        XCTAssertEqual(prepared.binding.finalStatus, missing)
        reservation.beginClosing(); XCTAssertFalse(reservation.isReleased)
    }
}
