#if canImport(SwiftUI) && canImport(MixerApple)
import Foundation
import XCTest
import MixerUpdates
import MixerUI
import MixerCapabilities
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

final class GuestUISignedRuntimeTests: XCTestCase, @unchecked Sendable {
    private func fixture() throws -> GuestUISignedFixture {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-signed-ui-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        addTeardownBlock { try FileManager.default.removeItem(at: root) }
        return try GuestUISignedFixture(root: root)
    }
    private func open(_ f: GuestUISignedFixture) async throws -> CapabilityGuestUIRuntime {
        try await CapabilityGuestUIRuntime.openOwned(configuration:f.configuration, installed:f.execution.installed,
            environment:.init(wall:{1000}))
    }
    private func stage(_ f: GuestUISignedFixture, _ runtime: CapabilityGuestUIRuntime,
                       mode: GuestUISignedProgram.Mode = .valid, storage: Bool = true) async throws {
        let bytes = GuestUISignedProgram.build(mode), documents = try f.documents(bytes,storage:storage)
        try await runtime.beginDownload(signedManifest:documents.0,signedAssignment:documents.1)
        try await runtime.appendDownload(bytes,atOffset:0); try await runtime.finishDownload()
    }
    private func eventually(_ label: String, _ predicate: () async throws -> Bool) async throws {
        let end = ContinuousClock.now.advanced(by:.seconds(8))
        while !(try await predicate()) {
            guard ContinuousClock.now < end else { throw UpdateError("test.timeout",label) }
            try await Task.sleep(for:.milliseconds(2))
        }
    }
    private func close(_ runtime: CapabilityGuestUIRuntime, baseline: Int) async throws {
        await runtime.close()
        try await eventually("Actual UI/native retirement did not return capacity") { CapabilityAttemptReservation.occupiedSlots == baseline }
    }
    func testSignedStartupDisplaysButOffscreenCannotEarnHealth() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await open(f)
        try await stage(f,runtime)
        let start = try await runtime.start()
        XCTAssertEqual(start.phase,.provisionalGuest); XCTAssertTrue(start.effectsMayHaveOpened)
        try await eventually("Confirmed frame never reached model") {
            await MainActor.run { runtime.presentation.state == .displaying(revision:1) }
        }
        try await Task.sleep(for:.milliseconds(1150))
        let observed = await runtime.recoverySnapshot()
        XCTAssertNil(observed.healthy); XCTAssertEqual(observed.activation.phase,.provisionalGuest)
        XCTAssertNil(observed.activation.firstBridgeFailure); XCTAssertNil(observed.activation.firstUIProtocolFailure)
        try await close(runtime,baseline:before)
        let retired = await MainActor.run { runtime.presentation.state }
        XCTAssertEqual(retired,.stopped)
    }
    func testStartupUIProtocolFailureFallsBackWithoutTrapCoercionOrEffects() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await open(f)
        try await stage(f,runtime,mode:.invalidHeader)
        let result = try await runtime.start()
        XCTAssertEqual(result.phase,.nativeFallback); XCTAssertFalse(result.effectsMayHaveOpened)
        XCTAssertNil(result.firstBridgeFailure)
        XCTAssertEqual(result.firstUIProtocolFailure?.failure,.init(phase:.startup,code:.header))
        XCTAssertEqual(result.firstUIProtocolFailure?.effectStage,.beforeIntent)
        guard case .protocolViolation = result.terminalCause else { return XCTFail("Typed primary UI cause lost") }
        let state = try StrictJSON.decode(CapabilityRecoveryState.self,from:Data(contentsOf:f.configuration.directory.appendingPathComponent("state.json")))
        XCTAssertEqual(state.lastRecovery,"ui_protocol_before_effects")
        XCTAssertTrue(state.failures.isEmpty); XCTAssertTrue(state.quarantine.isEmpty)
        XCTAssertNil(state.attempt); XCTAssertNil(state.staged)
        try await close(runtime,baseline:before)
    }
    func testMissingRequiredUIExportCannotStageOrCreateAdapter() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await open(f)
        do { try await stage(f,runtime,mode:.missingEvent); XCTFail("UI export-less module staged") }
        catch { XCTAssertEqual(error as? GuestUIProtocolFailureV1,.init(phase:.validation,code:.requiredExport)) }
        let state = await runtime.recoverySnapshot()
        XCTAssertNil(state.staged); XCTAssertNil(state.healthy)
        XCTAssertFalse(FileManager.default.fileExists(atPath:f.root.appendingPathComponent("material_test").path))
        try await close(runtime,baseline:before)
    }
    func testPublicUIOpenRejectsLegacyIdentityBeforeFullPoolAndFilesystem() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        let legacy = try ColdStartFixture(root:f.root)
        let held = try (before..<16).map { _ in try CapabilityAttemptReservation.acquire() }
        defer { for p in held { p.beginClosing() } }
        let directory = f.root.appendingPathComponent("must-not-open")
        do {
            let runtime = try await CapabilityGuestUIRuntime.open(configuration:.init(directory:directory,channel:"beta",installation:"test"),execution:legacy.execution)
            await runtime.close(); XCTFail("UI facade accepted legacy mode")
        } catch { XCTAssertEqual((error as? UpdateError)?.code,"capability.runtime.installed_mode") }
        XCTAssertFalse(FileManager.default.fileExists(atPath:directory.path)); XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots,16)
    }
    func testPublicUIFacadeUsesSignedIngressWithoutCallerClockOrMilestone() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        let runtime = try await CapabilityGuestUIRuntime.open(configuration:f.configuration,execution:f.execution)
        try await stage(f,runtime); let start = try await runtime.start()
        XCTAssertEqual(start.phase,.provisionalGuest); XCTAssertNil(start.terminalCause)
        try await close(runtime,baseline:before)
    }
    func testWrongSignedPayloadFailsWithoutStagingOrEffects() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await open(f)
        let bytes = GuestUISignedProgram.build(), documents = try f.documents(bytes)
        try await runtime.beginDownload(signedManifest:documents.0,signedAssignment:documents.1)
        var changed = bytes; changed[changed.count-1] ^= 1
        try await runtime.appendDownload(changed,atOffset:0)
        do { try await runtime.finishDownload(); XCTFail("Foreign payload accepted") } catch {}
        let state = await runtime.recoverySnapshot()
        XCTAssertNil(state.staged); XCTAssertFalse(state.activation.effectsMayHaveOpened)
        try await close(runtime,baseline:before)
    }
    func testPostIntentPresentationFailurePublishesReopenInBothPublicSnapshots() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await open(f)
        try await stage(f,runtime); _ = try await runtime.start()
        try await eventually("Confirmed frame missing") {
            await MainActor.run { runtime.presentation.state == .displaying(revision:1) }
        }
        try await MainActor.run {
            _ = try XCTUnwrap(runtime.presentation.claimNativeAttachment())
            XCTAssertNil(runtime.presentation.claimNativeAttachment())
        }
        try await eventually("UI failure was not durably reconciled") {
            let snapshot = await runtime.recoverySnapshot()
            return snapshot.activation.phase == .recoveryRequired && !snapshot.incompleteAttempt && !snapshot.busy
        }
        let report = await runtime.recoverySnapshot()
        XCTAssertTrue(report.requiresReopen); XCTAssertTrue(report.activation.requiresReopen)
        XCTAssertTrue(report.activation.effectsMayHaveOpened); XCTAssertNil(report.activation.firstBridgeFailure)
        XCTAssertEqual(report.activation.firstUIProtocolFailure?.failure,.init(phase:.presentation,code:.presentationInvariant))
        XCTAssertEqual(report.activation.firstUIProtocolFailure?.effectStage,.intentEntered)
        XCTAssertNil(report.healthy)
        let state = try StrictJSON.decode(CapabilityRecoveryState.self,from:Data(contentsOf:f.configuration.directory.appendingPathComponent("state.json")))
        XCTAssertEqual(state.lastRecovery,"ui_protocol_after_effects")
        XCTAssertTrue(state.failures.isEmpty); XCTAssertTrue(state.quarantine.isEmpty)
        try await close(runtime,baseline:before)
    }
    private func activateSave(_ runtime: CapabilityGuestUIRuntime) async throws {
        try await eventually("First frame missing before input") {
            await MainActor.run { runtime.presentation.state == .displaying(revision:1) }
        }
        try await MainActor.run {
            let model = runtime.presentation
            let attachment = try XCTUnwrap(model.claimNativeAttachment())
            let host = try XCTUnwrap(model.renderHost), identity = try XCTUnwrap(host.snapshot.identity(for:"save"))
            let action = try host.route(UIEventEnvelope(revision:1,identity:identity,event:.activate))
            XCTAssertTrue(model.inputEnabled)
            model.actionHandler(host:host,attachment:attachment)(action)
            XCTAssertFalse(model.inputEnabled)
        }
    }
    func testSignedEventCommitsStorageBeforeGuestShowsSaved() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await open(f)
        try await stage(f,runtime); _ = try await runtime.start(); try await activateSave(runtime)
        try await eventually("Guest never consumed committed storage result") {
            await MainActor.run { runtime.presentation.state == .displaying(revision:3) }
        }
        let text = await MainActor.run { runtime.presentation.renderHost?.snapshot.document.root.children.first?.properties["text"] }
        XCTAssertEqual(text,.string("Saved sample"))
        let report = await runtime.recoverySnapshot()
        XCTAssertNil(report.healthy); XCTAssertNil(report.activation.terminalCause)
        try await close(runtime,baseline:before)
        let reader = try AppPrivateKeyValueStore(directory:f.root.appendingPathComponent("material_test"),namespaces:["material_test"])
        let stored = try await reader.get(.init(namespace:"material_test",key:"binary")); await reader.close()
        XCTAssertTrue(stored.found); XCTAssertEqual(stored.valueBase64,"AAH+/w==")
    }
    func testSignedEventWithoutGrantReportsUnavailableWithoutStorage() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await open(f)
        try await stage(f,runtime,storage:false); _ = try await runtime.start(); try await activateSave(runtime)
        try await eventually("Guest never consumed denial result") {
            await MainActor.run { runtime.presentation.state == .displaying(revision:3) }
        }
        let text = await MainActor.run { runtime.presentation.renderHost?.snapshot.document.root.children.first?.properties["text"] }
        XCTAssertEqual(text,.string("Save unavailable"))
        XCTAssertFalse(FileManager.default.fileExists(atPath:f.root.appendingPathComponent("material_test").path))
        try await close(runtime,baseline:before)
    }
    func testInvalidEventFrameStopsBeforeItsPutButInvalidWakePreservesCommittedPut() async throws {
        for mode: GuestUISignedProgram.Mode in [.invalidEventDocument,.invalidWakeDocument] {
            let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await open(f)
            try await stage(f,runtime,mode:mode); _ = try await runtime.start(); try await activateSave(runtime)
            try await eventually("Invalid frame did not durably stop signed coordinator") {
                let snapshot = await runtime.recoverySnapshot()
                return snapshot.activation.phase == .recoveryRequired && !snapshot.incompleteAttempt && !snapshot.busy
            }
            let report = await runtime.recoverySnapshot()
            XCTAssertTrue(report.requiresReopen); XCTAssertTrue(report.activation.requiresReopen)
            XCTAssertNil(report.healthy); XCTAssertNil(report.activation.firstBridgeFailure)
            XCTAssertEqual(report.activation.firstUIProtocolFailure?.effectStage,.intentEntered)
            try await close(runtime,baseline:before)
            let reader = try AppPrivateKeyValueStore(directory:f.root.appendingPathComponent("material_test"),namespaces:["material_test"])
            let stored = try await reader.get(.init(namespace:"material_test",key:"binary")); await reader.close()
            XCTAssertEqual(stored.found,mode == .invalidWakeDocument)
            if stored.found { XCTAssertEqual(stored.valueBase64,"AAH+/w==") }
        }
    }
}
#endif
