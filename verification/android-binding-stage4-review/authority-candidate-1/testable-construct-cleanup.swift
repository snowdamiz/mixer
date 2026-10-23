import Foundation
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation
func bad(_ key: CapabilityAndroidHostLifetimeKey) { _ = CapabilityAndroidHostFacadeCleanupEvidence(key: key, cleanupSerial: 1, finalEntrySerial: 1, bridgeSlotGeneration: 1, clearedExchangeGeneration: nil, clearedResourceStageRevision: 1) }
