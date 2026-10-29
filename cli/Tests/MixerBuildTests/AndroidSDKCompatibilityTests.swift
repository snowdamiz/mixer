import Foundation
import Testing
import MixerUI
@testable import MixerBuild
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

let compatibilityRepository = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()

func copyCompatibilitySDK(to sdk: URL) throws {
    for relative in AndroidSDKCompatibility.profile.sdk_files.keys {
        let destination = sdk.appendingPathComponent(relative)
        try FileManager.default.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
        try FileManager.default.copyItem(at: compatibilityRepository.appendingPathComponent("sdk/" + relative), to: destination)
    }
}
func compatibilityToolchain() -> AndroidToolchainIdentity {
    AndroidToolchainIdentity(schema: 1, sdk_id: "host-test-only", abi: "arm64-v8a", min_api: 28, target_api: 37,
        swift_version: "host-test-only", javac_version: "host-test-only", java_version: "host-test-only", python_version: "host-test-only",
        tools: [:], metadata: [:], distributions: [:], sdk_search_path: "host-test-only")
}
func compatibilityProject(_ root: URL) throws -> ToolchainLock {
    try copyCompatibilitySDK(to: root.appendingPathComponent("Generated/MixerSDK"))
    let adapterDigest = try AndroidProject.snapshot(adapter: compatibilityRepository.appendingPathComponent("native/android"), destination: root.appendingPathComponent("Generated/MixerAndroid"))
    var config = ApplicationConfiguration(name: "App", application: "dev.example.app"); config.capabilities = []
    try JSONFile.write(config, to: root.appendingPathComponent("mixer.yml"))
    var lock = ToolchainLock(sdkDigest: try SourceDigest.tree(root.appendingPathComponent("Generated/MixerSDK")), swiftVersion: "TOOL-ORDER-SENTINEL")
    lock.android = AndroidToolchainLock(adapterDigest: adapterDigest, toolchain: compatibilityToolchain(), profile: AndroidSDKCompatibility.profile.lock)
    try JSONFile.write(lock, to: root.appendingPathComponent("mixer.lock"))
    return lock
}
private func expectCompatibilityFailure(_ operation: () throws -> Void, code: String = "android.sdk-compatibility") {
    do { try operation(); Issue.record("Expected refusal") }
    catch let failure as MixerFailure { #expect(failure.code == code) }
    catch { Issue.record("Expected actionable MixerFailure, received \(error)") }
}
private func allAdmissionEntrypoints(_ root: URL, code: String = "android.sdk-compatibility") {
    expectCompatibilityFailure({ _ = try ProjectBuild.verifyLock(root: root) }, code: code)
    for platform in ["android", "host", "ios"] {
        expectCompatibilityFailure({ _ = try ProjectBuild.run(root: root, test: false, platform: platform) }, code: code)
    }
    expectCompatibilityFailure({ _ = try AndroidProject.build(root: root) }, code: code)
    let destination = root.deletingLastPathComponent().appendingPathComponent("Export-\(UUID().uuidString)")
    expectCompatibilityFailure({ _ = try ProjectBuild.export(root: root, destination: destination) }, code: code)
    #expect(!FileManager.default.fileExists(atPath: destination.path))
    #expect(!FileManager.default.fileExists(atPath: root.appendingPathComponent(".mixer").path))
}

@Test func androidCompatibilityLinkedSDKAndTypedDefaultMatchCompiledPolicy() throws {
    let p = AndroidSDKCompatibility.profile
    #expect(p.id == "mixer.android-source-pair.6")
    #expect(p.sdk_compatibility_sha256 == "bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0")
    #expect(p.adapter_compatibility_sha256 == "7765667bc3e4b1d45a58ac122ff61b2fbfd7bcfe09b2172ffced62189fb00885")
    #expect(p.adapter_files["Sources/MixerAndroidRuntime/DocumentSession.swift"]?.bytes == 4328)
    #expect(p.adapter_files["Sources/MixerAndroidRuntime/DocumentSession.swift"]?.sha256 == "cf1954af12e316bcd7cf8ea4def41d2dc6b26921fffa60177bce477c7f0749b7")
    #expect(p.sdk_files.count == 22); #expect(p.adapter_files.count == 23)
    try AndroidSDKCompatibility.admitInput(sdk: compatibilityRepository.appendingPathComponent("sdk"), adapter: compatibilityRepository.appendingPathComponent("native/android"))
    let value = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
    let bytes = try UIAppearanceDescriptorCodecV2.canonicalData(value)
    #expect(try UIAppearanceDescriptorCodecV2.decode(bytes) == value)
    try AndroidSDKCompatibility.admitDefault(bytes)
    #expect(bytes.count == 9587)
}

@Test func androidCompatibilityRenderingHasExactlyOneMarkerAndRejectsMalformedTemplates() throws {
    let raw = try String(contentsOf: AndroidProject.buildDriver(), encoding: .utf8)
    let marker = AndroidSDKCompatibility.marker
    #expect(raw.components(separatedBy: marker).count == 2)
    let rendered = try AndroidSDKCompatibility.renderDriver(raw)
    #expect(!rendered.contains(marker))
    #expect(rendered.components(separatedBy: "SOURCE_PROFILE_HEX = '").count == 2)
    #expect(throws: MixerFailure.self) { try AndroidSDKCompatibility.renderDriver(raw.replacingOccurrences(of: marker, with: "missing")) }
    #expect(throws: MixerFailure.self) { try AndroidSDKCompatibility.renderDriver(raw + marker) }
}

private let manifestCases = ["Package@swift-6.4.swift", "package.swift", "PACKAGE.SWIFT", "Package.swift.bak", "Package.resolved", "Pac\u{212A}age.swift", "Pac\u{212A}age@swift-6.4.swift", "unrelated-東京"]
@Test(arguments: manifestCases)
func androidCompatibilityManifestNamespaceRejectsInputAndEveryGeneratedEntrypoint(_ name: String) throws {
    let base = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-profile-ns-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: base) }
    let root = base.appendingPathComponent("App")
    var lock = try compatibilityProject(root)
    let sdk = root.appendingPathComponent("Generated/MixerSDK")
    let item = sdk.appendingPathComponent(name)
    if name.lowercased() == "package.swift" || name == "Pac\u{212A}age.swift" { try FileManager.default.removeItem(at: sdk.appendingPathComponent("Package.swift")) }
    try Data("unadmitted selector".utf8).write(to: item)
    // Recompute the unauthenticated whole lock independently of source admission.
    lock.sdkDigest = try SourceDigest.tree(sdk)
    try JSONFile.write(lock, to: root.appendingPathComponent("mixer.lock"))
    allAdmissionEntrypoints(root)
    let target = base.appendingPathComponent("Created")
    expectCompatibilityFailure({ _ = try ProjectGenerator.create(name: "Created", application: "dev.example.created", destination: target, sdk: sdk, platform: "android", androidAdapter: compatibilityRepository.appendingPathComponent("native/android")) }, code: "create.android-sdk-compatibility")
    #expect(!FileManager.default.fileExists(atPath: target.path))
    #expect(try !FileManager.default.contentsOfDirectory(atPath: base.path).contains { $0.hasPrefix(".mixer-create-") })
}

