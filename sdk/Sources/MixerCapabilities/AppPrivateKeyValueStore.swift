#if !os(WASI)
import Foundation
import MixerCapabilityIO
#if canImport(Darwin)
import Darwin
#elseif canImport(Android)
import Android
#else
import Glibc
#endif

private func kvClose(_ fd: Int32) {
    #if canImport(Darwin)
    _ = Darwin.close(fd)
    #elseif canImport(Android)
    _ = Android.close(fd)
    #else
    _ = Glibc.close(fd)
    #endif
}
private func kvRead(_ fd: Int32, _ bytes: UnsafeMutableRawPointer, _ count: Int) -> Int {
    #if canImport(Darwin)
    Darwin.read(fd, bytes, count)
    #elseif canImport(Android)
    Android.read(fd, bytes, count)
    #else
    Glibc.read(fd, bytes, count)
    #endif
}

// An injective lowercase physical spelling prevents filesystem case-folding from
// merging distinct ASCII grant namespaces/keys. A128-byte key occupies208 bytes.
private enum KVFileNames {
    static let alphabet = Array("abcdefghijklmnopqrstuvwxyz234567".utf8)
    static func physical(_ value: String) -> String {
        var accumulator: UInt32 = 0, bits = 0
        var output = Array("v1-".utf8)
        for byte in value.utf8 {
            accumulator = (accumulator << 8) | UInt32(byte); bits += 8
            while bits >= 5 { bits -= 5; output.append(alphabet[Int((accumulator >> bits) & 31)]) }
            accumulator &= (1 << bits) - 1
        }
        if bits > 0 { output.append(alphabet[Int((accumulator << (5-bits)) & 31)]) }
        return String(decoding: output, as: UTF8.self)
    }
    static func logical(_ value: String, maximum: Int) throws -> String {
        guard value.hasPrefix("v1-"), value.utf8.count <= 208 else { throw CapabilityFailure.ioFailure }
        var accumulator: UInt32 = 0, bits = 0, output: [UInt8] = []
        for byte in value.utf8.dropFirst(3) {
            guard let digit = alphabet.firstIndex(of: byte) else { throw CapabilityFailure.ioFailure }
            accumulator = (accumulator << 5) | UInt32(digit); bits += 5
            if bits >= 8 { bits -= 8; output.append(UInt8((accumulator >> bits) & 255)) }
            accumulator &= (1 << bits) - 1
        }
        guard accumulator == 0, let logical = String(data: Data(output), encoding: .utf8), physical(logical) == value else { throw CapabilityFailure.ioFailure }
        return try WireRules.string(["v": .string(logical)], "v", rule: "identifier", maximum: maximum)
    }
}

