import Dispatch
import Foundation
import MixerCapabilities
import MixerUI
@_spi(GuestUIV1) import MixerGuest
@_spi(GuestUIV1) @_spi(CapabilityLifecycle) import MixerExperimentalCapabilityRuntime

private struct ProbeFailure: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

private final class RetirementObserver: CapabilityBridgeTerminalObserver, CapabilityBridgeRetirementObserver, @unchecked Sendable {
    private let lock = NSLock()
    private var retirements = 0
    private var failures = [ExperimentalCapabilityFailure]()

    func recordTerminalFailure(_ failure: ExperimentalCapabilityFailure) { lock.withLock { failures.append(failure) } }
    func recordRetired() { lock.withLock { retirements += 1 } }
    var retired: Bool { lock.withLock { retirements == 1 } }
    var clean: Bool { lock.withLock { retirements == 1 && failures.isEmpty } }
}

private struct Frame: Codable {
    let revision: UInt64
    let completed: Bool
    let progressPercent: Int
    let status: String
    let button: String
}

private struct Observation: Codable {
    let module: String
    let frames: [Frame]
    let acceptedEvents: UInt64
    let deliveredEvents: UInt64
    let producedFrames: UInt64
    let capabilityCalls: UInt64
    let retainedExitsAfterClose: Int
    let staleEventRefused: Bool
    let nativeMalformedEventCases: Int
    let workspaceOutboxCounts: [Int]
    let closedAndDrained: Bool
}

private func check(_ condition: Bool, _ description: String) throws {
    guard condition else { throw ProbeFailure(description) }
}

private func awaitValue<T>(_ description: String, _ poll: () throws -> T?) async throws -> T {
    let clock = ContinuousClock()
    let deadline = clock.now + .seconds(3)
    repeat {
        if let value = try poll() { return value }
        try await Task.sleep(for: .milliseconds(1))
    } while clock.now < deadline
    throw ProbeFailure("Timed out waiting for \(description)")
}

private func nativeDocument(_ task: TaskCompletion) throws -> UIDocument {
    var bytes = [UInt8](repeating: 0, count: 2048)
    let count = bytes.withUnsafeMutableBytes { task.render(into: $0) }
    return try UIDocument.decode(Data(bytes.prefix(count)))
}

private func canonicalEvent(_ revision: UInt64) throws -> Data {
    try GuestUIEventCodecV1.encode(GuestUIEventV1(sequence: revision, revision: revision, nodeID: "toggle", actionID: "task.toggle"))
}

private func activate(_ task: inout TaskCompletion, requireReview: Bool) throws -> Int {
    let canonical = try canonicalEvent(task.revision)
    try check(canonical.withUnsafeBytes { task.accepts($0) }, "Native guest parser refused the SDK-encoded event")
    let text = String(decoding: canonical, as: UTF8.self)
    let stale = try canonicalEvent(task.revision + 1)
    let malformed = [
        Data(), stale, canonical + Data([10]), Data(text.dropLast().utf8),
        Data(text.replacingOccurrences(of: "task.toggle", with: "task.other").utf8),
        Data(text.replacingOccurrences(of: "\"schemaVersion\":1", with: "\"schemaVersion\":1,\"schemaVersion\":1").utf8),
    ]
    for control in malformed {
        try check(!control.withUnsafeBytes { task.accepts($0) }, "Native guest parser accepted an invalid event")
    }
    try check(task.activate(requireReview: requireReview), "Native task refused activation")
    return malformed.count
}

