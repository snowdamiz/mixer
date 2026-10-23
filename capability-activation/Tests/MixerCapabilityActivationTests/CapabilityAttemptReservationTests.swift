import Foundation
import XCTest
@testable import MixerCapabilityActivation

private final class RetiringProbe: @unchecked Sendable {
    let entered: DispatchSemaphore
    let release: DispatchSemaphore
    init(_ entered: DispatchSemaphore, _ release: DispatchSemaphore) { self.entered = entered; self.release = release }
    deinit { entered.signal(); _ = release.wait(timeout: .now() + 10) }
}
private final class ReservationOwner: Sendable {}

final class CapabilityAttemptReservationTests: XCTestCase, @unchecked Sendable {
    /// Runs in a fresh test process; permanent negative quarantine is deliberately
    /// last, never reset or silently reclaimed to make the test suite pass.
    func testSinglePoolAdmissionExplicitRetirementDestructorAndAbandonment() async throws {
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 0)
        // Presentation admission is once per facade, even if retired before
        // closing; repeated fallback attempts must reuse that outer obligation.
        let facade = try CapabilityAttemptReservation.acquire()
        let presentation = try facade.reservePresentation()
        try presentation.retainOwner(ReservationOwner())
        XCTAssertThrowsError(try presentation.retainOwner(ReservationOwner()))
        XCTAssertThrowsError(try facade.reservePresentation())
        presentation.retire(); presentation.retire()
        XCTAssertFalse(facade.isReleased)
        XCTAssertThrowsError(try facade.reservePresentation())
        XCTAssertThrowsError(try presentation.retainOwner(ReservationOwner()))
        facade.beginClosing(); XCTAssertTrue(facade.isReleased)

