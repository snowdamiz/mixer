import Dispatch
import Foundation
import MixerSwiftUI
import MixerUI
import ReplayFeature

let replayExecutor = FeatureExecutor(serialQueue: .main)

func expect(
    _ condition: Bool, _ message: String, file: StaticString = #fileID, line: UInt = #line
) {
    precondition(condition, message, file: file, line: line)
}

func expectError<E: Error & Equatable>(
    _ expected: E, file: StaticString = #fileID, line: UInt = #line, _ operation: () throws -> Void
) throws {
    do {
        try operation()
        preconditionFailure("Expected \(expected)", file: file, line: line)
    } catch let actual as E {
        expect(actual == expected, "Expected \(expected), got \(actual)", file: file, line: line)
    }
}

func accept(_ frame: PreparedFrame, in session: FeatureSession) {
    expect(session.finish(frame.presentation.token, outcome: .drawnAndInputReady), "Draw receipt was refused")
    expect(session.acceptedPresentation?.snapshot.document == frame.presentation.snapshot.document,
           "Acceptance must publish the exact document")
}

private func event(_ frame: PreparedFrame, button label: String, occurrence: Int = 0) -> UIEventEnvelope {
    let snapshot = frame.presentation.snapshot
    var remaining = occurrence
    func find(_ node: UINode) -> UINode? {
        if node.kind == .button, node.properties["label"]?.string == label {
            if remaining == 0 { return node }
            remaining -= 1
        }
        for child in node.children {
            if let match = find(child) { return match }
        }
        return nil
    }

    guard let node = find(snapshot.document.root),
          let identity = snapshot.identity(for: node.id) else { preconditionFailure("Missing button \(label)") }
    return UIEventEnvelope(revision: snapshot.document.revision, identity: identity, event: .activate)
}

private func text(_ frame: PreparedFrame) -> [String] {
    func collect(_ node: UINode) -> [String] {
        if let text = node.properties["text"]?.string { return [text] }
        return node.children.flatMap(collect)
    }

    return collect(frame.presentation.snapshot.document.root)
}

