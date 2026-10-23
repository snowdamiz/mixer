import Foundation
import XCTest
import MixerUpdates
@testable import MixerCapabilityActivation

private final class ReviewMainActorGate: @unchecked Sendable {
    private let lock = NSLock()
    private let semaphore = DispatchSemaphore(value: 0)
    private var enteredValue = false
    var entered: Bool { lock.lock(); defer { lock.unlock() }; return enteredValue }
    func hold() {
        lock.lock(); enteredValue = true; lock.unlock()
        _ = semaphore.wait(timeout: .now() + 5)
    }
    func release() { semaphore.signal() }
}

private final class ReviewCloseLatch: @unchecked Sendable {
    private let lock = NSLock()
    private var value = false
    func set() { lock.lock(); value = true; lock.unlock() }
    var completed: Bool { lock.lock(); defer { lock.unlock() }; return value }
}

final class CloseBindingProbe: XCTestCase, @unchecked Sendable {
    private func eventually(_ predicate: () async -> Bool) async throws {
        let deadline = ContinuousClock.now.advanced(by: .seconds(4))
        while !(await predicate()) {
            guard ContinuousClock.now < deadline else { throw UpdateError("review.timeout", "Expected race checkpoint not reached") }
            try await Task.sleep(for: .milliseconds(2))
        }
    }

    func testCloseWaitsForDelayedMainActorBindingAndConsumerReturn() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-ui-close-review-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: directory) }
        let fixture = try GuestUISignedFixture(root: directory)
        let runtime = try await CapabilityGuestUIRuntime.openOwned(configuration: fixture.configuration,
            installed: fixture.execution.installed, environment: .init(wall: { 1000 }))
        let bytes = GuestUISignedProgram.build(), documents = try fixture.documents(bytes)
        try await runtime.beginDownload(signedManifest: documents.0, signedAssignment: documents.1)
        try await runtime.appendDownload(bytes, atOffset: 0)
        try await runtime.finishDownload()

        let gate = ReviewMainActorGate(), closed = ReviewCloseLatch()
        let blocked = Task { @MainActor in gate.hold() }
        defer { gate.release() }
        try await eventually { gate.entered }
        let startup = Task.detached { try await runtime.start() }
        try await eventually { (await runtime.recoverySnapshot()).activation.candidateID != nil }
        let closing = Task.detached { await runtime.close(); closed.set() }
        try await eventually { (await runtime.recoverySnapshot()).activation.phase == .closed }
        try await Task.sleep(for: .milliseconds(30))
        XCTAssertFalse(closed.completed, "Close returned while MainActor bind was still stalled")
        gate.release()
        await blocked.value
        do { _ = try await startup.value; XCTFail("Closed startup succeeded") } catch {}
        await closing.value
        XCTAssertTrue(closed.completed)
        let state = await MainActor.run { runtime.presentation.state }
        XCTAssertEqual(state, .stopped)
        try await eventually { CapabilityAttemptReservation.occupiedSlots == baseline }
        print("REVIEW delayed-bind close joined actual consumer return; presentation stopped; reservation retired")
    }
}
