import Foundation

public struct GeneratedProject: Codable, Sendable {
    public var path: String
    public var application: String
    public var sdkDigest: String
    public var qualification = "local-development-only"
    public var nextSteps: [String]
}

public enum ProjectGenerator {
    public static func create(name: String, application: String, destination: URL, sdk: URL) throws -> GeneratedProject {
        let config = ApplicationConfiguration(name: name, application: application)
        try config.validate()
        let fm = FileManager.default
        guard !fm.fileExists(atPath: destination.path) else { throw MixerFailure("create.exists", "Refusing to overwrite \(destination.path). Choose a new directory.") }
        guard fm.fileExists(atPath: sdk.appendingPathComponent("Package.swift").path) else { throw MixerFailure("create.sdk", "SDK package not found at \(sdk.path). Supply --sdk-path to an installed Mixer SDK source distribution.") }
        let parent = destination.deletingLastPathComponent()
        try fm.createDirectory(at: parent, withIntermediateDirectories: true)
        let staging = parent.appendingPathComponent(".mixer-create-\(UUID().uuidString)")
        try fm.createDirectory(at: staging, withIntermediateDirectories: true)
        defer { try? fm.removeItem(at: staging) }
        for path in ["Sources/AppModels", "Sources/AppFeatures", "Sources/NativeServices", "Tests/AppModelsTests", "Platforms/iOS", "Platforms/Android", "Resources", "Generated/MixerSDK"] {
            try fm.createDirectory(at: staging.appendingPathComponent(path), withIntermediateDirectories: true)
        }
        let sdk = sdk.resolvingSymlinksInPath().standardizedFileURL
        let sdkTarget = staging.appendingPathComponent("Generated/MixerSDK")
        for file in try SourceDigest.files(in: sdk) {
            let relative = String(file.path.dropFirst(sdk.path.count + 1))
            let target = sdkTarget.appendingPathComponent(relative)
            try fm.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
            try fm.copyItem(at: file, to: target)
        }
        let digest = try SourceDigest.tree(sdkTarget)
        let version = try ProcessRunner.run(["swift", "--version"])
        guard version.succeeded else { throw MixerFailure("create.swift", version.output) }
        try JSONFile.write(config, to: staging.appendingPathComponent("mixer.yml"))
        try JSONFile.write(ToolchainLock(sdkDigest: digest, swiftVersion: version.output.trimmingCharacters(in: .whitespacesAndNewlines)), to: staging.appendingPathComponent("mixer.lock"))
        let files = [
            "Package.swift": package(name),
            "Sources/AppModels/Entry.swift": models,
            "Sources/AppFeatures/ProjectFeature.swift": features,
            "Sources/NativeServices/README.md": "Native integrations live here. A new native capability requires a new store binary.\n",
            "Tests/AppModelsTests/EntryTests.swift": modelTests,
            "Platforms/iOS/\(name)App.swift": appleApp(name),
            "Platforms/Android/README.md": "Android host generation and Swift/JNI integration are tracked in W05. This project does not yet contain a qualified Android application.\n",
            "README.md": readme(name),
            ".gitignore": ".build/\n.swiftpm/\n.mixer/\n.DS_Store\n"
        ]
        for (path, contents) in files { try contents.write(to: staging.appendingPathComponent(path), atomically: true, encoding: .utf8) }
        _ = try AppleProject.generate(root: staging)
        // An entire project becomes visible only when construction succeeds.
        try fm.moveItem(at: staging, to: destination)
        return GeneratedProject(path: destination.path, application: application, sdkDigest: digest, nextSteps: ["cd \(destination.path)", "mixer test", "mixer doctor"])
    }

    private static func package(_ name: String) -> String {
        """
        // swift-tools-version: 6.0
        import PackageDescription
        let package = Package(
            name: "\(name)", platforms: [.iOS(.v17), .macOS(.v14)],
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
    import AppModels
    import MixerUI
    public enum ProjectFeature {
        public static func document(entries: [Entry], revision: UInt64 = 0) -> UIDocument {
            UIDocument(schemaVersion: 1, revision: revision, root: UINode(
                id: "project", kind: .vStack,
                properties: [:], children: [
                    UINode(id: "title", kind: .text, properties: ["text": .string("Your project")]),
                    UINode(id: "progress", kind: .text, properties: ["text": .string("\\(entries.filter(\\.completed).count) of \\(entries.count) completed")])
                ]
            ))
        }
    }
    """ + "\n"

    private static let modelTests = """
    import Testing
    import Foundation
    @testable import AppModels
    @testable import AppFeatures
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

        The iOS app entry point is in Platforms/iOS. Native project generation,
        Android UI, and signed OTA delivery are still being qualified. A passing host
        test is not a mobile release. Do not publish this preview as a qualified SDK.
        """ + "\n"
    }
}

public enum ProjectBuild {
    public static func verifyLock(root: URL) throws -> ToolchainLock {
        _ = try ApplicationConfiguration.load(root)
        let lock = try JSONDecoder().decode(ToolchainLock.self, from: Data(contentsOf: root.appendingPathComponent("mixer.lock")))
        guard lock.schema == 1 else { throw MixerFailure("lock.schema", "Unsupported lock schema") }
        let actual = try SourceDigest.tree(root.appendingPathComponent("Generated/MixerSDK"))
        guard actual == lock.sdkDigest else { throw MixerFailure("lock.sdk-drift", "Bundled SDK source differs from mixer.lock. Restore the original SDK snapshot or explicitly install a new qualified SDK.") }
        let version = try ProcessRunner.run(["swift", "--version"])
        guard version.succeeded, version.output.trimmingCharacters(in: .whitespacesAndNewlines) == lock.swiftVersion else { throw MixerFailure("lock.toolchain-drift", "Swift host compiler differs from mixer.lock. Select the pinned toolchain.") }
        return lock
    }
    public static func run(root: URL, test: Bool, platform: String) throws -> CommandResult {
        _ = try verifyLock(root: root)
        if platform == "ios", !test { return try AppleProject.build(root: root) }
        guard platform == "host" else { throw MixerFailure("build.unqualified-target", "\(platform) \(test ? "tests" : "build") requires pending native integration; no platform result is reported as passed. Available: host package build/test, unsigned iOS Simulator build.") }
        return try ProcessRunner.run(["swift", test ? "test" : "build", "--package-path", root.path], at: root)
    }
    public static func export(root: URL, destination: URL) throws -> String {
        _ = try verifyLock(root: root)
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
            return try SourceDigest.tree(destination)
        } catch { try? FileManager.default.removeItem(at: destination); throw error }
    }
}
