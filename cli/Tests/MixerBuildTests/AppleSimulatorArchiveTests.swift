import Foundation
import MixerBuild
import Testing

@Test func simulatorArchiveDeclarationRefusesDeviceBuildBeforeGeneration() throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-archive-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: root) }

    let archive = "Native/libmixer_vm.a"
    let digest = String(repeating: "0", count: 64)
    let configURL = root.appendingPathComponent("mixer.yml")
    var config = ApplicationConfiguration(name: "FieldLog", application: "dev.mixer.fieldlog")
    config.iosNative = AppleNativeConfiguration(simulatorArchive: archive, simulatorArchiveSHA256: digest)
    try JSONFile.write(config, to: configURL)
    #expect(try ApplicationConfiguration.load(root) == config)

    let failure = #expect(throws: MixerFailure.self) { try AppleProject.build(root: root, simulator: false) }
    #expect(failure?.code == "build.ios-native-archive")
    #expect(!FileManager.default.fileExists(atPath: root.appendingPathComponent("Platforms").path))
}
