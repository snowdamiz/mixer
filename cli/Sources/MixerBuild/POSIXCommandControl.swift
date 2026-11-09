import Foundation
import MixerProcessIO
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

private struct ProcessIOFailure: Error, CustomStringConvertible {
    let operation: String
    let code: Int32
    var description: String { "\(operation): errno \(code)" }
}
private func checked(_ code: Int32, _ operation: String) throws {
    if code != 0 { throw ProcessIOFailure(operation: operation, code: code) }
}
final class POSIXCommandControl: OwnedCommandControl {
    // No deinit cleanup: uncertainty deliberately retains these exact descriptors and ownership.
    private var child = mx_child(pid: 0, stdout_fd: -1, stderr_fd: -1, gate_fd: -1)
    private var readinessBytes = Data()
    func monotonicNow() throws -> UInt64 {
        let value = mx_monotonic_ns()
        guard value != 0 else { throw MixerFailure("process.clock", "CLOCK_MONOTONIC unavailable") }
        return value
    }
    func launch(command: [String], directory: URL?, environment: [String: String]) throws -> OwnedLaunch {
        let strings = ["/usr/bin/env"] + command
        let variables = environment.keys.sorted().map { "\($0)=\(environment[$0]!)" }
        let argv = strings.map { strdup($0) }, envp = variables.map { strdup($0) }
        defer { for pointer in argv + envp { free(pointer) } }
        guard (argv + envp).allSatisfy({ $0 != nil }) else { throw MixerFailure("process.allocate", "Cannot allocate argv/environment") }
        let code = (argv + [nil]).withUnsafeBufferPointer { a in
            (envp + [nil]).withUnsafeBufferPointer { e in
                if let path = directory?.path {
                    return path.withCString { mx_launch(a.baseAddress!, e.baseAddress!, $0, &child) }
                }
                return mx_launch(a.baseAddress!, e.baseAddress!, nil, &child)
            }
        }
        return OwnedLaunch(pid: child.pid, setupError: code)
    }
    private func bytes(_ fd: Int32) throws -> StreamObservation {
        var data = Data(count: 65_536), code: Int32 = 0
        let count = data.withUnsafeMutableBytes { mx_read(fd, $0.baseAddress!, $0.count, &code) }
        if count < 0 {
            if code == EAGAIN || code == EWOULDBLOCK || code == EINTR { return .pending }
            throw ProcessIOFailure(operation: "read", code: code)
        }
        if count == 0 { return .eof }
        data.count = count; return .bytes(data)
    }
    func readiness() throws -> LaunchReadiness {
        switch try bytes(child.gate_fd) {
        case .pending: return .pending
        case .eof: throw MixerFailure("process.launch", "Readiness channel closed before session acknowledgement")
        case .bytes(let data):
            readinessBytes.append(data)
            if readinessBytes.count < MemoryLayout<Int32>.size { return .pending }
            guard readinessBytes.count == MemoryLayout<Int32>.size else { throw MixerFailure("process.launch", "Invalid readiness frame") }
            let code = readinessBytes.withUnsafeBytes { $0.loadUnaligned(as: Int32.self) }
            return code == 0 ? .ready : .failed(code)
        }
    }
    func release() throws {
        try checked(mx_release(child.gate_fd), "release-owned-command")
        try checked(mx_close(child.gate_fd), "close-release-channel"); child.gate_fd = -1
    }
    func read(_ stream: CommandStream) throws -> StreamObservation {
        try bytes(stream == .stdout ? child.stdout_fd : child.stderr_fd)
    }
    func exitedWithoutReaping() throws -> Bool {
        var done: Int32 = 0; try checked(mx_peek_exit(child.pid, &done), "waitid-WNOWAIT"); return done != 0
    }
    func killOwnedGroup() throws { try checked(mx_kill_group(child.pid), "kill-owned-group-before-reap") }
    func reap() throws -> Int32? {
        var code: Int32 = 0, done: Int32 = 0
        try checked(mx_reap(child.pid, &code, &done), "waitpid"); return done != 0 ? code : nil
    }
    func groupAbsent() throws -> Bool {
        var absent: Int32 = 0; try checked(mx_group_absent(child.pid, &absent), "observe-owned-group"); return absent != 0
    }
    func pause() throws { try checked(mx_pause_ms(5), "pause") }
    func close() throws {
        try checked(mx_close(child.stdout_fd), "close-stdout"); child.stdout_fd = -1
        try checked(mx_close(child.stderr_fd), "close-stderr"); child.stderr_fd = -1
    }
}

