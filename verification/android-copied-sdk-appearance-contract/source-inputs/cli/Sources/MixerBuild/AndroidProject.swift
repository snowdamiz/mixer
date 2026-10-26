import Foundation
import MixerUI

public struct AndroidFileIdentity: Codable, Equatable, Sendable {
    public var path: String
    public var sha256: String
}
public struct AndroidToolchainIdentity: Codable, Equatable, Sendable {
    public var schema: Int
    public var sdk_id: String
    public var abi: String
    public var min_api: Int
    public var target_api: Int
    public var swift_version: String
    public var javac_version: String
    public var java_version: String
    public var python_version: String
    public var tools: [String: AndroidFileIdentity]
    public var metadata: [String: AndroidFileIdentity]
    public var distributions: [String: AndroidFileIdentity]
    public var sdk_search_path: String
}
public struct AndroidToolchainLock: Codable, Sendable {
    public var adapterDigest: String
    public var toolchain: AndroidToolchainIdentity
}

public enum AndroidProject {
    /// Export an explicit owned source closure. The checklist engine and its
    /// instrumentation never enter a created application's dependency graph.
    static func snapshot(adapter: URL, destination: URL) throws -> String {
        let adapter = adapter.resolvingSymlinksInPath().standardizedFileURL
        let expected = [
            "bridge/jni.c", "bridge/mixer_android.h", "bridge/mixer_android_v2.h", "contracts/android-profile-v1.json",
            "app/src/dev/mixer/android/Json.java", "app/src/dev/mixer/android/UiPacket.java",
            "app/src/dev/mixer/android/NativeRenderer.java", "app/src/dev/mixer/android/NativeBridge.java",
            "app/src/dev/mixer/android/MixerActivity.java",
            // Private coordinator source is available for compilation; the
            // public Activity continues to use the V1 exchange/bootstrap.
            "app/src/dev/mixer/android/NativeCoordinatorV2.java",
            // Compile dependencies of the internal renderer. Including them does
            // not opt generated applications into V2.
            "app/src/dev/mixer/android/AppearanceDescriptorV2.java",
            "app/src/dev/mixer/android/AppearanceGeometryV2.java",
            "app/src/dev/mixer/android/AppearanceResolverV2.java",
            "app/src/dev/mixer/android/AppearanceNativePathsV2.java",
            "app/src/dev/mixer/android/InstalledAppearanceV2.java",
            "app/src/dev/mixer/android/NativeEnvironmentV2.java",
            "app/src/dev/mixer/android/AuthoredToggleInputV2.java",
            "app/src/dev/mixer/android/NativeAppearanceViewsV2.java"
        ]
        let runtime = adapter.appendingPathComponent("engine/Sources/MixerAndroidRuntime")
        let runtimeFiles = try SourceDigest.files(in: runtime)
        guard !runtimeFiles.isEmpty, runtimeFiles.allSatisfy({ $0.pathExtension == "swift" }) else {
            throw MixerFailure("create.android-adapter", "Owned reusable Android runtime sources are missing or unsupported.")
        }
        var mapping = expected.map { ($0, $0) }
        mapping += runtimeFiles.map {
            let relative = String($0.path.dropFirst(runtime.path.count + 1))
            return ("engine/Sources/MixerAndroidRuntime/" + relative, "Sources/MixerAndroidRuntime/" + relative)
        }
        for (sourcePath, targetPath) in mapping {
            let source = adapter.appendingPathComponent(sourcePath)
            let info = try source.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])
            guard info.isRegularFile == true, info.isSymbolicLink != true else { throw MixerFailure("create.android-adapter", "Android adapter inputs must be regular source files: \(sourcePath)") }
            let target = destination.appendingPathComponent(targetPath)
            try FileManager.default.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
            try Data(contentsOf: source).write(to: target)
        }
        try runtimePackage.write(to: destination.appendingPathComponent("Package.swift"), atomically: true, encoding: .utf8)
        let driver = try buildDriver()
        try Data(contentsOf: driver).write(to: destination.appendingPathComponent("android-build.py"))
        let appearance = try defaultAppearanceData()
        let descriptor = destination.appendingPathComponent("app/assets/MixerAppearanceV2/descriptor.json")
        try FileManager.default.createDirectory(at: descriptor.deletingLastPathComponent(), withIntermediateDirectories: true)
        try appearance.write(to: descriptor)
        return try SourceDigest.tree(destination)
    }

    /// CLI-linked default data only. The separately selected SDK's default/API/ABI
    /// compatibility is pending; this does not enable the public V2 Activity.
    static func defaultAppearanceData() throws -> Data {
        let value = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
        let bytes = try UIAppearanceDescriptorCodecV2.canonicalData(value)
        let checked = try UIAppearanceDescriptorCodecV2.decode(bytes)
        guard checked == value, checked.resources.isEmpty,
              case let .shared(theme) = checked.mode,
              theme.typography.font == .systemSans else {
            throw MixerFailure("create.android-appearance", "The CLI default must be a canonical shared appearance with no resources and system sans typography.")
        }
        return bytes
    }

    static func buildDriver() throws -> URL {
        guard let resource = Bundle.module.url(forResource: "android-build", withExtension: "py", subdirectory: "Resources") else { throw MixerFailure("android.driver", "Installed CLI is missing its owned Android build driver.") }
        return resource
    }
    static func inspectToolchain() throws -> AndroidToolchainIdentity {
        let result = try ProcessRunner.run(["python3", try buildDriver().path, "inspect"])
        guard result.succeeded, !result.outputTruncated else { throw MixerFailure("android.toolchain", result.output) }
        do { return try JSONDecoder().decode(AndroidToolchainIdentity.self, from: Data(result.output.utf8)) }
        catch { throw MixerFailure("android.toolchain", "Android tool inventory was not a complete structured identity: \(error)") }
    }
    static func generate(root: URL) throws {
        let config = try ApplicationConfiguration.load(root)
        let directory = root.appendingPathComponent("Platforms/Android")
        let files = ["Package.swift": package(config.name), "AndroidManifest.xml": manifest(config),
                     "Sources/AppAndroid/NativeEntry.swift": entry,
                     "Tests/AppAndroidTests/SessionTests.swift": sessionTests,
                     "README.md": readme]
        for (path, source) in files {
            let target = directory.appendingPathComponent(path)
            guard !FileManager.default.fileExists(atPath: target.path) else { throw MixerFailure("generate.modified", "Refusing to overwrite Android app-owned file: \(target.path)") }
            try FileManager.default.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
            try source.write(to: target, atomically: true, encoding: .utf8)
        }
    }
    public static func build(root: URL) throws -> CommandResult {
        let lock = try ProjectBuild.verifyLock(root: root)
        guard lock.android != nil else { throw MixerFailure("android.not-generated", "This project has no locked Android host. Create a new project with --platform android; existing sources are never overwritten.") }
        let config = try ApplicationConfiguration.load(root)
        guard config.targets.contains("android"), config.capabilities.isEmpty else { throw MixerFailure("android.unsupported-capability", "Android local consumer requires an android target and no declared native capabilities; capability hosts are not integrated in this slice.") }
        guard try SourceDigest.files(in: root.appendingPathComponent("Resources")).isEmpty else { throw MixerFailure("android.unsupported-resources", "Android resource packaging is not integrated. App resources cannot be silently omitted.") }
        return try ProcessRunner.run(["python3", root.appendingPathComponent("Generated/MixerAndroid/android-build.py").path, "build", root.path], at: root)
    }

    private static let runtimePackage = """
    // swift-tools-version: 6.0
    import PackageDescription
    let package = Package(name: "MixerAndroid", platforms: [.macOS(.v14)],
        products: [.library(name: "MixerAndroidRuntime", targets: ["MixerAndroidRuntime"])],
        dependencies: [.package(path: "../MixerSDK")],
        targets: [.target(name: "MixerAndroidRuntime", dependencies: [
            .product(name: "MixerCore", package: "MixerSDK"), .product(name: "MixerUI", package: "MixerSDK")])],
        swiftLanguageModes: [.v6])
    """ + "\n"

    private static func package(_ name: String) -> String {
        """
        // swift-tools-version: 6.0
        import PackageDescription
        let package = Package(name: "\(name)Android", platforms: [.macOS(.v14)],
            products: [.library(name: "AppAndroid", type: .dynamic, targets: ["AppAndroid"])],
            dependencies: [.package(name: "Application", path: "../.."), .package(path: "../../Generated/MixerAndroid"), .package(path: "../../Generated/MixerSDK")],
            targets: [
                .target(name: "AppAndroid", dependencies: [.product(name: "AppFeatures", package: "Application"), .product(name: "MixerAndroidRuntime", package: "MixerAndroid")]),
                .testTarget(name: "AppAndroidTests", dependencies: ["AppAndroid", .product(name: "MixerUI", package: "MixerSDK")])
            ], swiftLanguageModes: [.v6])
        """ + "\n"
    }
    private static func manifest(_ config: ApplicationConfiguration) -> String {
        """
        <manifest xmlns:android="http://schemas.android.com/apk/res/android" package="\(config.application)" android:versionCode="1" android:versionName="0.1.0">
          <uses-sdk android:minSdkVersion="28" android:targetSdkVersion="37" />
          <application android:theme="@android:style/Theme.Material.Light.NoActionBar" android:label="\(config.name)" android:debuggable="true" android:allowBackup="false" android:extractNativeLibs="true" android:supportsRtl="true">
            <activity android:name="dev.mixer.android.MixerActivity" android:exported="true" android:windowSoftInputMode="adjustResize">
              <intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter>
            </activity>
          </application>
        </manifest>
        """ + "\n"
    }
    private static let entry = """
    import AppFeatures
    @_spi(MixerNativeAppearanceV2) import MixerAndroidRuntime
    // App-owned native entry point; state, document and reducer live in shared Swift.
    // State must remain a value type; callbacks are synchronous, non-reentrant and
    // free of I/O/async/shared mutable references. Sendable alone is insufficient.
    private let sessions = AndroidSessionRegistry {
        try AndroidDocumentSession(state: ProjectFeatureState(),
            document: { ProjectFeature.document(state: $0, revision: $1) },
            reduce: { try ProjectFeature.handle($1, state: &$0) })
    }
    @_cdecl("mixer_android_create")
    public func mixerAndroidCreate() -> UInt64 { sessions.create() }
    @_cdecl("mixer_android_destroy")
    public func mixerAndroidDestroy(_ handle: UInt64) -> Int32 { sessions.destroy(handle) }
    @_cdecl("mixer_android_exchange")
    public func mixerAndroidExchange(_ handle: UInt64, _ operation: UInt32,
        _ input: UnsafePointer<UInt8>?, _ inputLength: Int,
        _ output: UnsafeMutablePointer<UInt8>?, _ capacity: Int, _ written: UnsafeMutablePointer<Int>?
    ) -> Int32 { sessions.exchange(handle, operation, input, inputLength, output, capacity, written) }
    // Private ordinary-native staging. This does not opt the Activity into V2.
    @_spi(MixerNativeAppearanceV2)
    @_cdecl("mixer_android_prepare_v2")
    public func mixerAndroidPrepareV2(_ handle: UInt64, _ operation: UInt32,
        _ input: UnsafePointer<UInt8>?, _ inputLength: Int,
        _ output: UnsafeMutablePointer<UInt8>?, _ capacity: Int,
        _ written: UnsafeMutablePointer<Int>?, _ token: UnsafeMutablePointer<UInt64>?
    ) -> Int32 { sessions.prepareV2(handle, operation, input, inputLength, output, capacity, written, token) }
    @_spi(MixerNativeAppearanceV2)
    @_cdecl("mixer_android_commit_v2")
    public func mixerAndroidCommitV2(_ handle: UInt64, _ token: UInt64) -> Int32 { sessions.commitV2(handle, token) }
    @_spi(MixerNativeAppearanceV2)
    @_cdecl("mixer_android_abort_v2")
    public func mixerAndroidAbortV2(_ handle: UInt64, _ token: UInt64) -> Int32 { sessions.abortV2(handle, token) }
    """ + "\n"
    private static let readme = """
    # Android local development host

    `mixer build --platform android` compiles the original shared AppModels/AppFeatures
    package, app-owned Sources/AppAndroid entry, and locked owned runtime/Java/JNI.
    Output is `.mixer/android-build/*-unsigned.apk`, with a complete build receipt.
    The APK is unsigned and has not been installed or qualified on a device.
    `swift test --package-path Platforms/Android` exercises this exact app's exported
    session ABI on the host. Mac tests do not establish Android UI behavior.

    This host uses Android native widgets with the unchanged android-profile-v1
    subset. Shared ProjectFeatureState owns draft/add/toggle; the iOS starter uses
    the compatible read-only document(entries:) surface. State is process-local.
    There is no persistence, process restoration, navigation/back/sheets, native
    capabilities, lifecycle/effects, resource copying, production signing, store,
    accessibility or performance qualification. Unsupported UI/events fail closed.
    The generated JNI closure includes private staged prepare/commit/abort exports;
    the Activity still uses legacy exchange and does not opt into V2 rendering.
    Runtime state must preserve value semantics without shared mutable references.
    Callbacks run synchronously under a non-reentrant lock; they must not perform
    I/O, asynchronous work or external side effects. Sendable alone cannot ensure
    rollback for arbitrary reference state or effects.
    App-owned manifest/package/entry/Java files are compiled as edited; builds never
    regenerate them. Put optional Android Java extensions under Java/. Bundled
    Generated/MixerAndroid and Generated/MixerSDK inputs are immutable source locks.

    Supported installed tools: official Swift6.3.3 Android SDK arm64/API28, NDKr27d,
    Android platform37.0/build-tools37.0.0, JDK25 (Java bytecode17), Python3. Tool
    paths and complete distribution hashes are locked during creation. Configure
    MIXER_SWIFT, MIXER_SWIFT_SDKS_PATH, MIXER_ANDROID_ARTIFACT_PATH, MIXER_JDK and
    ANDROID_HOME before creation; builds require those exact distributions.
    No tools are downloaded. Published immutable SDK consumption is still pending.
    """ + "\n"
    private static let sessionTests = """
    import Foundation
    import Testing
    import MixerUI
    @_spi(MixerNativeAppearanceV2) @testable import AppAndroid
    @Suite(.serialized) struct ApplicationSessionTests {
        func exchange(_ handle: UInt64, _ input: Data? = nil, capacity: Int = 1_048_576) -> (Int32, Data) {
            var buffer = [UInt8](repeating: 0, count: capacity), written = 0
            let status = buffer.withUnsafeMutableBufferPointer { output in
                if let input { return input.withUnsafeBytes { bytes in
                    mixerAndroidExchange(handle, 1, bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count, output.baseAddress, capacity, &written)
                } }
                return mixerAndroidExchange(handle, 0, nil, 0, output.baseAddress, capacity, &written)
            }
            return (status, Data(buffer.prefix(min(written, capacity))))
        }
        func event(_ packet: Data, id: String, kind: UIEventKind, value: UIValue) throws -> Data {
            let object = try #require(JSONSerialization.jsonObject(with: packet) as? [String: Any])
            let document = try UIDocument.decode(JSONSerialization.data(withJSONObject: object["document"]!))
            let identities = try JSONDecoder().decode([UINodeIdentity].self, from: JSONSerialization.data(withJSONObject: object["identities"]!))
            return try JSONEncoder().encode(UIEventEnvelope(revision: document.revision,
                identity: #require(identities.first { $0.id == id }), event: kind, value: value))
        }
        @Test func sharedDraftAddToggleAndRejectedTransactions() throws {
            let handle = mixerAndroidCreate(); #expect(handle != 0)
            defer { #expect(mixerAndroidDestroy(handle) == 0) }
            let initial = exchange(handle); #expect(initial.0 == 0)
            let edit = try event(initial.1, id: "draft", kind: .textChange, value: .string("Café 東京 🧪"))
            #expect(exchange(handle, edit, capacity: 1).0 == 3)
            #expect(exchange(handle).1 == initial.1)
            let draft = exchange(handle, edit); #expect(draft.0 == 0)
            #expect(exchange(handle, edit).0 == 4)
            let added = exchange(handle, try event(draft.1, id: "add", kind: .activate, value: .null))
            #expect(added.0 == 0)
            let object = try #require(JSONSerialization.jsonObject(with: added.1) as? [String: Any])
            let identities = try JSONDecoder().decode([UINodeIdentity].self, from: JSONSerialization.data(withJSONObject: object["identities"]!))
            let task = try #require(identities.first { $0.id.hasPrefix("entry.") })
            let toggled = exchange(handle, try event(added.1, id: task.id, kind: .valueChange, value: .bool(true)))
            #expect(toggled.0 == 0)
            #expect(String(decoding: toggled.1, as: UTF8.self).contains("1 of 1 completed"))
            for bad in [Data("{}".utf8), Data("{\\"event\\":null,\\"\\\\u0065vent\\":null}".utf8), Data(repeating: 32, count: 131_073)] {
                #expect(exchange(handle, bad).0 != 0)
                #expect(exchange(handle).1 == toggled.1)
            }
        }
        @Test func stagedDecisionsPreserveCommittedState() throws {
            let handle = mixerAndroidCreate(); #expect(handle != 0)
            defer { #expect(mixerAndroidDestroy(handle) == 0) }
            let initial = exchange(handle); #expect(initial.0 == 0)
            let edit = try event(initial.1, id: "draft", kind: .textChange, value: .string("Staged café 東京"))
            func prepare() -> (Int32, Data, UInt64) {
                var buffer = [UInt8](repeating: 0, count: 1_048_576), written = 0
                var token: UInt64 = 0
                let status = buffer.withUnsafeMutableBufferPointer { output in
                    edit.withUnsafeBytes { input in
                        mixerAndroidPrepareV2(handle, 1, input.bindMemory(to: UInt8.self).baseAddress,
                            input.count, output.baseAddress, output.count, &written, &token)
                    }
                }
                return (status, Data(buffer.prefix(min(written, buffer.count))), token)
            }
            let aborted = prepare(); #expect(aborted.0 == 0); #expect(aborted.2 != 0)
            #expect(exchange(handle).0 == 5)
            #expect(mixerAndroidAbortV2(handle, aborted.2) == 0)
            #expect(mixerAndroidAbortV2(handle, aborted.2) == 0)
            #expect(exchange(handle).1 == initial.1)
            let committed = prepare(); #expect(committed.0 == 0); #expect(committed.2 != aborted.2)
            #expect(mixerAndroidAbortV2(handle, aborted.2) == 0)
            #expect(exchange(handle).0 == 5)
            #expect(mixerAndroidCommitV2(handle, committed.2) == 0)
            #expect(mixerAndroidCommitV2(handle, committed.2) == 6)
            #expect(exchange(handle).1 == committed.1)
            #expect(String(decoding: committed.1, as: UTF8.self).contains("Staged café 東京"))
        }
        @Test func boundedHandlesAndDestruction() {
            let handles = (0..<16).map { _ in mixerAndroidCreate() }
            #expect(handles.allSatisfy { $0 != 0 }); #expect(Set(handles).count == 16)
            #expect(mixerAndroidCreate() == 0)
            for handle in handles { #expect(mixerAndroidDestroy(handle) == 0); #expect(mixerAndroidDestroy(handle) == 2) }
            #expect(exchange(handles[0]).0 == 2)
        }
    }
    """ + "\n"
}
