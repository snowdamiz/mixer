#if os(macOS) && canImport(SwiftUI) && canImport(MixerApple)
import Foundation
import MixerApple
import MixerUI
import MixerUpdates
import XCTest
@_spi(InstalledApplicationStorage) import MixerCapabilities
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

/// Host-only exercise of the B' ownership seam with a signed ABI-2 fixture.
final class S4FeatureOwnershipTests: XCTestCase, @unchecked Sendable {
    @MainActor
    func testSignedFallbackSaveFirstFrameFailuresRollbackAndOfflineReopen() async throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("mixer-s4-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        let baselinePayload = GuestUISignedProgram.build()
        let reviewPayload = GuestUISignedProgram.build(.localizedChecklist)
        let ownership = S4RuntimeOwnership()
        var retiredInput: (@MainActor () -> Void)?

        do {
            let fixture = try GuestUISignedFixture(root: root)
            try await ownership.run(fixture) { runtime in
                let launch = try await runtime.start()
                XCTAssertEqual(launch.phase, .nativeFallback)
                XCTAssertFalse(launch.effectsMayHaveOpened)
                XCTAssertNil(runtime.presentation.renderHost)
                let bundled = try MixerUIHost(document: bundledDocument())
                let envelope = try saveEnvelope(in: bundled)
                XCTAssertEqual(try bundled.route(envelope).actionID, "sample.save")
                print("S4 cold fallback routed through MixerUIHost")
            }

            let baseline = try await ownership.run(fixture) { runtime in
                let candidate = try await stage(baselinePayload, sequence: 1, fixture, runtime)
                let launch = try await runtime.start()
                XCTAssertEqual(launch.candidateID, candidate)
                try await waitForFrame(1, runtime)
                let model = runtime.presentation
                let host = try XCTUnwrap(model.renderHost)
                try assertParity(host, bundledDocument())
                let attachment = try XCTUnwrap(model.claimNativeAttachment())
                defer { model.detachNativeAttachment(attachment) }
                let provisional = await runtime.recoverySnapshot()
                XCTAssertEqual(provisional.activation.phase, .provisionalGuest)
                XCTAssertNil(provisional.healthy)
                try acknowledgeForHostTest(model, attachment)
                try await waitForHealth(candidate, runtime)

                let envelope = try saveEnvelope(in: host)
                let routed = try host.route(envelope)
                let submit = model.actionHandler(host: host, attachment: attachment)
                retiredInput = { submit(routed) }
                XCTAssertTrue(model.inputEnabled)
                submit(routed)
                try await waitForFrame(3, runtime)
                try assertParity(host, bundledDocument(revision: 3, status: "Saved sample"))
                XCTAssertThrowsError(try host.route(envelope)) { error in
                    XCTAssertEqual(error as? UIRoutingError, .staleRevision)
                }
                print("S4 signed baseline reached revision 3 and refused the old render envelope")
                return candidate
            }
            try await assertSavedBytes(root)

            try await ownership.run(fixture) { runtime in
                let invalid = try await stage(GuestUISignedProgram.build(.invalidHeader),
                                              sequence: 2, fixture, runtime)
                let launch = try await runtime.start()
                XCTAssertNotEqual(launch.candidateID, invalid)
                XCTAssertEqual(launch.candidateID, baseline)
                try await waitForFrame(1, runtime)
                try assertParity(try XCTUnwrap(runtime.presentation.renderHost), bundledDocument())
                let disk = try recoveryState(fixture)
                XCTAssertEqual(disk.lastRecovery, "ui_protocol_before_effects")
                XCTAssertEqual(disk.healthy?.candidateID, baseline)
                XCTAssertNil(disk.staged)
                print("S4 rejected signed first-frame header before effects and selected retained baseline")
            }
            try await assertSavedBytes(root)

            try await ownership.run(fixture) { runtime in
                let candidate = try await stage(reviewPayload, sequence: 3, fixture, runtime)
                let launch = try await runtime.start()
                XCTAssertEqual(launch.candidateID, candidate)
                try await waitForFrame(1, runtime)
                let model = runtime.presentation
                let attachment = try XCTUnwrap(model.claimNativeAttachment())
                defer { model.detachNativeAttachment(attachment) }
                print("S4 before native display acknowledgement inputEnabled=\(model.inputEnabled)")
                XCTAssertNil(model.claimNativeAttachment())
                try await s4Eventually("post-intent first-frame failure settled") {
                    let result = await runtime.recoverySnapshot()
                    return result.activation.phase == .recoveryRequired && !result.incompleteAttempt
                }
                let stopped = await runtime.recoverySnapshot()
                XCTAssertEqual(stopped.healthy, baseline)
                XCTAssertTrue(stopped.requiresReopen)
                XCTAssertTrue(stopped.activation.effectsMayHaveOpened)
                XCTAssertEqual(stopped.activation.firstUIProtocolFailure?.effectStage, .intentEntered)
                XCTAssertEqual(stopped.activation.firstUIProtocolFailure?.failure,
                               .init(phase: .presentation, code: .presentationInvariant))
                XCTAssertFalse(model.inputEnabled)
                XCTAssertEqual(try recoveryState(fixture).lastRecovery, "ui_protocol_after_effects")
                print("S4 duplicate pre-display attachment required cold reopen after effects intent")
            }
            try await assertSavedBytes(root)

            let reviewed = try await ownership.run(fixture) { runtime in
                let candidate = try await stage(reviewPayload, sequence: 4, fixture, runtime)
                try await renderAndObserve(candidate, runtime, expected: reviewedDocument)
                return candidate
            }
            XCTAssertNotEqual(reviewed, baseline)

            let rollback = try await ownership.run(fixture) { runtime in
                let candidate = try await stage(baselinePayload, sequence: 5, fixture, runtime)
                try await renderAndObserve(candidate, runtime, expected: bundledDocument())
                let state = await runtime.recoverySnapshot()
                XCTAssertEqual(state.previousHealthy, reviewed)
                XCTAssertEqual(state.acceptedSequence, 5)
                return (candidate: candidate, launch: try XCTUnwrap(state.activation.launchID))
            }
            XCTAssertNotEqual(rollback.candidate, baseline)

            try await ownership.run(fixture) { runtime in
                try await renderAndObserve(rollback.candidate, runtime, expected: bundledDocument())
                let model = runtime.presentation
                let attachment = try XCTUnwrap(model.claimNativeAttachment())
                defer { model.detachNativeAttachment(attachment) }
                XCTAssertTrue(model.inputEnabled)
                let host = try XCTUnwrap(model.renderHost)
                XCTAssertEqual(try host.route(saveEnvelope(in: host)).actionID, "sample.save")
                let before = try XCTUnwrap(model.lifecycleObservation?.counters.acceptedEvents)
                try XCTUnwrap(retiredInput)()
                let after = try XCTUnwrap(model.lifecycleObservation?.counters.acceptedEvents)
                XCTAssertEqual(before, 0)
                XCTAssertEqual(after, before)
                XCTAssertEqual(model.state, .displaying(revision: 1))
                let state = await runtime.recoverySnapshot()
                XCTAssertEqual(state.healthy, rollback.candidate)
                XCTAssertEqual(state.acceptedSequence, 5)
                XCTAssertNotEqual(try XCTUnwrap(state.activation.launchID), rollback.launch)
                print("S4 offline reopen retained sequence 5 and refused the retired revision-1 callback")
            }
            try await assertSavedBytes(root)
        } catch {
            if ownership.settled { try FileManager.default.removeItem(at: root) }
            else { print("S4 HOLD unconfirmed runtime retirement at \(root.path)") }
            throw error
        }
        try FileManager.default.removeItem(at: root)
        print("S4 seven public owners retired and owned fixture removed")
    }

