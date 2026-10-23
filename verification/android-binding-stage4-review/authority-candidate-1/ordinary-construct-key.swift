import Foundation
@_spi(GuestUIV1) import MixerGuest
import MixerCapabilityActivation
func bad(_ id: CapabilityPresentationLifetimeID) { _ = CapabilityAndroidHostLifetimeKey(facade: 1, lifetime: id, endpoint: 1) }
