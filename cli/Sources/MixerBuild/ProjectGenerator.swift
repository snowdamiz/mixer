import Darwin
import Foundation

public struct GeneratedProject: Codable, Sendable {
    public var path: String
    public var application: String
    public var sdkDigest: String
    public var qualification = "local-development-only"
    public var nextSteps: [String]
}

private struct SwiftVersionIdentity {
    private static let driverPrefix = "swift-driver version: "
    let compiler: Substring
    let target: Substring
    let driver: Substring?

    var banner: String {
        if let driver { return "\(compiler)\n\(target)\n\(driver)" }
        return "\(compiler)\n\(target)"
    }

    func matches(lockBanner: String) -> Bool {
        if lockBanner.utf8.elementsEqual(banner.utf8) { return true }
        guard let driver else { return false }
        // Schema 1 could record the driver before or between the stdout
        // lines, including inline when stderr ended with a space.
        return lockBanner.utf8.elementsEqual("\(driver) \(compiler)\n\(target)".utf8)
            || lockBanner.utf8.elementsEqual("\(driver)\n\(compiler)\n\(target)".utf8)
            || lockBanner.utf8.elementsEqual("\(compiler)\n\(driver) \(target)".utf8)
            || lockBanner.utf8.elementsEqual("\(compiler)\n\(driver)\n\(target)".utf8)
    }

    private init?(banner: String) {
        var lines = banner.split(separator: "\n", omittingEmptySubsequences: false)
        var driverLine: Substring?
        if let first = lines.first, first.hasPrefix(Self.driverPrefix) {
            if lines.count == 2, let separator = first.dropFirst(Self.driverPrefix.count).firstIndex(of: " ") {
                driverLine = first[..<separator]
                lines[0] = first[first.index(after: separator)...]
            } else {
                driverLine = lines.removeFirst()
            }
        } else if lines.count == 3 {
            driverLine = lines.removeLast()
        }
        guard lines.count == 2,
              ["Apple Swift version ", "Swift version "].contains(where: {
                  lines[0].hasPrefix($0) && lines[0].count > $0.count
              }),
              lines[1].hasPrefix("Target: "), lines[1].count > "Target: ".count,
              !lines[1].dropFirst("Target: ".count).contains(where: \.isWhitespace) else { return nil }
        if let driverLine {
            let value = driverLine.dropFirst(Self.driverPrefix.count)
            guard driverLine.hasPrefix(Self.driverPrefix), !value.isEmpty,
                  !value.contains(where: \.isWhitespace) else { return nil }
        }
        compiler = lines[0]
        target = lines[1]
        driver = driverLine
    }

    static func inspect(swiftExecutable: String = "swift") throws -> (CommandResult, Self?) {
        var stdout = Data(), stderr = Data()
        let result = try ProcessRunner.run([swiftExecutable, "--version"], policy: .toolInspection, captureOutput: { stream, bytes in
            switch stream {
            case .stdout: stdout.append(bytes)
            case .stderr: stderr.append(bytes)
            }
        })
        guard result.succeeded, !result.outputTruncated,
              let standard = String(data: stdout, encoding: .utf8),
              let error = String(data: stderr, encoding: .utf8) else { return (result, nil) }
        // Drain order is useful for diagnostics only. Finish each stream
        // before assembling the version records, including unterminated stderr.
        let banner = [standard, error].map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }.joined(separator: "\n")
        return (result, Self(banner: banner))
    }
}

