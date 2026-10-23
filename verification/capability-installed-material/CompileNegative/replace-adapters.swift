import Foundation
import MixerCapabilityActivation
import MixerCapabilities
func construct(_ adapters: InstalledCapabilityAdapters) throws {
    _ = try InstalledCapabilityExecution(adapters: adapters)
}
