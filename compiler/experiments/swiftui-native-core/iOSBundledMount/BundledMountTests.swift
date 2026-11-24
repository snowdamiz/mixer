import Combine
import SwiftUI
import XCTest
import MixerSwiftUI
import MixerUI
import UP5StarterFeature
@testable import MixerApple

final class BundledMountTests: XCTestCase {
    // Drive receipt delivery explicitly so ordering stays deterministic. The UI
    // test independently exercises MixerNativeView's window/display callback.
    @MainActor
    func testAdmissionRejectsPendingStaleAndForeignInput() async throws {
        let mount = try MixerBundledFeatureMount { StarterFeature() }
        defer { mount.cancel() }
        let start = Task { await mount.start() }
        let initialID = try await waitForDisplay(on: mount.host)
        let initialAction = try increment(on: mount.host)
        XCTAssertThrowsError(try mount.receive(initialAction))
        mount.host.completeFeatureDisplay(UUID())
        XCTAssertEqual(mount.host.featureDisplayID, initialID)
        XCTAssertEqual(mount.status, .starting)
        mount.host.completeFeatureDisplay(initialID)
        await start.value
        XCTAssertEqual(mount.status, .ready)
        XCTAssertEqual(label(for: "Count: 0", on: mount.host), "Count: 0")

        let foreignHost = try MixerUIHost(document: mount.host.snapshot.document)
        XCTAssertThrowsError(try mount.receive(increment(on: foreignHost)))
        try mount.receive(initialAction)
        XCTAssertThrowsError(try mount.receive(initialAction))

        let update = try XCTUnwrap(mount.presentation)
        let updateID = try await waitForDisplay(on: mount.host)
        XCTAssertNotEqual(initialID, updateID)
        let updateAction = try increment(on: mount.host)
        XCTAssertThrowsError(try mount.receive(updateAction))
        mount.host.completeFeatureDisplay(initialID)
        XCTAssertEqual(mount.host.featureDisplayID, updateID)
        mount.host.completeFeatureDisplay(updateID)
        await update.value
        XCTAssertEqual(label(for: "Count: 1", on: mount.host), "Count: 1")
        XCTAssertThrowsError(try mount.receive(initialAction))

        // The current action must succeed after the update settles. Cancel that
        // candidate with its receipt still pending, then try to deliver it late.
        try mount.receive(updateAction)
        let canceled = try XCTUnwrap(mount.presentation)
        let canceledID = try await waitForDisplay(on: mount.host)
        let canceledAction = try increment(on: mount.host)
        mount.cancel()
        mount.host.completeFeatureDisplay(canceledID)
        XCTAssertEqual(mount.status, .closed)
        XCTAssertThrowsError(try mount.receive(canceledAction))
        await canceled.value
        XCTAssertNil(mount.host.featureDisplayID)
        XCTAssertEqual(mount.status, .closed)
    }

    @MainActor
    func testIssuedActionCannotReplayAfterInvalidState() async throws {
        var executions = 0
        let mount = try MixerBundledFeatureMount { InvalidStateFeature { executions += 1 } }
        defer { mount.cancel() }
        try await activate(mount)

        let issued = try increment(on: mount.host)
        XCTAssertThrowsError(try mount.receive(issued)) { error in
            XCTAssertEqual(error as? FeatureError, .limitExceeded("state value bytes"))
        }
        XCTAssertEqual(executions, 1)
        XCTAssertNil(mount.presentation)

        XCTAssertThrowsError(try mount.receive(issued)) { error in
            XCTAssertEqual(error as? UIRoutingError, .staleRevision)
        }
        XCTAssertEqual(executions, 1)

        XCTAssertThrowsError(try mount.receive(increment(on: mount.host))) { error in
            XCTAssertEqual(error as? FeatureError, .limitExceeded("state value bytes"))
        }
        XCTAssertEqual(executions, 2)
        XCTAssertNil(mount.presentation)
    }