public enum ProjectGenerator {
    public static func create(name: String, application: String, destination: URL, sdk: URL, platform: String = "ios", androidAdapter: URL? = nil, androidHost: AndroidApplicationHost? = nil) throws -> GeneratedProject {
        guard ["ios", "android"].contains(platform) else { throw MixerFailure("create.platform", "Create supports ios (default) or android (both native hosts).") }
        var config = ApplicationConfiguration(name: name, application: application)
        config.androidHost = androidHost == .legacyV1 ? nil : androidHost
        config.targets = platform == "android" ? ["ios", "android"] : ["ios"]
        // The starter requests no native capabilities. Adding one requires an
        // implemented native host and a new binary, never a successful stub.
        config.capabilities = []
        try config.validate()
        let fm = FileManager.default
        guard !fm.fileExists(atPath: destination.path) else { throw MixerFailure("create.exists", "Refusing to overwrite \(destination.path). Choose a new directory.") }
        guard platform == "android" || fm.fileExists(atPath: sdk.appendingPathComponent("Package.swift").path) else { throw MixerFailure("create.sdk", "SDK package not found at \(sdk.path). Supply --sdk-path to an installed Mixer SDK source distribution.") }
        try AndroidSDKCompatibility.requireHost(config.androidHost)
        let sdk = sdk.resolvingSymlinksInPath().standardizedFileURL
        if platform == "android" {
            guard let androidAdapter else { throw MixerFailure("create.android-adapter", "Supply the owned Mixer Android adapter source distribution.") }
            do { try AndroidSDKCompatibility.admitInput(sdk: sdk, adapter: androidAdapter.resolvingSymlinksInPath().standardizedFileURL) }
            catch { throw MixerFailure("create.android-sdk-compatibility", String(describing: error)) }
        }
        let parent = destination.deletingLastPathComponent()
        try fm.createDirectory(at: parent, withIntermediateDirectories: true)
        let staging = parent.appendingPathComponent(".mixer-create-\(UUID().uuidString)")
        try fm.createDirectory(at: staging, withIntermediateDirectories: true)
        defer { try? fm.removeItem(at: staging) }
        for path in ["Sources/AppModels", "Sources/AppFeatures", "Sources/NativeServices", "Tests/AppModelsTests", "Platforms/iOS", "Platforms/Android", "Resources", "Generated/MixerSDK"] {
            try fm.createDirectory(at: staging.appendingPathComponent(path), withIntermediateDirectories: true)
        }
        let digest = try snapshotSDK(from: sdk, into: staging)
        if platform == "android" { try AndroidSDKCompatibility.admitSDK(staging.appendingPathComponent("Generated/MixerSDK")) }
        var adapterDigest: String?
        if platform == "android", let androidAdapter {
            adapterDigest = try AndroidProject.snapshot(adapter: androidAdapter, destination: staging.appendingPathComponent("Generated/MixerAndroid"))
            try AndroidSDKCompatibility.admitProject(staging)
        }
        let (version, identity) = try SwiftVersionIdentity.inspect()
        guard version.succeeded else { throw MixerFailure("create.swift", version.output) }
        guard let identity else { throw MixerFailure("create.swift", "Could not read a complete Swift version banner. \(version.output)") }
        try JSONFile.write(config, to: staging.appendingPathComponent("mixer.yml"))
        var lock = ToolchainLock(sdkDigest: digest, swiftVersion: identity.banner)
        if let adapterDigest {
            lock.android = AndroidToolchainLock(adapterDigest: adapterDigest, toolchain: try AndroidProject.inspectToolchain(), profile: AndroidSDKCompatibility.profile.lock)
        }
        try JSONFile.write(lock, to: staging.appendingPathComponent("mixer.lock"))
        let files = [
            "Package.swift": package(name),
            "Sources/AppModels/Entry.swift": models,
            "Sources/AppFeatures/ProjectFeature.swift": features,
            "Sources/NativeServices/README.md": "Native integrations live here. A new native capability requires a new store binary.\n",
            "Tests/AppModelsTests/EntryTests.swift": modelTests,
            "Platforms/iOS/\(name)App.swift": appleApp(name),
            "README.md": readme(name),
            ".gitignore": ".build/\n.swiftpm/\n.mixer/\n.DS_Store\n"
        ]
        for (path, contents) in files { try contents.write(to: staging.appendingPathComponent(path), atomically: true, encoding: .utf8) }
        _ = try AppleProject.generate(root: staging)
        if platform == "android" {
            try AndroidProject.generate(root: staging)
            try AndroidProject.seedDependencyLock(root: staging)
        } else { try "No Android host was requested. Create a new project with --platform android for the unsigned local development host.\n".write(to: staging.appendingPathComponent("Platforms/Android/README.md"), atomically: true, encoding: .utf8) }
        // An entire project becomes visible only when construction succeeds.
        try fm.moveItem(at: staging, to: destination)
        return GeneratedProject(path: destination.path, application: application, sdkDigest: digest, nextSteps: ["cd \(destination.path)", "mixer test", "mixer doctor"])
    }

