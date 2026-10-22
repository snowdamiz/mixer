import Foundation
import MixerUpdates

struct ToolReport: Encodable {
    let status = "protocol-verified"
    let artifactSHA256: String
    let releaseID: String
    let payloadBytes: UInt64
    let assignmentSequence: UInt64
    let cohortBucket: UInt64
    let executableProfileVerified = false
    let policyApproved = false
    let activated = false
}
struct ToolError: Encodable { let status = "error"; let message: String }
func emit<T: Encodable>(_ value: T) throws {
    let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    FileHandle.standardOutput.write(try encoder.encode(value) + Data([10]))
}
func read(_ path: String, maximum: Int = 1_048_576) throws -> Data {
    let url = URL(fileURLWithPath: path)
    guard let size = try url.resourceValues(forKeys: [.fileSizeKey]).fileSize, size <= maximum else { throw UpdateError("file.size", "Input file exceeds configured limit") }
    let data = try Data(contentsOf: url)
    guard data.count <= maximum else { throw UpdateError("file.size", "Input file changed beyond limit") }
    return data
}
do {
    let args = Array(CommandLine.arguments.dropFirst())
    guard args.first == "verify", args.count == 19 else { throw UpdateError("arguments", "Usage: mixer-update verify --manifest FILE --payload FILE --host FILE --roots FILE --assignment FILE --channel NAME --installation ID --last-sequence N --now UNIX_SECONDS") }
    var values: [String: String] = [:]
    let keys: Set<String> = ["--manifest", "--payload", "--host", "--roots", "--assignment", "--channel", "--installation", "--last-sequence", "--now"]
    for index in stride(from: 1, to: args.count, by: 2) {
        guard keys.contains(args[index]), values[args[index]] == nil else { throw UpdateError("arguments", "Unknown or duplicate option") }
        values[args[index]] = args[index + 1]
    }
    guard Set(values.keys) == keys, let last = UInt64(values["--last-sequence"]!), let now = UInt64(values["--now"]!) else { throw UpdateError("arguments", "Missing options or invalid sequence/time") }
    let host = try StrictJSON.decode(InstalledRuntime.self, from: read(values["--host"]!))
    let roots = try StrictJSON.decode([TrustRoot].self, from: read(values["--roots"]!))
    let verifier = try ReleaseVerifier(host: host, roots: roots)
    let artifact = try verifier.verifyArtifact(signedManifest: read(values["--manifest"]!), payload: read(values["--payload"]!, maximum: Int(host.maxPayloadBytes)), now: now)
    let assignment = try verifier.verifyAssignment(signedAssignment: read(values["--assignment"]!), artifact: artifact, channel: values["--channel"]!, installation: values["--installation"]!, lastSequence: last, now: now)
    try emit(ToolReport(artifactSHA256: artifact.artifactSHA256, releaseID: artifact.releaseID, payloadBytes: artifact.payloadBytes, assignmentSequence: assignment.sequence, cohortBucket: assignment.cohortBucket))
} catch {
    try? emit(ToolError(message: String(describing: error))); exit(1)
}
