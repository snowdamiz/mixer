import Foundation
import MixerExperimentalCapabilityRuntime
import MixerUpdates

/// Trusted embedding configuration. This value opens no file, creates no adapter
/// and grants no executable or health authority. Bounds are checked by open.
public struct CapabilityColdStartConfiguration: Sendable {
    public let directory: URL
    public let channel: String
    public let installation: String
    public let failureThreshold: UInt64
    public let observationSeconds: UInt64
    public let requiredMilestones: Set<String>
    public let reserveDiskBytes: UInt64
    public init(directory: URL, channel: String, installation: String,
                failureThreshold: UInt64 = 2, observationSeconds: UInt64 = 10,
                requiredMilestones: Set<String> = ["feature_started", "first_screen"],
                reserveDiskBytes: UInt64 = 16 * 1_048_576) {
        self.directory = directory; self.channel = channel; self.installation = installation
        self.failureThreshold = failureThreshold; self.observationSeconds = observationSeconds
        self.requiredMilestones = requiredMilestones; self.reserveDiskBytes = reserveDiskBytes
    }
    func checked() throws -> CapabilityRecoveryConfiguration {
        guard directory.isFileURL, directory.path.hasPrefix("/"),
              directory.path.utf8.prefix(4097).count <= 4096, !directory.path.utf8.contains(0),
              capabilityRecoveryIdentifier(channel), capabilityRecoveryIdentifier(installation),
              (1...10).contains(failureThreshold), (1...3600).contains(observationSeconds),
              (1...16).contains(requiredMilestones.count), requiredMilestones.allSatisfy(capabilityRecoveryIdentifier) else {
            throw coldStartError("configuration")
        }
        return CapabilityRecoveryConfiguration(directory: directory, channel: channel, installation: installation,
            failureThreshold: failureThreshold, observationSeconds: observationSeconds,
            requiredMilestones: requiredMilestones, reserveDiskBytes: reserveDiskBytes)
    }
}

public enum CapabilityActivationPhase: Sendable, Equatable {
    case idle, starting, provisionalGuest, healthyGuest, nativeFallback, stopping, recoveryRequired, closed
}
public enum CapabilityColdStartTerminalCause: Sendable, Equatable {
    case cancelled, deadline, closed
    case bridge(ExperimentalCapabilityFailure)
}
/// Observational diagnostics. Native fallback asks the embedding to use its
/// compiled implementation; this value never fabricates a healthy native guest.
public struct CapabilityActivationSnapshot: Sendable {
    public let phase: CapabilityActivationPhase
    public let candidateID: String?
    public let launchID: String?
    public let acceptedSequence: UInt64
    public let effectsMayHaveOpened: Bool
    public let terminalCause: CapabilityColdStartTerminalCause?
    public let firstBridgeFailure: ExperimentalCapabilityFailure?
    public let requiresReopen: Bool
    public let cleanupPending: Bool
}
/// Bounded durable diagnostics; paths, payloads and executable selections are not
/// returned. Healthy identifiers are stored observations, not execution proofs.
public struct CapabilityColdStartRecoverySnapshot: Sendable {
    public let activation: CapabilityActivationSnapshot
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
    init(_ value: CapabilityRecoverySnapshot, activation: CapabilityActivationSnapshot) {
        self.activation = activation
        requiresReopen = value.requiresReopen; closed = value.closed; busy = value.busy
        acceptedSequence = value.acceptedSequence; downloading = value.downloading
        staged = value.staged; healthy = value.healthy; previousHealthy = value.previousHealthy
        retainedCandidates = value.retainedCandidates; incompleteAttempt = value.incompleteAttempt
    }
}

func coldStartError(_ code: String) -> UpdateError {
    UpdateError("capability.runtime.\(code)", "Capability cold-start runtime rejected")
}
