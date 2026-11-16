import Foundation
import Darwin

/// Two retained native products from one unsigned local iOS Simulator build.
public enum NativeBuildOutput {
    public struct Binding: Codable, Sendable {
        public let authoritativeSourceDigest: String
        public let lockSHA256: String
        public let lock: ToolchainLock
        public let sdkDigest: String
        public let compilerSourceDigest: String
        public let cliExecutableSHA256: String
        public let command: [String]
        public let environment: [String: String]
    }
    public struct Report: Codable, Sendable {
        public let commandResult: CommandResult
        public let nativeProduct: NativeProductCapture.Result?
        public let binding: Binding
        public let scope: String
        public var succeeded: Bool { commandResult.succeeded && nativeProduct != nil }
    }

    final class Store {
        let url: URL
        let fd: Int32
        init(url: URL, fd: Int32) { self.url = url; self.fd = fd }
        deinit { close(fd) }
        func check() throws {
            var held = stat(), named = stat()
            guard fstat(fd, &held) == 0, lstat(url.path, &named) == 0,
                  held.st_dev == named.st_dev, held.st_ino == named.st_ino,
                  named.st_mode & S_IFMT == S_IFDIR,
                  named.st_mode & 0o7777 == 0o700, named.st_uid == getuid()
            else { throw MixerFailure("build.output-store", "Private output store identity changed.") }
        }
        func persist(_ report: Report) throws {
            try check()
            let bytes = try JSONFile.data(report)
            let file = openat(fd, "native-build.json", O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
            guard file >= 0 else { throw MixerFailure("build.output-manifest", "Cannot exclusively create native manifest.") }
            defer { close(file) }
            try bytes.withUnsafeBytes { raw in
                var offset = 0
                while offset < raw.count {
                    let count = Darwin.write(file, raw.baseAddress!.advanced(by: offset), raw.count - offset)
                    if count < 0 && errno == EINTR { continue }
                    guard count > 0 else { throw MixerFailure("build.output-manifest", "Manifest write failed.") }
                    offset += count
                }
            }
            guard fchmod(file, 0o444) == 0, fsync(file) == 0, fsync(fd) == 0
            else { throw MixerFailure("build.output-manifest", "Manifest durability failed.") }
            try check()
        }
    }

