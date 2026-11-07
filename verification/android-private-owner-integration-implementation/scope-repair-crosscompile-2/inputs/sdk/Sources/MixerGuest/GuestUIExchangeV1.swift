import Foundation
import MixerUI

/// One fixed data-only control object shared by the bridge and coordinator.
/// It never owns a task, executor, callback, model, session, or activation owner.
@_spi(GuestUIV1) public final class GuestUIExchangeV1: @unchecked Sendable {
    public let deliveryWake = GuestUIWakeV1()
    public let coordinatorWake = GuestUIWakeV1()
    private let generation: UInt64
    private let issuer = GuestUIIssuerV1()
    private let lock = NSLock()
    private var state = State()

    private struct Notices: OptionSet {
        let rawValue: Int
        static let delivery = Notices(rawValue: 1)
        static let coordinator = Notices(rawValue: 2)
        static let finishDelivery = Notices(rawValue: 4)
    }
    private enum Event {
        case preparing(UInt64), queued(UInt64, Data), running(UInt64)
        case result(GuestUIEventResultV1)
        var sequence: UInt64 {
            switch self {
            case .preparing(let n), .queued(let n, _), .running(let n): n
            case .result(let result): result.sequence
            }
        }
    }
    private struct State {
        var stop: GuestUIStopV1?
        var firstUIFailure: GuestUIProtocolTerminalV1?
        var intent = false
        var confirmed = false
        var started = false
        var turn: GuestUITurnClaimV1?
        var turnSerial: UInt64 = 0
        var frameSerial: UInt64 = 0
        var eventSequence: UInt64 = 0
        var presentationSerial: UInt64 = 0
        var event: Event?
        var lastBytes: Data?
        var lastDocument: ValidatedUIDocument?
        var latestRevision: UInt64?
        var pending: GuestUIFrameV1?
        var presentation: UInt64?
        var presentationHasFrame = false
        var refresh = false
        var displayed: UIRenderSnapshot?
        var displayedFrameSerial: UInt64?
        var receipt: GuestUIPresentationReceiptV1?
        var counters = GuestUIExchangeCountersV1()
    }
    private static let validator = UIValidator(limits: UIValidationLimits(
        maximumMessageBytes: 65536, maximumNodes: 256, maximumDepth: 16,
        maximumChildrenPerNode: 64, maximumStringBytes: 4096),
        supportedKinds: [.vStack, .text, .button])

