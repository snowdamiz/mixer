import Dispatch
import Foundation
import Testing
import MixerUI
@_spi(GuestUIV1) @testable import MixerGuest

private func guestDocument(_ revision: UInt64 = 1, text: String = "Ready") -> Data {
    // Original protocol fixture, independently authored from UI encoder output.
    Data("{\"schemaVersion\":1,\"revision\":\(revision),\"root\":{\"id\":\"root\",\"kind\":\"vStack\",\"properties\":{},\"actions\":[],\"children\":[{\"id\":\"status\",\"kind\":\"text\",\"properties\":{\"text\":\"\(text)\"},\"children\":[],\"actions\":[]},{\"id\":\"save\",\"kind\":\"button\",\"properties\":{\"label\":\"Save sample\"},\"children\":[],\"actions\":[{\"id\":\"sample.save\",\"event\":\"activate\"}]}]}}".utf8)
}
private func startedGuestExchange(_ generation: UInt64 = 7, confirm: Bool = true) throws -> GuestUIExchangeV1 {
    let exchange = try GuestUIExchangeV1(generation: generation)
    let claim = try exchange.claimStartup(); try exchange.finishTurn(claim, documentBytes: guestDocument())
    if confirm { try exchange.enterEffectsIntent(generation: generation); try exchange.confirmEffectsEnabled(generation: generation) }
    return exchange
}
private func presentGuestFrame(_ exchange: GuestUIExchangeV1, _ reconciler: inout UIReconciler) throws -> GuestUIPresentationTicketV1 {
    let claim = try #require(exchange.claimPresentation(generation: exchange.snapshot().generation))
    let frame = try #require(claim.frame)
    try reconciler.apply(frame.document.document)
    return try #require(exchange.completePresentation(claim, snapshot: reconciler.currentSnapshot()))
}
private func saveEnvelope(_ reconciler: UIReconciler) throws -> UIEventEnvelope {
    let snapshot = try reconciler.currentSnapshot()
    return UIEventEnvelope(revision: snapshot.document.revision, identity: try #require(snapshot.identity(for: "save")), event: .activate)
}

@Test func guestUIExchangeRequiresStartupAndActualConfirmationBeforePresentation() throws {
    let exchange = try GuestUIExchangeV1(generation: 7)
    try exchange.requireCommitEntry(generation: 7)
    #expect(throws: GuestUIControlRejectionV1.busy) { try exchange.enterEffectsIntent(generation: 7) }
    #expect(throws: GuestUIControlRejectionV1.busy) { try exchange.requireEffectAdmission(generation: 7) }
    let startup = try exchange.claimStartup()
    #expect(throws: GuestUIControlRejectionV1.busy) { try exchange.claimStartup() }
    try exchange.finishTurn(startup, documentBytes: guestDocument())
    #expect(exchange.claimPresentation(generation: 7) == nil)
    try exchange.enterEffectsIntent(generation: 7)
    #expect(exchange.snapshot().effectsMayHaveOpened)
    #expect(!exchange.snapshot().effectsConfirmed)
    #expect(exchange.claimPresentation(generation: 7) == nil)
    try exchange.confirmEffectsEnabled(generation: 7)
    try exchange.requireEffectAdmission(generation: 7)
    var reconciler = UIReconciler()
    let ticket = try presentGuestFrame(exchange, &reconciler)
    #expect(exchange.observePresentation(ticket))
    #expect(exchange.snapshot().pendingPresentationReceipt?.revision == 1)
    exchange.consumeObservedPresentation(generation: 7, frameSerial: ticket.frameSerial)
    #expect(exchange.snapshot().pendingPresentationReceipt == nil)
}

@Test func guestUIExchangeDocumentsAreStrictBoundedAndByteRevisionAware() throws {
    let invalid = [guestDocument(0), guestDocument().replacingBytes("vStack", with: "hStack"),
                   guestDocument().replacingBytes("Ready", with: String(repeating: "x", count: 4097)),
                   Data(repeating: 32, count: 65537), Data("{}".utf8)]
    for bytes in invalid {
        let exchange = try GuestUIExchangeV1(generation: 1)
        let startup = try exchange.claimStartup()
        #expect(throws: GuestUIProtocolFailureV1(phase: .startup, code: .document)) {
            try exchange.finishTurn(startup, documentBytes: bytes)
        }
        #expect(exchange.snapshot().firstUIProtocolFailure?.effectStage == .beforeIntent)
        #expect(!exchange.snapshot().effectsMayHaveOpened)
    }
    let same = try startedGuestExchange()
    let wake = try #require(try same.claimNextTurn(ready: true))
    try same.finishTurn(wake, documentBytes: guestDocument())
    #expect(same.snapshot().counters.producedFrames == 1)
    #expect(same.snapshot().counters.successfulTurns == 2)
    let changed = try #require(try same.claimNextTurn(ready: true))
    #expect(throws: GuestUIProtocolFailureV1(phase: .wake, code: .sameRevisionMutation)) {
        try same.finishTurn(changed, documentBytes: Data(" ".utf8) + guestDocument())
    }
    #expect(same.snapshot().firstUIProtocolFailure?.effectStage == .intentEntered)
    let lower = try startedGuestExchange()
    let second = try #require(try lower.claimNextTurn(ready: true)); try lower.finishTurn(second, documentBytes: guestDocument(2))
    let third = try #require(try lower.claimNextTurn(ready: true))
    #expect(throws: GuestUIProtocolFailureV1(phase: .wake, code: .revisionRegressed)) {
        try lower.finishTurn(third, documentBytes: guestDocument(1))
    }
}