    static func snapshotSDK(from source: URL, into root: URL, requireIOS: Bool = false) throws -> String {
        let source = source.resolvingSymlinksInPath().standardizedFileURL
        let target = root.appendingPathComponent("Generated/MixerSDK")
        let fm = FileManager.default
        let entries = try SourceDigest.exportEntries(in: source)
        guard entries.contains(where: { $0.relative == "Package.swift" && !$0.directory }) else {
            throw MixerFailure("snapshot.sdk", "Supply an SDK directory with a regular Package.swift from your pinned Mixer checkout.")
        }
        try fm.createDirectory(at: target, withIntermediateDirectories: true)
        try ProjectBuild.copyExportEntries(entries, from: source, to: target)
        if requireIOS {
            let files = try SourceDigest.exportEntries(in: target).filter { !$0.directory }
            for module in ["MixerCore", "MixerUI", "MixerApple", "MixerGuest", "MixerCapabilities", "MixerAndroid"] {
                guard files.contains(where: { $0.relative.hasPrefix("Sources/\(module)/") && $0.relative.hasSuffix(".swift") }) else {
                    throw MixerFailure("snapshot.sdk", "The copied SDK is missing Swift sources for \(module). Supply the complete SDK from your pinned Mixer checkout.")
                }
            }
        }
        return try SourceDigest.tree(target)
    }

    private static func package(_ name: String) -> String {
        """
        // swift-tools-version: 6.0
        import PackageDescription
        let package = Package(
            name: "\(name)", platforms: [.iOS("26.0"), .macOS(.v14)],
            products: [.library(name: "AppFeatures", targets: ["AppFeatures"])],
            dependencies: [.package(path: "Generated/MixerSDK")],
            targets: [
                .target(name: "AppModels"),
                .target(name: "AppFeatures", dependencies: ["AppModels", .product(name: "MixerUI", package: "MixerSDK")]),
                .testTarget(name: "AppModelsTests", dependencies: ["AppModels", "AppFeatures"])
            ]
        )
        """ + "\n"
    }

    private static let models = """
    import Foundation
    public struct Entry: Codable, Equatable, Identifiable, Sendable {
        public let id: UUID
        public var title: String
        public var note: String
        public var completed: Bool
        public init(id: UUID = UUID(), title: String, note: String = "", completed: Bool = false) {
            self.id = id; self.title = title; self.note = note; self.completed = completed
        }
        public var isValid: Bool { !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    }
    public enum ProjectProgress {
        public static func fraction(_ entries: [Entry]) -> Double {
            entries.isEmpty ? 0 : Double(entries.filter(\\.completed).count) / Double(entries.count)
        }
    }
    """ + "\n"

    private static let features = """
    import Foundation
    import AppModels
    import MixerUI
    public struct ProjectFeatureState: Equatable, Sendable {
        public var entries: [Entry]
        public var draft: String
        public init(entries: [Entry] = [], draft: String = "") { self.entries = entries; self.draft = draft }
    }
    public enum ProjectFeatureError: Error { case invalidAction, invalidDraft, entryLimit }
    public enum ProjectFeature {
        // Compatible read-only surface retained for the iOS starter.
        public static func document(entries: [Entry], revision: UInt64 = 0) -> UIDocument {
            UIDocument(schemaVersion: 1, revision: revision, root: UINode(
                id: "project", kind: .vStack,
                properties: [:], children: [
                    UINode(id: "title", kind: .text, properties: ["text": .string("Your project")]),
                    UINode(id: "progress", kind: .text, properties: ["text": .string("\\(entries.filter(\\.completed).count) of \\(entries.count) completed")])
                ]
            ))
        }
        public static func document(state: ProjectFeatureState, revision: UInt64 = 0) -> UIDocument {
            MixerUI.Navigation("project", title: "Your project") {
                MixerUI.List("entries") {
                    MixerUI.Section("editor", title: "Entries") {
                        MixerUI.Text("progress", "\\(state.entries.filter(\\.completed).count) of \\(state.entries.count) completed")
                        MixerUI.TextField("draft", "New entry", value: state.draft, action: "draft.change", onSubmit: "entry.add")
                        MixerUI.Button("add", "Add entry", action: "entry.add")
                            .disabled(state.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || state.entries.count >= 100)
                    }
                    MixerUI.Section("items", title: "Project entries") {
                        for entry in state.entries {
                            MixerUI.Toggle("entry.\\(entry.id.uuidString)", entry.title, value: entry.completed, action: "entry.toggle")
                        }
                    }
                }
            }.document(revision: revision)
        }
        public static func handle(_ action: RoutedUIAction, state: inout ProjectFeatureState) throws {
            switch (action.actionID, action.value) {
            case ("draft.change", .string(let value)):
                guard action.nodeID == "draft", value.utf8.count <= 16_384 else { throw ProjectFeatureError.invalidAction }
                state.draft = value
            case ("entry.add", .null):
                guard action.nodeID == "add" || action.nodeID == "draft" else { throw ProjectFeatureError.invalidAction }
                let title = state.draft.trimmingCharacters(in: .whitespacesAndNewlines)
                guard !title.isEmpty else { throw ProjectFeatureError.invalidDraft }
                guard state.entries.count < 100 else { throw ProjectFeatureError.entryLimit }
                state.entries.append(Entry(title: title)); state.draft = ""
            case ("entry.toggle", .bool(let completed)):
                guard let index = state.entries.firstIndex(where: { "entry.\\($0.id.uuidString)" == action.nodeID }) else { throw ProjectFeatureError.invalidAction }
                state.entries[index].completed = completed
            default: throw ProjectFeatureError.invalidAction
            }
        }
    }
    """ + "\n"