    public init(generation: UInt64) throws {
        guard generation > 0 else { throw GuestUIControlRejectionV1.invalidGeneration }
        self.generation = generation
    }
    private func mutate<T>(_ body: (inout State, inout Notices) throws -> T) rethrows -> T {
        lock.lock()
        var notices: Notices = []
        do {
            let value = try body(&state, &notices)
            lock.unlock(); notify(notices); return value
        } catch { lock.unlock(); notify(notices); throw error }
    }
    private func notify(_ notices: Notices) {
        // No continuation can resume under the exchange or wake-state lock.
        if notices.contains(.delivery) { deliveryWake.signal() }
        if notices.contains(.coordinator) { coordinatorWake.signal() }
        if notices.contains(.finishDelivery) { deliveryWake.finish() }
    }
    private func requireLive(_ s: State, generation expected: UInt64) throws {
        guard expected == generation else { throw GuestUIControlRejectionV1.invalidGeneration }
        guard s.stop == nil else { throw GuestUIControlRejectionV1.closed }
    }
    private func requireTurn(_ claim: GuestUITurnClaimV1, _ s: State) throws {
        guard claim.issuer === issuer, claim.generation == generation else { throw GuestUIControlRejectionV1.staleClaim }
        try requireLive(s, generation: claim.generation)
        guard s.turn?.serial == claim.serial else { throw GuestUIControlRejectionV1.staleClaim }
    }
    private func protocolStop(_ failure: GuestUIProtocolFailureV1, _ s: inout State, _ notices: inout Notices) {
        let terminal = GuestUIProtocolTerminalV1(failure: failure, effectStage: s.intent ? .intentEntered : .beforeIntent)
        if s.firstUIFailure == nil { s.firstUIFailure = terminal; notices.insert(.coordinator) }
        guard s.stop == nil else { return }
        s.stop = .protocolViolation(terminal); stopContents(&s, &notices)
    }
    private func stopContents(_ s: inout State, _ notices: inout Notices) {
        if let event = s.event {
            switch event {
            case .preparing: s.event = nil // Admission never completed.
            case .queued:
                s.event = .result(GuestUIEventResultV1(generation: generation, sequence: event.sequence,
                                                     outcome: .terminal(turnBegan: false)))
                bump(&s.counters.terminalEvents)
            case .running, .result:
                s.event = .result(GuestUIEventResultV1(generation: generation, sequence: event.sequence,
                                                     outcome: .terminal(turnBegan: true)))
                bump(&s.counters.terminalEvents)
            }
        }
        s.turn = nil; s.pending = nil; s.lastBytes = nil; s.lastDocument = nil
        s.displayed = nil; s.displayedFrameSerial = nil; s.receipt = nil; s.refresh = true
        notices.formUnion([.delivery, .coordinator, .finishDelivery])
    }
    private func failure(_ claim: GuestUITurnClaimV1, _ code: GuestUIProtocolCodeV1) -> GuestUIProtocolFailureV1 {
        let phase: GuestUIProtocolPhaseV1
        switch claim.kind { case .startup: phase = .startup; case .event: phase = .event; case .ready: phase = .wake }
        return GuestUIProtocolFailureV1(phase: phase, code: code)
    }
    public func claimStartup() throws -> GuestUITurnClaimV1 {
        try mutate { s, notices in
            try requireLive(s, generation: generation)
            guard !s.started, s.turn == nil, s.event == nil else { throw GuestUIControlRejectionV1.busy }
            guard s.turnSerial < .max else {
                let error = GuestUIProtocolFailureV1(phase: .startup, code: .sequenceExhausted)
                protocolStop(error, &s, &notices); throw error
            }
            s.turnSerial += 1
            let claim = GuestUITurnClaimV1(issuer: issuer, generation: generation, serial: s.turnSerial, kind: .startup)
            s.turn = claim; return claim
        }
    }
    public func claimNextTurn(ready: Bool) throws -> GuestUITurnClaimV1? {
        try mutate { s, notices in
            try requireLive(s, generation: generation)
            guard s.started else { throw GuestUIControlRejectionV1.busy }
            guard s.turn == nil else { return nil }
            let kind: GuestUITurnKindV1
            switch s.event {
            case .preparing?, .running?: return nil
            case .queued(let sequence, let bytes)?: kind = .event(sequence: sequence, bytes: bytes)
            default: guard ready else { return nil }; kind = .ready
            }
            guard s.turnSerial < .max else {
                let error = GuestUIProtocolFailureV1(phase: .wake, code: .sequenceExhausted)
                protocolStop(error, &s, &notices); throw error
            }
            s.turnSerial += 1
            let claim = GuestUITurnClaimV1(issuer: issuer, generation: generation, serial: s.turnSerial, kind: kind)
            if case .event(let sequence, _) = kind { s.event = .running(sequence) }
            s.turn = claim; return claim
        }
    }
    public func finishReadyWithoutInvocation(_ claim: GuestUITurnClaimV1) throws {
        try mutate { s, _ in
            try requireTurn(claim, s)
            guard case .ready = claim.kind else { throw GuestUIControlRejectionV1.staleClaim }
            s.turn = nil
        }
    }
    public func finishTurn(_ claim: GuestUITurnClaimV1, documentBytes: Data) throws {
        try mutate { s, _ in try requireTurn(claim, s) }
        guard (1...65536).contains(documentBytes.count) else {
            try mutate { s, notices in
                try requireTurn(claim, s)
                let error = failure(claim, .document); protocolStop(error, &s, &notices); throw error
            }
            return
        }
        let owned = documentBytes.withUnsafeBytes { Data(bytes: $0.baseAddress!, count: $0.count) }
        let document: ValidatedUIDocument
        do {
            document = try GuestUICodec(validator: Self.validator).decode(owned)
            guard document.document.revision > 0 else { throw failure(claim, .document) }
        } catch {
            // A concurrent close is an ordinary dropped turn, not a later protocol stop.
            try mutate { s, notices in
                try requireTurn(claim, s)
                let failure = self.failure(claim, .document)
                protocolStop(failure, &s, &notices); throw failure
            }
            return
        }
        try mutate { s, notices in
            try requireTurn(claim, s)
            let revision = document.document.revision
            if let previous = s.latestRevision {
                if revision < previous {
                    let error = failure(claim, .revisionRegressed); protocolStop(error, &s, &notices); throw error
                }
                if revision == previous, owned != s.lastBytes {
                    let error = failure(claim, .sameRevisionMutation); protocolStop(error, &s, &notices); throw error
                }
            }
            if revision != s.latestRevision {
                guard s.frameSerial < .max else {
                    let error = failure(claim, .sequenceExhausted); protocolStop(error, &s, &notices); throw error
                }
                s.frameSerial += 1
                if s.pending != nil { bump(&s.counters.replacedPendingFrames) }
                s.pending = GuestUIFrameV1(issuer: issuer, generation: generation, serial: s.frameSerial, document: document)
                s.latestRevision = revision; s.lastDocument = document; s.lastBytes = owned
                bump(&s.counters.producedFrames); s.counters.maximumPendingFrames = 1
                s.counters.maximumRawDocumentBytes = max(s.counters.maximumRawDocumentBytes, UInt64(owned.count))
                s.refresh = true; notices.insert(.delivery)
            }
            if case .startup = claim.kind { s.started = true }
            if case .event(let sequence, _) = claim.kind {
                s.event = .result(GuestUIEventResultV1(generation: generation, sequence: sequence, outcome: .delivered))
                bump(&s.counters.deliveredEvents); s.refresh = true; notices.insert(.delivery)
            }
            s.turn = nil; bump(&s.counters.successfulTurns)
        }
    }

