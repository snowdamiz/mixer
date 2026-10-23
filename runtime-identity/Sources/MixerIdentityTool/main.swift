import Foundation
import MixerRuntimeIdentity
import MixerUpdates

do {
    let arguments = Array(CommandLine.arguments.dropFirst())
    guard arguments.count == 2, arguments[0] == "inspect" else {
        throw UpdateError("usage", "Usage: mixer-identity inspect <descriptor.json>")
    }
    let bytes = try UpdateInputFile.read(URL(fileURLWithPath: arguments[1]), maximumBytes: RuntimeIdentity.maximumDescriptorBytes)
    let identity = try RuntimeIdentity(json: bytes)
    struct Result: Encodable {
        let schema: Int
        let fingerprint: String
        let canonicalCBORBytes: Int
        let installedRuntime: InstalledRuntime
        let buildAttested: Bool
    }
    let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    let result = Result(schema: 1, fingerprint: identity.fingerprint, canonicalCBORBytes: identity.canonicalCBOR.count, installedRuntime: identity.installedRuntime, buildAttested: false)
    print(String(decoding: try encoder.encode(result), as: UTF8.self))
} catch {
    FileHandle.standardError.write(Data("\(error)\n".utf8))
    exit(1)
}
