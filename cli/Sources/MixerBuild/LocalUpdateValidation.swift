import Foundation

public struct LocalUpdateReport: Encodable {
    public let status: String
    public let payloadSHA256: String
    public let protocolVerification: CommandResult
    public let executableVerification: CommandResult?
    public let policyApproved = false
    public let published = false
    public let qualification = "local-validation-only; mobile integration and recovery receipts still required"
}

public enum LocalUpdateValidation {
    public static func verify(arguments: [String], verifier: String, vm: String) throws -> LocalUpdateReport {
        try verify(arguments: arguments, verifier: verifier, vm: vm, runner: { try ProcessRunner.run($0) })
    }

    // Both verifiers consume the same private snapshot. Reading caller paths again
    // between signature validation and execution validation could validate two
    // different payloads. No artifact is activated or published by this command.
    static func verify(arguments: [String], verifier: String, vm: String,
                       runner: ([String]) throws -> CommandResult) throws -> LocalUpdateReport {
        let keys: Set<String> = ["--manifest", "--payload", "--host", "--roots", "--assignment", "--channel", "--installation", "--last-sequence", "--now"]
        guard arguments.count == keys.count * 2 else { throw MixerFailure("update.arguments", "Expected all nine update verify options exactly once.") }
        var values: [String: String] = [:]
        for index in stride(from: 0, to: arguments.count, by: 2) {
            guard keys.contains(arguments[index]), values[arguments[index]] == nil else { throw MixerFailure("update.arguments", "Unknown or duplicate update verify option.") }
            values[arguments[index]] = arguments[index + 1]
        }
        guard Set(values.keys) == keys else { throw MixerFailure("update.arguments", "Missing update verify option.") }
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-verify-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        defer { try? FileManager.default.removeItem(at: folder) }
        var payloadDigest = ""
        for key in ["--manifest", "--payload", "--host", "--roots", "--assignment"] {
            let source = URL(fileURLWithPath: values[key]!)
            guard try source.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true else { throw MixerFailure("update.input-type", "Verification inputs must be regular files.") }
            let input = try FileHandle(forReadingFrom: source)
            defer { try? input.close() }
            let maximum = key == "--payload" ? 16_777_216 : 1_048_576
            let data = try input.read(upToCount: maximum + 1) ?? Data()
            guard data.count <= maximum else { throw MixerFailure("update.input-size", "\(key) exceeds the v1 input limit.") }
            let destination = folder.appendingPathComponent(String(key.dropFirst(2)))
            guard FileManager.default.createFile(atPath: destination.path, contents: data, attributes: [.posixPermissions: 0o400]) else { throw MixerFailure("update.snapshot", "Cannot snapshot verification input.") }
            values[key] = destination.path
            if key == "--payload" { payloadDigest = SourceDigest.sha256(data) }
        }
        let protocolResult = try runner([verifier, "verify"] + keys.sorted().flatMap { [$0, values[$0]!] })
        guard protocolResult.succeeded else {
            return LocalUpdateReport(status: "protocol-rejected", payloadSHA256: payloadDigest, protocolVerification: protocolResult, executableVerification: nil)
        }
        let vmResult = try runner([vm, "validate", values["--payload"]!])
        return LocalUpdateReport(status: vmResult.succeeded ? "local-candidate-verified" : "executable-rejected", payloadSHA256: payloadDigest, protocolVerification: protocolResult, executableVerification: vmResult)
    }
}
