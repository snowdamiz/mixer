import Foundation
import CryptoKit
import Darwin

/// Retained input bytes for a verified subset of one existing public build.
/// This capture is not another native build or an additional output role.
public enum BuildInputSnapshot {
    public enum Role: String, Codable, CaseIterable, Sendable { case project, compiler, sdk, cli, lock }
    public struct Material: Codable, Equatable, Sendable {
        public let role: Role
        public let logicalPath: String
        public let sha256: String
        public let sha1: String
        public let sizeBytes: UInt64
        public var objectPath: String { "objects/" + sha256 }
        public var mirrorPath: String { "materials/" + role.rawValue + "/" + logicalPath }
    }
    public struct Inputs: Sendable {
        public let projectRoot: URL
        public let compilerRoot: URL
        public let sdkRoot: URL
        public let cliBinary: URL
        public let lockFile: URL
        public init(projectRoot: URL, compilerRoot: URL, sdkRoot: URL, cliBinary: URL, lockFile: URL) {
            self.projectRoot = projectRoot; self.compilerRoot = compilerRoot; self.sdkRoot = sdkRoot
            self.cliBinary = cliBinary; self.lockFile = lockFile
        }
    }
    public struct Report: Codable, Sendable {
        public let version: Int
        public let completeness: String
        public let gaps: [String]
        public let originalParent: NativeBuildOutput.Report
        public let originalParentSHA256: String
        public let retainedParentSHA256: String
        public let bindingSHA256: String
        public let materials: [Material]
    }
    public struct Descriptor: Codable, Equatable, Sendable {
        public let sha256: String
        public let sizeBytes: UInt64
    }
    public struct RetainedMaterial: Codable, Sendable {
        public let logicalPath: String
        public let path: String
        public let sha256: String
        public let sizeBytes: UInt64
    }
    public enum Failure: Error, Equatable { case path, unsafeFile, mutation, limit, binding, roster, corrupt, incomplete, io(Int32) }
    public static let gaps = ["entire-toolchain-and-standard-library-link-closure-not-established",
        "platform-component-identities-not-established", "licenses-not-determined"]
    private static let fileLimit = 64 * 1024 * 1024
    private static let totalLimit = 256 * 1024 * 1024
    private static let entryLimit = 10000

    public static func requireAggregateEligible(_ descriptor: Descriptor) throws { throw Failure.incomplete }

