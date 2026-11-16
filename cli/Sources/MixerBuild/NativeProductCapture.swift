import Foundation
import CryptoKit
import Darwin

/// Local, unsigned arm64 iOS Simulator product capture. No process execution or lifecycle writes.
public enum NativeProductCapture {
    public enum Kind: String, Codable, Sendable { case unsignedNativeBinary = "unsigned_native_binary", debugSymbols = "debug_symbols" }

    public struct Descriptor: Codable, Equatable, Sendable {
        public let kind: Kind
        public let sha256: String
        public let sizeBytes: UInt64
        public let ownedPath: String
    }

    public struct Result: Codable, Equatable, Sendable {
        public let nativeBinary: Descriptor
        public let debugSymbols: Descriptor
        public let bindingSHA256: String
        public let executable: String
        public let uuid: String
        public let binarySignature: String
        public let dependencies: [String]
        public let appFiles: Int
        public let symbolFiles: Int
    }

    public enum Failure: Error, Equatable {
        case invalidPath, unsafeFile, mutation, limit, malformedProduct, target, symbols, dependency(String), corruptObject, io(Int32)
    }

    private static let limit = 256 * 1024 * 1024
    private static let magic = Data("MXNATIVE1\n".utf8)
    private struct Entry: Codable, Equatable {
        let path: String
        let mode: UInt32
        let directory: Bool
        let size: Int
        let sha256: String
    }
    private struct Header: Codable {
        let version: Int
        let kind: Kind
        let binding: String
        let entries: [Entry]
    }
    private struct Snapshot: Equatable {
        var entries: [Entry] = []
        var bytes: [String: Data] = [:]
        var sourceStamps: [String: String] = [:]
    }
    private struct Identity: Equatable {
        let uuid: Data
        let fileType: UInt32
        let platform: UInt32?
        let dependencies: [String]
        let dwarf: Bool
        let linkerAdHoc: Bool
    }

    /// Producer inputs must be frozen and their command custody terminal before entry.
    /// The store must already exist, be private (0700), and have exactly one writer.
    public static func capture(app: URL, dSYM: URL, store: URL, bindingSHA256: String) throws -> Result {
        guard digestString(bindingSHA256) else { throw Failure.malformedProduct }
        let appSnapshot = try snapshot(app)
        let symbols = try snapshot(dSYM)
        let product = try validate(app: appSnapshot, symbols: symbols)
        let native = try retain(archive(appSnapshot, kind: .unsignedNativeBinary, binding: bindingSHA256), kind: .unsignedNativeBinary, store: store)
        let debug = try retain(archive(symbols, kind: .debugSymbols, binding: bindingSHA256), kind: .debugSymbols, store: store)
        // A second complete read detects replacement, additions, removals and content changes.
        guard try snapshot(app) == appSnapshot, try snapshot(dSYM) == symbols else { throw Failure.mutation }
        let result = Result(nativeBinary: native, debugSymbols: debug, bindingSHA256: bindingSHA256,
            executable: product.0, uuid: hex(product.1.uuid), binarySignature: product.1.linkerAdHoc ? "linker-ad-hoc-no-signing-identity" : "absent", dependencies: product.1.dependencies,
            appFiles: appSnapshot.bytes.count, symbolFiles: symbols.bytes.count)
        try revalidate(result, store: store, expectedBindingSHA256: bindingSHA256)
        return result
    }

    /// Reopens both objects, validates all retained bytes, and repeats product/symbol identity checks.
    public static func revalidate(_ result: Result, store: URL, expectedBindingSHA256: String) throws {
        guard result.bindingSHA256 == expectedBindingSHA256, digestString(expectedBindingSHA256),
              result.nativeBinary.kind == .unsignedNativeBinary, result.debugSymbols.kind == .debugSymbols else { throw Failure.corruptObject }
        let app = try decode(readObject(result.nativeBinary, store: store), kind: .unsignedNativeBinary, binding: expectedBindingSHA256)
        let symbols = try decode(readObject(result.debugSymbols, store: store), kind: .debugSymbols, binding: expectedBindingSHA256)
        let product = try validate(app: app, symbols: symbols)
        guard result.executable == product.0, result.uuid == hex(product.1.uuid), result.dependencies == product.1.dependencies,
              result.binarySignature == (product.1.linkerAdHoc ? "linker-ad-hoc-no-signing-identity" : "absent"),
              result.appFiles == app.bytes.count, result.symbolFiles == symbols.bytes.count else { throw Failure.corruptObject }
    }