private func frameAuthorityAndRows() throws {
    let session = FeatureSession(executor: replayExecutor)
    let a = Row(1, "A")
    let b = Row(2, "B")
    var retained: [Int: Binding<Bool>] = [:]
    var onActivate: () -> Void = {}
    func stage(_ rows: [Row], showRows: Bool = true, markedFirst: Bool = false) throws -> PreparedFrame {
        try session.prepare {
            Screen(rows: rows, showRows: showRows, markedFirst: markedFirst,
                   retain: { retained[$0] = $1 }, onActivate: { onActivate() })
        }
    }

    let first = try stage([a, b])
    let oldMark = retained[2]!
    let firstB = event(first, button: "Increment B")
    expect(text(first) == ["Rows", "A 0 false", "B 0 false"], "Initial state must come from both declarations")
    let document = first.presentation.snapshot.document
    let validator = UIValidator()
    expect(try validator.decode(validator.encode(document)).document == document, "The existing wire must round-trip")
    expect(session.acceptedPresentation == nil, "Prepare cannot grant presentation authority")
    expect(session.dispatch(first.presentation.token, firstB) == .rejected, "Candidate callback must be gated")
    accept(first, in: session)
    expect(!session.finish(first.presentation.token, outcome: .drawnAndInputReady), "Receipt is one-use")

    oldMark.wrappedValue = true
    let speculative = try stage([b, a], markedFirst: true)
    expect(text(speculative) == ["Rows", "B false 0", "A false 0"], "An idle binding must be inert")
    let token = first.presentation.token
    let wrongRevision = UIEventEnvelope(revision: firstB.revision + 1, identity: firstB.identity, event: .activate)
    let wrongGeneration = UINodeIdentity(id: firstB.identity.id, generation: firstB.identity.generation + 1)
    let wrongIdentity = UIEventEnvelope(revision: firstB.revision, identity: wrongGeneration, event: .activate)
    let wrongPayload = UIEventEnvelope(revision: firstB.revision, identity: firstB.identity, event: .activate, value: .bool(true))
    let unboundEvent = UIEventEnvelope(revision: firstB.revision, identity: firstB.identity, event: .submit)
    for invalid in [wrongRevision, wrongIdentity, wrongPayload, unboundEvent] {
        expect(session.dispatch(token, invalid) == .rejected, "SDK routing must refuse the invalid envelope")
    }
    expect(session.finish(speculative.presentation.token, outcome: .canceled),
           "Rejected input must leave the pending frame available")
    expect(session.acceptedPresentation?.token == token, "Cancel must keep the previous acceptance")

    let abandoned = try stage([a, b], showRows: false)
    expect(session.dispatch(token, firstB) == .handled(superseded: abandoned.presentation.token),
           "Accepted input must identify the speculative frame that lost authority")
    expect(!session.finish(abandoned.presentation.token, outcome: .drawnAndInputReady), "A superseded draw is stale")
    expect(session.acceptedPresentation?.token == token, "Input changes state while preserving the displayed snapshot")

    let moved = try stage([b, a], markedFirst: true)
    let movedB = event(moved, button: "Increment B")
    expect(text(moved) == ["Rows", "B true 1", "A false 0"], "Changing read order and row index must keep both cells")
    expect(movedB.identity == firstB.identity, "Keyed row move must keep the SDK node identity")
    let bRowNode = moved.presentation.snapshot.document.root.children[1]
    expect(moved.changes.moved.contains { $0.id == bRowNode.id && $0.fromIndex == 2 && $0.toIndex == 1 },
           "SDK reconciliation must emit a move relative to the accepted document")
    expect(session.dispatch(moved.presentation.token, movedB) == .rejected, "The pending handler stays unroutable")

    accept(moved, in: session)
    expect(session.dispatch(token, firstB) == .rejected, "The old frame must lose authority after promotion")
    onActivate = { oldMark.wrappedValue = true }
    expect(session.dispatch(moved.presentation.token, movedB) == .handled(superseded: nil), "Promoted handler must run")
    onActivate = {}

    let removed = try stage([a])
    expect(session.finish(removed.presentation.token, outcome: .failed), "A failed draw must consume its candidate")
    let sameRows = try stage([a, b])
    expect(text(sameRows).last == "B 2 false", "Old binding writes and failed removal must leave current state intact")
    let branchRemoved = try stage([a, b], showRows: false)
    expect(!session.finish(sameRows.presentation.token, outcome: .drawnAndInputReady), "An older candidate cannot win")
    accept(branchRemoved, in: session)

    let reinserted = try stage([a, b])
    let newB = event(reinserted, button: "Increment B")
    expect(text(reinserted).last == "B 0 false", "Accepted branch removal must retire its cells")
    expect(newB.identity != movedB.identity, "Reinsertion must allocate a new identity")
    accept(reinserted, in: session)
    let retired = UIEventEnvelope(revision: newB.revision, identity: movedB.identity, event: .activate)
    expect(session.dispatch(reinserted.presentation.token, retired) == .rejected,
           "A current revision cannot revive a retired node identity")

    let beforeDetach = try stage([a])
    expect(session.detach(), "The host must be able to close the mount")
    expect(!session.detach() && session.acceptedPresentation == nil, "A closed mount owns no presentation")
    expect(!session.finish(beforeDetach.presentation.token, outcome: .drawnAndInputReady), "Detached draw must fail")
    expect(session.dispatch(reinserted.presentation.token, newB) == .rejected, "Detached callback must fail")
    try expectError(FeatureError.detached) { _ = try stage([b]) }

    let replacement = FeatureSession(executor: replayExecutor)
    let replacementFrame = try replacement.prepare { Screen(rows: [a, b]) }
    let replacementB = event(replacementFrame, button: "Increment B")
    expect(replacementB == firstB && replacementFrame.presentation.token.ordinal == token.ordinal,
           "The replacement control must reuse wire IDs, generation, revision and frame ordinal")
    expect(!replacement.finish(token, outcome: .drawnAndInputReady), "Old-mount receipt must fail on the replacement")
    accept(replacementFrame, in: replacement)
    expect(replacement.dispatch(token, firstB) == .rejected, "Old-mount input must fail despite wire reuse")
    expect(replacement.dispatch(replacementFrame.presentation.token, replacementB) == .handled(superseded: nil),
           "The replacement's own callback must work")
    print("PASS exact receipt, SDK routing, keyed move, branch retirement, binding provenance, mount replacement")
}

