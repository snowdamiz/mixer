#if canImport(SwiftUI) && canImport(MixerApple)
import Foundation
import XCTest
import MixerUpdates
import MixerUI
import MixerCapabilities
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

private actor SignedRuntimeRetirement {
    let runtime: CapabilityGuestUIRuntime
    private var job: Task<Void, Never>?
    private var closeReturned = false
    private var deadline: ContinuousClock.Instant?
    private var failure: UpdateError?
    init(_ runtime: CapabilityGuestUIRuntime) { self.runtime = runtime }
    var retired: Bool { closeReturned && runtime.ownerRetired }
    func close() async throws {
        if let failure { throw failure }
        if job == nil {
            deadline = .now + .seconds(8)
            job = Task { await runtime.close(); closeReturned = true }
        }
        while !closeReturned || !runtime.ownerRetired {
            guard ContinuousClock.now < deadline! else {
                let error = UpdateError("test.timeout", "This UI owner did not finish close and actual retirement")
                failure = error; throw error
            }
            try await Task.sleep(for: .milliseconds(2))
        }
        await job?.value
    }
}

final class GuestUISignedRuntimeTests: XCTestCase, @unchecked Sendable {
    private var owners: [ObjectIdentifier: SignedRuntimeRetirement] = [:]
    private var fixtureOwners: [String: [SignedRuntimeRetirement]] = [:]
    private var incompleteOpen = Set<String>()
    private func withRuntime(_ fixture: GuestUISignedFixture, publicIngress: Bool = false,
                             _ body: (CapabilityGuestUIRuntime) async throws -> Void) async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots
        incompleteOpen.insert(fixture.root.path)
        let runtime = try await (publicIngress
            ? CapabilityGuestUIRuntime.open(configuration: fixture.configuration, execution: fixture.execution)
            : open(fixture))
        let owner = SignedRuntimeRetirement(runtime)
        owners[ObjectIdentifier(runtime)] = owner
        fixtureOwners[fixture.root.path, default: []].append(owner)
        incompleteOpen.remove(fixture.root.path)
        do { try await body(runtime) }
        catch {
            let original = error
            do { try await close(runtime, baseline: baseline) }
            catch { XCTFail("Cleanup after test body failure also failed: \(error)") }
            throw original
        }
        try await close(runtime, baseline: baseline)
    }
    private func fixture() throws -> GuestUISignedFixture {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-signed-ui-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        addTeardownBlock { [self] in
            guard !incompleteOpen.contains(root.path) else {
                XCTFail("Retaining fixture after incomplete open: \(root.path)"); return
            }
            for owner in fixtureOwners[root.path] ?? [] {
                guard await owner.retired else {
                    XCTFail("Retaining fixture while its owner has not retired: \(root.path)"); return
                }
            }
            try FileManager.default.removeItem(at: root)
        }
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
    private func observeLifecycle(_ boundary: String, _ runtime: CapabilityGuestUIRuntime) async {
        let presentation = await MainActor.run {
            let model = runtime.presentation
            guard let value = model.lifecycleObservation else { return "state=\(model.state) exchange=nil" }
            return "state=\(model.state) input=\(model.inputEnabled) generation=\(value.generation) turn=\(value.guestTurnInFlight) event=\(value.eventOutstanding) presentation=\(value.presentationInFlight) latest=\(String(describing:value.latestRevision)) displayed=\(String(describing:value.displayedRevision)) accepted=\(value.counters.acceptedEvents) delivered=\(value.counters.deliveredEvents) terminal=\(value.counters.terminalEvents) turns=\(value.counters.successfulTurns) stop=\(String(describing:value.stop))"
        }
        let recovery = await runtime.recoverySnapshot()
        print("LIFECYCLE \(boundary) pool=\(CapabilityAttemptReservation.occupiedSlots) \(presentation) phase=\(recovery.activation.phase) closed=\(recovery.closed) busy=\(recovery.busy) cleanupPending=\(recovery.activation.cleanupPending) incomplete=\(recovery.incompleteAttempt) bridge=\(String(describing:recovery.activation.firstBridgeFailure)) ui=\(String(describing:recovery.activation.firstUIProtocolFailure))")
    }
    private func eventually(_ label: String, _ predicate: () async throws -> Bool) async throws {
        let end = ContinuousClock.now.advanced(by:.seconds(8))
        while !(try await predicate()) {
            guard ContinuousClock.now < end else { throw UpdateError("test.timeout",label) }
            try await Task.sleep(for:.milliseconds(2))
        }
    }
    private func close(_ runtime: CapabilityGuestUIRuntime, baseline: Int) async throws {
        await observeLifecycle("before-close expectedGlobal=\(baseline)",runtime)
        let owner = try XCTUnwrap(owners[ObjectIdentifier(runtime)])
        do {
            try await owner.close()
            await observeLifecycle("close-return diagnosticGlobal=\(baseline)",runtime)
            XCTAssertTrue(runtime.ownerRetired)
            let snapshot = await runtime.recoverySnapshot()
            XCTAssertTrue(snapshot.closed); XCTAssertFalse(snapshot.activation.cleanupPending)
        } catch {
            await observeLifecycle("retirement-timeout expectedGlobal=\(baseline)",runtime)
            throw error
        }
    }
    func testSignedStartupDisplaysButOffscreenCannotEarnHealth() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        try await withRuntime(f) { runtime in
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
    }
    func testStartupUIProtocolFailureFallsBackWithoutTrapCoercionOrEffects() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        try await withRuntime(f) { runtime in
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
    }
    func testMissingRequiredUIExportCannotStageOrCreateAdapter() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        try await withRuntime(f) { runtime in
            do { try await stage(f,runtime,mode:.missingEvent); XCTFail("UI export-less module staged") }
            catch { XCTAssertEqual(error as? GuestUIProtocolFailureV1,.init(phase:.validation,code:.requiredExport)) }
            let state = await runtime.recoverySnapshot()
            XCTAssertNil(state.staged); XCTAssertNil(state.healthy)
            XCTAssertFalse(FileManager.default.fileExists(atPath:f.root.appendingPathComponent("material_test").path))
            try await close(runtime,baseline:before)
        }
    }
    func testPublicUIOpenRejectsLegacyIdentityBeforeFullPoolAndFilesystem() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        let legacy = try ColdStartFixture(root:f.root)
        let held = try (before..<16).map { _ in try CapabilityAttemptReservation.acquire() }
        defer { for p in held { p.beginClosing() } }
        let directory = f.root.appendingPathComponent("must-not-open")
        do {
            let runtime = try await CapabilityGuestUIRuntime.open(configuration:.init(directory:directory,channel:"beta",installation:"test"),execution:legacy.execution)
            let owner = SignedRuntimeRetirement(runtime)
            owners[ObjectIdentifier(runtime)] = owner
            fixtureOwners[f.root.path, default: []].append(owner)
            try await close(runtime, baseline: before); XCTFail("UI facade accepted legacy mode")
        } catch { XCTAssertEqual((error as? UpdateError)?.code,"capability.runtime.installed_mode") }
        XCTAssertFalse(FileManager.default.fileExists(atPath:directory.path)); XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots,16)
    }
    func testPublicUIFacadeUsesSignedIngressWithoutCallerClockOrMilestone() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        try await withRuntime(f, publicIngress: true) { runtime in
            try await stage(f,runtime); let start = try await runtime.start()
            XCTAssertEqual(start.phase,.provisionalGuest); XCTAssertNil(start.terminalCause)
            try await close(runtime,baseline:before)
        }
    }
    func testWrongSignedPayloadFailsWithoutStagingOrEffects() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        try await withRuntime(f) { runtime in
            let bytes = GuestUISignedProgram.build(), documents = try f.documents(bytes)
            try await runtime.beginDownload(signedManifest:documents.0,signedAssignment:documents.1)
            var changed = bytes; changed[changed.count-1] ^= 1
            try await runtime.appendDownload(changed,atOffset:0)
            do { try await runtime.finishDownload(); XCTFail("Foreign payload accepted") } catch {}
            let state = await runtime.recoverySnapshot()
            XCTAssertNil(state.staged); XCTAssertFalse(state.activation.effectsMayHaveOpened)
            try await close(runtime,baseline:before)
        }
    }
    func testPostIntentPresentationFailurePublishesReopenInBothPublicSnapshots() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        try await withRuntime(f) { runtime in
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
            let before = model.lifecycleObservation
            model.actionHandler(host:host,attachment:attachment)(action)
            let after = model.lifecycleObservation
            print("LIFECYCLE input beforeTurn=\(String(describing:before?.guestTurnInFlight)) acceptedBefore=\(String(describing:before?.counters.acceptedEvents)) acceptedAfter=\(String(describing:after?.counters.acceptedEvents)) eventAfter=\(String(describing:after?.eventOutstanding)) stopAfter=\(String(describing:after?.stop))")
            XCTAssertFalse(model.inputEnabled)
        }
    }
    func testSignedEventCommitsStorageBeforeGuestShowsSaved() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        try await withRuntime(f) { runtime in
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
    }
    func testSignedEventWithoutGrantReportsUnavailableWithoutStorage() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
        try await withRuntime(f) { runtime in
            try await stage(f,runtime,storage:false); _ = try await runtime.start(); try await activateSave(runtime)
            do {
                try await eventually("Guest never consumed denial result") {
                    await MainActor.run { runtime.presentation.state == .displaying(revision:3) }
                }
            } catch {
                await observeLifecycle("denial-result-timeout",runtime)
                throw error
            }
            let text = await MainActor.run { runtime.presentation.renderHost?.snapshot.document.root.children.first?.properties["text"] }
            XCTAssertEqual(text,.string("Save unavailable"))
            XCTAssertFalse(FileManager.default.fileExists(atPath:f.root.appendingPathComponent("material_test").path))
            try await close(runtime,baseline:before)
        }
    }
    func testInvalidEventFrameStopsBeforeItsPutButInvalidWakePreservesCommittedPut() async throws {
        for mode: GuestUISignedProgram.Mode in [.invalidEventDocument,.invalidWakeDocument] {
            let before = CapabilityAttemptReservation.occupiedSlots, f = try fixture()
            try await withRuntime(f) { runtime in
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
    func testThrowingBodyClosesExactRuntimeBeforeErrorEscapes() async throws {
        let f = try fixture()
        var captured: CapabilityGuestUIRuntime?
        do {
            try await withRuntime(f) { runtime in
                captured = runtime
                try await stage(f, runtime); _ = try await runtime.start()
                throw UpdateError("test.injected_body_failure", "Intentional body failure")
            }
            XCTFail("Original body failure was swallowed")
        } catch { XCTAssertEqual((error as? UpdateError)?.code, "test.injected_body_failure") }
        let runtime = try XCTUnwrap(captured)
        XCTAssertTrue(runtime.ownerRetired)
        let snapshot = await runtime.recoverySnapshot()
        XCTAssertTrue(snapshot.closed); XCTAssertFalse(snapshot.activation.cleanupPending)
    }
}
#endif