/// Dedicated app-private directory; namespaces/keys are ASCII value identifiers,
/// never paths. One serial actor and exclusive OS lock own all file operations.
/// Configured total-byte/entry ceilings include retained state: reopening above
/// either ceiling fails without deleting stored values.
public actor AppPrivateKeyValueStore: AppPrivateKeyValueServing {
    private let directory: KVDirectory
    private let namespaces: Set<String>
    private let maximumBytes: Int
    private let maximumEntries: Int
    private var closed = false
    private var poisoned = false
    public init(directory: URL, namespaces: Set<String>, maximumTotalBytes: Int = 4_194_304, maximumEntries: Int = 1024) throws {
        guard !namespaces.isEmpty, namespaces.count <= 32, (1...4_194_304).contains(maximumTotalBytes), (1...1024).contains(maximumEntries) else { throw CapabilityWireError.invalid("storage configuration") }
        for name in namespaces { _ = try WireRules.string(["v": .string(name)], "v", rule: "identifier", maximum: 64) }
        self.namespaces = namespaces; maximumBytes = maximumTotalBytes; self.maximumEntries = maximumEntries
        self.directory = try KVDirectory(directory)
        let inventory = try self.directory.inventory(namespaces: namespaces)
        guard inventory.bytes <= maximumTotalBytes, inventory.entries <= maximumEntries else {
            throw CapabilityFailure.quotaExceeded
        }
    }
    public func close() { closed = true; directory.close() }
    private func available(_ namespace: String) throws {
        guard !closed, !poisoned else { throw CapabilityFailure.unavailable }
        guard namespaces.contains(namespace) else { throw CapabilityFailure.permissionDenied }
        try Task.checkCancellation()
    }
    public func get(_ arguments: KVGetArguments) throws -> KVGetResponse {
        _ = try KVGetArguments(wire: arguments.wire); try available(arguments.namespace)
        let data = try directory.read(namespace: arguments.namespace, key: arguments.key)
        return KVGetResponse(found: data != nil, valueBase64: data?.base64EncodedString() ?? "")
    }
    public func put(_ arguments: KVPutArguments) throws -> KVMutationResponse {
        _ = try KVPutArguments(wire: arguments.wire); try available(arguments.namespace)
        let data = Data(base64Encoded: arguments.valueBase64)!
        let inventory = try directory.inventory(namespaces: namespaces)
        let prior = try directory.read(namespace: arguments.namespace, key: arguments.key)
        guard inventory.bytes - (prior?.count ?? 0) + data.count <= maximumBytes,
              inventory.entries + (prior == nil ? 1 : 0) <= maximumEntries else { throw CapabilityFailure.quotaExceeded }
        do { try directory.replace(namespace: arguments.namespace, key: arguments.key, data: data) }
        catch is CancellationError { throw CancellationError() }
        catch { poisoned = true; throw CapabilityFailure.ioFailure }
        return KVMutationResponse(committed: true)
    }
    public func delete(_ arguments: KVDeleteArguments) throws -> KVMutationResponse {
        _ = try KVDeleteArguments(wire: arguments.wire); try available(arguments.namespace)
        do { try directory.remove(namespace: arguments.namespace, key: arguments.key) }
        catch { poisoned = true; throw CapabilityFailure.ioFailure }
        return KVMutationResponse(committed: true)
    }
}

