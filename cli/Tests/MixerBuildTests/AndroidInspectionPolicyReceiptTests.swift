import Foundation
import Testing
@testable import MixerBuild

private struct InspectionFailure: Error { let message: String }
private final class InspectionSchedule: OwnedCommandControl {
    var second: UInt64 = 1
    var exitsAt: UInt64 = 32
    var output = Data()
    var delivered = false, killed = false
    var code: Int32 = 0
    var failProbe = false, failPersist = false
    var calls: [String] = []
    var receipts: [CommandCustodyReceipt] = []
    func monotonicNow() throws -> UInt64 { calls.append("clock"); return second * 1_000_000_000 }
    func launch(command: [String], directory: URL?, environment: [String:String]) throws -> OwnedLaunch { calls.append("launch"); return OwnedLaunch(pid: 99001, setupError: 0) }
    func readiness() throws -> LaunchReadiness { calls.append("ready"); return .ready }
    func release() throws { calls.append("release") }
    func read(_ stream: CommandStream) throws -> StreamObservation {
        calls.append("read")
        if stream == .stderr { return .eof }
        if !delivered { delivered = true; return .bytes(output) }
        return .eof
    }
    func exitedWithoutReaping() throws -> Bool { calls.append("peek"); return second >= exitsAt }
    func killOwnedGroup() throws { calls.append("kill"); killed = true }
    func reap() throws -> Int32? { calls.append("reap"); return killed || second >= exitsAt ? code : nil }
    func groupAbsent() throws -> Bool { calls.append("probe"); if failProbe { throw InspectionFailure(message: "probe") }; return true }
    func pause() throws { calls.append("pause"); second += 1 }
    func close() throws { calls.append("close") }
    func persist(_ receipt: CommandCustodyReceipt) throws {
        receipts.append(receipt)
        if failPersist && receipt.state == "RUNNING" { throw InspectionFailure(message: "receipt") }
    }
    func run(_ argv: [String], _ policy: ProcessPolicy) throws -> CommandResult {
        let execution = OwnedCommandExecution(command: argv, directory: nil, policy: policy,
            aggregateLimit: 8 << 30, aggregateUsed: 0, control: self, save: persist)
        return try execution.execute(directory: nil, environment: [:])
    }
}

@Suite(.serialized) struct AndroidInspectionPolicyReceiptTests {
    let inventory = """
    {"schema":1,"sdk_id":"aarch64-unknown-linux-android28","abi":"arm64-v8a","min_api":28,"target_api":37,"swift_version":"fixture exact Swift6.3.3","javac_version":"javac 25.0.1","java_version":"fixture","python_version":"fixture","tools":{},"metadata":{},"distributions":{},"sdk_search_path":"/fixture"}
    """
    @Test func actualInspectionCallsiteUsesSeparatePolicyAndUnchangedValidation() throws {
        var seen = false
        let identity = try AndroidProject.inspectToolchain { argv, policy in
            seen = true
            #expect(argv.count == 3 && argv[0] == "python3" && argv[2] == "inspect")
            #expect(argv[1].hasSuffix("/Resources/android-build.py"))
            #expect(policy.name == "local-full-android-toolchain-inspection")
            #expect(policy.runtimeSeconds == 180 && policy.cleanupSeconds == 60 && policy.generatedOutputBytes == 64 << 20)
            let schedule = InspectionSchedule(); schedule.output = Data(inventory.utf8)
            let result = try schedule.run(argv, policy)
            #expect(schedule.second >= 32 && !schedule.killed)
            #expect(schedule.receipts.last?.terminalCustody == true)
            return result
        }
        #expect(seen && identity.min_api == 28 && identity.target_api == 37)
        #expect(ProcessPolicy.toolInspection.runtimeSeconds == 30)
        let old = InspectionSchedule(); old.output = Data(inventory.utf8)
        do { _ = try old.run(["python3", "android-build.py", "inspect"], .toolInspection); Issue.record("old30 must stop") }
        catch let error as MixerFailure { #expect(error.code == "process.runtime-deadline") }
        #expect(old.killed && old.receipts.last?.terminalCustody == true)
    }
    @Test func actualCallsiteRefusesNonzeroTruncatedMalformedAndExceptions() throws {
        for failure in 0..<4 {
            do {
                _ = try AndroidProject.inspectToolchain { argv, _ in
                    if failure == 3 { throw InspectionFailure(message: "runner") }
                    return CommandResult(command: argv, exitCode: failure == 0 ? 7 : 0,
                        output: failure == 2 ? "{bad" : inventory, outputTruncated: failure == 1)
                }
                Issue.record("inspection refusal missing")
            } catch { }
        }
    }
    @Test func fullPolicyStillStopsLateAndOversizeOutput() throws {
        let late = InspectionSchedule(); late.output = Data(inventory.utf8); late.exitsAt = 183
        do { _ = try AndroidProject.inspectToolchain(run: late.run); Issue.record("late must stop") }
        catch let error as MixerFailure { #expect(error.code == "process.runtime-deadline") }
        #expect(late.receipts.last?.terminalCustody == true)
        let huge = InspectionSchedule(); huge.output = Data(repeating: 65, count: (64 << 20) + 1)
        do { _ = try AndroidProject.inspectToolchain(run: huge.run); Issue.record("oversize must stop") }
        catch let error as MixerFailure { #expect(error.code == "process.generated-output-limit") }
        #expect(huge.receipts.last?.generatedBytes == (64 << 20) + 1)
        #expect(huge.receipts.last?.outputTruncated == true && huge.receipts.last?.terminalCustody == true)
    }
    @Test func unknownAndReceiptFailureFreezeAtActualInspectionCallsite() throws {
        for persistence in [false, true] {
            let f = InspectionSchedule(); f.output = Data(inventory.utf8)
            f.failProbe = !persistence; f.failPersist = persistence
            do { _ = try AndroidProject.inspectToolchain(run: f.run); Issue.record("UNKNOWN must stop") }
            catch is UnknownCommandCustody { }
            #expect(f.receipts.last?.state == "UNKNOWN")
            #expect(f.receipts.last?.terminalCustody == false)
            #expect(f.calls.last == (persistence ? "release" : "probe"))
        }
    }
}