    @MainActor
    func testBusySessionLeavesAnUnadmittedActionAvailableForRetry() async throws {
        var executions = 0
        var reenter: (() -> Void)?
        let mount = try MixerBundledFeatureMount {
            InvalidStateFeature {
                executions += 1
                reenter?()
            }
        }
        defer { mount.cancel() }
        try await activate(mount)

        let first = try increment(on: mount.host)
        let second = try increment(on: mount.host)
        reenter = {
            XCTAssertThrowsError(try mount.receive(second)) { error in
                XCTAssertEqual(error as? UIRoutingError, .unboundEvent)
            }
        }
        XCTAssertThrowsError(try mount.receive(first)) { error in
            XCTAssertEqual(error as? FeatureError, .limitExceeded("state value bytes"))
        }
        reenter = nil
        XCTAssertEqual(executions, 1)
        XCTAssertNil(mount.presentation)

        XCTAssertThrowsError(try mount.receive(second)) { error in
            XCTAssertEqual(error as? FeatureError, .limitExceeded("state value bytes"))
        }
        XCTAssertEqual(executions, 2)
        XCTAssertThrowsError(try mount.receive(second)) { error in
            XCTAssertEqual(error as? UIRoutingError, .staleRevision)
        }
        XCTAssertEqual(executions, 2)
    }

    @MainActor
    func testCancellationUnblocksMountWithoutDisplayCompletion() async throws {
        let mount = try MixerBundledFeatureMount { StarterFeature() }
        defer { mount.cancel() }
        let start = Task { await mount.start() }
        let pendingID = try await waitForDisplay(on: mount.host)
        let action = try increment(on: mount.host)

        start.cancel()
        try await eventually { mount.status == .closed && mount.host.featureDisplayID == nil }
        await start.value
        mount.host.completeFeatureDisplay(pendingID)
        XCTAssertEqual(mount.status, .closed)
        XCTAssertThrowsError(try mount.receive(action))
    }

    @MainActor
    func testForeignReceiptAndSnapshotMismatch() async throws {
        let mount = try MixerBundledFeatureMount { StarterFeature() }
        defer { mount.cancel() }
        let source = Task { await mount.start() }
        let initialID = try await waitForDisplay(on: mount.host)
        let document = mount.host.snapshot.document
        mount.cancel()
        mount.host.completeFeatureDisplay(initialID)
        await source.value
        XCTAssertEqual(mount.status, .closed)

        let validator = UIValidator()
        let prepared = try validator.validate(document)
        let exact = BundledFeatureDisplay(document: prepared)
        let foreign = BundledFeatureDisplay(document: prepared)
        let host = try MixerUIHost(document: UIDocument(revision: 0, root: UINode(id: "test", kind: .vStack)))
        let display = Task { try await host.presentFeature(exact.request) }
        defer { display.cancel() }
        let exactID = try await waitForDisplay(on: host)
        host.completeFeatureDisplay(exactID)
        let receipt = try await display.value
        XCTAssertTrue(exact.accepts(receipt))
        XCTAssertFalse(foreign.accepts(receipt))

        let mismatch = try validator.validate(UIDocument(revision: 2, root: document.root))
        let next = BundledFeatureDisplay(document: mismatch)
        let overwritten = Task { try await host.presentFeature(next.request) }
        defer { overwritten.cancel() }
        let nextID = try await waitForDisplay(on: host)
        try host.update(UIDocument(revision: 3, root: document.root))
        host.completeFeatureDisplay(nextID)
        let wrongSnapshot = try await overwritten.value
        XCTAssertFalse(next.accepts(wrongSnapshot))
    }

    @MainActor
    func testExactReceiptBeforeForeignUpdateCannotPromote() async throws {
        let mount = try MixerBundledFeatureMount { StarterFeature() }
        defer { mount.cancel() }
        let start = Task { await mount.start() }
        let displayID = try await waitForDisplay(on: mount.host)
        let callback = try increment(on: mount.host)
        mount.host.completeFeatureDisplay(displayID)
        // The mount cannot resume until this main actor turn yields.
        try replaceHostDocument(on: mount.host)
        await start.value

        XCTAssertEqual(mount.status, .failed)
        XCTAssertThrowsError(try mount.receive(callback))
        XCTAssertNil(mount.presentation)
    }