    public static func produce(inputs: Inputs, parentStore: URL, output: URL) throws -> Descriptor {
        let output = output.standardizedFileURL
        let parent = try NativeBuildOutput.reopen(store: parentStore)
        guard parent.formatVersion == 2, parent.binding.resourceInventoryPolicy == .retainedAppFilesV1,
              parent.succeeded, parent.resourceInventory != nil else { throw Failure.binding }
        let roots = [inputs.projectRoot, inputs.compilerRoot, inputs.sdkRoot, parentStore,
                     inputs.cliBinary.deletingLastPathComponent(), inputs.lockFile.deletingLastPathComponent()]
        for root in roots {
            let fd = try directory(root); close(fd)
            guard output.path != root.path, !output.path.hasPrefix(root.path + "/"),
                  !root.path.hasPrefix(output.path + "/") else { throw Failure.path }
        }
        let store = try NativeBuildOutput.prepare(output: output, root: inputs.projectRoot)
        let materialRoot = output.appendingPathComponent("materials")
        try mkdirOwned(materialRoot); try mkdirOwned(output.appendingPathComponent("objects"))
        var materials: [Material] = []
        var total = 0
        var objects = Set<String>()
        func retain(_ role: Role, _ logical: String, _ bytes: Data) throws {
            guard relative(logical), materials.count < entryLimit, bytes.count <= fileLimit,
                  total <= totalLimit - bytes.count else { throw Failure.limit }
            total += bytes.count
            let material = Material(role: role, logicalPath: logical, sha256: SourceDigest.sha256(bytes),
                sha1: Insecure.SHA1.hash(data: bytes).map { String(format: "%02x", $0) }.joined(), sizeBytes: UInt64(bytes.count))
            try makeParents(output.appendingPathComponent(material.mirrorPath).deletingLastPathComponent(), beneath: output)
            try write(bytes, to: output.appendingPathComponent(material.mirrorPath))
            if objects.insert(material.sha256).inserted { try write(bytes, to: output.appendingPathComponent(material.objectPath)) }
            materials.append(material)
        }
        for (role, root, expected) in [(Role.project, inputs.projectRoot, parent.binding.authoritativeSourceDigest),
            (.compiler, inputs.compilerRoot, parent.binding.compilerSourceDigest), (.sdk, inputs.sdkRoot, parent.binding.sdkDigest)] {
            let before = try SourceDigest.files(in: root)
            guard before.count <= entryLimit else { throw Failure.limit }
            for file in before {
                let logical = String(file.path.dropFirst(root.path.count + 1))
                try retain(role, logical, read(file))
            }
            // The closed retained roster, rather than only before/after live reads, must reproduce the parent digest.
            guard try SourceDigest.tree(materialRoot.appendingPathComponent(role.rawValue)) == expected,
                  try SourceDigest.files(in: root) == before else { throw Failure.binding }
            for material in materials where material.role == role {
                guard try SourceDigest.sha256(read(root.appendingPathComponent(material.logicalPath))) == material.sha256 else { throw Failure.mutation }
            }
        }
        let cli = try read(inputs.cliBinary), lock = try read(inputs.lockFile)
        guard SourceDigest.sha256(cli) == parent.binding.cliExecutableSHA256,
              SourceDigest.sha256(lock) == parent.binding.lockSHA256,
              try JSONFile.data(JSONDecoder().decode(ToolchainLock.self, from: lock)) == JSONFile.data(parent.binding.lock)
        else { throw Failure.binding }
        try retain(.cli, "mixer", cli); try retain(.lock, "mixer.lock", lock)
        let retained = try copyParents(parent, from: parentStore, to: output.appendingPathComponent("parents"), root: inputs.projectRoot)
        guard try JSONFile.data(NativeBuildOutput.reopen(store: parentStore)) == JSONFile.data(parent),
              try read(inputs.cliBinary) == cli, try read(inputs.lockFile) == lock else { throw Failure.mutation }
        let report = Report(version: 1, completeness: "verified_subset", gaps: gaps, originalParent: parent,
            originalParentSHA256: SourceDigest.sha256(try JSONFile.data(parent)),
            retainedParentSHA256: SourceDigest.sha256(try JSONFile.data(retained)),
            bindingSHA256: SourceDigest.sha256(try JSONFile.data(parent.binding)),
            materials: materials.sorted { $0.mirrorPath < $1.mirrorPath })
        let bytes = try JSONFile.data(report)
        try store.check(); try write(bytes, to: output.appendingPathComponent("snapshot.json")); try store.check()
        let descriptor = Descriptor(sha256: SourceDigest.sha256(bytes), sizeBytes: UInt64(bytes.count))
        _ = try reopen(descriptor, store: output)
        return descriptor
    }