    // Independent typed construction is the bundled side of the comparison.
    private func bundledDocument(revision: UInt64 = 1, status: String = "Ready") -> UIDocument {
        UIDocument(revision: revision, root: UINode(id: "root", kind: .vStack, children: [
            UINode(id: "status", kind: .text, properties: ["text": .string(status)]),
            UINode(id: "save", kind: .button, properties: ["label": .string("Save sample")],
                   actions: [UIActionBinding(id: "sample.save", event: .activate)])
        ]))
    }

    private var reviewedDocument: UIDocument {
        UIDocument(revision: 1, root: UINode(id: "fieldlog-task", kind: .vStack, children: [
            UINode(id: "task", kind: .text, properties: ["text": .string("فحص المضخة 07")]),
            UINode(id: "status", kind: .text, properties: ["text": .string("الفحص قيد التنفيذ")]),
            UINode(id: "toggle", kind: .button, properties: ["label": .string("وضع علامة مكتملة")],
                   actions: [UIActionBinding(id: "task.toggle", event: .activate)])
        ]))
    }

    @MainActor
    private func assertParity(_ guest: MixerUIHost, _ document: UIDocument) throws {
        let bundled = try MixerUIHost(document: document)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        XCTAssertEqual(try encoder.encode(guest.snapshot.document), try encoder.encode(bundled.snapshot.document))
    }

