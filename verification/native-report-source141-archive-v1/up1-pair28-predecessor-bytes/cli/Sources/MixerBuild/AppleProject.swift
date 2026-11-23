#if canImport(Darwin)
import Darwin
#elseif canImport(Android)
import Android
#else
import Glibc
#endif
import Foundation

public enum AppleProject {
    public struct RunReport: Encodable, Sendable {
        public let platform = "ios-simulator"
        public let device: String
        public let application: String
        public let commands: [CommandResult]
        public var succeeded: Bool { commands.allSatisfy(\.succeeded) }
    }

    public static func run(root: URL, simulator: String) throws -> RunReport {
        guard UUID(uuidString: simulator) != nil else { throw MixerFailure("run.device", "Pass an explicit iOS Simulator UUID from xcrun simctl list devices; physical signing is not integrated yet.") }
        _ = try ProjectBuild.verifyLock(root: root)
        let config = try ApplicationConfiguration.load(root)
        var commands = [try build(root: root)]
        guard commands.last?.succeeded == true else { return RunReport(device: simulator, application: config.application, commands: commands) }
        let binary = root.appendingPathComponent(".mixer/ios-build/Build/Products/Debug-iphonesimulator/\(config.name).app")
        commands.append(try ProcessRunner.run(["xcrun", "simctl", "install", simulator, binary.path], policy: .simulatorManagement))
        if commands.last?.succeeded == true { commands.append(try ProcessRunner.run(["xcrun", "simctl", "launch", simulator, config.application], policy: .simulatorManagement)) }
        return RunReport(device: simulator, application: config.application, commands: commands)
    }

    /// Only a prior rendering of the stock template can be regenerated.
    public static func generate(root: URL) throws -> URL {
        try generate(root: root, config: ApplicationConfiguration.load(root))
    }

