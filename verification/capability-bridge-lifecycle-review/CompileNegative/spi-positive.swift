@_spi(CapabilityLifecycle) import MixerExperimentalCapabilityRuntime
func allowed(_ group: OwnedCapabilityAdapterGroup) { group.closeIfUntransferred() }