final class CommandReceiptStore {
    let directory: URL
    init(parent: URL) throws {
        directory = parent.appendingPathComponent("command-\(UUID().uuidString)", isDirectory: true)
        if !FileManager.default.fileExists(atPath: parent.path) {
            try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
            try parent.deletingLastPathComponent().path.withCString { try checked(mx_sync_directory($0), "persist-receipt-root-entry") }
        }
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        try parent.path.withCString { try checked(mx_sync_directory($0), "persist-command-directory-entry") }
    }
    func persist(_ receipt: CommandCustodyReceipt) throws {
        let data = try JSONEncoder().encode(receipt)
        let name = receipt.state == "UNKNOWN" ? "HOLD.json" : "receipt.json"
        let target = directory.appendingPathComponent(name).path
        let staging = directory.appendingPathComponent(name + ".next").path
        let code = data.withUnsafeBytes { bytes in
            staging.withCString { s in target.withCString { t in directory.path.withCString { d in
                mx_persist(s, t, d, bytes.baseAddress!, bytes.count)
            } } }
        }
        try checked(code, "durable-receipt")
    }
}

public struct ProcessCustodyHold: Codable, Sendable {
    public let receiptDirectory: String
    public let retainedInputDirectories: [String]
    public let reason: String
}

// Allocation and cleanup stay bound to the admission scope that owns the inputs.
struct ProcessInputSnapshot {
    let directory: URL
    fileprivate let context: ProcessExecutionContext
    var retainedInputDirectories: [URL] { [directory] }
    func removeIfUnheld() { context.removeInputSnapshotIfUnheld(directory) }
}

