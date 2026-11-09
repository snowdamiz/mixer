import Foundation
import Darwin

// Test infrastructure only. Kernel operations share a lock; child lifetimes do not.
protocol StoreChildIO: AnyObject {
    var pid: Int32 { get }
    var now: Double { get }
    func reap() throws -> Int32?
    func read(_ stream: Int) throws -> Data?
    func groupAbsent() throws -> Bool
    func killGroup() throws -> Bool
    func close() throws
    func pause()
}

struct StoreChildError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

final class StoreChildReceipt: Codable {
    let id = UUID().uuidString
    var pid: Int32 = 0
    var pgid: Int32 = 0
    var argv: [String] = []
    var scratch = ""
    var started: Double = 0
    var finished: Double?
    var state = "STARTING"
    var exitCode: Int32?
    var directChildReaped = false
    var stdoutEOF = false
    var stderrEOF = false
    var ownedGroupAbsent = false
    var terminalCustody = false
    var outputBytes = 0
    var outputLimit = 8 * 1_048_576
    var aggregateLimit = 64 * 1_048_576
    var childSeconds: Double = 30
    var cleanupSeconds: Double = 10
    var stop: String?
    var unknown: String?
    var signals: [String] = []
    var groupProbes = 0
}

final class StoreChildSession: @unchecked Sendable {
    private let lock = NSLock()
    private(set) var hold: String?
    private(set) var bytes = 0
    private var limit = false
    private(set) var receipts: [StoreChildReceipt] = []
    let directory: URL?
    let fatalUnknown: Bool
    let outputLimit: Int
    let aggregateLimit: Int
    let childSeconds: Double
    let cleanupSeconds: Double

    init(directory: URL?, fatalUnknown: Bool = true, outputLimit: Int = 8 * 1_048_576,
         aggregateLimit: Int = 64 * 1_048_576, childSeconds: Double = 30, cleanupSeconds: Double = 10) {
        self.directory = directory; self.fatalUnknown = fatalUnknown
        self.outputLimit = outputLimit; self.aggregateLimit = aggregateLimit
        self.childSeconds = childSeconds; self.cleanupSeconds = cleanupSeconds
    }

    private func save(_ receipt: StoreChildReceipt) throws {
        guard let directory else { return }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(receipt).write(to: directory.appendingPathComponent(receipt.id + ".json"), options: .atomic)
    }

    private func unknown(_ receipt: StoreChildReceipt, _ error: Error) -> StoreChildError {
        hold = String(describing: error); receipt.unknown = hold; receipt.state = "UNKNOWN"
        receipt.terminalCustody = false
        if let directory {
            for item in receipts { try? save(item) }
            let data = try? JSONEncoder().encode(receipts)
            try? data?.write(to: directory.appendingPathComponent("HOLD.json"), options: .atomic)
        }
        // No stack unwinding: project defers must not delete held scratch.
        if fatalUnknown { Darwin._exit(125) }
        return StoreChildError("UNKNOWN: " + (hold ?? "unspecified"))
    }

    func run(executable: String, arguments: [String], environment: [String: String]) throws -> (Int32, String) {
        SuiteOwnedRunner.check()
        lock.lock()
        if let hold { lock.unlock(); throw StoreChildError("sticky UNKNOWN: " + hold) }
        if limit { lock.unlock(); throw StoreChildError("aggregate/output admission closed") }
        let receipt = StoreChildReceipt()
        receipt.argv = [executable] + arguments
        receipt.scratch = environment["TMPDIR"] ?? FileManager.default.temporaryDirectory.path
        receipt.outputLimit = outputLimit; receipt.aggregateLimit = aggregateLimit
        receipt.childSeconds = childSeconds; receipt.cleanupSeconds = cleanupSeconds
        receipts.append(receipt)
        do { try save(receipt) } catch { lock.unlock(); throw error }
        let io: POSIXStoreChild
        do { io = try POSIXStoreChild(executable, arguments, environment) }
        catch {
            receipt.state = "NOT_LAUNCHED"; receipt.stop = String(describing: error)
            try? save(receipt); lock.unlock(); throw error
        }
        receipt.pid = io.pid; receipt.pgid = io.pid; receipt.started = io.now; receipt.state = "RUNNING"
        do { try save(receipt); try io.closeWriters() }
        catch { let failure = unknown(receipt, error); lock.unlock(); throw failure }
        lock.unlock()
        return try drive(io, receipt)
    }

