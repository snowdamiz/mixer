import Darwin
import Foundation
import MixerProcessIO

/// Retains the products of one unsigned local Android build.
public enum AndroidBuildOutput {
    public enum Kind: String, Codable, Sendable {
        case unsignedAPK = "unsigned_apk"
        case debugSymbols = "debug_symbols"
        case resourceInventory = "resource_inventory"
    }

    public struct Product: Codable, Equatable, Sendable {
        public let kind: Kind
        public let sha256: String
        public let sizeBytes: UInt64
        public let ownedPath: String
    }

    public struct FileIdentity: Codable, Equatable, Sendable {
        public let sha256: String
        public let sizeBytes: UInt64
    }

    public struct Source: Codable, Equatable, Sendable {
        public let treeSHA256: String
        public let lock: FileIdentity
        public let sdkPins: FileIdentity
        public let platformPins: FileIdentity
        public let generatedDriver: FileIdentity
    }

    public struct Binding: Codable, Sendable {
        public let sourceBefore: Source
        public let sourceAfter: Source
        public let driverSourceBeforeSHA256: String
        public let driverSourceAfterSHA256: String
        public let validatedLock: ToolchainLock
        public let cliExecutable: FileIdentity
        public let command: [String]
        public let toolCommands: [[String]]
        public let environment: [String: String]
    }

    public struct APKEntry: Codable, Equatable, Sendable {
        public let path: String
        public let sha256: String
        public let sizeBytes: UInt64
        public let directory: Bool
    }

    public struct DebugProduct: Codable, Equatable, Sendable {
        public let library: String
        public let buildId: String
        public let debugPath: String
        public let sha256: String
        public let sizeBytes: UInt64
    }

    public struct Inventory: Codable, Equatable, Sendable {
        public let formatVersion: Int
        public let bindingSHA256: String
        public let apkSHA256: String
        public let debugSymbolsSHA256: String
        public let application: String
        public let androidHost: String
        public let activity: String
        public let abi: String
        public let minAPI: Int
        public let targetAPI: Int
        public let entries: [APKEntry]
        public let nativeDependencies: [String: [String]]
        public let debugProducts: [DebugProduct]
    }

    public struct Report: Codable, Sendable {
        public let formatVersion: Int
        public let scope: String
        public let binding: Binding
        public let unsignedAPK: Product
        public let debugSymbols: Product
        public let resourceInventory: Product
        fileprivate let storeDevice: Int32
        fileprivate let storeInode: UInt64
    }

    private struct DriverReceipt: Decodable {
        struct APKIdentity: Decodable {
            let application: String
            let activity: String
            let abi: String
            let minAPI: Int
            let targetAPI: Int
        }
        struct PinLock: Decodable {
            let path: String
            let sha256: String
            let bytes: UInt64
        }
        struct Command: Decodable {
            enum CodingKeys: String, CodingKey {
                case command, exitCode = "exit_code"
            }
            let command: [String]
            let exitCode: Int32
        }
        let schemaVersion: Int
        let qualification: String
        let application: String
        let androidHost: String
        let activity: String
        let applicationMinApi: Int
        let apk: String
        let apkIdentity: APKIdentity
        let apkSha256: String
        let apkBytes: UInt64
        let apkEntries: [APKEntry]
        let symbolsSha256: String
        let symbolsBytes: UInt64
        let debugProducts: [DebugProduct]
        let sourceTreeSha256: String
        let sourceTreeAfterSha256: String
        let platformDependencyLock: PinLock
        let sdkDigest: String
        let adapterDigest: String
        let sourceProfile: AndroidSDKProfileLock
        let toolchain: AndroidToolchainIdentity
        let nativeDependencies: [String: [String]]
        let commands: [Command]
        enum CodingKeys: String, CodingKey {
            case qualification, application, activity, apk, toolchain, commands
            case schemaVersion = "schema_version", androidHost = "android_host", applicationMinApi = "application_min_api"
            case apkIdentity = "apk_identity"
            case apkSha256 = "apk_sha256", apkBytes = "apk_bytes", apkEntries = "apk_entries"
            case symbolsSha256 = "symbols_sha256", symbolsBytes = "symbols_bytes", debugProducts = "debug_products"
            case sourceTreeSha256 = "source_tree_sha256", sourceTreeAfterSha256 = "source_tree_after_sha256"
            case platformDependencyLock = "platform_dependency_lock", sourceProfile = "source_profile"
            case sdkDigest = "sdk_digest", adapterDigest = "adapter_digest", nativeDependencies = "native_dependencies"
        }
    }

