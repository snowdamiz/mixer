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
    static func decode(_ bytes: Data, headerOffset: UInt32, phase: GuestUIProtocolPhaseV1) throws -> Self {
        func word(_ offset: Int) -> UInt32 {
            (0..<4).reduce(UInt32(0)) { $0 | UInt32(bytes[offset + $1]) << ($1 * 8) }
        }
        guard bytes.count == 32 else { throw GuestUIProtocolFailureV1(phase: phase, code: .header) }
        guard word(0) == 0x3155494d, word(4) == 32, (1...65536).contains(word(12)), word(20) == 4096,
              bytes[24..<32].allSatisfy({ $0 == 0 }) else { throw GuestUIProtocolFailureV1(phase: phase, code: .header) }
        let header = Self(documentOffset: word(8), documentLength: word(12), eventOffset: word(16), eventCapacity: word(20))
        let ranges = [(headerOffset, UInt32(32)), (header.documentOffset, header.documentLength), (header.eventOffset, header.eventCapacity)]
        var ends: [UInt32] = []
        for range in ranges { ends.append(try checkedEnd(range.0, range.1, phase: phase)) }
        for first in 0..<3 {
            for second in (first + 1)..<3 where ranges[first].0 < ends[second] && ranges[second].0 < ends[first] {
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
    private(set) var nativeTurns: UInt64 = 0
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
        try harvest(native, claim: claim, phase: .startup, initial: true)
    }
    /// nil is no available claim; false means a claimed native ready check did
    /// not execute guest code. Both leave turn accounting unchanged.
    func next(_ native: NativeCapabilitySession, ready: Bool) throws -> Bool? {
        guard let claim = try exchange.claimNextTurn(ready: ready) else { return nil }
        switch claim.kind {
        case .startup:
            throw GuestUIProtocolFailureV1(phase: .startup, code: .startupResult)
        case .event(_, let bytes):
            guard let eventOffset, let eventCapacity, bytes.count <= Int(eventCapacity) else {
                throw GuestUIProtocolFailureV1(phase: .event, code: .eventEncoding)
            }
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
                         phase: GuestUIProtocolPhaseV1, initial: Bool = false) throws {
        guard let headerOffset else { throw GuestUIProtocolFailureV1(phase: phase, code: .header) }
        let header = try GuestUIControlHeader.decode(native.read(offset: headerOffset, count: 32), headerOffset: headerOffset, phase: phase)
        if initial {
            // Copy once to let checked C memory bounds establish the entire
            // immutable event range before any event can be accepted.
            _ = try native.read(offset: header.eventOffset, count: Int(header.eventCapacity))
            eventOffset = header.eventOffset; eventCapacity = header.eventCapacity
        } else if eventOffset != header.eventOffset || eventCapacity != header.eventCapacity {
            throw GuestUIProtocolFailureV1(phase: phase, code: .bufferChanged)
        }
        let document = try native.read(offset: header.documentOffset, count: Int(header.documentLength))
        try exchange.finishTurn(claim, documentBytes: document)
    }
}
