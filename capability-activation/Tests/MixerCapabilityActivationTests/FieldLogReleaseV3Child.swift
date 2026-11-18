#if os(macOS) && canImport(MixerApple)
import Darwin
import Foundation
import MixerUpdates

/// Test-only direct children. Each gets its own process group at spawn.
@MainActor
final class FieldLogReleaseV3Child {
    private struct Receipt: Encodable {
        let parentPID = getpid()
        let executable: String
        var pid: pid_t?
        var pgid: pid_t?
        var state = "SPAWNING"
        var directChildReaped = false
        var ownedGroupAbsent = false
        var exitCode: Int32?
        var terminationSignal: Int32?
        var error: String?
    }

    private let record: URL
    private let pid: pid_t
    private var receipt: Receipt

    init(_ executable: URL, arguments: [String] = [], environment: [String: String],
         directory: URL, name: String) throws {
        record = directory.appendingPathComponent(name + ".json")
        receipt = Receipt(executable: executable.path)
        var actions: posix_spawn_file_actions_t?
        try Self.check(posix_spawn_file_actions_init(&actions), "file actions")
        defer { posix_spawn_file_actions_destroy(&actions) }
        var attributes: posix_spawnattr_t?
        try Self.check(posix_spawnattr_init(&attributes), "attributes")
        defer { posix_spawnattr_destroy(&attributes) }
        try Self.check(posix_spawnattr_setflags(&attributes, Int16(POSIX_SPAWN_SETPGROUP | POSIX_SPAWN_CLOEXEC_DEFAULT)), "flags")
        try Self.check(posix_spawnattr_setpgroup(&attributes, 0), "new group")
        let log = directory.appendingPathComponent(name + ".log")
        try Self.check(posix_spawn_file_actions_addopen(&actions, STDOUT_FILENO, log.path,
                                                       O_CREAT | O_EXCL | O_WRONLY, 0o600), "stdout")
        try Self.check(posix_spawn_file_actions_adddup2(&actions, STDOUT_FILENO, STDERR_FILENO), "stderr")

        let argv = ([executable.path] + arguments).map { strdup($0) } + [nil]
        let envp = environment.sorted(by: { $0.key < $1.key }).map { strdup("\($0.key)=\($0.value)") } + [nil]
        defer { (argv + envp).forEach { free($0) } }
        guard argv.dropLast().allSatisfy({ $0 != nil }), envp.dropLast().allSatisfy({ $0 != nil }) else {
            throw UpdateError("test.child", "Could not allocate child arguments")
        }
        try Self.save(receipt, to: record, options: .withoutOverwriting)
        var child: pid_t = 0
        let result = argv.withUnsafeBufferPointer { argv in
            envp.withUnsafeBufferPointer { envp in
                posix_spawn(&child, executable.path, &actions, &attributes, argv.baseAddress!, envp.baseAddress!)
            }
        }
        if result != 0 {
            receipt.state = "NOT_LAUNCHED"
            receipt.error = "posix_spawn errno \(result)"
            try Self.save(receipt, to: record)
            try Self.check(result, "posix_spawn")
        }
        pid = child
        receipt.pid = child
        receipt.pgid = child
        receipt.state = "LAUNCHED"
        do {
            try Self.save(receipt, to: record)
        } catch {
            throw hold(error)
        }
    }

    func finish(stop: Bool = false, expectedExitCode: Int32 = 0, pump: () -> Void = {},
                observeGroup: ((pid_t) throws -> Bool)? = nil) async throws {
        guard receipt.state == "LAUNCHED" else {
            throw UpdateError("test.child", "Child custody is already recorded in \(record.path)")
        }
        var waitedTooLong = false
        do {
            if stop { try terminateIfRunning() }
            let deadline = ContinuousClock.now + (stop ? .seconds(12) : .seconds(6))
            while try !reap() {
                if ContinuousClock.now >= deadline {
                    guard !stop else { throw UpdateError("test.child", "Service reap deadline") }
                    waitedTooLong = true
                    try terminateIfRunning()
                    let reapDeadline = ContinuousClock.now + .seconds(2)
                    while try !reap() {
                        guard ContinuousClock.now < reapDeadline else {
                            throw UpdateError("test.child", "AX client reap deadline after SIGTERM")
                        }
                        await pause(pump)
                    }
                    break
                }
                await pause(pump)
            }
            let groupDeadline = ContinuousClock.now + .seconds(2)
            let group = observeGroup ?? Self.groupAbsent
            while try !group(pid) {
                guard ContinuousClock.now < groupDeadline else {
                    throw UpdateError("test.child", "Owned process group remained present after direct reap")
                }
                await pause(pump)
            }
            receipt.ownedGroupAbsent = true
            receipt.state = "CLOSED"
            try Self.save(receipt, to: record)
        } catch {
            throw hold(error)
        }
        guard !waitedTooLong, receipt.exitCode == expectedExitCode else {
            throw UpdateError("test.child_exit", "Child \(pid) failed (exit=\(String(describing: receipt.exitCode)), signal=\(String(describing: receipt.terminationSignal)), timedOut=\(waitedTooLong)); custody closed")
        }
    }