@Test(arguments: ["extra", "hidden", "excluded", "empty-directory", "missing", "case", "source-case", "source-ancestor", "nested-symlink", "file-symlink", "directory-file", "fifo", "oversized", "short", "same-size", "manifest-symlink", "manifest-fifo", "manifest-directory", "manifest-oversized", "selector-symlink", "selector-fifo", "selector-directory", "selector-oversized", "adapter-extra", "adapter-case", "asset-case", "asset-oversized", "asset-symlink"])
func androidCompatibilityExactInventoryTypeLengthAndHashRefuseBeforeGenericSourcesAndTools(_ change: String) throws {
    let base = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-profile-layout-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: base) }
    let root = base.appendingPathComponent("App")
    _ = try compatibilityProject(root)
    let sdk = root.appendingPathComponent("Generated/MixerSDK")
    let core = sdk.appendingPathComponent("Sources/MixerCore")
    var file = core.appendingPathComponent("Lifecycle.swift")
    let fm = FileManager.default
    if change.hasPrefix("manifest-") { file = sdk.appendingPathComponent("Package.swift") }
    if change.hasPrefix("selector-") { file = sdk.appendingPathComponent("Package@swift-6.4.swift") }
    switch change {
    case "extra", "hidden", "excluded": try Data("extra".utf8).write(to: core.appendingPathComponent(change == "extra" ? "unknown.txt" : change == "hidden" ? ".env" : "secret.key"))
    case "empty-directory": try fm.createDirectory(at: core.appendingPathComponent(".build"), withIntermediateDirectories: true)
    case "missing": try fm.removeItem(at: file)
    case "case": try fm.moveItem(at: core, to: core.deletingLastPathComponent().appendingPathComponent("mixercore"))
    case "source-case": try fm.moveItem(at: file, to: file.deletingLastPathComponent().appendingPathComponent("lifecycle.swift"))
    case "source-ancestor": try fm.moveItem(at: sdk.appendingPathComponent("Sources"), to: sdk.appendingPathComponent("sources"))
    case "nested-symlink":
        let outside = base.appendingPathComponent("Core"); try fm.moveItem(at: core, to: outside); try fm.createSymbolicLink(at: core, withDestinationURL: outside)
    case "file-symlink", "manifest-symlink", "selector-symlink":
        try? fm.removeItem(at: file); try fm.createSymbolicLink(at: file, withDestinationURL: base.appendingPathComponent("missing"))
    case "directory-file", "manifest-directory", "selector-directory":
        try? fm.removeItem(at: file); try fm.createDirectory(at: file, withIntermediateDirectories: true)
    case "fifo", "manifest-fifo", "selector-fifo":
        try? fm.removeItem(at: file); #expect(mkfifo(file.path, 0o600) == 0)
    case "oversized", "manifest-oversized", "selector-oversized": try Data(repeating: 32, count: 2_000_000).write(to: file)
    case "short": try Data("x".utf8).write(to: file)
    case "same-size": let count = try Data(contentsOf: file).count; try Data(repeating: 32, count: count).write(to: file)
    case "adapter-extra": try Data().write(to: root.appendingPathComponent("Generated/MixerAndroid/app/src/.env"))
    case "adapter-case": try fm.moveItem(at: root.appendingPathComponent("Generated/MixerAndroid/bridge"), to: root.appendingPathComponent("Generated/MixerAndroid/Bridge"))
    case "asset-case": try fm.moveItem(at: root.appendingPathComponent("Generated/MixerAndroid/app/assets/MixerAppearanceV2"), to: root.appendingPathComponent("Generated/MixerAndroid/app/assets/mixerappearancev2"))
    case "asset-oversized": try Data(repeating: 32, count: 65_537).write(to: root.appendingPathComponent("Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json"))
    default:
        let asset = root.appendingPathComponent("Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json")
        try fm.removeItem(at: asset); try fm.createSymbolicLink(at: asset, withDestinationURL: base.appendingPathComponent("missing"))
    }
    // This unrelated whole-source symlink is a generic-hasher ordering sentinel:
    // a missing preflight would report files.symlink, never compatibility.
    try fm.createSymbolicLink(at: sdk.appendingPathComponent("hash-order-sentinel"), withDestinationURL: base.appendingPathComponent("missing"))
    allAdmissionEntrypoints(root)
    if !change.hasPrefix("adapter-") && !change.hasPrefix("asset-") {
        let target = base.appendingPathComponent("Created")
        expectCompatibilityFailure({ _ = try ProjectGenerator.create(name: "Created", application: "dev.example.created", destination: target, sdk: sdk, platform: "android", androidAdapter: compatibilityRepository.appendingPathComponent("native/android")) }, code: "create.android-sdk-compatibility")
        #expect(!FileManager.default.fileExists(atPath: target.path))
        #expect(try !FileManager.default.contentsOfDirectory(atPath: base.path).contains { $0.hasPrefix(".mixer-create-") })
    }
}

