import Darwin
import Foundation

/// The generated application owns its Activity and Swift feature source. The
/// maintained Android renderer and Gradle locks come from the admitted adapter.
enum AndroidComposeProject {
    private static let relativeModule = "Platforms/Android/Compose"
    static let activityName = "MixerComposeActivity"
    static let assets = ["bundled-document.json", "bundled-generations.bin"]
    private static let failure = MixerFailure("android.compose-source", "The Compose module requires the exact maintained adapter projection and a bundled read-only Swift feature.")

    private static let renderer: [String: AndroidSDKSourceIdentity] = [
        "THIRD_PARTY.yml": .init(bytes: 8125, sha256: "f51ab3b648352ab131346ef1a1c97f853d2ee7468478366fe6fb38131e442f16"),
        "buildscript-gradle.lockfile": .init(bytes: 6186, sha256: "4d663ae9e7ce133108ca8ffc2ec1178c10d2be7a80e4c3099168c011b393dd2f"),
        "gradle.lockfile": .init(bytes: 65721, sha256: "4f46bf7af1a3f8037567d22f9d9dfe56fa4573d651f70c7b0a5222931590c1b6"),
        "gradle.properties": .init(bytes: 123, sha256: "1cc4fdd32abaeb91447af9582d0394f561b3b39b097975237053defa282f93bc"),
        "gradle/verification-metadata.xml": .init(bytes: 198651, sha256: "e3127e333b1599485438e66dc20120f148846fbac8f84d75870a51a3ef91551c"),
        "settings.gradle": .init(bytes: 315, sha256: "5c708b616ce188a6aee19382a02e9554e4f5f0080a7464216637d33e56fdb5cb"),
        "src/main/kotlin/dev/mixer/compose/BufferMarker.kt": .init(bytes: 1454, sha256: "26289b74cf0ec1d3226deab04730266cc02c855db17404635b38fc8b903bd234"),
        "src/main/kotlin/dev/mixer/compose/ComposeDocumentHost.kt": .init(bytes: 15131, sha256: "4e6ae9265f8c2c1dc0de4e58e8cfce84c968f1fa9942875e6269abf5ae36b200"),
        "src/main/kotlin/dev/mixer/compose/Document.kt": .init(bytes: 828, sha256: "3d1168ea457230feec79efab0ad5c25d7d1c1caf6bdb4a04b40b168bf614600e"),
        "src/main/kotlin/dev/mixer/compose/DocumentReader.kt": .init(bytes: 11204, sha256: "30126d7e241654717d7979615b1518973684f3ccec7adee020594522c2678eea"),
        "src/main/kotlin/dev/mixer/compose/DocumentSurface.kt": .init(bytes: 14843, sha256: "968cd31f450937513d34dedb25925d8bdf49b97fd39b6705d95ea42964facf8e"),
        "src/main/kotlin/dev/mixer/compose/FrameAuthority.kt": .init(bytes: 8322, sha256: "1dec7f903a76502e29e97495f8541f2bb8499555de3621e3a9257e2197365d43"),
        "src/main/kotlin/dev/mixer/compose/SharedTheme.kt": .init(bytes: 3513, sha256: "07fe53ca821056cdbcd5b5268cce30c66ec7196cfe452147ff286483a398f3dc"),
        "toolchain.json": .init(bytes: 490, sha256: "90e4bf13c6a4d2de64f2d82cac3d7d12f61ea4918a764742073dda0369565136"),
    ]

    static func installRenderer(root: URL, adapter: URL, upgrading: Bool = false) throws {
        let source = adapter.resolvingSymlinksInPath().standardizedFileURL.appendingPathComponent("compose")
        let target = root.appendingPathComponent(relativeModule)
        for path in renderer.keys.sorted() {
            let bytes = try readPinned(path, in: source)
            let destination = target.appendingPathComponent(path)
            if upgrading {
                // Preserve app sources and require the maintained paths to match
                // the admitted projection before publishing the upgraded copy.
                guard try readPinned(path, in: target) == bytes else { throw failure }
            } else {
                try FileManager.default.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
                try bytes.write(to: destination, options: .withoutOverwriting)
            }
        }
    }

    static func verifyAdapter(root: URL) throws {
        try verifyRenderer(root.appendingPathComponent(relativeModule))
    }

    static func verifyRenderer(_ module: URL) throws {
        for path in renderer.keys.sorted() { _ = try readPinned(path, in: module) }
    }

