@_spi(CapabilityLifecycle) import MixerExperimentalCapabilityRuntime
func denied(_ group: OwnedCapabilityAdapterGroup) { group.nativeDidDrain() }
