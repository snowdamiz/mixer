import MixerCapabilityActivation
func forbidden(_ runtime: CapabilityColdStartRuntime) async throws { _ = try await runtime.invoke("run") }
