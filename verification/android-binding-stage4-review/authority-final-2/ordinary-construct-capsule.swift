import Foundation
@_spi(GuestUIV1) import MixerGuest
import MixerCapabilityActivation
func bad(_ key: CapabilityAndroidHostLifetimeKey, _ task: Task<Void, Never>, _ control: CapabilityAndroidLifetimeControl) { _ = CapabilityAndroidHostLifetimeCapsule(key: key, task: task, control: control) }
