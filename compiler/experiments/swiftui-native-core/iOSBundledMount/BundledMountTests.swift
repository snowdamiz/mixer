import SwiftUI
import XCTest
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
