import MixerRuntimeIdentity
import MixerUpdates

/// A pure check of already captured installed identity. Passing this check is
/// not executable selection, validation, adapter creation or UI health.
enum CapabilityInstalledExecutionMode {
    static let startup = "mixer_guest_ui_start_v1"
    static let contractID = "mixer.guest-ui-event-v1"
    static let deferredStartupID = "mixer.guest-ui-deferred-startup-v1"
    static let deferredStartupSHA256 = "cdc8e301305ecfd6abe40872df55d90dce86ea816781904c45d1fa119d2da260"
    static let headerID = "mixer.guest-ui-native-header-v1"
    static let contractSHA256 = "34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024"
    static let headerSHA256 = "d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5"

    static let f10Startup = "mixer_guest_ui_start_v3"
    static let f10WireID = "mixer.guest-ui-event-v3"
    static let f10HeaderID = "mixer.guest-ui-native-header-v3"
#if os(macOS) && MIXER_PRIVATE_F10
    static let f10WireSHA256 = "2aa7ea5a007be20decffb7a35f450e89e7e77691bbaef4694c7f9456ba7787fc"
    static let f10HeaderSHA256 = "875c5d4c81ed0e98fd334d198eae26e8287b6f1f47baa93b36a470380aa2d8d9"

    static func requirePrivateF10(_ identity: CapabilityRuntimeIdentity, milestones: Set<String>) throws {
        let dependencies = try entries(identity)
        guard identity.execution.startupExport == f10Startup, milestones == ["feature_started", "first_screen"],
              identity.installedRuntime.uiSchema == 3,
              !dependencies.contains(where: { entry in
                  [contractID, headerID, deferredStartupID, "mixer.guest-ui-event-v2", "mixer.guest-ui-native-header-v2"]
                    .contains(entry.object?["id"]?.text ?? "")
              }) else { throw rejection() }
        for (id, digest) in [(f10WireID, f10WireSHA256), (f10HeaderID, f10HeaderSHA256)] {
            guard let fields = dependencies.first(where: { $0.object?["id"]?.text == id })?.object,
                  fields["version"]?.text == "3", fields["artifact_sha256"]?.text == digest else { throw rejection() }
        }
    }
#endif

    static func requireCapabilityOnly(_ identity: CapabilityRuntimeIdentity) throws {
        let dependencies = try entriesRejectingOtherProfiles(identity)
        guard identity.execution.startupExport != startup,
              !dependencies.contains(where: { entry in
                  let id = entry.object?["id"]?.text
                  return id == contractID || id == headerID || id == deferredStartupID
              }) else { throw rejection() }
    }

    static func requireGuestUI(_ identity: CapabilityRuntimeIdentity, milestones: Set<String>) throws {
        guard identity.execution.startupExport == startup,
              milestones == ["feature_started", "first_screen"] else { throw rejection() }
        let dependencies = try entriesRejectingOtherProfiles(identity)
        for (id, digest) in [(contractID, contractSHA256), (headerID, headerSHA256)] {
            // The identity parser already requires bounded, sorted, unique IDs.
            guard let fields = dependencies.first(where: { $0.object?["id"]?.text == id })?.object,
                  fields["version"]?.text == "1", fields["artifact_sha256"]?.text == digest else {
                throw rejection()
            }
        }
    }

    static func allowsDeferredGuestUIStartup(_ identity: CapabilityRuntimeIdentity) throws -> Bool {
        guard let fields = try entries(identity).first(where: { $0.object?["id"]?.text == deferredStartupID })?.object
        else { return false }
        guard identity.execution.startupExport == startup, fields["version"]?.text == "1",
              fields["artifact_sha256"]?.text == deferredStartupSHA256 else { throw rejection() }
        return true
    }

    private static func entriesRejectingOtherProfiles(_ identity: CapabilityRuntimeIdentity) throws -> [CanonicalValue] {
        let dependencies = try entries(identity)
        guard !["mixer_guest_ui_start_v2", f10Startup, "mixer_guest_ui_event_v3", "mixer_guest_ui_ready_v3"]
                  .contains(identity.execution.startupExport),
              !dependencies.contains(where: { entry in
                  let id = entry.object?["id"]?.text
                  return id == "mixer.guest-ui-event-v2" || id == "mixer.guest-ui-native-header-v2" || id == f10WireID || id == f10HeaderID
              }) else { throw rejection() }
        return dependencies
    }

    private static func entries(_ identity: CapabilityRuntimeIdentity) throws -> [CanonicalValue] {
        guard case let .array(entries) = identity.descriptor.object?["dependencies"] else { throw rejection() }
        return entries
    }
    private static func rejection() -> UpdateError {
        UpdateError("capability.runtime.installed_mode", "Installed execution mode rejected")
    }
}
