import Foundation
import Crypto
import MixerUpdates
import MixerRuntimeIdentity

struct IdentityVector: Decodable { let name: String; let descriptor: CanonicalValue }
struct ReleaseVector: Decodable {
    let payload: Data
    let signedManifest: CanonicalValue
    enum CodingKeys: String, CodingKey { case payload; case signedManifest = "signed_manifest" }
}
let identities = try JSONDecoder().decode([IdentityVector].self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
let identity = try CapabilityRuntimeIdentity(json: JSONEncoder().encode(identities.first { $0.name == "both" }!.descriptor))
let fixture = try JSONDecoder().decode(ReleaseVector.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[2])))
let host = identity.installedRuntime
let seed = Data(SHA256.hash(data: Data("Mixer root integration TEST ONLY signing seed".utf8)))
let key = try Curve25519.Signing.PrivateKey(rawRepresentation: seed)
let roots = [TrustRoot(keyID: "integration-test", publicKey: key.publicKey.rawRepresentation, scope: host.scope, artifact: true, assignment: true)]
let verifier = try ReleaseVerifierV3(host: host, roots: roots)
var manifest = fixture.signedManifest.object!["manifest"]!.object!
manifest["scope"] = try JSONDecoder().decode(CanonicalValue.self, from: JSONEncoder().encode(host.scope))
manifest["runtime"] = .text(identity.fingerprint)
manifest["key_id"] = .text("integration-test")
manifest["state_min"] = .uint(host.stateVersion)
manifest["state_max"] = .uint(host.stateVersion)
manifest["capability_hashes"] = .object(host.capabilityHashes.mapValues(CanonicalValue.text))
manifest["limits"] = .object(["memory_bytes": .uint(1), "fuel": .uint(1), "startup_milliseconds": .uint(1)])
let value = CanonicalValue.object(manifest)
let signature = try key.signature(for: Data("mixer.artifact.v3\0".utf8) + value.canonicalCBOR())
let signed = try JSONEncoder().encode(CanonicalValue.object(["manifest": value, "signature": .text(signature.base64EncodedString())]))
let artifact = try verifier.verifyArtifact(signedManifest: signed, payload: fixture.payload, now: 1_792_627_300)
guard artifact.manifest.object?["runtime"]?.text == identity.fingerprint,
      artifact.resourceLimits.memoryBytes / 65536 == 0,
      artifact.capabilityGrants.entries.count == 2 else { fatalError("identity-to-release binding mismatch") }
do {
    _ = try ReleaseVerifier(host: host, roots: roots)
    fatalError("legacy verifier accepted capability tuple")
} catch is UpdateError { }
print("Identity2 -> explicit release3 verified exact identity and signed 1-byte memory; legacy rejects; no executable validation or effects")