@Test func guestUIExchangeLatestFrameSlotAllowsOneClaimAndOnePendingFrame() throws {
    let exchange = try startedGuestExchange()
    for revision in 2...100 {
        let turn = try #require(try exchange.claimNextTurn(ready: true))
        try exchange.finishTurn(turn, documentBytes: guestDocument(UInt64(revision)))
    }
    let claim = try #require(exchange.claimPresentation(generation: 7))
    #expect(claim.frame?.document.document.revision == 100)
    #expect(exchange.claimPresentation(generation: 7) == nil)
    let turn = try #require(try exchange.claimNextTurn(ready: true)); try exchange.finishTurn(turn, documentBytes: guestDocument(101))
    var reconciler = UIReconciler(); try reconciler.apply(try #require(claim.frame).document.document)
    let ticket100 = try #require(exchange.completePresentation(claim, snapshot: reconciler.currentSnapshot()))
    #expect(exchange.offer(try saveEnvelope(reconciler), generation: 7) == .stale)
    #expect(exchange.observePresentation(ticket100))
    let ticket101 = try presentGuestFrame(exchange, &reconciler)
    #expect(!exchange.observePresentation(ticket100))
    #expect(exchange.observePresentation(ticket101))
    #expect(exchange.snapshot().pendingPresentationReceipt?.revision == 100) // Already earned receipt survives newer frames.
    #expect(exchange.snapshot().counters.maximumPendingFrames == 1)
    #expect(exchange.snapshot().counters.maximumClaimedFrames == 1)
    #expect(exchange.snapshot().counters.replacedPendingFrames == 99)
}

@Test func guestUIExchangeEnforcesNodeDepthAndChildrenBoundaries() throws {
    func leaf(_ id: String) -> String {
        "{\"id\":\"\(id)\",\"kind\":\"text\",\"properties\":{\"text\":\"x\"},\"children\":[],\"actions\":[]}"
    }
    func stack(_ id: String, _ children: [String]) -> String {
        "{\"id\":\"\(id)\",\"kind\":\"vStack\",\"properties\":{},\"children\":[\(children.joined(separator: ","))],\"actions\":[]}"
    }
    func bytes(_ root: String) -> Data { Data("{\"schemaVersion\":1,\"revision\":1,\"root\":\(root)}".utf8) }
    func accepts(_ root: String) throws -> Bool {
        let exchange = try GuestUIExchangeV1(generation: 1)
        let claim = try exchange.claimStartup()
        do { try exchange.finishTurn(claim, documentBytes: bytes(root)); return true }
        catch let failure as GuestUIProtocolFailureV1 { #expect(failure.code == .document); return false }
    }
    var deep = leaf("leaf")
    for index in 0..<15 { deep = stack("depth.\(index)", [deep]) }
    #expect(try accepts(deep))
    #expect(try !accepts(stack("too.deep", [deep])))
    #expect(try accepts(stack("wide", (0..<64).map { leaf("wide.\($0)") })))
    #expect(try !accepts(stack("wide", (0..<65).map { leaf("wide.\($0)") })))
    let groups = (0..<4).map { group in
        stack("group.\(group)", (0..<(group == 0 ? 62 : 63)).map { leaf("g.\(group).\($0)") })
    }
    #expect(try accepts(stack("all", groups))) // 251 leaves + 5 containers = 256.
    let over = groups + [leaf("extra")]
    #expect(try !accepts(stack("all", over)))
}

@Test func guestUIExchangeDoesNotPublishForeignOrMismatchedPresentationReceipts() throws {
    let exchange = try startedGuestExchange(), other = try startedGuestExchange()
    let claim = try #require(exchange.claimPresentation(generation: 7))
    var foreignReconciler = UIReconciler()
    try foreignReconciler.apply(GuestUICodec().decode(guestDocument(2)).document)
    let foreignClaim = try #require(other.claimPresentation(generation: 7))
    #expect(exchange.completePresentation(foreignClaim, snapshot: try foreignReconciler.currentSnapshot()) == nil)
    #expect(exchange.snapshot().stop == nil)
    #expect(exchange.snapshot().presentationInFlight)
    #expect(exchange.completePresentation(claim, snapshot: try foreignReconciler.currentSnapshot()) == nil)
    #expect(exchange.snapshot().firstUIProtocolFailure?.failure == GuestUIProtocolFailureV1(phase: .presentation, code: .presentationInvariant))
    #expect(exchange.snapshot().pendingPresentationReceipt == nil)
}

@Test func guestUIExchangeAdmissionAndResultConsumptionRefreshWithoutNewFrame() async throws {
    let exchange = try startedGuestExchange(); let reader = try exchange.deliveryWake.takeConsumer()
    #expect(try await reader.next())
    var reconciler = UIReconciler(); _ = try presentGuestFrame(exchange, &reconciler)
    #expect(exchange.offer(try saveEnvelope(reconciler), generation: 7) == .accepted(sequence: 1))
    #expect(try await reader.next())
    let busyRefresh = try #require(exchange.claimPresentation(generation: 7))
    #expect(busyRefresh.frame == nil && busyRefresh.eventResult == nil)
    #expect(exchange.completePresentation(busyRefresh, snapshot: nil) == nil)
    let event = try #require(try exchange.claimNextTurn(ready: false))
    try exchange.finishTurn(event, documentBytes: guestDocument()) // Delivery but no new revision.
    #expect(try await reader.next())
    let result = try #require(exchange.claimPresentation(generation: 7))
    #expect(result.frame == nil && result.eventResult?.outcome == .delivered)
    #expect(exchange.completePresentation(result, snapshot: nil) == nil)
    #expect(!exchange.snapshot().eventOutstanding)
    #expect(try await reader.next()) // Result consumption itself signals controls.
    exchange.stop(.closed)
}

@Test func guestUIExchangePreservesAcceptedEventUntilResultConsumption() throws {
    let exchange = try startedGuestExchange(); var reconciler = UIReconciler()
    _ = try presentGuestFrame(exchange, &reconciler)
    let envelope = try saveEnvelope(reconciler)
    #expect(exchange.offer(envelope, generation: 7) == .accepted(sequence: 1))
    #expect(exchange.offer(envelope, generation: 7) == .busy)
    let event = try #require(try exchange.claimNextTurn(ready: true))
    guard case let .event(sequence, bytes) = event.kind else { Issue.record("accepted event was overtaken by wake"); return }
    #expect(sequence == 1)
    #expect(try GuestUIEventCodecV1.decode(bytes).actionID == "sample.save")
    try exchange.finishTurn(event, documentBytes: guestDocument(2, text: "Saving sample"))
    #expect(exchange.offer(envelope, generation: 7) == .busy)
    let delivery = try #require(exchange.claimPresentation(generation: 7))
    #expect(delivery.eventResult?.outcome == .delivered)
    #expect(exchange.snapshot().eventOutstanding)
    try reconciler.apply(try #require(delivery.frame).document.document)
    #expect(exchange.completePresentation(delivery, snapshot: try reconciler.currentSnapshot()) != nil)
    #expect(!exchange.snapshot().eventOutstanding)
    #expect(exchange.offer(try saveEnvelope(reconciler), generation: 7) == .accepted(sequence: 2))
    #expect(exchange.snapshot().counters.maximumEventSlots == 1)
    #expect(exchange.snapshot().counters.maximumEventBytes <= 4096)
}

@Test func guestUIExchangeNoopWakeAndForeignClaimsNeverPublishOrStopAnotherOwner() throws {
    let exchange = try startedGuestExchange(); var reconciler = UIReconciler()
    let ticket = try presentGuestFrame(exchange, &reconciler)
    let wake = try #require(try exchange.claimNextTurn(ready: true))
    #expect(exchange.offer(try saveEnvelope(reconciler), generation: 7) == .busy)
    try exchange.finishReadyWithoutInvocation(wake)
    #expect(exchange.snapshot().counters.successfulTurns == 1)
    #expect(throws: GuestUIControlRejectionV1.staleClaim) { try exchange.finishReadyWithoutInvocation(wake) }
    let other = try startedGuestExchange(); let foreign = try #require(try other.claimNextTurn(ready: true))
    #expect(throws: GuestUIControlRejectionV1.staleClaim) { try exchange.finishTurn(foreign, documentBytes: guestDocument(2)) }
    #expect(!other.observePresentation(ticket))
    #expect(exchange.snapshot().stop == nil && other.snapshot().stop == nil)
    #expect(exchange.offer(try saveEnvelope(reconciler), generation: 8) == .stale)
    #expect(exchange.offer(UIEventEnvelope(revision: 1, identity: UINodeIdentity(id: "save", generation: .max), event: .activate), generation: 7) == .invalid(.staleIdentity))
    #expect(exchange.snapshot().counters.acceptedEvents == 0)
}

@Test func guestUIExchangeCloseRacesPreserveFirstCauseAndRetirePresentation() throws {
    for runEvent in [false, true] {
        let exchange = try startedGuestExchange(); var reconciler = UIReconciler()
        let ticket = try presentGuestFrame(exchange, &reconciler)
        #expect(exchange.observePresentation(ticket))
        #expect(exchange.offer(try saveEnvelope(reconciler), generation: 7) == .accepted(sequence: 1))
        let running = runEvent ? try exchange.claimNextTurn(ready: true) : nil
        exchange.stop(.closed)
        #expect(exchange.snapshot().stop == .closed)
        #expect(!exchange.observePresentation(ticket))
        #expect(exchange.snapshot().pendingPresentationReceipt == nil)
        if let running {
            #expect(throws: GuestUIControlRejectionV1.closed) { try exchange.finishTurn(running, documentBytes: guestDocument(2)) }
        }
        let retirement = try #require(exchange.claimPresentation(generation: 7))
        #expect(retirement.frame == nil)
        #expect(retirement.eventResult?.outcome == .terminal(turnBegan: runEvent))
        #expect(exchange.completePresentation(retirement, snapshot: nil) == nil)
        #expect(!exchange.snapshot().eventOutstanding)
        exchange.recordProtocolFailure(GuestUIProtocolFailureV1(phase: .wake, code: .document))
        #expect(exchange.snapshot().stop == .closed)
        #expect(exchange.snapshot().firstUIProtocolFailure?.effectStage == .intentEntered)
    }
    let exchange = try startedGuestExchange()
    let claim = try #require(exchange.claimPresentation(generation: 7))
    var reconciler = UIReconciler(); try reconciler.apply(try #require(claim.frame).document.document)
    exchange.stop(.cancelled)
    #expect(exchange.completePresentation(claim, snapshot: try reconciler.currentSnapshot()) == nil)
    #expect(!exchange.snapshot().presentationInFlight)
    #expect(exchange.snapshot().displayedRevision == nil)
}

private final class GuestUIRaceResults: @unchecked Sendable {
    let lock = NSLock()
    var admission: GuestUIEventAdmissionV1?
    var claim: GuestUITurnClaimV1?
    func set(_ value: GuestUIEventAdmissionV1) { lock.lock(); admission = value; lock.unlock() }
    func set(_ value: GuestUITurnClaimV1?) { lock.lock(); claim = value; lock.unlock() }
}

@Test func guestUIExchangeConcurrentEventWakeAndIntentStopUseOneAuthority() throws {
    for _ in 0..<64 {
        let exchange = try startedGuestExchange(); var reconciler = UIReconciler()
        _ = try presentGuestFrame(exchange, &reconciler); let envelope = try saveEnvelope(reconciler)
        let results = GuestUIRaceResults()
        DispatchQueue.concurrentPerform(iterations: 2) { index in
            if index == 0 { results.set(exchange.offer(envelope, generation: 7)) }
            else { results.set(try? exchange.claimNextTurn(ready: true)) }
        }
        if case .accepted? = results.admission {
            let selected = try (results.claim ?? exchange.claimNextTurn(ready: true))
            let claim = try #require(selected)
            guard case .event = claim.kind else { Issue.record("wake overtook an accepted event"); return }
        } else {
            #expect(results.admission == .busy)
            guard case .ready? = results.claim?.kind else { Issue.record("busy event without winning wake"); return }
        }
        exchange.stop(.closed)
        let beforeIntent = try startedGuestExchange(confirm: false)
        DispatchQueue.concurrentPerform(iterations: 2) { index in
            if index == 0 { try? beforeIntent.enterEffectsIntent(generation: 7) }
            else { beforeIntent.recordProtocolFailure(GuestUIProtocolFailureV1(phase: .startup, code: .header)) }
        }
        let state = beforeIntent.snapshot()
        #expect(state.firstUIProtocolFailure?.effectStage == (state.effectsMayHaveOpened ? .intentEntered : .beforeIntent))
        #expect(throws: GuestUIControlRejectionV1.closed) { try beforeIntent.requireCommitEntry(generation: 7) }
    }
}

private extension Data {
    func replacingBytes(_ before: String, with after: String) -> Data {
        Data(String(decoding: self, as: UTF8.self).replacingOccurrences(of: before, with: after).utf8)
    }
}

@Test func guestUIExchangeRejectsCanonicalUnicodeSnapshotSubstitution() throws {
    let original = "caf\u{00e9}", changed = "cafe\u{0301}"
    #expect(original == changed)
    #expect(!original.utf8.elementsEqual(changed.utf8))
    for field in ["node", "action", "label", "unchanged"] {
        func document(changedSnapshot: Bool) -> UIDocument {
            UIDocument(revision: 1, root: UINode(
                id: changedSnapshot && field == "node" ? changed : original, kind: .button,
                properties: ["label": .string(changedSnapshot && field == "label" ? changed : original)],
                actions: [.init(id: changedSnapshot && field == "action" ? changed : original, event: .activate)]))
        }
        let exchange = try GuestUIExchangeV1(generation: 1)
        try exchange.finishTurn(exchange.claimStartup(), documentBytes: GuestUICodec().encode(document(changedSnapshot: false)))
        try exchange.enterEffectsIntent(generation: 1); try exchange.confirmEffectsEnabled(generation: 1)
        let claim = try #require(exchange.claimPresentation(generation: 1))
        var reconciler = UIReconciler(); try reconciler.apply(document(changedSnapshot: true))
        let snapshot = try reconciler.currentSnapshot()
        let ticket = exchange.completePresentation(claim, snapshot: snapshot)
        if field == "unchanged" {
            #expect(ticket != nil); #expect(exchange.snapshot().stop == nil)
        } else {
            #expect(ticket == nil)
            #expect(exchange.snapshot().firstUIProtocolFailure?.failure == .init(phase: .presentation, code: .presentationInvariant))
            #expect(exchange.snapshot().displayedRevision == nil)
            let id = field == "node" ? changed : original
            let event = UIEventEnvelope(revision: 1, identity: try #require(snapshot.identity(for: id)), event: .activate)
            #expect(exchange.offer(event, generation: 1) == .closed)
        }
    }
}

@Test func guestUIExchangeStopCannotConsumeAnUnseenOrChangedEventResult() throws {
    for phase in ["queued", "running", "delivered"] {
        let exchange = try startedGuestExchange()
        var reconciler = UIReconciler(); _ = try presentGuestFrame(exchange, &reconciler)
        #expect(exchange.offer(try saveEnvelope(reconciler), generation: 7) == .accepted(sequence: 1))
        if phase != "queued" {
            let turn = try #require(try exchange.claimNextTurn(ready: false))
            if phase == "delivered" { try exchange.finishTurn(turn, documentBytes: guestDocument()) }
        }
        let beforeStop = try #require(exchange.claimPresentation(generation: 7))
        if phase == "delivered" { #expect(beforeStop.eventResult?.outcome == .delivered) }
        else { #expect(beforeStop.eventResult == nil) }
        exchange.stop(.closed)
        #expect(exchange.completePresentation(beforeStop, snapshot: nil) == nil)
        #expect(exchange.snapshot().eventOutstanding)
        let retirement = try #require(exchange.claimPresentation(generation: 7))
        #expect(retirement.eventResult?.sequence == 1)
        #expect(retirement.eventResult?.outcome == .terminal(turnBegan: phase != "queued"))
        #expect(exchange.completePresentation(retirement, snapshot: nil) == nil)
        #expect(!exchange.snapshot().eventOutstanding)
    }
}