    private static let manifest = "android-build-v1.json"
    private static let scope = "unsigned-android/local-development"
    private static let driver = "Generated/MixerAndroid/android-build.py"
    private static let sdkPins = "Generated/MixerSDK/Package.resolved"
    private static let platformPins = "Platforms/Android/Package.resolved"

    struct ComposeReceipt: Decodable, Sendable {
        struct APK: Decodable, Sendable {
            let path: String
            let sha256: String
            let sizeBytes: UInt64
            let entries: [APKEntry]
        }
        struct Tool: Decodable, Sendable {
            let path: String
            let sha256: String
        }
        struct ToolCommand: Decodable, Sendable {
            let command: [String]
            let exitCode: Int
        }
        let schema: String
        let qualification: String
        let selection: AndroidProject.StagedComposeProject.Selection
        let command: [String]
        let toolCommands: [ToolCommand]
        let projectTreeBeforeSHA256: String
        let projectTreeAfterSHA256: String
        let driverSHA256: String
        let gradleVersion: String
        let tools: [String: Tool]
        let unsignedInitSHA256: String
        let toolEnvironment: [String: String]
        let dependencyCache: String
        let apk: APK
    }

    struct RetainedComposeBuild: Sendable {
        let receipt: ComposeReceipt
        let receiptBytes: Data
        let apk: Data
    }

    /// Execute a locked Compose module through the owned command boundary.
    /// The public build and store need the dedicated Compose runtime contract.
    static func buildRetainedCompose(
        root requestedRoot: URL, python: URL, toolEnvironment: [String: String], context: ProcessExecutionContext
    ) throws -> RetainedComposeBuild {
        let root = requestedRoot.resolvingSymlinksInPath().standardizedFileURL
        let inputs = ["MIXER_COMPOSE_GRADLE", "ANDROID_HOME", "MIXER_JDK", "MIXER_COMPOSE_DEPENDENCY_CACHE"]
        let executable = python.resolvingSymlinksInPath()
        guard root.path != "/", root.path != context.receiptDirectory.path,
              !context.receiptDirectory.path.hasPrefix(root.path + "/"),
              executable.isFileURL, executable.path.hasPrefix("/"), access(executable.path, X_OK) == 0,
              toolEnvironment.count == inputs.count,
              inputs.allSatisfy({ toolEnvironment[$0]?.hasPrefix("/") == true }) else { throw invalid }
        let driverURL = root.appendingPathComponent(driver)
        let installed = try AndroidSDKCompatibility.renderDriver(
            String(contentsOf: AndroidProject.buildDriver(), encoding: .utf8))
        let driverIdentity = identity(Data(installed.utf8))
        guard driverURL.resolvingSymlinksInPath().path == driverURL.path,
              try identity(file: driverURL) == driverIdentity else { throw drift }

        let snapshot = try context.makeInputSnapshot()
        defer { snapshot.removeIfUnheld() }
        let staged = try AndroidProject.stageRetainedCompose(root: root, in: snapshot)
        let output = snapshot.directory.appendingPathComponent("android-build", isDirectory: true)
        let argv = [executable.path, "-I", "-B", "-S", driverURL.path, "build-retained-v2",
                    staged.directory.path, output.path, staged.treeSHA256]
        let result = try ProcessRunner.run(argv, at: root, environment: toolEnvironment, policy: .developmentBuild,
                                           context: context, retaining: snapshot.retainedInputDirectories)
        guard result.succeeded else {
            throw MixerFailure("android.output-build", "Compose build exited \(result.exitCode).\n\(result.output.suffix(8_192))")
        }

        let fd = open(output.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw invalid }
        defer { close(fd) }
        let raw = try read("compose-build-receipt-v2.json", in: fd, maximum: 4 * 1_048_576)
        let receipt = try JSONDecoder().decode(ComposeReceipt.self, from: raw)
        let name = "compose-unsigned.apk"
        let apk = try read(name, in: fd, maximum: 32 * 1_048_576)
        let entries = receipt.apk.entries.map(\.path)
        guard receipt.schema == "mixer.android.retained-compose.2",
              receipt.qualification == "local-unsigned-compose-boundary-only",
              receipt.selection == staged.selection,
              receipt.command == argv, result.command == argv,
              receipt.projectTreeBeforeSHA256 == staged.treeSHA256,
              receipt.projectTreeAfterSHA256 == staged.treeSHA256,
              receipt.driverSHA256 == driverIdentity.sha256,
              try identity(file: driverURL) == driverIdentity,
              !receipt.gradleVersion.isEmpty, receipt.toolCommands.count == 3,
              receipt.toolCommands.allSatisfy({ $0.exitCode == 0 && !$0.command.isEmpty }),
              receipt.apk.path == output.appendingPathComponent(name).path,
              identity(apk) == FileIdentity(sha256: receipt.apk.sha256, sizeBytes: receipt.apk.sizeBytes),
              entries == Array(Set(entries)).sorted(by: { $0.utf8.lexicographicallyPrecedes($1.utf8) }),
              entries.contains("AndroidManifest.xml"), entries.contains("classes.dex") else { throw invalid }
        return RetainedComposeBuild(receipt: receipt, receiptBytes: raw, apk: apk)
    }

