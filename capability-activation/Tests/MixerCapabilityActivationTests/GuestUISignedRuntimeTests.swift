#if canImport(SwiftUI) && canImport(MixerApple)
import Foundation
import XCTest
import MixerUpdates
import MixerUI
@_spi(InstalledApplicationStorage) import MixerCapabilities
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation
#if os(macOS)
import AppKit
import SwiftUI
#endif

private actor SignedApplicationRepository: InstalledApplicationStorageServing {
    static let namespace = "material_test"
    private let store: AppPrivateKeyValueStore
    private(set) var writes: [KVPutArguments] = []

    init(directory: URL) throws {
        store = try AppPrivateKeyValueStore(directory: directory, namespaces: [Self.namespace],
                                            maximumTotalBytes: 4_194_304, maximumEntries: 1024)
    }

    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        try await store.get(arguments)
    }

    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        writes.append(arguments)
        guard maximumTotalBytes == 4_194_304, maximumEntries == 1024 else { throw CapabilityFailure.ioFailure }
        return try await store.put(arguments)
    }

    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        try await store.delete(arguments)
    }

    func close() async { await store.close() }
}

private actor SignedCommitFactsProbe: InstalledApplicationStorageServing {
    private(set) var events: [InstalledGuestUICommitEvent] = []
    private(set) var ordinaryReads: [KVGetArguments] = []

    func read(_ event: InstalledGuestUICommitEvent) -> KVGetResponse {
        events.append(event)
        return .init(found: true, valueBase64: "AQ==")
    }
    func get(_ arguments: KVGetArguments) throws -> KVGetResponse {
        ordinaryReads.append(arguments)
        guard arguments == .init(namespace: "material_test", key: "trigger") else { throw CapabilityFailure.permissionDenied }
        return .init(found: true, valueBase64: "AQ==")
    }
    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) throws -> KVMutationResponse {
        throw CapabilityFailure.permissionDenied
    }
    func delete(_ arguments: KVDeleteArguments) throws -> KVMutationResponse {
        throw CapabilityFailure.permissionDenied
    }
}

