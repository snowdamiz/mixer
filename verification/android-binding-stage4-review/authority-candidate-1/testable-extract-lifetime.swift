import Foundation
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation
func bad(_ host: CapabilityAndroidHostInstallation) { _ = host.lifetime }