// Only the owning actor uses these descriptors. Construction/deinit may run on
// another executor; no descriptor or native address is exported to the guest.
private final class KVDirectory: @unchecked Sendable {
    let url: URL
    private var root: Int32 = -1
    private var lock: Int32 = -1
    init(_ url: URL) throws {
        guard url.isFileURL, url.path.hasPrefix("/"), !url.path.utf8.contains(0), url.path.utf8.count <= 4096 else { throw CapabilityFailure.ioFailure }
        self.url = url
        let result = url.withUnsafeFileSystemRepresentation { mkdir($0!, 0o700) }
        guard result == 0 || errno == EEXIST else { throw CapabilityFailure.ioFailure }
        root = url.withUnsafeFileSystemRepresentation { open($0!, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC) }
        guard root >= 0 else { throw CapabilityFailure.ioFailure }
        do {
            guard fchmod(root, 0o700) == 0 else { throw CapabilityFailure.ioFailure }
            lock = openat(root, ".lock", O_CREAT | O_RDWR | O_NOFOLLOW | O_CLOEXEC, 0o600)
            guard lock >= 0 else { throw CapabilityFailure.ioFailure }; _ = try regular(lock)
            guard mixer_capability_lock(lock, LOCK_EX | LOCK_NB) == 0 else { throw CapabilityFailure.unavailable }
            let parent = url.deletingLastPathComponent().withUnsafeFileSystemRepresentation { open($0!, O_RDONLY | O_DIRECTORY | O_CLOEXEC) }
            guard parent >= 0 else { throw CapabilityFailure.ioFailure }; defer { kvClose(parent) }
            guard fsync(parent) == 0 else { throw CapabilityFailure.ioFailure }
        } catch { close(); throw error }
    }
    deinit { close() }
    func close() { if lock >= 0 { _ = mixer_capability_lock(lock, LOCK_UN); kvClose(lock); lock = -1 }; if root >= 0 { kvClose(root); root = -1 } }
    private func namespace(_ name: String, create: Bool = false) throws -> Int32? {
        guard root >= 0 else { throw CapabilityFailure.unavailable }
        let name = KVFileNames.physical(name)
        if create {
            let result = mkdirat(root, name, 0o700)
            guard result == 0 || errno == EEXIST else { throw CapabilityFailure.ioFailure }
            guard fsync(root) == 0 else { throw CapabilityFailure.ioFailure }
        }
        let fd = openat(root, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        if fd < 0 && errno == ENOENT { return nil }
        guard fd >= 0 else { throw CapabilityFailure.ioFailure }; return fd
    }
    private func regular(_ fd: Int32) throws -> Int {
        var status = stat(); guard fstat(fd, &status) == 0, status.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG), status.st_nlink == 1,
            status.st_size >= 0, status.st_size <= 65536 else { throw CapabilityFailure.ioFailure }; return Int(status.st_size)
    }
    func read(namespace name: String, key: String) throws -> Data? {
        guard let ns = try namespace(name) else { return nil }; defer { kvClose(ns) }
        let fd = openat(ns, KVFileNames.physical(key), O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
        if fd < 0 && errno == ENOENT { return nil }; guard fd >= 0 else { throw CapabilityFailure.ioFailure }; defer { kvClose(fd) }
        _ = try regular(fd)
        var result = Data(); var buffer = [UInt8](repeating: 0, count: 8192)
        while true {
            let count = buffer.withUnsafeMutableBytes { kvRead(fd, $0.baseAddress!, min($0.count, 65537 - result.count)) }
            if count < 0 && errno == EINTR { continue }; guard count >= 0 else { throw CapabilityFailure.ioFailure }
            if count == 0 { return result }; guard count <= 65536 - result.count else { throw CapabilityFailure.quotaExceeded }
            result.append(contentsOf: buffer.prefix(count))
        }
    }
    func replace(namespace name: String, key: String, data: Data) throws {
        let ns = try namespace(name, create: true)!; defer { kvClose(ns) }
        let temporary = ".txn-" + UUID().uuidString
        let fd = openat(ns, temporary, O_CREAT | O_EXCL | O_WRONLY | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard fd >= 0 else { throw CapabilityFailure.ioFailure }; defer { kvClose(fd); _ = unlinkat(ns, temporary, 0) }
        try data.withUnsafeBytes { bytes in
            var offset = 0
            while offset < bytes.count {
                let count = write(fd, bytes.baseAddress!.advanced(by: offset), bytes.count-offset)
                if count < 0 && errno == EINTR { continue }; guard count > 0 else { throw CapabilityFailure.ioFailure }; offset += count
            }
        }
        guard fsync(fd) == 0 else { throw CapabilityFailure.ioFailure }
        try Task.checkCancellation()
        guard renameat(ns, temporary, ns, KVFileNames.physical(key)) == 0, fsync(ns) == 0 else { throw CapabilityFailure.ioFailure }
    }
    func remove(namespace name: String, key: String) throws {
        guard let ns = try namespace(name) else { return }; defer { kvClose(ns) }
        let result = unlinkat(ns, KVFileNames.physical(key), 0); guard result == 0 || errno == ENOENT else { throw CapabilityFailure.ioFailure }
        guard fsync(ns) == 0 else { throw CapabilityFailure.ioFailure }
    }
    func inventory(namespaces: Set<String>) throws -> (bytes: Int, entries: Int) {
        let entries = try FileManager.default.contentsOfDirectory(atPath: url.path)
        guard entries.count <= 33 else { throw CapabilityFailure.quotaExceeded }
        let allowed = Dictionary(uniqueKeysWithValues: namespaces.map { (KVFileNames.physical($0), $0) })
        var bytes = 0, count = 0
        for physicalNamespace in entries where physicalNamespace != ".lock" {
            guard let name = allowed[physicalNamespace], let ns = try namespace(name) else { throw CapabilityFailure.ioFailure }; defer { kvClose(ns) }
            let keys = try FileManager.default.contentsOfDirectory(atPath: url.appendingPathComponent(physicalNamespace).path)
            guard keys.count <= 2048 else { throw CapabilityFailure.quotaExceeded }
            for key in keys {
                if key.hasPrefix(".txn-"), UUID(uuidString: String(key.dropFirst(5))) != nil {
                    guard unlinkat(ns, key, 0) == 0, fsync(ns) == 0 else { throw CapabilityFailure.ioFailure }; continue
                }
                _ = try KVFileNames.logical(key, maximum: 128)
                let fd = openat(ns, key, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
                guard fd >= 0 else { throw CapabilityFailure.ioFailure }; defer { kvClose(fd) }
                bytes += try regular(fd); count += 1
                guard count <= 1024, bytes <= 4_194_304 else { throw CapabilityFailure.quotaExceeded }
            }
        }
        return (bytes, count)
    }
}
#endif