    public func offer(_ envelope: UIEventEnvelope, generation expected: UInt64) -> GuestUIEventAdmissionV1 {
        enum Preparation { case rejected(GuestUIEventAdmissionV1), encode(UInt64, RoutedUIAction) }
        let preparation: Preparation = mutate { s, notices in
            guard expected == generation else { return .rejected(.stale) }
            guard s.stop == nil else { return .rejected(.closed) }
            guard s.confirmed, s.turn == nil, s.event == nil else { return .rejected(.busy) }
            guard let displayed = s.displayed, displayed.document.revision == s.latestRevision,
                  envelope.revision == displayed.document.revision else { return .rejected(.stale) }
            let action: RoutedUIAction
            do { action = try displayed.route(envelope) }
            catch let error as UIRoutingError { return .rejected(.invalid(error)) }
            catch { return .rejected(.invalid(.invalidValue)) }
            guard action.event == .activate, action.value == .null else { return .rejected(.invalid(.invalidValue)) }
            guard s.eventSequence < .max else {
                protocolStop(GuestUIProtocolFailureV1(phase: .event, code: .sequenceExhausted), &s, &notices)
                return .rejected(.closed)
            }
            let sequence = s.eventSequence + 1
            s.event = .preparing(sequence); s.counters.maximumEventSlots = 1
            s.refresh = true; notices.insert(.delivery)
            return .encode(sequence, action)
        }
        guard case .encode(let sequence, let action) = preparation else {
            if case .rejected(let result) = preparation { return result }
            return .closed
        }
        let bytes: Data
        do {
            bytes = try GuestUIEventCodecV1.encode(GuestUIEventV1(sequence: sequence, revision: action.revision,
                nodeID: action.nodeID, actionID: action.actionID))
        } catch {
            return mutate { s, notices in
                guard s.stop == nil, case .preparing(sequence)? = s.event else { return .closed }
                protocolStop(GuestUIProtocolFailureV1(phase: .event, code: .eventEncoding), &s, &notices)
                return .closed
            }
        }
        return mutate { s, notices in
            guard s.stop == nil, case .preparing(let current)? = s.event, current == sequence else { return .closed }
            s.event = .queued(sequence, bytes); s.eventSequence = sequence
            bump(&s.counters.acceptedEvents); s.counters.maximumEventBytes = max(s.counters.maximumEventBytes, UInt64(bytes.count))
            s.refresh = true; notices.insert(.delivery); return .accepted(sequence: sequence)
        }
    }
    public func claimPresentation(generation expected: UInt64) -> GuestUIPresentationClaimV1? {
        mutate { s, notices in
            guard expected == generation, s.presentation == nil, s.refresh,
                  s.confirmed || s.stop != nil else { return nil }
            guard s.presentationSerial < .max else {
                protocolStop(GuestUIProtocolFailureV1(phase: .presentation, code: .sequenceExhausted), &s, &notices)
                return nil
            }
            s.presentationSerial += 1; s.presentation = s.presentationSerial; s.refresh = false
            let frame = s.pending; s.pending = nil; s.presentationHasFrame = frame != nil
            if frame != nil { s.counters.maximumClaimedFrames = 1 }
            let event: GuestUIEventResultV1?
            if case .result(let result)? = s.event { event = result } else { event = nil }
            return GuestUIPresentationClaimV1(issuer: issuer, generation: generation,
                serial: s.presentationSerial, frame: frame, eventResult: event, stop: s.stop)
        }
    }
    public func completePresentation(_ claim: GuestUIPresentationClaimV1,
                                     snapshot: UIRenderSnapshot?) -> GuestUIPresentationTicketV1? {
        mutate { s, notices in
            guard claim.issuer === issuer, claim.generation == generation, s.presentation == claim.serial else { return nil }
            s.presentation = nil; s.presentationHasFrame = false
            if case .result(let result)? = s.event, claim.eventResult == result {
                s.event = nil; s.refresh = true; notices.insert(.delivery)
            }
            guard s.stop == nil else { return nil }
            guard let frame = claim.frame else { return nil }
            guard let snapshot, Self.exactDocument(frame.document.document, snapshot.document) else {
                protocolStop(GuestUIProtocolFailureV1(phase: .presentation, code: .presentationInvariant), &s, &notices)
                return nil
            }
            s.displayed = snapshot; s.displayedFrameSerial = frame.serial
            return GuestUIPresentationTicketV1(issuer: issuer, generation: generation,
                frameSerial: frame.serial, revision: snapshot.document.revision)
        }
    }
    // Swift String equality folds canonically equivalent Unicode spellings.
    // Guest identifiers are wire bytes: a native snapshot must preserve their
    // exact UTF-8, as well as every other validated scalar. Work follows only
    // the bounded expected tree; count checks reject a wider candidate before
    // traversal and elementsEqual stops by the expected string's end. Property
    // keys are at most 16 per node, so exact-key matching needs no sorted copy,
    // normalization, serialized buffer or candidate-sized allocation.
    private static func exactDocument(_ expected: UIDocument, _ actual: UIDocument) -> Bool {
        expected.schemaVersion == actual.schemaVersion && expected.revision == actual.revision &&
            exactNode(expected.root, actual.root)
    }
    private static func exactNode(_ expected: UINode, _ actual: UINode) -> Bool {
        guard expected.id.utf8.elementsEqual(actual.id.utf8), expected.kind == actual.kind,
              expected.properties.count == actual.properties.count,
              expected.actions.count == actual.actions.count,
              expected.children.count == actual.children.count else { return false }
        for (key, value) in expected.properties {
            guard let found = actual.properties.first(where: { key.utf8.elementsEqual($0.key.utf8) }),
                  exactValue(value, found.value) else { return false }
        }
        for (left, right) in zip(expected.actions, actual.actions) {
            guard left.id.utf8.elementsEqual(right.id.utf8), left.event == right.event else { return false }
        }
        for (left, right) in zip(expected.children, actual.children) {
            guard exactNode(left, right) else { return false }
        }
        return true
    }
    private static func exactValue(_ expected: UIValue, _ actual: UIValue) -> Bool {
        switch (expected, actual) {
        case (.string(let left), .string(let right)): return left.utf8.elementsEqual(right.utf8)
        case (.number(let left), .number(let right)): return left.bitPattern == right.bitPattern
        case (.bool(let left), .bool(let right)): return left == right
        case (.null, .null): return true
        default: return false
        }
    }
    public func observePresentation(_ ticket: GuestUIPresentationTicketV1) -> Bool {
        mutate { s, notices in
            guard ticket.issuer === issuer, ticket.generation == generation, s.stop == nil, s.confirmed,
                  s.displayedFrameSerial == ticket.frameSerial, s.displayed?.document.revision == ticket.revision else { return false }
            if s.receipt == nil {
                s.receipt = GuestUIPresentationReceiptV1(generation: generation, frameSerial: ticket.frameSerial,
                                                        revision: ticket.revision)
                notices.insert(.coordinator)
            }
            return true
        }
    }
    public func consumeObservedPresentation(generation expected: UInt64, frameSerial: UInt64) {
        mutate { s, _ in
            guard expected == generation, s.receipt?.frameSerial == frameSerial else { return }
            s.receipt = nil
        }
    }
    public func enterEffectsIntent(generation expected: UInt64) throws {
        try mutate { s, _ in
            try requireLive(s, generation: expected)
            guard s.started, !s.intent else { throw GuestUIControlRejectionV1.busy }
            s.intent = true
        }
    }
    public func confirmEffectsEnabled(generation expected: UInt64) throws {
        try mutate { s, notices in
            try requireLive(s, generation: expected)
            guard s.started, s.intent, !s.confirmed else { throw GuestUIControlRejectionV1.busy }
            s.confirmed = true; s.refresh = true; notices.insert(.delivery)
        }
    }
    public func requireCommitEntry(generation expected: UInt64) throws {
        try mutate { s, _ in try requireLive(s, generation: expected) }
    }
    public func requireEffectAdmission(generation expected: UInt64) throws {
        try mutate { s, _ in
            try requireLive(s, generation: expected)
            guard s.confirmed else { throw GuestUIControlRejectionV1.busy }
        }
    }
    public func recordProtocolFailure(_ failure: GuestUIProtocolFailureV1) {
        mutate { s, notices in protocolStop(failure, &s, &notices) }
    }
    public func stop(_ cause: GuestUIExternalStopV1) {
        mutate { s, notices in
            guard s.stop == nil else { return }
            switch cause { case .bridge: s.stop = .bridge; case .cancelled: s.stop = .cancelled
            case .deadline: s.stop = .deadline; case .closed: s.stop = .closed }
            stopContents(&s, &notices)
        }
    }
    public func snapshot() -> GuestUIExchangeSnapshotV1 {
        mutate { s, _ in GuestUIExchangeSnapshotV1(generation: generation, stop: s.stop,
            effectsMayHaveOpened: s.intent, effectsConfirmed: s.confirmed, hasStarted: s.started,
            guestTurnInFlight: s.turn != nil, eventOutstanding: s.event != nil,
            presentationInFlight: s.presentation != nil, latestRevision: s.latestRevision,
            displayedRevision: s.displayed?.document.revision, pendingPresentationReceipt: s.receipt,
            firstUIProtocolFailure: s.firstUIFailure, counters: s.counters) }
    }
}

private func bump(_ value: inout UInt64) { if value < .max { value += 1 } }