    // The fake controls exercise this exact loop, replacing only kernel IO and the clock.
    func runFake(_ io: StoreChildIO) throws -> (Int32, String) {
        lock.lock()
        if let hold { lock.unlock(); throw StoreChildError("sticky UNKNOWN: " + hold) }
        if limit { lock.unlock(); throw StoreChildError("output admission closed") }
        let receipt = StoreChildReceipt()
        receipt.pid = io.pid; receipt.pgid = io.pid; receipt.started = io.now; receipt.state = "RUNNING"
        receipt.outputLimit = outputLimit; receipt.aggregateLimit = aggregateLimit
        receipt.childSeconds = childSeconds; receipt.cleanupSeconds = cleanupSeconds
        receipts.append(receipt); lock.unlock()
        return try drive(io, receipt)
    }

    private func drive(_ io: StoreChildIO, _ receipt: StoreChildReceipt) throws -> (Int32, String) {
        var streams = [Data(), Data()]
        var cleanupDeadline: Double?
        while true {
            lock.lock()
            if let hold { lock.unlock(); throw StoreChildError("sticky UNKNOWN: " + hold) }
            var unlocked = false
            do {
                // Reap before probing: Darwin can report EPERM for an unreaped zombie.
                if !receipt.directChildReaped, let code = try io.reap() {
                    receipt.exitCode = code; receipt.directChildReaped = true
                }
                for stream in 0..<2 where !(stream == 0 ? receipt.stdoutEOF : receipt.stderrEOF) {
                    if let data = try io.read(stream) {
                        if data.isEmpty {
                            if stream == 0 { receipt.stdoutEOF = true } else { receipt.stderrEOF = true }
                        } else {
                            let room = max(0, min(outputLimit - receipt.outputBytes, aggregateLimit - bytes))
                            let kept = data.prefix(room); streams[stream].append(kept)
                            receipt.outputBytes += kept.count; bytes += kept.count
                            if kept.count != data.count { receipt.stop = "output-limit"; limit = true }
                        }
                    }
                }
                if receipt.directChildReaped && !receipt.ownedGroupAbsent {
                    receipt.groupProbes += 1
                    receipt.ownedGroupAbsent = try io.groupAbsent()
                }
                if cleanupDeadline == nil && io.now >= receipt.started + childSeconds { receipt.stop = receipt.stop ?? "timeout" }
                if limit { receipt.stop = receipt.stop ?? "aggregate-output-limit" }
                if receipt.directChildReaped && receipt.stdoutEOF && receipt.stderrEOF && receipt.ownedGroupAbsent {
                    try io.close()
                    receipt.terminalCustody = true; receipt.state = "TERMINAL"; receipt.finished = io.now
                    if let directory {
                        try streams[0].write(to: directory.appendingPathComponent(receipt.id + ".stdout"))
                        try streams[1].write(to: directory.appendingPathComponent(receipt.id + ".stderr"))
                    }
                    try save(receipt)
                    let code = receipt.exitCode!
                    let refusal = receipt.stop
                    lock.unlock(); unlocked = true
                    if let refusal { throw StoreChildError(refusal) }
                    return (code, String(decoding: streams[0] + streams[1], as: UTF8.self))
                }
                if cleanupDeadline == nil {
                    if io.now >= receipt.started + childSeconds { receipt.stop = receipt.stop ?? "timeout" }
                    if limit { receipt.stop = receipt.stop ?? "aggregate-output-limit" }
                    if receipt.stop != nil {
                        cleanupDeadline = io.now + cleanupSeconds
                        if !receipt.ownedGroupAbsent {
                            receipt.ownedGroupAbsent = try io.killGroup()
                            receipt.signals.append("SIGKILL")
                        }
                    }
                }
                if let deadline = cleanupDeadline, io.now >= deadline {
                    throw StoreChildError("cleanup-deadline: custody incomplete")
                }
            } catch {
                // A terminal, bounded failure has already unlocked and is safe to report.
                if unlocked { throw error }
                let failure = unknown(receipt, error); lock.unlock(); throw failure
            }
            lock.unlock()
            io.pause()
        }
    }
}

private final class POSIXStoreChild: StoreChildIO {
    var pid: Int32 = 0
    private var outputs: [Int32] = []
    private var writers: [Int32] = []
    var now: Double { ProcessInfo.processInfo.systemUptime }

