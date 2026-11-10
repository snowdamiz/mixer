import Foundation
import Testing
@testable import MixerBuild

@Test func r59ProductionGenerationAndConfigSelection() throws {
    let scratch = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-generated-v3-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: scratch, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: scratch) }
    let sdk = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("sdk")
    // Create the real starter through the public create path without an Android
    // cross-toolchain probe. Then exercise production config loading/generation.
    let legacy = scratch.appendingPathComponent("Legacy")
    _ = try ProjectGenerator.create(name: "Legacy", application: "example.r59.legacy", destination: legacy, sdk: sdk)
    var config = try ApplicationConfiguration.load(legacy)
    config.targets.append("android")
    try JSONFile.write(config, to: legacy.appendingPathComponent("mixer.yml"))
    try FileManager.default.removeItem(at: legacy.appendingPathComponent("Platforms/Android/README.md"))
    try AndroidProject.generate(root: legacy)
    let manifest = try String(contentsOf: legacy.appendingPathComponent("Platforms/Android/AndroidManifest.xml"), encoding: .utf8)
    #expect(manifest.contains("dev.mixer.android.MixerActivity"))
    #expect(!manifest.contains("PublicActivity"))
    #expect(!FileManager.default.fileExists(atPath: legacy.appendingPathComponent("Platforms/Android/public-host-v3.json").path))
    #expect(throws: (any Error).self) { try AndroidProject.generate(root: legacy) }
    #expect(throws: (any Error).self) {
        _ = try ProjectGenerator.create(name: "Bad", application: "example.r59.bad", destination: scratch.appendingPathComponent("Bad"), sdk: sdk, androidHost: .publicV3)
    }
    let publicRoot = scratch.appendingPathComponent("Public")
    _ = try ProjectGenerator.create(name: "Public", application: "example.r59.publicapp", destination: publicRoot, sdk: sdk)
    var selected = try ApplicationConfiguration.load(publicRoot)
    selected.targets.append("android"); selected.androidHost = .publicV3
    try JSONFile.write(selected, to: publicRoot.appendingPathComponent("mixer.yml"))
    #expect(try ApplicationConfiguration.load(publicRoot).androidHost == .publicV3)
    try FileManager.default.removeItem(at: publicRoot.appendingPathComponent("Platforms/Android/README.md"))
    try AndroidProject.generate(root: publicRoot)
    #expect(try String(contentsOf: publicRoot.appendingPathComponent("Platforms/Android/public-host-v3.json"), encoding: .utf8) == AndroidPublicHost.selection)
    #expect(throws: (any Error).self) { try AndroidProject.generate(root: publicRoot) }
    selected.application = "dev.mixer.android.consumer"
    #expect(throws: (any Error).self) { try selected.validate() }
    selected.application = "example.class.consumer"
    #expect(throws: (any Error).self) { try selected.validate() }
    // Old serialized configuration still decodes with the optional key absent.
    #expect(config.androidHost == nil)
    let unknown = try JSONSerialization.jsonObject(with: JSONFile.data(config)) as! [String: Any]
    var modified = unknown; modified["androidHost"] = "public-v99"
    try JSONSerialization.data(withJSONObject: modified).write(to: legacy.appendingPathComponent("mixer.yml"))
    #expect(throws: (any Error).self) { try ApplicationConfiguration.load(legacy) }
}
