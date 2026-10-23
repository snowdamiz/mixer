import MixerExperimentalCapabilityRuntime
func unavailable(_ session: ExperimentalCapabilitySession) async throws {
    try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: 0)
}