    init(_ executable: String, _ arguments: [String], _ environment: [String: String]) throws {
        guard executable.hasPrefix("/"), !([executable] + arguments + environment.map { $0.key + "=" + $0.value }).contains(where: { $0.utf8.contains(0) }) else {
            throw StoreChildError("absolute executable and NUL-free inputs required")
        }
        var actions: posix_spawn_file_actions_t?
        var attributes: posix_spawnattr_t?
        func check(_ code: Int32, _ operation: String) throws {
            if code != 0 { throw StoreChildError(operation + ": " + String(code)) }
        }
        try check(posix_spawn_file_actions_init(&actions), "actions-init")
        defer { posix_spawn_file_actions_destroy(&actions) }
        try check(posix_spawnattr_init(&attributes), "attributes-init")
        defer { posix_spawnattr_destroy(&attributes) }
        var launched = false
        defer { if !launched { for fd in outputs + writers { Darwin.close(fd) } } }
        for stream in 0..<2 {
            var fds: [Int32] = [-1, -1]
            guard pipe(&fds) == 0 else { throw StoreChildError("pipe: " + String(errno)) }
            outputs.append(fds[0]); writers.append(fds[1])
            for fd in fds {
                guard fcntl(fd, F_SETFD, FD_CLOEXEC) == 0 else { throw StoreChildError("cloexec: " + String(errno)) }
            }
            guard fcntl(fds[0], F_SETFL, O_NONBLOCK) == 0 else { throw StoreChildError("nonblock: " + String(errno)) }
            try check(posix_spawn_file_actions_adddup2(&actions, fds[1], Int32(stream + 1)), "dup-stream")
        }
        try check(posix_spawn_file_actions_addopen(&actions, 0, "/dev/null", O_RDONLY, 0), "stdin-null")
        try check(posix_spawnattr_setflags(&attributes, Int16(POSIX_SPAWN_SETPGROUP | POSIX_SPAWN_CLOEXEC_DEFAULT)), "flags")
        try check(posix_spawnattr_setpgroup(&attributes, 0), "new-process-group")
        let args = ([executable] + arguments).map { strdup($0) } + [nil]
        let env = environment.sorted { $0.key < $1.key }.map { strdup($0.key + "=" + $0.value) } + [nil]
        defer { for value in args + env { free(value) } }
        guard args.dropLast().allSatisfy({ $0 != nil }), env.dropLast().allSatisfy({ $0 != nil }) else { throw StoreChildError("allocation") }
        let result = args.withUnsafeBufferPointer { argv in env.withUnsafeBufferPointer { envp in
            posix_spawn(&pid, executable, &actions, &attributes, argv.baseAddress!, envp.baseAddress!)
        } }
        try check(result, "posix-spawn")
        launched = true
    }
    func closeWriters() throws {
        for fd in writers { guard Darwin.close(fd) == 0 else { throw StoreChildError("close-writer: " + String(errno)) } }
        writers = []
    }
    func reap() throws -> Int32? {
        var status: Int32 = 0
        let result = waitpid(pid, &status, WNOHANG)
        if result == 0 || result == -1 && errno == EINTR { return nil }
        guard result == pid else { throw StoreChildError("waitpid: " + String(errno)) }
        if status & 0x7f == 0 { return (status >> 8) & 0xff }
        return 128 + (status & 0x7f)
    }
    func read(_ stream: Int) throws -> Data? {
        var bytes = [UInt8](repeating: 0, count: 65_536)
        let count = Darwin.read(outputs[stream], &bytes, bytes.count)
        if count >= 0 { return Data(bytes.prefix(count)) }
        if errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR { return nil }
        throw StoreChildError("read: " + String(errno))
    }
    func groupAbsent() throws -> Bool {
        if Darwin.kill(-pid, 0) == 0 { return false }
        if errno == ESRCH { return true }
        throw StoreChildError("group-probe: " + String(errno))
    }
    func killGroup() throws -> Bool {
        if Darwin.kill(-pid, SIGKILL) == 0 { return false }
        if errno == ESRCH { return true }
        throw StoreChildError("group-signal: " + String(errno))
    }
    func close() throws {
        for fd in outputs { guard Darwin.close(fd) == 0 else { throw StoreChildError("close-reader: " + String(errno)) } }
        outputs = []
    }
    func pause() { usleep(1_000) }
}

enum StoreCLIChild {
    static let session = StoreChildSession(directory: ProcessInfo.processInfo.environment["MIXER_STORE_CUSTODY_DIR"].map { URL(fileURLWithPath: $0) }, aggregateLimit: min(64 * 1_048_576, Int(ProcessInfo.processInfo.environment["MIXER_STORE_CUSTODY_AGGREGATE_BYTES"] ?? "67108864") ?? 0))
    static func run(_ executable: String, _ arguments: [String], environment: [String: String]) throws -> (Int32, String) {
        guard session.directory != nil else { throw StoreChildError("MIXER_STORE_CUSTODY_DIR required for per-child receipts") }
        return try session.run(executable: executable, arguments: arguments, environment: environment)
    }
}
