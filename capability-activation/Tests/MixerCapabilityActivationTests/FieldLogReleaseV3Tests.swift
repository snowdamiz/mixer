#if os(macOS) && canImport(MixerApple)
import AppKit
import ApplicationServices
import Foundation
import MixerUpdates
import SwiftUI
import XCTest
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

final class FieldLogReleaseV3Tests: XCTestCase {
    @MainActor
    func testLoopbackUpdateRollbackAndOfflineReopen() async throws {
        let environment = ProcessInfo.processInfo.environment
        guard let run = environment["MIXER_FIELDLOG_V3_RUN"] else {
            throw XCTSkip("Run capability-activation/verification/fieldlog-release-v3.py to supply exact local artifacts")
        }
        guard AXIsProcessTrusted() else {
            throw UpdateError("test.accessibility", "Local accessibility permission for the owned AppKit test is unavailable")
        }
        let directory = URL(fileURLWithPath: run, isDirectory: true)
        let repository = URL(fileURLWithPath: try XCTUnwrap(environment["MIXER_FIELDLOG_V3_REPOSITORY"]), isDirectory: true)
        let archive = try XCTUnwrap(environment["MIXER_FIELDLOG_V3_ARCHIVE_SHA256"])
        let port = try XCTUnwrap(environment["MIXER_FIELDLOG_V3_PORT"].flatMap(UInt16.init))
        let initialSlots = CapabilityAttemptReservation.occupiedSlots
        let fixture = try FieldLogReleaseV3Fixture(repository: repository, directory: directory, archiveSHA256: archive)
        let service = try FieldLogReleaseV3Loopback(executable: directory.appendingPathComponent("mixer-service"),
                                                   port: port, directory: directory, fixture: fixture)
        let application = NSApplication.shared
        application.setActivationPolicy(.regular)
        application.finishLaunching()
        application.activate()
        var rollbackID: String
        var reviewedID: String
        do {
            try await service.waitUntilReady()
            try await service.upload(fixture.baseline)
            try await service.upload(fixture.reviewed)
            try await service.publish(sequence: 1, operation: "publish")
            let baselineID = try await withOwner(fixture) { owner in
                let baseline = try await self.stage(owner, service, fixture.baseline, sequence: 1)
                try await self.play(owner, directory: directory, candidate: baseline, reviewed: false, label: "baseline")
                return baseline
            }
            try await service.publish(sequence: 2, operation: "publish")
            reviewedID = try await withOwner(fixture) { owner in
                let before = await owner.recoverySnapshot()
                XCTAssertEqual(before.healthy, baselineID)
                let reviewed = try await self.stage(owner, service, fixture.reviewed, sequence: 2)
                try await self.play(owner, directory: directory, candidate: reviewed, reviewed: true, label: "reviewed")
                let after = await owner.recoverySnapshot()
                XCTAssertEqual(after.previousHealthy, baselineID)
                return reviewed
            }
            try await service.publish(sequence: 3, operation: "rollback")
            rollbackID = try await withOwner(fixture) { owner in
                let before = await owner.recoverySnapshot()
                XCTAssertEqual(before.healthy, reviewedID)
                let rollback = try await self.stage(owner, service, fixture.baseline, sequence: 3)
                try await self.play(owner, directory: directory, candidate: rollback, reviewed: false, label: "rollback")
                let after = await owner.recoverySnapshot()
                XCTAssertEqual(after.previousHealthy, reviewedID)
                return rollback
            }
            try await service.publish(sequence: 4, operation: "publish")
            try await withOwner(fixture) { owner in
                let offer = try await service.fetch(fixture.reviewed, sequence: 4)
                try await owner.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment)
                let prefix = Data(offer.payload.prefix(128))
                try await owner.appendDownload(prefix, atOffset: 0)
                let offset = try await owner.downloadOffset()
                XCTAssertEqual(offset, UInt64(prefix.count))
                let pending = await owner.recoverySnapshot()
                XCTAssertEqual(pending.acceptedSequence, 4)
                XCTAssertNotNil(pending.downloading)
                print("FIELDLOG interrupted download accepted=\(pending.acceptedSequence) offset=\(offset)")
            }
        } catch {
            let workError = error
            do {
                try await service.stop()
            } catch {
                XCTFail("Service teardown after \(workError): \(error)")
            }
            throw workError
        }
        try await service.stop()