private actor SignedRuntimeRetirement {
    let runtime: CapabilityGuestUIRuntime
    private var job: Task<Void, Never>?
    private var closeReturned = false
    private var deadline: ContinuousClock.Instant?
    private var failure: UpdateError?
    init(_ runtime: CapabilityGuestUIRuntime) { self.runtime = runtime }
    private(set) var retired = false
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
        let snapshot = await runtime.recoverySnapshot()
        guard snapshot.closed, !snapshot.activation.cleanupPending else {
            let error = UpdateError("test.retirement_unconfirmed", "This UI owner still has cleanup pending")
            failure = error
            throw error
        }
        retired = true
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
    private func requireFixtureRetirement(_ root: URL) async throws {
        guard !incompleteOpen.contains(root.path) else {
            throw UpdateError("test.retirement_unconfirmed", "Retaining fixture after incomplete open: \(root.path)")
        }
        for owner in fixtureOwners[root.path] ?? [] {
            guard await owner.retired else {
                throw UpdateError("test.retirement_unconfirmed", "Retaining fixture while its owner has not retired: \(root.path)")
            }
        }
    }
    private func fixtureRoot() throws -> URL {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-signed-ui-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        addTeardownBlock { [self] in
            try await requireFixtureRetirement(root)
            try FileManager.default.removeItem(at: root)
        }
        return root
    }
    private func fixture(commitProbe: SignedCommitFactsProbe? = nil,
                         commitAction: String = "sample.save") throws -> GuestUISignedFixture {
        let facts = commitProbe.map { probe in
            InstalledGuestUICommitFacts(arguments: .init(namespace: "material_test", key: "facts"),
                                        nodeID: "save", actionID: commitAction) { event in
                await probe.read(event)
            }
        }
        return try GuestUISignedFixture(root: fixtureRoot(), storageService: commitProbe, commitFacts: facts)
    }
    private func open(_ f: GuestUISignedFixture) async throws -> CapabilityGuestUIRuntime {
        try await CapabilityGuestUIRuntime.openOwned(configuration:f.configuration, installed:f.execution.installed,
            environment:.init(wall:{1000}))
    }
    private func stage(_ f: GuestUISignedFixture, _ runtime: CapabilityGuestUIRuntime,
                       mode: GuestUISignedProgram.Mode = .valid, storage: Bool = true,
                       payload: Data? = nil, sequence: UInt64 = 1) async throws {
        let bytes = payload ?? GuestUISignedProgram.build(mode)
        let documents = try f.documents(bytes, sequence: sequence, storage: storage)
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
    @discardableResult
    private func activateSave(_ runtime: CapabilityGuestUIRuntime) async throws -> @MainActor @Sendable () -> Void {
        try await eventually("First frame missing before input") {
            await MainActor.run { runtime.presentation.state == .displaying(revision:1) }
        }
        return try await MainActor.run {
            let model = runtime.presentation
            let attachment = try XCTUnwrap(model.claimNativeAttachment())
            let host = try XCTUnwrap(model.renderHost), identity = try XCTUnwrap(host.snapshot.identity(for:"save"))
            let action = try host.route(UIEventEnvelope(revision:1,identity:identity,event:.activate))
            XCTAssertTrue(model.inputEnabled)
            let before = model.lifecycleObservation
            let handle = model.actionHandler(host:host,attachment:attachment)
            handle(action)
            let after = model.lifecycleObservation
            print("LIFECYCLE input beforeTurn=\(String(describing:before?.guestTurnInFlight)) acceptedBefore=\(String(describing:before?.counters.acceptedEvents)) acceptedAfter=\(String(describing:after?.counters.acceptedEvents)) eventAfter=\(String(describing:after?.eventOutstanding)) stopAfter=\(String(describing:after?.stop))")
            XCTAssertFalse(model.inputEnabled)
            return { handle(action) }
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
    func testSignedCommitFactsReadUsesAcceptedEventOnceAndRetiresWithOwner() async throws {
        let probe = SignedCommitFactsProbe()
        let f = try fixture(commitProbe: probe)
        let baseline = CapabilityAttemptReservation.occupiedSlots
        try await withRuntime(f) { runtime in
            try await stage(f, runtime, mode: .commitFacts)
            _ = try await runtime.start()
            try await eventually("First signed frame missing") {
                await MainActor.run { runtime.presentation.state == .displaying(revision: 1) }
            }
            let initialEvents = await probe.events
            XCTAssertTrue(initialEvents.isEmpty)
            let generation = try await MainActor.run { try XCTUnwrap(runtime.presentation.lifecycleObservation?.generation) }
            let replay = try await activateSave(runtime)
            try await eventually("Guest did not consume the authorized read and duplicate denial") {
                await MainActor.run { runtime.presentation.state == .displaying(revision: 4) }
            }
            let delivered = await MainActor.run {
                replay() // This handler was bound to the now-stale displayed frame.
                XCTAssertEqual(runtime.presentation.lifecycleObservation?.counters.acceptedEvents, 1)
                return runtime.presentation.lastEventResult
            }
            let events = await probe.events
            XCTAssertEqual(events.count, 1)
            let event = try XCTUnwrap(events.first)
            XCTAssertEqual(event.generation, generation)
            XCTAssertEqual(event.sequence, 1)
            XCTAssertEqual(event.sequence, delivered?.sequence)
            XCTAssertEqual(delivered?.outcome, .delivered)
            XCTAssertGreaterThan(event.turnSerial, 1)
            XCTAssertEqual(event.displayedRevision, 1)
            XCTAssertEqual(event.nodeID, "save")
            XCTAssertEqual(event.actionID, "sample.save")
            XCTAssertTrue(event.isLive)
            let ordinary = await probe.ordinaryReads
            XCTAssertTrue(ordinary.isEmpty)
            try await close(runtime, baseline: baseline)
            XCTAssertFalse(event.isLive)
            await replay()
            let afterRetirement = await probe.events
            XCTAssertEqual(afterRetirement.count, 1)
        }
    }

    func testSignedCommitFactsReadDeniesReadyWrongActionAndMalformedEvent() async throws {
        let denied = try GuestCapabilityTransportCodecV1.encodeCompletion(
            .failure(.permissionDenied), operation: .storageGet)
        for (mode, action) in [(GuestUISignedProgram.Mode.readyCommitFacts, "sample.save"),
                               (.commitFacts, "sample.other"), (.invalidCommitFacts, "sample.save")] {
            let probe = SignedCommitFactsProbe()
            let f = try fixture(commitProbe: probe, commitAction: action)
            let payload = mode == .commitFacts ? GuestUISignedProgram.build(mode, expectedDenial: denied) : nil
            try await withRuntime(f) { runtime in
                try await stage(f, runtime, mode: mode, payload: payload)
                _ = try await runtime.start()
                try await activateSave(runtime)
                if mode == .invalidCommitFacts {
                    try await eventually("Malformed signed event did not stop") {
                        await runtime.recoverySnapshot().activation.firstUIProtocolFailure?.failure.phase == .event
                    }
                    let failure = await runtime.recoverySnapshot().activation.firstUIProtocolFailure?.failure
                    XCTAssertEqual(failure?.code, .document)
                } else {
                    let revision: UInt64 = mode == .readyCommitFacts ? 4 : 3
                    try await eventually("Guest did not consume the scoped read denial") {
                        await MainActor.run { runtime.presentation.state == .displaying(revision: revision) }
                    }
                }
            }
            let events = await probe.events
            let ordinary = await probe.ordinaryReads
            XCTAssertTrue(events.isEmpty)
            XCTAssertEqual(ordinary, mode == .readyCommitFacts ? [.init(namespace: "material_test", key: "trigger")] : [])
        }
    }
    #if os(macOS)
    func testSignedLocalizedChecklistActionIsReachableInShortAppKitViewports() async throws {
        try XCTSkipUnless(ProcessInfo.processInfo.environment["MIXER_GUEST_UI_VISIBLE_WINDOW"] == "1")
        await MainActor.run {
            let app = NSApplication.shared
            app.setActivationPolicy(.accessory)
            app.finishLaunching()
        }

        for height in [96, 16, 32] {
            for size in [DynamicTypeSize.large, .accessibility5] {
                let f = try fixture()
                try await withRuntime(f, publicIngress: true) { runtime in
                    try await stage(f, runtime, mode: .localizedChecklist, storage: true)
                    try await exerciseLocalizedChecklist(runtime, height: height, size: size)
                }
            }
        }
    }

    @MainActor
    private func exerciseLocalizedChecklist(_ runtime: CapabilityGuestUIRuntime, height: Int, size: DynamicTypeSize) async throws {
        let label = "288x\(height) \(size)"
        let view = NSHostingView(rootView: MixerGuestScreen(presentation: runtime.presentation)
            .environment(\.layoutDirection, .rightToLeft)
            .dynamicTypeSize(size))
        view.sizingOptions = []
        let viewport = NSRect(x: 40, y: 80, width: 288, height: height)
        let window = NSWindow(contentRect: viewport, styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        defer {
            window.orderOut(nil)
            window.contentView = nil
            window.close()
            XCTAssertFalse(window.isVisible)
            XCTAssertNil(view.window)
        }
        window.contentView = view
        window.orderFrontRegardless()
        let start = try await runtime.start()
        XCTAssertEqual(start.phase, .provisionalGuest, label)
        try await awaitPresentation {
            view.layoutSubtreeIfNeeded()
            window.displayIfNeeded()
            return runtime.presentation.state == .displaying(revision: 1) && runtime.presentation.inputEnabled
        }
        XCTAssertEqual(view.visibleRect.size, viewport.size, label)
        XCTAssertTrue(window.isVisible, label)
        let scrollView = nativeScrollView(in: view)
        let travel = scrollView.map { max(0, $0.contentView.documentRect.height - $0.contentView.bounds.height) } ?? 0
        print("FieldLog AppKit \(label) nativeScrollView=\(scrollView != nil) travel=\(travel)")
        if height == 96 {
            XCTAssertEqual(travel, 0, accuracy: 1, label)
        } else {
            XCTAssertGreaterThan(travel, 0, label)
            if let scrollView {
                if height == 16 {
                    XCTAssertNil(try clickChecklistAction(in: window, height: height, presentation: runtime.presentation), label)
                }
                let clip = scrollView.contentView
                let initial = clip.bounds.origin
                let bottom = clip.isFlipped ? clip.documentRect.maxY - clip.bounds.height : clip.documentRect.minY
                clip.scroll(to: NSPoint(x: initial.x, y: bottom))
                scrollView.reflectScrolledClipView(clip)
                view.layoutSubtreeIfNeeded()
                window.displayIfNeeded()
                XCTAssertEqual(abs(clip.bounds.minY - initial.y), travel, accuracy: 1, label)
                print("FieldLog AppKit \(label) scrollY=\(initial.y)->\(clip.bounds.minY)")
            }
        }

        // Pointer events are delivered only to the owned fixture window.
        XCTAssertEqual(runtime.presentation.lifecycleObservation?.counters.acceptedEvents, 0, label)
        let hit = try clickChecklistAction(in: window, height: height, presentation: runtime.presentation)
        print("FieldLog AppKit \(label) hitRow=\(String(describing: hit))")
        XCTAssertNotNil(hit, label)
        guard hit != nil else { return }
        try await awaitPresentation { runtime.presentation.state == .displaying(revision: 3) }
        XCTAssertEqual(runtime.presentation.renderHost?.snapshot.document.root.children[1].properties["text"],
                       .string("اكتمل الفحص"), label)
        XCTAssertEqual(runtime.presentation.lifecycleObservation?.counters.acceptedEvents, 1, label)
    }

    @MainActor
    private func nativeScrollView(in view: NSView) -> NSScrollView? {
        if let scrollView = view as? NSScrollView { return scrollView }
        for child in view.subviews {
            if let scrollView = nativeScrollView(in: child) { return scrollView }
        }
        return nil
    }

    @MainActor
    private func clickChecklistAction(in window: NSWindow, height: Int, presentation: GuestUIPresentation) throws -> Int? {
        for row in 0..<height {
            let point = NSPoint(x: window.contentLayoutRect.midX, y: Double(row) + 0.5)
            for type in [NSEvent.EventType.leftMouseDown, .leftMouseUp] {
                let event = try XCTUnwrap(NSEvent.mouseEvent(with: type, location: point, modifierFlags: [],
                    timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber,
                    context: nil, eventNumber: 0, clickCount: 1, pressure: 1))
                window.sendEvent(event)
            }
            if presentation.lifecycleObservation?.counters.acceptedEvents == 1 { return row }
        }
        return nil
    }
    #endif
    func testInstalledApplicationStorageGrantDenialAndColdReadback() async throws {
        let root = try fixtureRoot()
        let directory = root.appendingPathComponent("app-owned-repository", isDirectory: true)
        let namespace = SignedApplicationRepository.namespace
        let expected = KVPutArguments(namespace: namespace, key: "binary", valueBase64: "AAH+/w==")
        let denial = try GuestCapabilityTransportCodecV1.encodeCompletion(.failure(.permissionDenied), operation: .storagePut)
        let repository = try SignedApplicationRepository(directory: directory)
        do {
            let fixture = try GuestUISignedFixture(root: root, storageService: repository, boundNamespace: namespace)
            for sequence: UInt64 in [1, 2] {
                let allowed = sequence == 1
                let payload = GuestUISignedProgram.build(storageNamespace: allowed ? namespace : "outside_scope",
                                                         expectedDenial: allowed ? nil : denial)
                try await withRuntime(fixture, publicIngress: true) { runtime in
                    try await stage(fixture, runtime, payload: payload, sequence: sequence)
                    let start = try await runtime.start()
                    XCTAssertTrue(start.effectsMayHaveOpened)
                    try await activateSave(runtime)
                    try await eventually("Guest did not consume the expected storage completion") {
                        await MainActor.run { runtime.presentation.state == .displaying(revision: 3) }
                    }
                    let text = await MainActor.run {
                        runtime.presentation.renderHost?.snapshot.document.root.children.first?.properties["text"]
                    }
                    XCTAssertEqual(text, .string(allowed ? "Saved sample" : "Save unavailable"))
                    let writes = await repository.writes
                    XCTAssertEqual(writes, [expected])
                }
            }
        } catch {
            if (try? await requireFixtureRetirement(root)) != nil {
                await repository.close()
            }
            throw error
        }
        try await requireFixtureRetirement(root)
        await repository.close()

        XCTAssertFalse(FileManager.default.fileExists(atPath: root.appendingPathComponent(namespace).path))
        let reopened = try SignedApplicationRepository(directory: directory)
        let value: KVGetResponse
        do { value = try await reopened.get(.init(namespace: namespace, key: expected.key)) }
        catch { await reopened.close(); throw error }
        await reopened.close()
        XCTAssertEqual(value, KVGetResponse(found: true, valueBase64: expected.valueBase64))
        print("W09 signed storage retirement confirmed")
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
