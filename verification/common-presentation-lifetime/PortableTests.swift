import XCTest
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

final class PortablePresentationTests: XCTestCase, @unchecked Sendable {
    func testUnsupportedPrepareRetiresUnusedObligationBeforeThrowing() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots
        for _ in 0..<32 {
            let reservation = try CapabilityAttemptReservation.acquire()
            do {
                _ = try await CapabilityGuestUIPresentationBinding.prepare(reservation: reservation)
                XCTFail("Portable signed UI unexpectedly became available")
            } catch let failure as GuestUIProtocolFailureV1 {
                XCTAssertEqual(failure, GuestUIProtocolFailureV1(phase: .presentation, code: .presentationInvariant))
            }
            // Issue remains one-shot even though the unsupported path explicitly
            // retired its unused obligation before returning the rejection.
            XCTAssertThrowsError(try reservation.reservePresentation())
            XCTAssertFalse(reservation.isQuarantined)
            reservation.beginClosing()
            XCTAssertTrue(reservation.isReleased)
            XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, baseline)
        }
    }
}