@Test(arguments: ["missing-file", "missing-lock", "legacy", "profile-1", "profile-2", "profile-3", "profile-4", "profile-5-current", "profile-5-prior", "broader-6-axis", "mixed-sdk", "mixed-adapter", "unknown", "digest", "default"])
func androidCompatibilityRequiredContextRejectsMissingLegacyOrMismatchedProfile(_ change: String) throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-profile-lock-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: root) }
    var lock = try compatibilityProject(root)
    switch change {
    case "missing-file", "missing-lock": lock.android = nil
    case "legacy": lock.android?.profile = nil
    case "profile-1": lock.android?.profile?.id = "mixer.android-source-pair.1"
    case "profile-2": lock.android?.profile?.id = "mixer.android-source-pair.2"
    case "profile-3": lock.android?.profile?.id = "mixer.android-source-pair.3"
    case "profile-4": lock.android?.profile?.id = "mixer.android-source-pair.4"
    case "profile-5-current":
        lock.android?.profile?.id = "mixer.android-source-pair.5"
        lock.android?.profile?.sdk_compatibility_sha256 = "bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0"
        lock.android?.profile?.adapter_compatibility_sha256 = "2b001980e07e0d1c8a5139e79de6ad6ca83d8db66d386bd4f77689ab32a6325a"
    case "profile-5-prior":
        lock.android?.profile?.id = "mixer.android-source-pair.5"
        lock.android?.profile?.sdk_compatibility_sha256 = "4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7"
        lock.android?.profile?.adapter_compatibility_sha256 = "9d47585c18c325888c6d87914808449f1a92e4a3839d02ce5c4ae8f15801c10c"
    case "broader-6-axis":
        // The same ID cannot authorize the unselected broader adapter24 source tuple.
        lock.android?.profile?.id = "mixer.android-source-pair.6"
        lock.android?.profile?.sdk_compatibility_sha256 = "bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0"
        lock.android?.profile?.adapter_compatibility_sha256 = "ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e"
        lock.android?.profile?.default_descriptor = AndroidSDKSourceIdentity(bytes: 9587, sha256: "1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3")
    case "mixed-sdk": lock.android?.profile?.sdk_compatibility_sha256 = "4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7"
    case "mixed-adapter": lock.android?.profile?.adapter_compatibility_sha256 = "2b001980e07e0d1c8a5139e79de6ad6ca83d8db66d386bd4f77689ab32a6325a"
    case "unknown": lock.android?.profile?.id = "unknown"
    case "digest": lock.android?.profile?.sdk_compatibility_sha256 = String(repeating: "0", count: 64)
    default: lock.android?.profile?.default_descriptor.bytes += 1
    }
    try JSONFile.write(lock, to: root.appendingPathComponent("mixer.lock"))
    if change == "missing-file" { try FileManager.default.removeItem(at: root.appendingPathComponent("mixer.lock")) }
    // Missing sources make missing-profile precedence executable.
    try FileManager.default.removeItem(at: root.appendingPathComponent("Generated"))
    allAdmissionEntrypoints(root, code: ["missing-file", "missing-lock", "legacy"].contains(change) ? "android.sdk-profile-required" : "android.sdk-profile-mismatch")
}