private func handlerPromotion() throws {
    let session = FeatureSession(executor: replayExecutor)
    var calls: [String] = []
    func stage(_ name: String) throws -> PreparedFrame {
        try session.prepare { Button("Change") { calls.append(name) } }
    }

    let first = try stage("first")
    accept(first, in: session)
    let rejected = try stage("failed")
    expect(session.finish(rejected.presentation.token, outcome: .failed), "Expected the failure receipt to match")
    expect(session.dispatch(first.presentation.token, event(first, button: "Change")) == .handled(superseded: nil),
           "The accepted handler must survive a candidate failure")

    let next = try stage("next")
    let nextEvent = event(next, button: "Change")
    expect(session.dispatch(next.presentation.token, nextEvent) == .rejected, "Prepare must keep the new handler gated")
    expect(calls == ["first"], "Only the accepted handler could run")
    accept(next, in: session)
    expect(session.dispatch(next.presentation.token, nextEvent) == .handled(superseded: nil), "The new handler must run")
    expect(calls == ["first", "next"], "Successful receipt must promote the new handler table")
    print("PASS handler table promotion with identical rendered button properties")
}

private struct CustomMirrorView: View, CustomReflectable {
    var customMirror: Mirror { fatalError("A custom mirror ran") }
    var body: some View {
        let _ = fatal()
        Text("unreachable")
    }
}

private final class ReferenceView: View {
    var body: some View {
        let _ = fatal()
        Text("unreachable")
    }
}

private struct UnknownPrimitive: View {
    typealias Body = Never
}

private func fatal() {
    preconditionFailure("Unsupported view body or row content ran")
}

private struct InvalidState<Value>: View {
    @State var value: Value
    var body: some View {
        let _ = fatal()
        Text("unreachable")
    }
}

private struct WritingBody: View {
    @State private var count = 0

    var body: some View {
        let _ = mutate()
        Text("unreachable")
    }

    private func mutate() { count += 1 }
}

private struct AliasedDeclarations: View {
    @State private var first: Int
    @State private var second: Int

    init() {
        let declaration = State(wrappedValue: 0)
        _first = declaration
        _second = declaration
    }

    var body: some View {
        let _ = fatal()
        Text("unreachable")
    }
}

private struct PrematureWrite: View {
    @State private var value = 0

    init() { value = 1 }

    var body: some View {
        let _ = fatal()
        Text("unreachable")
    }
}

private struct InvalidTurn: View {
    @State private var count = 0
    @State private var message = "initial"

    var body: some View {
        VStack {
            Text("\(count) \(message)")
            Button("Invalid turn") {
                count += 1
                message = String(repeating: "x", count: 1_025)
            }
        }
    }
}

private struct UnsupportedKey: Hashable {
    static func == (_ lhs: Self, _ rhs: Self) -> Bool { preconditionFailure("Unsupported equality ran") }
    func hash(into hasher: inout Hasher) { preconditionFailure("Unsupported hash ran") }
}

private func refusedBuildsAndAtomicWrites() throws {
    let session = FeatureSession(
        executor: replayExecutor, validator: UIValidator(limits: UIValidationLimits(maximumStringBytes: 32))
    )
    let accepted = try session.prepare { InvalidTurn() }
    accept(accepted, in: session)

    let candidate = try session.prepare { InvalidTurn() }
    try expectError(FeatureError.duplicateRowKey) {
        _ = try session.prepare {
            VStack {
                ForEach([7, 7], id: \.self) { _ in
                    let _ = fatal()
                    Text("unreachable")
                }
            }
        }
    }
    expect(!session.finish(candidate.presentation.token, outcome: .drawnAndInputReady),
           "A refused build must supersede a previous pending frame")

    try expectError(FeatureError.unsupportedRowKey) {
        _ = try session.prepare { ForEach([UnsupportedKey()], id: \.self) { _ in Text("unreachable") } }
    }
    try expectError(FeatureError.limitExceeded("row key bytes")) {
        _ = try session.prepare { ForEach([String(repeating: "é", count: 129)], id: \.self) { Text($0) } }
    }
    try expectError(FeatureError.limitExceeded("rows per loop")) {
        _ = try session.prepare { ForEach(Array(0...1_000), id: \.self) { Text(String($0)) } }
    }
    try expectError(FeatureError.customMirror) { _ = try session.prepare { CustomMirrorView() } }
    try expectError(FeatureError.unsupportedView) { _ = try session.prepare { ReferenceView() } }
    try expectError(FeatureError.unsupportedView) { _ = try session.prepare { UnknownPrimitive() } }
    try expectError(FeatureError.unsupportedState) { _ = try session.prepare { InvalidState(value: [1]) } }
    try expectError(FeatureError.unsupportedState) { _ = try session.prepare { InvalidState(value: Optional(1)) } }
    try expectError(FeatureError.stateWriteDuringBuild) { _ = try session.prepare { WritingBody() } }
    let writtenBeforePrepare = PrematureWrite()
    try expectError(FeatureError.stateWriteDuringBuild) { _ = try session.prepare { writtenBeforePrepare } }
    try expectError(FeatureError.stateWriteDuringBuild) { _ = try session.prepare { PrematureWrite() } }
    try expectError(FeatureError.invalidRoot) {
        _ = try session.prepare { ViewBuilder.buildBlock(Text("one"), Text("two")) }
    }
    try expectError(UIValidationError.limitExceeded("stringBytes")) {
        _ = try session.prepare { Text(String(repeating: "x", count: 33)) }
    }

    try expectError(FeatureError.reusedState) { _ = try session.prepare { AliasedDeclarations() } }

    let scopedKeys = try session.prepare {
        VStack {
            ForEach(["key"], id: \.self) { Text($0) }
            ForEach(["key"], id: \.self) { Text($0) }
        }
    }
    let children = scopedKeys.presentation.snapshot.document.root.children
    expect(children.count == 2 && Set(children.map(\.id)).count == 2, "Row keys must be scoped to their loop")

    expect(session.acceptedPresentation?.token == accepted.presentation.token,
           "Refusals and key-scope probes must leave the accepted frame intact")
    let invalid = event(accepted, button: "Invalid turn")
    expect(session.dispatch(accepted.presentation.token, invalid) ==
           .invalidState(.limitExceeded("state value bytes"), superseded: scopedKeys.presentation.token),
           "An invalid routed turn must report its error and the exact superseded candidate")
    let rebuilt = try session.prepare { InvalidTurn() }
    expect(text(rebuilt) == ["0 initial"], "An invalid write must discard the entire event draft")
    accept(rebuilt, in: session)
    print("PASS fail-closed build, duplicate keys before row execution, SDK validation, event rollback")
}

