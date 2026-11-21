import Foundation
@_spi(InstalledApplicationStorage) import MixerCapabilities
@_spi(GuestUIV1) import MixerGuest
#if os(macOS) && MIXER_PRIVATE_F10
@_spi(FeatureUIV3) import MixerGuest
#endif

protocol RuntimeGuestUIExchange: AnyObject, Sendable {
    func snapshot() -> GuestUIExchangeSnapshotV1
    func stop(_ cause: GuestUIExternalStopV1)
    func requireCommitEntry(generation: UInt64) throws
    func requireEffectAdmission(generation: UInt64) throws
    func recordProtocolFailure(_ failure: GuestUIProtocolFailureV1)
    func claimStartup() throws -> GuestUITurnClaimV1
    func claimNextTurn(ready: Bool) throws -> GuestUITurnClaimV1?
    func finishReadyWithoutInvocation(_ claim: GuestUITurnClaimV1) throws
    func finishTurn(_ claim: GuestUITurnClaimV1, documentBytes: Data) throws
}
extension GuestUIExchangeV1: RuntimeGuestUIExchange {}
#if os(macOS) && MIXER_PRIVATE_F10
extension GuestUIExchangeV3: RuntimeGuestUIExchange {}
#endif

/// Owned numeric descriptors only. All reads and turns stay on the existing
/// guest queue; the exchange alone arbitrates input against every guest turn.
struct GuestUIControlHeader {
    let documentOffset: UInt32
    let documentLength: UInt32
    let eventOffset: UInt32
    let eventCapacity: UInt32

    static func checkedEnd(_ offset: UInt32, _ length: UInt32, phase: GuestUIProtocolPhaseV1) throws -> UInt32 {
        let (end, overflow) = offset.addingReportingOverflow(length)
        guard !overflow else { throw GuestUIProtocolFailureV1(phase: phase, code: .memoryRange) }
        return end
    }
    static func decode(_ bytes: Data, headerOffset: UInt32, phase: GuestUIProtocolPhaseV1, allowsEmptyDocument: Bool = false) throws -> Self {
        func word(_ offset: Int) -> UInt32 {
            (0..<4).reduce(UInt32(0)) { $0 | UInt32(bytes[offset + $1]) << ($1 * 8) }
        }
        guard bytes.count == 32 else { throw GuestUIProtocolFailureV1(phase: phase, code: .header) }
        guard word(0) == 0x3155494d, word(4) == 32,
              (word(12) > 0 || allowsEmptyDocument), word(12) <= 65536, word(20) == 4096,
              bytes[24..<32].allSatisfy({ $0 == 0 }) else { throw GuestUIProtocolFailureV1(phase: phase, code: .header) }
        let header = Self(documentOffset: word(8), documentLength: word(12), eventOffset: word(16), eventCapacity: word(20))
        let ranges = [(headerOffset, UInt32(32)), (header.documentOffset, header.documentLength), (header.eventOffset, header.eventCapacity)]
        var ends: [UInt32] = []
        for range in ranges { ends.append(try checkedEnd(range.0, range.1, phase: phase)) }
        for first in 0..<3 {
            for second in (first + 1)..<3 where ranges[first].1 != 0 && ranges[second].1 != 0
                && ranges[first].0 < ends[second] && ranges[second].0 < ends[first] {
                throw GuestUIProtocolFailureV1(phase: phase, code: .memoryRange)
            }
        }
        return header
    }
}

final class GuestUITurns: @unchecked Sendable {
    let exchange: any RuntimeGuestUIExchange
    private var v1: GuestUIExchangeV1? { exchange as? GuestUIExchangeV1 }
#if os(macOS) && MIXER_PRIVATE_F10
    private var v3: GuestUIExchangeV3? { exchange as? GuestUIExchangeV3 }
    private var featureHeader: GuestUIHeaderV3?
    private var inertDocument: Data?
    private struct FeatureRead {
        let generation: UInt64
        let kickTurn: UInt64
        let token: UInt64
    }
    private enum FeatureHydration {
        case beforeKick
        case awaitingRequest(generation: UInt64, kickTurn: UInt64)
        case awaitingResponse(FeatureRead)
        case posted(FeatureRead)
        case hydrated
    }
    // The installed exit owner confines the kick, native take, post and ready
    // turn to its guest queue. A mailbox notification carries no authority.
    private var featureHydration = FeatureHydration.beforeKick
    private var featureHydrated: Bool {
        if case .hydrated = featureHydration { return true }
        return false
    }
#endif
    let commitFacts: InstalledGuestUICommitFacts?
    private var headerOffset: UInt32?
    private var eventOffset: UInt32?
    private var eventCapacity: UInt32?
    private enum InitialDocument { case immediate, pendingHook, awaitingRead, published }
    private var initialDocument = InitialDocument.immediate
    private var startupCutoff: UInt64?
    private var didTakeHydrationRead = false
    private var postedHydrationSnapshot = false
    private var activeCommitEvent: InstalledGuestUICommitEvent?
    private(set) var nativeTurns: UInt64 = 0