    @MainActor
    private func saveEnvelope(in host: MixerUIHost) throws -> UIEventEnvelope {
        UIEventEnvelope(revision: host.snapshot.document.revision,
                        identity: try XCTUnwrap(host.snapshot.identity(for: "save")), event: .activate)
    }

    private func stage(_ payload: Data, sequence: UInt64, _ fixture: GuestUISignedFixture,
                       _ runtime: CapabilityGuestUIRuntime) async throws -> String {
        let (manifest, assignment) = try fixture.documents(payload, sequence: sequence, storage: true)
        try await runtime.beginDownload(signedManifest: manifest, signedAssignment: assignment)
        try await runtime.appendDownload(payload, atOffset: 0)
        try await runtime.finishDownload()
        let state = await runtime.recoverySnapshot()
        XCTAssertEqual(state.acceptedSequence, sequence)
        return try XCTUnwrap(state.staged)
    }

    @MainActor
    private func waitForFrame(_ revision: UInt64, _ runtime: CapabilityGuestUIRuntime) async throws {
        try await s4Eventually("frame \(revision)") {
            runtime.presentation.state == .displaying(revision: revision)
        }
    }

    @MainActor
    private func acknowledgeForHostTest(_ model: GuestUIPresentation,
                                        _ attachment: CapabilityGuestUIAttachmentIdentity) throws {
        // Substitute only the platform display callback. Ticket/owner validation
        // and the durable health decision still run through the production path.
        let ticket = try XCTUnwrap(model.nativeDisplayTicket(attachment: attachment))
        XCTAssertTrue(model.observeNativeDisplay(ticket))
    }

    @MainActor
    private func waitForHealth(_ candidate: String, _ runtime: CapabilityGuestUIRuntime) async throws {
        try await s4Eventually("health for \(candidate)") {
            let result = await runtime.recoverySnapshot()
            return result.activation.phase == .healthyGuest && result.healthy == candidate
        }
    }

    @MainActor
    private func renderAndObserve(_ candidate: String, _ runtime: CapabilityGuestUIRuntime,
                                  expected: UIDocument) async throws {
        let launch = try await runtime.start()
        XCTAssertEqual(launch.candidateID, candidate)
        try await waitForFrame(expected.revision, runtime)
        let model = runtime.presentation
        try assertParity(try XCTUnwrap(model.renderHost), expected)
        let attachment = try XCTUnwrap(model.claimNativeAttachment())
        defer { model.detachNativeAttachment(attachment) }
        try acknowledgeForHostTest(model, attachment)
        try await waitForHealth(candidate, runtime)
    }

    private func recoveryState(_ fixture: GuestUISignedFixture) throws -> CapabilityRecoveryState {
        try StrictJSON.decode(CapabilityRecoveryState.self,
                              from: Data(contentsOf: fixture.configuration.directory.appendingPathComponent("state.json")))
    }

    private func assertSavedBytes(_ root: URL) async throws {
        let reader = try AppPrivateKeyValueStore(directory: root.appendingPathComponent("material_test"),
                                                namespaces: ["material_test"])
        let result: KVGetResponse
        do {
            result = try await reader.get(.init(namespace: "material_test", key: "binary"))
        } catch {
            await reader.close()
            throw error
        }
        await reader.close()
        XCTAssertEqual(result, KVGetResponse(found: true, valueBase64: "AAH+/w=="))
    }
}

@MainActor
private final class S4RuntimeOwnership {
    private(set) var settled = true

    func run<T>(_ fixture: GuestUISignedFixture,
                _ body: (CapabilityGuestUIRuntime) async throws -> T) async throws -> T {
        settled = false
        let runtime = try await CapabilityGuestUIRuntime.open(configuration: fixture.configuration,
                                                              execution: fixture.execution)
        let result: Result<T, any Error>
        do { result = .success(try await body(runtime)) }
        catch { result = .failure(error) }

        var closeReturned = false
        let close = Task { await runtime.close(); closeReturned = true }
        try await s4Eventually("public owner retirement") { closeReturned && runtime.ownerRetired }
        await close.value
        let state = await runtime.recoverySnapshot()
        guard state.closed, !state.activation.cleanupPending else {
            throw S4Timeout(boundary: "public owner cleanup")
        }
        settled = true
        return try result.get()
    }
}

private struct S4Timeout: Error {
    let boundary: String
}

@MainActor
private func s4Eventually(_ boundary: String, _ predicate: () async throws -> Bool) async throws {
    let deadline = ContinuousClock.now + .seconds(8)
    while try await !predicate() {
        guard ContinuousClock.now < deadline else { throw S4Timeout(boundary: boundary) }
        try await Task.sleep(for: .milliseconds(5))
    }
}
#endif
