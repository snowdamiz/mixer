import Darwin
import Dispatch
import Foundation
import MixerCapabilities
import MixerUI
@_spi(GuestUIV1) import MixerGuest
@_spi(GuestUIV1) @_spi(CapabilityLifecycle) import MixerExperimentalCapabilityRuntime

private let eventCount: UInt64 = 12
private let generation: UInt64 = 1

private struct Failure: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

private func require(_ ok: Bool, _ message: @autoclosure () -> String) throws {
    guard ok else { throw Failure(message()) }
}

private final class Retirement: CapabilityBridgeTerminalObserver, CapabilityBridgeRetirementObserver, @unchecked Sendable {
    private let lock = NSLock()
    private var count = 0
    private var recorded = [ExperimentalCapabilityFailure]()
    func recordTerminalFailure(_ failure: ExperimentalCapabilityFailure) { lock.withLock { recorded.append(failure) } }
    func recordRetired() { lock.withLock { count += 1 } }
    var retirements: Int { lock.withLock { count } }
    var failures: [ExperimentalCapabilityFailure] { lock.withLock { recorded } }
}

private func drain(_ session: ExperimentalCapabilitySession, _ observer: Retirement) async throws {
    session.close()
    let clock = ContinuousClock()
    let deadline = clock.now + .seconds(3)
    while !session.status.drained || observer.retirements == 0 {
        try require(clock.now < deadline, "Owned session failed to drain and retire")
        try await Task.sleep(for: .milliseconds(1))
    }
    let status = session.status
    try require(status.closed && status.retainedExits == 0 && status.retainedPayloadBytes == 0
        && status.acceptedCalls == 0 && observer.retirements == 1, "Unexpected close/adapter ledger")
}

private func construction(_ bytes: Data, _ configuration: ExperimentalCapabilityConfiguration,
                          _ exchange: GuestUIExchangeV1, _ observer: Retirement) throws -> ExperimentalCapabilityConstruction {
    try ExperimentalCapabilitySession.prepareOwnedGuestUIV1(module: bytes, configuration: configuration,
        policy: CapabilityPolicy(installed: [], manifest: []),
        adapterGroup: OwnedCapabilityAdapterGroup(terminal: observer, retirement: observer), exchange: exchange)
}

private func validate(_ bytes: Data, _ configuration: ExperimentalCapabilityConfiguration = .init()) async throws {
    try await ExperimentalCapabilityValidator.prepareGuestUIV1(module: bytes, configuration: configuration).validate()
}

private struct Presentation {
    let document: UIDocument
    let event: UIEventEnvelope
    let time: UInt64
}

private struct Driver {
    let exchange: GuestUIExchangeV1
    let wake: GuestUIWakeConsumerV1
    var reconciler = UIReconciler()

    init(_ exchange: GuestUIExchangeV1) throws {
        self.exchange = exchange
        self.wake = try exchange.deliveryWake.takeConsumer()
    }

    func start(_ session: ExperimentalCapabilitySession) async throws {
        try await session.startupGuestUIV1()
        try exchange.enterEffectsIntent(generation: generation)
        try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: DispatchTime.now().uptimeNanoseconds + 3_000_000_000)
        try exchange.confirmEffectsEnabled(generation: generation)
    }

    mutating func present(revision: UInt64) async throws -> Presentation {
        while true {
            let state = exchange.snapshot()
            try require(state.stop == nil, "Exchange stopped before revision \(revision): \(String(describing: state.stop))")
            if let claim = exchange.claimPresentation(generation: generation) {
                guard let document = claim.frame?.document.document else {
                    _ = exchange.completePresentation(claim, snapshot: nil)
                    try require(claim.eventResult == nil, "Event settled without a new document")
                    continue
                }
                _ = try reconciler.apply(document)
                let render = try reconciler.currentSnapshot()
                let ticket = exchange.completePresentation(claim, snapshot: render)
                let time = DispatchTime.now().uptimeNanoseconds
                try require(ticket != nil && document.revision == revision, "Unexpected document or rejected presentation")
                if revision == 1 {
                    try require(claim.eventResult == nil, "Unexpected first-document settlement")
                } else {
                    try require(claim.eventResult?.sequence == revision - 1 && claim.eventResult?.outcome == .delivered,
                                "Expected exactly one delivered event for revision \(revision)")
                }
                guard let identity = render.identity(for: "toggle") else { throw Failure("Missing toggle identity") }
                return Presentation(document: document,
                    event: UIEventEnvelope(revision: revision, identity: identity, event: .activate), time: time)
            }
            let signalled = try await wake.next()
            try require(signalled, "Delivery wake closed before document")
        }
    }

    func offer(_ event: UIEventEnvelope, expected: GuestUIEventAdmissionV1) async throws {
        let clock = ContinuousClock()
        let deadline = clock.now + .seconds(3)
        while true {
            let admission = exchange.offer(event, generation: generation)
            if admission != .busy {
                try require(admission == expected, "Unexpected input admission \(admission) for revision \(event.revision)")
                return
            }
            try require(clock.now < deadline && !Task.isCancelled, "Input admission remained busy")
            // Ready-only guest turns can race an offer. Keep retries in the sample.
            await Task.yield()
        }
    }
}