    private static func generate(root: URL, config: ApplicationConfiguration) throws -> URL {
        let platforms = root.appendingPathComponent("Platforms")
        let platform = platforms.appendingPathComponent("iOS")
        let project = platform.appendingPathComponent("\(config.name).xcodeproj")
        let file = project.appendingPathComponent("project.pbxproj")
        let receipt = project.appendingPathComponent("mixer-generated.sha256")
        let rawPlist = project.appendingPathComponent("MixerNativeInfo.plist")
        for directory in [platforms, platform, project] {
            try AppleNativeConfiguration.require(directory, type: S_IFDIR, allowMissing: true)
        }
        let inputs = config.iosNative ?? AppleNativeConfiguration()
        try AppleNativeConfiguration.require(platform.appendingPathComponent("\(config.name)App.swift"),
                                             type: S_IFREG, allowMissing: inputs.isEmpty)
        try inputs.validateFiles(in: platform)
        let plist = try inputs.plist()
        let desired = try generatedArtifacts(name: config.name, application: config.application, inputs: inputs,
                                             plist: plist)

        try FileManager.default.createDirectory(at: project, withIntermediateDirectories: true)
        let directory = open(project.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard directory >= 0 else { throw POSIXError(.init(rawValue: errno) ?? .EIO) }
        defer { close(directory) }
        guard flock(directory, LOCK_EX) == 0 else { throw POSIXError(.init(rawValue: errno) ?? .EIO) }

        // The historical fixed path may contain app-owned data, even during recovery.
        guard try AppleNativeConfiguration.fileType(rawPlist) == nil else { throw modified }
        for output in [file, receipt] {
            try AppleNativeConfiguration.require(output, type: S_IFREG, allowMissing: true)
        }
        let observed = try Artifacts(project: readIfPresent(file), receipt: readIfPresent(receipt))
        let previous: Artifacts
        let previousPlist: Data?
        if let data = observed.receipt, data.starts(with: Transaction.header) {
            let pending = try Transaction.decode(data)
            let before = try pending.before.validatedPlist(name: config.name)
            let after = try pending.after.validatedPlist(name: config.name, complete: true)
            if observed.project == pending.after.project {
                previous = pending.after
                previousPlist = after
            } else {
                guard observed.project == pending.before.project else { throw modified }
                previous = pending.before
                previousPlist = before
            }
        } else {
            previous = observed
            previousPlist = try observed.validatedPlist(name: config.name)
        }

        if let previousPlist, previousPlist != plist {
            try checkPlist(previousPlist, root: root, publish: false)
        }
        if let plist { try checkPlist(plist, root: root, publish: false) }
        if observed.project != desired.project {
            let pending = try Transaction(before: previous, after: Artifacts(project: desired.project, receipt: desired.receipt)).encoded()
            if pending != observed.receipt { try pending.write(to: receipt, options: .atomic) }
        }
        if let plist { try checkPlist(plist, root: root, publish: true) }
        if observed.project != desired.project { try desired.project.write(to: file, options: .atomic) }
        if observed.project != desired.project || observed.receipt != desired.receipt {
            try desired.receipt.write(to: receipt, options: .atomic)
        }
        return project
    }

    private struct Artifacts: Codable {
        let project: Data?
        let receipt: Data?

        func validatedPlist(name: String, complete: Bool = false) throws -> Data? {
            guard let project else {
                guard !complete, receipt == nil else { throw modified }
                return nil
            }
            return try previousPlist(project: project, receipt: receipt, name: name, allowLegacy: !complete)
        }
    }

    private struct Transaction: Codable {
        static let header = Data("mixer-ios-generation-transaction-v2\n".utf8)

        let before: Artifacts
        let after: Artifacts

        func encoded() throws -> Data { try Self.header + JSONFile.data(self) }

        static func decode(_ data: Data) throws -> Self {
            guard let transaction = try? JSONDecoder().decode(Self.self, from: data.dropFirst(header.count)) else {
                throw modified
            }
            return transaction
        }
    }

    private static func generatedArtifacts(name: String, application: String, inputs: AppleNativeConfiguration,
                                           plist: Data?) throws -> (project: Data, receipt: Data) {
        let project = Data(source(name: name, application: application, inputs: inputs, plist: plist).utf8)
        var receipt = SourceDigest.sha256(project) + "\n"
        if !inputs.isEmpty {
            var canonical = inputs
            canonical.swiftSources = inputs.sources.isEmpty ? nil : inputs.sources
            canonical.resourceFolders = inputs.folders.isEmpty ? nil : inputs.folders
            receipt += try JSONFile.data(canonical).base64EncodedString() + "\n"
        }
        return (project, Data(receipt.utf8))
    }

    private static let plistDirectory = "ios-plists"

    private static func plistName(_ bytes: Data) -> String { SourceDigest.sha256(bytes) + ".plist" }

    // A digest names an input, not an owned inode. Publish exclusively and only read existing names.
    private static func checkPlist(_ bytes: Data, root: URL, publish: Bool) throws {
        let directoryFlags = O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC
        let project = open(root.path, directoryFlags)
        guard project >= 0 else { throw ioError() }
        defer { close(project) }

        func openDirectory(_ parent: Int32, _ name: String) throws -> Int32? {
            if publish, mkdirat(parent, name, 0o755) != 0, errno != EEXIST { throw ioError() }
            let fd = openat(parent, name, directoryFlags)
            if fd >= 0 { return fd }
            if !publish, errno == ENOENT { return nil }
            if errno == ELOOP || errno == ENOTDIR { throw modified }
            throw ioError()
        }

        guard let mixer = try openDirectory(project, ".mixer") else { return }
        defer { close(mixer) }
        guard let directory = try openDirectory(mixer, plistDirectory) else { return }
        defer { close(directory) }

        let name = plistName(bytes)
        func existingMatches() throws -> Bool {
            let fd = openat(directory, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
            if fd < 0 {
                if errno == ENOENT { return false }
                if errno == ELOOP { throw modified }
                throw ioError()
            }
            let file = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
            var info = stat()
            guard fstat(fd, &info) == 0, info.st_mode & S_IFMT == S_IFREG, info.st_size == bytes.count,
                  try file.read(upToCount: bytes.count + 1) == bytes else { throw modified }
            return true
        }

        if try existingMatches() { return }
        guard publish else { return }
        let stage = ".plist-" + UUID().uuidString
        let fd = openat(directory, stage, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard fd >= 0 else { throw ioError() }
        defer { unlinkat(directory, stage, 0) }
        let file = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        try file.write(contentsOf: bytes)
        guard fchmod(fd, 0o444) == 0 else { throw ioError() }
        try file.close()
        if linkat(directory, stage, directory, name, 0) != 0 {
            guard errno == EEXIST else { throw ioError() }
            guard try existingMatches() else { throw modified }
        }
    }

    private static func ioError() -> POSIXError { POSIXError(.init(rawValue: errno) ?? .EIO) }

    private static var modified: MixerFailure {
        MixerFailure("generate.modified", "Generated Xcode project was edited. Preserve your edits and reconcile the project before regeneration.")
    }

    private static func readIfPresent(_ file: URL) throws -> Data? {
        guard try AppleNativeConfiguration.fileType(file) != nil else { return nil }
        return try Data(contentsOf: file)
    }

    private static func previousPlist(project: Data, receipt: Data?, name: String, allowLegacy: Bool) throws -> Data? {
        guard let receipt, let text = String(data: receipt, encoding: .utf8) else { throw modified }
        let lines = text.trimmingCharacters(in: .whitespacesAndNewlines).split(separator: "\n", omittingEmptySubsequences: false)
        guard (1...2).contains(lines.count), lines[0] == SourceDigest.sha256(project),
              let content = String(data: project, encoding: .utf8),
              let start = content.range(of: "PRODUCT_BUNDLE_IDENTIFIER = ")?.upperBound,
              let end = content[start...].firstIndex(of: ";") else { throw modified }

        let application = String(content[start..<end])
        guard application.range(of: #"\A[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+\z"#,
                                options: .regularExpression) != nil else { throw modified }
        var inputs = AppleNativeConfiguration()
        if lines.count == 2 {
            guard let data = Data(base64Encoded: String(lines[1])),
                  let candidate = try? JSONDecoder().decode(AppleNativeConfiguration.self, from: data),
                  (try? candidate.validate(appName: name)) != nil else { throw modified }
            inputs = candidate
        }
        let plist = try inputs.plist()
        var templates: [ProjectTemplate] = [.current, .beforeDebugCondition]
        if allowLegacy && lines.count == 1 { templates.append(.legacy17) }
        guard templates.contains(where: { template in
            let rendering = source(name: name, application: application, inputs: inputs, plist: plist,
                                   template: template)
            return project == Data(rendering.utf8)
        }) else { throw modified }
        return plist
    }

    public static func build(root: URL, simulator: Bool = true) throws -> CommandResult {
        let config = try ApplicationConfiguration.load(root)
        if !simulator, config.iosNative?.simulatorArchive != nil {
            throw MixerFailure("build.ios-native-archive", "This project declares a Simulator-only static archive.")
        }
        let project = try generate(root: root, config: config)
        return try ProcessRunner.run([
            "xcodebuild", "-project", project.path, "-scheme", config.name,
            "-configuration", "Debug", "-sdk", simulator ? "iphonesimulator" : "iphoneos",
            "-destination", simulator ? "generic/platform=iOS Simulator" : "generic/platform=iOS",
            "-derivedDataPath", root.appendingPathComponent(".mixer/ios-build").path,
            "CODE_SIGNING_ALLOWED=NO", "build"
        ], at: root, policy: .developmentBuild)
    }


    static func build(root: URL, retainingIn store: NativeBuildOutput.Store, lock: ToolchainLock) throws -> NativeBuildOutput.Report {
        let config = try ApplicationConfiguration.load(root)
        let project = try generate(root: root, config: config)
        // Xcode otherwise creates this source-side workspace during compilation.
        let workspace = project.appendingPathComponent("project.xcworkspace/contents.xcworkspacedata")
        if !FileManager.default.fileExists(atPath: workspace.path) {
            try FileManager.default.createDirectory(at: workspace.deletingLastPathComponent(), withIntermediateDirectories: true)
            try Data("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<Workspace version=\"1.0\"><FileRef location=\"self:\"></FileRef></Workspace>\n".utf8).write(to: workspace, options: .withoutOverwriting)
        }
        let derived = root.appendingPathComponent(".mixer/ios-build")
        let products = derived.appendingPathComponent("Build/Products/Debug-iphonesimulator")
        let command = ["/usr/bin/xcodebuild", "-project", project.path, "-scheme", config.name,
            "-configuration", "Debug", "-sdk", "iphonesimulator",
            "-destination", "generic/platform=iOS Simulator", "-derivedDataPath", derived.path,
            "-clonedSourcePackagesDirPath", derived.appendingPathComponent("SourcePackages").path,
            "-jobs", "4", "DEBUG_INFORMATION_FORMAT=dwarf-with-dsym", "ARCHS=arm64",
            "ONLY_ACTIVE_ARCH=YES", "ENABLE_DEBUG_DYLIB=NO", "COMPILER_INDEX_STORE_ENABLE=NO",
            "CODE_SIGNING_ALLOWED=NO", "build"]
        return try NativeBuildOutput.build(root: root, store: store, lock: lock, command: command,
            app: products.appendingPathComponent(config.name + ".app"),
            symbols: products.appendingPathComponent(config.name + ".app.dSYM"))
    }

    private enum ProjectTemplate {
        case current
        case beforeDebugCondition
        case legacy17
    }

    private static func source(name: String, application: String, inputs: AppleNativeConfiguration = .init(),
                               plist: Data? = nil, template: ProjectTemplate = .current) -> String {
        let minimumIOS = template == .legacy17 ? "17.0" : "26.0"
        let debugCondition = template == .current ? " SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;" : ""
        let swift = "sourcecode.swift"
        let paths = inputs.sources.map { ($0, swift) } + inputs.folders.map { ($0, "folder") }
        var children = ""
        var sources = ""
        var resources = [String]()
        var objects = ""
        for (index, entry) in paths.enumerated() {
            let (path, type) = entry
            let ref = String(format: "B%023llX", Int64(index * 2))
            let build = String(format: "B%023llX", Int64(index * 2 + 1))
            children += ", \(ref)"
            if type == swift { sources += ", \(build)" } else { resources.append(build) }
            objects += "    \(ref) = { isa = PBXFileReference; explicitFileType = \(type); path = \"\(path)\"; sourceTree = \"<group>\"; };\n"
            objects += "    \(build) = { isa = PBXBuildFile; fileRef = \(ref); };\n"
        }
        let archiveSettings = inputs.simulatorArchive.map {
            " SDKROOT = iphonesimulator; SUPPORTED_PLATFORMS = iphonesimulator;" +
            " \"OTHER_LDFLAGS[sdk=iphonesimulator*]\" = (\"$(inherited)\", \"$(SRCROOT)/\($0)\");"
        } ?? ""
        let plistSetting = plist.map { " INFOPLIST_FILE = \"../../.mixer/\(plistDirectory)/\(plistName($0))\";" } ?? ""
        return """
        // !$*UTF8*$!
        // Generated by mixer. App-owned native source lives beside this project.
        {
          archiveVersion = 1;
          classes = {};
          objectVersion = 60;
          objects = {
            A00000000000000000000001 = { isa = PBXProject; attributes = { LastUpgradeCheck = 2700; }; buildConfigurationList = A00000000000000000000002; compatibilityVersion = "Xcode 15.0"; developmentRegion = en; hasScannedForEncodings = 0; knownRegions = (en, Base); mainGroup = A00000000000000000000003; productRefGroup = A00000000000000000000004; projectDirPath = ""; projectRoot = ""; targets = (A00000000000000000000005); packageReferences = (A00000000000000000000020, A00000000000000000000021); };
            A00000000000000000000002 = { isa = XCConfigurationList; buildConfigurations = (A00000000000000000000006, A00000000000000000000007); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release; };
            A00000000000000000000003 = { isa = PBXGroup; children = (A00000000000000000000008, A00000000000000000000004\(children)); sourceTree = "<group>"; };
            A00000000000000000000004 = { isa = PBXGroup; name = Products; children = (A00000000000000000000009); sourceTree = "<group>"; };
            A00000000000000000000005 = { isa = PBXNativeTarget; buildConfigurationList = A00000000000000000000010; buildPhases = (A00000000000000000000011, A00000000000000000000012, A00000000000000000000013); buildRules = (); dependencies = (); name = \(name); productName = \(name); productReference = A00000000000000000000009; productType = "com.apple.product-type.application"; packageProductDependencies = (A00000000000000000000022, A00000000000000000000023); };
            A00000000000000000000006 = { isa = XCBuildConfiguration; buildSettings = { SDKROOT = iphoneos; IPHONEOS_DEPLOYMENT_TARGET = \(minimumIOS); SWIFT_VERSION = 6.0; CLANG_ENABLE_MODULES = YES; }; name = Debug; };
            A00000000000000000000007 = { isa = XCBuildConfiguration; buildSettings = { SDKROOT = iphoneos; IPHONEOS_DEPLOYMENT_TARGET = \(minimumIOS); SWIFT_VERSION = 6.0; CLANG_ENABLE_MODULES = YES; }; name = Release; };
            A00000000000000000000008 = { isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = \(name)App.swift; sourceTree = "<group>"; };
            A00000000000000000000009 = { isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = \(name).app; sourceTree = BUILT_PRODUCTS_DIR; };
            A00000000000000000000010 = { isa = XCConfigurationList; buildConfigurations = (A00000000000000000000014, A00000000000000000000015); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release; };
            A00000000000000000000011 = { isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = (A00000000000000000000016\(sources)); runOnlyForDeploymentPostprocessing = 0; };
            A00000000000000000000012 = { isa = PBXFrameworksBuildPhase; buildActionMask = 2147483647; files = (A00000000000000000000024, A00000000000000000000025); runOnlyForDeploymentPostprocessing = 0; };
            A00000000000000000000013 = { isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = (\(resources.joined(separator: ", "))); runOnlyForDeploymentPostprocessing = 0; };
            A00000000000000000000014 = { isa = XCBuildConfiguration; buildSettings = { \(settings(name, application, minimumIOS))\(plistSetting) SWIFT_OPTIMIZATION_LEVEL = "-Onone";\(debugCondition)\(archiveSettings) }; name = Debug; };
            A00000000000000000000015 = { isa = XCBuildConfiguration; buildSettings = { \(settings(name, application, minimumIOS))\(plistSetting) SWIFT_OPTIMIZATION_LEVEL = "-O";\(archiveSettings) }; name = Release; };
            A00000000000000000000016 = { isa = PBXBuildFile; fileRef = A00000000000000000000008; };
            A00000000000000000000020 = { isa = XCLocalSwiftPackageReference; relativePath = "../.."; };
            A00000000000000000000021 = { isa = XCLocalSwiftPackageReference; relativePath = "../../Generated/MixerSDK"; };
            A00000000000000000000022 = { isa = XCSwiftPackageProductDependency; package = A00000000000000000000020; productName = AppFeatures; };
            A00000000000000000000023 = { isa = XCSwiftPackageProductDependency; package = A00000000000000000000021; productName = MixerApple; };
            A00000000000000000000024 = { isa = PBXBuildFile; productRef = A00000000000000000000022; };
            A00000000000000000000025 = { isa = PBXBuildFile; productRef = A00000000000000000000023; };
        \(objects)  };
          rootObject = A00000000000000000000001;
        }
        """ + "\n"
    }
    private static func settings(_ name: String, _ app: String, _ minimumIOS: String) -> String {
        "PRODUCT_BUNDLE_IDENTIFIER = \(app); PRODUCT_NAME = \(name); GENERATE_INFOPLIST_FILE = YES; INFOPLIST_KEY_UILaunchScreen_Generation = YES; INFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES; TARGETED_DEVICE_FAMILY = \"1,2\"; CODE_SIGN_STYLE = Automatic; CURRENT_PROJECT_VERSION = 1; MARKETING_VERSION = 0.1.0; SWIFT_VERSION = 6.0; IPHONEOS_DEPLOYMENT_TARGET = \(minimumIOS); ENABLE_USER_SCRIPT_SANDBOXING = YES;"
    }
}
