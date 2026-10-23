import Foundation
import MixerUpdates
@testable import MixerCapabilityActivation

private final class ReviewCommitFault: @unchecked Sendable {
    private let lock = NSLock()
    private var selected: CapabilityDurabilityFaultPoint?
    func arm(_ point: CapabilityDurabilityFaultPoint) { lock.lock(); selected = point; lock.unlock() }
    func check(_ point: CapabilityDurabilityFaultPoint) throws {
        lock.lock(); let fail = selected == point; if fail { selected = nil }; lock.unlock()
        if fail { throw UpdateError("review.injected", "Original review durability fault") }
    }
}
private actor ReviewValidationGate {
    private var entered = false, released = false
    func hold() async { entered = true; while !released { await Task.yield() } }
    func waitForEntry() async throws {
        let cutoff = ContinuousClock.now.advanced(by: .seconds(10))
        while !entered && ContinuousClock.now < cutoff { await Task.yield() }
        try reviewRequire(entered, "validation gate was not entered")
    }
    func release() { released = true }
}

@main struct IndependentStoreProbe {
    static func main() async throws {
        let mode = CommandLine.arguments[1], templates = URL(fileURLWithPath: CommandLine.arguments[2])
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-independent-store-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        switch mode {
        case "uncertain-stage": try await uncertainStage(templates, parent)
        case "signed-highwater": try await signedHighwater(templates, parent)
        case "cancel-close": try await cancellationAndClose(templates, parent)
        case "host-mismatch": try await hostMismatch(templates, parent)
        default: throw UpdateError("review.mode", "Unknown review probe")
        }
        print("REVIEW_PASS \(mode)")
    }
    private static func open(_ fixture: ReviewStoreFixture, environment: CapabilityRecoveryEnvironment = .init(wall: { 100 })) async throws -> (CapabilityRecoveryStore, CapabilityAttemptReservation) {
        let owner = try CapabilityAttemptReservation.acquire()
        do {
            let store = try await CapabilityRecoveryStore.open(admission: owner.issueStoreAdmission(), installed: fixture.installed,
                configuration: fixture.configuration, environment: environment)
            return (store, owner)
        } catch { owner.beginClosing(); throw error }
    }
    private static func close(_ store: CapabilityRecoveryStore, _ owner: CapabilityAttemptReservation) async throws {
        owner.beginClosing(); await store.close()
        try reviewRequire(owner.isReleased, "actual descriptor close/operation join did not release slot")
    }
    private static func uncertainStage(_ templates: URL, _ parent: URL) async throws {
        for (index, point) in [CapabilityDurabilityFaultPoint.beforeStateRename, .afterStateRename].enumerated() {
            let fixture = try ReviewStoreFixture(templates: templates, root: parent.appendingPathComponent("state-\(index)"))
            let fault = ReviewCommitFault(), (manifest, assignment) = try fixture.offer(41)
            let (store, owner) = try await open(fixture, environment: .init(wall: { 100 }, fault: { try fault.check($0) }))
            try await store.beginDownload(signedManifest: manifest, signedAssignment: assignment)
            try await store.appendDownload(fixture.payload, atOffset: 0)
            fault.arm(point)
            var failed = false
            do { try await store.finishDownload() } catch let error as UpdateError { failed = error.code == "review.injected" }
            try reviewRequire(failed && store.snapshot.requiresReopen, "uncertain stage did not poison")
            var denied = false
            do { _ = try await store.downloadOffset() } catch { denied = true }
            try reviewRequire(denied, "poison remained usable")
            try await close(store, owner)
            let (again, next) = try await open(fixture)
            try reviewRequire(again.snapshot.acceptedSequence == 41, "reserved highwater rolled back")
            if point == .beforeStateRename {
                try reviewRequire(again.snapshot.staged == nil && again.snapshot.downloading != nil, "uncommitted stage advertised")
                let offset = try await again.downloadOffset()
                try reviewRequire(offset == UInt64(fixture.payload.count), "published orphan payload could not be rehashed/resumed")
                try await again.finishDownload()
            } else {
                try reviewRequire(again.snapshot.staged != nil && again.snapshot.downloading == nil, "actual renamed state was discarded")
            }
            let state = try StrictJSON.decode(CapabilityRecoveryState.self, from: Data(contentsOf: fixture.root.appendingPathComponent("state.json")))
            try reviewRequire(state.candidates.count == 1, "candidate count mismatch")
            let candidate = state.candidates.values.first!
            try reviewRequire(candidate.signedManifest == manifest && candidate.signedAssignment == assignment, "raw signed bytes changed")
            let bytes = try Data(contentsOf: fixture.root.appendingPathComponent(candidate.payloadSHA256 + ".payload"))
            try reviewRequire(bytes == fixture.payload, "published payload changed")
            try await close(again, next)
        }
    }
    private static func signedHighwater(_ templates: URL, _ parent: URL) async throws {
        let fixture = try ReviewStoreFixture(templates: templates, root: parent.appendingPathComponent("state"))
        let (store, owner) = try await open(fixture), (m, a) = try fixture.offer(73)
        try await store.beginDownload(signedManifest: m, signedAssignment: a)
        try await store.appendDownload(fixture.payload, atOffset: 0); try await store.finishDownload()
        let first = store.snapshot.staged
        let (nextM, nextA) = try fixture.offer(79)
        try await store.beginDownload(signedManifest: nextM, signedAssignment: nextA)
        try await store.cancelDownload()
        try reviewRequire(store.snapshot.acceptedSequence == 79 && store.snapshot.staged == first, "cancel widened or reset durable state")
        try await close(store, owner)
        let (again, next) = try await open(fixture)
        var replayDenied = false
        do { try await again.beginDownload(signedManifest: m, signedAssignment: a) } catch { replayDenied = true }
        try reviewRequire(replayDenied && again.snapshot.acceptedSequence == 79 && again.snapshot.staged == first, "old signed offer replayed after reopen")
        try await close(again, next)
    }
    private static func cancellationAndClose(_ templates: URL, _ parent: URL) async throws {
        let fixture = try ReviewStoreFixture(templates: templates, root: parent.appendingPathComponent("state")), gate = ReviewValidationGate()
        let (store, owner) = try await open(fixture, environment: .init(wall: { 100 }, afterValidation: { await gate.hold() }))
        let (manifest, assignment) = try fixture.offer(83)
        try await store.beginDownload(signedManifest: manifest, signedAssignment: assignment)
        try await store.appendDownload(fixture.payload, atOffset: 0)
        let finish = Task { try await store.finishDownload() }
        try await gate.waitForEntry()
        let others = try (0..<15).map { _ in try CapabilityAttemptReservation.acquire() }
        let cancel = Task { try? await store.cancelDownload() }
        owner.beginClosing(); await store.close(); await cancel.value
        try reviewRequire(!owner.isReleased && store.snapshot.closed, "close skipped held validator tail")
        var busy = false
        do { let unexpected = try CapabilityAttemptReservation.acquire(); unexpected.beginClosing() } catch { busy = true }
        try reviewRequire(busy, "17th complete attempt admitted while validator result was retained")
        await gate.release()
        var retiredFailure = false
        do { try await finish.value } catch { retiredFailure = true }
        try reviewRequire(retiredFailure && owner.isReleased && store.snapshot.staged == nil, "cancel/close published stale validated result")
        others.forEach { $0.beginClosing() }
    }
    private static func hostMismatch(_ templates: URL, _ parent: URL) async throws {
        let fixture = try ReviewStoreFixture(templates: templates, root: parent.appendingPathComponent("state"))
        let (store, owner) = try await open(fixture)
        try await close(store, owner)
        let path = fixture.root.appendingPathComponent("state.json")
        var object = try JSONSerialization.jsonObject(with: Data(contentsOf: path)) as! [String: Any]
        var host = object["host"] as! [String: Any]
        host["runtime"] = String(repeating: "0", count: 64); object["host"] = host
        let changed = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        try changed.write(to: path)
        var denied = false
        do { let (unexpected, reservation) = try await open(fixture); try await close(unexpected, reservation) } catch { denied = true }
        try reviewRequire(denied, "state host mismatch accepted with matching outer fingerprint")
        let remaining = try Data(contentsOf: path)
        try reviewRequire(remaining == changed, "bad old state silently reset")
    }
}