    public static func build(root requestedRoot: URL, output: URL) throws -> Report {
        let root = requestedRoot.resolvingSymlinksInPath().standardizedFileURL
        let context = ProcessExecutionContext.localDevelopment
        let worker = try WorkerProfile.load(root: root, output: output, context: context)
        guard root.path != "/", context.receiptDirectory.path != root.path,
              !context.receiptDirectory.path.hasPrefix(root.path + "/") else {
            throw MixerFailure("android.output-scratch", "Retained Android builds require temporary storage outside the project.")
        }
        try AndroidProject.rejectComposeSelection(root: root)
        let standaloneStore = try worker == nil
            ? NativeBuildOutput.prepare(output: output, root: root, requireSourceIdentity: true) : nil
        let validated = try AndroidProject.prepareBuild(root: root, worker: worker != nil)
        guard let android = validated.lock.android else {
            throw MixerFailure("android.not-generated", "Retained products require a locked Android project.")
        }
        let workerEnvironment = try worker?.environment(toolchain: android.toolchain)
        let before = try source(root)
        guard before.lock == identity(validated.bytes) else { throw drift }
        if worker != nil, before.sdkPins != before.platformPins {
            throw MixerFailure("android.output-worker", "The managed Android platform lock must match the admitted SDK lock.")
        }
        let config = try ApplicationConfiguration.load(root)
        let cli = try runningExecutableIdentity()
        if let worker {
            try ProjectBuild.verifyHostSwift(lock: validated.lock, swiftExecutable: worker.hostSwift)
        }
        let store = try standaloneStore ?? NativeBuildOutput.prepare(output: output, root: root, requireSourceIdentity: true)

        let scratch = try context.makeInputSnapshot()
        defer { scratch.removeIfUnheld() }
        let staging = scratch.directory.appendingPathComponent("android-build", isDirectory: true)
        let environment = try buildEnvironment(in: scratch.directory, worker: workerEnvironment)
        let command = [worker?.python ?? "python3", "-I", "-B", "-S", root.appendingPathComponent(driver).path,
                       "build-retained-v1", root.path, staging.path]
        let result = try ProcessRunner.run(command, at: root, environment: environment, policy: .developmentBuild,
                                           context: context, retaining: scratch.retainedInputDirectories)
        guard result.succeeded else {
            throw MixerFailure("android.output-build", "Android build exited \(result.exitCode).\n\(result.output.suffix(8_192))")
        }

        let stagingFD = open(staging.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard stagingFD >= 0 else { throw invalid }
        defer { close(stagingFD) }
        let captured = try JSONDecoder().decode(DriverReceipt.self,
            from: read("build-receipt.json", in: stagingFD, maximum: 4 * 1_048_576))
        let after = try source(root)
        let apkName = config.name + "-unsigned.apk"
        guard before == after, cli == (try runningExecutableIdentity()),
              captured.sourceTreeSha256 == captured.sourceTreeAfterSha256,
              captured.platformDependencyLock.path == platformPins,
              captured.platformDependencyLock.sha256 == before.platformPins.sha256,
              captured.platformDependencyLock.bytes == before.platformPins.sizeBytes else { throw drift }
        let apkIdentity = captured.apkIdentity
        let host = AndroidPublicHost.RetainedSelection(config.androidHost)
        let isPublic = config.androidHost?.isPublic == true
        let expectedActivity = isPublic ? config.application + ".androidhost.PublicActivity" : "dev.mixer.android.MixerActivity"
        guard captured.schemaVersion == 2, captured.qualification == "local-unsigned-cross-build-only",
              captured.apk == staging.appendingPathComponent(apkName).path, captured.application == config.application,
              apkIdentity.application == config.application,
              apkIdentity.activity == expectedActivity, apkIdentity.activity == captured.activity,
              apkIdentity.abi == android.toolchain.abi,
              apkIdentity.minAPI == captured.applicationMinApi,
              apkIdentity.minAPI >= max(host.minimumAPI, android.toolchain.min_api),
              apkIdentity.minAPI <= apkIdentity.targetAPI, apkIdentity.targetAPI == android.toolchain.target_api,
              captured.androidHost == host.rawValue, captured.toolchain == android.toolchain,
              captured.sourceProfile == android.profile, captured.sdkDigest == validated.lock.sdkDigest,
              captured.adapterDigest == android.adapterDigest, !captured.commands.isEmpty,
              captured.commands.allSatisfy({ $0.exitCode == 0 && !$0.command.isEmpty }) else { throw invalid }

        let binding = Binding(sourceBefore: before, sourceAfter: after,
            driverSourceBeforeSHA256: captured.sourceTreeSha256, driverSourceAfterSHA256: captured.sourceTreeAfterSha256,
            validatedLock: validated.lock, cliExecutable: cli, command: result.command,
            toolCommands: captured.commands.map(\.command), environment: environment)
        let inventory = Inventory(formatVersion: 1, bindingSHA256: SourceDigest.sha256(try JSONFile.data(binding)),
            apkSHA256: captured.apkSha256, debugSymbolsSHA256: captured.symbolsSha256,
            application: apkIdentity.application, androidHost: captured.androidHost,
            activity: apkIdentity.activity, abi: apkIdentity.abi, minAPI: apkIdentity.minAPI,
            targetAPI: apkIdentity.targetAPI, entries: captured.apkEntries,
            nativeDependencies: captured.nativeDependencies, debugProducts: captured.debugProducts)
        try validate(inventory, binding: binding)
        let apk = try read(apkName, in: stagingFD)
        let debug = try read("debug-symbols.zip", in: stagingFD)
        guard identity(apk) == FileIdentity(sha256: captured.apkSha256, sizeBytes: captured.apkBytes),
              identity(debug) == FileIdentity(sha256: captured.symbolsSha256, sizeBytes: captured.symbolsBytes)
        else { throw invalid }

        let storeID = try identity(store)
        let report = try Report(formatVersion: 1, scope: scope, binding: binding,
            unsignedAPK: retain(apk, kind: .unsignedAPK, store: store),
            debugSymbols: retain(debug, kind: .debugSymbols, store: store),
            resourceInventory: retain(JSONFile.data(inventory), kind: .resourceInventory, store: store),
            storeDevice: storeID.st_dev, storeInode: storeID.st_ino)
        guard try source(root) == before else { throw drift }
        try store.persist(report, named: manifest)
        return report
    }

    /// Reopens the private store without executing the project or its tools.
    public static func reopen(store url: URL, root requestedRoot: URL) throws -> Report {
        let root = requestedRoot.resolvingSymlinksInPath().standardizedFileURL
        let store = try NativeBuildOutput.openStore(url)
        let raw = try NativeBuildOutput.readManifest(store: store, named: manifest)
        let report = try JSONDecoder().decode(Report.self, from: raw)
        let storeID = try identity(store)
        guard report.storeDevice == storeID.st_dev, report.storeInode == storeID.st_ino else {
            throw MixerFailure("build.output-store", "Retained Android store identity differs from the original.")
        }
        guard try JSONFile.data(report) == raw, report.formatVersion == 1, report.scope == scope,
              report.unsignedAPK.kind == .unsignedAPK, report.debugSymbols.kind == .debugSymbols,
              report.resourceInventory.kind == .resourceInventory else { throw invalid }
        let current = try source(root)
        guard current == report.binding.sourceBefore, current == report.binding.sourceAfter else { throw drift }
        try AndroidSDKCompatibility.admitProject(root)
        let bytes = try read(report.resourceInventory, store: store)
        let inventory = try JSONDecoder().decode(Inventory.self, from: bytes)
        let bindingSHA256 = SourceDigest.sha256(try JSONFile.data(report.binding))
        guard try JSONFile.data(inventory) == bytes, inventory.apkSHA256 == report.unsignedAPK.sha256,
              inventory.debugSymbolsSHA256 == report.debugSymbols.sha256,
              inventory.bindingSHA256 == bindingSHA256 else { throw invalid }
        try validate(inventory, binding: report.binding)
        _ = try read(report.unsignedAPK, store: store)
        _ = try read(report.debugSymbols, store: store)
        guard try source(root) == current else { throw drift }
        try store.check()
        return report
    }

    private static var invalid: MixerFailure {
        MixerFailure("android.output-product", "Invalid retained Android report or product.")
    }
    private static var drift: MixerFailure {
        MixerFailure("android.output-drift", "Android source, lock, pins, driver or CLI identity differs.")
    }

    private static func validate(_ inventory: Inventory, binding: Binding) throws {
        let paths = inventory.entries.map(\.path)
        let libraries = inventory.debugProducts.map(\.library)
        let prefix = "lib/arm64-v8a/"
        let jni = inventory.androidHost == "legacy-v1" ? "libmixer_android_jni.so" : "libmixer_public_android_jni.so"
        guard inventory.formatVersion == 1, inventory.abi == "arm64-v8a",
              inventory.targetAPI == binding.validatedLock.android?.toolchain.target_api,
              binding.sourceBefore == binding.sourceAfter,
              binding.driverSourceBeforeSHA256 == binding.driverSourceAfterSHA256,
              paths == Array(Set(paths)).sorted(),
              paths.contains("AndroidManifest.xml"), paths.contains("classes.dex"),
              paths.contains("assets/MixerAppearanceV2/descriptor.json"),
              Set(libraries) == [prefix + "libAppAndroid.so", prefix + jni], libraries.count == 2,
              inventory.debugProducts.allSatisfy({ product in
                  paths.contains(product.library) && product.sizeBytes > 0 &&
                  product.debugPath == "arm64-v8a/" + product.library.dropFirst(prefix.count) + ".debug"
              }) else { throw invalid }
    }

    private static func source(_ root: URL) throws -> Source {
        try Source(treeSHA256: SourceDigest.exportFingerprint(root),
                   lock: identity(file: root.appendingPathComponent("mixer.lock")),
                   sdkPins: identity(file: root.appendingPathComponent(sdkPins)),
                   platformPins: identity(file: root.appendingPathComponent(platformPins)),
                   generatedDriver: identity(file: root.appendingPathComponent(driver)))
    }

    private static func identity(_ data: Data) -> FileIdentity {
        FileIdentity(sha256: SourceDigest.sha256(data), sizeBytes: UInt64(data.count))
    }
    private static func identity(file: URL, maximum: Int = 1_048_576) throws -> FileIdentity {
        try identity(read(file.path, in: AT_FDCWD, maximum: maximum))
    }
    private static func runningExecutableIdentity() throws -> FileIdentity {
        func executablePath() throws -> String {
            var bytes = [CChar](repeating: 0, count: 4 * Int(MAXPATHLEN))
            let count = proc_pidpath(getpid(), &bytes, UInt32(bytes.count))
            guard count > 0, count < bytes.count, let path = bytes.withUnsafeBufferPointer({
                $0.baseAddress.flatMap { String(validatingCString: $0) }
            }), path.hasPrefix("/") else { throw drift }
            return path
        }

        let path = try executablePath()
        let fd = open(path, O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw drift }
        defer { close(fd) }
        // The executable's path can now name a replacement. The main Mach-O
        // mapping identifies the vnode from which this process actually runs.
        var mapped = proc_regionwithpathinfo()
        let mappedSize = Int32(MemoryLayout.size(ofValue: mapped))
        var held = stat()
        guard let header = mx_executable_header(),
              proc_pidinfo(getpid(), PROC_PIDREGIONPATHINFO, UInt64(UInt(bitPattern: header)),
                           &mapped, mappedSize) == mappedSize,
              fstat(fd, &held) == 0,
              UInt32(bitPattern: held.st_dev) == mapped.prp_vip.vip_vi.vi_stat.vst_dev,
              held.st_ino == mapped.prp_vip.vip_vi.vi_stat.vst_ino else { throw drift }

        let bytes = try NativeProductCapture.regular(fd)
        var named = stat()
        guard try executablePath() == path, lstat(path, &named) == 0,
              held.st_dev == named.st_dev, held.st_ino == named.st_ino else { throw drift }
        return identity(bytes)
    }
    private static func identity(_ store: NativeBuildOutput.Store) throws -> stat {
        try store.check()
        var info = stat()
        guard fstat(store.fd, &info) == 0 else { throw invalid }
        return info
    }
    private static func read(_ name: String, in directory: Int32,
                             maximum: Int = NativeProductCapture.archiveByteLimit) throws -> Data {
        let fd = openat(directory, name, O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw invalid }
        defer { close(fd) }
        return try NativeProductCapture.regular(fd, maximum: maximum)
    }
    private static func read(_ product: Product, store: NativeBuildOutput.Store) throws -> Data {
        try NativeProductCapture.readContent(sha256: product.sha256, size: product.sizeBytes,
            path: product.ownedPath, store: store.url, fd: store.fd)
    }
    private static func retain(_ data: Data, kind: Kind, store: NativeBuildOutput.Store) throws -> Product {
        try store.check()
        let item = try NativeProductCapture.retainContent(data, store: store.url, fd: store.fd)
        return Product(kind: kind, sha256: item.sha256, sizeBytes: item.size, ownedPath: item.path)
    }

    private static func buildEnvironment(in scratch: URL, worker: [String: String]?) throws -> [String: String] {
        let initial = ProcessInfo.processInfo.environment
        let keys = ["PATH", "DEVELOPER_DIR", "ANDROID_HOME", "ANDROID_SDK_ROOT", "MIXER_JDK", "MIXER_SWIFT",
                    "MIXER_SWIFT_SDKS_PATH", "MIXER_ANDROID_ARTIFACT_PATH"]
        var environment = worker ?? initial.filter { keys.contains($0.key) }
        if worker == nil {
            let toolsHome = FileManager.default.homeDirectoryForCurrentUser
            environment["MIXER_SWIFT"] = initial["MIXER_SWIFT"] ?? toolsHome
                .appendingPathComponent("Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift").path
            environment["MIXER_SWIFT_SDKS_PATH"] = initial["MIXER_SWIFT_SDKS_PATH"] ?? toolsHome
                .appendingPathComponent(".swiftpm/swift-sdks").path
            environment["PATH"] = initial["PATH"] ?? "/usr/bin:/bin:/usr/sbin:/sbin"
        }
        let privateDirectories = worker == nil ? ["home", "tmp"] : ["home", "tmp", "module-cache"]
        for name in privateDirectories {
            try FileManager.default.createDirectory(at: scratch.appendingPathComponent(name), withIntermediateDirectories: false,
                                                    attributes: [.posixPermissions: 0o700])
        }
        environment["HOME"] = scratch.appendingPathComponent("home").path
        environment["CFFIXED_USER_HOME"] = environment["HOME"]
        environment["TMPDIR"] = scratch.appendingPathComponent("tmp").path
        if worker != nil {
            environment["CLANG_MODULE_CACHE_PATH"] = scratch.appendingPathComponent("module-cache").path
            environment["SWIFTPM_MODULECACHE_OVERRIDE"] = environment["CLANG_MODULE_CACHE_PATH"]
        }
        environment["LANG"] = "C"
        environment["LC_ALL"] = "C"
        environment["GIT_CONFIG_NOSYSTEM"] = "1"
        environment["GIT_CONFIG_GLOBAL"] = "/dev/null"
        environment["GIT_TERMINAL_PROMPT"] = "0"
        return environment
    }
}

private struct WorkerProfile {
    private static let profileKey = "MIXER_WORKER_NATIVE_PROFILE"
    private static let pythonKey = "MIXER_WORKER_ANDROID_PYTHON"
    private static let hostSwiftKey = "MIXER_WORKER_ANDROID_HOST_SWIFT"
    private static let developerKey = "MIXER_WORKER_ANDROID_DEVELOPER_DIR"
    private static let mirrors = [
        (key: "MIXER_WORKER_ANDROID_SWIFT_ASN1_MIRROR", repository: "swift-asn1.git"),
        (key: "MIXER_WORKER_ANDROID_SWIFT_CRYPTO_MIRROR", repository: "swift-crypto.git")
    ]
    let python: String
    let hostSwift: String
    private let developerDirectory: URL
    private let mirrorURIs: [String]

