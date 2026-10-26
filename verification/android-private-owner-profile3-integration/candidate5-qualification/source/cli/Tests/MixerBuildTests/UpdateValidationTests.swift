import Foundation
import Testing
@testable import MixerBuild

private func fixture(_ body: ([String], URL) throws -> Void) throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-update-test-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
    defer { try? FileManager.default.removeItem(at: root) }
    var arguments: [String] = []
    for key in ["manifest", "payload", "host", "roots", "assignment"] {
        let file = root.appendingPathComponent(key)
        try Data(key.utf8).write(to: file)
        arguments += ["--" + key, file.path]
    }
    arguments += ["--channel", "internal", "--installation", "local-test", "--last-sequence", "0", "--now", "1"]
    try body(arguments, root)
}

@Test func unsignedInputsCannotReachExternalVerification() throws {
    try fixture { args, _ in
        var calls = 0
        let report = try LocalUpdateValidation.verify(arguments: args, verifier: "verifier", vm: "vm") { command in
            calls += 1
            return CommandResult(command: command, exitCode: 0, output: "test-only")
        }
        #expect(calls == 0)
        #expect(report.payloadSHA256 == SourceDigest.sha256(Data("payload".utf8)))
        #expect(report.status == "protocol-rejected")
    }
}

@Test func protocolRejectionDoesNotInvokeVM() throws {
    try fixture { args, _ in
        var calls = 0
        let report = try LocalUpdateValidation.verify(arguments: args, verifier: "verifier", vm: "vm") { command in
            calls += 1
            return CommandResult(command: command, exitCode: 1, output: "invalid signature")
        }
        #expect(calls == 0)
        #expect(report.status == "protocol-rejected")
        #expect(report.executableVerification == nil)
    }
}

@Test func localVerificationRejectsDuplicateOptionsAndOversizedInputs() throws {
    try fixture { args, root in
        var duplicate = args
        duplicate[2] = "--manifest"
        #expect(throws: MixerFailure.self) {
            try LocalUpdateValidation.verify(arguments: duplicate, verifier: "missing", vm: "missing")
        }
        try Data(repeating: 0, count: 1_048_577).write(to: root.appendingPathComponent("manifest"))
        #expect(throws: MixerFailure.self) {
            try LocalUpdateValidation.verify(arguments: args, verifier: "missing", vm: "missing")
        }
    }
}
