import Foundation
import MixerCapabilityActivation
import MixerRuntimeIdentity
import MixerUpdates

// Cross-check the installed grant parser through public inputs against the
// independently authored Go/Swift release corpus. No test-only module access.
struct GrammarCase: Decodable { let value: String; let accepted: Bool }
struct Corpus: Decodable { let origin_cases: [GrammarCase]; let namespace_cases: [GrammarCase] }
let fixtureDirectory = URL(fileURLWithPath: CommandLine.arguments[1])
func read(_ name: String) throws -> Data { try Data(contentsOf: fixtureDirectory.appendingPathComponent(name)) }
func canonical(_ object: Any) throws -> Data {
    try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys, .withoutEscapingSlashes]) + Data([10])
}
let identityBytes = try read("identity.json")
let identityObject = try JSONSerialization.jsonObject(with: identityBytes) as! [String: Any]
let roots = try read("roots.json")
let names = ["bridge.json", "http.json", "http-grant.json", "storage.json", "storage-grant.json"]
let original = try Dictionary(uniqueKeysWithValues: names.map { ($0, try read($0)) })
let http = "network.http.v1", storage = "storage.keyValue.v1"
let container = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-root-material-" + UUID().uuidString)
func admit(_ identity: [String: Any], _ bytes: [String: Data]) throws -> InstalledCapabilityExecution {
    try InstalledCapabilityExecution(identityJSON: canonical(identity), materials: [
        .init(role: .bridgePolicy, bytes: bytes["bridge.json"]!),
        .init(role: .configuration(capabilityID: http), bytes: bytes["http.json"]!),
        .init(role: .installedGrant(capabilityID: http), bytes: bytes["http-grant.json"]!),
        .init(role: .configuration(capabilityID: storage), bytes: bytes["storage.json"]!),
        .init(role: .installedGrant(capabilityID: storage), bytes: bytes["storage-grant.json"]!),
    ], trustRootsJSON: roots, privateContainer: container)
}
let baseline = try admit(identityObject, original)
let expectedFingerprint = try CapabilityRuntimeIdentity(json: identityBytes).fingerprint
precondition(baseline.runtimeFingerprint == expectedFingerprint)
let cases = try JSONDecoder().decode(Corpus.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[2])))
var checked = 0
for (file, id, field, values) in [("http-grant.json", http, "origins", cases.origin_cases),
                                 ("storage-grant.json", storage, "namespaces", cases.namespace_cases)] {
    for test in values {
        var identity = identityObject, bytes = original
        var grant = try JSONSerialization.jsonObject(with: bytes[file]!) as! [String: Any]
        grant[field] = [test.value]
        bytes[file] = try canonical(grant)
        var capabilities = identity["capabilities"] as! [[String: Any]]
        let index = capabilities.firstIndex { $0["id"] as? String == id }!
        capabilities[index]["grants_sha256"] = ReleaseVerifier.sha256(bytes[file]!)
        identity["capabilities"] = capabilities
        let accepted: Bool
        do { _ = try admit(identity, bytes); accepted = true } catch { accepted = false }
        precondition(accepted == test.accepted, "installed/signed grammar mismatch: \(field) \(test.value)")
        checked += 1
    }
}
precondition(!FileManager.default.fileExists(atPath: container.path))
print("Root public installed-material review: \(checked) shared grant grammar cases agree; exact identity binding and no container creation; no executable authority")