private func run(_ module: URL, requireReview: Bool) async throws -> Observation {
    let bytes = try Data(contentsOf: module)
    let validation = try ExperimentalCapabilityValidator.prepareGuestUIV1(module: bytes, configuration: .init())
    try await validation.validate()

    let exchange = try GuestUIExchangeV1(generation: 1)
    let observer = RetirementObserver()
    let adapters = OwnedCapabilityAdapterGroup(terminal: observer, retirement: observer)
    let construction = try ExperimentalCapabilitySession.prepareOwnedGuestUIV1(module: bytes, configuration: .init(),
        policy: CapabilityPolicy(installed: [], manifest: []), adapterGroup: adapters, exchange: exchange)
    let session = try await construction.create()

    var frames = [Frame]()
    var rejectedNativeMessages = 0
    var outboxCounts = [Int]()
    do {
        try await session.startupGuestUIV1()
        try exchange.enterEffectsIntent(generation: 1)
        try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: DispatchTime.now().uptimeNanoseconds + 3_000_000_000)
        try exchange.confirmEffectsEnabled(generation: 1)

        var reconciler = UIReconciler()
        var task = TaskCompletion()
        let now = Date(timeIntervalSince1970: 1_792_627_200)
        var workspace = Workspace(createdAt: now)
        let project = try workspace.createProject(title: "Site inspection", site: "Pump station", now: now)
        try workspace.saveTask(projectID: project, title: "Inspect pump", responsible: "", now: now)
        let taskID = workspace.tasks[0].id
        outboxCounts.append(workspace.outbox.count)
        var prior: UIEventEnvelope?

        for revision in 1...4 as ClosedRange<UInt64> {
            let claim: GuestUIPresentationClaimV1 = try await awaitValue("frame \(revision)") {
                let snapshot = exchange.snapshot()
                try check(snapshot.stop == nil, "Guest stopped unexpectedly: \(String(describing: snapshot.firstUIProtocolFailure))")
                guard let claim = exchange.claimPresentation(generation: 1) else { return nil }
                if claim.frame == nil {
                    _ = exchange.completePresentation(claim, snapshot: nil)
                    try check(claim.eventResult == nil, "Event settled without its expected new frame")
                    return nil
                }
                return claim
            }
            guard let document = claim.frame?.document.document else { throw ProbeFailure("Missing frame \(revision)") }
            let expected = try nativeDocument(task)
            try check(document == expected && document.revision == revision, "Owned VM document differs from native Swift")
            if revision > 1 {
                try check(claim.eventResult?.sequence == revision - 1 && claim.eventResult?.outcome == .delivered,
                          "The previous event did not settle exactly once")
            }
            _ = try reconciler.apply(document)
            let snapshot = try reconciler.currentSnapshot()
            try check(exchange.completePresentation(claim, snapshot: snapshot) != nil, "Exchange refused the reconciled frame")
            guard let identity = snapshot.identity(for: "toggle"),
                  let status = document.root.children.first(where: { $0.id == "status" })?.properties["text"]?.string,
                  let button = document.root.children.first(where: { $0.id == "toggle" })?.properties["label"]?.string
            else { throw ProbeFailure("Missing task status or button") }
            let complete = workspace.tasks[0].completed
            let pending = requireReview && revision == 2
            let expectedStatus = complete ? "Completed" : pending ? "Review required" : "Open"
            let expectedButton = complete ? "Reopen task" : pending ? "Confirm completion" : "Complete task"
            try check(task.completed == complete && status == expectedStatus && button == expectedButton,
                "Rendered policy state differs from the upstream Workspace transition")
            let progress = Int(workspace.progress(for: project) * 100)
            try check(progress == (complete ? 100 : 0), "Workspace progress disagrees with completion")
            frames.append(Frame(revision: revision, completed: complete, progressPercent: progress, status: status, button: button))

            if let prior {
                _ = try await awaitValue("stale event refusal") {
                    let admission = exchange.offer(prior, generation: 1)
                    if admission == .busy { return nil as Bool? }
                    try check(admission == .stale, "A stale display event was admitted")
                    return true
                }
            }
            guard revision < 4 else { break }
            let event = UIEventEnvelope(revision: revision, identity: identity, event: .activate)
            _ = try await awaitValue("activation \(revision)") {
                let admission = exchange.offer(event, generation: 1)
                if admission == .busy { return nil as Bool? }
                try check(admission == .accepted(sequence: revision), "Current button activation was refused")
                return true
            }
            prior = event
            rejectedNativeMessages += try activate(&task, requireReview: requireReview)
            let priorOutbox = workspace.outbox
            if !requireReview || revision != 1 {
                try workspace.toggleTask(taskID, now: now)
                guard workspace.outbox.count == priorOutbox.count + 1,
                      workspace.outbox.dropLast().elementsEqual(priorOutbox),
                      let appended = workspace.outbox.last,
                      appended.recordID == taskID, appended.kind == .taskSaved,
                      !priorOutbox.contains(where: { $0.id == appended.id })
                else { throw ProbeFailure("Workspace toggle did not append exactly one new taskSaved entry for the task") }
            } else {
                try check(workspace.outbox == priorOutbox, "The review-only activation changed the Workspace outbox")
            }
            outboxCounts.append(workspace.outbox.count)
        }
    } catch {
        session.close()
        _ = try await awaitValue("failure cleanup") { session.status.drained && observer.retired ? true : nil }
        throw error
    }
    let counters = exchange.snapshot().counters
    session.close()
    _ = try await awaitValue("session drain and adapter retirement") { session.status.drained && observer.clean ? true : nil }
    let status = session.status
    try check(status.closed && status.acceptedCalls == 0 && status.retainedExits == 0 && status.failure == nil
              && counters.acceptedEvents == 3 && counters.deliveredEvents == 3 && counters.producedFrames == 4,
              "Unexpected event or cleanup counters")
    return Observation(module: module.lastPathComponent, frames: frames, acceptedEvents: counters.acceptedEvents,
        deliveredEvents: counters.deliveredEvents, producedFrames: counters.producedFrames, capabilityCalls: status.acceptedCalls,
        retainedExitsAfterClose: status.retainedExits, staleEventRefused: true,
        nativeMalformedEventCases: rejectedNativeMessages, workspaceOutboxCounts: outboxCounts,
        closedAndDrained: status.closed && status.drained)
}

@main private enum HostProbe {
    static func main() async {
        do {
            let args = CommandLine.arguments
            try check(args.count == 4, "Expected baseline, reviewed and full-SDK Wasm paths")
            let full = try Data(contentsOf: URL(fileURLWithPath: args[3]))
            do {
                let validation = try ExperimentalCapabilityValidator.prepareGuestUIV1(module: full, configuration: .init())
                validation.cancel()
                throw ProbeFailure("Full-SDK control passed the installed payload size check")
            } catch let error as ExperimentalCapabilityError where full.count > 4_194_304 {
                try check(error.code == "invalid_module_or_startup" && error.nativeStatus == nil,
                          "Unexpected full-SDK control refusal: \(error)")
                FileHandle.standardError.write(Data("full-SDK control: \(full.count) bytes, \(error.code) before native validation\n".utf8))
            }
            let baseline = try await run(URL(fileURLWithPath: args[1]), requireReview: false)
            let reviewed = try await run(URL(fileURLWithPath: args[2]), requireReview: true)
            try check(baseline.frames[1].completed && !reviewed.frames[1].completed,
                "Matched activation failed to distinguish the guest policies")
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.sortedKeys, .prettyPrinted]
            print(String(decoding: try encoder.encode([baseline, reviewed]), as: UTF8.self))
        } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(1)
        }
    }
}