@Test func androidCompatibilityOrdinaryRelocationCommonLockAndCopiedExportPass() throws {
    let base = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-profile-relocation-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: base) }
    let root = base.appendingPathComponent("Original")
    var lock = try compatibilityProject(root)
    lock.swiftVersion = try ProcessRunner.run(["swift", "--version"]).output.trimmingCharacters(in: .whitespacesAndNewlines)
    try JSONFile.write(lock, to: root.appendingPathComponent("mixer.lock"))
    let moved = base.appendingPathComponent("Relocated"); try FileManager.default.moveItem(at: root, to: moved)
    #expect(try ProjectBuild.verifyLock(root: moved).android?.profile == AndroidSDKCompatibility.profile.lock)
    let exported = base.appendingPathComponent("Export")
    _ = try ProjectBuild.export(root: moved, destination: exported)
    #expect(try ProjectBuild.verifyLock(root: exported).android?.profile == AndroidSDKCompatibility.profile.lock)
    try AndroidSDKCompatibility.admitProject(exported)
    let canonicalSession = try Data(contentsOf: compatibilityRepository.appendingPathComponent("native/android/engine/Sources/MixerAndroidRuntime/DocumentSession.swift"))
    #expect(canonicalSession.count == 4328)
    #expect(SourceDigest.sha256(canonicalSession) == "cf1954af12e316bcd7cf8ea4def41d2dc6b26921fffa60177bce477c7f0749b7")
    for project in [moved, exported] {
        let copied = try Data(contentsOf: project.appendingPathComponent("Generated/MixerAndroid/Sources/MixerAndroidRuntime/DocumentSession.swift"))
        #expect(copied == canonicalSession)
    }
}