    private static let modelTests = """
    import Testing
    import Foundation
    @testable import AppModels
    @testable import AppFeatures
    import MixerUI
    @Test func progressPreservesFraction() {
        #expect(ProjectProgress.fraction([Entry(title: "A", completed: true), Entry(title: "B")]) == 0.5)
        #expect(ProjectProgress.fraction([]) == 0)
    }
    @Test func draftRoundTrip() throws {
        let entry = Entry(title: "Inspect site", note: "Offline draft")
        #expect(try JSONDecoder().decode(Entry.self, from: JSONEncoder().encode(entry)) == entry)
        #expect(!Entry(title: "  ").isValid)
    }
    @Test func featureBuilds() { #expect(ProjectFeature.document(entries: []).root.id == "project") }
    @Test func sharedDraftAddToggle() throws {
        var state = ProjectFeatureState()
        var reconciler = UIReconciler()
        func action(_ id: String, _ event: UIEventKind, _ value: UIValue) throws -> RoutedUIAction {
            let snapshot = try reconciler.currentSnapshot()
            return try snapshot.route(UIEventEnvelope(revision: snapshot.document.revision,
                identity: #require(snapshot.identity(for: id)), event: event, value: value))
        }
        try reconciler.apply(ProjectFeature.document(state: state, revision: 1))
        try ProjectFeature.handle(action("draft", .textChange, .string(" Café 東京 ")), state: &state)
        try reconciler.apply(ProjectFeature.document(state: state, revision: 2))
        try ProjectFeature.handle(action("add", .activate, .null), state: &state)
        #expect(state.entries.count == 1); #expect(state.entries[0].title == "Café 東京"); #expect(state.draft.isEmpty)
        try reconciler.apply(ProjectFeature.document(state: state, revision: 3))
        try ProjectFeature.handle(action("entry.\\(state.entries[0].id.uuidString)", .valueChange, .bool(true)), state: &state)
        #expect(state.entries[0].completed)
    }
    """ + "\n"

    private static func appleApp(_ name: String) -> String {
        """
        import SwiftUI
        import MixerApple
        import AppFeatures
        @main struct \(name)App: App {
            @State private var host: MixerUIHost?
            @State private var failure: String?
            var body: some Scene {
                WindowGroup {
                    Group {
                        if let host { MixerNativeView(host: host, onAction: { _ in }) }
                        else if let failure { Text(failure) }
                        else { ProgressView() }
                    }.task {
                        do { host = try MixerUIHost(document: ProjectFeature.document(entries: [])) }
                        catch { failure = String(describing: error) }
                    }
                }
            }
        }
        """ + "\n"
    }
    private static func readme(_ name: String) -> String {
        """
        # \(name)

        Created with the mixer development preview. Run `mixer test` or `swift test`.
        `mixer.yml` uses JSON, a valid YAML 1.2 subset. The bundled SDK source snapshot
        is hashed in mixer.lock and allows offline builds without a cloud account.
        Source edits to that snapshot invalidate the lock until explicitly regenerated.

        The iOS app entry point is in Platforms/iOS. An explicit `--platform android`
        creation also generates a locked native Android host; see Platforms/Android.
        Android is an unsigned local cross-build, pending device qualification.
        SDK installation, Android UI, and signed OTA delivery are still being qualified. A passing host
        test is not a mobile release. Do not publish this preview as a qualified SDK.
        """ + "\n"
    }
}

