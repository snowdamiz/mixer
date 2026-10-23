import MixerCapabilityActivation
import MixerUpdates
func forbidden(_ runtime: CapabilityColdStartRuntime,_ artifact: VerifiedArtifactV3) async throws {
    _ = try await runtime.start(artifact: artifact)
}