@Test func androidCompatibilityStagingFailureRemovesOwnedScratch() throws {
    let base = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-profile-cleanup-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: base) }
    let sdk = base.appendingPathComponent("SDK")
    try copyCompatibilitySDK(to: sdk)
    try AndroidSDKCompatibility.admitSDK(sdk)
    // Excluded from compatibility closure; existing whole-snapshot rule refuses.
    try FileManager.default.createSymbolicLink(at: sdk.appendingPathComponent("UnrelatedLink"), withDestinationURL: base.appendingPathComponent("missing"))
    let target = base.appendingPathComponent("Created")
    expectCompatibilityFailure({ _ = try ProjectGenerator.create(name: "Created", application: "dev.example.created", destination: target, sdk: sdk, platform: "android", androidAdapter: compatibilityRepository.appendingPathComponent("native/android")) }, code: "files.symlink")
    #expect(!FileManager.default.fileExists(atPath: target.path))
    #expect(try !FileManager.default.contentsOfDirectory(atPath: base.path).contains { $0.hasPrefix(".mixer-create-") })
}

@Test func androidCompatibilityAndroidLockAloneAndRequestedAndroidRequireAdmission() throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-profile-context-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: root) }
    var lock = try compatibilityProject(root)
    var config = try ApplicationConfiguration.load(root); config.targets = ["ios"]
    try JSONFile.write(config, to: root.appendingPathComponent("mixer.yml"))
    lock.android?.profile = nil
    try JSONFile.write(lock, to: root.appendingPathComponent("mixer.lock"))
    allAdmissionEntrypoints(root, code: "android.sdk-profile-required")
    lock.android = nil
    try JSONFile.write(lock, to: root.appendingPathComponent("mixer.lock"))
    expectCompatibilityFailure({ _ = try ProjectBuild.run(root: root, test: false, platform: "android") }, code: "android.sdk-profile-required")
    expectCompatibilityFailure({ _ = try AndroidProject.build(root: root) }, code: "android.sdk-profile-required")
}

@Test(arguments: ["extra", "missing", "wrong-type", "nested-extra"])
func androidCompatibilityMalformedProfileRecordFailsActionablyBeforeSourceReads(_ change: String) throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-profile-record-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: root) }
    _ = try compatibilityProject(root)
    var object = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: root.appendingPathComponent("mixer.lock"))) as? [String: Any])
    var android = try #require(object["android"] as? [String: Any])
    var profile = try #require(android["profile"] as? [String: Any])
    switch change {
    case "extra": profile["unknown"] = true
    case "missing": profile.removeValue(forKey: "id")
    case "wrong-type": profile["id"] = 1
    default: var identity = try #require(profile["default_descriptor"] as? [String: Any]); identity["unknown"] = true; profile["default_descriptor"] = identity
    }
    android["profile"] = profile; object["android"] = android
    try JSONSerialization.data(withJSONObject: object).write(to: root.appendingPathComponent("mixer.lock"))
    try FileManager.default.removeItem(at: root.appendingPathComponent("Generated"))
    allAdmissionEntrypoints(root, code: "android.sdk-profile-mismatch")
}