    private static func digestString(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
    private static func hex(_ bytes: some Sequence<UInt8>) -> String { bytes.map { String(format: "%02x", $0) }.joined() }
    private static func hash(_ data: Data) -> String { hex(SHA256.hash(data: data)) }
    private static func check(_ result: Int32) throws { guard result >= 0 else { throw Failure.io(errno) } }
    private static func components(_ path: String) throws -> [String] {
        guard path.hasPrefix("/"), !path.utf8.contains(0), !path.contains("//") else { throw Failure.invalidPath }
        let pieces = path.split(separator: "/").map(String.init)
        guard !pieces.isEmpty, pieces.allSatisfy({ $0 != "." && $0 != ".." }) else { throw Failure.invalidPath }
        return pieces
    }
    private static func validRelative(_ path: String) -> Bool {
        !path.isEmpty && !path.hasPrefix("/") && !path.utf8.contains(0) && !path.contains("//") &&
        path.split(separator: "/").allSatisfy { $0 != "." && $0 != ".." }
    }
    private static func directory(_ url: URL, privateStore: Bool = false) throws -> Int32 {
        guard url.isFileURL else { throw Failure.invalidPath }
        let parts = try components(url.path)
        var fd = open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC)
        try check(fd)
        do {
            for part in parts {
                let next = openat(fd, part, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
                try check(next)
                close(fd); fd = next
            }
            var info = stat()
            try check(fstat(fd, &info))
            guard info.st_uid == geteuid(), !privateStore || info.st_mode & 0o777 == 0o700 else { throw Failure.unsafeFile }
            return fd
        } catch { close(fd); throw error }
    }
    private static func stable(_ a: stat, _ b: stat) -> Bool {
        a.st_dev == b.st_dev && a.st_ino == b.st_ino && a.st_mode == b.st_mode && a.st_nlink == b.st_nlink &&
        a.st_size == b.st_size && a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec && a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
        a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec && a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec
    }
    private static func stamp(_ info: stat) -> String {
        "\(info.st_dev):\(info.st_ino):\(info.st_mode):\(info.st_nlink):\(info.st_size):\(info.st_mtimespec.tv_sec):\(info.st_mtimespec.tv_nsec):\(info.st_ctimespec.tv_sec):\(info.st_ctimespec.tv_nsec)"
    }
    private static func regular(_ fd: Int32, maximum: Int = limit) throws -> Data {
        var before = stat(); try check(fstat(fd, &before))
        guard before.st_mode & S_IFMT == S_IFREG, before.st_nlink == 1, before.st_uid == geteuid(),
              before.st_size >= 0, before.st_size <= maximum else { throw Failure.unsafeFile }
        var bytes = Data()
        var chunk = [UInt8](repeating: 0, count: 64 * 1024)
        while true {
            let count = Darwin.read(fd, &chunk, chunk.count)
            if count < 0 && errno == EINTR { continue }
            guard count >= 0 else { throw Failure.io(errno) }
            if count == 0 { break }
            guard bytes.count <= maximum - count else { throw Failure.limit }
            bytes.append(contentsOf: chunk.prefix(count))
        }
        var after = stat(); try check(fstat(fd, &after))
        guard stable(before, after), bytes.count == before.st_size else { throw Failure.mutation }
        return bytes
    }
    private static func names(_ fd: Int32) throws -> [String] {
        let copy = dup(fd); try check(copy)
        guard let stream = fdopendir(copy) else { close(copy); throw Failure.io(errno) }
        defer { closedir(stream) }
        var result: [String] = []
        errno = 0
        while let entry = readdir(stream) {
            let name = withUnsafePointer(to: &entry.pointee.d_name) {
                $0.withMemoryRebound(to: CChar.self, capacity: Int(MAXNAMLEN) + 1) { String(validatingCString: $0) }
            }
            guard let name else { throw Failure.invalidPath }
            if name != "." && name != ".." { result.append(name) }
            guard result.count <= 10000 else { throw Failure.limit }
            errno = 0
        }
        guard errno == 0 else { throw Failure.io(errno) }
        return result.sorted()
    }
    private static func snapshot(_ url: URL) throws -> Snapshot {
        let fd = try directory(url); defer { close(fd) }
        var result = Snapshot()
        var total = 0
        func walk(_ parent: Int32, prefix: String, depth: Int) throws {
            guard depth < 32 else { throw Failure.limit }
            var before = stat(); try check(fstat(parent, &before))
            result.sourceStamps[prefix] = stamp(before)
            for name in try names(parent) {
                let path = prefix + name
                guard validRelative(path), result.entries.count < 10000 else { throw Failure.limit }
                var info = stat()
                try check(fstatat(parent, name, &info, AT_SYMLINK_NOFOLLOW))
                let isDirectory = info.st_mode & S_IFMT == S_IFDIR
                result.sourceStamps[path] = stamp(info)
                guard isDirectory || info.st_mode & S_IFMT == S_IFREG else { throw Failure.unsafeFile }
                let child = openat(parent, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | (isDirectory ? O_DIRECTORY : 0))
                try check(child)
                do {
                    var opened = stat(); try check(fstat(child, &opened))
                    guard stable(info, opened), opened.st_mode & 0o7000 == 0 else { throw Failure.mutation }
                    let bytes = isDirectory ? Data() : try regular(child, maximum: limit - total)
                    total += bytes.count
                    result.entries.append(Entry(path: path, mode: UInt32(info.st_mode & 0o777), directory: isDirectory,
                        size: bytes.count, sha256: hash(bytes)))
                    if isDirectory { try walk(child, prefix: path + "/", depth: depth + 1) }
                    else { result.bytes[path] = bytes }
                    close(child)
                } catch { close(child); throw error }
                var current = stat(); try check(fstatat(parent, name, &current, AT_SYMLINK_NOFOLLOW))
                guard stable(info, current) else { throw Failure.mutation }
            }
            var after = stat(); try check(fstat(parent, &after))
            guard stable(before, after) else { throw Failure.mutation }
        }
        try walk(fd, prefix: "", depth: 0)
        result.entries.sort { $0.path < $1.path }
        return result
    }
    private static func u32(_ bytes: Data, _ offset: Int) throws -> UInt32 {
        guard offset >= 0, offset <= bytes.count - 4 else { throw Failure.malformedProduct }
        return (0..<4).reduce(0) { $0 | UInt32(bytes[offset + $1]) << ($1 * 8) }
    }
    private static func string(_ bytes: Data, _ start: Int, _ end: Int) throws -> String {
        guard start >= 0, start < end, end <= bytes.count, let zero = bytes[start..<end].firstIndex(of: 0),
              let value = String(data: bytes[start..<zero], encoding: .utf8) else { throw Failure.malformedProduct }
        return value
    }
    private static func fixedString(_ bytes: Data, _ start: Int) throws -> String {
        guard start >= 0, start <= bytes.count - 16,
              let value = String(data: bytes[start..<(bytes[start..<start + 16].firstIndex(of: 0) ?? start + 16)], encoding: .utf8) else { throw Failure.malformedProduct }
        return value
    }
    private static func big32(_ data: Data, _ offset: Int) throws -> UInt32 { try u32(data, offset).byteSwapped }
    private static func verifyLinkerSignature(_ bytes: Data, command: Int, length: Int) throws -> Bool {
        guard length == 16 else { throw Failure.target }
        let offset = Int(try u32(bytes, command + 8)), size = Int(try u32(bytes, command + 12))
        if size == 0 { return false }
        guard offset > 0, offset <= bytes.count, size == bytes.count - offset, size >= 64 else { throw Failure.target }
        let signature = bytes.subdata(in: offset..<bytes.count)
        let declared = Int(try big32(signature, 4))
        guard try big32(signature, 0) == 0xfade0cc0, declared <= size, declared >= 20,
              signature[declared...].allSatisfy({ $0 == 0 }), try big32(signature, 8) == 1,
              try big32(signature, 12) == 0, try big32(signature, 16) == 20 else { throw Failure.target }
        let cd = signature.subdata(in: 20..<declared)
        guard cd.count >= 88, try big32(cd, 0) == 0xfade0c02, try big32(cd, 4) == cd.count,
              try big32(cd, 8) == 0x20400, try big32(cd, 12) == 0x20002,
              try big32(cd, 24) == 0, try big32(cd, 32) == offset,
              cd[36] == 32, cd[37] == 2, cd[39] == 12 else { throw Failure.target }
        // Exactly one linker CodeDirectory, no CMS signer, entitlements, or special slots.
        let hashOffset = Int(try big32(cd, 16)), slots = Int(try big32(cd, 28))
        guard slots == (offset + 4095) / 4096, hashOffset >= 88, hashOffset <= cd.count,
              slots <= (cd.count - hashOffset) / 32, hashOffset + slots * 32 == cd.count else { throw Failure.target }
        for page in 0..<slots {
            let pageBytes = bytes.subdata(in: page * 4096..<min(offset, (page + 1) * 4096))
            guard Data(SHA256.hash(data: pageBytes)) == cd.subdata(in: hashOffset + page * 32..<hashOffset + (page + 1) * 32) else { throw Failure.target }
        }
        return true
    }
    private static func macho(_ bytes: Data) throws -> Identity {
        guard bytes.count >= 32, try u32(bytes, 0) == 0xfeedfacf, try u32(bytes, 4) == 0x0100000c,
              try u32(bytes, 8) == 0 else { throw Failure.target }
        let type = try u32(bytes, 12)
        let count = Int(try u32(bytes, 16)), size = Int(try u32(bytes, 20))
        guard count > 0, count < 4096, size <= bytes.count - 32 else { throw Failure.malformedProduct }
        var cursor = 32, uuid: Data?, platform: UInt32?, dependencies: [String] = [], dwarfInfo = false, dwarfAbbrev = false, linkerAdHoc = false, signatureSeen = false
        for _ in 0..<count {
            let command = try u32(bytes, cursor), length = Int(try u32(bytes, cursor + 4))
            guard length >= 8, length % 8 == 0, cursor + length <= 32 + size else { throw Failure.malformedProduct }
            if command == 0x1b {
                guard length == 24, uuid == nil else { throw Failure.malformedProduct }
                uuid = bytes.subdata(in: cursor + 8..<cursor + 24)
            } else if command == 0x32 {
                guard length >= 24, platform == nil else { throw Failure.malformedProduct }
                platform = try u32(bytes, cursor + 8)
            } else if [UInt32(0xc), 0x80000018, 0x8000001f, 0x20, 0x80000023].contains(command) {
                let offset = Int(try u32(bytes, cursor + 8))
                guard offset >= 24, offset < length else { throw Failure.malformedProduct }
                dependencies.append(try string(bytes, cursor + offset, cursor + length))
            } else if command == 0x1d {
                guard !signatureSeen else { throw Failure.target }
                signatureSeen = true
                linkerAdHoc = try verifyLinkerSignature(bytes, command: cursor, length: length)
            } else if command == 0x19 {
                guard length >= 72 else { throw Failure.malformedProduct }
                let sectionCount = Int(try u32(bytes, cursor + 64))
                guard sectionCount <= (length - 72) / 80 else { throw Failure.malformedProduct }
                for i in 0..<sectionCount {
                    let section = cursor + 72 + i * 80
                    let name = try fixedString(bytes, section)
                    let segment = try fixedString(bytes, section + 16)
                    let sectionSize = UInt64(try u32(bytes, section + 40)) | UInt64(try u32(bytes, section + 44)) << 32
                    let offset = UInt64(try u32(bytes, section + 48))
                    if segment == "__DWARF", sectionSize > 0 {
                        guard offset <= bytes.count, sectionSize <= UInt64(bytes.count) - offset else { throw Failure.symbols }
                        if name == "__debug_info" { dwarfInfo = true }
                        if name == "__debug_abbrev" { dwarfAbbrev = true }
                    }
                }
            }
            cursor += length
        }
        guard cursor == 32 + size, let uuid, uuid.contains(where: { $0 != 0 }) else { throw Failure.malformedProduct }
        return Identity(uuid: uuid, fileType: type, platform: platform, dependencies: dependencies.sorted(), dwarf: dwarfInfo && dwarfAbbrev, linkerAdHoc: linkerAdHoc)
    }
    private static func validate(app: Snapshot, symbols: Snapshot) throws -> (String, Identity) {
        guard let plist = app.bytes["Info.plist"],
              let info = try PropertyListSerialization.propertyList(from: plist, format: nil) as? [String: Any],
              let executable = info["CFBundleExecutable"] as? String, !executable.contains("/"), validRelative(executable),
              info["CFBundlePackageType"] as? String == "APPL", let binary = app.bytes[executable], !binary.isEmpty,
              let mode = app.entries.first(where: { $0.path == executable })?.mode, mode & 0o111 != 0 else { throw Failure.malformedProduct }
        let identity = try macho(binary)
        guard identity.fileType == 2, identity.platform == 7 else { throw Failure.target }
        let symbolPaths = symbols.bytes.keys.filter { $0.hasPrefix("Contents/Resources/DWARF/") }
        guard symbolPaths.count == 1, let symbol = symbols.bytes["Contents/Resources/DWARF/" + executable] else { throw Failure.symbols }
        let debug = try macho(symbol)
        guard debug.fileType == 0xa, debug.uuid == identity.uuid, debug.dwarf else { throw Failure.symbols }
        // Every embedded native image is inspected; unsupported images fail closed.
        for (path, bytes) in app.bytes where bytes.count >= 4 {
            switch try u32(bytes, 0) {
            case 0xfeedfacf: break
            case 0xfeedface, 0xcefaedfe, 0xcffaedfe,
                 0xcafebabe, 0xbebafeca, 0xcafebabf, 0xbfbafeca:
                throw Failure.target
            default: continue
            }
            let image = try macho(bytes)
            guard image.platform == 7, path == executable || image.fileType == 6 else { throw Failure.target }
            for dependency in image.dependencies {
                guard validDependency(dependency) else { throw Failure.dependency(dependency) }
                if dependency.hasPrefix("/System/Library/") || dependency.hasPrefix("/usr/lib/") { continue }
                let local: String
                if dependency.hasPrefix("@rpath/") { local = "Frameworks/" + dependency.dropFirst(7) }
                else if dependency.hasPrefix("@executable_path/") { local = String(dependency.dropFirst(17)) }
                else if dependency.hasPrefix("@loader_path/") {
                    let parent = path.split(separator: "/").dropLast().joined(separator: "/")
                    local = (parent.isEmpty ? "" : parent + "/") + dependency.dropFirst(13)
                } else { throw Failure.dependency(dependency) }
                guard let linked = app.bytes[local], try macho(linked).fileType == 6 else { throw Failure.dependency(dependency) }
            }
        }
        return (executable, identity)
    }
    private static func validDependency(_ value: String) -> Bool {
        !value.contains("//") && !value.utf8.contains(0) && !value.split(separator: "/").contains("..") && !value.split(separator: "/").contains(".")
    }
    private static func archive(_ snapshot: Snapshot, kind: Kind, binding: String) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let header = try encoder.encode(Header(version: 1, kind: kind, binding: binding, entries: snapshot.entries))
        var result = magic
        var length = UInt64(header.count).bigEndian
        withUnsafeBytes(of: &length) { result.append(contentsOf: $0) }
        result.append(header)
        for entry in snapshot.entries where !entry.directory { result.append(snapshot.bytes[entry.path]!) }
        guard result.count <= limit else { throw Failure.limit }
        return result
    }
    private static func decode(_ data: Data, kind: Kind, binding: String) throws -> Snapshot {
        guard data.count >= magic.count + 8, data.prefix(magic.count) == magic else { throw Failure.corruptObject }
        let length = data[magic.count..<magic.count + 8].reduce(UInt64(0)) { ($0 << 8) | UInt64($1) }
        var cursor = magic.count + 8
        guard length <= data.count - cursor, length <= 8 * 1024 * 1024 else { throw Failure.corruptObject }
        let header = try JSONDecoder().decode(Header.self, from: data.subdata(in: cursor..<cursor + Int(length)))
        cursor += Int(length)
        guard header.version == 1, header.kind == kind, header.binding == binding, !header.entries.isEmpty,
              header.entries.count <= 10000, header.entries.map(\.path) == header.entries.map(\.path).sorted(),
              Set(header.entries.map(\.path)).count == header.entries.count else { throw Failure.corruptObject }
        var result = Snapshot(entries: header.entries)
        let directories = Set(header.entries.filter(\.directory).map(\.path))
        for entry in header.entries {
            guard validRelative(entry.path), entry.mode <= 0o777, entry.size >= 0, entry.size <= data.count - cursor else { throw Failure.corruptObject }
            let parents = entry.path.split(separator: "/").dropLast()
            for count in 1...max(1, parents.count) where count <= parents.count {
                guard directories.contains(parents.prefix(count).joined(separator: "/")) else { throw Failure.corruptObject }
            }
            if entry.directory {
                guard entry.size == 0, entry.sha256 == hash(Data()) else { throw Failure.corruptObject }
            } else {
                let bytes = data.subdata(in: cursor..<cursor + entry.size)
                guard hash(bytes) == entry.sha256 else { throw Failure.corruptObject }
                result.bytes[entry.path] = bytes; cursor += entry.size
            }
        }
        guard cursor == data.count else { throw Failure.corruptObject }
        return result
    }
    private static func readObject(_ descriptor: Descriptor, store: URL) throws -> Data {
        guard digestString(descriptor.sha256), descriptor.sizeBytes > 0, descriptor.sizeBytes <= limit,
              descriptor.ownedPath == store.path + "/" + descriptor.sha256 else { throw Failure.corruptObject }
        let root = try directory(store, privateStore: true); defer { close(root) }
        let fd = openat(root, descriptor.sha256, O_RDONLY | O_NOFOLLOW | O_CLOEXEC); try check(fd); defer { close(fd) }
        var info = stat(); try check(fstat(fd, &info))
        guard info.st_mode & 0o777 == 0o444 else { throw Failure.corruptObject }
        let bytes = try regular(fd)
        guard UInt64(bytes.count) == descriptor.sizeBytes, hash(bytes) == descriptor.sha256 else { throw Failure.corruptObject }
        return bytes
    }
    private static func retain(_ data: Data, kind: Kind, store: URL) throws -> Descriptor {
        let digest = hash(data)
        let descriptor = Descriptor(kind: kind, sha256: digest, sizeBytes: UInt64(data.count), ownedPath: store.path + "/" + digest)
        let root = try directory(store, privateStore: true); defer { close(root) }
        let temporary = ".stage-" + UUID().uuidString
        let fd = openat(root, temporary, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        try check(fd)
        defer { close(fd); unlinkat(root, temporary, 0) }
        try data.withUnsafeBytes { buffer in
            var offset = 0
            while offset < buffer.count {
                let count = Darwin.write(fd, buffer.baseAddress!.advanced(by: offset), buffer.count - offset)
                if count < 0 && errno == EINTR { continue }
                guard count > 0 else { throw Failure.io(errno) }
                offset += count
            }
        }
        try check(fchmod(fd, 0o444)); try check(fsync(fd))
        if linkat(root, temporary, root, digest, 0) != 0, errno != EEXIST { throw Failure.io(errno) }
        // Remove the staging hard link before regular-file revalidation (nlink must be one).
        try check(unlinkat(root, temporary, 0)); try check(fsync(root))
        guard try readObject(descriptor, store: store) == data else { throw Failure.corruptObject }
        return descriptor
    }
}
