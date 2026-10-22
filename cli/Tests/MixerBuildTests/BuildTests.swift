import Foundation
import Testing
@testable import MixerBuild

private func temporary(_ body: (URL) throws -> Void) throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-tests-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: root) }
    try body(root)
}

@Test func configurationRejectsUnsafeAndUnknownValues() throws {
    try temporary { root in
        var config = ApplicationConfiguration(name: "FieldLog", application: "com.example.fieldlog")
        try JSONFile.write(config, to: root.appendingPathComponent("mixer.yml"))
        #expect(try ApplicationConfiguration.load(root) == config)
        config.updates.requireArtifactSignature = false
        #expect(throws: MixerFailure.self) { try config.validate() }
        config.updates.requireArtifactSignature = true
        config.targets = ["ios", "ios"]
        #expect(throws: MixerFailure.self) { try config.validate() }
        var object = try #require(JSONSerialization.jsonObject(with: JSONFile.data(ApplicationConfiguration(name: "A", application: "com.example.a"))) as? [String: Any])
        object["silentTypo"] = true
        try JSONSerialization.data(withJSONObject: object).write(to: root.appendingPathComponent("mixer.yml"))
        #expect(throws: MixerFailure.self) { try ApplicationConfiguration.load(root) }
    }
}

@Test func sourceDigestIsStableAndContentSensitive() throws {
    try temporary { root in
        try "a".write(to: root.appendingPathComponent("a.swift"), atomically: true, encoding: .utf8)
        let first = try SourceDigest.tree(root)
        let build = root.appendingPathComponent(".build")
        try FileManager.default.createDirectory(at: build, withIntermediateDirectories: true)
        try "ignored".write(to: build.appendingPathComponent("out"), atomically: true, encoding: .utf8)
        #expect(try SourceDigest.tree(root) == first)
        try "b".write(to: root.appendingPathComponent("a.swift"), atomically: true, encoding: .utf8)
        #expect(try SourceDigest.tree(root) != first)
        try FileManager.default.createSymbolicLink(at: root.appendingPathComponent("escape"), withDestinationURL: URL(fileURLWithPath: "/etc/hosts"))
        #expect(throws: MixerFailure.self) { try SourceDigest.tree(root) }
    }
}

@Test func createIsAtomicLocksSnapshotAndNeverOverwrites() throws {
    try temporary { root in
        let sdk = root.appendingPathComponent("sdk")
        try FileManager.default.createDirectory(at: sdk, withIntermediateDirectories: true)
        try "// test SDK fixture".write(to: sdk.appendingPathComponent("Package.swift"), atomically: true, encoding: .utf8)
        let project = root.appendingPathComponent("App")
        let result = try ProjectGenerator.create(name: "App", application: "com.example.app", destination: project, sdk: sdk)
        let expectedDigest = try SourceDigest.tree(sdk)
        #expect(result.sdkDigest == expectedDigest)
        #expect(try ProjectBuild.verifyLock(root: project).sdkDigest == result.sdkDigest)
        #expect(throws: MixerFailure.self) { try ProjectGenerator.create(name: "App", application: "com.example.app", destination: project, sdk: sdk) }
        let exported = root.appendingPathComponent("Export")
        try "development-secret".write(to: project.appendingPathComponent(".env"), atomically: true, encoding: .utf8)
        let exportDigest = try ProjectBuild.export(root: project, destination: exported)
        let projectDigest = try SourceDigest.tree(project)
        #expect(exportDigest == projectDigest)
        #expect(!FileManager.default.fileExists(atPath: exported.appendingPathComponent(".env").path))
        let xcode = try AppleProject.generate(root: project).appendingPathComponent("project.pbxproj")
        try "// user edit".write(to: xcode, atomically: true, encoding: .utf8)
        #expect(throws: MixerFailure.self) { try AppleProject.generate(root: project) }
        try "changed".write(to: project.appendingPathComponent("Generated/MixerSDK/Package.swift"), atomically: true, encoding: .utf8)
        #expect(throws: MixerFailure.self) { try ProjectBuild.verifyLock(root: project) }
    }
}

@Test func importerIsReadOnlyAndNeverAuthorizesRelease() throws {
    try temporary { root in
        try "import SwiftUI\nlet p: UnsafeMutablePointer<Int>? = nil\n".write(to: root.appendingPathComponent("Screen.swift"), atomically: true, encoding: .utf8)
        let before = try SourceDigest.tree(root)
        let report = try MigrationInspector.inspect(root)
        #expect(report.technicalEligibility == "unverified")
        #expect(report.findings.map(\.line) == [1, 2])
        #expect(report.findings.first?.category == "adaptation-required")
        #expect(try SourceDigest.tree(root) == before)
    }
}

@Test func processPreservesFailureDiagnosticsWithoutShellExpansion() throws {
    let result = try ProcessRunner.run(["/usr/bin/printf", "%s", "$(echo secret); `pwd`"])
    #expect(result.succeeded)
    #expect(result.output == "$(echo secret); `pwd`")
    let failure = try ProcessRunner.run(["/usr/bin/false"])
    #expect(!failure.succeeded)
}
