import Foundation
import MixerDurableIO
#if canImport(Darwin)
import Darwin
#elseif canImport(Android)
import Android
#else
import Glibc
#endif

public enum DurabilityFaultPoint: String, Sendable, CaseIterable {
    case beforeStateWrite, beforeStateFileSync, beforeStateRename, afterStateRename, afterStateDirectorySync
    case beforePayloadWrite, beforePayloadSync, beforePayloadRename, afterPayloadRename, afterPayloadDirectorySync
}

private func closeDescriptor(_ descriptor: Int32) {
    #if canImport(Darwin)
    _ = Darwin.close(descriptor)
    #elseif canImport(Android)
    _ = Android.close(descriptor)
    #else
    _ = Glibc.close(descriptor)
    #endif
}

private func readDescriptor(_ descriptor: Int32, _ pointer: UnsafeMutableRawPointer, _ count: Int) -> Int {
    #if canImport(Darwin)
    Darwin.read(descriptor, pointer, count)
    #elseif canImport(Android)
    Android.read(descriptor, pointer, count)
    #else
    Glibc.read(descriptor, pointer, count)
    #endif
}

private func lockDescriptor(_ descriptor: Int32, _ operation: Int32) -> Int32 {
    mixer_update_flock(descriptor, operation)
}

/// Internal descriptors never escape their owning updater actor. Construction and
/// destruction can occur outside its executor; all operations are serialized by it.
final class DurableDirectory: @unchecked Sendable {
    let url: URL
    let wasCreated: Bool
    private var directory: Int32 = -1
    private var lock: Int32 = -1
    private let fault: (@Sendable (DurabilityFaultPoint) throws -> Void)?

    init(url: URL, fault: (@Sendable (DurabilityFaultPoint) throws -> Void)?) throws {
        guard url.isFileURL, url.path.hasPrefix("/"), !url.path.utf8.contains(0), url.path.utf8.count <= 4096 else {
            throw UpdateError("store.directory", "Store requires an absolute private file URL")
        }
        self.url = url; self.fault = fault
        let created = url.withUnsafeFileSystemRepresentation { path in mkdir(path!, 0o700) }
        guard created == 0 || errno == EEXIST else { throw Self.ioError("create store directory") }
        wasCreated = created == 0
        directory = url.withUnsafeFileSystemRepresentation { open($0!, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC) }
        guard directory >= 0 else { throw Self.ioError("open store directory") }
        do {
            guard fchmod(directory, 0o700) == 0 else { throw Self.ioError("make store private") }
            lock = openat(directory, ".lock", O_CREAT | O_RDWR | O_NOFOLLOW | O_CLOEXEC, 0o600)
            guard lock >= 0 else { throw Self.ioError("open store lock") }
            try regularFile(lock)
            guard lockDescriptor(lock, LOCK_EX | LOCK_NB) == 0 else { throw UpdateError("store.locked", "Recovery store is already open") }
            let parent = url.deletingLastPathComponent().withUnsafeFileSystemRepresentation { open($0!, O_RDONLY | O_DIRECTORY | O_CLOEXEC) }
            guard parent >= 0 else { throw Self.ioError("open parent directory") }
            defer { closeDescriptor(parent) }
            guard fsync(parent) == 0 else { throw Self.ioError("sync parent directory") }
        } catch { close(); throw error }
    }

    deinit { close() }

    func close() {
        if lock >= 0 { _ = lockDescriptor(lock, LOCK_UN); closeDescriptor(lock); lock = -1 }
        if directory >= 0 { closeDescriptor(directory); directory = -1 }
    }

    func availableBytes() throws -> UInt64 {
        var status = statvfs()
        guard fstatvfs(directory, &status) == 0 else { throw Self.ioError("query free disk") }
        let product = UInt64(status.f_bavail).multipliedReportingOverflow(by: UInt64(status.f_frsize))
        guard !product.overflow else { throw UpdateError("store.disk", "Free disk size overflow") }
        return product.partialValue
    }

