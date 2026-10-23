import Foundation
import Testing
import Crypto
import MixerUpdates
import MixerRuntime
import MixerRuntimeIdentity
import MixerActivation

private func executionReviewDescriptor() throws -> CanonicalValue {
    let fixture = try #require(Bundle.module.url(forResource: "runtime-identity", withExtension: "json", subdirectory: "Fixtures"))
    return try JSONDecoder().decode(CanonicalValue.self, from: Data(contentsOf: fixture))
}
struct IndependentIdentityExecutionTests {
    @Test func subpageMemoryCeilingsAlwaysRoundDownAndNeverExpandNativeAuthority() throws {
        let descriptor = try executionReviewDescriptor()
        for bytes: UInt64 in [1, 65535, 65536, 65537, 4194303, 4194304] {
            var root = descriptor.object!, execution = root["execution"]!.object!
            execution["memory_bytes"] = .uint(bytes); root["execution"] = .object(execution)
            let identity = try RuntimeIdentity(json: JSONEncoder().encode(CanonicalValue.object(root)))
            let installed = try InstalledExecution(identity: identity)
            #expect(UInt64(installed.limits.memoryPages) * 65536 <= bytes)
            #expect(installed.limits.memoryPages == UInt32(bytes / 65536))
            #expect(identity.installedRuntime.limits.memoryBytes == bytes)
        }
    }
    @Test func profilesAreExactAndLegacyTrustedStringAPIKeepsItsDeclaredSemantics() async throws {
        let descriptor = try executionReviewDescriptor()
        for (name, profile) in [("mixer-integer-v1", VMProfile.integerV1), ("mixer-numeric-v2", .numericV2), ("mixer-table-memory-v3", .tableMemoryV3)] {
            var root = descriptor.object!, engine = root["engine"]!.object!
            engine["profile"] = .text(name); root["engine"] = .object(engine)
            let identity = try RuntimeIdentity(json: JSONEncoder().encode(CanonicalValue.object(root)))
            #expect(try InstalledExecution(identity: identity).profile == profile)
        }
        let identity = try RuntimeIdentity(json: JSONEncoder().encode(descriptor)), host = identity.installedRuntime
        let legacy = try InstalledExecution(runtimeFingerprint: identity.fingerprint, profile: .integerV1, startupExport: "run")
        let changed = InstalledRuntime(scope: host.scope, runtime: host.runtime, protocolVersion: 1, guestABI: host.guestABI,
            uiSchema: host.uiSchema, capabilityHashes: [:], stateVersion: host.stateVersion + 1, maxPayloadBytes: 999, limits: host.limits)
        let key = Curve25519.Signing.PrivateKey()
        let verifier = try ReleaseVerifier(host: changed, roots: [TrustRoot(keyID: "review-key", publicKey: key.publicKey.rawRepresentation,
            scope: host.scope, artifact: true, assignment: true)])
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("identity-legacy-review-\(UUID())")
        defer { try? FileManager.default.removeItem(at: directory) }
        // This explicit legacy API trusts manually supplied installed policy; it
        // has no descriptor binding and must not silently pretend otherwise.
        let runtime = try ColdStartRuntime.open(configuration: ColdStartConfiguration(directory: directory, channel: "review",
            installation: "review-installation", reserveDiskBytes: 0), verifier: verifier, execution: legacy)
        await runtime.close()
    }
}