private func reentrantTurns() throws {
    let session = FeatureSession(executor: replayExecutor)
    var eventHook: () -> Void = {}
    let initial = try session.prepare { Button("Invoke") { eventHook() } }
    accept(initial, in: session)
    let envelope = event(initial, button: "Invoke")
    let token = initial.presentation.token
    var refusals = 0

    func attemptReentry() {
        do {
            _ = try session.prepare { Text("unreachable") }
            preconditionFailure("Reentrant prepare unexpectedly succeeded")
        } catch FeatureError.reentrant {
            refusals += 1
        } catch {
            preconditionFailure("Unexpected reentrant error \(error)")
        }
        expect(!session.finish(token, outcome: .drawnAndInputReady), "Reentrant finish must fail")
        expect(!session.detach(), "Reentrant detach must fail")
        expect(session.dispatch(token, envelope) == .rejected, "Reentrant dispatch must fail")
    }

    let pending = try session.prepare {
        attemptReentry()
        return Text("candidate")
    }
    eventHook = attemptReentry
    expect(session.dispatch(token, envelope) == .handled(superseded: pending.presentation.token),
           "The outer event must remain authoritative")
    eventHook = {}
    expect(refusals == 2 && session.acceptedPresentation?.token == token,
           "Build and event turns must both preserve acceptance on reentry")
    print("PASS synchronous owner reentrancy refusal during build and dispatch")
}

private struct TurnCounter: View {
    @State private var count = 0
    var retain: (Binding<Int>) -> Void
    var onActivate: () -> Void = {}
    var retainState: (State<Int>) -> Void = { _ in }

    var body: some View {
        let _ = retainState(_count)
        let countBinding = $count
        let _ = retain(countBinding)
        VStack {
            Text(String(count))
            Button("Increment") {
                count += 1
                onActivate()
                countBinding.wrappedValue += 1
            }
        }
    }
}

private struct RejectingBuild: View {
    @State private var local = 0
    let write: () -> Void

    var body: some View {
        let _ = write()
        let _ = invalidate()
        Text("unreachable")
    }

    private func invalidate() { local += 1 }
}

private struct ReplayFailure: Error {
    let message: String
}

private func require(_ condition: Bool, _ message: String) throws {
    guard condition else { throw ReplayFailure(message: message) }
}