public enum ProjectBuild {
    public static func verifyLock(root: URL, androidRequired: Bool = false) throws -> ToolchainLock {
        try verifiedLock(root: root, androidRequired: androidRequired).lock
    }

    static func verifiedLock(
        root: URL, androidRequired: Bool = false, requireCurrentAndroidProfile: Bool = true,
        swiftExecutable: String = "swift"
    ) throws -> (lock: ToolchainLock, bytes: Data) {
        let (lock, bytes) = try verifiedSourceLock(root: root, androidRequired: androidRequired,
                                                  requireCurrentAndroidProfile: requireCurrentAndroidProfile)
        try verifyHostSwift(lock: lock, swiftExecutable: swiftExecutable)
        return (lock, bytes)
    }

    static func verifyHostSwift(lock: ToolchainLock, swiftExecutable: String) throws {
        let (version, identity) = try SwiftVersionIdentity.inspect(swiftExecutable: swiftExecutable)
        if ProcessInfo.processInfo.environment["MIXER_SWIFT_IDENTITY_DIAGNOSTICS"] == "1" {
            let environment = ProcessInfo.processInfo.environment
            var observation: [String: Any] = [
                "event": "mixer.swift-lock-comparison", "argv": version.command,
                "expected": lock.swiftVersion, "observed": version.output,
                "exitCode": version.exitCode, "outputTruncated": version.outputTruncated,
                "cwd": FileManager.default.currentDirectoryPath,
                "environment": environment.filter { ["PATH", "DEVELOPER_DIR", "TOOLCHAINS", "SWIFT_EXEC", "SDKROOT", "MIXER_SWIFT"].contains($0.key) }
            ]
            if let identity { observation["observedIdentity"] = identity.banner }
            if let bytes = try? JSONSerialization.data(withJSONObject: observation, options: [.sortedKeys]) {
                FileHandle.standardError.write(bytes + Data([10]))
            }
        }
        guard identity?.matches(lockBanner: lock.swiftVersion) == true else { throw MixerFailure("lock.toolchain-drift", "Swift host compiler differs from mixer.lock. Select the pinned toolchain.") }
    }

    static func verifiedSourceLock(
        root: URL, androidRequired: Bool, requireCurrentAndroidProfile: Bool = true
    ) throws -> (lock: ToolchainLock, bytes: Data) {
        let config = try ApplicationConfiguration.load(root)
        try AndroidSDKCompatibility.requireHost(config.androidHost)
        let lockURL = root.appendingPathComponent("mixer.lock")
        if (androidRequired || config.targets.contains("android")), !FileManager.default.fileExists(atPath: lockURL.path) {
            try AndroidSDKCompatibility.require(nil)
        }
        let bytes = try Data(contentsOf: lockURL)
        let lock = try JSONDecoder().decode(ToolchainLock.self, from: bytes)
        guard lock.schema == 1 else { throw MixerFailure("lock.schema", "Unsupported lock schema") }
        if androidRequired || config.targets.contains("android") || lock.android != nil {
            if requireCurrentAndroidProfile {
                try AndroidSDKCompatibility.require(lock.android?.profile)
                try AndroidSDKCompatibility.admitProject(root)
            } else if lock.android == nil {
                throw MixerFailure("upgrade.android-lock", "The source project needs a locked Android adapter.")
            }
        }
        let actual = try SourceDigest.tree(root.appendingPathComponent("Generated/MixerSDK"))
        guard actual == lock.sdkDigest else { throw MixerFailure("lock.sdk-drift", "Bundled SDK source differs from mixer.lock. Restore the original SDK snapshot or explicitly install a new qualified SDK.") }
        if let android = lock.android {
            guard try SourceDigest.tree(root.appendingPathComponent("Generated/MixerAndroid")) == android.adapterDigest else { throw MixerFailure("lock.android-drift", "Bundled Android adapter source differs from mixer.lock. Restore the original locked adapter snapshot.") }
        }
        return (lock, bytes)
    }
    public static func run(root: URL, test: Bool, platform: String) throws -> CommandResult {
        _ = try verifyLock(root: root, androidRequired: platform == "android")
        if platform == "ios", !test { return try AppleProject.build(root: root) }
        if platform == "android", !test { return try AndroidProject.build(root: root) }
        guard platform == "host" else { throw MixerFailure("build.unqualified-target", "\(platform) \(test ? "tests" : "build") requires pending native integration; no platform result is reported as passed. Available: host package build/test, unsigned iOS Simulator build.") }
        return try ProcessRunner.run(["swift", test ? "test" : "build", "--package-path", root.path], at: root, policy: .developmentBuild)
    }
    public static func runRetainingNative(root: URL, test: Bool, platform: String, output: URL) throws -> NativeBuildOutput.Report {
        guard platform == "ios", !test else {
            throw MixerFailure("build.output-platform", "--output requires an explicit non-test --platform ios build.")
        }
        let store = try NativeBuildOutput.prepare(output: output, root: root)
        let swiftExecutable = ProcessInfo.processInfo.environment["MIXER_WORKER_COMMAND_CONTROL"] == "1"
            ? "/usr/bin/swift" : "swift"
        let lock = try verifiedLock(root: root, swiftExecutable: swiftExecutable).lock
        return try AppleProject.build(root: root, retainingIn: store, lock: lock)
    }
    public static func export(root: URL, destination: URL) throws -> String {
        let original = try verifiedLock(root: root)
        return try publishSnapshot(root: root, destination: destination) { staging in
            let copied = try verifiedLock(root: staging)
            guard copied.bytes == original.bytes else {
                throw MixerFailure("export.lock-changed", "mixer.lock changed while copying the project. Retry the export.")
            }
        }
    }

