import Foundation
import MixerRuntimeIdentity
import MixerUpdates

do {
    let arguments = Array(CommandLine.arguments.dropFirst())
    guard arguments.count == 2, ["inspect", "inspect-v2"].contains(arguments[0]) else {
        throw UpdateError("usage", "Usage: mixer-identity inspect|inspect-v2 <descriptor.json>")
    }
    let bytes = try UpdateInputFile.read(URL(fileURLWithPath: arguments[1]), maximumBytes: RuntimeIdentity.maximumDescriptorBytes)
    struct Result: Encodable {
        let schema: Int
        let fingerprint: String
        let canonicalCBORBytes: Int
        let installedRuntime: InstalledRuntime
        let buildAttested: Bool
    }
    let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    if arguments[0] == "inspect" {
        let identity = try RuntimeIdentity(json: bytes)
        let result = Result(schema: 1, fingerprint: identity.fingerprint, canonicalCBORBytes: identity.canonicalCBOR.count, installedRuntime: identity.installedRuntime, buildAttested: false)
        print(String(decoding: try encoder.encode(result), as: UTF8.self))
    } else {
        let identity = try CapabilityRuntimeIdentity(json: bytes)
        struct CapabilityResult: Encodable {
            let schema: Int
            let fingerprint: String
            let canonicalCBORBytes: Int
            let installedRuntime: InstalledRuntime
            let execution: CapabilityRuntimeIdentity.ExecutionPolicy
            let capabilityExecution: CapabilityRuntimeIdentity.CapabilityExecutionPolicy
            let capabilities: [CapabilityRuntimeIdentity.CapabilityRecord]
            let buildAttested: Bool
        }
        let result = CapabilityResult(schema: 2, fingerprint: identity.fingerprint, canonicalCBORBytes: identity.canonicalCBOR.count, installedRuntime: identity.installedRuntime, execution: identity.execution, capabilityExecution: identity.capabilityExecution, capabilities: identity.capabilities, buildAttested: false)
        print(String(decoding: try encoder.encode(result), as: UTF8.self))
    }
} catch {
    FileHandle.standardError.write(Data("\(error)\n".utf8))
    exit(1)
}
