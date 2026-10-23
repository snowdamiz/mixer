import Foundation
@_spi(CapabilityDurableV3) import MixerUpdates
func attempt(_ v: ReleaseVerifierV3, _ r: RetainedHealthyEvidenceV3) throws {
    _ = try v.revalidateArtifact(r, payload: Data(), now: 1)
}
