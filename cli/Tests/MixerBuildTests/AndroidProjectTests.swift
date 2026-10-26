import Foundation
import MixerUI
import Testing
@testable import MixerBuild

private let repository = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()

@Test func androidSnapshotOwnsOnlyRuntimeRendererCoordinatorAndBridgeAndLocksExactBytes() throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-android-snapshot-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: root) }
    let adapter = repository.appendingPathComponent("native/android")
    let digest = try AndroidProject.snapshot(adapter: adapter, destination: root)
    #expect(try SourceDigest.tree(root) == digest)
    let descriptor = try Data(contentsOf: root.appendingPathComponent("app/assets/MixerAppearanceV2/descriptor.json"))
    let expectedAppearance = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
    let expectedBytes = try UIAppearanceDescriptorCodecV2.canonicalData(expectedAppearance)
    #expect(descriptor == expectedBytes)
    let appearance = try UIAppearanceDescriptorCodecV2.decode(descriptor)
    #expect(appearance == expectedAppearance)
    #expect(appearance.resources.isEmpty)
    guard case let .shared(theme) = appearance.mode else { Issue.record("Default must be shared"); return }
    #expect(theme.typography.font == .systemSans)
    #expect(try SourceDigest.files(in: root.appendingPathComponent("app/assets")).map { String($0.path.dropFirst(root.path.count + 1)) } == ["app/assets/MixerAppearanceV2/descriptor.json"])
    let java = ["Json.java", "UiPacket.java", "NativeRenderer.java", "NativeBridge.java", "MixerActivity.java", "NativeCoordinatorV2.java",
                 "AppearanceDescriptorV2.java", "AppearanceGeometryV2.java", "AppearanceResolverV2.java",
                 "AppearanceNativePathsV2.java", "InstalledAppearanceV2.java", "NativeEnvironmentV2.java",
                 "AuthoredToggleInputV2.java", "NativeAppearanceViewsV2.java", "NativeOwnerV2.java", "OwnerLifecycleV2.java"]
    #expect(Set(try SourceDigest.files(in: root.appendingPathComponent("app/src")).map(\.lastPathComponent)) == Set(java))
    for name in java {
        let relative = "app/src/dev/mixer/android/\(name)"
        #expect(try Data(contentsOf: root.appendingPathComponent(relative)) == Data(contentsOf: adapter.appendingPathComponent(relative)))
    }
    for relative in ["bridge/jni.c", "bridge/mixer_android.h", "bridge/mixer_android_v2.h"] {
        #expect(try Data(contentsOf: root.appendingPathComponent(relative)) == Data(contentsOf: adapter.appendingPathComponent(relative)))
    }
    #expect(!FileManager.default.fileExists(atPath: root.appendingPathComponent("app/src/dev/mixer/android/AdapterInstrumentation.java").path))
    #expect(!FileManager.default.fileExists(atPath: root.appendingPathComponent("Sources/MixerAndroidEngine").path))
    #expect(!FileManager.default.fileExists(atPath: root.appendingPathComponent("engine/Sources/MixerAndroidEngine").path))
    try "changed".write(to: root.appendingPathComponent("bridge/jni.c"), atomically: true, encoding: .utf8)
    #expect(try SourceDigest.tree(root) != digest)
}

@Test(arguments: ["edit", "remove", "rename", "symlink"])
func androidDefaultAppearanceSnapshotChangesInvalidateAdapterLock(_ change: String) throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-android-appearance-lock-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: root) }
    let sdk = root.appendingPathComponent("Generated/MixerSDK")
    let adapter = root.appendingPathComponent("Generated/MixerAndroid")
    try copyCompatibilitySDK(to: sdk)
    let digest = try AndroidProject.snapshot(adapter: repository.appendingPathComponent("native/android"), destination: adapter)
    try JSONFile.write(ApplicationConfiguration(name: "App", application: "dev.example.app"), to: root.appendingPathComponent("mixer.yml"))
    let version = try ProcessRunner.run(["swift", "--version"])
    #expect(version.succeeded)
    var lock = ToolchainLock(sdkDigest: try SourceDigest.tree(sdk), swiftVersion: version.output.trimmingCharacters(in: .whitespacesAndNewlines))
    lock.android = AndroidToolchainLock(adapterDigest: digest, toolchain: AndroidToolchainIdentity(
        schema: 1, sdk_id: "host-test-only", abi: "arm64-v8a", min_api: 28, target_api: 37,
        swift_version: "host-test-only", javac_version: "host-test-only", java_version: "host-test-only",
        python_version: "host-test-only", tools: [:], metadata: [:], distributions: [:], sdk_search_path: "host-test-only"), profile: AndroidSDKCompatibility.profile.lock)
    try JSONFile.write(lock, to: root.appendingPathComponent("mixer.lock"))
    #expect(try ProjectBuild.verifyLock(root: root).android?.adapterDigest == digest)
    let descriptor = adapter.appendingPathComponent("app/assets/MixerAppearanceV2/descriptor.json")
    switch change {
    case "edit": try Data("changed".utf8).write(to: descriptor)
    case "remove": try FileManager.default.removeItem(at: descriptor)
    case "rename": try FileManager.default.moveItem(at: descriptor, to: descriptor.appendingPathExtension("renamed"))
    default:
        let copy = root.appendingPathComponent("descriptor-copy.json")
        try FileManager.default.copyItem(at: descriptor, to: copy)
        try FileManager.default.removeItem(at: descriptor)
        try FileManager.default.createSymbolicLink(at: descriptor, withDestinationURL: copy)
    }
    #expect(throws: (any Error).self) { _ = try ProjectBuild.verifyLock(root: root) }
    let direct = try ProcessRunner.run(["python3", adapter.appendingPathComponent("android-build.py").path, "build", root.path])
    #expect(!direct.succeeded)
    #expect(direct.output.contains(change == "edit" ? "source compatibility rejected" : "Android appearance"))
    #expect(!direct.output.contains("Traceback"))
    #expect(!FileManager.default.fileExists(atPath: root.appendingPathComponent(".mixer").path))
}

