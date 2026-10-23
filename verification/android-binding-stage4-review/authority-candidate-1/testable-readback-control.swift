import Foundation
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation
func readback(_ value: CapabilityAndroidHostInstallation) -> CapabilityAndroidHostJoinStatus { value.status }
