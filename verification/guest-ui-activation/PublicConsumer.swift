import Foundation
import MixerCapabilityActivation

@main struct PublicGuestUIConsumer {
    @MainActor static func main() async throws {
        let fixtures = URL(fileURLWithPath: CommandLine.arguments[1])
        let root = URL(fileURLWithPath: CommandLine.arguments[2])
        func bytes(_ name: String) throws -> Data { try Data(contentsOf: fixtures.appendingPathComponent(name)) }
        var identity = try JSONSerialization.jsonObject(with: bytes("identity.json")) as! [String: Any]
        var mode = identity["execution"] as! [String: Any]
        mode["startup_export"] = "mixer_guest_ui_start_v1"; identity["execution"] = mode
        var dependencies = identity["dependencies"] as! [[String: Any]]
        dependencies += [
            ["id":"mixer.guest-ui-event-v1","version":"1","artifact_sha256":"34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024"],
            ["id":"mixer.guest-ui-native-header-v1","version":"1","artifact_sha256":"d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5"]]
        identity["dependencies"] = dependencies.sorted { ($0["id"] as! String) < ($1["id"] as! String) }
        let execution = try InstalledCapabilityExecution(
            identityJSON: JSONSerialization.data(withJSONObject:identity,options:[.sortedKeys,.withoutEscapingSlashes]),
            materials: [
                .init(role:.bridgePolicy,bytes:bytes("bridge.json")),
                .init(role:.configuration(capabilityID:"network.http.v1"),bytes:bytes("http.json")),
                .init(role:.configuration(capabilityID:"storage.keyValue.v1"),bytes:bytes("storage.json")),
                .init(role:.installedGrant(capabilityID:"network.http.v1"),bytes:bytes("http-grant.json")),
                .init(role:.installedGrant(capabilityID:"storage.keyValue.v1"),bytes:bytes("storage-grant.json"))],
            trustRootsJSON:bytes("roots.json"),privateContainer:root)
        let runtime = try await CapabilityGuestUIRuntime.open(
            configuration:.init(directory:root.appendingPathComponent("recovery"),channel:"beta",installation:"public-ui-consumer"),execution:execution)
        let presentation: GuestUIPresentation = runtime.presentation
        let screen = MixerGuestScreen(presentation:presentation)
        withExtendedLifetime(screen) {}
        let snapshot = try await runtime.start()
        guard snapshot.phase == .nativeFallback, presentation.state == .waiting else {
            throw NSError(domain:"consumer.unexpectedGuest",code:1)
        }
        await runtime.close()
        print("PASS ordinary-import public UI facade and wrapper; empty signed store selects native fallback. No native display or health claim.")
    }
}
