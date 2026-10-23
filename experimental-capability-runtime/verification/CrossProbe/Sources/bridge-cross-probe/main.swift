import Foundation
import MixerCapabilities
import MixerExperimentalCapabilityRuntime

@main struct CrossProbe {
    static func main() async throws {
        let validation = try ExperimentalCapabilityValidator.prepare(module:Data(),startupExport:"boot",configuration:.init(memoryPages:0))
        do { try await validation.validate(); throw ProbeFailure.unexpectedSuccess }
        catch let error as ExperimentalCapabilityError {
            guard error.failure.kind == .validation(.malformed), error.failure.operation == .validation,
                  error.failure.nativeStatus == 1, error.failure.location?.functionIndex == nil else { throw error }
            print("Expected typed validate-only rejection: \(error)")
        }
        validation.cancel()
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

private enum ProbeFailure: Error { case unexpectedSuccess }
