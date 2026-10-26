import Darwin
import Foundation
import Testing
@testable import MixerBuild

private let vmReceipt = #"{"profile":"mixer-integer-v1","valid":true,"inventory_complete":true,"imports":[],"exports":[],"opcodes":[],"extended_opcodes":[],"error":null,"inventory_error":null}"#

private func signedFixture(_ body: ([String], URL, Data, String) throws -> Void) throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-signed-update-test-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
    defer { try? FileManager.default.removeItem(at: root) }
    let source = try #require(Bundle.module.url(forResource: "signed-release-v1", withExtension: "json", subdirectory: "Fixtures"))
    let vector = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: source)) as? [String: Any])
    var arguments: [String] = []
    let payloadBase64 = try #require(vector["payload"] as? String)
    let payload = try #require(Data(base64Encoded: payloadBase64))
    for (key, field) in [("manifest", "signed_manifest"), ("host", "host"), ("roots", "roots"), ("assignment", "signed_assignment")] {
        let file = root.appendingPathComponent(key)
        try JSONSerialization.data(withJSONObject: try #require(vector[field])).write(to: file)
        arguments += ["--" + key, file.path]
    }
    try payload.write(to: root.appendingPathComponent("payload"))
    arguments += ["--payload", root.appendingPathComponent("payload").path, "--channel", "beta", "--installation", "fixture-installation-1", "--last-sequence", "6", "--now", "1792627300"]
    let signed = try #require(vector["signed_manifest"] as? [String: Any]), manifest = try #require(signed["manifest"] as? [String: Any])
    let receipt: [String: Any] = ["status": "protocol-verified", "artifactSHA256": try #require(vector["artifact_sha256"]), "releaseID": try #require(manifest["release_id"]), "payloadBytes": payload.count, "assignmentSequence": 7, "cohortBucket": try #require(vector["cohort_bucket"]), "executableProfileVerified": false, "policyApproved": false, "activated": false]
    try body(arguments, root, payload, String(decoding: JSONSerialization.data(withJSONObject: receipt), as: UTF8.self))
}

@Test func authenticatedVerifiersReadTheSamePrivateSnapshotAndSignedLimits() throws {
    try signedFixture { args, root, payload, protocolReceipt in
        var calls = 0, snapshot: String?
        let report = try LocalUpdateValidation.verify(arguments: args, verifier: "/usr/bin/true", vm: "/usr/bin/true") { command in
            calls += 1
            if calls == 1 {
                snapshot = command[try #require(command.firstIndex(of: "--payload")) + 1]
                #expect(try Data(contentsOf: URL(fileURLWithPath: snapshot!)) == payload)
                try Data("unverified replacement".utf8).write(to: root.appendingPathComponent("payload"))
            } else {
                #expect(Array(command.prefix(3)) == ["/usr/bin/true", "validate", snapshot!])
                #expect(Array(command.suffix(4)) == ["--fuel", "1000", "--memory-pages", "16"])
                #expect(try Data(contentsOf: URL(fileURLWithPath: command[2])) == payload)
            }
            return CommandResult(command: command, exitCode: 0, output: calls == 1 ? protocolReceipt : vmReceipt)
        }
        #expect(calls == 2 && report.status == "local-candidate-verified")
        #expect(report.payloadSHA256 == SourceDigest.sha256(payload))
        #expect(report.linkedProtocolVerification?.assignmentSequence == 7)
        #expect(report.protocolTool?.sha256.count == 64 && report.executableTool?.sha256.count == 64)
        #expect(!FileManager.default.fileExists(atPath: snapshot!))
    }
}

@Test func linkedProtocolRejectionCannotBeOverriddenBySuccessfulExecutables() throws {
    try signedFixture { args, root, _, _ in
        try Data("unsigned payload".utf8).write(to: root.appendingPathComponent("payload"))
        var calls = 0
        let report = try LocalUpdateValidation.verify(arguments: args, verifier: "/usr/bin/true", vm: "/usr/bin/true") { command in
            calls += 1
            return CommandResult(command: command, exitCode: 0, output: vmReceipt)
        }
        #expect(calls == 0 && report.status == "protocol-rejected")
        #expect(report.executableVerification == nil && report.linkedProtocolVerification == nil)
    }
}

@Test func missingContradictoryAndWrongProfileReceiptsFailClosed() throws {
    try signedFixture { args, _, _, protocolReceipt in
        for output in ["", "{}", protocolReceipt.replacingOccurrences(of: "protocol-verified", with: "error"), protocolReceipt.replacingOccurrences(of: "\"assignmentSequence\":7", with: "\"assignmentSequence\":1")] {
            let report = try LocalUpdateValidation.verify(arguments: args, verifier: "/usr/bin/true", vm: "/usr/bin/true") { command in
                CommandResult(command: command, exitCode: 0, output: output)
            }
            #expect(report.status == "protocol-rejected" && report.executableVerification == nil)
        }
        for output in ["", "{}", vmReceipt.replacingOccurrences(of: "\"valid\":true", with: "\"valid\":false"), vmReceipt.replacingOccurrences(of: "mixer-integer-v1", with: "unknown-profile"), vmReceipt.replacingOccurrences(of: "\"valid\":true", with: "\"valid\":true,\"valid\":false")] {
            var calls = 0
            let report = try LocalUpdateValidation.verify(arguments: args, verifier: "/usr/bin/true", vm: "/usr/bin/true") { command in
                calls += 1
                return CommandResult(command: command, exitCode: 0, output: calls == 1 ? protocolReceipt : output)
            }
            #expect(report.status == "executable-rejected")
        }
        for truncatedCall in [1, 2] {
            var calls = 0
            let report = try LocalUpdateValidation.verify(arguments: args, verifier: "/usr/bin/true", vm: "/usr/bin/true") { command in
                calls += 1
                return CommandResult(command: command, exitCode: 0, output: calls == 1 ? protocolReceipt : vmReceipt, outputTruncated: calls == truncatedCall)
            }
            #expect(report.status == (truncatedCall == 1 ? "protocol-rejected" : "executable-rejected"))
        }
    }
}

@Test func nonRegularInputsFailWithoutOpeningOrBlocking() throws {
    try signedFixture { args, root, _, _ in
        let manifest = root.appendingPathComponent("manifest")
        try FileManager.default.removeItem(at: manifest)
        #expect(mkfifo(manifest.path, 0o600) == 0)
        let started = Date()
        #expect(throws: MixerFailure.self) { try LocalUpdateValidation.verify(arguments: args, verifier: "/usr/bin/true", vm: "/usr/bin/true") }
        #expect(Date().timeIntervalSince(started) < 1)
        try FileManager.default.removeItem(at: manifest)
        try FileManager.default.createSymbolicLink(at: manifest, withDestinationURL: root.appendingPathComponent("payload"))
        #expect(throws: MixerFailure.self) { try LocalUpdateValidation.verify(arguments: args, verifier: "/usr/bin/true", vm: "/usr/bin/true") }
    }
}

@Test func privateSnapshotMutationByAToolIsRejected() throws {
    try signedFixture { args, _, _, protocolReceipt in
        #expect(throws: MixerFailure.self) {
            try LocalUpdateValidation.verify(arguments: args, verifier: "/usr/bin/true", vm: "/usr/bin/true") { command in
                let payload = URL(fileURLWithPath: command[try #require(command.firstIndex(of: "--payload")) + 1])
                try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: payload.path)
                try Data("changed private snapshot".utf8).write(to: payload)
                return CommandResult(command: command, exitCode: 0, output: protocolReceipt)
            }
        }
    }
}

@Test func processOutputLimitDoesNotRequireReadingWholeLogIntoMemory() throws {
    let script = "import sys; sys.stdout.buffer.write(b'x' * (9 * 1024 * 1024)); sys.stdout.write('tail')"
    let result = try ProcessRunner.run(["python3", "-c", script])
    #expect(result.succeeded && result.output.utf8.count == 8 * 1_048_576)
    #expect(result.outputTruncated)
    #expect(result.output.hasSuffix("tail"))
}
