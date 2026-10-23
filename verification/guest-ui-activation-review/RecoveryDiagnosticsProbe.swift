import Foundation
import XCTest
import MixerUpdates
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

/// This probe drives private store transitions after real signed download and
/// native module validation. It does not construct/enable a VM or earn health.
final class RecoveryDiagnosticsProbe: XCTestCase, @unchecked Sendable {
    func testPostIntentUIFailurePublishesRequiresReopen() async throws {
        try await exercise(intent: true)
    }

    func testBeforeIntentUIFailureDoesNotRequireReopen() async throws {
        try await exercise(intent: false)
    }

    private func exercise(intent: Bool) async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-ui-review-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: directory) }
        let fixture = try GuestUISignedFixture(root: directory)
        let reservation = try CapabilityAttemptReservation.acquire()
        let store = try await CapabilityRecoveryStore.open(admission: reservation.issueStoreAdmission(),
            installed: fixture.execution.installed, configuration: fixture.configuration.checked(),
            environment: .init(wall: { 1000 }), guestUI: true)
        let bytes = GuestUISignedProgram.build(), documents = try fixture.documents(bytes)
        try await store.beginDownload(signedManifest: documents.0, signedAssignment: documents.1)
        try await store.appendDownload(bytes, atOffset: 0)
        try await store.finishDownload()
        let selection = try await store.prepareStartupSelection()
        let selected = try XCTUnwrap(selection)
        let exchange = try GuestUIExchangeV1(generation: selected.generation)
        let signals = CapabilityAttemptSignals(generation: selected.generation, guestUI: exchange)
        let consumed = try await store.consume(selected, signals: signals)
        try exchange.finishTurn(exchange.claimStartup(), documentBytes: GuestUISignedProgram.document(1, "Ready"))
        if intent { try await store.recordEffectsIntent(consumed, signals: signals) }
        exchange.recordProtocolFailure(.init(phase: .presentation, code: .presentationInvariant))
        let disposition = try await store.failAndPrepareFallback(consumed, signals: signals, allowFallback: false)
        let snapshot = store.snapshot
        let state = try StrictJSON.decode(CapabilityRecoveryState.self,
            from: Data(contentsOf: fixture.configuration.directory.appendingPathComponent("state.json")))
        print("REVIEW observed intent=\(intent) requiresReopen=\(snapshot.requiresReopen) lastRecovery=\(state.lastRecovery)")
        XCTAssertEqual(state.lastRecovery, intent ? "ui_protocol_after_effects" : "ui_protocol_before_effects")
        XCTAssertTrue(state.failures.isEmpty)
        XCTAssertTrue(state.quarantine.isEmpty)
        switch (intent, disposition) {
        case (true, .recoveryRequired), (false, .nativeFallback): break
        default: XCTFail("Unexpected recovery disposition")
        }
        XCTAssertEqual(snapshot.requiresReopen, intent,
            "The public recovery projection must publish the post-intent reopen requirement")
        signals.finishNotifications()
        store.requestStop()
        await store.close()
        reservation.beginClosing()
    }
}
