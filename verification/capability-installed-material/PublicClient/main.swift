import Foundation
import MixerCapabilityActivation
import MixerRuntimeIdentity

let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
func bytes(_ name: String) throws -> Data { try Data(contentsOf: directory.appendingPathComponent(name)) }
let identity = try bytes("identity.json")
let materials: [CapabilityMaterialFile] = try [
    .init(role: .bridgePolicy, bytes: bytes("bridge.json")),
    .init(role: .configuration(capabilityID: "network.http.v1"), bytes: bytes("http.json")),
    .init(role: .installedGrant(capabilityID: "network.http.v1"), bytes: bytes("http-grant.json")),
    .init(role: .configuration(capabilityID: "storage.keyValue.v1"), bytes: bytes("storage.json")),
    .init(role: .installedGrant(capabilityID: "storage.keyValue.v1"), bytes: bytes("storage-grant.json")),
]
let value = try InstalledCapabilityExecution(identityJSON: identity, materials: materials, trustRootsJSON: bytes("roots.json"),
                                             privateContainer: URL(fileURLWithPath: "/material-public-client-never-created"))
let expected = try CapabilityRuntimeIdentity(json: identity).fingerprint
precondition(value.runtimeFingerprint == expected)
print("material public client passed; fingerprint=" + value.runtimeFingerprint)