@Test(arguments: ["runtime-extra", "java-drift", "java-missing", "bridge-ancestor", "runtime-case", "java-case", "runtime-fifo"])
func androidCompatibilityInputAdapterAdmissionRefusesBeforeStagingAndSnapshotReads(_ change: String) throws {
    let base = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-profile-adapter-input-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: base) }
    let sdk = base.appendingPathComponent("SDK"), adapter = base.appendingPathComponent("Adapter")
    try copyCompatibilitySDK(to: sdk)
    let fm = FileManager.default
    for relative in AndroidSDKCompatibility.profile.adapter_files.keys {
        let source = relative.hasPrefix("Sources/") ? "engine/" + relative : relative
        let destination = adapter.appendingPathComponent(source)
        try fm.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
        try fm.copyItem(at: compatibilityRepository.appendingPathComponent("native/android/" + source), to: destination)
    }
    try AndroidSDKCompatibility.admitInput(sdk: sdk, adapter: adapter)
    let runtime = adapter.appendingPathComponent("engine/Sources/MixerAndroidRuntime")
    let java = adapter.appendingPathComponent("app/src/dev/mixer/android/Json.java")
    switch change {
    case "runtime-extra": try fm.createDirectory(at: runtime.appendingPathComponent(".build"), withIntermediateDirectories: true)
    case "java-drift": let bytes = try Data(contentsOf: java); try Data(repeating: 32, count: bytes.count).write(to: java)
    case "java-missing": try fm.removeItem(at: java)
    case "bridge-ancestor":
        let bridge = adapter.appendingPathComponent("bridge"), outside = base.appendingPathComponent("MovedBridge")
        try fm.moveItem(at: bridge, to: outside); try fm.createSymbolicLink(at: bridge, withDestinationURL: outside)
    case "runtime-case": try fm.moveItem(at: runtime, to: runtime.deletingLastPathComponent().appendingPathComponent("mixerandroidruntime"))
    case "java-case": try fm.moveItem(at: java, to: java.deletingLastPathComponent().appendingPathComponent("json.java"))
    default:
        let file = runtime.appendingPathComponent("DocumentSession.swift"); try fm.removeItem(at: file); #expect(mkfifo(file.path, 0o600) == 0)
    }
    let target = base.appendingPathComponent("Created")
    expectCompatibilityFailure({ _ = try ProjectGenerator.create(name: "Created", application: "dev.example.created", destination: target, sdk: sdk, platform: "android", androidAdapter: adapter) }, code: "create.android-sdk-compatibility")
    #expect(!fm.fileExists(atPath: target.path))
    let snapshot = base.appendingPathComponent("Snapshot")
    expectCompatibilityFailure({ _ = try AndroidProject.snapshot(adapter: adapter, destination: snapshot) })
    #expect(!fm.fileExists(atPath: snapshot.path))
    #expect(try !fm.contentsOfDirectory(atPath: base.path).contains { $0.hasPrefix(".mixer-create-") })
}

@Test(arguments: ["baseline", "same-size", "appended"])
func androidCompatibilityAxisSessionDriftRefusesRecomputedLocksBeforeGenericSourcesAndTools(_ change: String) throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-profile-axis-drift-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: root) }
    var lock = try compatibilityProject(root)
    let adapter = root.appendingPathComponent("Generated/MixerAndroid")
    let file = adapter.appendingPathComponent("Sources/MixerAndroidRuntime/DocumentSession.swift")
    let candidate = try Data(contentsOf: file)
    #expect(candidate.count == 4328)
    #expect(SourceDigest.sha256(candidate) == "cf1954af12e316bcd7cf8ea4def41d2dc6b26921fffa60177bce477c7f0749b7")
    let axisGuard = "            // Android's native packet decoder does not admit an explicit axis key.\n            if node.kind == .textField, node.properties[\"axis\"] != nil { throw AndroidDocumentError.unsupportedUI }\n"
    let baseline = Data(try #require(String(data: candidate, encoding: .utf8)).replacingOccurrences(of: axisGuard, with: "").utf8)
    #expect(baseline.count == 4128)
    #expect(SourceDigest.sha256(baseline) == "701b3d82add793a2b425bfc9673583afa8be4112406071242099da7da252bd0c")
    switch change {
    case "baseline": try baseline.write(to: file)
    case "same-size": try Data(repeating: 32, count: candidate.count).write(to: file)
    default: try (candidate + Data("\n// drift".utf8)).write(to: file)
    }
    lock.android?.adapterDigest = try SourceDigest.tree(adapter)
    try JSONFile.write(lock, to: root.appendingPathComponent("mixer.lock"))
    // If source admission is skipped, generic hashing reaches this sentinel.
    try FileManager.default.createSymbolicLink(at: root.appendingPathComponent("Generated/MixerSDK/hash-order-sentinel"), withDestinationURL: root.appendingPathComponent("missing"))
    allAdmissionEntrypoints(root)
}
