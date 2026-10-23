import MixerRuntimeIdentity
import MixerUpdates

/// A pure check of already captured installed identity. Passing this check is
/// not executable selection, validation, adapter creation or UI health.
enum CapabilityInstalledExecutionMode {
    static let startup = "mixer_guest_ui_start_v1"
    static let contractID = "mixer.guest-ui-event-v1"
    static let headerID = "mixer.guest-ui-native-header-v1"
    static let contractSHA256 = "34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024"
    static let headerSHA256 = "d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5"

    static func requireCapabilityOnly(_ identity: CapabilityRuntimeIdentity) throws {
        let dependencies = try entries(identity)
        guard identity.execution.startupExport != startup,
              !dependencies.contains(where: { entry in
                  let id = entry.object?["id"]?.text
                  return id == contractID || id == headerID
              }) else { throw rejection() }
    }

    static func requireGuestUI(_ identity: CapabilityRuntimeIdentity, milestones: Set<String>) throws {
        guard identity.execution.startupExport == startup,
              milestones == ["feature_started", "first_screen"] else { throw rejection() }
        let dependencies = try entries(identity)
        for (id, digest) in [(contractID, contractSHA256), (headerID, headerSHA256)] {
            // The identity parser already requires bounded, sorted, unique IDs.
            guard let fields = dependencies.first(where: { $0.object?["id"]?.text == id })?.object,
                  fields["version"]?.text == "1", fields["artifact_sha256"]?.text == digest else {
                throw rejection()
            }
        }
    }

    private static func entries(_ identity: CapabilityRuntimeIdentity) throws -> [CanonicalValue] {
        guard case let .array(entries) = identity.descriptor.object?["dependencies"] else { throw rejection() }
        return entries
    }
    private static func rejection() -> UpdateError {
        UpdateError("capability.runtime.installed_mode", "Installed execution mode rejected")
    }
}