    private static func refusal(_ reason: String) -> MixerFailure {
        MixerFailure("android.output-worker", reason)
    }

    static func load(root: URL, output: URL, context: ProcessExecutionContext) throws -> Self? {
        let env = ProcessInfo.processInfo.environment
        let control = env["MIXER_WORKER_COMMAND_CONTROL"]
        let fields = [profileKey, pythonKey, hostSwiftKey, developerKey] + mirrors.map(\.key)
        if control == nil, fields.allSatisfy({ env[$0] == nil }) { return nil }
        guard control == "1", env[profileKey] == "unsigned-android-local-v1" else {
            throw refusal("Managed Android output requires the unsigned-android-local-v1 worker profile.")
        }
        guard let python = env[pythonKey], path(python) != nil else {
            throw refusal("Managed Android output requires an absolute Python executable.")
        }
        guard let hostSwift = env[hostSwiftKey], path(hostSwift) != nil, access(hostSwift, X_OK) == 0 else {
            throw refusal("Managed Android output requires an absolute host Swift executable.")
        }
        guard let developerDirectory = path(env[developerKey]),
              entry("usr/bin/xcodebuild", in: developerDirectory, type: S_IFREG) else {
            throw refusal("Managed Android output requires an absolute Xcode developer directory.")
        }
        let tmp = context.receiptDirectory.deletingLastPathComponent().path
        var tmpInfo = stat()
        guard env["TMPDIR"] == tmp, lstat(tmp, &tmpInfo) == 0,
              tmpInfo.st_mode == S_IFDIR | 0o700, tmpInfo.st_uid == geteuid() else {
            throw refusal("Managed Android output requires a canonical, private worker TMPDIR.")
        }
        var identities: [stat] = []
        let uris = try mirrors.map { mirror in
            guard let uri = env[mirror.key], let url = mirrorPath(uri), url.lastPathComponent == mirror.repository,
                  [root.path, output.standardizedFileURL.path, tmp].allSatisfy({ !overlap(url.path, $0) }) else {
                throw refusal("Invalid local Android dependency mirror in \(mirror.key).")
            }
            var info = stat()
            guard lstat(url.path, &info) == 0, info.st_mode & S_IFMT == S_IFDIR,
                  !identities.contains(where: { $0.st_dev == info.st_dev && $0.st_ino == info.st_ino }),
                  entry("HEAD", in: url, type: S_IFREG), entry("config", in: url, type: S_IFREG),
                  entry("objects", in: url, type: S_IFDIR), entry("refs", in: url, type: S_IFDIR) else {
                throw refusal("Expected a distinct bare Git mirror in \(mirror.key).")
            }
            identities.append(info)
            return uri
        }
        return Self(python: python, hostSwift: hostSwift, developerDirectory: developerDirectory, mirrorURIs: uris)
    }

