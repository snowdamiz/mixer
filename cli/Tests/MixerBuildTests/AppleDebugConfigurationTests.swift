import Foundation
import MixerBuild
import Testing

@Test(arguments: ["stock", "plist", "archive"])
func regeneratesPreviousIOSDebugTemplate(_ variant: String) throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-ios-debug-\(UUID())")
    let platform = root.appendingPathComponent("Platforms/iOS")
    try FileManager.default.createDirectory(at: platform, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: root) }
    try Data().write(to: platform.appendingPathComponent("FieldLogApp.swift"))

    var config = ApplicationConfiguration(name: "FieldLog", application: "dev.mixer.fieldlog")
    if variant != "stock" {
        config.iosNative = AppleNativeConfiguration(allowsLocalNetworking: true)
    }
    if variant == "archive" {
        let archive = Data("!<arch>\n".utf8)
        try archive.write(to: platform.appendingPathComponent("libmixer_vm.a"))
        config.iosNative?.simulatorArchive = "libmixer_vm.a"
        config.iosNative?.simulatorArchiveSHA256 = SourceDigest.sha256(archive)
    }
    try JSONFile.write(config, to: root.appendingPathComponent("mixer.yml"))

    let project = try AppleProject.generate(root: root)
    let projectFile = project.appendingPathComponent("project.pbxproj")
    let receiptFile = project.appendingPathComponent("mixer-generated.sha256")
    let current = try String(contentsOf: projectFile, encoding: .utf8)
    let condition = " SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;"
    let debug = try #require(current.split(separator: "\n").first { $0.contains("SWIFT_OPTIMIZATION_LEVEL = \"-Onone\"") })
    let release = try #require(current.split(separator: "\n").first { $0.contains("SWIFT_OPTIMIZATION_LEVEL = \"-O\"") })
    #expect(debug.contains(condition))
    #expect(!release.contains("SWIFT_ACTIVE_COMPILATION_CONDITIONS"))

    let previous = current.replacingOccurrences(of: condition, with: "")
    let receiptSuffix = try String(contentsOf: receiptFile, encoding: .utf8).drop(while: { $0 != "\n" })
    func install(_ source: String) throws -> Data {
        let bytes = Data(source.utf8)
        try bytes.write(to: projectFile)
        let receipt = Data((SourceDigest.sha256(bytes) + receiptSuffix).utf8)
        try receipt.write(to: receiptFile)
        return receipt
    }

    _ = try install(previous)
    _ = try AppleProject.generate(root: root)
    #expect(try String(contentsOf: projectFile, encoding: .utf8) == current)

    let edited = previous + "// handwritten edit\n"
    let editedReceipt = try install(edited)
    let failure = #expect(throws: MixerFailure.self) { try AppleProject.generate(root: root) }
    #expect(failure?.code == "generate.modified")
    #expect(try String(contentsOf: projectFile, encoding: .utf8) == edited)
    #expect(try Data(contentsOf: receiptFile) == editedReceipt)
}
