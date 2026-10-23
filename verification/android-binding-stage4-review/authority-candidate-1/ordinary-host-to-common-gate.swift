import Foundation
@_spi(GuestUIV1) import MixerGuest
import MixerCapabilityActivation
func bad(_ host: CapabilityAndroidHostInstallation, _ gate: CapabilityPresentationBindingGate) { _ = gate.accept(host) }
