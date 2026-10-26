import Foundation
import MixerUpdates

public struct LocalUpdateReport: Encodable {
    public let status: String
    public let payloadSHA256: String
    public let protocolVerification: CommandResult
    public let executableVerification: CommandResult?
    public let policyApproved = false
    public let published = false
    public let qualification = "local-validation-only; mobile integration and recovery receipts still required"
    public let linkedProtocolVerification: LinkedProtocolReceipt?
    public let protocolTool: VerificationToolIdentity?
    public let executableTool: VerificationToolIdentity?
    public let rejectionReason: String?
}

public struct LinkedProtocolReceipt: Encodable {
    public let implementation = "linked MixerUpdates.ReleaseVerifier"
    public let artifactSHA256: String
    public let payloadBytes: UInt64
    public let assignmentSequence: UInt64
    public let cohortBucket: UInt64
}

private struct ProtocolToolReceipt: Decodable {
    let status: String
    let artifactSHA256: String
    let releaseID: String
    let payloadBytes: UInt64
    let assignmentSequence: UInt64
    let cohortBucket: UInt64
    let executableProfileVerified: Bool
    let policyApproved: Bool
    let activated: Bool
}
private struct VMToolReceipt: Decodable {
    let profile: String
    let valid: Bool
    let inventory_complete: Bool
    let imports: [Import]
    let exports: [Export]
    let opcodes: [Opcode]
    let extended_opcodes: [Opcode]
    let error: Failure?
    let inventory_error: Failure?
    struct Import: Decodable { let module: String; let name: String; let type_index: UInt64 }
    struct Export: Decodable { let name: String; let kind: UInt64; let index: UInt64 }
    struct Opcode: Decodable { let opcode: String; let count: UInt64 }
    struct Failure: Decodable { let code: String; let message: String; let function: UInt64?; let offset: UInt64 }
}

