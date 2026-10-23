import Foundation
import MixerExperimentalCapabilityRuntime
@_spi(GuestUIV1) import MixerGuest

public typealias CapabilityGuestUITerminalCause = GuestUIStopV1

/// Observations only. These values cannot select code, deliver an event or
/// acknowledge presentation. Native detail may arrive after the shared stop.
public struct CapabilityGuestUIActivationSnapshot: Sendable {
    public let phase: CapabilityActivationPhase
    public let candidateID: String?
    public let launchID: String?
    public let acceptedSequence: UInt64
    public let effectsMayHaveOpened: Bool
    public let terminalCause: CapabilityGuestUITerminalCause?
    public let firstBridgeFailure: ExperimentalCapabilityFailure?
    public let firstUIProtocolFailure: GuestUIProtocolTerminalV1?
    public let requiresReopen: Bool
    public let cleanupPending: Bool

    init(_ base: CapabilityActivationSnapshot, ui: GuestUIExchangeSnapshotV1?) {
        phase = base.phase; candidateID = base.candidateID; launchID = base.launchID
        acceptedSequence = base.acceptedSequence
        effectsMayHaveOpened = ui?.effectsMayHaveOpened ?? base.effectsMayHaveOpened
        terminalCause = ui?.stop; firstBridgeFailure = base.firstBridgeFailure
        firstUIProtocolFailure = ui?.firstUIProtocolFailure
        requiresReopen = base.requiresReopen; cleanupPending = base.cleanupPending
    }
}

public struct CapabilityGuestUIRecoverySnapshot: Sendable {
    public let activation: CapabilityGuestUIActivationSnapshot
    public let requiresReopen: Bool
    public let closed: Bool
    public let busy: Bool
    public let acceptedSequence: UInt64
    public let downloading: String?
    public let staged: String?
    public let healthy: String?
    public let previousHealthy: String?
    public let retainedCandidates: Int
    public let incompleteAttempt: Bool

    init(_ value: CapabilityRecoverySnapshot, activation: CapabilityGuestUIActivationSnapshot) {
        self.activation = activation
        requiresReopen = value.requiresReopen; closed = value.closed; busy = value.busy
        acceptedSequence = value.acceptedSequence; downloading = value.downloading
        staged = value.staged; healthy = value.healthy; previousHealthy = value.previousHealthy
        retainedCandidates = value.retainedCandidates; incompleteAttempt = value.incompleteAttempt
    }
}
