import Foundation
import MixerUpdates
func misuse(_ verifier: ReleaseVerifierV3, _ legacy: VerifiedArtifact) throws {
    _ = try verifier.verifyAssignment(signedAssignment: Data(), artifact: legacy,
        channel: "beta", installation: "test", lastSequence: 0, now: 1)
}
