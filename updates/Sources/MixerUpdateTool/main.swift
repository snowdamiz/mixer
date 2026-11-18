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
struct ToolError: Encodable {
    let status = "error"
    let message: String
    let code: String?
}
func emit<T: Encodable>(_ value: T) throws {
    let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    FileHandle.standardOutput.write(try encoder.encode(value) + Data([10]))
}
func read(_ path: String, maximum: Int = 1_048_576) throws -> Data {
    try UpdateInputFile.read(URL(fileURLWithPath: path), maximumBytes: maximum)
}
enum VerificationCommand: String {
    case legacy = "verify"
    case v3 = "verify-v3"
}

let args = Array(CommandLine.arguments.dropFirst())
let command = args.first.flatMap(VerificationCommand.init(rawValue:))
do {
    guard let command, args.count == 19 else {
        throw UpdateError("arguments", "Usage: mixer-update <verify|verify-v3> --manifest FILE --payload FILE --host FILE --roots FILE --assignment FILE --channel NAME --installation ID --last-sequence N --now UNIX_SECONDS")
    }
    var values: [String: String] = [:]
    let keys: Set<String> = ["--manifest", "--payload", "--host", "--roots", "--assignment", "--channel", "--installation", "--last-sequence", "--now"]
    for index in stride(from: 1, to: args.count, by: 2) {
        guard keys.contains(args[index]), values[args[index]] == nil else { throw UpdateError("arguments", "Unknown or duplicate option") }
        values[args[index]] = args[index + 1]
    }
    guard Set(values.keys) == keys, let last = UInt64(values["--last-sequence"]!), let now = UInt64(values["--now"]!) else { throw UpdateError("arguments", "Missing options or invalid sequence/time") }
    let host = try StrictJSON.decode(InstalledRuntime.self, from: read(values["--host"]!))
    let roots = try StrictJSON.decode([TrustRoot].self, from: read(values["--roots"]!))
    let channel = values["--channel"]!
    let installation = values["--installation"]!
    switch command {
    case .legacy:
        let verifier = try ReleaseVerifier(host: host, roots: roots)
        let artifact = try verifier.verifyArtifact(signedManifest: read(values["--manifest"]!), payload: read(values["--payload"]!, maximum: Int(host.maxPayloadBytes)), now: now)
        let assignment = try verifier.verifyAssignment(signedAssignment: read(values["--assignment"]!), artifact: artifact, channel: channel, installation: installation, lastSequence: last, now: now)
        try emit(ToolReport(artifactSHA256: artifact.artifactSHA256, releaseID: artifact.releaseID, payloadBytes: artifact.payloadBytes, assignmentSequence: assignment.sequence, cohortBucket: assignment.cohortBucket))
    case .v3:
        let verifier = try ReleaseVerifierV3(host: host, roots: roots)
        let signedManifest = try read(values["--manifest"]!, maximum: ReleaseVerifierV3.maximumSignedDocumentBytes)
        let payload = try read(values["--payload"]!, maximum: Int(verifier.host.maxPayloadBytes))
        let artifact = try verifier.verifyArtifact(signedManifest: signedManifest, payload: payload, now: now)
        let signedAssignment = try read(values["--assignment"]!, maximum: ReleaseVerifierV3.maximumSignedDocumentBytes)
        let assignment = try verifier.verifyAssignment(signedAssignment: signedAssignment, artifact: artifact,
            channel: channel, installation: installation, lastSequence: last, now: now)
        try emit(ToolReport(artifactSHA256: artifact.artifactSHA256, releaseID: artifact.releaseID,
            payloadBytes: artifact.payloadBytes, assignmentSequence: assignment.sequence, cohortBucket: assignment.cohortBucket))
    }
} catch {
    let code = command == .v3 ? (error as? UpdateError)?.code : nil
    try? emit(ToolError(message: String(describing: error), code: code))
    exit(1)
}
