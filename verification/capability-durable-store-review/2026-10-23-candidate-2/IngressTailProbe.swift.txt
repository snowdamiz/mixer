import Foundation
import Darwin
@testable import MixerCapabilityActivation

actor ReviewIngressGate {
    static let shared = ReviewIngressGate()
    private var entered = false, released = false
    func hold() async {
        entered = true
        while !released { await Task.yield() }
    }
    func waitForEntry() async throws {
        let deadline = ContinuousClock.now.advanced(by: .seconds(10))
        while !entered && ContinuousClock.now < deadline { await Task.yield() }
        try reviewRequire(entered, "did not enter derived ingress-tail gate")
    }
    func release() { released = true }
}

@main struct IndependentIngressTailProbe {
    static func main() async throws {
        let templates = URL(fileURLWithPath: CommandLine.arguments[1])
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-review-ingress-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: parent) }
        let fixture = try ReviewStoreFixture(templates: templates, root: parent.appendingPathComponent("state"))
        let owner = try CapabilityAttemptReservation.acquire()
        let store = try await CapabilityRecoveryStore.open(admission: owner.issueStoreAdmission(), installed: fixture.installed,
            configuration: fixture.configuration, environment: .init(wall: { 100 }))
        let (m,a) = try fixture.offer(19)
        try await store.beginDownload(signedManifest: m, signedAssignment: a)
        let append = Task { try await store.appendDownload(fixture.payload, atOffset: 0) }
        try await ReviewIngressGate.shared.waitForEntry()
        let others = try (0..<15).map { _ in try CapabilityAttemptReservation.acquire() }
        owner.beginClosing(); await store.close()
        let releasedBeforeTail = owner.isReleased, busyBeforeTail = store.snapshot.busy
        let countBeforeTail = CapabilityAttemptReservation.occupiedSlots
        let extra = try? CapabilityAttemptReservation.acquire()
        print("held_owned_append_frame occupied=\(countBeforeTail) released=\(releasedBeforeTail) ordinary_busy=\(busyBeforeTail) extra_admitted=\(extra != nil)")
        await ReviewIngressGate.shared.release()
        do { try await append.value } catch is CancellationError {}
        others.forEach { $0.beginClosing() }; extra?.beginClosing()
        guard !releasedBeforeTail, countBeforeTail == 16, extra == nil, busyBeforeTail else {
            print("FAIL outer slot retired before owned ingress frame returned")
            exit(1)
        }
        try reviewRequire(owner.isReleased, "joined frame did not retire after tail")
        print("owned ingress tail participates in actual-close retirement")
    }
}
