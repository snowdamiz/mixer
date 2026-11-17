#if canImport(Crypto)
import Foundation
import Testing
@testable import MixerUI
@_spi(FeatureUIV3) @_spi(GuestUIV1) @testable import MixerGuest

private enum PolicyFailure: Error { case acquire, frame, event, close }
private let policyPacket = Data("abc".utf8)
private let policyHash = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
private func policyDocument(_ revision: UInt64 = 1, _ text: String = "Draft") -> UIDocument {
    UIDocument(revision: revision, root: UINode(id: "task.title", kind: .textField,
        properties: ["label": .string("Title"), "value": .string(text), "axis": .string("vertical")],
        actions: [UIActionBinding(id: "task.title.change", event: .textChange)]))
}
private func policyGrant(_ hash: String = policyHash) -> ReviewedDevelopmentGrant {
    ReviewedDevelopmentGrant(artifactSHA256: hash,
        surfaceKinds: FeatureDocumentV3(textValuePolicy: .standard).validator.supportedKinds, executionProfile: .development256)
}
@MainActor private final class PolicyAuthority: SwiftFeatureCleanupAuthority {}
/// Policy-only doubles. No VM, frontend, process, device or database resource.
@MainActor private final class PolicyOwner: SwiftFeatureRuntimeOwner {
    var bytes: Data
    var replies: [Data] = []
    var values: [String] = []
    var frameFailure = false
    var eventFailure = false
    var eventError: (any Error)?
    var frameError: (any Error)?
    var onEvent: (() -> Void)?
    var onFrame: (() -> Void)?
    var frameCalls = 0
    var consumeCalls = 0
    var consumption = SwiftFeatureConsumption.reportedClosed(.init(currents: Array(repeating: 0, count: 14), tickets: 0, invariant: 0))
    init() throws { bytes = try FeatureDocumentV3(textValuePolicy: .standard).encode(policyDocument()) }
    func frame() throws -> Data {
        frameCalls += 1; onFrame?()
        if let frameError { throw frameError }
        if frameFailure { throw PolicyFailure.frame }; return bytes
    }
    func event(_ bytes: Data) throws {
        if let eventError { throw eventError }
        if eventFailure { throw PolicyFailure.event }
        let object = try JSONSerialization.jsonObject(with: bytes) as! [String: Any]
        values.append(object["value"] as! String)
        onEvent?()
        if !replies.isEmpty { self.bytes = replies.removeFirst() }
    }
    func consume() -> SwiftFeatureConsumption {
        consumeCalls += 1; let report = consumption
        consumption = .reportedClosed(.init(currents: Array(repeating: 0, count: 14), tickets: 0, invariant: 0))
        return report
    }
}
@MainActor private final class PolicyFactory: SwiftFeatureRuntimeFactory {
    var owner: PolicyOwner?
    var calls = 0
    var refusal = false
    var partial = false
    var onAcquire: (() -> Void)?
    init(_ owner: PolicyOwner) { self.owner = owner }
    func acquire(_ request: SwiftFeatureRuntimeRequest) -> SwiftFeatureAcquisition {
        calls += 1; onAcquire?()
        if refusal { return .refused(PolicyFailure.acquire) }
        if partial { return .failedOwned(owner!, cause: PolicyFailure.acquire) }
        return .ready(owner!)
    }
}
@MainActor private final class PolicyGate {
    private var open = false
    private var continuation: CheckedContinuation<Void, Never>?
    func wait() async { if open { return }; await withCheckedContinuation { continuation = $0 } }
    func release() { open = true; continuation?.resume(); continuation = nil }
}
@MainActor private final class PolicyPresenter: SwiftFeatureNativePresenter {
    var router: UINativeActionRouter?
    var calls = 0
    var onPresent: (() -> Void)?
    var gate: PolicyGate?
    var previous: NativeDisplayAcknowledgement?
    var returnPrevious = false
    func present(_ request: NativePresentationRequest) async throws -> NativeDisplayAcknowledgement {
        calls += 1
        if let router { try router.update(request.document.document) }
        else { router = try UINativeActionRouter(document: request.document.document, validator: FeatureDocumentV3(textValuePolicy: .standard).validator) }
        onPresent?()
        if let gate { await gate.wait() } // Deliberately uncooperative cancellation policy control.
        if returnPrevious, let previous { return previous }
        let ack = request.acknowledgement(snapshot: try router!.snapshot)
        previous = ack; return ack
    }
    func issue(_ value: String) throws -> IssuedUIAction {
        let router = try #require(router), snapshot = try router.snapshot
        return try router.route(UIEventEnvelope(revision: snapshot.document.revision,
            identity: try #require(snapshot.identity(for: "task.title")), event: .textChange, value: .string(value)))
    }
}
@MainActor private struct PolicyHarness {
    let scope = SwiftFeatureOwnershipScope()
    let owner: PolicyOwner
    let presenter = PolicyPresenter()
    let factory: PolicyFactory
    init() throws { owner = try PolicyOwner(); factory = PolicyFactory(owner) }
    func mount() async throws { _ = try await scope.mount(policyPacket, grant: policyGrant(), backend: factory, presenter: presenter) }
    func ticket(_ text: String) throws -> SwiftFeatureActionTicket {
        guard case .accepted(let ticket) = scope.submit(try presenter.issue(text)) else { throw SwiftFeatureError.input }
        return ticket
    }
    func finish() async throws -> SwiftFeatureScopeResult {
        try await scope.finish(.ownerRequested, teardown: { _ in }).outcome()
    }
}
@MainActor private func spin(_ condition: () -> Bool) async {
    for _ in 0..<4000 { if condition() { return }; await Task.yield() }
    #expect(condition())
}

@Suite(.serialized) struct SwiftFeaturePolicyTests {
    @Test @MainActor func synchronousEventRetirementPreventsReplyFrameAndPresentation() async throws {
        let h = try PolicyHarness(); try await h.mount()
        h.owner.replies = [try FeatureDocumentV3(textValuePolicy: .standard).encode(policyDocument(2, "new"))]
        var retirement: SwiftFeatureRetirementTicket?
        var teardowns = 0
        h.owner.onEvent = {
            retirement = h.scope.finish(.cancelled) { _ in teardowns += 1 }
        }
        let active = try h.ticket("new")
        guard case .terminal(let result) = try await active.outcome() else {
            Issue.record("synchronous retirement acknowledged a reply"); _ = try await h.finish(); return
        }
        _ = try await #require(retirement).outcome()
        #expect(result.primaryError is CancellationError)
        #expect(h.owner.values == ["new"] && h.owner.replies.isEmpty)
        #expect(h.owner.frameCalls == 1 && h.presenter.calls == 1)
        #expect(h.owner.consumeCalls == 1 && teardowns == 1)
        h.owner.onEvent = nil
    }
    @Test @MainActor func synchronousInitialFrameRetirementNeverStartsPresentation() async throws {
        let h = try PolicyHarness()
        var retirement: SwiftFeatureRetirementTicket?
        var teardowns = 0
        h.owner.onFrame = {
            retirement = h.scope.finish(.cancelled) { _ in teardowns += 1 }
        }
        do { try await h.mount(); Issue.record("retired initial frame mounted") } catch {}
        let result = try await #require(retirement).outcome()
        #expect(result.primaryError is CancellationError)
        #expect(h.owner.frameCalls == 1 && h.presenter.calls == 0)
        #expect(h.owner.values.isEmpty && h.owner.consumeCalls == 1 && teardowns == 1)
        h.owner.onFrame = nil
    }
    @Test @MainActor func retiredStartupLateAcknowledgementCannotAdmitEffectsOrCommitSnapshot() async throws {
        let owner = try PolicyOwner(), presenter = PolicyPresenter(), gate = PolicyGate()
        let (exchange, startup) = try SwiftFeatureSession.prepare(policyPacket, grant: policyGrant())
        let session = SwiftFeatureSession(exchange: exchange, startup: startup,
            lease: SwiftFeatureLease(owner), presenter: presenter)
        presenter.gate = gate
        let start = Task { @MainActor in try await session.start() }
        await spin { presenter.calls == 1 }
        session.cancelPresentation()
        #expect(owner.consumeCalls == 0)
        #expect(throws: GuestUIControlRejectionV1.busy) { try exchange.requireEffectAdmission(generation: 1) }
        gate.release()
        do { _ = try await start.value; Issue.record("late acknowledgement returned a snapshot") }
        catch is CancellationError {}
        #expect(throws: GuestUIControlRejectionV1.busy) { try exchange.requireEffectAdmission(generation: 1) }
        #expect(exchange.snapshot().displayedRevision == nil)
        #expect(exchange.snapshot().pendingPresentationReceipt == nil)
        do { _ = try await session.start(); Issue.record("retired session restarted") }
        catch is CancellationError {}
        do { _ = try await session.send(presenter.issue("late")); Issue.record("retired session dispatched") }
        catch is CancellationError {}
        #expect(owner.frameCalls == 1 && owner.values.isEmpty && presenter.calls == 1)
        guard case .clean(let ledger) = session.consume() else { Issue.record("clean policy close lost"); return }
        try ledger.requireFourteenZeroCurrentsAndNoTicketsOrInvariant()
        _ = session.consume()
        #expect(owner.consumeCalls == 1)
    }
    @Test @MainActor func standardHashVectorsAndRefusalBeforeAcquire() async throws {
        #expect(SwiftFeatureSession.artifactDigest(Data()) == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        #expect(SwiftFeatureSession.artifactDigest(policyPacket) == policyHash)
        for packet in [Data(), policyPacket] {
            let h = try PolicyHarness()
            do { _ = try await h.scope.mount(packet, grant: policyGrant("bad"), backend: h.factory, presenter: h.presenter); Issue.record("invalid admission") }
            catch SwiftFeatureError.grant {}
            #expect(h.factory.calls == 0 && h.owner.consumeCalls == 0)
        }
        let h = try PolicyHarness()
        let cancelled = Task { @MainActor in try Task.checkCancellation(); try await h.mount() }
        cancelled.cancel()
        do { try await cancelled.value; Issue.record("cancelled admission") } catch is CancellationError {}
        #expect(h.factory.calls == 0)
    }
    @Test @MainActor func refusalAndPartialOwnershipSettleExactlyOnce() async throws {
        for partial in [false, true] {
            let h = try PolicyHarness(); h.factory.partial = partial; h.factory.refusal = !partial
            do { try await h.mount(); Issue.record("expected acquisition failure") } catch {}
            var teardowns: [SwiftFeatureFrontendRequest] = []
            let a = h.scope.finish(.ownerRequested) { teardowns.append($0) }
            let b = h.scope.finish(.cancelled) { teardowns.append($0) }
            #expect(a === b)
            let result = try await a.outcome()
            #expect(result.primaryError is PolicyFailure)
            #expect(h.owner.consumeCalls == (partial ? 1 : 0) && teardowns == [.closeOwnedWindowAndStop])
        }
    }
    @Test @MainActor func cancellationAfterAcquisitionOwnsCleanup() async throws {
        let h = try PolicyHarness()
        var ticket: SwiftFeatureRetirementTicket?
        h.factory.onAcquire = { ticket = h.scope.finish(.cancelled, teardown: { _ in }) }
        do { try await h.mount(); Issue.record("cancelled acquired mount") } catch {}
        let result = try await #require(ticket).outcome()
        #expect(result.primaryError is CancellationError)
        #expect(h.owner.consumeCalls == 1 && h.presenter.calls == 0)
    }
    @Test @MainActor func malformedAndNonzeroReportsRetainOriginalOwner() async throws {
        let reports = [SwiftFeatureLedgerObservation(currents: [0], tickets: 0, invariant: 0),
            .init(currents: Array(repeating: 0, count: 13) + [1], tickets: 0, invariant: 0),
            .init(currents: Array(repeating: 0, count: 14), tickets: 1, invariant: 0),
            .init(currents: Array(repeating: 0, count: 14), tickets: 0, invariant: 1)]
        for report in reports {
            var owner: PolicyOwner? = try PolicyOwner(); weak var original = owner
            let factory = PolicyFactory(owner!)
            let scope = SwiftFeatureOwnershipScope(), presenter = PolicyPresenter()
            owner!.consumption = .reportedClosed(report)
            _ = try await scope.mount(policyPacket, grant: policyGrant(), backend: factory, presenter: presenter)
            let result = try await scope.finish(.ownerRequested, teardown: { _ in }).outcome()
            owner = nil; factory.owner = nil
            guard case .retained(let retained) = result.close else { Issue.record("invalid report accepted"); continue }
            #expect(retained.cause as? SwiftFeatureError == .invalidLedger)
            #expect(result.frontendRequest == .closeOwnedWindowAndHold && original?.consumeCalls == 1)
        }
    }
    @Test @MainActor func primaryFailureAndDependentRetentionStaySeparate() async throws {
        let h = try PolicyHarness(); h.owner.frameFailure = true
        var authority: PolicyAuthority? = PolicyAuthority(); weak var retained = authority
        h.owner.consumption = .retained(authority!, cause: PolicyFailure.close)
        authority = nil
        do { try await h.mount(); Issue.record("bad frame") }
        catch let error as SwiftFeatureFailure {
            #expect(error.cause is PolicyFailure)
            guard case .retained(let cleanup) = error.close else { Issue.record("lost close"); return }
            #expect(cleanup.cause is PolicyFailure && retained != nil)
        }
        #expect(h.owner.consumeCalls == 1)
        _ = try await h.finish(); #expect(h.owner.consumeCalls == 1)
    }
    @Test @MainActor func startupCallbacksFIFOReplayNoopAndForeignOrigin() async throws {
        let h = try PolicyHarness()
        var tickets: [SwiftFeatureActionTicket] = []
        h.presenter.onPresent = {
            do { tickets = try (0..<8).map { try h.ticket("v\($0)") } } catch { Issue.record(error) }
        }
        try await h.mount(); h.presenter.onPresent = nil
        for ticket in tickets { guard case .acknowledged = try await ticket.outcome() else { Issue.record("callback lost"); return } }
        #expect(h.owner.values == (0..<8).map { "v\($0)" } && h.presenter.calls == 1)
        let a = try h.presenter.issue("repeat")
        guard case .accepted(let first) = h.scope.submit(a) else { Issue.record("first refused"); return }
        _ = try await first.outcome()
        guard case .accepted(let replay) = h.scope.submit(a) else { Issue.record("replay not admitted"); return }
        guard case .rejected(.invalidOrStale) = try await replay.outcome() else { Issue.record("replay dispatched"); return }
        let foreign = try PolicyHarness(); try await foreign.mount()
        guard case .accepted(let bad) = h.scope.submit(try foreign.presenter.issue("foreign")) else { Issue.record("not queued"); return }
        guard case .rejected(.invalidOrStale) = try await bad.outcome() else { Issue.record("foreign dispatched"); return }
        #expect(h.owner.values.count == 9 && h.owner.consumeCalls == 0)
        _ = try await h.finish(); _ = try await foreign.finish()
    }
    @Test @MainActor func changedRevisionDoesNotRebaseQueuedActions() async throws {
        let h = try PolicyHarness(); try await h.mount()
        h.owner.replies = [try FeatureDocumentV3(textValuePolicy: .standard).encode(policyDocument(2, "new"))]
        let a = try h.ticket("new"), stale = try h.ticket("old queued")
        guard case .acknowledged(let snapshot) = try await a.outcome() else { Issue.record("change refused"); return }
        #expect(snapshot.document.revision == 2)
        guard case .rejected(.invalidOrStale) = try await stale.outcome() else { Issue.record("stale rebased"); return }
        #expect(h.owner.values == ["new"] && h.presenter.calls == 2)
        _ = try await h.finish()
    }
    @Test @MainActor func sameRevisionMutationIsTerminal() async throws {
        let h = try PolicyHarness(); try await h.mount()
        h.owner.replies = [try FeatureDocumentV3(textValuePolicy: .standard).encode(policyDocument(1, "mutated"))]
        let ticket = try h.ticket("mutated")
        guard case .terminal(let result) = try await ticket.outcome() else { Issue.record("mutation acknowledged"); return }
        #expect((result.primaryError as? GuestUIProtocolFailureV1)?.code == .sameRevisionMutation)
        #expect(h.owner.consumeCalls == 1 && h.presenter.calls == 1)
    }
    @Test @MainActor func overloadSettlesAllAcceptedTicketsAndRetires() async throws {
        let h = try PolicyHarness(), gate = PolicyGate(); h.presenter.gate = gate
        let mount = Task { @MainActor in try await h.mount() }
        await spin { h.presenter.calls == 1 }
        let accepted = try (0..<64).map { try h.ticket("\($0)") }
        guard case .rejected(.overloaded) = h.scope.submit(try h.presenter.issue("overflow")) else { Issue.record("unbounded queue"); gate.release(); return }
        for action in accepted { guard case .retiring = try await action.outcome() else { Issue.record("lost queued settlement"); continue } }
        #expect(h.owner.consumeCalls == 0)
        gate.release(); do { try await mount.value } catch {}
        #expect(h.owner.values.isEmpty && h.owner.consumeCalls == 1)
        #expect(h.scope.result?.primaryError as? SwiftFeatureError == .overloaded)
    }
    @Test @MainActor func queuedCancellationAndCancelledObserverDoNotCancelWork() async throws {
        let h = try PolicyHarness(); try await h.mount()
        let a = try h.ticket("a"), b = try h.ticket("b")
        #expect(b.cancel() == .removedBeforeDispatch && b.cancel() == .alreadySettled)
        guard case .cancelledBeforeDispatch = try await b.outcome() else { Issue.record("queued cancel lost"); return }
        let observer = Task { @MainActor in try await a.outcome() }; observer.cancel()
        do { _ = try await observer.value; Issue.record("observer cancellation lost") } catch is CancellationError {}
        guard case .acknowledged = try await a.outcome() else { Issue.record("work cancelled by observer"); return }
        #expect(h.owner.values == ["a"])
        _ = try await h.finish()
    }
    @Test @MainActor func activeCancellationWaitsForUncooperativePresentationAndIgnoresLateAck() async throws {
        let h = try PolicyHarness(); try await h.mount()
        h.owner.replies = [try FeatureDocumentV3(textValuePolicy: .standard).encode(policyDocument(2, "new"))]
        let gate = PolicyGate(); h.presenter.gate = gate
        let active = try h.ticket("new")
        await spin { h.presenter.calls == 2 }
        let queued = try h.ticket("queued")
        #expect(active.cancel() == .retirementRequested)
        var teardownCount = 0
        let retirement = h.scope.finish(.cancelled) { _ in teardownCount += 1 }
        guard case .pending(let runtimeClose) = retirement.state else { Issue.record("fabricated closure"); gate.release(); return }
        #expect(runtimeClose == nil && h.owner.consumeCalls == 0 && teardownCount == 0)
        guard case .retiring(let linked) = try await queued.outcome() else { Issue.record("queued not settled"); gate.release(); return }
        #expect(linked === retirement)
        let cancelledObserver = Task { @MainActor in try await retirement.outcome() }; cancelledObserver.cancel()
        do { _ = try await cancelledObserver.value } catch is CancellationError {}
        gate.release()
        let result = try await retirement.outcome()
        guard case .terminal = try await active.outcome() else { Issue.record("late ack revived action"); return }
        #expect(result.primaryError is CancellationError && h.owner.consumeCalls == 1 && teardownCount == 1)
        guard case .rejected(.retired) = h.scope.submit(try h.presenter.issue("late")) else { Issue.record("retired scope revived"); return }
    }
    @Test @MainActor func acknowledgementFromEarlierRequestCannotSatisfyNewDisplay() async throws {
        let h = try PolicyHarness(); try await h.mount(); h.presenter.returnPrevious = true
        h.owner.replies = [try FeatureDocumentV3(textValuePolicy: .standard).encode(policyDocument(2, "new"))]
        guard case .terminal(let result) = try await h.ticket("new").outcome() else { Issue.record("foreign acknowledgement accepted"); return }
        #expect(result.primaryError as? SwiftFeatureError == .presentation && h.owner.consumeCalls == 1)
    }
    @Test @MainActor func floodYieldsToRetirementAndNeverDispatchesAfterIt() async throws {
        let h = try PolicyHarness(); try await h.mount()
        var accepted: [SwiftFeatureActionTicket] = []
        var retirement: SwiftFeatureRetirementTicket?
        h.owner.onEvent = {
            if h.owner.values.count == 1 {
                Task { @MainActor in retirement = h.scope.finish(.cancelled, teardown: { _ in }) }
            }
            if h.owner.values.count < 60 {
                do { accepted.append(try h.ticket("reentrant\(h.owner.values.count)")) } catch { Issue.record(error) }
            }
        }
        let first = try h.ticket("first")
        _ = try await first.outcome()
        await spin { retirement != nil }
        let result = try await #require(retirement).outcome()
        #expect(result.primaryError is CancellationError && h.owner.values.count < 60)
        let dispatched = h.owner.values.count
        for ticket in accepted { _ = try await ticket.outcome() }
        await Task.yield()
        #expect(h.owner.values.count == dispatched && h.owner.consumeCalls == 1)
        h.owner.onEvent = nil
    }
    @Test @MainActor func invalidBindingAndValueRefuseBeforeRuntimeAndEventFailureRootsCause() async throws {
        let h = try PolicyHarness(); try await h.mount()
        let router = try #require(h.presenter.router), snapshot = try router.snapshot
        let identity = try #require(snapshot.identity(for: "task.title"))
        #expect(throws: UIRoutingError.unboundEvent) { try router.route(UIEventEnvelope(revision: 1, identity: identity, event: .submit)) }
        #expect(throws: UIRoutingError.invalidValue) { try router.route(UIEventEnvelope(revision: 1, identity: identity, event: .textChange, value: .bool(true))) }
        #expect(h.owner.values.isEmpty && h.owner.consumeCalls == 0)
        h.owner.eventFailure = true
        guard case .terminal(let result) = try await h.ticket("event failure").outcome() else { Issue.record("runtime failure ignored"); return }
        #expect(result.primaryError is PolicyFailure && h.owner.consumeCalls == 1)
        guard case .clean(let ledger) = result.close else { Issue.record("clean report lost"); return }
        try ledger.requireFourteenZeroCurrentsAndNoTicketsOrInvariant()
    }
    @Test @MainActor func externalOwnerInputErrorIsTerminalAfterRuntimeEntry() async throws {
        for failDuringFrame in [false, true] {
            let h = try PolicyHarness(); try await h.mount()
            if failDuringFrame { h.owner.frameError = SwiftFeatureError.input }
            else { h.owner.eventError = SwiftFeatureError.input }
            guard case .terminal(let result) = try await h.ticket("runtime input error").outcome() else {
                Issue.record("runtime failure misclassified as admission refusal"); _ = try await h.finish(); continue
            }
            #expect(result.primaryError as? SwiftFeatureError == .input && h.owner.consumeCalls == 1)
            #expect(h.owner.values == (failDuringFrame ? ["runtime input error"] : []))
        }
    }
}
#endif
