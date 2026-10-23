import Foundation
@_spi(CapabilityDurableV3) import MixerUpdates
let forged = try JSONDecoder().decode(RetainedHealthyEvidenceV3.self, from: Data())