    public static func reopen(_ descriptor: Descriptor, store: URL) throws -> Report {
        let fd = try directory(store, privateStore: true); defer { close(fd) }
        let bytes = try read(store.appendingPathComponent("snapshot.json"), immutable: true)
        guard bytes.count == descriptor.sizeBytes, SourceDigest.sha256(bytes) == descriptor.sha256 else { throw Failure.corrupt }
        let report = try JSONDecoder().decode(Report.self, from: bytes)
        guard report.version == 1, report.completeness == "verified_subset", report.gaps == gaps,
              !report.materials.isEmpty, report.materials.count <= entryLimit,
              report.materials.map(\.mirrorPath) == report.materials.map(\.mirrorPath).sorted(),
              Set(report.materials.map(\.mirrorPath)).count == report.materials.count,
              Set(report.materials.map { $0.mirrorPath.lowercased() }).count == report.materials.count,
              Set(report.materials.map(\.role)) == Set(Role.allCases),
              SourceDigest.sha256(try JSONFile.data(report.originalParent)) == report.originalParentSHA256,
              SourceDigest.sha256(try JSONFile.data(report.originalParent.binding)) == report.bindingSHA256
        else { throw Failure.roster }
        let parentStore = store.appendingPathComponent("parents")
        let parent = try NativeBuildOutput.reopen(store: parentStore)
        guard SourceDigest.sha256(try JSONFile.data(parent)) == report.retainedParentSHA256,
              try JSONFile.data(parent) == JSONFile.data(relocate(report.originalParent, to: parentStore)) else { throw Failure.binding }
        var expected: Set<String> = ["snapshot.json", "parents/native-build.json"]
        guard let product = parent.nativeProduct, let inventory = parent.resourceInventory else { throw Failure.binding }
        expected.formUnion(["parents/" + product.nativeBinary.sha256, "parents/" + product.debugSymbols.sha256, "parents/" + inventory.sha256])
        var total = 0
        for material in report.materials {
            guard relative(material.logicalPath), digest(material.sha256, count: 64), digest(material.sha1, count: 40),
                  material.sizeBytes <= fileLimit, total <= totalLimit - Int(material.sizeBytes) else { throw Failure.limit }
            total += Int(material.sizeBytes)
            let object = try read(store.appendingPathComponent(material.objectPath), immutable: true)
            guard object.count == material.sizeBytes, SourceDigest.sha256(object) == material.sha256,
                  Insecure.SHA1.hash(data: object).map({ String(format: "%02x", $0) }).joined() == material.sha1,
                  try read(store.appendingPathComponent(material.mirrorPath), immutable: true) == object else { throw Failure.corrupt }
            expected.formUnion([material.objectPath, material.mirrorPath])
        }
        for (role, digest) in [(Role.project, parent.binding.authoritativeSourceDigest),
            (.compiler, parent.binding.compilerSourceDigest), (.sdk, parent.binding.sdkDigest)] {
            guard try SourceDigest.tree(store.appendingPathComponent("materials/" + role.rawValue)) == digest else { throw Failure.binding }
        }
        guard report.materials.filter({ $0.role == .cli }).count == 1,
              report.materials.contains(where: { $0.role == .cli && $0.logicalPath == "mixer" && $0.sha256 == parent.binding.cliExecutableSHA256 }),
              report.materials.filter({ $0.role == .lock }).count == 1,
              report.materials.contains(where: { $0.role == .lock && $0.logicalPath == "mixer.lock" && $0.sha256 == parent.binding.lockSHA256 }) else { throw Failure.binding }
        var allowed = expected
        for path in expected {
            var pieces = path.split(separator: "/"); pieces.removeLast()
            while !pieces.isEmpty { allowed.insert(pieces.joined(separator: "/")); pieces.removeLast() }
        }
        guard try roster(store) == allowed else { throw Failure.roster }
        return report
    }

    /// Same logicalPath/path/size/SHA256 record shape used by the reviewed SBOM and provenance producers.
    public static func retainedMaterials(_ descriptor: Descriptor, store: URL) throws -> [RetainedMaterial] {
        try reopen(descriptor, store: store).materials.map {
            RetainedMaterial(logicalPath: $0.role.rawValue + "/" + $0.logicalPath,
                path: store.appendingPathComponent($0.mirrorPath).path, sha256: $0.sha256, sizeBytes: $0.sizeBytes)
        }
    }

