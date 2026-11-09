import Foundation
#if !MIXER_BOUNDARY_STANDALONE
import Testing
@testable import MixerBuild
@Test func ownedCommandControlSchedules() throws { _ = try OwnedCommandProof.run() }
#endif

private struct ProofFailure: Error, CustomStringConvertible { let description: String }
private func require(_ condition: @autoclosure () -> Bool, _ detail: String) throws {
    if !condition() { throw ProofFailure(description: detail) }
}
private final class FakeCommand: OwnedCommandControl {
    var tick = 0, readyAt = 0, exitAt = 0, reapDelay = 0, absentAt = 0
    var exitCode: Int32 = 0, setupError: Int32 = 0, readinessError: Int32 = 0
    var fail: String?, failureTick: Int?, backwardsAt: Int?
    var stdout: [StreamObservation] = [.eof], stderr: [StreamObservation] = [.eof]
    var calls: [String] = [], receipts: [CommandCustodyReceipt] = []
    var command: [String] = [], directory: URL?, environment: [String: String] = [:]
    var killedAt: Int?, reaped = false, stdoutEOF = false, stderrEOF = false, absent = false
    var persistFailure: String?
    private func operation(_ name: String) throws {
        calls.append(name)
        if fail == name && (failureTick == nil || tick >= failureTick!) { throw ProofFailure(description: "injected \(name)") }
    }
    func persist(_ receipt: CommandCustodyReceipt) throws {
        receipts.append(receipt)
        if persistFailure == receipt.state { throw ProofFailure(description: "injected receipt \(receipt.state)") }
    }
    func monotonicNow() throws -> UInt64 {
        try operation("clock")
        if backwardsAt == tick { return 1 }
        return 1_000_000_000 + UInt64(tick) * 100_000_000
    }
    func launch(command: [String], directory: URL?, environment: [String: String]) throws -> OwnedLaunch {
        try operation("launch")
        try require(receipts.last?.state == "INTENT", "intent must precede fork")
        self.command = command; self.directory = directory; self.environment = environment
        return OwnedLaunch(pid: 90001, setupError: setupError)
    }
    func readiness() throws -> LaunchReadiness {
        try operation("ready")
        if readinessError != 0 { return .failed(readinessError) }
        return tick >= readyAt ? .ready : .pending
    }
    func release() throws {
        try operation("release")
        try require(receipts.last?.state == "OWNED_GATE_CLOSED", "durable owned identity must precede release")
        try require(receipts.last?.ownedPGID == 90001 && receipts.last?.ownedSession == 90001, "session identity")
    }
    func read(_ stream: CommandStream) throws -> StreamObservation {
        try operation("read-" + stream.rawValue)
        try require(!(stream == .stdout ? stdoutEOF : stderrEOF), "no reread after EOF")
        let next: StreamObservation
        if stream == .stdout { next = stdout.isEmpty ? .pending : stdout.removeFirst() }
        else { next = stderr.isEmpty ? .pending : stderr.removeFirst() }
        if case .eof = next { if stream == .stdout { stdoutEOF = true } else { stderrEOF = true } }
        return next
    }
    func exitedWithoutReaping() throws -> Bool { try operation("peek"); return tick >= exitAt }
    func killOwnedGroup() throws {
        try operation("kill"); try require(!reaped, "never signal after reap")
        try require(killedAt == nil, "at most one group kill"); killedAt = tick
    }
    func reap() throws -> Int32? {
        try operation("reap"); try require(!reaped, "reap only once")
        if tick < (killedAt ?? exitAt) + reapDelay { return nil }
        reaped = true; return exitCode
    }
    func groupAbsent() throws -> Bool {
        try operation("probe"); try require(reaped, "absence observed after direct-child reap")
        absent = tick >= absentAt; return absent
    }
    func pause() throws { try operation("pause"); tick += 1 }
    func close() throws {
        try operation("close")
        try require(reaped && stdoutEOF && stderrEOF && absent, "all four facts precede descriptor closure")
    }
}