    public static func upgrade(root: URL, destination: URL, sdk: URL, androidAdapter: URL?) throws -> String {
        let root = root.resolvingSymlinksInPath().standardizedFileURL
        // Check the old snapshot against its own lock without executing its SDK or adapter.
        let original = try verifiedLock(root: root, requireCurrentAndroidProfile: false)
        guard (original.lock.android != nil) == (androidAdapter != nil) else {
            throw MixerFailure("upgrade.android-adapter", "For an Android project, supply the SDK and Android adapter from the same target revision.")
        }
        let originalSource = try SourceDigest.exportFingerprint(root)
        let sourceChanged = MixerFailure("upgrade.source-changed", "Project files changed during the copy. Close editors and builds, then retry.")
        return try publishSnapshot(root: root, destination: destination, prepare: { staging in
            let copied = try verifiedLock(root: staging, requireCurrentAndroidProfile: false)
            guard copied.bytes == original.bytes else {
                throw MixerFailure("upgrade.lock-changed", "mixer.lock changed while copying the project. Retry the upgrade.")
            }
            guard try SourceDigest.exportFingerprint(staging) == originalSource else { throw sourceChanged }
            let config = try ApplicationConfiguration.load(staging)
            let fm = FileManager.default
            var lock = copied.lock
            try fm.removeItem(at: staging.appendingPathComponent("Generated/MixerSDK"))
            lock.sdkDigest = try ProjectGenerator.snapshotSDK(from: sdk, into: staging, requireIOS: config.targets.contains("ios"))
            if let androidAdapter {
                let target = staging.appendingPathComponent("Generated/MixerAndroid")
                try fm.removeItem(at: target)
                let digest = try AndroidProject.snapshot(adapter: androidAdapter, destination: target)
                lock.android = AndroidToolchainLock(adapterDigest: digest, toolchain: try AndroidProject.inspectToolchain(),
                                                   profile: AndroidSDKCompatibility.profile.lock)
            }
            try JSONFile.write(lock, to: staging.appendingPathComponent("mixer.lock"))
            let prepared = try SourceDigest.exportFingerprint(staging)
            _ = try verifyLock(root: staging)
            guard try SourceDigest.exportFingerprint(staging) == prepared else {
                throw MixerFailure("upgrade.stage-changed", "The staged project changed during validation. Retry the upgrade.")
            }
        }, beforePublish: {
            guard try SourceDigest.exportFingerprint(root) == originalSource else { throw sourceChanged }
        })
    }