    private static func relocate(_ p: NativeBuildOutput.Report, to store: URL) throws -> NativeBuildOutput.Report {
        guard let c = p.nativeProduct, let i = p.resourceInventory else { throw Failure.binding }
        func descriptor(_ d: NativeProductCapture.Descriptor) -> NativeProductCapture.Descriptor {
            .init(kind: d.kind, sha256: d.sha256, sizeBytes: d.sizeBytes, ownedPath: store.path + "/" + d.sha256)
        }
        let capture = NativeProductCapture.Result(nativeBinary: descriptor(c.nativeBinary), debugSymbols: descriptor(c.debugSymbols),
            bindingSHA256: c.bindingSHA256, executable: c.executable, uuid: c.uuid, binarySignature: c.binarySignature,
            dependencies: c.dependencies, appFiles: c.appFiles, symbolFiles: c.symbolFiles)
        return .init(commandResult: p.commandResult, nativeProduct: capture, binding: p.binding, scope: p.scope,
            formatVersion: p.formatVersion, resourceInventory: .init(kind: i.kind, sha256: i.sha256, sizeBytes: i.sizeBytes, ownedPath: store.path + "/" + i.sha256))
    }
    private static func copyParents(_ p: NativeBuildOutput.Report, from source: URL, to target: URL, root: URL) throws -> NativeBuildOutput.Report {
        let store = try NativeBuildOutput.prepare(output: target, root: root)
        guard let c = p.nativeProduct, let i = p.resourceInventory else { throw Failure.binding }
        try retainParentArchive(c.nativeBinary, from: source, in: store)
        try retainParentArchive(c.debugSymbols, from: source, in: store)
        let inventory = try read(source.appendingPathComponent(i.sha256), immutable: true)
        guard inventory.count == i.sizeBytes, SourceDigest.sha256(inventory) == i.sha256 else { throw Failure.corrupt }
        try write(inventory, to: target.appendingPathComponent(i.sha256))
        let relocated = try relocate(p, to: target); try store.persist(relocated)
        return try NativeBuildOutput.reopen(store: target)
    }
    static func retainParentArchive(_ descriptor: NativeProductCapture.Descriptor,
                                    from source: URL, in store: NativeBuildOutput.Store,
                                    renameExclusive: (Int32, String, String) -> Int32 = {
                                        renameatx_np($0, $1, $0, $2, UInt32(RENAME_EXCL))
                                    },
                                    flushDirectory: (Int32) -> Int32 = Darwin.fsync) throws {
        let name = descriptor.sha256
        guard digest(name, count: 64), descriptor.ownedPath == source.path + "/" + name else { throw Failure.path }
        guard descriptor.sizeBytes > 0, descriptor.sizeBytes <= NativeProductCapture.archiveByteLimit else { throw Failure.limit }
        let size = Int(descriptor.sizeBytes)
        let parent = try directory(source, privateStore: true)
        defer { close(parent) }
        let input = openat(parent, name, O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)
        guard input >= 0 else { throw Failure.path }
        defer { close(input) }
        try store.check()

        let stage = ".archive-" + UUID().uuidString
        let output = openat(store.fd, stage, O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard output >= 0 else { throw Failure.io(errno) }
        var ownedName = stage
        var committed = false
        defer {
            // The operation owns this private store. Recheck identity before FD-relative
            // cleanup so an observed replacement or pre-existing digest is left alone.
            if !committed {
                var held = stat(), named = stat()
                if fstat(output, &held) == 0,
                   fstatat(store.fd, ownedName, &named, AT_SYMLINK_NOFOLLOW) == 0,
                   held.st_dev == named.st_dev, held.st_ino == named.st_ino,
                   unlinkat(store.fd, ownedName, 0) == 0 {
                    _ = flushDirectory(store.fd)
                }
            }
            close(output)
        }

        var hash = SHA256()
        try readChunks(input, parent: parent, name: name, maximum: size, immutable: true, expectedSize: size) { chunk in
            hash.update(bufferPointer: chunk)
            try writeAll(chunk, to: output)
        }
        guard hex(hash.finalize()) == name else { throw Failure.corrupt }
        guard fchmod(output, 0o444) == 0, fsync(output) == 0, lseek(output, 0, SEEK_SET) == 0 else { throw Failure.io(errno) }

        var readback = SHA256()
        let verified = try readChunks(output, parent: store.fd, name: stage, maximum: size,
                                      immutable: true, expectedSize: size) {
            readback.update(bufferPointer: $0)
        }
        guard hex(readback.finalize()) == name else { throw Failure.corrupt }

        func namedArchive(_ name: String) throws -> stat {
            var held = stat(), named = stat()
            guard fstat(output, &held) == 0,
                  fstatat(store.fd, name, &named, AT_SYMLINK_NOFOLLOW) == 0,
                  stable(held, named) else { throw Failure.mutation }
            return held
        }

        try store.check()
        guard try stable(verified, namedArchive(stage)) else { throw Failure.mutation }
        guard renameExclusive(store.fd, stage, name) == 0 else { throw Failure.io(errno) }
        ownedName = name

        let published = try namedArchive(name)
        // Rename may advance ctime. The inode and the rest of its verified stamp must match.
        guard stable(verified, published, includingChangeTime: false) else { throw Failure.mutation }
        guard flushDirectory(store.fd) == 0 else { throw Failure.io(errno) }
        try store.check()
        guard try stable(published, namedArchive(name)) else { throw Failure.mutation }
        committed = true
    }

    private static func hex(_ digest: SHA256.Digest) -> String {
        digest.map { String(format: "%02x", $0) }.joined()
    }

    private static func relative(_ s: String) -> Bool {
        !s.isEmpty && !s.hasPrefix("/") && !s.hasSuffix("/") && !s.utf8.contains(0) &&
        s.split(separator: "/", omittingEmptySubsequences: false).count <= 32 &&
        s.split(separator: "/", omittingEmptySubsequences: false).allSatisfy { !$0.isEmpty && $0 != "." && $0 != ".." }
    }
    private static func digest(_ s: String, count: Int) -> Bool {
        s.utf8.count == count && s.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
    private static func directory(_ url: URL, privateStore: Bool = false) throws -> Int32 {
        guard url.isFileURL, url.path == url.standardizedFileURL.path, relative(String(url.path.dropFirst())) else { throw Failure.path }
        var fd = open("/", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw Failure.io(errno) }
        do {
            for part in url.path.split(separator: "/") {
                let next = openat(fd, String(part), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
                guard next >= 0 else { throw Failure.path }; close(fd); fd = next
                var info = stat()
                guard fstat(fd, &info) == 0, info.st_mode & 0o022 == 0,
                      info.st_uid == 0 || info.st_uid == geteuid() else { throw Failure.unsafeFile }
            }
            if privateStore {
                var info = stat()
                guard fstat(fd, &info) == 0, info.st_uid == geteuid(), info.st_mode & 0o7777 == 0o700 else { throw Failure.unsafeFile }
            }
            return fd
        } catch { close(fd); throw error }
    }
    private static func stable(_ a: stat, _ b: stat, includingChangeTime: Bool = true) -> Bool {
        a.st_dev == b.st_dev && a.st_ino == b.st_ino && a.st_mode == b.st_mode && a.st_uid == b.st_uid &&
        a.st_nlink == b.st_nlink && a.st_size == b.st_size && a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec &&
        a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
        (!includingChangeTime || (a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec &&
                                   a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec))
    }
    private static func read(_ url: URL, immutable: Bool = false) throws -> Data {
        let parent = try directory(url.deletingLastPathComponent()); defer { close(parent) }
        guard relative(url.lastPathComponent) else { throw Failure.path }
        let fd = openat(parent, url.lastPathComponent, O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw Failure.path }; defer { close(fd) }
        var data = Data()
        try readChunks(fd, parent: parent, name: url.lastPathComponent, maximum: fileLimit, immutable: immutable) {
            data.append(contentsOf: $0)
        }
        return data
    }

    @discardableResult
    private static func readChunks(_ fd: Int32, parent: Int32, name: String, maximum: Int,
                                   immutable: Bool, expectedSize: Int? = nil,
                                   consume: (UnsafeRawBufferPointer) throws -> Void) throws -> stat {
        var before = stat()
        guard fstat(fd, &before) == 0, before.st_mode & S_IFMT == S_IFREG, before.st_nlink == 1,
              before.st_uid == geteuid(), before.st_size >= 0, before.st_size <= maximum,
              !immutable || before.st_mode & 0o7777 == 0o444 else { throw Failure.unsafeFile }
        if let expectedSize, before.st_size != expectedSize { throw Failure.corrupt }

        var count = 0
        var buffer = [UInt8](repeating: 0, count: 65536)
        while true {
            let n = Darwin.read(fd, &buffer, min(buffer.count, maximum - count + 1))
            if n < 0 && errno == EINTR { continue }
            guard n >= 0, n <= maximum - count else { throw Failure.limit }
            if n == 0 { break }
            try buffer.withUnsafeBytes { try consume(UnsafeRawBufferPointer(rebasing: $0.prefix(n))) }
            count += n
        }
        var after = stat(), named = stat()
        guard fstat(fd, &after) == 0, fstatat(parent, name, &named, AT_SYMLINK_NOFOLLOW) == 0,
              stable(before, after), stable(after, named), count == before.st_size else { throw Failure.mutation }
        return after
    }

    private static func writeAll(_ raw: UnsafeRawBufferPointer, to fd: Int32) throws {
        var offset = 0
        while offset < raw.count {
            let n = Darwin.write(fd, raw.baseAddress!.advanced(by: offset), raw.count - offset)
            if n < 0 && errno == EINTR { continue }
            guard n > 0 else { throw Failure.io(errno) }
            offset += n
        }
    }

    private static func write(_ data: Data, to url: URL) throws {
        let parent = try directory(url.deletingLastPathComponent(), privateStore: true); defer { close(parent) }
        let fd = openat(parent, url.lastPathComponent, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard fd >= 0 else { throw Failure.io(errno) }; defer { close(fd) }
        try data.withUnsafeBytes { try writeAll($0, to: fd) }
        guard fchmod(fd, 0o444) == 0, fsync(fd) == 0, fsync(parent) == 0 else { throw Failure.io(errno) }
    }
    private static func mkdirOwned(_ url: URL) throws {
        guard mkdir(url.path, 0o700) == 0 else { throw Failure.io(errno) }
    }
    private static func makeParents(_ url: URL, beneath root: URL) throws {
        guard url.path.hasPrefix(root.path + "/") else { throw Failure.path }
        var current = root
        for part in url.path.dropFirst(root.path.count + 1).split(separator: "/") {
            current.appendPathComponent(String(part))
            if mkdir(current.path, 0o700) != 0, errno != EEXIST { throw Failure.io(errno) }
            let fd = try directory(current, privateStore: true); close(fd)
        }
    }
    private static func roster(_ root: URL) throws -> Set<String> {
        var result = Set<String>()
        func visit(_ url: URL, prefix: String, depth: Int) throws {
            guard depth <= 32 else { throw Failure.limit }
            let fd = try directory(url, privateStore: true); defer { close(fd) }
            for name in try FileManager.default.contentsOfDirectory(atPath: url.path) {
                guard relative(name), !name.contains("/"), result.count < entryLimit * 4 else { throw Failure.limit }
                let path = prefix + name; var info = stat()
                guard fstatat(fd, name, &info, AT_SYMLINK_NOFOLLOW) == 0 else { throw Failure.path }
                result.insert(path)
                if info.st_mode & S_IFMT == S_IFDIR { try visit(url.appendingPathComponent(name), prefix: path + "/", depth: depth + 1) }
                else if info.st_mode & S_IFMT != S_IFREG { throw Failure.unsafeFile }
            }
        }
        try visit(root, prefix: "", depth: 0); return result
    }

}