@Test(arguments: ["NativeCoordinatorV2.java", "AuthoredToggleInputV2.java", "NativeOwnerV2.java", "OwnerLifecycleV2.java"], ["edit", "remove", "rename"])
func androidCoordinatorAndAuthoredToggleSnapshotChangesInvalidateAdapterLock(_ filename: String, _ change: String) throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-android-coordinator-lock-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: root) }
    let sdk = root.appendingPathComponent("Generated/MixerSDK")
    let adapter = root.appendingPathComponent("Generated/MixerAndroid")
    try copyCompatibilitySDK(to: sdk)
    let digest = try AndroidProject.snapshot(adapter: repository.appendingPathComponent("native/android"), destination: adapter)
    try JSONFile.write(ApplicationConfiguration(name: "App", application: "dev.example.app"), to: root.appendingPathComponent("mixer.yml"))
    let version = try ProcessRunner.run(["swift", "--version"])
    #expect(version.succeeded)
    var lock = ToolchainLock(sdkDigest: try SourceDigest.tree(sdk), swiftVersion: version.output.trimmingCharacters(in: .whitespacesAndNewlines))
    // verifyLock validates source and host compiler identity without invoking
    // Android tools. This synthetic identity does not qualify a toolchain.
    lock.android = AndroidToolchainLock(adapterDigest: digest, toolchain: AndroidToolchainIdentity(
        schema: 1, sdk_id: "host-test-only", abi: "arm64-v8a", min_api: 28, target_api: 37,
        swift_version: "host-test-only", javac_version: "host-test-only", java_version: "host-test-only",
        python_version: "host-test-only", tools: [:], metadata: [:], distributions: [:], sdk_search_path: "host-test-only"), profile: AndroidSDKCompatibility.profile.lock)
    try JSONFile.write(lock, to: root.appendingPathComponent("mixer.lock"))
    #expect(try ProjectBuild.verifyLock(root: root).android?.adapterDigest == digest)
    let source = adapter.appendingPathComponent("app/src/dev/mixer/android/\(filename)")
    switch change {
    case "edit": try Data("changed source".utf8).write(to: source)
    case "remove": try FileManager.default.removeItem(at: source)
    default: try FileManager.default.moveItem(at: source, to: source.appendingPathExtension("renamed"))
    }
    // A caller can recompute the generic lock, but cannot change the compiled
    // source-pair policy for a changed, removed, or renamed owner/core source.
    lock.android?.adapterDigest = try SourceDigest.tree(adapter)
    try JSONFile.write(lock, to: root.appendingPathComponent("mixer.lock"))
    #expect(throws: MixerFailure.self) {
        do { _ = try ProjectBuild.verifyLock(root: root) }
        catch let failure as MixerFailure { #expect(failure.code == "android.sdk-compatibility"); throw failure }
    }
    let direct = try ProcessRunner.run(["python3", adapter.appendingPathComponent("android-build.py").path, "build", root.path])
    #expect(!direct.succeeded)
    #expect(direct.output.contains("Android SDK source compatibility rejected"))
    #expect(!FileManager.default.fileExists(atPath: root.appendingPathComponent(".mixer").path))
}

