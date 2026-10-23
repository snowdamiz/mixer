import Dispatch
import Foundation
import MixerUI
#if REVIEW_INTERNALS
@_spi(GuestUIV1) @testable import MixerGuest
#else
@_spi(GuestUIV1) import MixerGuest
#endif

struct ReviewFailure: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}
func require(_ value: Bool, _ message: String) throws {
    if !value { throw ReviewFailure(message) }
}
func rejects(_ body: () throws -> Void) -> Bool {
    do { try body(); return false } catch { return true }
}
func localReject(_ expected: GuestUIControlRejectionV1, _ body: () throws -> Void) -> Bool {
    do { try body(); return false } catch let error as GuestUIControlRejectionV1 { return error == expected }
    catch { return false }
}
func need<T>(_ value: T?, _ message: String) throws -> T {
    guard let value else { throw ReviewFailure(message) }; return value
}
func doc(_ revision: UInt64 = 1, label: String = "Save", action: String = "sample.save") -> UIDocument {
    UIDocument(revision: revision, root: UINode(id: "root", kind: .vStack, children: [
        UINode(id: "status", kind: .text, properties: ["text": .string("Ready")]),
        UINode(id: "save", kind: .button, properties: ["label": .string(label)],
            actions: [UIActionBinding(id: action, event: .activate)])]))
}
func bytes(_ document: UIDocument) throws -> Data { try GuestUICodec().encode(document) }
func exchange(_ generation: UInt64 = 7, confirmed: Bool = true) throws -> GuestUIExchangeV1 {
    let owner = try GuestUIExchangeV1(generation: generation)
    try owner.finishTurn(owner.claimStartup(), documentBytes: bytes(doc()))
    if confirmed {
        try owner.enterEffectsIntent(generation: generation)
        try owner.confirmEffectsEnabled(generation: generation)
    }
    return owner
}
func show(_ owner: GuestUIExchangeV1, _ reconciler: inout UIReconciler) throws -> GuestUIPresentationTicketV1 {
    let claim = try need(owner.claimPresentation(generation: owner.snapshot().generation), "no presentation")
    let frame = try need(claim.frame, "no frame")
    try reconciler.apply(frame.document.document)
    return try need(owner.completePresentation(claim, snapshot: reconciler.currentSnapshot()), "no ticket")
}
func envelope(_ reconciler: UIReconciler) throws -> UIEventEnvelope {
    let snapshot = try reconciler.currentSnapshot()
    return UIEventEnvelope(revision: snapshot.document.revision,
        identity: try need(snapshot.identity(for: "save"), "no button identity"), event: .activate)
}
func next(_ owner: GuestUIExchangeV1) throws -> GuestUITurnClaimV1 {
    try need(owner.claimNextTurn(ready: true), "no turn")
}

