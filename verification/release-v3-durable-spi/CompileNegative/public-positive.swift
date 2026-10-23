import Foundation
import MixerUpdates
func ordinary(_ v: ReleaseVerifierV3, _ a: VerifiedArtifactV3) throws -> VerifiedArtifactV3 {
    try v.revalidateArtifact(a, payload: Data(), now: 1)
}