enum OwnedCommandProof {
    static func run() throws -> Int {
        var groups = 0
        let policy = ProcessPolicy(name: "proof", runtimeSeconds: 1, cleanupSeconds: 1, generatedOutputBytes: 100)
        let argv = ["printf", "%s", "$(echo secret); \u{60}pwd\u{60}"]
        let cwd = URL(fileURLWithPath: "/proof/cwd")
        func execute(_ fake: FakeCommand, _ selected: ProcessPolicy = policy, used: UInt64 = 0, limit: UInt64 = 1000) throws -> CommandResult {
            let execution = OwnedCommandExecution(command: argv, directory: cwd, policy: selected,
                aggregateLimit: limit, aggregateUsed: used, control: fake, save: fake.persist)
            return try execution.execute(directory: cwd, environment: ["EXACT": "selected"])
        }
        func unknown(_ fake: FakeCommand, _ selected: ProcessPolicy = policy) throws {
            do { _ = try execute(fake, selected); throw ProofFailure(description: "expected UNKNOWN") }
            catch is UnknownCommandCustody { }
            try require(fake.receipts.last?.state == "UNKNOWN", "UNKNOWN is sticky in durable receipt")
            try require(!fake.receipts.contains(where: { $0.state == "TERMINAL" && !$0.terminalCustody }), "never false terminal")
        }
        do {
            let f = FakeCommand(); f.stdout = [.bytes(Data("literal".utf8)), .eof]
            let r = try execute(f)
            try require(r.succeeded && r.output == "literal" && !r.outputTruncated, "normal command output")
            try require(f.command == argv && f.directory == cwd && f.environment == ["EXACT": "selected"], "literal argv/cwd/selected environment")
            try require(f.receipts.last?.terminalCustody == true && f.receipts.last?.state == "TERMINAL", "terminal requires all facts")
            groups += 1
        }
        do {
            let f = FakeCommand(); f.exitCode = 7; f.stderr = [.bytes(Data("diagnostic".utf8)), .eof]
            let r = try execute(f)
            try require(r.exitCode == 7 && !r.succeeded && r.output == "diagnostic", "nonzero status/diagnostics preserved")
            groups += 1
        }
        do {
            let f = FakeCommand(); f.exitAt = 200
            f.stdout = Array(repeating: .bytes(Data(repeating: 120, count: 65_536)), count: 144) + [.bytes(Data("tail".utf8)), .eof]
            let r = try execute(f, .developmentBuild, limit: 1 << 30)
            try require(r.succeeded && r.output.utf8.count == 8 * 1_048_576 && r.outputTruncated && r.output.hasSuffix("tail"), "9MiB+tail succeeds with exact 8MiB tail")
            try require(f.receipts.last?.generatedBytes == 9 * 1_048_576 + 4, "generated count independent from retention")
            groups += 1
        }
        // Delay each terminal fact independently, then vary both streams, reap and group lifetime together.
        for outDelay in 0...3 {
            for errDelay in 0...3 {
                for reapDelay in 0...3 {
                    for groupDelay in 0...3 {
                        let f = FakeCommand(); f.reapDelay = reapDelay; f.absentAt = groupDelay
                        f.stdout = Array(repeating: .pending, count: outDelay) + [.eof]
                        f.stderr = Array(repeating: .pending, count: errDelay) + [.eof]
                        _ = try execute(f)
                        try require(f.tick >= max(outDelay, errDelay, reapDelay, groupDelay), "no return before last required fact")
                        try require(!f.calls.contains("kill"), "natural exit never signals")
                        groups += 1
                    }
                }
            }
        }
        do {
            let f = FakeCommand(); f.exitAt = 100
            do { _ = try execute(f); throw ProofFailure(description: "deadline should fail") }
            catch let e as MixerFailure { try require(e.code == "process.runtime-deadline", "runtime failure with terminal custody") }
            try require(f.receipts.last?.terminalCustody == true && f.tick >= 10, "runtime and cleanup independently budgeted")
            groups += 1
        }
        for aggregate in [false, true] {
            let f = FakeCommand(); f.stdout = [.bytes(Data(repeating: 65, count: 101)), .eof]
            do { _ = try execute(f, used: aggregate ? 950 : 0); throw ProofFailure(description: "output budget should fail") }
            catch let e as MixerFailure {
                // Per-command budget takes precedence when both are crossed.
                try require(e.code == "process.generated-output-limit", "generated-output failure")
            }
            try require(f.receipts.last?.terminalCustody == true, "overflow still completes custody")
            groups += 1
        }
        do {
            let f = FakeCommand(); f.stdout = [.bytes(Data(repeating: 65, count: 51)), .eof]
            do { _ = try execute(f, used: 950); throw ProofFailure(description: "aggregate budget should fail") }
            catch let e as MixerFailure { try require(e.code == "process.aggregate-output-limit", "aggregate output independent from per-command output") }
            groups += 1
        }
        // Failure at each OS-facing boundary must end the process-operation trace immediately.
        for operation in ["clock", "launch", "ready", "release", "read-stdout", "read-stderr", "peek", "kill", "reap", "probe", "pause", "close"] {
            let f = FakeCommand(); f.fail = operation
            if operation == "kill" { f.exitAt = 100 }
            if operation == "pause" { f.stdout = [.pending, .eof] }
            try unknown(f)
            try require(f.calls.last == operation, "no process operation after \(operation) uncertainty")
            groups += 1
        }
        for phase in ["INTENT", "FORKED_GATE_CLOSED", "OWNED_GATE_CLOSED", "RUNNING", "CLEANUP_REQUESTED", "CLEANING", "TERMINAL"] {
            let f = FakeCommand(); f.persistFailure = phase
            try unknown(f)
            if phase == "INTENT" { try require(f.calls == ["clock"], "failed intent prevents launch") }
            if phase == "OWNED_GATE_CLOSED" { try require(!f.calls.contains("release"), "failed identity persistence prevents exec") }
            groups += 1
        }
        do { let f = FakeCommand(); f.setupError = 5; try unknown(f); try require(!f.calls.contains("release") && !f.calls.contains("kill"), "failed setup freezes without guessing ownership"); groups += 1 }
        do { let f = FakeCommand(); f.readyAt = 100; try unknown(f); try require(!f.calls.contains("release") && !f.calls.contains("kill"), "unconfirmed readiness deadline fails closed"); groups += 1 }
        do { let f = FakeCommand(); f.stderr = []; try unknown(f); try require(f.stdoutEOF && !f.stderrEOF, "one EOF is insufficient"); groups += 1 }
        do { let f = FakeCommand(); f.reapDelay = 100; try unknown(f); try require(!f.calls.contains("probe"), "no absence claim without reap"); groups += 1 }
        do { let f = FakeCommand(); f.absentAt = 100; try unknown(f); try require(!f.calls.contains("kill"), "residual group is observed only; no signal after natural exit"); groups += 1 }
        do { let f = FakeCommand(); f.stdout = [.pending, .eof]; f.backwardsAt = 1; try unknown(f); try require(f.calls.last == "clock", "backwards clock freezes operations"); groups += 1 }
        do {
            let f = FakeCommand(); f.stdout = [.bytes(Data(repeating: 1, count: 100)), .eof]
            _ = try execute(f, limit: 100)
            try require(f.receipts.last?.stopReason == nil, "exact budget inclusive")
            groups += 1
        }
        do {
            let context = ProcessExecutionContext(receiptDirectory: URL(fileURLWithPath: "/never-created"), aggregateGeneratedOutputBytes: 200)
            let f = FakeCommand(); f.fail = "probe"
            do { _ = try context.run(command: argv, directory: cwd, environment: [:], policy: policy,
                controlFactory: { f }, receiptFactory: { _ in ("fake-receipt", f.persist) }); throw ProofFailure(description: "expected held context") }
            catch let e as MixerFailure { try require(e.code == "process.custody-unknown", "context records hold") }
            let before = f.calls
            do { _ = try context.run(command: argv, directory: cwd, environment: [:], policy: policy,
                controlFactory: { f }, receiptFactory: { _ in throw ProofFailure(description: "must not prepare new receipt") }); throw ProofFailure(description: "expected closed admission") }
            catch let e as MixerFailure { try require(e.code == "process.custody-held", "UNKNOWN admission remains closed") }
            try require(f.calls == before, "zero process operations on held admission")
            groups += 1
        }
        do {
            let context = ProcessExecutionContext(receiptDirectory: URL(fileURLWithPath: "/never-created"), aggregateGeneratedOutputBytes: 2)
            let f = FakeCommand(); f.stdout = [.bytes(Data([1,2])), .eof]
            _ = try context.run(command: argv, directory: nil, environment: [:], policy: policy,
                controlFactory: { f }, receiptFactory: { _ in ("fake-receipt", f.persist) })
            let before = f.calls
            do { _ = try context.run(command: argv, directory: nil, environment: [:], policy: policy,
                controlFactory: { f }, receiptFactory: { _ in ("fake-receipt", f.persist) }); throw ProofFailure(description: "expected exhausted context") }
            catch let e as MixerFailure { try require(e.code == "process.aggregate-output-limit", "aggregate carried across commands") }
            try require(f.calls == before, "exhausted budget rejects before process operations")
            groups += 1
        }
        do { let f = FakeCommand(); f.readinessError = 13; try unknown(f); try require(!f.calls.contains("release"), "failed readiness never executes argv"); groups += 1 }
        do { let f = FakeCommand(); f.stdout = [.bytes(Data())]; try unknown(f); try require(f.calls.last == "read-stdout", "zero bytes must be explicit EOF"); groups += 1 }
        do {
            let f = FakeCommand(); f.fail = "probe"; f.persistFailure = "UNKNOWN"
            do { _ = try execute(f); throw ProofFailure(description: "expected unknown with failed hold write") }
            catch let error as UnknownCommandCustody { try require(error.description.contains("HOLD persistence failed"), "failed durable hold is reported") }
            try require(f.calls.last == "probe", "hold write failure does not resume process operations")
            groups += 1
        }
        do {
            let f = FakeCommand(); f.stdout = [.bytes(Data("out1".utf8)), .bytes(Data("out2".utf8)), .eof]
            f.stderr = [.bytes(Data("err1".utf8)), .bytes(Data("err2".utf8)), .eof]
            let result = try execute(f)
            try require(result.output == "out1err1out2err2", "combined output follows read-observation order")
            groups += 1
        }
        do {
            let context = ProcessExecutionContext(receiptDirectory: URL(fileURLWithPath: "/never-created"))
            let f = FakeCommand()
            do { _ = try context.run(command: argv, directory: cwd, environment: [:], policy: policy,
                controlFactory: { f }, receiptFactory: { _ in throw ProofFailure(description: "directory persistence failure") }); throw ProofFailure(description: "expected receipt failure") }
            catch let e as MixerFailure { try require(e.code == "process.receipt", "receipt preparation fails before launch") }
            try require(f.calls.isEmpty, "no process operations on failed receipt preparation")
            do { _ = try context.run(command: argv, directory: cwd, environment: [:], policy: policy,
                controlFactory: { f }, receiptFactory: { _ in ("fake", f.persist) }); throw ProofFailure(description: "expected sticky admission hold") }
            catch let e as MixerFailure { try require(e.code == "process.custody-held", "failed preparation also closes admission") }
            try require(f.calls.isEmpty, "held preparation cannot launch")
            groups += 1
        }
        return groups
    }
}
