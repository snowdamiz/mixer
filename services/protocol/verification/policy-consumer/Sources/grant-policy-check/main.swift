import Foundation
import MixerCapabilities
import MixerUpdates

struct CheckFailure: Error { let reason: String }
struct RuleCase: Decodable { let value: String; let accepted: Bool }
struct DocumentCase: Decodable { let name: String; let accepted: Bool; let signed_manifest_json: String }
struct Corpus: Decodable {
    let cases: [DocumentCase]
    let origin_cases: [RuleCase]
    let namespace_cases: [RuleCase]
}
struct Vector: Decodable {
    let host: InstalledRuntime
    let roots: [TrustRoot]
    let payload: Data
    let verification_time_unix: UInt64
}
func read<T: Decodable>(_ name: String, from directory: URL, as type: T.Type) throws -> T {
    try StrictJSON.decode(type, from: Data(contentsOf: directory.appendingPathComponent(name)))
}
func policyAccepts(_ grant: CapabilityGrant) -> Bool {
    do { _ = try CapabilityPolicy(installed: [grant], manifest: [grant]); return true }
    catch { return false }
}
guard CommandLine.arguments.count == 2 else { throw CheckFailure(reason: "Expected the test-only fixture directory") }
let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let corpus = try read("capability-grant-cases-v1.json", from: directory, as: Corpus.self)
let vector = try read("signed-release-v2.json", from: directory, as: Vector.self)
let verifier = try ReleaseVerifier(host: vector.host, roots: vector.roots)
for item in corpus.origin_cases {
    let grant = CapabilityGrant(capabilityID: CapabilitySchemas.httpID, schemaSHA256: CapabilitySchemas.httpSHA256,
        permissions: ["network.https"], origins: [item.value], methods: ["GET"])
    guard policyAccepts(grant) == item.accepted else { throw CheckFailure(reason: "Origin grammar drift: \(item.value)") }
}
for item in corpus.namespace_cases {
    let grant = CapabilityGrant(capabilityID: CapabilitySchemas.storageID, schemaSHA256: CapabilitySchemas.storageSHA256,
        permissions: ["storage.appPrivate"], namespaces: [item.value])
    guard policyAccepts(grant) == item.accepted else { throw CheckFailure(reason: "Namespace grammar drift: \(item.value)") }
}
for item in corpus.cases {
    let artifact: VerifiedArtifact?
    do { artifact = try verifier.verifyArtifact(signedManifest: Data(item.signed_manifest_json.utf8), payload: vector.payload, now: vector.verification_time_unix) }
    catch { artifact = nil }
    guard (artifact != nil) == item.accepted else { throw CheckFailure(reason: "Verifier expectation drift: \(item.name)") }
    if let artifact {
        guard let grants = artifact.capabilityGrants else { throw CheckFailure(reason: "V2 grants absent") }
        let mapped = grants.entries.map {
            CapabilityGrant(capabilityID: $0.capabilityID, schemaSHA256: $0.schemaSHA256, permissions: Set($0.permissions),
                origins: Set($0.origins), methods: Set($0.methods), namespaces: Set($0.namespaces))
        }
        // A valid release grant must also be a valid installed-policy value. This
        // check does not install grants or execute a capability/Wasm guest.
        _ = try CapabilityPolicy(installed: mapped, manifest: mapped)
    }
}
let result: [String: Any] = ["schema": 1, "status": "passed", "scope": "local checkout public verifier-to-policy mapping and grammar parity only; no guest/device/publication qualification",
    "signedCases": corpus.cases.count, "originCases": corpus.origin_cases.count, "namespaceCases": corpus.namespace_cases.count,
    "grantDescriptorSHA256": VerifiedCapabilityGrants.descriptorSHA256, "httpSchemaSHA256": CapabilitySchemas.httpSHA256, "storageSchemaSHA256": CapabilitySchemas.storageSHA256]
print(String(decoding: try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]), as: UTF8.self))
