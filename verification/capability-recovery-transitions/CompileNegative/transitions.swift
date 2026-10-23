import MixerCapabilityActivation
func outside(_ value: CapabilityRecoveryStore) async throws {
    _ = try await value.prepareStartupSelection()
}