    var awaitingInitialDocument: Bool {
#if os(macOS) && MIXER_PRIVATE_F10
        if v3 != nil { return !featureHydrated }
#endif
        return initialDocument == .pendingHook || initialDocument == .awaitingRead
    }
    private var publishedHydration: Bool {
#if os(macOS) && MIXER_PRIVATE_F10
        if v3 != nil { return featureHydrated }
#endif
        return initialDocument == .published
    }
    var needsEmptyMailboxBeforeNextTurn: Bool {
#if os(macOS) && MIXER_PRIVATE_F10
        if v3 != nil { return true }
#endif
        return publishedHydration || commitFacts != nil
    }
    func setStartupCutoff(_ cutoff: UInt64?) { startupCutoff = cutoff }
    func acceptsHydrationOperation(token: UInt64, isRead: Bool) throws -> Bool {
#if os(macOS) && MIXER_PRIVATE_F10
        if v3 != nil {
            guard case .awaitingRequest(let generation, let kickTurn) = featureHydration, isRead else {
                throw GuestUIProtocolFailureV1(phase: .wake, code: .document)
            }
            featureHydration = .awaitingResponse(FeatureRead(generation: generation, kickTurn: kickTurn, token: token))
            return true
        }
#endif
        if initialDocument == .immediate { return true }
        guard initialDocument == .awaitingRead, isRead, !didTakeHydrationRead else { return false }
        didTakeHydrationRead = true
        return true
    }
    func acceptsTypedHydrationOperation(_ operation: CapabilityOperation, token: UInt64) -> Bool {
#if os(macOS) && MIXER_PRIVATE_F10
        if v3 != nil {
            guard case .awaitingResponse(let read) = featureHydration, read.token == token,
                  case .get(let arguments) = operation else { return false }
            return arguments == KVGetArguments(namespace: "material_test", key: "queue-0")
        }
#endif
        return true
    }
    func recordHydrationPost(token: UInt64, delivered: Bool, found: Bool) throws {
#if os(macOS) && MIXER_PRIVATE_F10
        if let v3 {
            guard case .awaitingResponse(let read) = featureHydration, read.token == token,
                  read.generation == v3.snapshot().generation, delivered, found else {
                throw GuestUIProtocolFailureV1(phase: .wake, code: .document)
            }
            try v3.requireEffectAdmission(generation: read.generation)
            featureHydration = .posted(read)
            return
        }
#endif
        if initialDocument == .awaitingRead, delivered, found { postedHydrationSnapshot = true }
    }
    var initialDocumentRemainingNanoseconds: UInt64? {
        guard awaitingInitialDocument, let startupCutoff else { return nil }
        let now = DispatchTime.now().uptimeNanoseconds
        return now < startupCutoff ? startupCutoff - now : 0
    }
    func requireInitialDocumentDeadline() throws {
        guard awaitingInitialDocument else { return }
        guard let startupCutoff, DispatchTime.now().uptimeNanoseconds < startupCutoff else {
            throw GuestUIProtocolFailureV1(phase: .startup, code: .startupDeadline)
        }
    }
    init(exchange: any RuntimeGuestUIExchange, commitFacts: InstalledGuestUICommitFacts?) {
        self.exchange = exchange; self.commitFacts = commitFacts
    }
    static func requireLive(_ exchange: any RuntimeGuestUIExchange) throws {
        try exchange.requireCommitEntry(generation: exchange.snapshot().generation)
    }
    var stopped: Bool { exchange.snapshot().stop != nil }
    func requireEffectAdmission() throws {
        try exchange.requireEffectAdmission(generation: exchange.snapshot().generation)
    }
    func invalidateActiveCommit() {
        activeCommitEvent?.invalidateCommit()
        activeCommitEvent = nil
    }
    func startup(_ native: NativeCapabilitySession) throws {
        let claim = try exchange.claimStartup()
        let result = try native.startup()
        if nativeTurns < .max { nativeTurns += 1 }
        guard case .i32(let raw) = result.value else { throw GuestUIProtocolFailureV1(phase: .startup, code: .startupResult) }
        let offset = UInt32(bitPattern: raw)
        _ = try GuestUIControlHeader.checkedEnd(offset, 32, phase: .startup)
        headerOffset = offset
#if os(macOS) && MIXER_PRIVATE_F10
        if v3 != nil {
            try harvestFeature(native, claim: claim, phase: .startup)
            return
        }
#endif
        try harvest(native, claim: claim, phase: .startup, initial: true, allowsEmptyDocument: v1?.allowsDeferredStartup == true)
    }
    enum NextTurn {
        case idle
        case hydration
        case event(InstalledGuestUICommitEvent?)
        case ready
    }
    /// A missing claim and an idle native ready check leave turn accounting unchanged.
    func next(_ native: NativeCapabilitySession, ready: Bool) throws -> NextTurn? {
#if os(macOS) && MIXER_PRIVATE_F10
        if let v3 {
            switch featureHydration {
            case .beforeKick:
                guard v3.snapshot().effectsConfirmed, let claim = try v3.claimNextTurn(ready: true) else { return nil }
                try requireInitialDocumentDeadline()
                let result = try native.invoke(GuestUIProtocolV3.readyExport, arguments: [])
                if nativeTurns < .max { nativeTurns += 1 }
                guard result.value == nil else { throw GuestUIProtocolFailureV1(phase: .wake, code: .eventResult) }
                try harvestFeature(native, claim: claim, phase: .wake, kick: true)
                featureHydration = .awaitingRequest(generation: claim.generation, kickTurn: claim.serial)
                return .ready
            case .awaitingRequest, .awaitingResponse: return nil
            case .posted, .hydrated: break
            }
        }
#endif
        if initialDocument == .pendingHook {
            guard exchange.snapshot().effectsConfirmed else { return nil }
            try requireInitialDocumentDeadline()
            guard let claim = try exchange.claimNextTurn(ready: true) else { return nil }
            let result = try native.invoke("mixer_guest_ui_hydrate_v1", arguments: [])
            if nativeTurns < .max { nativeTurns += 1 }
            guard result.value == .i32(0) else {
                throw GuestUIProtocolFailureV1(phase: .startup, code: .startupResult)
            }
            initialDocument = .awaitingRead
            try harvest(native, claim: claim, phase: .startup, allowsEmptyDocument: true, requiresEmptyDocument: true)
            return .hydration
        }
        guard let claim = try exchange.claimNextTurn(ready: ready && !publishedHydration) else { return nil }
        switch claim.kind {
        case .startup:
            throw GuestUIProtocolFailureV1(phase: .startup, code: .startupResult)
        case .event(let sequence, let bytes):
            invalidateActiveCommit()
            guard let eventOffset, let eventCapacity, bytes.count <= Int(eventCapacity) else {
                throw GuestUIProtocolFailureV1(phase: .event, code: .eventEncoding)
            }
            initialDocument = .immediate
            // One claimed worker operation. No pump wake can split this pair.
            try native.write(offset: eventOffset, data: bytes)
            var eventExport = "mixer_guest_ui_event_v1"
#if os(macOS) && MIXER_PRIVATE_F10
            if v3 != nil { eventExport = GuestUIProtocolV3.eventExport }
#endif
            let result = try native.invoke(eventExport, arguments: [.i32(Int32(bytes.count))])
            if nativeTurns < .max { nativeTurns += 1 }
            guard result.value == .i32(0) else { throw GuestUIProtocolFailureV1(phase: .event, code: .eventResult) }
#if os(macOS) && MIXER_PRIVATE_F10
            if v3 != nil {
                try harvestFeature(native, claim: claim, phase: .event)
                return .event(nil)
            }
#endif
            try harvest(native, claim: claim, phase: .event)
            guard let commitFacts, let action = claim.eventSelection,
                  action.nodeID == commitFacts.nodeID, action.actionID == commitFacts.actionID else { return .event(nil) }
            let generation = claim.generation
            let event = InstalledGuestUICommitEvent(generation: generation, sequence: sequence, turnSerial: claim.serial,
                displayedRevision: action.revision, nodeID: action.nodeID, actionID: action.actionID) { [weak exchange] in
                    guard let exchange else { return false }
                    return (try? exchange.requireEffectAdmission(generation: generation)) != nil
                }
            if commitFacts.commitArguments != nil { activeCommitEvent = event }
            return .event(event)
        case .ready:
#if os(macOS) && MIXER_PRIVATE_F10
            if v3 != nil {
                guard case .posted(let read) = featureHydration, read.generation == claim.generation,
                      read.kickTurn < claim.serial, let startupCutoff else {
                    throw GuestUIProtocolFailureV1(phase: .wake, code: .document)
                }
                try requireInitialDocumentDeadline()
                guard try native.wake() else {
                    try exchange.finishReadyWithoutInvocation(claim)
                    return .idle
                }
                if nativeTurns < .max { nativeTurns += 1 }
                try harvestFeature(native, claim: claim, phase: .wake, hydrationCutoff: startupCutoff)
                featureHydration = .hydrated
                return .ready
            }
#endif
            guard try native.wake() else {
                try exchange.finishReadyWithoutInvocation(claim)
                return .idle
            }
            if nativeTurns < .max { nativeTurns += 1 }
            try harvest(native, claim: claim, phase: .wake)
            return .ready
        }
    }
#if os(macOS) && MIXER_PRIVATE_F10
    private func harvestFeature(_ native: NativeCapabilitySession, claim: GuestUITurnClaimV1,
                                phase: GuestUIProtocolPhaseV1, kick: Bool = false, hydrationCutoff: UInt64? = nil) throws {
        guard let v3, let headerOffset else { throw GuestUIProtocolFailureV1(phase: phase, code: .header) }
        let raw = try native.read(offset: headerOffset, count: 32)
        let header: GuestUIHeaderV3
        do {
            header = try GuestUIHeaderV3.decode(raw, at: headerOffset, memoryBytes: native.memoryLimitBytes, previous: featureHeader)
        } catch GuestUIFeatureErrorV3.bufferChanged {
            throw GuestUIProtocolFailureV1(phase: phase, code: .bufferChanged)
        } catch GuestUIFeatureErrorV3.range {
            throw GuestUIProtocolFailureV1(phase: phase, code: .memoryRange)
        } catch {
            throw GuestUIProtocolFailureV1(phase: phase, code: .header)
        }
        if featureHeader == nil {
            let last = header.eventOffset + UInt32(GuestUIProtocolV3.maximumBytes - 1)
            _ = try native.read(offset: last, count: 1)
            featureHeader = header
            eventOffset = header.eventOffset
            eventCapacity = UInt32(GuestUIProtocolV3.maximumBytes)
        }
        let document = try native.read(offset: header.documentOffset, count: Int(header.documentLength))
        if kick {
            guard document == inertDocument else { throw GuestUIProtocolFailureV1(phase: phase, code: .document) }
            inertDocument = nil
            try v3.finishReadyWithoutInvocation(claim)
        } else if let hydrationCutoff {
            try v3.finishFieldLogHydration(claim, documentBytes: document, startupCutoff: hydrationCutoff)
        } else {
            try v3.finishTurn(claim, documentBytes: document)
            if phase == .startup { inertDocument = document }
        }
    }
#endif
    private func harvest(_ native: NativeCapabilitySession, claim: GuestUITurnClaimV1,
                         phase: GuestUIProtocolPhaseV1, initial: Bool = false,
                         allowsEmptyDocument: Bool = false, requiresEmptyDocument: Bool = false) throws {
        guard let v1, let headerOffset else { throw GuestUIProtocolFailureV1(phase: phase, code: .header) }
        let header = try GuestUIControlHeader.decode(native.read(offset: headerOffset, count: 32),
            headerOffset: headerOffset, phase: phase, allowsEmptyDocument: allowsEmptyDocument)
        if initial {
            // Copy once to let checked C memory bounds establish the entire
            // immutable event range before any event can be accepted.
            _ = try native.read(offset: header.eventOffset, count: Int(header.eventCapacity))
            eventOffset = header.eventOffset; eventCapacity = header.eventCapacity
        } else if eventOffset != header.eventOffset || eventCapacity != header.eventCapacity {
            throw GuestUIProtocolFailureV1(phase: phase, code: .bufferChanged)
        }
        if header.documentLength == 0 {
            guard header.documentOffset == 0 else { throw GuestUIProtocolFailureV1(phase: phase, code: .header) }
            if initial {
                initialDocument = .pendingHook
                try v1.finishStartupWithoutDocument(claim)
            } else {
                try v1.finishHydrationHook(claim)
            }
            return
        }
        guard !requiresEmptyDocument, !awaitingInitialDocument || postedHydrationSnapshot else {
            throw GuestUIProtocolFailureV1(phase: phase, code: .header)
        }
        let document = try native.read(offset: header.documentOffset, count: Int(header.documentLength))
        try requireInitialDocumentDeadline()
        try v1.finishTurn(claim, documentBytes: document,
            startupCutoff: awaitingInitialDocument ? startupCutoff : nil)
        if awaitingInitialDocument { initialDocument = .published }
    }
}
