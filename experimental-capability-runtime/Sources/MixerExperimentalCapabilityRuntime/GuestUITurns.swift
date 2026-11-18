import Foundation
@_spi(GuestUIV1) import MixerGuest

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
    let exchange: GuestUIExchangeV1
    private var headerOffset: UInt32?
    private var eventOffset: UInt32?
    private var eventCapacity: UInt32?
    private enum InitialDocument { case immediate, pendingHook, awaitingRead, published }
    private var initialDocument = InitialDocument.immediate
    private var startupCutoff: UInt64?
    private var didTakeHydrationRead = false
    private var postedHydrationSnapshot = false
    private(set) var nativeTurns: UInt64 = 0

    var awaitingInitialDocument: Bool { initialDocument == .pendingHook || initialDocument == .awaitingRead }
    var publishedHydration: Bool { initialDocument == .published }
    func setStartupCutoff(_ cutoff: UInt64?) { startupCutoff = cutoff }
    func acceptsHydrationOperation(isRead: Bool) -> Bool {
        if initialDocument == .immediate { return true }
        guard initialDocument == .awaitingRead, isRead, !didTakeHydrationRead else { return false }
        didTakeHydrationRead = true
        return true
    }
    func didPostHydrationSnapshot() {
        if initialDocument == .awaitingRead { postedHydrationSnapshot = true }
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
    init(exchange: GuestUIExchangeV1) { self.exchange = exchange }
    static func requireLive(_ exchange: GuestUIExchangeV1) throws {
        try exchange.requireCommitEntry(generation: exchange.snapshot().generation)
    }
    var stopped: Bool { exchange.snapshot().stop != nil }
    func requireEffectAdmission() throws {
        try exchange.requireEffectAdmission(generation: exchange.snapshot().generation)
    }
    func startup(_ native: NativeCapabilitySession) throws {
        let claim = try exchange.claimStartup()
        let result = try native.startup()
        if nativeTurns < .max { nativeTurns += 1 }
        guard case .i32(let raw) = result.value else { throw GuestUIProtocolFailureV1(phase: .startup, code: .startupResult) }
        let offset = UInt32(bitPattern: raw)
        _ = try GuestUIControlHeader.checkedEnd(offset, 32, phase: .startup)
        headerOffset = offset
        try harvest(native, claim: claim, phase: .startup, initial: true, allowsEmptyDocument: exchange.allowsDeferredStartup)
    }
    /// nil is no available claim; false means a claimed native ready check did
    /// not execute guest code. Both leave turn accounting unchanged.
    func next(_ native: NativeCapabilitySession, ready: Bool) throws -> Bool? {
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
            return true
        }
        guard let claim = try exchange.claimNextTurn(ready: ready && !publishedHydration) else { return nil }
        switch claim.kind {
        case .startup:
            throw GuestUIProtocolFailureV1(phase: .startup, code: .startupResult)
        case .event(_, let bytes):
            guard let eventOffset, let eventCapacity, bytes.count <= Int(eventCapacity) else {
                throw GuestUIProtocolFailureV1(phase: .event, code: .eventEncoding)
            }
            initialDocument = .immediate
            // One claimed worker operation. No pump wake can split this pair.
            try native.write(offset: eventOffset, data: bytes)
            let result = try native.invoke("mixer_guest_ui_event_v1", arguments: [.i32(Int32(bytes.count))])
            if nativeTurns < .max { nativeTurns += 1 }
            guard result.value == .i32(0) else { throw GuestUIProtocolFailureV1(phase: .event, code: .eventResult) }
            try harvest(native, claim: claim, phase: .event)
            return true
        case .ready:
            guard try native.wake() else {
                try exchange.finishReadyWithoutInvocation(claim)
                return false
            }
            if nativeTurns < .max { nativeTurns += 1 }
            try harvest(native, claim: claim, phase: .wake)
            return true
        }
    }
    private func harvest(_ native: NativeCapabilitySession, claim: GuestUITurnClaimV1,
                         phase: GuestUIProtocolPhaseV1, initial: Bool = false,
                         allowsEmptyDocument: Bool = false, requiresEmptyDocument: Bool = false) throws {
        guard let headerOffset else { throw GuestUIProtocolFailureV1(phase: phase, code: .header) }
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
                try exchange.finishStartupWithoutDocument(claim)
            } else {
                try exchange.finishHydrationHook(claim)
            }
            return
        }
        guard !requiresEmptyDocument, !awaitingInitialDocument || postedHydrationSnapshot else {
            throw GuestUIProtocolFailureV1(phase: phase, code: .header)
        }
        let document = try native.read(offset: header.documentOffset, count: Int(header.documentLength))
        try requireInitialDocumentDeadline()
        try exchange.finishTurn(claim, documentBytes: document,
            startupCutoff: awaitingInitialDocument ? startupCutoff : nil)
        if awaitingInitialDocument { initialDocument = .published }
    }
}