    func environment(toolchain: AndroidToolchainIdentity) throws -> [String: String] {
        guard let pin = toolchain.tools["python"], pin.path == python,
              let actual = try? VerificationFile.tool(python), actual.path == python, actual.sha256 == pin.sha256 else {
            throw Self.refusal("Worker Python differs from the Android toolchain lock.")
        }
        // The worker admits the complete lock before forwarding this profile.
        guard let swift = Self.path(toolchain.tools["swift"]?.path),
              let sdks = Self.path(toolchain.sdk_search_path),
              let sdkMetadata = Self.path(toolchain.metadata["swift_sdk"]?.path),
              let jdk = Self.path(toolchain.distributions["jdk"]?.path),
              let buildTools = Self.path(toolchain.distributions["android_build_tools"]?.path) else {
            throw Self.refusal("Managed Android tool locations must be absolute, locked paths.")
        }
        var env = [
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "DEVELOPER_DIR": developerDirectory.path,
            "MIXER_SWIFT": swift.path, "MIXER_SWIFT_SDKS_PATH": sdks.path, "MIXER_JDK": jdk.path,
            "MIXER_ANDROID_ARTIFACT_PATH": sdkMetadata.deletingLastPathComponent().path,
            "ANDROID_HOME": buildTools.deletingLastPathComponent().deletingLastPathComponent().path,
            "GIT_ALLOW_PROTOCOL": "file", "GIT_NO_REPLACE_OBJECTS": "1", "GIT_CONFIG_COUNT": "2"
        ]
        for (index, mirror) in Self.mirrors.enumerated() {
            env["GIT_CONFIG_KEY_\(index)"] = "url.\(mirrorURIs[index]).insteadOf"
            env["GIT_CONFIG_VALUE_\(index)"] = "https://github.com/apple/\(mirror.repository)"
        }
        return env
    }

    private static func path(_ value: String?) -> URL? {
        guard let value, value.hasPrefix("/"), value != "/",
              value.rangeOfCharacter(from: .controlCharacters) == nil else { return nil }
        let url = URL(fileURLWithPath: value)
        return value == url.standardizedFileURL.path ? url : nil
    }

    private static func mirrorPath(_ uri: String) -> URL? {
        guard uri.hasPrefix("file:///"), let parts = URLComponents(string: uri),
              parts.query == nil, parts.fragment == nil,
              parts.percentEncodedPath == String(uri.dropFirst("file://".count)),
              let url = path(parts.percentEncodedPath.removingPercentEncoding),
              url.path == url.resolvingSymlinksInPath().path else { return nil }
        return url
    }

    private static func overlap(_ lhs: String, _ rhs: String) -> Bool {
        lhs == rhs || lhs.hasPrefix(rhs + "/") || rhs.hasPrefix(lhs + "/")
    }

    private static func entry(_ name: String, in directory: URL, type: mode_t) -> Bool {
        var info = stat()
        return lstat(directory.appendingPathComponent(name).path, &info) == 0 && info.st_mode & S_IFMT == type
    }
}