private func nestedMountTurns() throws {
    let outer = FeatureSession(executor: replayExecutor)
    let inner = FeatureSession(executor: replayExecutor)
    var outerBinding: Binding<Int>?
    var innerBinding: Binding<Int>?
    var outerHook: () -> Void = {}
    var innerHook: () -> Void = {}
    var afterRejectedBuild: Int?
    let outerFrame = try outer.prepare {
        TurnCounter(retain: { outerBinding = $0 }, onActivate: { outerHook() })
    }
    let innerFrame = try inner.prepare {
        TurnCounter(retain: { innerBinding = $0 }, onActivate: { innerHook() })
    }
    let escaped = outerBinding!
    accept(outerFrame, in: outer)
    accept(innerFrame, in: inner)
    outerHook = {
        do {
            _ = try inner.prepare { RejectingBuild { escaped.wrappedValue = 100 } }
            preconditionFailure("The inner build committed")
        } catch FeatureError.stateWriteDuringBuild {
            expect(inner.acceptedPresentation?.token == innerFrame.presentation.token,
                   "The refused build must preserve the independent mount")
        } catch {
            preconditionFailure("Unexpected nested build error: \(error)")
        }
        afterRejectedBuild = escaped.wrappedValue
    }
    let trigger = event(outerFrame, button: "Increment")
    expect(outer.dispatch(outerFrame.presentation.token, trigger) ==
           .handled(superseded: nil), "The outer accepted event must run")
    let rebuilt = try outer.prepare { TurnCounter(retain: { _ in }) }
    try require(afterRejectedBuild == 1 && text(rebuilt) == ["2"],
                "Outer draft after rejected build: \(afterRejectedBuild ?? -1), committed: \(text(rebuilt))")

    innerHook = { escaped.wrappedValue = 300 }
    outerHook = {
        innerBinding!.wrappedValue = 200
        expect(inner.dispatch(innerFrame.presentation.token, event(innerFrame, button: "Increment")) ==
               .handled(superseded: nil), "The nested accepted event must run")
    }
    expect(outer.dispatch(outerFrame.presentation.token, trigger) == .handled(superseded: rebuilt.presentation.token),
           "The outer accepted event must supersede its pending frame")
    try require(escaped.wrappedValue == 4 && innerBinding!.wrappedValue == 2,
                "Each event must write only to its own mount")

    try expectError(FeatureError.stateWriteDuringBuild) {
        _ = try inner.prepare {
            escaped.wrappedValue = 400
            return Text("root")
        }
    }
    print("PASS lexical authority across nested mounts, both phases, and scope restoration")
}

private func repeatedViewValues() throws {
    let session = FeatureSession(executor: replayExecutor)
    var bindings: [Binding<Int>] = []
    let child = TurnCounter(retain: { bindings.append($0) })
    func stage() throws -> PreparedFrame {
        bindings = []
        return try session.prepare { VStack { child; child } }
    }
    let first = try stage()
    accept(first, in: session)
    try require(bindings.count == 2 && text(first) == ["0", "0"], "Both copies must render")
    let firstCaptures = bindings
    let left = event(first, button: "Increment")
    let right = event(first, button: "Increment", occurrence: 1)
    try require(left.identity != right.identity, "Copies must have distinct node identities")
    expect(session.dispatch(first.presentation.token, right) == .handled(superseded: nil), "Right event refused")
    expect(session.dispatch(first.presentation.token, right) == .handled(superseded: nil), "Right event refused")
    expect(session.dispatch(first.presentation.token, left) == .handled(superseded: nil), "Left event refused")
    try require(firstCaptures.map(\.wrappedValue) == [2, 4], "Captures must target their own cells")
    let next = try stage()
    try require(text(next) == ["2", "4"], "Reused declarations must resolve at their structural paths")
    accept(next, in: session)
    try require(bindings.map(\.wrappedValue) == [2, 4], "Promoted captures must resolve at their structural paths")
    print("PASS reused view value has independent structural cells and captures across frames")
}

private func publishedBindingReads() throws {
    let session = FeatureSession(executor: replayExecutor)
    var captured: Binding<Int>?
    var onActivate: () -> Void = {}
    func stage() throws -> PreparedFrame {
        try session.prepare { TurnCounter(retain: { captured = $0 }, onActivate: { onActivate() }) }
    }
    let first = try stage()
    let firstBinding = captured!
    accept(first, in: session)
    let trigger = event(first, button: "Increment")
    expect(session.dispatch(first.presentation.token, trigger) == .handled(superseded: nil), "Initial event refused")
    try require(firstBinding.wrappedValue == 2, "Accepted idle getter returned \(firstBinding.wrappedValue), expected 2")

    let rejected = try stage()
    let rejectedBinding = captured!
    try require(firstBinding.wrappedValue == 2, "Preparing a candidate must preserve the accepted read")
    expect(session.finish(rejected.presentation.token, outcome: .failed), "Failed receipt refused")
    expect(session.dispatch(first.presentation.token, trigger) == .handled(superseded: nil), "Retained event refused")
    try require(firstBinding.wrappedValue == 4, "Failed frame must preserve the current binding")
    try require(rejectedBinding.wrappedValue == 2, "A failed frame keeps its captured value")

    let next = try stage()
    let currentBinding = captured!
    accept(next, in: session)
    onActivate = {
        firstBinding.wrappedValue = 500
        rejectedBinding.wrappedValue = 600
    }
    expect(session.dispatch(next.presentation.token, event(next, button: "Increment")) == .handled(superseded: nil),
           "Replacement event refused")
    try require(currentBinding.wrappedValue == 6, "Only the exact accepted frame may write")
    try require(firstBinding.wrappedValue == 0, "A retired frame keeps its captured value")
    expect(session.detach(), "Detach refused")
    try require(currentBinding.wrappedValue == 4, "A detached frame keeps its captured value")
    print("PASS accepted binding reads committed value; stale reads keep their capture value")
}

