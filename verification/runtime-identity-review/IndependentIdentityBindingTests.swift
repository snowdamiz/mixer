import Foundation
import Testing
import Crypto
import MixerUpdates
import MixerRuntimeIdentity
import MixerActivation

@Suite(.serialized)
struct IndependentIdentityBindingTests {
    @Test func descriptorBoundExecutionRejectsEveryDifferentRepresentedHostPolicy() async throws {
        let fixture = try #require(Bundle.module.url(forResource: "runtime-identity", withExtension: "json", subdirectory: "Fixtures"))
        let identity = try RuntimeIdentity(json: Data(contentsOf: fixture))
        let execution = try InstalledExecution(identity: identity)
        let original = identity.installedRuntime
        func host(scope: UpdateScope? = nil, protocolVersion: UInt64? = nil, state: UInt64? = nil,
                  payload: UInt64? = nil, limits: ResourceLimits? = nil) -> InstalledRuntime {
            InstalledRuntime(scope: scope ?? original.scope, runtime: original.runtime,
                protocolVersion: protocolVersion ?? original.protocolVersion,
                guestABI: original.guestABI, uiSchema: original.uiSchema, capabilityHashes: original.capabilityHashes,
                stateVersion: state ?? original.stateVersion, maxPayloadBytes: payload ?? original.maxPayloadBytes,
                limits: limits ?? original.limits)
        }
        let changedScope = UpdateScope(organization: original.scope.organization, project: original.scope.project,
            app: "different-app", environment: original.scope.environment, platform: original.scope.platform)
        let cases: [(String, InstalledRuntime)] = [
            ("scope", host(scope: changedScope)), ("protocol", host(protocolVersion: 1)),
            ("state", host(state: original.stateVersion + 1)), ("payload", host(payload: 999)),
            ("memory", host(limits: ResourceLimits(memoryBytes: 65536, fuel: original.limits.fuel, startupMilliseconds: original.limits.startupMilliseconds))),
            ("fuel", host(limits: ResourceLimits(memoryBytes: original.limits.memoryBytes, fuel: 1, startupMilliseconds: original.limits.startupMilliseconds))),
            ("startup", host(limits: ResourceLimits(memoryBytes: original.limits.memoryBytes, fuel: original.limits.fuel, startupMilliseconds: 1)))
        ]
        let key = Curve25519.Signing.PrivateKey() // Ephemeral, never persisted.
        for (name, changed) in cases {
            let directory = FileManager.default.temporaryDirectory.appendingPathComponent("identity-policy-review-\(UUID())")
            defer { try? FileManager.default.removeItem(at: directory) }
            let verifier = try ReleaseVerifier(host: changed, roots: [TrustRoot(keyID: "review-key", publicKey: key.publicKey.rawRepresentation,
                scope: changed.scope, artifact: true, assignment: true)])
            do {
                let runtime = try ColdStartRuntime.open(configuration: ColdStartConfiguration(directory: directory,
                    channel: "review", installation: "review-installation", reserveDiskBytes: 0), verifier: verifier, execution: execution)
                await runtime.close()
                Issue.record("descriptor-derived execution accepted same-fingerprint mismatched host: \(name)")
            } catch let error as UpdateError {
                #expect(error.code == "activation.compatibility", "\(name): \(error)")
            }
        }
    }
}
