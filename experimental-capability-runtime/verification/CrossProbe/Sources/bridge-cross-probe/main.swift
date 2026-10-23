import Foundation
import MixerCapabilities
import MixerExperimentalCapabilityRuntime

@main struct CrossProbe {
    static func main() async throws {
        let policy = try CapabilityPolicy(installed: [], manifest: [])
        let attempt = try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy,
            adapters: InstalledCapabilityAdapters())
        do {
            let session = try await attempt.create()
            _ = try await session.startup()
            session.close()
        } catch { print("Expected empty-module rejection: \(error)") }
    }
}