private final class AsyncAttempt: @unchecked Sendable {
    let binding: Binding<Int>
    let firstWrite = DispatchSemaphore(value: 0)
    let resume = DispatchSemaphore(value: 0)
    let secondWrite = DispatchSemaphore(value: 0)

    init(_ binding: Binding<Int>) { self.binding = binding }

    func start() {
        Task {
            expect(binding.wrappedValue == 0, "A child task must see the committed value during its parent's event")
            binding.wrappedValue = 100
            firstWrite.signal()
            waitFor(resume)
            expect(binding.wrappedValue == 2, "An expired context must still read the accepted value")
            binding.wrappedValue = 200
            secondWrite.signal()
        }
    }
}

private func waitFor(_ semaphore: DispatchSemaphore) {
    expect(semaphore.wait(timeout: .now() + 5) == .success, "Timed out waiting for concurrent test task")
}

private func asynchronousWrites() {
    let done = DispatchSemaphore(value: 0)
    let owner = DispatchQueue(label: "up5.replay.async-owner")
    let executor = FeatureExecutor(serialQueue: owner)
    Task.detached {
        defer { done.signal() }
        owner.sync {
            let session = FeatureSession(executor: executor)
            var captured: Binding<Int>?
            var onActivate: () -> Void = {}
            func stage() throws -> PreparedFrame {
                try session.prepare { TurnCounter(retain: { captured = $0 }, onActivate: { onActivate() }) }
            }
            do {
                let first = try stage()
                accept(first, in: session)
                let trigger = event(first, button: "Increment")
                let attempt = AsyncAttempt(captured!)
                onActivate = {
                    expect(withUnsafeCurrentTask { $0 != nil }, "The owner turn must run in a Swift task")
                    attempt.start()
                    waitFor(attempt.firstWrite)
                }
                expect(session.dispatch(first.presentation.token, trigger) == .handled(superseded: nil), "Event refused")
                expect(captured!.wrappedValue == 2, "The inherited write must fail while its parent turn runs")
                onActivate = {
                    attempt.resume.signal()
                    waitFor(attempt.secondWrite)
                }
                expect(session.dispatch(first.presentation.token, trigger) == .handled(superseded: nil), "Event refused")
                expect(captured!.wrappedValue == 4, "A retained context must fail during a later turn of the same frame")
                let rebuilt = try stage()
                expect(text(rebuilt) == ["4"], "Only synchronous event writes may commit")
            } catch {
                preconditionFailure("Unexpected asynchronous replay failure: \(error)")
            }
        }
    }
    waitFor(done)
    print("PASS inherited and expired asynchronous contexts cannot write during an event")
}

@main
enum Replay {
    static func main() throws {
        let probes = CommandLine.arguments.dropFirst()
        if !probes.isEmpty {
            var failures = 0
            for probe in probes {
                do {
                    switch probe {
                    case "cross-mount": try nestedMountTurns()
                    case "repeated": try repeatedViewValues()
                    case "published": try publishedBindingReads()
                    case "queue": try queueConfinement()
                    case "host-executor": try queueConfinement(hostSupplied: true)
                    case "nested-alias": try nestedAliasAction()
                    case "three-turns": try tripleNestedTurns()
                    case "typed-controls": try typedControls()
                    case "layout-refusals": try layoutRefusals()
                    default: throw ReplayFailure(message: "Unknown regression probe: \(probe)")
                    }
                } catch {
                    print("FAIL \(probe): \((error as? ReplayFailure)?.message ?? String(describing: error))")
                    failures += 1
                }
            }
            if failures > 0 { exit(1) }
            return
        }
        try frameAuthorityAndRows()
        try handlerPromotion()
        try refusedBuildsAndAtomicWrites()
        try reentrantTurns()
        try nestedMountTurns()
        try repeatedViewValues()
        try publishedBindingReads()
        asynchronousWrites()
        try queueConfinement()
        try queueConfinement(hostSupplied: true)
        try nestedAliasAction()
        try tripleNestedTurns()
        try typedControls()
        try layoutRefusals()
    }
}