private func toolReceipt<T: Decodable>(_ type: T.Type, from output: String, fields: Set<String>) throws -> T {
    let bytes = Data(output.utf8)
    let decoded = try StrictJSON.decode(type, from: bytes)
    guard let object = try JSONSerialization.jsonObject(with: bytes) as? [String: Any], Set(object.keys) == fields else {
        throw MixerFailure("update.tool-receipt", "Verification tool returned unknown or missing receipt fields.")
    }
    return decoded
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
        var snapshots: [String: Data] = [:]
        for key in ["--manifest", "--payload", "--host", "--roots", "--assignment"] {
            let source = URL(fileURLWithPath: values[key]!)
            let maximum = key == "--payload" ? 16_777_216 : 1_048_576
            let data = try VerificationFile.read(source, maximumBytes: maximum)
            let destination = folder.appendingPathComponent(String(key.dropFirst(2)))
            guard FileManager.default.createFile(atPath: destination.path, contents: data, attributes: [.posixPermissions: 0o400]) else { throw MixerFailure("update.snapshot", "Cannot snapshot verification input.") }
            values[key] = destination.path
            snapshots[key] = data
            if key == "--payload" { payloadDigest = SourceDigest.sha256(data) }
        }
        let host: InstalledRuntime, artifact: VerifiedArtifact, assignment: VerifiedAssignment
        do {
            guard let last = UInt64(values["--last-sequence"]!), let now = UInt64(values["--now"]!) else { throw MixerFailure("update.arguments", "Invalid sequence/time.") }
            host = try StrictJSON.decode(InstalledRuntime.self, from: snapshots["--host"]!)
            let roots = try StrictJSON.decode([TrustRoot].self, from: snapshots["--roots"]!)
            let linked = try ReleaseVerifier(host: host, roots: roots)
            artifact = try linked.verifyArtifact(signedManifest: snapshots["--manifest"]!, payload: snapshots["--payload"]!, now: now)
            assignment = try linked.verifyAssignment(signedAssignment: snapshots["--assignment"]!, artifact: artifact, channel: values["--channel"]!, installation: values["--installation"]!, lastSequence: last, now: now)
        } catch {
            return LocalUpdateReport(status: "protocol-rejected", payloadSHA256: payloadDigest,
                protocolVerification: CommandResult(command: ["linked MixerUpdates.ReleaseVerifier"], exitCode: 1, output: String(describing: error)), executableVerification: nil,
                linkedProtocolVerification: nil, protocolTool: nil, executableTool: nil, rejectionReason: String(describing: error))
        }
        let linkedReceipt = LinkedProtocolReceipt(artifactSHA256: artifact.artifactSHA256, payloadBytes: artifact.payloadBytes, assignmentSequence: assignment.sequence, cohortBucket: assignment.cohortBucket)
        let protocolIdentity = try VerificationFile.tool(verifier), vmIdentity = try VerificationFile.tool(vm)
        let protocolResult = try runner([protocolIdentity.path, "verify"] + keys.sorted().flatMap { [$0, values[$0]!] })
        guard try VerificationFile.tool(protocolIdentity.path) == protocolIdentity else { throw MixerFailure("update.tool-changed", "Protocol verification executable changed during validation.") }
        guard protocolResult.succeeded, !protocolResult.outputTruncated else {
            return LocalUpdateReport(status: "protocol-rejected", payloadSHA256: payloadDigest, protocolVerification: protocolResult, executableVerification: nil, linkedProtocolVerification: linkedReceipt, protocolTool: protocolIdentity, executableTool: vmIdentity, rejectionReason: "Protocol tool rejected the candidate.")
        }
        do {
            let receipt = try toolReceipt(ProtocolToolReceipt.self, from: protocolResult.output, fields: ["status","artifactSHA256","releaseID","payloadBytes","assignmentSequence","cohortBucket","executableProfileVerified","policyApproved","activated"])
            guard receipt.status == "protocol-verified", receipt.artifactSHA256 == artifact.artifactSHA256,
                  receipt.releaseID == artifact.releaseID, receipt.payloadBytes == artifact.payloadBytes,
                  receipt.assignmentSequence == assignment.sequence, receipt.cohortBucket == assignment.cohortBucket,
                  !receipt.executableProfileVerified, !receipt.policyApproved, !receipt.activated else { throw MixerFailure("update.tool-receipt", "Protocol tool receipt does not bind the verified snapshot.") }
        } catch {
            return LocalUpdateReport(status: "protocol-rejected", payloadSHA256: payloadDigest, protocolVerification: protocolResult, executableVerification: nil, linkedProtocolVerification: linkedReceipt, protocolTool: protocolIdentity, executableTool: vmIdentity, rejectionReason: String(describing: error))
        }
        guard try VerificationFile.read(URL(fileURLWithPath: values["--payload"]!), maximumBytes: 16_777_216) == snapshots["--payload"]! else { throw MixerFailure("update.snapshot-changed", "Private payload snapshot changed during verification.") }
        guard let limits = artifact.manifest.object?["limits"]?.object, let memory = limits["memory_bytes"]?.uint, let fuel = limits["fuel"]?.uint else { throw MixerFailure("update.limits", "Missing verified resource limits.") }
        let vmResult = try runner([vmIdentity.path, "validate", values["--payload"]!, "--fuel", String(fuel), "--memory-pages", String(memory / 65_536)])
        guard try VerificationFile.tool(vmIdentity.path) == vmIdentity,
              try VerificationFile.read(URL(fileURLWithPath: values["--payload"]!), maximumBytes: 16_777_216) == snapshots["--payload"]! else { throw MixerFailure("update.snapshot-changed", "Verification executable or payload changed during validation.") }
        var valid = false, rejection: String? = vmResult.succeeded ? nil : "Owned VM rejected the executable profile."
        if vmResult.succeeded && !vmResult.outputTruncated {
            do {
                let receipt = try toolReceipt(VMToolReceipt.self, from: vmResult.output, fields: ["profile","valid","inventory_complete","imports","exports","opcodes","extended_opcodes","error","inventory_error"])
                guard receipt.profile == "mixer-integer-v1", receipt.valid, receipt.inventory_complete, receipt.error == nil, receipt.inventory_error == nil else { throw MixerFailure("update.vm-receipt", "Owned VM did not return a valid supported executable-profile receipt.") }
                valid = true
            } catch { rejection = String(describing: error) }
        } else if vmResult.outputTruncated { rejection = "Owned VM output exceeded its byte limit." }
        return LocalUpdateReport(status: valid ? "local-candidate-verified" : "executable-rejected", payloadSHA256: payloadDigest, protocolVerification: protocolResult, executableVerification: vmResult, linkedProtocolVerification: linkedReceipt, protocolTool: protocolIdentity, executableTool: vmIdentity, rejectionReason: rejection)
    }
}