    @MainActor
    func testForeignUpdateAfterPromotionRevokesOldCallback() async throws {
        let mount = try MixerBundledFeatureMount { StarterFeature() }
        defer { mount.cancel() }
        try await activate(mount)
        let callback = try increment(on: mount.host)
        let observation = mount.host.$snapshot.dropFirst().sink { _ in
            // The router has advanced before the published snapshot stores.
            do {
                try mount.receive(callback)
                XCTFail("Accepted a callback while the host was publishing a replacement")
            } catch {
                XCTAssertEqual(error as? UIRoutingError, .staleRevision)
            }
        }
        defer { observation.cancel() }

        try replaceHostDocument(on: mount.host)
        XCTAssertThrowsError(try mount.receive(callback)) { error in
            XCTAssertEqual(error as? UIRoutingError, .staleRevision)
        }
        XCTAssertThrowsError(try mount.receive(increment(on: mount.host)))
        XCTAssertNil(mount.presentation)
    }

    @MainActor
    func testCancelFromReadyObserverStaysTerminal() async throws {
        let mount = try MixerBundledFeatureMount { StarterFeature() }
        var observed: [MixerBundledFeatureMount<StarterFeature>.Status] = []
        let observation = mount.$status.sink { next in
            observed.append(next)
            if next == .ready || next == .closed { mount.cancel() }
        }
        defer { observation.cancel() }

        let start = Task { await mount.start() }
        let displayID = try await waitForDisplay(on: mount.host)
        let callback = try increment(on: mount.host)
        mount.host.completeFeatureDisplay(displayID)
        await start.value

        XCTAssertEqual(mount.status, .closed)
        XCTAssertEqual(observed, [.starting, .ready, .closed])
        XCTAssertThrowsError(try mount.receive(callback))
        await mount.start()
        XCTAssertNil(mount.presentation)
        XCTAssertNil(mount.host.featureDisplayID)
    }

    @MainActor
    func testHeldTextBindingContinuesAcrossItsOwnReceipts() async throws {
        let mount = try MixerBundledFeatureMount { StarterFeature() }
        defer { mount.cancel() }
        try await activate(mount)
        let originalButton = try increment(on: mount.host)
        let held = try textBinding(on: mount)
        let unrelatedOldBinding = try textBinding(on: mount)

        held.wrappedValue = "A"
        let a = try await waitForDisplay(on: mount.host)
        let resumedBinding = try textBinding(on: mount)
        unrelatedOldBinding.wrappedValue = "foreign"
        XCTAssertEqual(unrelatedOldBinding.wrappedValue, "")
        held.wrappedValue = "AB"
        XCTAssertEqual(held.wrappedValue, "AB")
        XCTAssertEqual(resumedBinding.wrappedValue, "AB")
        XCTAssertEqual(label(for: "Draft: A", on: mount.host), "Draft: A")
        XCTAssertThrowsError(try mount.receive(originalButton))
        try await complete(a, on: mount)

        let ab = try await waitForDisplay(on: mount.host)
        XCTAssertEqual(label(for: "Draft: AB", on: mount.host), "Draft: AB")
        try await complete(ab, on: mount)
        XCTAssertEqual(held.wrappedValue, "AB")
        held.wrappedValue = "ABC"
        let abc = try await waitForDisplay(on: mount.host)
        XCTAssertEqual(label(for: "Draft: ABC", on: mount.host), "Draft: ABC")
        try await complete(abc, on: mount)
        XCTAssertEqual(resumedBinding.wrappedValue, "ABC")
        XCTAssertThrowsError(try mount.receive(originalButton))

        try mount.receive(increment(on: mount.host))
        let incremented = try await waitForDisplay(on: mount.host)
        try await complete(incremented, on: mount)
        held.wrappedValue = "late"
        XCTAssertEqual(held.wrappedValue, "ABC")
        XCTAssertNil(mount.presentation)
        XCTAssertEqual(label(for: "Draft: ABC", on: mount.host), "Draft: ABC")
    }