    func read(_ name: String, maximumBytes: Int) throws -> Data? {
        try filename(name)
        let descriptor = openat(directory, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
        if descriptor < 0, errno == ENOENT { return nil }
        guard descriptor >= 0 else { throw Self.ioError("open stored input") }
        defer { closeDescriptor(descriptor) }
        try regularFile(descriptor)
        var data = Data()
        var buffer = [UInt8](repeating: 0, count: 65_536)
        while true {
            let count = min(buffer.count, maximumBytes - data.count + 1)
            let received = buffer.withUnsafeMutableBytes { readDescriptor(descriptor, $0.baseAddress!, count) }
            if received < 0, errno == EINTR { continue }
            guard received >= 0 else { throw Self.ioError("read stored input") }
            if received == 0 { return data }
            guard received <= maximumBytes - data.count else { throw UpdateError("store.size", "Stored input exceeds bound") }
            data.append(contentsOf: buffer.prefix(received))
        }
    }

    func size(_ name: String) throws -> UInt64? {
        try filename(name)
        let descriptor = openat(directory, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
        if descriptor < 0, errno == ENOENT { return nil }
        guard descriptor >= 0 else { throw Self.ioError("open partial input") }
        defer { closeDescriptor(descriptor) }
        let status = try regularFile(descriptor)
        return UInt64(status.st_size)
    }

    func append(_ data: Data, to name: String, offset: UInt64, maximumBytes: UInt64) throws {
        try filename(name)
        let descriptor = openat(directory, name, O_CREAT | O_RDWR | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard descriptor >= 0 else { throw Self.ioError("open partial output") }
        defer { closeDescriptor(descriptor) }
        let status = try regularFile(descriptor)
        guard UInt64(status.st_size) == offset, offset <= maximumBytes, UInt64(data.count) <= maximumBytes - offset else {
            throw UpdateError("download.offset", "Partial size, requested offset or chunk exceeds declaration")
        }
        guard lseek(descriptor, 0, SEEK_END) >= 0 else { throw Self.ioError("seek partial output") }
        try fault?(.beforePayloadWrite)
        try writeAll(data, to: descriptor)
        try fault?(.beforePayloadSync)
        guard fsync(descriptor) == 0 else { throw Self.ioError("sync partial output") }
        try sync()
    }

    func publishPayload(_ part: String, as name: String) throws {
        try filename(part); try filename(name)
        try fault?(.beforePayloadRename)
        guard renameat(directory, part, directory, name) == 0 else { throw Self.ioError("rename payload") }
        try fault?(.afterPayloadRename)
        try sync()
        try fault?(.afterPayloadDirectorySync)
    }

    func atomicState(_ data: Data) throws {
        let temporary = ".state-\(UUID().uuidString).tmp"
        let descriptor = openat(directory, temporary, O_CREAT | O_EXCL | O_WRONLY | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard descriptor >= 0 else { throw Self.ioError("create state transaction") }
        defer { closeDescriptor(descriptor); _ = unlinkat(directory, temporary, 0) }
        try fault?(.beforeStateWrite)
        try writeAll(data, to: descriptor)
        try fault?(.beforeStateFileSync)
        guard fsync(descriptor) == 0 else { throw Self.ioError("sync state transaction") }
        try fault?(.beforeStateRename)
        guard renameat(directory, temporary, directory, "state.json") == 0 else { throw Self.ioError("commit state transaction") }
        try fault?(.afterStateRename)
        try sync()
        try fault?(.afterStateDirectorySync)
    }

    func remove(_ name: String) throws {
        try filename(name)
        let result = unlinkat(directory, name, 0)
        guard result == 0 || errno == ENOENT else { throw Self.ioError("remove cached file") }
        try sync()
    }

    func pruneOwnedFiles(keeping names: Set<String>) throws {
        let contents = try FileManager.default.contentsOfDirectory(atPath: url.path)
        guard contents.count <= 1024 else { throw UpdateError("store.contents", "Recovery directory requires native maintenance") }
        for name in contents where !names.contains(name) {
            let digest: String?
            if name.hasSuffix(".payload.part") { digest = String(name.dropLast(".payload.part".count)) }
            else if name.hasSuffix(".payload") { digest = String(name.dropLast(".payload".count)) }
            else { digest = nil }
            let transaction = name.hasPrefix(".state-") && name.hasSuffix(".tmp")
                && UUID(uuidString: String(name.dropFirst(".state-".count).dropLast(".tmp".count))) != nil
            if digest.map(recoveryDigest) == true || transaction { try remove(name) }
        }
    }

    private func sync() throws {
        guard fsync(directory) == 0 else { throw Self.ioError("sync store directory") }
    }

    private func filename(_ name: String) throws {
        guard directory >= 0, !name.isEmpty, name.utf8.count < 256, !name.contains("/"), !name.utf8.contains(0), name != ".", name != ".." else {
            throw UpdateError("store.filename", "Invalid local store filename or closed directory")
        }
    }

    @discardableResult
    private func regularFile(_ descriptor: Int32) throws -> stat {
        var status = stat()
        guard fstat(descriptor, &status) == 0 else { throw Self.ioError("stat stored file") }
        guard status.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG), status.st_size >= 0, status.st_nlink == 1 else {
            throw UpdateError("store.file", "Stored input must be a private regular file without hard links")
        }
        return status
    }

    private func writeAll(_ data: Data, to descriptor: Int32) throws {
        try data.withUnsafeBytes { buffer in
            var offset = 0
            while offset < buffer.count {
                let count = write(descriptor, buffer.baseAddress!.advanced(by: offset), buffer.count - offset)
                if count < 0, errno == EINTR { continue }
                guard count > 0 else { throw Self.ioError("write private store") }
                offset += count
            }
        }
    }

    private static func ioError(_ operation: String) -> UpdateError {
        UpdateError("store.io", "\(operation) failed (errno \(errno))")
    }
}