        // Every kind's final destructor independently fences the outer slot,
        // including presentation before any guest was bound or started.
        for heldKind in 0..<3 {
            let owners = try (0..<16).map { _ in try CapabilityAttemptReservation.acquire() }
            let store = try owners[0].issueStoreAdmission().claimStore()
            let adapter = try owners[0].reserveAdapterGroup()
            let ui = try owners[0].reservePresentation()
            let entered = DispatchSemaphore(value: 0), release = DispatchSemaphore(value: 0), finished = DispatchSemaphore(value: 0)
            switch heldKind {
            case 0: try ui.retainOwner(RetiringProbe(entered, release))
            case 1: try store.retainOwner(RetiringProbe(entered, release))
            default: try adapter.retainOwner(RetiringProbe(entered, release))
            }
            owners[0].beginClosing()
            DispatchQueue.global().async {
                switch heldKind {
                case 0: ui.retire()
                case 1: store.retire()
                default: adapter.retire()
                }
                finished.signal()
            }
            XCTAssertEqual(entered.wait(timeout: .now() + 10), .success)
            if heldKind != 0 { ui.retire() }
            if heldKind != 1 { store.retire() }
            if heldKind != 2 { adapter.retire() }
            XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 16)
            XCTAssertFalse(owners[0].isReleased)
            XCTAssertThrowsError(try CapabilityAttemptReservation.acquire())
            XCTAssertThrowsError(try owners[0].reservePresentation())
            release.signal(); XCTAssertEqual(finished.wait(timeout: .now() + 10), .success)
            for owner in owners { owner.beginClosing() }
            XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 0)
        }

        let contested = try CapabilityAttemptReservation.acquire()
        let presentations = await withTaskGroup(of: CapabilityPresentationObligation?.self) { group in
            for _ in 0..<32 { group.addTask { try? contested.reservePresentation() } }
            var results: [CapabilityPresentationObligation] = []
            for await result in group { if let result { results.append(result) } }
            return results
        }
        XCTAssertEqual(presentations.count, 1)
        contested.beginClosing(); XCTAssertFalse(contested.isReleased)
        presentations[0].retire(); XCTAssertTrue(contested.isReleased)
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 0)

        let all = try (0..<16).map { _ in try CapabilityAttemptReservation.acquire() }
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 16)
        XCTAssertThrowsError(try CapabilityAttemptReservation.acquire())
        let entered = DispatchSemaphore(value: 0), release = DispatchSemaphore(value: 0), finished = DispatchSemaphore(value: 0)
        let adapter = try all[0].reserveAdapterGroup()
        try adapter.retainOwner(RetiringProbe(entered, release))
        XCTAssertThrowsError(try all[0].reserveAdapterGroup())
        all[0].beginClosing()
        DispatchQueue.global().async { adapter.retire(); finished.signal() }
        XCTAssertEqual(entered.wait(timeout: .now() + 10), .success)
        // Final retained owner destruction occurs outside reservation/pool locks
        // and capacity remains occupied until its destructor really completes.
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 16)
        XCTAssertFalse(all[0].isReleased)
        XCTAssertThrowsError(try CapabilityAttemptReservation.acquire())
        XCTAssertThrowsError(try all[0].issueStoreAdmission())
        release.signal(); XCTAssertEqual(finished.wait(timeout: .now() + 10), .success)
        for r in all { r.beginClosing() }
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 0)

        // Regression: the last ID can retire while a different moved owner is
        // still being destroyed. Both retirements must remain counted.
        let concurrent = try (0..<16).map { _ in try CapabilityAttemptReservation.acquire() }
        let store = try concurrent[0].issueStoreAdmission().claimStore()
        let secondEntered = DispatchSemaphore(value: 0), secondRelease = DispatchSemaphore(value: 0), secondFinished = DispatchSemaphore(value: 0)
        try store.retainOwner(RetiringProbe(secondEntered, secondRelease))
        let other = try concurrent[0].reserveAdapterGroup()
        concurrent[0].beginClosing()
        DispatchQueue.global().async { store.retire(); secondFinished.signal() }
        XCTAssertEqual(secondEntered.wait(timeout: .now() + 10), .success)
        other.retire()
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 16)
        XCTAssertFalse(concurrent[0].isReleased)
        XCTAssertThrowsError(try CapabilityAttemptReservation.acquire())
        secondRelease.signal(); XCTAssertEqual(secondFinished.wait(timeout: .now() + 10), .success)
        for r in concurrent { r.beginClosing() }
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 0)

        let unused = try CapabilityAttemptReservation.acquire()
        var admission: CapabilityRecoveryStoreAdmission? = try unused.issueStoreAdmission()
        XCTAssertNotNil(admission); unused.beginClosing(); XCTAssertFalse(unused.isReleased)
        admission = nil; XCTAssertTrue(unused.isReleased)

        let owner = try CapabilityAttemptReservation.acquire(), a = try owner.issueStoreAdmission()
        let claims = await withTaskGroup(of: CapabilityStoreObligation?.self) { group in
            for _ in 0..<32 { group.addTask { try? a.claimStore() } }
            var results: [CapabilityStoreObligation] = []
            for await result in group { if let result { results.append(result) } }
            return results
        }
        XCTAssertEqual(claims.count, 1)
        XCTAssertThrowsError(try owner.issueStoreAdmission()); XCTAssertThrowsError(try a.claimStore())
        let firstAdapter = try owner.reserveAdapterGroup(); firstAdapter.retire()
        let nextAdapter = try owner.reserveAdapterGroup()
        owner.beginClosing(); XCTAssertFalse(owner.isReleased)
        XCTAssertThrowsError(try owner.reserveAdapterGroup())
        claims[0].retire(); XCTAssertFalse(owner.isReleased)
        nextAdapter.retire(); nextAdapter.retire(); XCTAssertTrue(owner.isReleased)
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 0)

        let abandoned = try CapabilityAttemptReservation.acquire()
        var unfinished: CapabilityStoreObligation? = try abandoned.issueStoreAdmission().claimStore()
        XCTAssertNotNil(unfinished); unfinished = nil
        XCTAssertTrue(abandoned.isQuarantined); abandoned.beginClosing(); XCTAssertFalse(abandoned.isReleased)
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 1)

        let abandonedFacade = try CapabilityAttemptReservation.acquire()
        var unfinishedPresentation: CapabilityPresentationObligation? = try abandonedFacade.reservePresentation()
        XCTAssertNotNil(unfinishedPresentation); unfinishedPresentation = nil
        XCTAssertTrue(abandonedFacade.isQuarantined)
        XCTAssertThrowsError(try abandonedFacade.reservePresentation())
        abandonedFacade.beginClosing(); XCTAssertFalse(abandonedFacade.isReleased)
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, 2)
    }
}
