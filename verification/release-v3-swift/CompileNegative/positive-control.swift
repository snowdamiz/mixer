import Foundation
import MixerUpdates
func read(_ verifier: ReleaseVerifierV3, _ artifact: VerifiedArtifactV3) throws -> [String] {
    let current = try verifier.revalidateArtifact(artifact, payload: Data(), now: 1)
    return current.capabilityGrants.entries.map(\.capabilityID)
}
