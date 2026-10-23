import Foundation
import MixerUpdates

struct PublicVector: Decodable {
    let test_only: Bool
    let host: InstalledRuntime
    let roots: [TrustRoot]
    let payload: Data
    let signed_manifest: CanonicalValue
    let signed_assignment: CanonicalValue
    let installation: String
    let verification_time_unix: UInt64
    let last_sequence: UInt64
    let artifact_sha256: String
    let cohort_bucket: UInt64
}
let arguments = CommandLine.arguments
if arguments.count != 2 { fatalError("expected the frozen public test vector path") }
let data = try Data(contentsOf:URL(fileURLWithPath:arguments[1]))
let vector = try StrictJSON.decode(PublicVector.self,from:data)
guard vector.test_only else { fatalError("test-only vector required") }
let verifier = try ReleaseVerifierV3(host:vector.host,roots:vector.roots), copy = verifier
let artifact = try verifier.verifyArtifact(signedManifest:JSONEncoder().encode(vector.signed_manifest),payload:vector.payload,now:vector.verification_time_unix)
let refreshed = try copy.revalidateArtifact(artifact,payload:vector.payload,now:vector.verification_time_unix)
let assignment = try copy.verifyAssignment(signedAssignment:JSONEncoder().encode(vector.signed_assignment),artifact:refreshed,
    channel:"beta",installation:vector.installation,lastSequence:vector.last_sequence,now:vector.verification_time_unix)
guard artifact.artifactSHA256 == vector.artifact_sha256, assignment.cohortBucket == vector.cohort_bucket else { fatalError("vector mismatch") }
print("PUBLIC_V3_PROOF_OK artifact="+artifact.artifactSHA256+" grants="+String(artifact.capabilityGrants.entries.count)+" sequence="+String(assignment.sequence))