    @MainActor
    func testQueuedTextIsDroppedWhenHostIsReplaced() async throws {
        let mount = try MixerBundledFeatureMount { StarterFeature() }
        defer { mount.cancel() }
        try await activate(mount)
        let held = try textBinding(on: mount)
        held.wrappedValue = "A"
        let displayID = try await waitForDisplay(on: mount.host)
        held.wrappedValue = "AB"
        let task = try XCTUnwrap(mount.presentation)
        mount.host.completeFeatureDisplay(displayID)
        try replaceHostDocument(on: mount.host)
        await task.value

        XCTAssertEqual(mount.status, .failed)
        XCTAssertEqual(held.wrappedValue, "")
        held.wrappedValue = "ABC"
        XCTAssertEqual(held.wrappedValue, "")
        XCTAssertNil(mount.presentation)
    }

    @MainActor
    private func activate<Content>(_ mount: MixerBundledFeatureMount<Content>) async throws {
        let start = Task { await mount.start() }
        let id = try await waitForDisplay(on: mount.host)
        mount.host.completeFeatureDisplay(id)
        await start.value
        XCTAssertEqual(mount.status, .ready)
    }

    @MainActor
    private func complete(_ id: UUID, on mount: MixerBundledFeatureMount<StarterFeature>) async throws {
        let task = try XCTUnwrap(mount.presentation)
        mount.host.completeFeatureDisplay(id)
        await task.value
    }

    @MainActor
    private func replaceHostDocument(on host: MixerUIHost) throws {
        let document = host.snapshot.document
        try host.update(UIDocument(revision: document.revision + 1, root: document.root))
    }

    @MainActor
    private func textBinding(on mount: MixerBundledFeatureMount<StarterFeature>) throws -> SwiftUI.Binding<String> {
        let snapshot = mount.host.snapshot
        let node = try XCTUnwrap(snapshot.document.root.children.first { $0.kind == .textField })
        return try XCTUnwrap(mount.textBinding(node: node, snapshot: snapshot))
    }

    @MainActor
    private func increment(on host: MixerUIHost) throws -> IssuedUIAction {
        let snapshot = host.snapshot
        let node = try XCTUnwrap(snapshot.document.root.children.first { $0.kind == .button })
        let identity = try XCTUnwrap(snapshot.identity(for: node.id))
        return try host.routeIssued(UIEventEnvelope(revision: snapshot.document.revision, identity: identity,
                                                   event: .activate))
    }

    @MainActor
    private func label(for value: String, on host: MixerUIHost) -> String? {
        host.snapshot.document.root.children
            .first { $0.properties["text"]?.string == value }?.properties["text"]?.string
    }

    @MainActor
    private func waitForDisplay(on host: MixerUIHost) async throws -> UUID {
        try await eventually { host.featureDisplayID != nil }
        return try XCTUnwrap(host.featureDisplayID)
    }

    @MainActor
    private func eventually(_ condition: () throws -> Bool) async throws {
        for _ in 0..<200 {
            if try condition() { return }
            try await Task.sleep(for: .milliseconds(5))
        }
        throw FixtureTimeout.condition
    }

    private enum FixtureTimeout: Error { case condition }
}

private struct InvalidStateFeature: MixerSwiftUI.View {
    @MixerSwiftUI.State private var draft = ""
    let onTap: () -> Void

    var body: some MixerSwiftUI.View {
        MixerSwiftUI.VStack {
            MixerSwiftUI.Button("Write draft") {
                onTap()
                draft = String(repeating: "x", count: 1_025)
            }
            MixerSwiftUI.Text(draft)
        }
    }
}