func rawCorpus() throws {
    let packet = #"{"schemaVersion":1,"sequence":1,"revision":1,"nodeID":"save","actionID":"sample.save","event":"activate","value":null}"#
    let lexemes = ["0", "-0", "-1", "+1", "01", "1.0", "1e0", "1E+0", "1e-0", "0x1", "NaN", "Infinity",
        "18446744073709551616", "184467440737095516150", "true", "null", #""1""#, "[]", "{}"]
    var rejected = 0
    for key in ["sequence", "revision"] {
        for raw in lexemes {
            let changed = packet.replacingOccurrences(of: "\"\(key)\":1", with: "\"\(key)\":\(raw)")
            try require(rejects { _ = try GuestUIEventCodecV1.decode(Data(changed.utf8)) }, "accepted numeric \(key)=\(raw)")
            rejected += 1
        }
    }
    for key in ["schemaVersion", "sequence", "revision", "nodeID", "actionID", "event", "value"] {
        let escaped = String(key.dropLast()) + "\\u" + String(format: "%04x", key.utf8.last!)
        let duplicate = String(packet.dropLast()) + ",\"\(escaped)\":null}"
        try require(rejects { _ = try GuestUIEventCodecV1.decode(Data(duplicate.utf8)) }, "accepted escaped duplicate \(key)")
        rejected += 1
    }
    let invalid = [packet + "\u{0000}", packet + "true", packet + ",", String(packet.dropLast()) + ",}",
        packet.replacingOccurrences(of: "\"save\"", with: #""\udc00""#),
        packet.replacingOccurrences(of: "\"save\"", with: #""\ud800x""#),
        packet.replacingOccurrences(of: "\"save\"", with: #""\u001f""#),
        packet.replacingOccurrences(of: "\"save\"", with: #""\u007f""#),
        packet.replacingOccurrences(of: "\"event\":\"activate\"", with: "\"event\":\"Activate\""),
        String(packet.dropLast()) + ",\"native_generation\":7}"]
    for input in invalid {
        try require(rejects { _ = try GuestUIEventCodecV1.decode(Data(input.utf8)) }, "accepted malformed/unknown packet")
        rejected += 1
    }
    for raw in [Data([0xef, 0xbb, 0xbf]) + Data(packet.utf8), Data([0xc0, 0xaf]), Data(repeating: 32, count: 4097)] {
        try require(rejects { _ = try GuestUIEventCodecV1.decode(raw) }, "accepted invalid UTF8/BOM/oversize")
        rejected += 1
    }
    for id in [String(repeating: "\"", count: 128), String(repeating: "\\", count: 128),
               String(repeating: "é", count: 64), String(repeating: "e\u{301}", count: 42), "emoji.🧪/漢字"] {
        let event = try GuestUIEventV1(sequence: .max, revision: .max, nodeID: id, actionID: id)
        let encoded = try GuestUIEventCodecV1.encode(event)
        let decoded = try GuestUIEventCodecV1.decode(encoded)
        try require(Array(decoded.nodeID.utf8) == Array(id.utf8) && Array(decoded.actionID.utf8) == Array(id.utf8), "ID bytes changed")
        try require(encoded.count <= 4096, "encoded worst escape bound exceeded")
        try require(!String(decoding: encoded, as: UTF8.self).contains(#"\/"#), "slash escaped")
    }
    print("DETAIL raw_rejections=\(rejected) boundary_roundtrips=5")
}

func staleAuthority() throws {
    let a = try exchange(), b = try exchange() // Deliberately reuse numeric generation and serials.
    let turnA = try next(a), turnB = try next(b)
    for target in [a, b] {
        let foreign = target === a ? turnB : turnA
        try require(localReject(.staleClaim) { try target.finishTurn(foreign, documentBytes: Data("{}".utf8)) }, "foreign malformed turn caused protocol failure")
        try require(localReject(.staleClaim) { try target.finishReadyWithoutInvocation(foreign) }, "foreign ready release accepted")
        try require(target.snapshot().stop == nil && target.snapshot().guestTurnInFlight, "foreign claim changed target")
    }
    try a.finishReadyWithoutInvocation(turnA)
    let later = try next(a)
    try require(localReject(.staleClaim) { try a.finishTurn(turnA, documentBytes: Data(repeating: 0, count: 65537)) }, "stale oversize turn stopped owner")
    try a.finishTurn(later, documentBytes: bytes(doc(2)))
    try b.finishReadyWithoutInvocation(turnB)
    var renderA = UIReconciler(), renderB = UIReconciler()
    let ticketA = try show(a, &renderA), ticketB = try show(b, &renderB)
    try require(!a.observePresentation(ticketB) && !b.observePresentation(ticketA), "foreign ticket earned receipt")
    let claimA = a.claimPresentation(generation: 7)
    try require(claimA == nil, "unexpected clean refresh")
    let pendingB = try next(b); try b.finishTurn(pendingB, documentBytes: bytes(doc(2)))
    let presentationB = try need(b.claimPresentation(generation: 7), "no B frame")
    try require(a.completePresentation(presentationB, snapshot: try renderA.currentSnapshot()) == nil, "foreign presentation completed")
    try require(a.snapshot().stop == nil && b.snapshot().presentationInFlight, "foreign presentation stole current slot")
    b.stop(.closed)
    try require(localReject(.closed) { try b.finishTurn(pendingB, documentBytes: bytes(doc(3))) }, "closed turn failed as protocol")
    try require(b.completePresentation(presentationB, snapshot: nil) == nil && b.snapshot().stop == .closed, "close completion altered cause")
}

func wholeDocumentEquality() throws {
    let composed = "caf\u{00e9}", decomposed = "cafe\u{0301}"
    let alternatives = [(doc(), doc(label: "Changed")), (doc(), doc(action: "changed.save")), (doc(), UIDocument(revision: 1,
        root: UINode(id: "different", kind: .text, properties: ["text": .string("Ready")]))),
        (doc(label: composed), doc(label: decomposed)), (doc(action: composed), doc(action: decomposed)),
        (UIDocument(revision: 1, root: UINode(id: composed, kind: .text, properties: ["text": .string("Ready")])),
         UIDocument(revision: 1, root: UINode(id: decomposed, kind: .text, properties: ["text": .string("Ready")]))),
        (UIDocument(revision: 1, root: UINode(id: "root", kind: .vStack, properties: ["spacing": .number(-0.0)])),
         UIDocument(revision: 1, root: UINode(id: "root", kind: .vStack, properties: ["spacing": .number(0.0)])))]
    for (expected, alternative) in alternatives {
        let owner = try GuestUIExchangeV1(generation: 7)
        try owner.finishTurn(owner.claimStartup(), documentBytes: bytes(expected))
        try owner.enterEffectsIntent(generation: 7); try owner.confirmEffectsEnabled(generation: 7)
        let claim = try need(owner.claimPresentation(generation: 7), "no candidate")
        var other = UIReconciler(); try other.apply(alternative)
        try require(owner.completePresentation(claim, snapshot: try other.currentSnapshot()) == nil, "same revision changed whole document accepted")
        try require(owner.snapshot().firstUIProtocolFailure?.failure.code == .presentationInvariant, "wrong mismatch classification")
    }
}

func framesReceiptsAndLag() throws {
    let owner = try exchange(); var renderer = UIReconciler()
    let initial = try show(owner, &renderer)
    try require(owner.observePresentation(initial), "initial receipt denied")
    let earned = try need(owner.snapshot().pendingPresentationReceipt, "no earned receipt")
    for revision in UInt64(2)...512 { try owner.finishTurn(next(owner), documentBytes: bytes(doc(revision))) }
    try require(owner.offer(try envelope(renderer), generation: 7) == .stale, "lagging display admitted input")
    let claim = try need(owner.claimPresentation(generation: 7), "no latest frame")
    try require(claim.frame?.document.document.revision == 512, "did not coalesce latest frame")
    try owner.finishTurn(next(owner), documentBytes: bytes(doc(513)))
    try renderer.apply(try need(claim.frame, "no 512 frame").document.document)
    let lagTicket = try need(owner.completePresentation(claim, snapshot: renderer.currentSnapshot()), "no lag ticket")
    try require(owner.observePresentation(lagTicket), "valid displayed lag frame denied receipt")
    try require(owner.snapshot().pendingPresentationReceipt == earned, "new document revoked earned receipt")
    _ = try show(owner, &renderer)
    owner.consumeObservedPresentation(generation: 8, frameSerial: earned.frameSerial)
    owner.consumeObservedPresentation(generation: 7, frameSerial: earned.frameSerial + 1)
    try require(owner.snapshot().pendingPresentationReceipt == earned, "wrong consume removed receipt")
    owner.consumeObservedPresentation(generation: 7, frameSerial: earned.frameSerial)
    try require(owner.snapshot().pendingPresentationReceipt == nil, "exact consume failed")
    let counters = owner.snapshot().counters
    try require(counters.producedFrames == 513 && counters.replacedPendingFrames == 510, "frame counters wrong")
    try require(counters.maximumPendingFrames == 1 && counters.maximumClaimedFrames == 1, "frame slot bound wrong")
    owner.stop(.closed)
    try require(!owner.observePresentation(initial) && owner.snapshot().pendingPresentationReceipt == nil, "stopped receipt retained")
}

func eventsAndRefresh() async throws {
    let owner = try exchange(); let reader = try owner.deliveryWake.takeConsumer()
    try require(try await reader.next(), "no first hint")
    var renderer = UIReconciler(); _ = try show(owner, &renderer)
    let event = try envelope(renderer)
    for sequence in UInt64(1)...32 {
        try require(owner.offer(event, generation: 7) == .accepted(sequence: sequence), "sequence not admitted")
        try require(try await reader.next(), "offer did not refresh controls")
        try require(owner.offer(event, generation: 7) == .busy, "accepted slot overwritten")
        let turn = try next(owner)
        guard case .event(let selected, let raw) = turn.kind else { throw ReviewFailure("wake overtook accepted event") }
        try require(selected == sequence && (try GuestUIEventCodecV1.decode(raw)).sequence == sequence, "wrong sequence wire")
        try owner.finishTurn(turn, documentBytes: bytes(doc()))
        try require(try await reader.next(), "same revision event did not refresh")
        let result = try need(owner.claimPresentation(generation: 7), "no result refresh")
        try require(result.frame == nil && result.eventResult?.outcome == .delivered, "result caused frame or wrong outcome")
        try require(owner.offer(event, generation: 7) == .busy, "result slot released before consume")
        _ = owner.completePresentation(result, snapshot: nil)
        try require(!owner.snapshot().eventOutstanding, "result slot not consumed")
        try require(try await reader.next(), "result consumption did not refresh controls")
    }
    owner.stop(.closed)
    try require(try await reader.next(), "no final retirement hint")
    try require(try await !reader.next(), "finished wake stayed live")
}

func unseenTerminalSurvivesOlderPresentationClaim() throws {
    for run in [false, true] {
        let owner = try exchange(); var renderer = UIReconciler(); _ = try show(owner, &renderer)
        try require(owner.offer(try envelope(renderer), generation: 7) == .accepted(sequence: 1), "event not admitted")
        if run { _ = try next(owner) }
        let beforeStop = try need(owner.claimPresentation(generation: 7), "no busy refresh")
        try require(beforeStop.frame == nil && beforeStop.eventResult == nil && beforeStop.stop == nil, "claim already observed a result")
        owner.stop(.closed)
        _ = owner.completePresentation(beforeStop, snapshot: nil)
        try require(owner.snapshot().eventOutstanding, "older result-free presentation claim consumed unseen terminal event run=\(run)")
        let final = try need(owner.claimPresentation(generation: 7), "no final stop claim")
        try require(final.stop == .closed && final.eventResult?.sequence == 1 && final.eventResult?.outcome == .terminal(turnBegan: run), "final claim lost terminal outcome run=\(run)")
        _ = owner.completePresentation(final, snapshot: nil)
        try require(!owner.snapshot().eventOutstanding, "final terminal result did not consume")
    }
    let delivered = try exchange(); var renderer = UIReconciler(); _ = try show(delivered, &renderer)
    try require(delivered.offer(try envelope(renderer), generation: 7) == .accepted(sequence: 1), "delivered event not admitted")
    try delivered.finishTurn(next(delivered), documentBytes: bytes(doc()))
    let oldOutcome = try need(delivered.claimPresentation(generation: 7), "no delivered-result claim")
    try require(oldOutcome.eventResult?.outcome == .delivered, "claim did not capture delivered result")
    delivered.stop(.closed)
    _ = delivered.completePresentation(oldOutcome, snapshot: nil)
    try require(delivered.snapshot().eventOutstanding, "delivered claim consumed changed unseen terminal outcome")
    let final = try need(delivered.claimPresentation(generation: 7), "no changed-outcome final claim")
    try require(final.eventResult?.outcome == .terminal(turnBegan: true), "changed terminal outcome lost")
    _ = delivered.completePresentation(final, snapshot: nil)
    try require(!delivered.snapshot().eventOutstanding, "changed terminal outcome did not consume")
}

final class RaceResult: @unchecked Sendable {
    let lock = NSLock()
    private var input: GuestUIEventAdmissionV1?
    private var turn: GuestUITurnClaimV1?
    func put(_ value: GuestUIEventAdmissionV1) { lock.lock(); input = value; lock.unlock() }
    func put(_ value: GuestUITurnClaimV1?) { lock.lock(); turn = value; lock.unlock() }
    func read() -> (GuestUIEventAdmissionV1?, GuestUITurnClaimV1?) {
        lock.lock(); defer { lock.unlock() }; return (input, turn)
    }
}
func arbitration() throws {
    var eventWins = 0, wakeWins = 0
    for iteration in 0..<256 {
        let owner = try exchange(); var renderer = UIReconciler(); _ = try show(owner, &renderer)
        let offered = try envelope(renderer), result = RaceResult()
        DispatchQueue.concurrentPerform(iterations: 2) { index in
            if index == iteration % 2 { result.put(owner.offer(offered, generation: 7)) }
            else { result.put(try? owner.claimNextTurn(ready: true)) }
        }
        let (input, claimed) = result.read()
        switch input {
        case .accepted?:
            let selected = try need(claimed ?? owner.claimNextTurn(ready: true), "accepted without next claim")
            guard case .event = selected.kind else { throw ReviewFailure("accepted input lost to wake") }
            eventWins += 1
        case .busy?:
            guard case .ready? = claimed?.kind else { throw ReviewFailure("busy without winning ready") }
            wakeWins += 1
        default: throw ReviewFailure("unexpected race admission")
        }
        owner.stop(.closed)
        let before = try exchange(confirmed: false)
        DispatchQueue.concurrentPerform(iterations: 2) { index in
            if index == 0 { try? before.enterEffectsIntent(generation: 7) }
            else { before.recordProtocolFailure(GuestUIProtocolFailureV1(phase: .startup, code: .header)) }
        }
        let state = before.snapshot()
        try require(state.firstUIProtocolFailure?.effectStage == (state.effectsMayHaveOpened ? .intentEntered : .beforeIntent), "intent/stop not linearized")
        try require(localReject(.closed) { try before.requireCommitEntry(generation: 7) }, "stopped commit allowed")
    }
    // Exercise both linearized orders deterministically, independently of which
    // queue receives CPU first in the contended trials.
    let wakeFirst = try exchange(); var renderWake = UIReconciler(); _ = try show(wakeFirst, &renderWake)
    let held = try next(wakeFirst)
    try require(wakeFirst.offer(try envelope(renderWake), generation: 7) == .busy, "claimed wake did not block input")
    try wakeFirst.finishReadyWithoutInvocation(held)
    try require(wakeFirst.offer(try envelope(renderWake), generation: 7) == .accepted(sequence: 1), "no-op wake did not release input")
    let eventNext = try next(wakeFirst)
    guard case .event = eventNext.kind else { throw ReviewFailure("event-first order selected wake") }
    print("DETAIL arbitration_iterations=256 event_wins=\(eventWins) wake_wins=\(wakeWins)")
}

func wakeLifetime() async throws {
    let owner = try GuestUIExchangeV1(generation: 1)
    let source = owner.deliveryWake, reader = try source.takeConsumer()
    try require(localReject(.consumerAlreadyIssued) { _ = try source.takeConsumer() }, "second consumer issued")
    for _ in 0..<65536 { source.signal() }
    source.finish()
    try require(try await reader.next(), "coalesced final hint lost")
    try require(try await !reader.next(), "signals did not coalesce")
    let control = try owner.coordinatorWake.takeConsumer()
    owner.stop(.closed)
    try require(try await control.next(), "stop control hint absent")
    owner.coordinatorWake.signal()
    try require(try await control.next(), "exchange prematurely finished control wake")
    owner.coordinatorWake.finish()
    try require(try await !control.next(), "control did not finish")
#if REVIEW_INTERNALS
    let parked = try GuestUIExchangeV1(generation: 2)
    let one = try parked.deliveryWake.takeConsumer()
    let task = Task { try await one.next() }
    for _ in 0..<10000 {
        if parked.deliveryWake.hasWaitingConsumer { break }
        await Task.yield()
    }
    try require(parked.deliveryWake.hasWaitingConsumer, "waiter failed to park")
    do { _ = try await one.next(); throw ReviewFailure("second simultaneous waiter admitted") }
    catch let rejection as GuestUIControlRejectionV1 { try require(rejection == .readerBusy, "wrong extra waiter rejection") }
    task.cancel()
    try require(parked.deliveryWake.hasWaitingConsumer, "cancel discarded parked continuation")
    parked.deliveryWake.signal()
    try require(try await task.value, "cancel lost signal")
    parked.deliveryWake.finish()
    try require(try await !one.next(), "parked source did not finish")
#endif
}

@main struct ExchangeAdversarialProbe {
    static func main() async {
        var failures = 0
        let syncCases: [(String, () throws -> Void)] = [
            ("raw-closed-json", rawCorpus), ("exact-issuer-stale-close", staleAuthority),
            ("whole-document-mismatch", wholeDocumentEquality), ("fixed-frames-earned-receipt-lag", framesReceiptsAndLag),
            ("shared-guard-arbitration", arbitration), ("unseen-terminal-result-retention", unseenTerminalSurvivesOlderPresentationClaim)]
        for (name, body) in syncCases {
            do { try body(); print("PASS \(name)") }
            catch { failures += 1; print("FAIL \(name): \(error)") }
        }
        for (name, body) in [("single-event-through-consumption-refresh", eventsAndRefresh), ("wake-lifetime", wakeLifetime)] {
            do { try await body(); print("PASS \(name)") }
            catch { failures += 1; print("FAIL \(name): \(error)") }
        }
        print("RESULT groups=8 failures=\(failures)")
        if failures != 0 { exit(1) }
    }
}