/// One serialized admission scope. UNKNOWN permanently freezes it; there is deliberately no reset API.
public final class ProcessExecutionContext: @unchecked Sendable {
    private let lock = NSLock()
    private var hold: ProcessCustodyHold?
    public var custodyHold: ProcessCustodyHold? {
        lock.lock(); defer { lock.unlock() }; return hold
    }
    private var generated: UInt64 = 0
    public let aggregateGeneratedOutputBytes: UInt64
    public let receiptDirectory: URL
    public init(receiptDirectory: URL, aggregateGeneratedOutputBytes: UInt64 = 8 << 30) {
        self.receiptDirectory = receiptDirectory; self.aggregateGeneratedOutputBytes = aggregateGeneratedOutputBytes
    }
    private var defaultParentFailure: Int32?
    public static let localDevelopment: ProcessExecutionContext = {
        // TMPDIR is the trusted launch configuration; explicit receipt paths never take this route.
        let configured = ProcessInfo.processInfo.environment["TMPDIR"]
        let parent = configured.flatMap { $0.isEmpty ? nil : $0 } ?? FileManager.default.temporaryDirectory.path
        var failure: Int32?
        let canonical: String? = parent.withCString { path in
            guard parent.hasPrefix("/"), !parent.utf8.contains(0) else { failure = EINVAL; return nil }
            guard let resolved = realpath(path, nil) else { failure = errno; return nil }
            defer { free(resolved) }
            return String(cString: resolved)
        }
        let context = ProcessExecutionContext(receiptDirectory: URL(fileURLWithPath:
            (canonical ?? parent) + "/mixer-command-receipts-\(UUID().uuidString)", isDirectory: true))
        context.defaultParentFailure = failure
        return context
    }()
    private func requireAdmission() throws {
        guard hold == nil else { throw MixerFailure("process.custody-held", "UNKNOWN at \(hold!.receiptDirectory): \(hold!.reason)") }
        if let code = defaultParentFailure { throw ProcessIOFailure(operation: "resolve-default-snapshot-parent", code: code) }
        guard generated < aggregateGeneratedOutputBytes else { throw MixerFailure("process.aggregate-output-limit", "Execution context generated-output budget exhausted") }
    }
    func makeInputSnapshot() throws -> ProcessInputSnapshot {
        lock.lock(); defer { lock.unlock() }
        try requireAdmission()
        let root = receiptDirectory
        let components = root.path.split(separator: "/").map(String.init)
        guard root.isFileURL, root.path.hasPrefix("/"), !root.path.utf8.contains(0),
              !components.isEmpty, !components.contains("."), !components.contains("..") else {
            throw MixerFailure("process.snapshot-path", "Expected a private receipt directory")
        }
        // Walk without following any supplied symlink, including ancestor components.
        var parent = open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC)
        guard parent >= 0 else { throw ProcessIOFailure(operation: "open-snapshot-ancestor", code: errno) }
        defer { _ = close(parent) }
        for component in components.dropLast() {
            let next = openat(parent, component, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard next >= 0 else { throw ProcessIOFailure(operation: "open-snapshot-ancestor", code: errno) }
            _ = close(parent); parent = next
        }
        let rootName = components.last!
        let created = mkdirat(parent, rootName, 0o700) == 0
        guard created || errno == EEXIST else { throw ProcessIOFailure(operation: "create-snapshot-root", code: errno) }
        let owner = openat(parent, rootName, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard owner >= 0 else { throw ProcessIOFailure(operation: "open-snapshot-root", code: errno) }
        defer { _ = close(owner) }
        var metadata = stat()
        guard fstat(owner, &metadata) == 0, metadata.st_uid == geteuid(), metadata.st_mode & 0o777 == 0o700 else {
            throw MixerFailure("process.snapshot-path", "Snapshot root must be owned and private (0700)")
        }
        if created, fsync(parent) != 0 { throw ProcessIOFailure(operation: "persist-snapshot-root-entry", code: errno) }
        let name = "mixer-verify-\(UUID().uuidString)"
        guard mkdirat(owner, name, 0o700) == 0 else { throw ProcessIOFailure(operation: "create-input-snapshot", code: errno) }
        let folder = root.appendingPathComponent(name, isDirectory: true)
        let snapshot = openat(owner, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard snapshot >= 0 else { throw ProcessIOFailure(operation: "open-input-snapshot", code: errno) }
        defer { _ = close(snapshot) }
        guard fstat(snapshot, &metadata) == 0, metadata.st_uid == geteuid(), metadata.st_mode & 0o777 == 0o700,
              folder.path == root.path + "/" + name else {
            throw MixerFailure("process.snapshot-path", "Input snapshot failed its private path proof")
        }
        guard fsync(owner) == 0 else { throw ProcessIOFailure(operation: "persist-input-snapshot-entry", code: errno) }
        return ProcessInputSnapshot(directory: folder, context: self)
    }
    fileprivate func removeInputSnapshotIfUnheld(_ directory: URL) {
        lock.lock(); defer { lock.unlock() }
        if hold == nil { try? FileManager.default.removeItem(at: directory) }
    }
    func run(command: [String], directory: URL?, environment: [String: String], policy: ProcessPolicy, retainedInputs: [URL] = [],
             controlFactory: () -> any OwnedCommandControl = { POSIXCommandControl() },
             receiptFactory: (URL) throws -> (String, (CommandCustodyReceipt) throws -> Void) = { parent in
                 let store = try CommandReceiptStore(parent: parent); return (store.directory.path, store.persist)
             }) throws -> CommandResult {
        lock.lock(); defer { lock.unlock() }
        try requireAdmission()
        let store: (String, (CommandCustodyReceipt) throws -> Void)
        do { store = try receiptFactory(receiptDirectory) }
        catch {
            let reason = "Receipt directory could not be prepared: \(error)"
            hold = ProcessCustodyHold(receiptDirectory: receiptDirectory.path, retainedInputDirectories: retainedInputs.map { $0.path }, reason: reason)
            throw MixerFailure("process.receipt", reason)
        }
        let execution = OwnedCommandExecution(command: command, directory: directory, policy: policy,
            aggregateLimit: aggregateGeneratedOutputBytes, aggregateUsed: generated, retainedInputs: retainedInputs,
            control: controlFactory(), save: store.1)
        defer {
            let (total, overflow) = generated.addingReportingOverflow(execution.receipt.generatedBytes)
            generated = overflow ? UInt64.max : total
        }
        do { return try execution.execute(directory: directory, environment: environment) }
        catch let unknown as UnknownCommandCustody {
            hold = ProcessCustodyHold(receiptDirectory: store.0, retainedInputDirectories: execution.receipt.retainedInputDirectories, reason: unknown.description)
            throw MixerFailure("process.custody-unknown", "UNKNOWN at \(store.0): \(unknown)")
        }
    }
}