    // Inspect only this child. A port selected by the runner could have been
    // claimed before the service bound it, so a successful HTTP probe alone
    // would not identify our listener.
    func ownsLoopbackListener(port: UInt16) -> Bool {
        guard receipt.state == "LAUNCHED" else { return false }
        var descriptors = Array(repeating: proc_fdinfo(), count: 256)
        let bytes = descriptors.withUnsafeMutableBytes { buffer in
            proc_pidinfo(pid, PROC_PIDLISTFDS, 0, buffer.baseAddress, Int32(buffer.count))
        }
        let stride = MemoryLayout<proc_fdinfo>.stride
        guard bytes > 0, Int(bytes) % stride == 0 else { return false }
        let loopback = in_addr_t(INADDR_LOOPBACK).bigEndian
        for descriptor in descriptors.prefix(Int(bytes) / stride) where descriptor.proc_fdtype == PROX_FDTYPE_SOCKET {
            var socket = socket_fdinfo()
            let size = Int32(MemoryLayout<socket_fdinfo>.size)
            guard proc_pidfdinfo(pid, descriptor.proc_fd, PROC_PIDFDSOCKETINFO, &socket, size) == size,
                  socket.psi.soi_family == AF_INET, Int(socket.psi.soi_kind) == SOCKINFO_TCP else { continue }
            let tcp = socket.psi.soi_proto.pri_tcp
            if tcp.tcpsi_state == TSI_S_LISTEN,
               tcp.tcpsi_ini.insi_lport == Int32(port.bigEndian),
               tcp.tcpsi_ini.insi_laddr.ina_46.i46a_addr4.s_addr == loopback { return true }
        }
        return false
    }

    private func terminateIfRunning() throws {
        if try reap() { return }
        if Darwin.kill(pid, SIGTERM) == -1, errno != ESRCH {
            try Self.check(errno, "SIGTERM")
        }
    }

    private func reap() throws -> Bool {
        if receipt.directChildReaped { return true }
        var status: Int32 = 0
        let result = waitpid(pid, &status, WNOHANG)
        if result == 0 || (result == -1 && errno == EINTR) { return false }
        guard result == pid else { throw UpdateError("test.child", "waitpid errno \(errno)") }
        receipt.directChildReaped = true
        let signal = status & 0x7f
        if signal == 0 { receipt.exitCode = (status >> 8) & 0xff }
        else { receipt.terminationSignal = signal }
        return true
    }

    static func groupAbsent(_ pgid: pid_t) throws -> Bool {
        if Darwin.kill(-pgid, 0) == 0 { return false }
        let code = errno
        if code == ESRCH { return true }
        try check(code, "process group observation")
        return false
    }

    private func pause(_ pump: () -> Void) async {
        pump()
        await withCheckedContinuation { continuation in
            DispatchQueue.global().asyncAfter(deadline: .now() + .milliseconds(20)) {
                continuation.resume()
            }
        }
    }

    private func hold(_ error: Error) -> UpdateError {
        receipt.state = "HOLD"
        receipt.error = String(describing: error)
        do {
            try Self.save(receipt, to: record)
        } catch {
            // Keep the recorded spawn intent/identity and a separate log if the receipt write failed.
            let line = "FIELDLOG HOLD pid=\(pid) pgid=\(pid) path=\(record.path) receiptError=\(error)\n"
            try? FileHandle.standardError.write(contentsOf: Data(line.utf8))
        }
        return UpdateError("test.child_custody", "Preserve \(record.deletingLastPathComponent().path); child \(pid), group \(pid): \(receipt.error ?? "unknown")")
    }

    private static func save(_ receipt: Receipt, to path: URL, options: Data.WritingOptions = .atomic) throws {
        try JSONEncoder().encode(receipt).write(to: path, options: options)
    }

    private static func check(_ code: Int32, _ operation: String) throws {
        guard code == 0 else { throw UpdateError("test.child", "\(operation) errno \(code)") }
    }
}
#endif