        // The service has exited. Reopen the same app private directory with the
        // same immutable installed material. No download or health injection.
        try await withOwner(fixture) { owner in
            let retained = await owner.recoverySnapshot()
            XCTAssertEqual(retained.healthy, rollbackID)
            XCTAssertEqual(retained.previousHealthy, reviewedID)
            XCTAssertEqual(retained.acceptedSequence, 4)
            XCTAssertNotNil(retained.downloading)
            let offset = try await owner.downloadOffset()
            XCTAssertEqual(offset, 128)
            try await self.play(owner, directory: directory, candidate: rollbackID, reviewed: false, label: "offline")
        }
        let state = try StrictJSON.decode(CapabilityRecoveryState.self,
            from: Data(contentsOf: fixture.configuration.directory.appendingPathComponent("state.json")))
        XCTAssertEqual(state.fingerprint, fixture.host.runtime)
        XCTAssertEqual(state.installation, fixture.configuration.installation)
        XCTAssertEqual(state.acceptedSequence, 4)
        XCTAssertEqual(state.pending?.sequence, 4)
        XCTAssertEqual(state.healthy?.candidateID, rollbackID)
        XCTAssertEqual(state.previousHealthy?.candidateID, reviewedID)
        XCTAssertEqual(state.healthy?.completedMilestones, ["feature_started", "first_screen"])
        XCTAssertNil(state.attempt)
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, initialSlots)
        print("FIELDLOG durable runtime=\(state.fingerprint) installation=\(state.installation) highWater=\(state.acceptedSequence) healthy=\(rollbackID) previous=\(reviewedID) pending=4 ownerSlots=\(initialSlots)")
    }

    @MainActor
    func testChildCustodyOnFailure() async throws {
        guard let run = ProcessInfo.processInfo.environment["MIXER_FIELDLOG_V3_RUN"] else {
            throw XCTSkip("Run the signed FieldLog replay to supply a fresh custody directory")
        }
        let directory = URL(fileURLWithPath: run, isDirectory: true).appendingPathComponent("custody-control")
        let failing = try FieldLogReleaseV3Child(URL(fileURLWithPath: "/usr/bin/false"), environment: [:],
                                                  directory: directory, name: "nonzero")
        do {
            try await failing.finish()
            XCTFail("A child exiting 1 must fail the invocation")
        } catch {
            XCTAssertTrue(String(describing: error).contains("custody closed"))
        }

        let denied = try FieldLogReleaseV3Child(URL(fileURLWithPath: "/usr/bin/true"), environment: [:],
                                                 directory: directory, name: "probe-denied")
        var groupAbsenceObserved = false
        do {
            try await denied.finish(observeGroup: { pgid in
                // Establish real custody before injecting an observation error.
                // The control must not leave a live or unobserved child behind.
                guard try FieldLogReleaseV3Child.groupAbsent(pgid) else { return false }
                groupAbsenceObserved = true
                throw UpdateError("test.custody_control", "injected group observation EPERM")
            })
            XCTFail("An observation error must retain a custody hold")
        } catch {
            XCTAssertTrue(String(describing: error).contains("injected group observation EPERM"))
        }
        XCTAssertTrue(groupAbsenceObserved)
        if groupAbsenceObserved { print("FIELDLOG custody control real group absence observed before injected EPERM") }
    }

    @MainActor
    private func withOwner<Result>(_ fixture: FieldLogReleaseV3Fixture,
                                   _ body: (CapabilityGuestUIRuntime) async throws -> Result) async throws -> Result {
        let owner = try await CapabilityGuestUIRuntime.open(configuration: fixture.configuration, execution: fixture.execution)
        let result: Swift.Result<Result, Error>
        do { result = .success(try await body(owner)) }
        catch { result = .failure(error) }
        await owner.close()
        try await eventually("Owned guest, store, and presentation retirement") { owner.ownerRetired }
        let snapshot = await owner.recoverySnapshot()
        XCTAssertTrue(snapshot.closed)
        XCTAssertFalse(snapshot.activation.cleanupPending)
        XCTAssertFalse(snapshot.incompleteAttempt)
        return try result.get()
    }

    @MainActor
    private func stage(_ owner: CapabilityGuestUIRuntime, _ service: FieldLogReleaseV3Loopback,
                       _ release: FieldLogReleaseV3Fixture.Release, sequence: Int) async throws -> String {
        let offer = try await service.fetch(release, sequence: sequence)
        try await owner.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment)
        try await owner.appendDownload(offer.payload, atOffset: 0)
        try await owner.finishDownload()
        let snapshot = await owner.recoverySnapshot()
        XCTAssertEqual(snapshot.acceptedSequence, UInt64(sequence))
        return try XCTUnwrap(snapshot.staged)
    }

    @MainActor
    private func play(_ owner: CapabilityGuestUIRuntime, directory: URL, candidate: String, reviewed: Bool, label: String) async throws {
        let view = NSHostingView(rootView: MixerGuestScreen(presentation: owner.presentation))
        let window = NSWindow(contentRect: NSRect(x: 40, y: 40, width: 450, height: 260),
                              styleMask: [.titled], backing: .buffered, defer: false)
        window.title = "FieldLog development proof"
        window.isReleasedWhenClosed = false
        window.contentView = view
        window.center()
        window.makeKeyAndOrderFront(nil)
        window.orderFrontRegardless()
        defer { window.contentView = nil; window.close() }
        let startup = try await owner.start()
        XCTAssertEqual(startup.phase, .provisionalGuest)
        XCTAssertEqual(startup.candidateID, candidate)
        try await inspectFrame(owner, window: window, revision: 1, status: "Open", button: "Complete task", label: label)
        print("FIELDLOG \(label) window=\(window.windowNumber) onscreen=\(window.isVisible) space=\(window.isOnActiveSpace) occlusion=\(window.occlusionState.rawValue) active=\(NSApp.isActive)")
        try await eventually("\(label) native layout/display health") {
            view.needsLayout = true
            view.layoutSubtreeIfNeeded()
            window.displayIfNeeded()
            let report = await owner.recoverySnapshot()
            return report.activation.phase == .healthyGuest && report.healthy == candidate
        }
        XCTAssertTrue(window.isVisible)
        XCTAssertTrue(window.occlusionState.contains(.visible))
        print("FIELDLOG \(label) healthy candidate=\(candidate) launch=\(startup.launchID ?? "missing")")
        try await press(owner, window: window, directory: directory, label: "Complete task", name: "ax-\(label)-complete")
        if reviewed {
            try await inspectFrame(owner, window: window, revision: 2, status: "Review required",
                                   button: "Confirm completion", label: label)
            try await press(owner, window: window, directory: directory, label: "Confirm completion", name: "ax-\(label)-confirm")
        }
        try await inspectFrame(owner, window: window, revision: reviewed ? 3 : 2, status: "Completed",
                               button: "Reopen task", label: label)
        let counters = try XCTUnwrap(owner.presentation.lifecycleObservation?.counters)
        XCTAssertEqual(counters.acceptedEvents, reviewed ? 2 : 1)
        XCTAssertEqual(counters.deliveredEvents, reviewed ? 2 : 1)
    }

    @MainActor
    private func inspectFrame(_ owner: CapabilityGuestUIRuntime, window: NSWindow, revision: UInt64,
                              status: String, button: String, label: String) async throws {
        try await eventually("\(label) frame \(revision)") {
            window.contentView?.layoutSubtreeIfNeeded()
            return owner.presentation.state == .displaying(revision: revision)
        }
        let children = try XCTUnwrap(owner.presentation.renderHost?.snapshot.document.root.children)
        let actualStatus = try XCTUnwrap(children.first(where: { $0.id == "status" })?.properties["text"]?.string)
        let actualButton = try XCTUnwrap(children.first(where: { $0.id == "toggle" })?.properties["label"]?.string)
        XCTAssertEqual(actualStatus, status)
        XCTAssertEqual(actualButton, button)
        if revision > 1 {
            XCTAssertEqual(owner.presentation.lastEventResult?.sequence, revision - 1)
            XCTAssertEqual(owner.presentation.lastEventResult?.outcome, .delivered)
        }
        print("FIELDLOG \(label) frame=\(revision) status=\(actualStatus) button=\(actualButton)")
    }

    @MainActor
    private func press(_ owner: CapabilityGuestUIRuntime, window: NSWindow, directory: URL,
                       label: String, name: String) async throws {
        try await eventually("Native \(label) button ready") { owner.presentation.inputEnabled }
        // An external AX client makes AppKit deliver the native action on the
        // application's main thread. An in-process AX call can run inline.
        let client = try FieldLogReleaseV3Child(directory.appendingPathComponent("fieldlog-press"),
                                                 arguments: [String(getpid()), window.title, label],
                                                 environment: ProcessInfo.processInfo.environment,
                                                 directory: directory.appendingPathComponent("custody"), name: name)
        try await client.finish(pump: pumpApplicationEvents)
    }

    @MainActor
    private func pumpApplicationEvents() {
        // Drain only this test application's AppKit events.
        for _ in 0..<32 {
            guard let event = NSApp.nextEvent(matching: .any, until: .distantPast, inMode: .default, dequeue: true) else { break }
            NSApp.sendEvent(event)
        }
        NSApp.updateWindows()
    }

    @MainActor
    private func eventually(_ observation: String, _ test: () async -> Bool) async throws {
        let deadline = ContinuousClock.now + .seconds(6)
        while !(await test()) {
            pumpApplicationEvents()
            guard ContinuousClock.now < deadline else { throw UpdateError("test.timeout", observation) }
            try await Task.sleep(for: .milliseconds(10))
        }
    }
}
#endif
