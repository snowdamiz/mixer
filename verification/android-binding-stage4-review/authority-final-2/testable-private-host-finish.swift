import Foundation
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation
func bad(_ lifetime: CapabilityGuestUIPresentationLifetime, _ permit: CapabilityPresentationJoinPermit) async { _ = await lifetime.finishAndroidHost(using: permit) }
