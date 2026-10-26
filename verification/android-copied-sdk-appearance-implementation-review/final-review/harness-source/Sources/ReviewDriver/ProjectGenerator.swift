import Foundation

public struct GeneratedProject: Codable, Sendable {
    public var path: String
    public var application: String
    public var sdkDigest: String
    public var qualification = "local-development-only"
    public var nextSteps: [String]
}

public enum ProjectGenerator {
    public static func create(name: String, application: String, destination: URL, sdk: URL, platform: String = "ios", androidAdapter: URL? = nil) throws -> GeneratedProject {
        guard ["ios", "android"].contains(platform) else { throw MixerFailure("create.platform", "Create supports ios (default) or android (both native hosts).") }
        var config = ApplicationConfiguration(name: name, application: application)
        config.targets = platform == "android" ? ["ios", "android"] : ["ios"]
        // The starter requests no native capabilities. Adding one requires an
        // implemented native host and a new binary, never a successful stub.
        config.capabilities = []
        try config.validate()
        let fm = FileManager.default
        guard !fm.fileExists(atPath: destination.path) else { throw MixerFailure("create.exists", "Refusing to overwrite \(destination.path). Choose a new directory.") }
        guard platform == "android" || fm.fileExists(atPath: sdk.appendingPathComponent("Package.swift").path) else { throw MixerFailure("create.sdk", "SDK package not found at \(sdk.path). Supply --sdk-path to an installed Mixer SDK source distribution.") }
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
        let sdkTarget = staging.appendingPathComponent("Generated/MixerSDK")
        for file in try SourceDigest.files(in: sdk) {
            let relative = String(file.path.dropFirst(sdk.path.count + 1))
            let target = sdkTarget.appendingPathComponent(relative)
            try fm.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
            try fm.copyItem(at: file, to: target)
        }
        if platform == "android" { try AndroidSDKCompatibility.admitSDK(sdkTarget) }
        let digest = try SourceDigest.tree(sdkTarget)
        var adapterDigest: String?
        if platform == "android", let androidAdapter {
            adapterDigest = try AndroidProject.snapshot(adapter: androidAdapter, destination: staging.appendingPathComponent("Generated/MixerAndroid"))
            try AndroidSDKCompatibility.admitProject(staging)
        }
        let version = try ProcessRunner.run(["swift", "--version"])
        guard version.succeeded else { throw MixerFailure("create.swift", version.output) }
        try JSONFile.write(config, to: staging.appendingPathComponent("mixer.yml"))
        var lock = ToolchainLock(sdkDigest: digest, swiftVersion: version.output.trimmingCharacters(in: .whitespacesAndNewlines))
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
        if platform == "android" { try AndroidProject.generate(root: staging) }
        else { try "No Android host was requested. Create a new project with --platform android for the unsigned local development host.\n".write(to: staging.appendingPathComponent("Platforms/Android/README.md"), atomically: true, encoding: .utf8) }
        // An entire project becomes visible only when construction succeeds.
        try fm.moveItem(at: staging, to: destination)
        return GeneratedProject(path: destination.path, application: application, sdkDigest: digest, nextSteps: ["cd \(destination.path)", "mixer test", "mixer doctor"])
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
        let config = try ApplicationConfiguration.load(root)
        let lockURL = root.appendingPathComponent("mixer.lock")
        if (androidRequired || config.targets.contains("android")), !FileManager.default.fileExists(atPath: lockURL.path) {
            try AndroidSDKCompatibility.require(nil)
        }
        let lock = try JSONDecoder().decode(ToolchainLock.self, from: Data(contentsOf: lockURL))
        guard lock.schema == 1 else { throw MixerFailure("lock.schema", "Unsupported lock schema") }
        if androidRequired || config.targets.contains("android") || lock.android != nil {
            try AndroidSDKCompatibility.require(lock.android?.profile)
            try AndroidSDKCompatibility.admitProject(root)
        }
        let actual = try SourceDigest.tree(root.appendingPathComponent("Generated/MixerSDK"))
        guard actual == lock.sdkDigest else { throw MixerFailure("lock.sdk-drift", "Bundled SDK source differs from mixer.lock. Restore the original SDK snapshot or explicitly install a new qualified SDK.") }
        if let android = lock.android {
            guard try SourceDigest.tree(root.appendingPathComponent("Generated/MixerAndroid")) == android.adapterDigest else { throw MixerFailure("lock.android-drift", "Bundled Android adapter source differs from mixer.lock. Restore the original locked adapter snapshot.") }
        }
        let version = try ProcessRunner.run(["swift", "--version"])
        guard version.succeeded, version.output.trimmingCharacters(in: .whitespacesAndNewlines) == lock.swiftVersion else { throw MixerFailure("lock.toolchain-drift", "Swift host compiler differs from mixer.lock. Select the pinned toolchain.") }
        return lock
    }
    public static func run(root: URL, test: Bool, platform: String) throws -> CommandResult {
        _ = try verifyLock(root: root, androidRequired: platform == "android")
        if platform == "ios", !test { return try AppleProject.build(root: root) }
        if platform == "android", !test { return try AndroidProject.build(root: root) }
        guard platform == "host" else { throw MixerFailure("build.unqualified-target", "\(platform) \(test ? "tests" : "build") requires pending native integration; no platform result is reported as passed. Available: host package build/test, unsigned iOS Simulator build.") }
        return try ProcessRunner.run(["swift", test ? "test" : "build", "--package-path", root.path], at: root)
    }
    public static func export(root: URL, destination: URL) throws -> String {
        let lock = try verifyLock(root: root)
        let root = root.resolvingSymlinksInPath().standardizedFileURL; let destination = destination.resolvingSymlinksInPath().standardizedFileURL
        guard !destination.path.hasPrefix(root.path + "/"), destination != root else { throw MixerFailure("export.destination", "Export must be outside the source project.") }
        guard !FileManager.default.fileExists(atPath: destination.path) else { throw MixerFailure("export.exists", "Refusing to overwrite export destination.") }
        let files = try SourceDigest.files(in: root)
        try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)
        do {
            for source in files {
                let relative = String(source.path.dropFirst(root.path.count + 1))
                let target = destination.appendingPathComponent(relative)
                try FileManager.default.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
                try FileManager.default.copyItem(at: source, to: target)
            }
            if lock.android != nil { try AndroidSDKCompatibility.admitProject(destination) }
            return try SourceDigest.tree(destination)
        } catch { try? FileManager.default.removeItem(at: destination); throw error }
    }
}
