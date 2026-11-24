import Darwin
import Foundation
import Testing
@testable import MixerBuild

@Test func publicProfilesDeclareTheirRequiredEnvironmentFloor() throws {
    for host in [AndroidApplicationHost.publicV3, .publicV4] {
        var config = ApplicationConfiguration(name: "Floor", application: "example.floor")
        config.targets = ["android"]; config.capabilities = []; config.androidHost = host
        try config.validate()
        let files = AndroidPublicHost.files(config)
        let manifest = try #require(files["AndroidManifest.xml"])
        let xml = try XMLDocument(xmlString: manifest)
        let floor = try xml.nodes(forXPath: "/manifest/uses-sdk/@android:minSdkVersion").first?.stringValue
        #expect(floor == "36")
        let java = try #require(files["Java/example/floor/androidhost/PublicActivity.java"])
        #expect(java.contains("android.os.Build.VERSION.SDK_INT < 36"))
        #expect(java.contains("high-contrast read/listener"))
        #expect(files["README.md"]?.contains("full API 28 product acceptance is pending") == true)
        #expect(!files.values.contains(where: { $0.contains("__MIN_API__") }))
        if let outputPath = ProcessInfo.processInfo.environment["R346_OUTPUT"] {
            let output = URL(fileURLWithPath: outputPath).appendingPathComponent(host.rawValue)
            for (path, source) in files {
                let target = output.appendingPathComponent(path)
                try FileManager.default.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
                try source.write(to: target, atomically: true, encoding: .utf8)
            }
        }
        let selection = try #require(files[AndroidPublicHost.selectionFile(config)])
        #expect(selection.contains(host == .publicV4 ? "MEASURED_MULTILINE_LONG_NOTES_V4" : "MEASURED_MULTILINE_RETIREMENT_V3"))
    }
}

@Test func retainedComposeRequiresTheExactLockedModuleAndHostFloor() throws {
    let canonical = try #require(realpath(FileManager.default.temporaryDirectory.path, nil))
    defer { free(canonical) }
    let temporary = URL(fileURLWithPath: String(cString: canonical), isDirectory: true)
        .appendingPathComponent("retained-compose-\(UUID().uuidString)")
    let root = temporary.appendingPathComponent("project")
    let module = root.appendingPathComponent("Platforms/Android/Compose")
    try FileManager.default.createDirectory(at: module.appendingPathComponent("gradle"), withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: temporary) }
    let context = ProcessExecutionContext(receiptDirectory: temporary.appendingPathComponent("receipts"))
    let paths = ["settings.gradle", "build.gradle", "gradle.properties", "toolchain.json",
                 "buildscript-gradle.lockfile", "gradle.lockfile", "gradle/verification-metadata.xml"]
    for path in paths {
        try Data(path.utf8).write(to: module.appendingPathComponent(path))
    }
    let marker = module.appendingPathComponent("mixer-compose.json")
    func select(_ host: String, minimum: Int) throws {
        try Data("""
        {"schema":1,"host":"\(host)","application":"example.compose","minAPI":\(minimum),"targetAPI":37}
        """.utf8).write(to: marker)
    }
    let snapshot = try context.makeInputSnapshot()
    defer { snapshot.removeIfUnheld() }
    #expect(AndroidPublicHost.RetainedSelection(nil).minimumAPI == 28)
    #expect(AndroidPublicHost.RetainedSelection(.publicV3).minimumAPI == 36)
    #expect(AndroidPublicHost.RetainedSelection(.publicV4).minimumAPI == 36)
    #expect(throws: MixerFailure.self) { try AndroidProject.stageRetainedCompose(root: root, in: snapshot) }
    for (host, minimum) in [("legacy-v1", 28), ("public-v4", 36), ("public-compose-v1", 27)] {
        try select(host, minimum: minimum)
        #expect(throws: MixerFailure.self) { try AndroidProject.stageRetainedCompose(root: root, in: snapshot) }
    }
    try select("public-compose-v1", minimum: 28)
    #expect(throws: MixerFailure.self) { try AndroidProject.prepareBuild(root: root) }
    let hidden = module.appendingPathComponent(".gradle")
    try FileManager.default.createDirectory(at: hidden, withIntermediateDirectories: false)
    #expect(throws: MixerFailure.self) { try AndroidProject.stageRetainedCompose(root: root, in: snapshot) }
    try FileManager.default.removeItem(at: hidden)
    let staged = try AndroidProject.stageRetainedCompose(root: root, in: snapshot)
    #expect(staged.selection.host == .publicComposeV1)
    #expect(staged.selection.minAPI == 28)
    #expect(staged.treeSHA256 == (try SourceDigest.exportFingerprint(module)))
    try Data("changed".utf8).write(to: module.appendingPathComponent("build.gradle"))
    #expect(staged.treeSHA256 != (try SourceDigest.exportFingerprint(module)))
    #expect(staged.treeSHA256 == (try SourceDigest.exportFingerprint(staged.directory)))
}

@Test(.enabled(if: ProcessInfo.processInfo.environment["MIXER_COMPOSE_REPLAY"] != nil))
func retainedComposeBuildsTheLockedModuleOffline() throws {
    let env = ProcessInfo.processInfo.environment
    let directory = URL(fileURLWithPath: try #require(env["MIXER_COMPOSE_REPLAY"]), isDirectory: true)
    let root = directory.appendingPathComponent("project", isDirectory: true)
    let receipts = directory.appendingPathComponent("receipts", isDirectory: true)
    let context = ProcessExecutionContext(receiptDirectory: receipts)
    let driver = root.appendingPathComponent("Generated/MixerAndroid/android-build.py")
    let rendered = try AndroidSDKCompatibility.renderDriver(String(contentsOf: AndroidProject.buildDriver(), encoding: .utf8))
    try FileManager.default.createDirectory(at: driver.deletingLastPathComponent(), withIntermediateDirectories: true)
    try Data(rendered.utf8).write(to: driver, options: .withoutOverwriting)
    let keys = ["MIXER_COMPOSE_GRADLE", "ANDROID_HOME", "MIXER_JDK", "MIXER_COMPOSE_DEPENDENCY_CACHE"]
    let toolEnvironment = env.filter { keys.contains($0.key) }
    let python = URL(fileURLWithPath: try #require(env["MIXER_COMPOSE_PYTHON"]))
    let result = try AndroidBuildOutput.buildRetainedCompose(root: root, python: python,
        toolEnvironment: toolEnvironment, context: context)
    #expect(result.receipt.selection.minAPI == 28)
    #expect(result.receipt.selection.targetAPI == 37)
    #expect(result.receipt.apk.sha256 == SourceDigest.sha256(result.apk))
    #expect(result.receipt.toolCommands[1].command.contains("--offline"))
    #expect(context.custodyHold == nil)
    #expect(try FileManager.default.contentsOfDirectory(atPath: receipts.path).allSatisfy { !$0.hasPrefix("mixer-verify-") })
    try result.receiptBytes.write(to: directory.appendingPathComponent("compose-build-receipt-v2.json"),
                                  options: .withoutOverwriting)
    try result.apk.write(to: directory.appendingPathComponent("compose-unsigned.apk"), options: .withoutOverwriting)
}