    private static func publishSnapshot(
        root: URL, destination: URL, prepare: (URL) throws -> Void, beforePublish: () throws -> Void = {}
    ) throws -> String {
        let root = root.resolvingSymlinksInPath().standardizedFileURL
        let requested = destination.standardizedFileURL
        let parent = requested.deletingLastPathComponent().resolvingSymlinksInPath().standardizedFileURL
        let destination = parent.appendingPathComponent(requested.lastPathComponent)
        try requireExportOutsideSource(destination, root: root)
        let exists = MixerFailure("export.exists", "Refusing to overwrite export destination.")
        var existing = stat()
        guard lstat(destination.path, &existing) != 0 else { throw exists }

        let entries = try SourceDigest.exportEntries(in: root)
        let files = FileManager.default
        try files.createDirectory(at: parent, withIntermediateDirectories: true)
        try requireExportOutsideSource(destination, root: root)
        let staging = parent.appendingPathComponent(".mixer-export-" + UUID().uuidString, isDirectory: true)
        guard mkdir(staging.path, 0o700) == 0 else {
            let reason = String(cString: strerror(errno))
            throw MixerFailure("export.stage", "Cannot create export staging directory: \(reason)")
        }
        var published = false
        defer { if !published { try? files.removeItem(at: staging) } }

        try copyExportEntries(entries, from: root, to: staging)
        try prepare(staging)
        let digest = try SourceDigest.tree(staging)
        try requireExportOutsideSource(destination, root: root)
        try beforePublish()
        guard renameatx_np(AT_FDCWD, staging.path, AT_FDCWD, destination.path, UInt32(RENAME_EXCL)) == 0 else {
            let error = errno
            if error == EEXIST { throw exists }
            throw MixerFailure("export.publish", "Cannot publish export: \(String(cString: strerror(error)))")
        }
        published = true
        return digest
    }

    static func copyExportEntries(_ entries: [(relative: String, directory: Bool)], from root: URL, to staging: URL) throws {
        var created = Set<Data>()
        for entry in entries {
            let components = entry.relative.split(separator: "/")
            let parents = entry.directory ? components[...] : components.dropLast()
            var directory = staging
            var relative = ""
            for name in parents {
                relative = relative.isEmpty ? String(name) : relative + "/" + name
                directory = directory.appendingPathComponent(String(name), isDirectory: true)
                // Use the source spelling so canonically equivalent names still attempt separate mkdirs.
                if created.insert(Data(relative.utf8)).inserted, mkdir(directory.path, 0o777) != 0 {
                    let error = errno
                    if error == EEXIST {
                        throw MixerFailure("export.directory-collision", "Export directory collides with an existing entry: \(relative)")
                    }
                    throw MixerFailure("export.stage", "Cannot stage directory \(relative): \(String(cString: strerror(error)))")
                }
            }
            if !entry.directory {
                let target = staging.appendingPathComponent(entry.relative)
                try FileManager.default.copyItem(at: root.appendingPathComponent(entry.relative), to: target)
                let info = try target.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])
                guard info.isRegularFile == true, info.isSymbolicLink != true else {
                    throw MixerFailure("export.source-changed", "Source changed type while copying: \(entry.relative)")
                }
            }
        }
    }

    private static func requireExportOutsideSource(_ destination: URL, root: URL) throws {
        var source = stat()
        guard stat(root.path, &source) == 0 else {
            throw MixerFailure("export.destination", "Cannot inspect the export source directory.")
        }

        // An absent destination can hide a symlink in one of its existing parents.
        var ancestor = destination
        while !FileManager.default.fileExists(atPath: ancestor.path) {
            let parent = ancestor.deletingLastPathComponent()
            guard parent.path != ancestor.path else {
                throw MixerFailure("export.destination", "Cannot inspect the export destination ancestry.")
            }
            ancestor = parent
        }
        ancestor = ancestor.resolvingSymlinksInPath().standardizedFileURL
        while true {
            var directory = stat()
            guard stat(ancestor.path, &directory) == 0 else {
                throw MixerFailure("export.destination", "Cannot inspect the export destination ancestry.")
            }
            // Directory identity also handles case and Unicode aliases on volumes that allow them.
            guard directory.st_dev != source.st_dev || directory.st_ino != source.st_ino else {
                throw MixerFailure("export.destination", "Export must be outside the source project.")
            }
            if ancestor.path == "/" { return }
            ancestor = ancestor.deletingLastPathComponent()
        }
    }
}
