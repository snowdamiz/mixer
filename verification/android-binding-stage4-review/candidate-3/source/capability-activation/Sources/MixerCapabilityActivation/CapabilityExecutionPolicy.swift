import Foundation
import MixerCapabilities
import MixerExperimentalCapabilityRuntime
@_spi(CapabilityDurableV3) import MixerUpdates

/// Pure derivation from enclosing evidence and the one captured verifier context.
/// This value is internal configuration, never a selection or execution proof.
/// Retained provenance and one-shot admission remain the private store's duties.
struct CapabilityExecutionPolicy: Sendable {
    struct HTTP: Sendable {
        let maximumConcurrentRequests: UInt32
        let origins: Set<String>
        let methods: Set<String>
    }
    struct Storage: Sendable {
        let directoryComponent: String
        let maximumTotalBytes: Int
        let maximumEntries: Int
        let namespaces: Set<String>
    }
    let native: ExperimentalCapabilityConfiguration
    let startupMilliseconds: UInt64
    let policy: CapabilityPolicy
    let http: HTTP?
    let storage: Storage?

    init(installed: InstalledMaterial, artifact: VerifiedArtifactV3, payload: Data, now: UInt64) throws {
        let checked = try installed.verifier.revalidateArtifact(artifact, payload: payload, now: now)
        try self.init(installed: installed, limits: checked.resourceLimits, grants: checked.capabilityGrants)
    }
    init(installed: InstalledMaterial, retained: RetainedHealthyEvidenceV3, payload: Data) throws {
        let checked = try installed.verifier._revalidateRetainedHealthyV3(retained, payload: payload)
        try self.init(installed: installed, limits: checked.resourceLimits, grants: checked.capabilityGrants)
    }
    private init(installed: InstalledMaterial, limits: ResourceLimits, grants: VerifiedCapabilityGrantsV3) throws {
        let nativeGrants = installed.grants.values.map {
            CapabilityGrant(capabilityID: $0.capabilityID, schemaSHA256: $0.schemaSHA256,
                permissions: Set($0.permissions), origins: Set($0.origins), methods: Set($0.methods), namespaces: Set($0.namespaces))
        }
        let signedGrants = grants.entries.map {
            CapabilityGrant(capabilityID: $0.capabilityID, schemaSHA256: $0.schemaSHA256,
                permissions: Set($0.permissions), origins: Set($0.origins), methods: Set($0.methods), namespaces: Set($0.namespaces))
        }
        // The SDK independently validates and intersects both sets for dispatch.
        policy = try CapabilityPolicy(installed: nativeGrants, manifest: signedGrants)
        native = Self.nativeConfiguration(installed: installed, signed: limits)
        startupMilliseconds = min(limits.startupMilliseconds, installed.identity.installedRuntime.limits.startupMilliseconds)

        // Adapter admission uses the same separate inputs. An empty dimension
        // denies the family; never invent a namespace or widen an origin/method.
        var http: HTTP?, storage: Storage?
        for signed in signedGrants {
            guard let original = installed.grants[signed.capabilityID] else { continue }
            let permissions = Set(original.permissions).intersection(signed.permissions)
            switch installed.configurations[signed.capabilityID] {
            case .http(let maximum)? where signed.capabilityID == CapabilitySchemas.httpID:
                let origins = Set(original.origins).intersection(signed.origins)
                let methods = Set(original.methods).intersection(signed.methods)
                if permissions.contains("network.https"), !origins.isEmpty, !methods.isEmpty {
                    http = HTTP(maximumConcurrentRequests: maximum, origins: origins, methods: methods)
                }
            case .storage(let component, let bytes, let entries)? where signed.capabilityID == CapabilitySchemas.storageID:
                let namespaces = Set(original.namespaces).intersection(signed.namespaces)
                if permissions.contains("storage.appPrivate"), !namespaces.isEmpty {
                    storage = Storage(directoryComponent: component, maximumTotalBytes: bytes,
                        maximumEntries: entries, namespaces: namespaces)
                }
            default: break
            }
        }
        self.http = http; self.storage = storage
    }

    /// Configuration only: no native validation or execution is implied.
    static func nativeConfiguration(installed: InstalledMaterial, signed: ResourceLimits) -> ExperimentalCapabilityConfiguration {
        let identity = installed.identity, host = identity.installedRuntime.limits, capability = identity.capabilityExecution
        return ExperimentalCapabilityConfiguration(fuel: min(signed.fuel, host.fuel),
            memoryPages: UInt32(min(signed.memoryBytes, host.memoryBytes) / 65_536),
            operandStack: identity.execution.operandStack, callDepth: identity.execution.callDepth,
            hostCalls: UInt32(identity.execution.hostCalls), maximumRequests: capability.maximumRequests,
            reservationBytes: capability.reservationBytes, timeoutMilliseconds: UInt32(capability.timeoutMilliseconds),
            turnMilliseconds: UInt32(capability.turnMilliseconds), dispatchBurst: installed.bridge.burst,
            dispatchesPerSecond: installed.bridge.startsPerSecond, batchTurns: 4, batchMilliseconds: 8)
    }
}
