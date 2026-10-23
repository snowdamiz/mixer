import Foundation
import XCTest
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

final class GuestUISignalTests: XCTestCase, @unchecked Sendable {
    private func started() throws -> (GuestUIExchangeV1, CapabilityAttemptSignals) {
        let exchange = try GuestUIExchangeV1(generation:1)
        try exchange.finishTurn(exchange.claimStartup(),documentBytes:GuestUISignedProgram.document(1,"Ready"))
        return (exchange,CapabilityAttemptSignals(generation:1,guestUI:exchange))
    }
    func testProtocolStopBeforeIntentBlocksEveryCommitWithoutLegacyCauseCoercion() throws {
        let (exchange,signals) = try started()
        exchange.recordProtocolFailure(.init(phase:.startup,code:.document))
        XCTAssertThrowsError(try signals.enterEffectsIntentCommit(expectedGeneration:1))
        XCTAssertThrowsError(try signals.requireCommitEntry(expectedGeneration:1))
        let state = signals.snapshot
        XCTAssertTrue(state.stopped); XCTAssertNil(state.firstCause); XCTAssertNil(state.firstBridgeFailure)
        XCTAssertFalse(state.effectsMayHaveOpened)
        XCTAssertEqual(state.guestUI?.firstUIProtocolFailure?.effectStage,.beforeIntent)
    }
    func testProtocolStopAfterIntentKeepsUncertaintyAndPrimaryTypedCause() throws {
        let (exchange,signals) = try started()
        try signals.enterEffectsIntentCommit(expectedGeneration:1)
        exchange.recordProtocolFailure(.init(phase:.wake,code:.document))
        signals.requestStop(.closed)
        let state = signals.snapshot
        XCTAssertTrue(state.stopped); XCTAssertTrue(state.effectsMayHaveOpened); XCTAssertNil(state.firstCause)
        XCTAssertEqual(state.guestUI?.firstUIProtocolFailure?.effectStage,.intentEntered)
        guard case .protocolViolation = state.guestUI?.stop else { return XCTFail("Late close replaced UI cause") }
    }
    func testConcurrentIntentAndProtocolStopHaveOneSharedOrdering() throws {
        for _ in 0..<128 {
            let (exchange,signals) = try started()
            DispatchQueue.concurrentPerform(iterations:2) { i in
                if i == 0 { try? signals.enterEffectsIntentCommit(expectedGeneration:1) }
                else { exchange.recordProtocolFailure(.init(phase:.event,code:.document)) }
            }
            let state = signals.snapshot, terminal = try XCTUnwrap(state.guestUI?.firstUIProtocolFailure)
            XCTAssertEqual(state.effectsMayHaveOpened,terminal.effectStage == .intentEntered)
            XCTAssertTrue(state.stopped); XCTAssertThrowsError(try signals.requireCommitEntry(expectedGeneration:1))
        }
    }
    func testUIControlWakeUsesSingleReaderAndFinishPreservesFinalHint() async throws {
        let (exchange,signals) = try started(), reader = try exchange.coordinatorWake.takeConsumer()
        signals.recordControlWake(expectedGeneration:1)
        signals.requestStop(.cancelled); signals.finishNotifications()
        let finalHint = try await reader.next(), ended = try await reader.next()
        XCTAssertTrue(finalHint); XCTAssertFalse(ended)
        XCTAssertEqual(signals.snapshot.guestUI?.stop,.cancelled)
    }
}