    private static func readPinned(_ relative: String, in root: URL) throws -> Data {
        let url = root.appendingPathComponent(relative)
        guard url.resolvingSymlinksInPath().path == url.path, let row = renderer[relative] else { throw failure }
        let fd = open(url.path, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
        guard fd >= 0 else { throw failure }
        defer { close(fd) }
        let data = try NativeProductCapture.regular(fd, maximum: row.bytes)
        guard data.count == row.bytes, SourceDigest.sha256(data) == row.sha256 else { throw failure }
        return data
    }

    static func generate(root: URL, adapter: URL, config: ApplicationConfiguration) throws {
        try installRenderer(root: root, adapter: adapter)
        let module = root.appendingPathComponent(relativeModule)
        let application = config.applicationIdentifier(for: "android")
        let namespace = application + ".androidhost"
        let kotlinPackage = namespace.split(separator: ".").map { "`" + $0 + "`" }.joined(separator: ".")
        let activityPath = namespace.replacingOccurrences(of: ".", with: "/") + "/" + activityName + ".kt"
        let selection = AndroidProject.StagedComposeProject.Selection(schema: 1, host: .publicComposeV1,
            application: application, minAPI: AndroidPublicHost.RetainedSelection.publicComposeV1.minimumAPI, targetAPI: 37)
        let resources = Bundle.module.resourceURL!.appendingPathComponent("Resources/AndroidComposeStarter")
        let files: [String: Data] = [
            "mixer-compose.json": try JSONFile.data(selection),
            "build.gradle": try Data(contentsOf: resources.appendingPathComponent("build.gradle")),
            "swift/BundledFrame.swift": try Data(contentsOf: resources.appendingPathComponent("BundledFrame.swift")),
            "src/main/kotlin/" + activityPath: Data(try String(contentsOf: resources.appendingPathComponent(activityName + ".kt"),
                encoding: .utf8).replacingOccurrences(of: "__PACKAGE__", with: kotlinPackage).utf8),
            "src/main/AndroidManifest.xml": Data("""
            <manifest xmlns:android="http://schemas.android.com/apk/res/android">
              <application android:label="\(config.name)" android:allowBackup="false"
                  android:theme="@android:style/Theme.Material.Light.NoActionBar">
                <activity android:name="\(namespace).\(activityName)" android:exported="true">
                  <intent-filter>
                    <action android:name="android.intent.action.MAIN"/>
                    <category android:name="android.intent.category.LAUNCHER"/>
                  </intent-filter>
                </activity>
              </application>
            </manifest>

            """.utf8),
        ]
        for (relative, data) in files {
            let file = module.appendingPathComponent(relative)
            try FileManager.default.createDirectory(at: file.deletingLastPathComponent(), withIntermediateDirectories: true)
            try data.write(to: file, options: .withoutOverwriting)
        }
    }

    struct BundledFrame: Codable, Sendable {
        let sourceSHA256: String
        let compilerSHA256: String
        let compilerVersion: String
        let sdkSettingsSHA256: String
        let commands: [[String]]
        let assets: [String: String]
    }

    /// Capture only the SDK and application modules that author the bundled
    /// frame. The host build uses static modules and needs no SwiftPM downloads.
    static func bundle(root: URL, project: URL, snapshot: ProcessInputSnapshot,
                       context: ProcessExecutionContext) throws -> BundledFrame {
        let fm = FileManager.default
        let source = snapshot.directory.appendingPathComponent("bundled-sources")
        let work = snapshot.directory.appendingPathComponent("bundle-work")
        let output = project.appendingPathComponent("src/main/assets/mixer")
        for directory in [source, work] {
            try fm.createDirectory(at: directory, withIntermediateDirectories: false)
        }
        guard !fm.fileExists(atPath: output.path) else { throw failure }
        let modules = [
            ("MixerCore", "Generated/MixerSDK/Sources/MixerCore"),
            ("MixerUI", "Generated/MixerSDK/Sources/MixerUI"),
            ("MixerAndroid", "Generated/MixerSDK/Sources/MixerAndroid"),
            ("AppModels", "Sources/AppModels"),
            ("AppFeatures", "Sources/AppFeatures"),
        ]
        var sources: [String: [String]] = [:]
        for (module, relative) in modules {
            let directory = root.appendingPathComponent(relative)
            guard directory.resolvingSymlinksInPath().path == directory.path else { throw failure }
            let sourceIdentity = try SourceDigest.exportFingerprint(directory)
            let entries = try SourceDigest.exportEntries(in: directory)
            let files = entries.filter { !$0.directory }
            guard !files.isEmpty, files.allSatisfy({ $0.relative.hasSuffix(".swift") }) else { throw failure }
            let target = source.appendingPathComponent(module)
            try fm.createDirectory(at: target, withIntermediateDirectories: false)
            try ProjectBuild.copyExportEntries(entries, from: directory, to: target)
            guard try SourceDigest.exportFingerprint(target) == sourceIdentity,
                  try SourceDigest.exportFingerprint(directory) == sourceIdentity else { throw failure }
            sources[module] = files.map { target.appendingPathComponent($0.relative).path }.sorted()
        }
        let entry = source.appendingPathComponent("BundledFrame.swift")
        try fm.copyItem(at: project.appendingPathComponent("swift/BundledFrame.swift"), to: entry)
        let sourceSHA = try SourceDigest.exportFingerprint(source)

        let inherited = ProcessInfo.processInfo.environment
        var environment = inherited.filter { ["DEVELOPER_DIR", "TOOLCHAINS"].contains($0.key) }
        environment["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
        environment["TMPDIR"] = work.path
        environment["CLANG_MODULE_CACHE_PATH"] = work.appendingPathComponent("module-cache").path
        var commands: [[String]] = []
        func run(_ command: [String]) throws -> String {
            let result = try ProcessRunner.run(command, at: work, environment: environment, policy: .developmentBuild,
                                               context: context, retaining: snapshot.retainedInputDirectories)
            guard result.succeeded, !result.outputTruncated else {
                throw MixerFailure("android.compose-swift", "Bundled Swift build exited \(result.exitCode).\n\(result.output.suffix(8192))")
            }
            commands.append(result.command)
            return result.output.trimmingCharacters(in: .whitespacesAndNewlines)
        }
        let swiftc = try run(["/usr/bin/xcrun", "--sdk", "macosx", "--find", "swiftc"])
        let sdk = try run(["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path"])
        guard swiftc.hasPrefix("/"), sdk.hasPrefix("/") else { throw failure }
        let compiler = URL(fileURLWithPath: swiftc).resolvingSymlinksInPath()
        let sdkSettings = URL(fileURLWithPath: sdk).appendingPathComponent("SDKSettings.json")
        let compilerSHA = try SourceDigest.sha256(Data(contentsOf: compiler, options: .mappedIfSafe))
        let settingsSHA = try SourceDigest.sha256(Data(contentsOf: sdkSettings))
        let version = try run([swiftc, "--version"])
        let common = [swiftc, "-sdk", sdk, "-swift-version", "6", "-package-name", "Mixer",
                      "-I", work.path, "-module-cache-path", environment["CLANG_MODULE_CACHE_PATH"]!]
        for (module, _) in modules {
            _ = try run(common + ["-parse-as-library", "-emit-module", "-emit-module-path", work.appendingPathComponent(module + ".swiftmodule").path,
                         "-emit-library", "-static", "-module-name", module, "-o", work.appendingPathComponent("lib" + module + ".a").path]
                         + sources[module]!)
        }
        let producer = work.appendingPathComponent("bundled-frame")
        _ = try run(common + ["-parse-as-library", entry.path, "-L", work.path, "-o", producer.path]
                    + modules.reversed().map { "-l" + $0.0 })
        try fm.createDirectory(at: output, withIntermediateDirectories: true)
        _ = try run([producer.path, output.path])
        guard try SourceDigest.exportFingerprint(source) == sourceSHA,
              URL(fileURLWithPath: swiftc).resolvingSymlinksInPath() == compiler,
              try SourceDigest.sha256(Data(contentsOf: compiler, options: .mappedIfSafe)) == compilerSHA,
              try SourceDigest.sha256(Data(contentsOf: sdkSettings)) == settingsSHA else { throw failure }
        return BundledFrame(sourceSHA256: sourceSHA, compilerSHA256: compilerSHA, compilerVersion: version,
            sdkSettingsSHA256: settingsSHA, commands: commands,
            assets: try Dictionary(uniqueKeysWithValues: assets.map {
                ($0, try SourceDigest.sha256(Data(contentsOf: output.appendingPathComponent($0))))
            }))
    }
}
