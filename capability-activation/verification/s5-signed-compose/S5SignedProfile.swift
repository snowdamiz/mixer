#if MIXER_S5_SIGNED_COMPOSE
import MixerRuntimeIdentity
import MixerUpdates

enum S5SignedProfile {
    static let scope = UpdateScope(organization: "mixer-local", project: "s5", app: "signed-compose-v2",
                                   environment: "development", platform: "android")
    static let bundle = "dev.mixer.compose.s5.signed.v2"
    static let startup = "mixer_guest_ui_start_v2"
    // The document retains its UI schema-1 envelope. These independent version-2
    // dependencies identify the experimental event and control-header contracts.
    static let dependencies: [CanonicalValue] = [
        .object(["id": .text("mixer.guest-ui-event-v2"), "version": .text("2"),
                 "artifact_sha256": .text("0dfb6a99a9d06235739f5735c32d39ee1494147bedafc88bba49bbb7d3b48106")]),
        .object(["id": .text("mixer.guest-ui-native-header-v2"), "version": .text("2"),
                 "artifact_sha256": .text("be7ebb2da4836351c54b7f431a34722c35aed5ef003e806cd5b0607d48b54ea0")]),
    ]

    static func matches(_ identity: CapabilityRuntimeIdentity) -> Bool {
        let descriptor = identity.descriptor.object
        return identity.installedRuntime.scope == scope && identity.installedRuntime.uiSchema == 1 &&
            identity.execution.startupExport == startup && identity.capabilities.map(\.id) == ["storage.keyValue.v1"] &&
            descriptor?["application"]?.object?["bundle_id"]?.text == bundle &&
            descriptor?["platform"]?.object?["target"]?.text == "aarch64-unknown-linux-android28" &&
            descriptor?["build"]?.object?["configuration"]?.text == "debug" &&
            descriptor?["dependencies"] == .array(dependencies)
    }

    static func require(_ identity: CapabilityRuntimeIdentity, milestones: Set<String>) throws {
        guard matches(identity), milestones == ["feature_started", "first_screen"] else {
            throw coldStartError("installed_mode")
        }
    }
}
#endif
