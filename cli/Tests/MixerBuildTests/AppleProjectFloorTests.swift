import Foundation
import MixerBuild
import Testing

private let floor26 = "IPHONEOS_DEPLOYMENT_TARGET = 26.0;"
private let floor17 = "IPHONEOS_DEPLOYMENT_TARGET = 17.0;"

// The fixtures start from `mixer create` at e12a685633. The earlier templates
// predate 78d25a1b8d (Debug condition) and 3c16aa8af4 (iOS 26 floor).
@Test(arguments: ["26-debug", "26", "17-legacy", "26-edited"])
func recognizesHistoricalIOSProjectsByTheirBytes(_ variant: String) throws {
    let fm = FileManager.default
    let workspace = fm.temporaryDirectory.appendingPathComponent("mixer-ios-floor-\(UUID())")
    defer { try? fm.removeItem(at: workspace) }
    let sdk = workspace.appendingPathComponent("sdk")
    try fm.createDirectory(at: sdk, withIntermediateDirectories: true)
    try Data("// SDK fixture\n".utf8).write(to: sdk.appendingPathComponent("Package.swift"))
    let root = workspace.appendingPathComponent("App")
    _ = try SuiteOwnedRunner.create(name: "FloorApp", application: "dev.mixer.floorapp", destination: root, sdk: sdk)

    let package = root.appendingPathComponent("Package.swift")
    let packageBytes = try Data(contentsOf: package)
    #expect(String(decoding: packageBytes, as: UTF8.self).contains(".iOS(\"17.0\")"))
    let platform = root.appendingPathComponent("Platforms/iOS")
    let nativeSource = platform.appendingPathComponent("FloorAppApp.swift")
    let appOwned = try Data(contentsOf: nativeSource) + Data("\n// App-owned edit\n".utf8)
    try appOwned.write(to: nativeSource)

    let project = platform.appendingPathComponent("FloorApp.xcodeproj")
    let pbxproj = project.appendingPathComponent("project.pbxproj")
    let receipt = project.appendingPathComponent("mixer-generated.sha256")
    let expected = try currentProjectBytes()
    #expect(try Data(contentsOf: pbxproj) == expected)
    #expect(try Data(contentsOf: receipt) == projectReceipt(expected))

    let historical = try projectFixture(variant)
    let historicalReceipt = projectReceipt(historical)
    try historical.write(to: pbxproj)
    try historicalReceipt.write(to: receipt)
    if variant == "26-edited" {
        let failure = #expect(throws: MixerFailure.self) { try AppleProject.generate(root: root) }
        #expect(failure?.code == "generate.modified")
        #expect(try Data(contentsOf: pbxproj) == historical)
        #expect(try Data(contentsOf: receipt) == historicalReceipt)
    } else {
        #expect(try AppleProject.generate(root: root).path == project.path)
        #expect(try Data(contentsOf: pbxproj) == expected)
        #expect(try Data(contentsOf: receipt) == projectReceipt(expected))

        let then = Date(timeIntervalSince1970: 1_000_000_000)
        for file in [pbxproj, receipt] {
            try fm.setAttributes([.modificationDate: then], ofItemAtPath: file.path)
        }
        #expect(try AppleProject.generate(root: root).path == project.path)
        #expect(try Data(contentsOf: pbxproj) == expected)
        #expect(try Data(contentsOf: receipt) == projectReceipt(expected))
        for file in [pbxproj, receipt] {
            let attributes = try fm.attributesOfItem(atPath: file.path)
            #expect(attributes[.modificationDate] as? Date == then)
        }
    }
    #expect(try Data(contentsOf: package) == packageBytes)
    #expect(try Data(contentsOf: nativeSource) == appOwned)
}

@Test(arguments: [false, true], [false, true])
func recoversInterruptedIOSFloorGeneration(olderTransaction: Bool, projectWritten: Bool) throws {
    struct Artifacts: Encodable {
        let project: Data
        let receipt: Data
    }
    struct Transaction: Encodable {
        let before: Artifacts
        let after: Artifacts
    }
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-ios-floor-recovery-\(UUID())")
    let project = root.appendingPathComponent("Platforms/iOS/FloorApp.xcodeproj")
    try FileManager.default.createDirectory(at: project, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: root) }
    let config = ApplicationConfiguration(name: "FloorApp", application: "dev.mixer.floorapp")
    try JSONFile.write(config, to: root.appendingPathComponent("mixer.yml"))

    let expected = try currentProjectBytes()
    let before = try projectFixture(olderTransaction ? "26" : "26-debug")
    let after = olderTransaction ? try projectFixture("26-debug") : expected
    let transaction = Transaction(before: Artifacts(project: before, receipt: projectReceipt(before)),
                                  after: Artifacts(project: after, receipt: projectReceipt(after)))
    let pending = try Data("mixer-ios-generation-transaction-v2\n".utf8) + JSONFile.data(transaction)
    let pbxproj = project.appendingPathComponent("project.pbxproj")
    let receipt = project.appendingPathComponent("mixer-generated.sha256")
    try (projectWritten ? after : before).write(to: pbxproj)
    try pending.write(to: receipt)

    #expect(try AppleProject.generate(root: root).path == project.path)
    #expect(try Data(contentsOf: pbxproj) == expected)
    #expect(try Data(contentsOf: receipt) == projectReceipt(expected))
}

private func projectFixture(_ name: String) throws -> Data {
    let resources = try #require(Bundle.module.resourceURL)
    let fixture = resources.appendingPathComponent("Fixtures/AppleProject/\(name).pbxproj")
    return try Data(contentsOf: fixture)
}

private func currentProjectBytes() throws -> Data {
    let baseline = String(decoding: try projectFixture("26-debug"), as: UTF8.self)
    return Data(baseline.replacingOccurrences(of: floor26, with: floor17).utf8)
}

private func projectReceipt(_ project: Data) -> Data {
    Data((SourceDigest.sha256(project) + "\n").utf8)
}