private final class ReplayQueueContext: @unchecked Sendable {
    private let key = DispatchSpecificKey<String>()

    init(owner: DispatchQueue, foreign: DispatchQueue) {
        owner.setSpecific(key: key, value: "owner")
        foreign.setSpecific(key: key, value: "foreign")
    }

    var current: String? { DispatchQueue.getSpecific(key: key) }
}

private func queueConfinement(hostSupplied: Bool = false) throws {
    let owner = DispatchQueue(label: "up5.review.queue")
    let foreign = DispatchQueue(label: "up5.review.queue")
    let context = ReplayQueueContext(owner: owner, foreign: foreign)
    let executor = hostSupplied
        ? FeatureExecutor(isCurrent: { context.current == "owner" })
        : FeatureExecutor(serialQueue: owner)
    try owner.sync {
        let session = FeatureSession(executor: executor)
        var binding: Binding<Int>?
        var state: State<Int>?
        var foreignRead: Int?
        var foreignState: Int?
        var foreignProjection: Int?
        let frame = try session.prepare {
            TurnCounter(retain: { binding = $0 }, onActivate: {
                expect(context.current == "owner", "Wrong owner queue")
                expect(withUnsafeCurrentTask { $0 == nil }, "The owner must enter without a Swift task")
                let ownerThread = Thread.current
                foreign.sync {
                    expect(context.current == "foreign", "The probe must switch queues")
                    expect(Thread.current === ownerThread, "The queue switch must stay on the owner thread")
                    expect(withUnsafeCurrentTask { $0 == nil }, "The foreign turn must have no Swift task")
                    foreignRead = binding!.wrappedValue
                    binding!.wrappedValue = 100
                    foreignState = state!.wrappedValue
                    state!.wrappedValue = 200
                    let projection = state!.projectedValue
                    foreignProjection = projection.wrappedValue
                    projection.wrappedValue = 300
                }
                expect(context.current == "owner", "Owner queue did not resume")
                expect(binding!.wrappedValue == 1 && state!.wrappedValue == 1, "Owner draft must resume")
            }, retainState: { state = $0 })
        }
        accept(frame, in: session)
        let token = frame.presentation.token
        let trigger = event(frame, button: "Increment")
        let pending = try session.prepare { Text("pending") }
        try foreign.sync {
            var built = false
            try expectError(FeatureError.wrongExecutor) {
                _ = try session.prepare {
                    built = true
                    return Text("foreign")
                }
            }
            expect(!built, "A foreign prepare must never run the root")
            expect(session.acceptedPresentation == nil, "A foreign session read must be refused")
            expect(!session.finish(pending.presentation.token, outcome: .drawnAndInputReady),
                   "A foreign receipt must be refused")
            expect(session.dispatch(token, trigger) == .rejected, "A foreign event must be refused")
            expect(!session.detach(), "A foreign detach must be refused")
        }
        expect(session.finish(pending.presentation.token, outcome: .failed), "The owner must retain its candidate")
        expect(session.dispatch(token, trigger) ==
               .handled(superseded: nil), "The owner's accepted callback must run")
        try require(foreignRead == 0 && foreignState == 0 && foreignProjection == 0,
                    "A foreign serial queue read the owner event's draft")
        try require(binding!.wrappedValue == 2, "A foreign serial queue wrote the owner event's state")
    }
    let origin = hostSupplied ? "host-supplied" : "native Dispatch"
    print("PASS \(origin) executor confines session entry and draft access across same-thread queues")
}

private struct NestedAliasParent: View {
    @State private var value = 0
    let alias: Bool
    var retain: (Binding<Int>) -> Void = { _ in }

    var body: some View {
        let binding = $value
        let _ = retain(binding)
        VStack {
            Text("parent \(value)")
            if alias {
                NestedAliasChild(state: _value, parentAction: { value += 1 })
            } else {
                NestedBindingChild(parent: binding)
            }
        }
    }
}

private struct NestedAliasChild: View {
    @State private var value: Int
    let parentAction: () -> Void

