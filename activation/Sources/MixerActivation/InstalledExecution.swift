import Foundation
import MixerRuntime
import MixerUpdates
import MixerRuntimeIdentity

/// Trusted native configuration compiled into an installed binary. The release
/// cannot choose a profile, entry point, native implementation or higher ceiling.
/// The embedding must compute its fingerprint from its complete installed build;
/// this local package does not attest or publish that build.
public struct InstalledExecution: Sendable {
    public let runtimeFingerprint: String
    public let profile: VMProfile
    public let limits: VMLimits
    public let startupExport: String
    public let maximumStartupMilliseconds: UInt64

    /// Derive execution and verifier policy from the same immutable descriptor.
    /// Build-input completeness and actual binary embedding remain the native
    /// build pipeline's responsibility. This cannot enable unimplemented imports.
    public init(identity: RuntimeIdentity) throws {
        let profile: VMProfile
        switch identity.execution.profile {
        case "mixer-integer-v1": profile = .integerV1
        case "mixer-numeric-v2": profile = .numericV2
        case "mixer-table-memory-v3": profile = .tableMemoryV3
        default: throw UpdateError("activation.configuration", "Unsupported identity profile")
        }
        let host = identity.installedRuntime
        try self.init(runtimeFingerprint: identity.fingerprint, profile: profile,
            limits: VMLimits(fuel: host.limits.fuel, memoryPages: UInt32(host.limits.memoryBytes / 65_536),
                operandStack: identity.execution.operandStack, callDepth: identity.execution.callDepth,
                hostCalls: UInt32(identity.execution.hostCalls)),
            startupExport: identity.execution.startupExport, maximumStartupMilliseconds: host.limits.startupMilliseconds)
        try check(host)
    }

    public init(runtimeFingerprint: String, profile: VMProfile, limits: VMLimits = VMLimits(),
                startupExport: String, maximumStartupMilliseconds: UInt64 = 1_000) throws {
        guard runtimeFingerprint.utf8.count == 64,
              runtimeFingerprint.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
              !startupExport.isEmpty, startupExport.utf8.count <= 4096,
              (1...60_000).contains(maximumStartupMilliseconds),
              limits.fuel <= 1_000_000, limits.memoryPages <= 64,
              (1...4096).contains(limits.operandStack), (1...64).contains(limits.callDepth),
              limits.hostCalls <= 1024 else {
            throw UpdateError("activation.configuration", "Invalid installed execution contract")
        }
        self.runtimeFingerprint = runtimeFingerprint; self.profile = profile; self.limits = limits
        self.startupExport = startupExport; self.maximumStartupMilliseconds = maximumStartupMilliseconds
    }

    func check(_ host: InstalledRuntime) throws {
        guard host.runtime == runtimeFingerprint, host.guestABI == 1,
              host.capabilityHashes.isEmpty, host.maxPayloadBytes <= 4_194_304 else {
            throw UpdateError("activation.compatibility", "Installed bounded VM cannot provide this runtime contract")
        }
    }

    func boundedLimits(_ artifact: VerifiedArtifact) throws -> VMLimits {
        guard artifact.manifest.object?["runtime"]?.text == runtimeFingerprint,
              artifact.manifest.object?["capability_hashes"]?.object?.isEmpty == true,
              artifact.capabilityGrants?.entries.isEmpty != false,
              artifact.resourceLimits.memoryBytes > 0, artifact.resourceLimits.fuel > 0 else {
            throw UpdateError("activation.binding", "Verified artifact does not bind the installed VM policy")
        }
        // memory_bytes bounds linear memory. Decoder/frame/process memory remains
        // bounded by the unchanged VM profile; this is not a total-RSS guarantee.
        return VMLimits(fuel: min(limits.fuel, artifact.resourceLimits.fuel),
            memoryPages: UInt32(min(UInt64(limits.memoryPages), artifact.resourceLimits.memoryBytes / 65_536)),
            operandStack: limits.operandStack, callDepth: limits.callDepth, hostCalls: limits.hostCalls)
    }

    func startupMilliseconds(_ artifact: VerifiedArtifact) throws -> UInt64 {
        guard artifact.resourceLimits.startupMilliseconds > 0 else { throw UpdateError("activation.binding", "Missing signed startup budget") }
        return min(maximumStartupMilliseconds, artifact.resourceLimits.startupMilliseconds)
    }

    func validate(_ payload: Data, artifact: VerifiedArtifact) throws {
        guard UInt64(payload.count) == artifact.payloadBytes,
              ReleaseVerifier.sha256(payload) == artifact.payloadSHA256 else {
            throw UpdateError("activation.binding", "Payload differs from verified selection")
        }
        try VMValidator.validate(payload, profile: profile, limits: boundedLimits(artifact))
    }
}