    /// Admission precedes tool inspection, generation, and compilation.
    static func prepare(output: URL, root: URL) throws -> Store {
        let output = output.standardizedFileURL
        guard output.path != root.standardizedFileURL.path,
              !output.path.hasPrefix(root.standardizedFileURL.path + "/"),
              !output.path.utf8.contains(0), output.path != "/"
        else { throw MixerFailure("build.output-path", "Output must be a new private store outside the source project.") }
        let parts = output.path.split(separator: "/").map(String.init)
        var parent = open("/", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard parent >= 0 else { throw MixerFailure("build.output-path", "Cannot open output ancestors.") }
        defer { close(parent) }
        for part in parts.dropLast() {
            let next = openat(parent, part, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard next >= 0 else { throw MixerFailure("build.output-path", "Output ancestors must be existing real directories.") }
            var info = stat()
            guard fstat(next, &info) == 0, info.st_mode & 0o022 == 0,
                  info.st_uid == 0 || info.st_uid == getuid()
            else { close(next); throw MixerFailure("build.output-path", "Unsafe output ancestor ownership or mode.") }
            close(parent); parent = next
        }
        var info = stat()
        guard fstat(parent, &info) == 0, info.st_uid == getuid(), info.st_mode & 0o7777 == 0o700
        else { throw MixerFailure("build.output-private", "Output parent must be owned by this user with mode 0700.") }
        guard let name = parts.last, mkdirat(parent, name, 0o700) == 0
        else { throw MixerFailure("build.output-exists", "Output must not already exist.") }
        let fd = openat(parent, parts.last!, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw MixerFailure("build.output-store", "Cannot open newly owned store.") }
        let store = Store(url: output, fd: fd)
        try store.check()
        return store
    }

    static func build(root: URL, store: Store, lock: ToolchainLock,
                      command: [String], app: URL, symbols: URL) throws -> Report {
        let keys: Set<String> = ["PATH", "DEVELOPER_DIR", "TMPDIR", "CFFIXED_USER_HOME",
            "CLANG_MODULE_CACHE_PATH", "SWIFTPM_MODULECACHE_OVERRIDE", "LANG", "LC_ALL"]
        let environment = ProcessInfo.processInfo.environment.filter { keys.contains($0.key) }
        let compilerSources = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let executable = URL(fileURLWithPath: CommandLine.arguments[0])
        func bind() throws -> Binding {
            let lockBytes = try Data(contentsOf: root.appendingPathComponent("mixer.lock"))
            let currentLock = try JSONDecoder().decode(ToolchainLock.self, from: lockBytes)
            let sdk = try SourceDigest.tree(root.appendingPathComponent("Generated/MixerSDK"))
            guard try JSONFile.data(lock) == JSONFile.data(currentLock), sdk == lock.sdkDigest
            else { throw MixerFailure("build.output-binding", "Lock or SDK changed.") }
            return Binding(authoritativeSourceDigest: try SourceDigest.tree(root),
                lockSHA256: SourceDigest.sha256(lockBytes), lock: currentLock, sdkDigest: sdk,
                compilerSourceDigest: try SourceDigest.tree(compilerSources),
                cliExecutableSHA256: SourceDigest.sha256(try Data(contentsOf: executable)),
                command: command, environment: environment)
        }
        try store.check()
        let before = try bind()
        let beforeBytes = try JSONFile.data(before)
        let actual = try ProcessRunner.run(command, at: root, environment: environment, policy: .developmentBuild)
        // ProcessRunner returns only after its terminal-custody contract; UNKNOWN throws.
        guard actual.succeeded else {
            let report = Report(commandResult: actual, nativeProduct: nil, binding: before,
                                scope: "unsigned-simulator/local-development")
            try store.persist(report)
            return report
        }
        guard try beforeBytes == JSONFile.data(bind())
        else { throw MixerFailure("build.output-drift", "Source, lock, SDK, CLI or compiler recipe changed during the build.") }
        try store.check()
        let products = try NativeProductCapture.capture(app: app, dSYM: symbols, store: store.url,
            bindingSHA256: SourceDigest.sha256(beforeBytes))
        guard try beforeBytes == JSONFile.data(bind())
        else { throw MixerFailure("build.output-drift", "Inputs changed during native capture.") }
        let report = Report(commandResult: actual, nativeProduct: products, binding: before,
                            scope: "unsigned-simulator/local-development")
        try store.persist(report)
        return report
    }

    // Match retained-object admission, using the opened store and file identities.
    private static func readManifest(store url: URL) throws -> Data {
        guard url.isFileURL, url.path == url.standardizedFileURL.path,
              !url.path.utf8.contains(0), url.path != "/"
        else { throw MixerFailure("build.output-path", "Invalid native store path.") }
        let parts = url.path.split(separator: "/").map(String.init)
        var directory = open("/", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard directory >= 0 else { throw MixerFailure("build.output-path", "Cannot open native store ancestors.") }
        do {
            for part in parts {
                let next = openat(directory, part, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
                guard next >= 0 else { throw MixerFailure("build.output-path", "Native store ancestors must be real directories.") }
                var info = stat()
                guard fstat(next, &info) == 0, info.st_mode & 0o022 == 0,
                      info.st_uid == 0 || info.st_uid == geteuid()
                else { close(next); throw MixerFailure("build.output-path", "Unsafe native store ancestor.") }
                close(directory); directory = next
            }
        } catch { close(directory); throw error }
        let store = Store(url: url, fd: directory)
        try store.check()
        let file = openat(store.fd, "native-build.json", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)
        guard file >= 0 else { throw MixerFailure("build.output-manifest", "Cannot open regular non-symlink native manifest.") }
        defer { close(file) }
        let maximum = 8 * 1_048_576
        var before = stat()
        guard fstat(file, &before) == 0, before.st_mode & S_IFMT == S_IFREG,
              before.st_mode & 0o7777 == 0o444, before.st_uid == geteuid(),
              before.st_nlink == 1, before.st_size >= 0, before.st_size <= maximum
        else { throw MixerFailure("build.output-manifest", "Native manifest must be owned, single-link, bounded and mode 0444.") }
        var bytes = Data()
        var chunk = [UInt8](repeating: 0, count: 65_536)
        while true {
            let count = Darwin.read(file, &chunk, min(chunk.count, maximum - bytes.count + 1))
            if count < 0 && errno == EINTR { continue }
            guard count >= 0, count <= maximum - bytes.count
            else { throw MixerFailure("build.output-manifest", "Native manifest read failed or exceeded its bound.") }
            if count == 0 { break }
            bytes.append(contentsOf: chunk.prefix(count))
        }
        func unchanged(_ a: stat, _ b: stat) -> Bool {
            a.st_dev == b.st_dev && a.st_ino == b.st_ino && a.st_mode == b.st_mode &&
            a.st_uid == b.st_uid && a.st_nlink == b.st_nlink && a.st_size == b.st_size &&
            a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec && a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
            a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec && a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec
        }
        var after = stat(), named = stat()
        guard fstat(file, &after) == 0,
              fstatat(store.fd, "native-build.json", &named, AT_SYMLINK_NOFOLLOW) == 0,
              unchanged(before, after), unchanged(after, named), bytes.count == before.st_size
        else { throw MixerFailure("build.output-manifest", "Native manifest identity changed during read.") }
        try store.check()
        return bytes
    }


    public static func reopen(store: URL) throws -> Report {
        let report = try JSONDecoder().decode(Report.self, from: readManifest(store: store))
        guard report.scope == "unsigned-simulator/local-development", report.commandResult.succeeded,
              let products = report.nativeProduct
        else { throw MixerFailure("build.output-incomplete", "Manifest does not describe retained native products.") }
        try NativeProductCapture.revalidate(products, store: store,
            expectedBindingSHA256: SourceDigest.sha256(try JSONFile.data(report.binding)))
        return report
    }
}
