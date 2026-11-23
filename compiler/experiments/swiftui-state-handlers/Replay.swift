#if S3_GUEST
import WASILibc
#endif
#if S3_LINKED_S2
import FieldLogSpike
#endif

private func require(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() { fatalError(message) }
}

private func handler(_ title: String, in document: Document) -> Int {
    let matches = document.nodes.compactMap { node -> Int? in
        if case let .button(label, id) = node, title == label { return id }
        return nil
    }
    require(matches.count == 1, "Expected exactly one button named \(title)")
    return matches[0]
}

private func labels(_ document: Document) -> [String] {
    document.nodes.compactMap { node in
        if case let .text(title) = node { return title }
        return nil
    }
}

private struct DuplicateKeys: View {
    var body: some View {
        ForEach([1, 1], id: \.self) { key in
            Text("Duplicate \(key)")
        }
    }
}

private struct BodyWrite: View {
    @State private var count = 0

    private func attemptWrite() -> Int {
        count += 1
        return count
    }

    var body: some View { Text("Invalid \(attemptWrite())") }
}

private struct HiddenState: View, CustomReflectable {
    @State private var count = 0
    let recordEvaluation: (String) -> Void

    var customMirror: Mirror {
        recordEvaluation("customMirror")
        return Mirror(self, children: [:])
    }

    private func attemptWrite() -> Int {
        recordEvaluation("body")
        count += 1
        return count
    }

    var body: some View {
        Text("Hidden count = \(attemptWrite())")
        Button("Bump hidden state") { count += 1 }
    }
}

private struct SharedScreenReplay {
    private let runtime = FrameRuntime(feature: 1)
    private var previous: Document?

    mutating func advance(_ index: Int) -> String {
        let checkpoint = Checkpoint.journey[index]
        if let action = checkpoint.action, let previous {
            require(runtime.dispatch(previous.id, handler: handler(action, in: previous)), "Dispatch \(action)")
        }
        let candidate = runtime.stage(ProbeScreen())!
        require(labels(candidate) == checkpoint.labels, "Checkpoint \(index): \(labels(candidate))")
        require(!runtime.dispatch(candidate.id, handler: 0), "Candidate dispatch before presentation")
        require(runtime.acknowledge(candidate.id), "Present checkpoint \(index)")
        if let previous {
            require(!runtime.dispatch(previous.id, handler: 0), "Previous frame still routable")
            require(!runtime.acknowledge(previous.id), "Previous acknowledgment replay")
        }
        require(!runtime.acknowledge(candidate.id), "Repeated acknowledgment")
        previous = candidate
        return "s3 checkpoint \(index) | " + labels(candidate).joined(separator: " | ")
    }
}

private func replayPublicationAndRollback() -> String {
    let runtime = FrameRuntime(feature: 1)
    let initial = runtime.stage(ProbeScreen())!
    require(runtime.acknowledge(initial.id), "Initial presentation")
    require(!runtime.dispatch(initial.id, handler: -1), "Negative handler ID")
    require(!runtime.dispatch(initial.id, handler: Int.max), "Unregistered handler ID")
    require(runtime.dispatch(initial.id, handler: handler("Bump branch", in: initial)), "Set branch state")
    let prior = runtime.stage(ProbeScreen())!
    require(runtime.acknowledge(prior.id), "Present branch")
    require(labels(prior).last == "Branch = 1", "Persist branch")

    let canceled = runtime.stage(ProbeScreen(hideBranchForPresentation: true))!
    require(labels(canceled).last == "Branch hidden", "Need candidate to prune accepted branch")
    require(!runtime.discard(initial.id), "Wrong frame discarded newer stage")
    require(runtime.discard(canceled.id), "Cancel staged draw")
    require(!runtime.acknowledge(canceled.id), "Canceled draw resurrected")
    require(runtime.presented?.id == prior.id, "Cancel replaced accepted document")
    require(!runtime.dispatch(canceled.id, handler: 0), "Canceled handlers became routable")

    let pending = runtime.stage(ProbeScreen())!
    let wrongOwner = FrameID(feature: pending.id.feature + 1, frame: pending.id.frame)
    require(!runtime.acknowledge(wrongOwner), "Other feature acknowledged matching frame")
    require(!runtime.discard(wrongOwner), "Other feature discarded matching frame")
    require(runtime.dispatch(prior.id, handler: handler("Bump branch", in: prior)), "Prior branch handler lost")
    require(!runtime.acknowledge(pending.id), "Action left out-of-date snapshot publishable")
    require(runtime.stage(DuplicateKeys()) == nil, "Duplicate row keys admitted")
    require(runtime.stage(BodyWrite()) == nil, "Write during body admitted")
    var evaluations: [String] = []
    require(runtime.stage(HiddenState { evaluations.append($0) }) == nil, "Custom-reflectable view admitted")
    require(evaluations.isEmpty, "Rejected view evaluated \(evaluations)")
    require(runtime.presented?.id == prior.id, "Invalid render replaced accepted document")
    require(runtime.dispatch(prior.id, handler: handler("Bump branch", in: prior)), "Prior handler after invalid render")
    let recovered = runtime.stage(ProbeScreen())!
    require(labels(recovered).last == "Branch = 3", "Accepted state lost after cancel or validation failure")
    require(runtime.acknowledge(recovered.id), "Present after recovery")

    let oldPending = runtime.stage(ProbeScreen())!
    require(!runtime.replaceFeature(with: initial.id.feature), "Reused a retired feature epoch")
    require(runtime.replaceFeature(with: 2), "Replace feature for rollback")
    require(runtime.presented == nil, "Retired document still presented")
    let restored = runtime.stage(ProbeScreen())!
    require(initial.id.frame == restored.id.frame && initial.id.feature != restored.id.feature, "Need frame collision")
    require(handler("Bump first", in: initial) == handler("Bump first", in: restored), "Need handler collision")
    require(!runtime.acknowledge(initial.id), "Previous owner published reused frame")
    require(!runtime.acknowledge(oldPending.id), "Previous owner's pending draw survived rollback")
    require(runtime.acknowledge(restored.id), "Present restored feature")
    require(!runtime.dispatch(initial.id, handler: 0), "Previous owner hit reused handler")
    require(!runtime.dispatch(recovered.id, handler: 0), "Retired accepted frame dispatched")
    require(runtime.dispatch(restored.id, handler: 0), "Restored owner could not dispatch")
    let after = runtime.stage(ProbeScreen())!
    require(labels(after) == ["Values 2 / 10", "Row 1 = 0", "Row 2 = 0", "Branch = 0"], "Stale action affected restored state")
    return "s3 publication | pending refused | canceled draw | invalid render | prior handlers | rollback collision refused"
}

