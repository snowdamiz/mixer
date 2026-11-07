import Foundation
import MixerUI

public enum GuestUIProtocolPhaseV1: String, Sendable, Equatable {
    case validation, startup, event, wake, presentation
}
public enum GuestUIProtocolCodeV1: String, Sendable, Equatable {
    case requiredExport, startupResult, header, memoryRange, bufferChanged, document
    case revisionRegressed, sameRevisionMutation, eventEncoding, eventResult
    case sequenceExhausted, presentationInvariant
}
/// A diagnostic value; construction does not stop an owner or grant authority.
public struct GuestUIProtocolFailureV1: Error, Sendable, Equatable {
    public let phase: GuestUIProtocolPhaseV1
    public let code: GuestUIProtocolCodeV1
    public init(phase: GuestUIProtocolPhaseV1, code: GuestUIProtocolCodeV1) {
        self.phase = phase; self.code = code
    }
}
public enum GuestUIEffectStageV1: Sendable, Equatable { case beforeIntent, intentEntered }
public struct GuestUIProtocolTerminalV1: Sendable, Equatable {
    public let failure: GuestUIProtocolFailureV1
    public let effectStage: GuestUIEffectStageV1
}
public enum GuestUIStopV1: Sendable, Equatable {
    case bridge, cancelled, deadline, closed
    case protocolViolation(GuestUIProtocolTerminalV1)
}
@_spi(GuestUIV1) public enum GuestUIExternalStopV1: Sendable {
    case bridge, cancelled, deadline, closed
}
@_spi(GuestUIV1) public enum GuestUIControlRejectionV1: Error, Sendable, Equatable {
    case invalidGeneration, busy, closed, consumerAlreadyIssued, readerBusy, staleClaim
}
@_spi(GuestUIV1) public enum GuestUIProtocolV1 {
    public static let contractSHA256 = "34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024"
    public static let nativeHeaderSHA256 = "d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5"
    public static let startupExport = "mixer_guest_ui_start_v1"
    public static let eventExport = "mixer_guest_ui_event_v1"
    public static let readyExport = "mixer_guest_capability_ready_v1"
}

// Identity only, with no reference to an exchange, task, source or owner.
final class GuestUIIssuerV1: Sendable {}

@_spi(GuestUIV1) public enum GuestUITurnKindV1: Sendable {
    case startup, event(sequence: UInt64, bytes: Data), ready
}
@_spi(GuestUIV1) public struct GuestUITurnClaimV1: Sendable {
    let issuer: GuestUIIssuerV1
    public let generation: UInt64
    public let serial: UInt64
    public let kind: GuestUITurnKindV1
}
@_spi(GuestUIV1) public struct GuestUIFrameV1: Sendable {
    let issuer: GuestUIIssuerV1
    public let generation: UInt64
    public let serial: UInt64
    public let document: ValidatedUIDocument
}
@_spi(GuestUIV1) public enum GuestUIEventAdmissionV1: Sendable, Equatable {
    case accepted(sequence: UInt64), busy, stale, closed, invalid(UIRoutingError)
}
@_spi(GuestUIV1) public enum GuestUIEventOutcomeV1: Sendable, Equatable {
    case delivered, terminal(turnBegan: Bool)
}
@_spi(GuestUIV1) public struct GuestUIEventResultV1: Sendable, Equatable {
    public let generation: UInt64
    public let sequence: UInt64
    public let outcome: GuestUIEventOutcomeV1
}
@_spi(GuestUIV1) public struct GuestUIPresentationClaimV1: Sendable {
    let issuer: GuestUIIssuerV1
    public let generation: UInt64
    public let serial: UInt64
    public let frame: GuestUIFrameV1?
    public let eventResult: GuestUIEventResultV1?
    public let stop: GuestUIStopV1?
}
@_spi(GuestUIV1) public struct GuestUIPresentationTicketV1: Sendable {
    let issuer: GuestUIIssuerV1
    public let generation: UInt64
    public let frameSerial: UInt64
    public let revision: UInt64
}
@_spi(GuestUIV1) public struct GuestUIPresentationReceiptV1: Sendable, Equatable {
    public let generation: UInt64
    public let frameSerial: UInt64
    public let revision: UInt64
}
@_spi(GuestUIV1) public struct GuestUIExchangeCountersV1: Sendable {
    public internal(set) var successfulTurns: UInt64 = 0
    public internal(set) var producedFrames: UInt64 = 0
    public internal(set) var replacedPendingFrames: UInt64 = 0
    public internal(set) var acceptedEvents: UInt64 = 0
    public internal(set) var deliveredEvents: UInt64 = 0
    public internal(set) var terminalEvents: UInt64 = 0
    public internal(set) var maximumPendingFrames: UInt64 = 0
    public internal(set) var maximumClaimedFrames: UInt64 = 0
    public internal(set) var maximumEventSlots: UInt64 = 0
    public internal(set) var maximumEventBytes: UInt64 = 0
    public internal(set) var maximumRawDocumentBytes: UInt64 = 0
}
@_spi(GuestUIV1) public struct GuestUIExchangeSnapshotV1: Sendable {
    public let generation: UInt64
    public let stop: GuestUIStopV1?
    public let effectsMayHaveOpened: Bool
    public let effectsConfirmed: Bool
    public let hasStarted: Bool
    public let guestTurnInFlight: Bool
    public let eventOutstanding: Bool
    public let presentationInFlight: Bool
    public let latestRevision: UInt64?
    public let displayedRevision: UInt64?
    public let pendingPresentationReceipt: GuestUIPresentationReceiptV1?
    public let firstUIProtocolFailure: GuestUIProtocolTerminalV1?
    public let counters: GuestUIExchangeCountersV1
}

func guestUIIdentifierV1(_ value: String) -> Bool {
    !value.isEmpty && value.utf8.count <= 128 &&
        !value.unicodeScalars.contains { $0.value < 0x20 || $0.value == 0x7f }
}
