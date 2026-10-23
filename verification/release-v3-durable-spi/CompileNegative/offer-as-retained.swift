import Foundation
@_spi(CapabilityDurableV3) import MixerUpdates
func attempt(_ v: ReleaseVerifierV3, _ o: OfferEvidenceV3) throws {
    _ = try v._revalidateRetainedHealthyV3(o, payload: Data())
}
