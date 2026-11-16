import Foundation
import CryptoKit
import Darwin

/// Retained-file inventory only. Does not establish release or OTA eligibility.
public enum ResourceInventoryProduct {
    public enum Kind: String, Codable, Sendable { case resourceInventory = "resource_inventory" }
    public enum EntryKind: String, Codable, Sendable { case directory, file }
    public enum Classification: String, Codable, Sendable {
        case nativeExecutable = "native_executable", unclassified
    }
    public struct Identity: Codable, Equatable, Sendable {
        public let kind: NativeProductCapture.Kind
        public let sha256: String
        public let sizeBytes: UInt64
    }
    public struct Entry: Codable, Equatable, Sendable {
        public let path: String
        public let kind: EntryKind
        public let mode: UInt32
        public let sizeBytes: UInt64
        public let sha256: String
        public let classification: Classification?
    }
    public struct Inventory: Codable, Equatable, Sendable {
        public let version: Int
        public let kind: Kind
        public let parentApp: Identity
        public let parentSymbols: Identity
        public let bindingSHA256: String
        public let executable: String
        public let uuid: String
        public let entries: [Entry]
    }
    public struct Descriptor: Codable, Equatable, Sendable {
        public let kind: Kind
        public let sha256: String
        public let sizeBytes: UInt64
        public let ownedPath: String
    }
    public enum Failure: Error, Equatable {
        case invalidPath, unsafeFile, corruptObject, conflictingPath, limit, mutation, io(Int32)
    }

    // This is the owning capture's versioned archive header, not a native image parser.
    private struct CaptureEntry: Decodable {
        let path: String
        let mode: UInt32
        let directory: Bool
        let size: Int
        let sha256: String
    }
    private struct CaptureHeader: Decodable {
        let version: Int
        let kind: NativeProductCapture.Kind
        let binding: String
        let entries: [CaptureEntry]
    }
    private static let maximum = 256 * 1024 * 1024
    private static let magic = Data("MXNATIVE1\n".utf8)

