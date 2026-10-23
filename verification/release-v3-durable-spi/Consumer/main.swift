import Foundation
@_spi(CapabilityDurableV3) import MixerUpdates

struct Fixture: Decodable {
    let host: InstalledRuntime
    let roots: [TrustRoot]
    let payload: Data
    let signed_manifest: CanonicalValue
    let signed_assignment: CanonicalValue
    let installation: String
    let verification_time_unix: UInt64
    let last_sequence: UInt64
    let artifact_sha256: String
}
func require(_ condition: @autoclosure () -> Bool) throws {
    guard condition() else { throw UpdateError("consumer.check", "SPI consumer check failed") }
}
guard CommandLine.arguments.count == 2 else { throw UpdateError("consumer.input", "One fixture required") }
let f = try StrictJSON.decode(Fixture.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
let m = try JSONEncoder().encode(f.signed_manifest), a = try JSONEncoder().encode(f.signed_assignment)
let verifier = try ReleaseVerifierV3(host: f.host, roots: f.roots)
let offer: OfferEvidenceV3 = try verifier._authorizeOfferV3(exactManifest: m, exactAssignment: a,
    channel: "beta", installation: f.installation, lastSequence: f.last_sequence, now: f.verification_time_unix)
try require(offer.artifactSHA256 == f.artifact_sha256 && offer.signedManifest == m && offer.signedAssignment == a)
let ordinary = try verifier.verifyArtifact(signedManifest: m, payload: f.payload, now: f.verification_time_unix)
try require(offer.artifactSHA256 == ordinary.artifactSHA256)
let expiredRoots = f.roots.map { TrustRoot(keyID: $0.keyID, publicKey: $0.publicKey, scope: $0.scope,
    artifact: $0.artifact, assignment: $0.assignment, revoked: $0.revoked, notBeforeUnix: 1, notAfterUnix: 2) }
let expired = try ReleaseVerifierV3(host: f.host, roots: expiredRoots)
let retained: RetainedHealthyEvidenceV3 = try expired._verifyRetainedHealthySnapshotV3(exactManifest: m,
    exactAssignment: a, payload: f.payload, channel: "beta", installation: f.installation,
    storedSequence: offer.sequence, acceptedSequence: offer.sequence)
let copy = expired
let refreshed = try copy._revalidateRetainedHealthyV3(retained, payload: f.payload)
try require(refreshed.artifactSHA256 == ordinary.artifactSHA256 && refreshed.resourceLimits == ordinary.resourceLimits)
try require(refreshed.capabilityGrants.entries.count == ordinary.capabilityGrants.entries.count)
do {
    _ = try expired.verifyArtifact(signedManifest: m, payload: f.payload, now: f.verification_time_unix)
    throw UpdateError("consumer.unexpected", "Expired ordinary verification accepted")
} catch let error as UpdateError { try require(error.code == "v3.signature.authority") }
do {
    _ = try verifier._revalidateRetainedHealthyV3(retained, payload: f.payload)
    throw UpdateError("consumer.unexpected", "Foreign retained proof accepted")
} catch let error as UpdateError { try require(error.code == "v3.proof.context") }
print("SPI metadata consumer passed; no durable provenance or executable authority claimed")
