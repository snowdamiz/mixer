import Foundation
import MixerCapabilityActivation

/// Example trusted native embedding. These callbacks must be connected to real
/// native feature-start/first-screen observations. Startup success does not call
/// either callback and never constitutes health evidence by itself.
final class NativeFeatureEmbedding: Sendable {
    let runtime: CapabilityColdStartRuntime
    init(runtime: CapabilityColdStartRuntime) { self.runtime = runtime }
    func start() async throws -> CapabilityActivationSnapshot { try await runtime.start() }
    func nativeFeatureDidStart() async throws { try await runtime.reportMilestone("feature_started") }
    func nativeFirstScreenWasPresented() async throws { try await runtime.reportMilestone("first_screen") }
    func close() async { await runtime.close() }
}

@main struct PublicColdStartConsumer {
    static func main() async throws {
        let fixtures=URL(fileURLWithPath: CommandLine.arguments[1]), root=URL(fileURLWithPath: CommandLine.arguments[2])
        func bytes(_ name: String) throws -> Data { try Data(contentsOf: fixtures.appendingPathComponent(name)) }
        let execution=try InstalledCapabilityExecution(identityJSON: bytes("identity.json"),materials: [
            .init(role: .bridgePolicy,bytes: bytes("bridge.json")),
            .init(role: .configuration(capabilityID: "network.http.v1"),bytes: bytes("http.json")),
            .init(role: .configuration(capabilityID: "storage.keyValue.v1"),bytes: bytes("storage.json")),
            .init(role: .installedGrant(capabilityID: "network.http.v1"),bytes: bytes("http-grant.json")),
            .init(role: .installedGrant(capabilityID: "storage.keyValue.v1"),bytes: bytes("storage-grant.json"))],
            trustRootsJSON: bytes("roots.json"),privateContainer: root)
        let runtime=try await CapabilityColdStartRuntime.open(configuration: .init(directory: root.appendingPathComponent("recovery"),channel: "beta",installation: "public-consumer"),execution: execution)
        let embedding=NativeFeatureEmbedding(runtime: runtime), snapshot=try await embedding.start()
        guard snapshot.phase == .nativeFallback else { throw NSError(domain:"consumer.unexpectedGuest",code:1) }
        // No signed candidate and no real screen are produced by this smoke:
        // the actual native observation methods above are compiled, not invoked.
        await embedding.close(); print("PASS public consumer native fallback and explicit real-native milestone API example; no UI/health claim")
    }
}
