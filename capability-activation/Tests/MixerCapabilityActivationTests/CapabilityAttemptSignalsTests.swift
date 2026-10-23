import Foundation
@testable import MixerExperimentalCapabilityRuntime
#if !SIGNALS_STANDALONE
import XCTest
@testable import MixerCapabilityActivation

@MainActor final class CapabilityAttemptSignalsTests: XCTestCase {
    func testGenerationAndStopGateCommit() async throws { try await SignalCases.commitGate() }
    func testIntentIsStickyAndSingleUse() async throws { try await SignalCases.stickyIntent() }
    func testLocalCausePrecedesResultingNativeCancellation() async throws { try await SignalCases.localFirst() }
    func testCheckedFailureSurvivesLaterLocalStop() async throws { try await SignalCases.bridgeFirst() }
    func testTerminalNotificationCoalescesUnderContention() async throws { try await SignalCases.coalescing() }
    func testCommitEntryAndStopSerialize() async throws { try await SignalCases.commitRace() }
}
#endif

private enum SignalCases {
    struct Failed: Error { let message: String }
    static func check(_ value: @autoclosure () -> Bool, _ message: String) throws {
        if !value() { throw Failed(message: message) }
    }
    static func rejects(_ operation: () throws -> Void) throws {
        var rejected = false
        do { try operation() } catch { rejected = true }
        try check(rejected, "Expected commit rejection")
    }
    static func failure(_ code: String, kind: ExperimentalCapabilityFailureKind = .guestTrap(.unreachable)) -> ExperimentalCapabilityFailure {
        ExperimentalCapabilityFailure(kind: kind, operation: .startup, code: code, nativeStatus: 2, location: nil)
    }
    static func commitGate() async throws {
        let signals = CapabilityAttemptSignals(generation: 7)
        try signals.requireCommitEntry(expectedGeneration: 7)
        try rejects { try signals.requireCommitEntry(expectedGeneration: 6) }
        try rejects { try signals.enterEffectsIntentCommit(expectedGeneration: 8) }
        try check(!signals.snapshot.effectsMayHaveOpened, "Stale generation set intent")
        signals.requestStop(.deadline)
        try rejects { try signals.requireCommitEntry(expectedGeneration: 7) }
        try rejects { try signals.enterEffectsIntentCommit(expectedGeneration: 7) }
        try check(!signals.snapshot.effectsMayHaveOpened, "Stopped attempt set intent")
        signals.finishNotifications()
    }
    static func stickyIntent() async throws {
        let signals = CapabilityAttemptSignals(generation: 1)
        try signals.enterEffectsIntentCommit(expectedGeneration: 1)
        try rejects { try signals.enterEffectsIntentCommit(expectedGeneration: 1) }
        signals.requestStop(.cancelled)
        signals.recordTerminalFailure(failure("cancelled", kind: .cancelled))
        try check(signals.snapshot.stopped && signals.snapshot.effectsMayHaveOpened, "Intent cleared on terminal failure")
        signals.finishNotifications()
    }
    static func localFirst() async throws {
        let signals = CapabilityAttemptSignals(generation: 1)
        signals.requestStop(.cancelled)
        let first = failure("cancelled", kind: .cancelled)
        signals.recordTerminalFailure(first)
        signals.recordTerminalFailure(failure("later"))
        guard case .local(.cancelled)? = signals.snapshot.firstCause else { throw Failed(message: "Local cancellation replaced") }
        try check(signals.snapshot.firstBridgeFailure == first, "First bridge facts replaced")
        signals.finishNotifications()
    }
    static func bridgeFirst() async throws {
        let signals = CapabilityAttemptSignals(generation: 1), first = failure("unreachable")
        signals.recordTerminalFailure(first)
        signals.requestStop(.cancelled); signals.requestStop(.closed)
        signals.recordTerminalFailure(failure("later", kind: .deadlineExceeded))
        guard case .bridge(let actual)? = signals.snapshot.firstCause else { throw Failed(message: "Checked failure replaced") }
        try check(actual == first && signals.snapshot.firstBridgeFailure == first, "First checked facts changed")
        signals.finishNotifications()
    }
    static func coalescing() async throws {
        let signals = CapabilityAttemptSignals(generation: 1), first = failure("first")
        signals.recordTerminalFailure(first)
        await withTaskGroup(of: Void.self) { group in
            for index in 0..<128 {
                group.addTask {
                    signals.recordTerminalFailure(failure("later-\(index)"))
                    signals.requestStop(.closed)
                }
            }
        }
        signals.finishNotifications()
        var count = 0
        for await _ in signals.notifications { count += 1 }
        try check(count == 1 && signals.snapshot.firstBridgeFailure == first, "Notification was not coalesced")
    }
    static func commitRace() async throws {
        for _ in 0..<128 {
            let signals = CapabilityAttemptSignals(generation: 1)
            let committed = await withTaskGroup(of: Bool.self, returning: Int.self) { group in
                group.addTask {
                    do { try signals.enterEffectsIntentCommit(expectedGeneration: 1); return true }
                    catch { return false }
                }
                group.addTask { signals.requestStop(.cancelled); return false }
                var successes = 0
                for await success in group { if success { successes += 1 } }
                return successes
            }
            try check(signals.snapshot.stopped, "Stop was lost")
            try check(signals.snapshot.effectsMayHaveOpened == (committed == 1), "Commit-entry result disagrees with sticky intent")
            try rejects { try signals.requireCommitEntry(expectedGeneration: 1) }
            signals.finishNotifications()
        }
    }
}

#if SIGNALS_STANDALONE
@main struct SignalProbe {
    static func main() async throws {
        try await SignalCases.commitGate(); try await SignalCases.stickyIntent()
        try await SignalCases.localFirst(); try await SignalCases.bridgeFirst()
        try await SignalCases.coalescing(); try await SignalCases.commitRace()
        print("PASS 6 signal cases including128 commit races and128 concurrent terminal reports")
    }
}
#endif