    init(state: State<Int>, parentAction: @escaping () -> Void) {
        _value = state
        self.parentAction = parentAction
    }

    var body: some View {
        VStack {
            Text("child \(value)")
            Button("Increment parent", action: parentAction)
        }
    }
}

private struct NestedBindingChild: View {
    @State private var value = 10
    let parent: Binding<Int>

    var body: some View {
        VStack {
            Text("child \(value), parent binding \(parent.wrappedValue)")
            Button("Increment parent") {
                parent.wrappedValue += 1
                value += 2
            }
        }
    }
}

private func nestedAliasAction() throws {
    let session = FeatureSession(executor: replayExecutor)
    var parent: Binding<Int>?
    let frame = try session.prepare { NestedAliasParent(alias: false, retain: { parent = $0 }) }
    accept(frame, in: session)
    expect(text(frame) == ["parent 0", "child 10, parent binding 0"], "The two cells must start independently")
    let token = frame.presentation.token
    let trigger = event(frame, button: "Increment parent")
    expect(session.dispatch(token, trigger) == .handled(superseded: nil), "Initial Binding action refused")
    expect(parent!.wrappedValue == 1, "The child must write the parent's cell through its Binding")

    let pending = try session.prepare { NestedAliasParent(alias: false) }
    try expectError(FeatureError.reusedState) {
        _ = try session.prepare { NestedAliasParent(alias: true) }
    }
    expect(session.acceptedPresentation?.snapshot.document == frame.presentation.snapshot.document,
           "Rejecting the alias must preserve the accepted document")
    expect(!session.finish(pending.presentation.token, outcome: .drawnAndInputReady),
           "The alias build must supersede the older candidate")
    expect(parent!.wrappedValue == 1, "Rejecting the alias must preserve committed state")
    expect(session.dispatch(token, trigger) == .handled(superseded: nil), "Accepted Binding action must remain routable")
    let next = try session.prepare { NestedAliasParent(alias: false) }
    try require(text(next) == ["parent 2", "child 14, parent binding 2"],
                "Recovery must preserve independent cells and parent Binding reads and writes")
    print("PASS ancestor wrapper alias refuses preparation and preserves the accepted parent Binding action")
}

private func tripleNestedTurns() throws {
    let outer = FeatureSession(executor: replayExecutor)
    let middle = FeatureSession(executor: replayExecutor)
    let inner = FeatureSession(executor: replayExecutor)
    var outerBinding: Binding<Int>?
    var middleBinding: Binding<Int>?
    var innerBinding: Binding<Int>?
    var outerHook: () -> Void = {}
    var middleHook: () -> Void = {}
    let outerFrame = try outer.prepare {
        TurnCounter(retain: { outerBinding = $0 }, onActivate: { outerHook() })
    }
    let middleFrame = try middle.prepare {
        TurnCounter(retain: { middleBinding = $0 }, onActivate: { middleHook() })
    }
    let innerFrame = try inner.prepare {
        TurnCounter(retain: { innerBinding = $0 }, onActivate: {
            expect(outerBinding!.wrappedValue == 0 && middleBinding!.wrappedValue == 0,
                   "Inner event read foreign drafts")
            outerBinding!.wrappedValue = 100
            middleBinding!.wrappedValue = 200
        })
    }
    accept(outerFrame, in: outer)
    accept(middleFrame, in: middle)
    accept(innerFrame, in: inner)
    middleHook = {
        expect(inner.dispatch(innerFrame.presentation.token, event(innerFrame, button: "Increment")) ==
               .handled(superseded: nil), "Inner event refused")
        expect(middleBinding!.wrappedValue == 1, "Middle draft did not resume")
        expect(innerBinding!.wrappedValue == 2, "Inner commit missing")
    }
    outerHook = {
        expect(middle.dispatch(middleFrame.presentation.token, event(middleFrame, button: "Increment")) ==
               .handled(superseded: nil), "Middle event refused")
        expect(outerBinding!.wrappedValue == 1, "Outer draft did not resume")
        expect(middleBinding!.wrappedValue == 2, "Middle commit missing")
    }
    expect(outer.dispatch(outerFrame.presentation.token, event(outerFrame, button: "Increment")) ==
           .handled(superseded: nil), "Outer event refused")
    try require([outerBinding!, middleBinding!, innerBinding!].map(\.wrappedValue) == [2, 2, 2],
                "One or more mounts committed a foreign write")
    print("PASS three nested accepted events isolate drafts and restore owner scope")
}