@Test func unsupportedAndroidRequestDoesNotCreateOrOverwriteProject() throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-android-create-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: root) }
    let sdk = root.appendingPathComponent("SDK")
    try FileManager.default.createDirectory(at: sdk, withIntermediateDirectories: true)
    try "// fixture".write(to: sdk.appendingPathComponent("Package.swift"), atomically: true, encoding: .utf8)
    let target = root.appendingPathComponent("App")
    #expect(throws: MixerFailure.self) { try ProjectGenerator.create(name: "App", application: "com.example.app", destination: target, sdk: sdk, platform: "unknown") }
    #expect(!FileManager.default.fileExists(atPath: target.path))
    #expect(throws: MixerFailure.self) { try ProjectGenerator.create(name: "App", application: "com.example.app", destination: target, sdk: sdk, platform: "android") }
    #expect(!FileManager.default.fileExists(atPath: target.path))
    _ = try ProjectGenerator.create(name: "App", application: "com.example.app", destination: target, sdk: sdk)
    #expect(try ApplicationConfiguration.load(target).targets == ["ios"])
    #expect(try ApplicationConfiguration.load(target).capabilities.isEmpty)
    #expect(throws: MixerFailure.self) { try AndroidProject.build(root: target) }
}

@Test func installedDistributionHashesRejectDirectorySymlinksOutsideTheHashRoot() throws {
    let parent = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-tool-tree-\(UUID().uuidString)")
    let distribution = parent.appendingPathComponent("tool")
    let outside = parent.appendingPathComponent("outside")
    defer { try? FileManager.default.removeItem(at: parent) }
    try FileManager.default.createDirectory(at: distribution.appendingPathComponent("real"), withIntermediateDirectories: true)
    try FileManager.default.createDirectory(at: outside, withIntermediateDirectories: true)
    try "bytes".write(to: distribution.appendingPathComponent("real/source"), atomically: true, encoding: .utf8)
    try FileManager.default.createSymbolicLink(at: distribution.appendingPathComponent("internal"), withDestinationURL: distribution.appendingPathComponent("real"))
    let code = "import runpy,sys,pathlib; print(runpy.run_path(sys.argv[1])['tree'](pathlib.Path(sys.argv[2])))"
    let accepted = try ProcessRunner.run(["python3", "-c", code, try AndroidProject.buildDriver().path, distribution.path])
    #expect(accepted.succeeded)
    try FileManager.default.createSymbolicLink(at: distribution.appendingPathComponent("external"), withDestinationURL: outside)
    let rejected = try ProcessRunner.run(["python3", "-c", code, try AndroidProject.buildDriver().path, distribution.path])
    #expect(!rejected.succeeded)
    #expect(rejected.output.contains("symlink escapes hashed root"))
}

@Test func rawAndroidDriverRefusesUnrenderedProfileBeforeTouchingOutputFiles() throws {
    let parent = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-driver-path-\(UUID().uuidString)")
    let root = parent.appendingPathComponent("App")
    defer { try? FileManager.default.removeItem(at: parent) }
    for relative in ["Generated/MixerSDK", "Generated/MixerAndroid"] {
        try FileManager.default.createDirectory(at: root.appendingPathComponent(relative), withIntermediateDirectories: true)
    }
    let empty = try SourceDigest.tree(root.appendingPathComponent("Generated/MixerSDK"))
    let descriptor = root.appendingPathComponent("Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json")
    try FileManager.default.createDirectory(at: descriptor.deletingLastPathComponent(), withIntermediateDirectories: true)
    try Data("layout-only fixture".utf8).write(to: descriptor)
    let adapterDigest = try SourceDigest.tree(root.appendingPathComponent("Generated/MixerAndroid"))
    let lock: [String: Any] = ["schema": 1, "sdkDigest": empty, "android": ["adapterDigest": adapterDigest, "toolchain": [:]]]
    try JSONSerialization.data(withJSONObject: lock).write(to: root.appendingPathComponent("mixer.lock"))
    var config = ApplicationConfiguration(name: "App", application: "dev.example.app")
    config.capabilities = []
    let sentinel = parent.appendingPathComponent("should-survive-unsigned.apk")
    try "sentinel".write(to: sentinel, atomically: true, encoding: .utf8)
    for unsafe in [parent.appendingPathComponent("should-survive").path, "../../should-survive", "bad/name", "App;command"] {
        config.name = unsafe
        try JSONFile.write(config, to: root.appendingPathComponent("mixer.yml"))
        let result = try ProcessRunner.run(["python3", try AndroidProject.buildDriver().path, "build", root.path])
        #expect(!result.succeeded); #expect(result.output.contains("Android SDK source profile is not rendered or supported"))
        #expect(try String(contentsOf: sentinel, encoding: .utf8) == "sentinel")
        #expect(!FileManager.default.fileExists(atPath: root.appendingPathComponent(".mixer").path))
    }
}
