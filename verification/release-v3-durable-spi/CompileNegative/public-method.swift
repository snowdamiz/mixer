import Foundation
import MixerUpdates
func attempt(_ v: ReleaseVerifierV3) throws {
    _ = try v._authorizeOfferV3(exactManifest: Data(), exactAssignment: Data(), channel: "beta", installation: "a", lastSequence: 0, now: 1)
}