#if S3_OWNED_VM
private let eventCapacity = 1_048_576
private let frameCapacity = 4096
private nonisolated(unsafe) var session = SharedScreenReplay()
private nonisolated(unsafe) var nextStep = 0
private nonisolated(unsafe) var input: UnsafeMutablePointer<UInt8>?
private nonisolated(unsafe) var frame: UnsafeMutablePointer<UInt8>?
private nonisolated(unsafe) var header: UnsafeMutablePointer<UInt32>?

private func publish(_ line: String) -> UInt32 {
    let bytes = line.utf8
    precondition(bytes.count <= frameCapacity)
    for (index, byte) in bytes.enumerated() { frame![index] = byte }
    header![3] = UInt32(bytes.count)
    return UInt32(UInt(bitPattern: header!))
}

@_cdecl("mixer_guest_ui_start_v3")
func reactorStart() -> UInt32 {
    precondition(header == nil)
    let eventBuffer = UnsafeMutablePointer<UInt8>.allocate(capacity: eventCapacity)
    let frameBuffer = UnsafeMutablePointer<UInt8>.allocate(capacity: frameCapacity)
    let words = UnsafeMutablePointer<UInt32>.allocate(capacity: 8)
    words.initialize(repeating: 0, count: 8)
    words[0] = 0x3349554d
    words[1] = 32
    words[2] = UInt32(UInt(bitPattern: frameBuffer))
    words[4] = UInt32(UInt(bitPattern: eventBuffer))
    words[5] = UInt32(eventCapacity)
    input = eventBuffer
    frame = frameBuffer
    header = words
    nextStep = 1
    return publish(session.advance(0))
}

@_cdecl("mixer_guest_ui_event_v3")
func reactorEvent(_ length: UInt32) -> UInt32 {
    guard length == 1, let input else { return 0 }
    let step = Int(input.pointee)
    let rollback = Checkpoint.journey.count
    #if S3_LINKED_S2
    // Each independent fixture can start immediately after the first snapshot.
    if nextStep == 1 && (step == rollback || step == rollback + 1) { nextStep = step }
    #endif
    guard step == nextStep else { return 0 }
    nextStep += 1
    if step < rollback { return publish(session.advance(step)) }
    if step == rollback { return publish(replayPublicationAndRollback()) }
    #if S3_LINKED_S2
    let s2Step = step - rollback - 1
    if s2Step < 6 { return publish(String(decoding: linkedS2Snapshot(UInt8(s2Step)), as: UTF8.self)) }
    #endif
    return 0
}

@_cdecl("mixer_guest_ui_ready_v3")
func reactorReady() {}
#else
private func replay() {
    var session = SharedScreenReplay()
    for index in Checkpoint.journey.indices { print(session.advance(index)) }
    print(replayPublicationAndRollback())
}

#if S3_GUEST
@_cdecl("mixer_s3_replay")
func guestReplay() -> Int32 {
    replay()
    return fflush(nil)
}
#else
@main
struct HostReplay {
    static func main() { replay() }
}
#endif
#endif