private struct Oracle {
    var task = TaskCompletion()
    var workspace: Workspace
    let project: UUID
    let taskID: UUID
    let reviewed: Bool
    let now = Date(timeIntervalSince1970: 1_792_627_200)
    var malformed = 0
    var outbox: [Int]

    init(reviewed: Bool) throws {
        self.reviewed = reviewed
        var workspace = Workspace(createdAt: now)
        project = try workspace.createProject(title: "Site inspection", site: "Pump station", now: now)
        try workspace.saveTask(projectID: project, title: "Inspect pump", responsible: "", now: now)
        taskID = workspace.tasks[0].id
        self.workspace = workspace
        outbox = [workspace.outbox.count]
    }

    func compare(_ document: UIDocument) throws {
        var bytes = [UInt8](repeating: 0, count: 2048)
        let count = bytes.withUnsafeMutableBytes { task.render(into: $0) }
        let expected = try UIDocument.decode(Data(bytes.prefix(count)))
        try require(document == expected, "Owned document differs from native Swift at revision \(document.revision)")
        let completed = workspace.tasks[0].completed
        try require(completed == task.completed && workspace.progress(for: project) == (completed ? 1 : 0),
                    "Workspace completion or progress differs")
    }

    mutating func activate() throws {
        let revision = task.revision
        let input = try GuestUIEventCodecV1.encode(.init(sequence: revision, revision: revision,
            nodeID: "toggle", actionID: "task.toggle"))
        let stale = try GuestUIEventCodecV1.encode(.init(sequence: revision, revision: revision + 1,
            nodeID: "toggle", actionID: "task.toggle"))
        let text = String(decoding: input, as: UTF8.self)
        let invalid = [Data(), stale, input + Data([10]), Data(text.dropLast().utf8),
                       Data(text.replacingOccurrences(of: "task.toggle", with: "task.other").utf8),
                       Data(text.replacingOccurrences(of: #""schemaVersion":1"#,
                                                      with: #""schemaVersion":1,"schemaVersion":1"#).utf8)]
        try require(input.withUnsafeBytes { task.accepts($0) }, "Native parser rejected canonical activation")
        for sample in invalid {
            try require(!sample.withUnsafeBytes { task.accepts($0) }, "Native parser accepted malformed activation")
        }
        malformed += invalid.count
        let before = workspace.outbox
        if !reviewed || (revision - 1) % 3 != 0 {
            try workspace.toggleTask(taskID, now: now)
            let after = workspace.outbox
            try require(after.count == before.count + 1 && after.dropLast().elementsEqual(before)
                && after.last?.recordID == taskID && after.last?.kind == .taskSaved, "Incorrect Workspace outbox append")
        } else {
            try require(workspace.outbox == before, "Review changed the Workspace outbox")
        }
        try require(task.activate(requireReview: reviewed), "Native activation failed")
        outbox.append(workspace.outbox.count)
    }
}

private func checkPolicy(_ document: UIDocument, reviewed: Bool) throws -> String {
    let sequence = document.revision - 1
    let label: String
    let button: String
    if reviewed && sequence % 3 == 1 {
        (label, button) = ("Review required", "Confirm completion")
    } else if reviewed ? sequence % 3 == 2 : sequence % 2 == 1 {
        (label, button) = ("Completed", "Reopen task")
    } else {
        (label, button) = ("Open", "Complete task")
    }
    let children = document.root.children
    try require(children.first(where: { $0.id == "task" })?.properties["text"]?.string == "Inspect pump"
        && children.first(where: { $0.id == "status" })?.properties["text"]?.string == label
        && children.first(where: { $0.id == "toggle" })?.properties["label"]?.string == button,
        "Document policy differs at revision \(document.revision)")
    return label
}

private func residentBytes() throws -> UInt64 {
    var info = mach_task_basic_info_data_t()
    var count = mach_msg_type_number_t(MemoryLayout.size(ofValue: info) / MemoryLayout<integer_t>.stride)
    let result = withUnsafeMutablePointer(to: &info) {
        $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
            task_info(mach_task_self_, task_flavor_t(MACH_TASK_BASIC_INFO), $0, &count)
        }
    }
    try require(result == KERN_SUCCESS, "task_info failed: \(result)")
    return info.resident_size
}

private func usage() throws -> rusage {
    var value = rusage()
    let result = getrusage(RUSAGE_SELF, &value)
    try require(result == 0, "getrusage failed: \(errno)")
    return value
}

private struct Sample: Encodable {
    var fixture: String
    var launchNS: UInt64?
    var inputNS = [UInt64]()
    var inputTimerTicks = [UInt64]()
    var rssBytes = [String: UInt64]()
    var peakRSSBytes: Int?
    var processCPUMicroseconds: Int?
    var statuses = [String]()
    var workspaceOutbox = [Int]()
    var nativeMalformed = 0
    var staleRefusals = 0
    var acceptedEvents: UInt64 = 0
    var deliveredEvents: UInt64 = 0
    var producedFrames: UInt64 = 0
    var maxDocumentBytes: UInt64 = 0
    var maxEventBytes: UInt64 = 0
    var vmTurns: UInt64 = 0
    var maximumBatchNS: UInt64 = 0
    var retired = false
}

private func run(_ bytes: Data, fixture: String, timed: Bool) async throws -> Sample {
    let reviewed = fixture == "reviewed"
    var sample = Sample(fixture: fixture)
    var oracle = timed ? nil : try Oracle(reviewed: reviewed)
    let configuration = ExperimentalCapabilityConfiguration()
    if timed { sample.rssBytes["beforeValidation"] = try residentBytes() }
    let launchStart = DispatchTime.now().uptimeNanoseconds
    try await validate(bytes, configuration)
    let exchange = try GuestUIExchangeV1(generation: generation)
    let observer = Retirement()
    var driver = try Driver(exchange)
    let session = try await construction(bytes, configuration, exchange, observer).create()
    let watchdog = DispatchSource.makeTimerSource()
    watchdog.schedule(deadline: .now() + .seconds(8))
    watchdog.setEventHandler { exchange.stop(.deadline) }
    watchdog.resume()
    defer { watchdog.cancel() }

    do {
        try await driver.start(session)
        var presentation = try await driver.present(revision: 1)
        if timed {
            sample.launchNS = presentation.time - launchStart
            sample.rssBytes["firstDocument"] = try residentBytes()
        }
        sample.statuses.append(try checkPolicy(presentation.document, reviewed: reviewed))
        try oracle?.compare(presentation.document)
        for sequence in 1...eventCount {
            let prior = presentation.event
            try oracle?.activate()
            let ticks = timed ? session.status.timerTicks : 0
            let inputStart = DispatchTime.now().uptimeNanoseconds
            try await driver.offer(prior, expected: .accepted(sequence: sequence))
            presentation = try await driver.present(revision: sequence + 1)
            if timed {
                sample.inputNS.append(presentation.time - inputStart)
                sample.inputTimerTicks.append(session.status.timerTicks - ticks)
            }
            sample.statuses.append(try checkPolicy(presentation.document, reviewed: reviewed))
            try oracle?.compare(presentation.document)
            if !timed {
                try await driver.offer(prior, expected: .stale)
                sample.staleRefusals += 1
            }
        }
        if timed { sample.rssBytes["lastDocument"] = try residentBytes() }
        let counters = exchange.snapshot().counters
        try require(session.status.turns == eventCount + 1 && counters.acceptedEvents == eventCount && counters.deliveredEvents == eventCount
            && counters.producedFrames == eventCount + 1 && counters.terminalEvents == 0 && counters.replacedPendingFrames == 0
            && counters.maximumPendingFrames == 1 && counters.maximumClaimedFrames == 1
            && counters.maximumEventSlots == 1, "Unexpected input or frame counters")
        sample.acceptedEvents = counters.acceptedEvents
        sample.deliveredEvents = counters.deliveredEvents
        sample.producedFrames = counters.producedFrames
        sample.maxDocumentBytes = counters.maximumRawDocumentBytes
        sample.maxEventBytes = counters.maximumEventBytes
        sample.workspaceOutbox = oracle?.outbox ?? []
        sample.nativeMalformed = oracle?.malformed ?? 0
    } catch {
        try await drain(session, observer)
        throw error
    }
    try await drain(session, observer)
    try require(session.status.failure == nil && observer.failures.isEmpty, "Unexpected terminal failure")
    sample.retired = true
    sample.vmTurns = session.status.turns
    sample.maximumBatchNS = session.status.maximumBatchNanoseconds
    if timed {
        sample.rssBytes["afterDrain"] = try residentBytes()
        let observed = try usage()
        sample.peakRSSBytes = observed.ru_maxrss
        sample.processCPUMicroseconds = [observed.ru_utime, observed.ru_stime].reduce(0) {
            $0 + $1.tv_sec * 1_000_000 + Int($1.tv_usec)
        }
    }
    return sample
}

private func controls(_ bytes: Data, full: Data) async throws -> [String: String] {
    do {
        let validation = try ExperimentalCapabilityValidator.prepareGuestUIV1(module: full, configuration: .init())
        validation.cancel()
        throw Failure("Oversize full-SDK payload admitted")
    } catch let error as ExperimentalCapabilityError {
        try require(full.count > 4_194_304 && error.code == "invalid_module_or_startup"
            && error.nativeStatus == nil, "Incorrect oversized payload refusal")
    }
    do {
        try await validate(Data(bytes.prefix(7)))
        throw Failure("Truncated Wasm admitted")
    } catch let error as ExperimentalCapabilityError {
        try require(error.code == "malformed" && error.failure.operation == .validation && error.nativeStatus != nil,
                    "Incorrect malformed Rust validation response: \(error)")
    }
    let configuration = ExperimentalCapabilityConfiguration(fuel: 1)
    try await validate(bytes, configuration)
    let exhausted = try GuestUIExchangeV1(generation: generation)
    let exhaustedObserver = Retirement()
    let lowFuel = try await construction(bytes, configuration, exhausted, exhaustedObserver).create()
    do {
        var refusal: ExperimentalCapabilityError?
        do { try await lowFuel.startupGuestUIV1() }
        catch let error as ExperimentalCapabilityError { refusal = error }
        try require(refusal?.code == "fuel_exhausted" && refusal?.failure.kind == .resource(.fuel)
            && refusal?.nativeStatus != nil && exhausted.snapshot().counters.producedFrames == 0,
            "Incorrect startup fuel refusal: \(String(describing: refusal))")
    } catch {
        try await drain(lowFuel, exhaustedObserver)
        throw error
    }
    try await drain(lowFuel, exhaustedObserver)

    let stopped = try GuestUIExchangeV1(generation: generation)
    let stoppedObserver = Retirement()
    let session = try await construction(bytes, .init(), stopped, stoppedObserver).create()
    let watchdog = DispatchSource.makeTimerSource()
    watchdog.schedule(deadline: .now() + .seconds(8))
    watchdog.setEventHandler { stopped.stop(.deadline) }
    watchdog.resume()
    defer { watchdog.cancel() }
    let began: Bool
    do {
        var driver = try Driver(stopped)
        try await driver.start(session)
        let first = try await driver.present(revision: 1)
        try await driver.offer(first.event, expected: .accepted(sequence: 1))
        stopped.stop(.cancelled)
        guard let claim = stopped.claimPresentation(generation: generation) else {
            throw Failure("Missing cancellation settlement")
        }
        let result = claim.eventResult
        _ = stopped.completePresentation(claim, snapshot: nil)
        guard claim.stop == .cancelled, claim.frame == nil, result?.sequence == 1,
              case .terminal(let turnBegan)? = result?.outcome else {
            throw Failure("Cancelled event did not settle as terminal without publication")
        }
        began = turnBegan
        if let refresh = stopped.claimPresentation(generation: generation) {
            _ = stopped.completePresentation(refresh, snapshot: nil)
            try require(refresh.eventResult == nil && refresh.frame == nil, "Cancelled result repeated")
        }
        try await driver.offer(first.event, expected: .closed)
        let state = stopped.snapshot()
        try require(state.counters.acceptedEvents == 1 && state.counters.terminalEvents == 1
            && !state.eventOutstanding && !state.guestTurnInFlight && !state.presentationInFlight,
            "Cancellation did not clear exchange ownership")
    } catch {
        try await drain(session, stoppedObserver)
        throw error
    }
    try await drain(session, stoppedObserver)
    try require(session.status.failure == nil && stoppedObserver.failures.isEmpty, "Unexpected cancellation bridge failure")
    return ["oversize": "invalid_module_or_startup before native validation",
            "truncatedWasm": "malformed in native validation",
            "startupFuel": "fuel_exhausted, zero frames, drained and retired",
            "acceptedEventCancellation": "one terminal result, turnBegan=\(began), no frame published after stop, later input closed, drained and retired"]
}

@main private enum Benchmark {
    static func main() async {
        do {
            let args = CommandLine.arguments
            try require(args.count == 4 && ["differential", "timed", "guards"].contains(args[1]),
                        "Expected differential|timed baseline|reviewed module, or guards baseline-module full-SDK-module")
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.sortedKeys]
            let result: Data
            if args[1] == "guards" {
                result = try await encoder.encode(controls(Data(contentsOf: URL(fileURLWithPath: args[2])),
                    full: Data(contentsOf: URL(fileURLWithPath: args[3]))))
            } else {
                try require(["baseline", "reviewed"].contains(args[2]), "Unknown fixture")
                let bytes = try Data(contentsOf: URL(fileURLWithPath: args[3]))
                result = try await encoder.encode(run(bytes, fixture: args[2], timed: args[1] == "timed"))
            }
            print(String(decoding: result, as: UTF8.self))
        } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(1)
        }
    }
}