    public static func produce(capture: NativeProductCapture.Result, captureStore: URL,
        store: URL, expectedBindingSHA256: String) throws -> Descriptor {
        let bytes = try canonical(capture: capture, captureStore: captureStore, expectedBindingSHA256: expectedBindingSHA256)
        let digest = hash(bytes)
        let descriptor = Descriptor(kind: .resourceInventory, sha256: digest,
            sizeBytes: UInt64(bytes.count), ownedPath: store.path + "/" + digest)
        let root = try directory(store); defer { close(root) }
        let stage = ".inventory-" + UUID().uuidString
        let fd = openat(root, stage, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        try check(fd)
        defer { close(fd); unlinkat(root, stage, 0) }
        try bytes.withUnsafeBytes { buffer in
            var offset = 0
            while offset < buffer.count {
                let count = Darwin.write(fd, buffer.baseAddress!.advanced(by: offset), buffer.count - offset)
                if count < 0 && errno == EINTR { continue }
                guard count > 0 else { throw Failure.io(errno) }
                offset += count
            }
        }
        try check(fchmod(fd, 0o444)); try check(fsync(fd))
        if linkat(root, stage, root, digest, 0) != 0, errno != EEXIST { throw Failure.io(errno) }
        try check(unlinkat(root, stage, 0)); try check(fsync(root))
        guard try readObject(sha256: digest, size: descriptor.sizeBytes, path: descriptor.ownedPath, store: store) == bytes else {
            throw Failure.corruptObject
        }
        return descriptor
    }

    /// Reopens the report and both exact expected parents; a report hash alone is insufficient.
    @discardableResult
    public static func revalidate(_ descriptor: Descriptor, capture: NativeProductCapture.Result,
        captureStore: URL, store: URL, expectedBindingSHA256: String) throws -> Inventory {
        let actual = try readObject(sha256: descriptor.sha256, size: descriptor.sizeBytes, path: descriptor.ownedPath, store: store)
        let expected = try canonical(capture: capture, captureStore: captureStore, expectedBindingSHA256: expectedBindingSHA256)
        guard actual == expected else { throw Failure.corruptObject }
        return try JSONDecoder().decode(Inventory.self, from: actual)
    }

    private static func canonical(capture: NativeProductCapture.Result, captureStore: URL,
        expectedBindingSHA256: String) throws -> Data {
        try NativeProductCapture.revalidate(capture, store: captureStore, expectedBindingSHA256: expectedBindingSHA256)
        let parent = capture.nativeBinary
        let data = try readObject(sha256: parent.sha256, size: parent.sizeBytes, path: parent.ownedPath, store: captureStore)
        guard data.count >= magic.count + 8, data.prefix(magic.count) == magic else { throw Failure.corruptObject }
        let length = data[magic.count..<magic.count + 8].reduce(UInt64(0)) { ($0 << 8) | UInt64($1) }
        var cursor = magic.count + 8
        guard length <= 8 * 1024 * 1024, length <= data.count - cursor else { throw Failure.limit }
        let header = try JSONDecoder().decode(CaptureHeader.self, from: data.subdata(in: cursor..<cursor + Int(length)))
        cursor += Int(length)
        guard header.version == 1, header.kind == .unsignedNativeBinary, header.binding == expectedBindingSHA256,
            !header.entries.isEmpty, header.entries.count <= 10000,
            header.entries.map(\.path) == header.entries.map(\.path).sorted() else { throw Failure.corruptObject }
        var paths = Set<String>()
        for entry in header.entries {
            guard validRelative(entry.path), entry.mode <= 0o777 else { throw Failure.invalidPath }
            // Reject aliases on case-insensitive stores as well as exact duplicates.
            guard paths.insert(entry.path.lowercased()).inserted else { throw Failure.conflictingPath }
        }
        let directories = Set(header.entries.filter(\.directory).map(\.path))
        var entries: [Entry] = []
        for entry in header.entries {
            let pieces = entry.path.split(separator: "/")
            for count in 1..<pieces.count {
                guard directories.contains(pieces.prefix(count).joined(separator: "/")) else { throw Failure.conflictingPath }
            }
            guard entry.size >= 0, entry.size <= data.count - cursor, validDigest(entry.sha256) else { throw Failure.corruptObject }
            if entry.directory {
                guard entry.size == 0, entry.sha256 == hash(Data()) else { throw Failure.corruptObject }
            } else {
                let payload = data.subdata(in: cursor..<cursor + entry.size)
                guard hash(payload) == entry.sha256 else { throw Failure.corruptObject }
                cursor += entry.size
            }
            entries.append(Entry(path: entry.path, kind: entry.directory ? .directory : .file,
                mode: entry.mode, sizeBytes: UInt64(entry.size), sha256: entry.sha256,
                classification: entry.directory ? nil : (entry.path == capture.executable ? .nativeExecutable : .unclassified)))
        }
        guard cursor == data.count, entries.filter({ $0.kind == .file }).count == capture.appFiles,
            entries.contains(where: { $0.classification == .nativeExecutable }) else { throw Failure.corruptObject }
        try NativeProductCapture.revalidate(capture, store: captureStore, expectedBindingSHA256: expectedBindingSHA256)
        let inventory = Inventory(version: 1, kind: .resourceInventory,
            parentApp: Identity(kind: parent.kind, sha256: parent.sha256, sizeBytes: parent.sizeBytes),
            parentSymbols: Identity(kind: capture.debugSymbols.kind, sha256: capture.debugSymbols.sha256, sizeBytes: capture.debugSymbols.sizeBytes),
            bindingSHA256: expectedBindingSHA256, executable: capture.executable, uuid: capture.uuid, entries: entries)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return try encoder.encode(inventory)
    }

    private static func validRelative(_ path: String) -> Bool {
        !path.isEmpty && !path.hasPrefix("/") && !path.hasSuffix("/") && !path.utf8.contains(0) &&
            path.split(separator: "/", omittingEmptySubsequences: false).allSatisfy { !$0.isEmpty && $0 != "." && $0 != ".." }
    }
    private static func validDigest(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
    private static func hash(_ bytes: Data) -> String { SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined() }
    private static func check(_ value: Int32) throws { guard value >= 0 else { throw Failure.io(errno) } }
    private static func directory(_ url: URL) throws -> Int32 {
        guard url.isFileURL, url.path.hasPrefix("/"), validRelative(String(url.path.dropFirst())) else { throw Failure.invalidPath }
        var fd = open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC); try check(fd)
        do {
            for part in url.path.split(separator: "/") {
                let next = openat(fd, String(part), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
                try check(next); close(fd); fd = next
            }
            var info = stat(); try check(fstat(fd, &info))
            guard info.st_uid == geteuid(), info.st_mode & 0o777 == 0o700 else { throw Failure.unsafeFile }
            return fd
        } catch { close(fd); throw error }
    }
    private static func stable(_ a: stat, _ b: stat) -> Bool {
        a.st_dev == b.st_dev && a.st_ino == b.st_ino && a.st_mode == b.st_mode && a.st_nlink == b.st_nlink &&
            a.st_size == b.st_size && a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec && a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
            a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec && a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec
    }
    private static func readObject(sha256: String, size: UInt64, path: String, store: URL) throws -> Data {
        guard validDigest(sha256), size > 0, size <= maximum, path == store.path + "/" + sha256 else { throw Failure.corruptObject }
        let root = try directory(store); defer { close(root) }
        let fd = openat(root, sha256, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC); try check(fd); defer { close(fd) }
        var before = stat(); try check(fstat(fd, &before))
        guard before.st_mode & S_IFMT == S_IFREG, before.st_mode & 0o777 == 0o444,
            before.st_uid == geteuid(), before.st_nlink == 1, before.st_size == size else { throw Failure.unsafeFile }
        var bytes = Data(); var buffer = [UInt8](repeating: 0, count: 65536)
        while true {
            let count = Darwin.read(fd, &buffer, buffer.count)
            if count < 0 && errno == EINTR { continue }
            guard count >= 0 else { throw Failure.io(errno) }
            if count == 0 { break }
            guard bytes.count <= Int(size) - count else { throw Failure.limit }
            bytes.append(contentsOf: buffer.prefix(count))
        }
        var after = stat(); try check(fstat(fd, &after))
        guard stable(before, after) else { throw Failure.mutation }
        guard UInt64(bytes.count) == size, hash(bytes) == sha256 else { throw Failure.corruptObject }
        return bytes
    }
}
