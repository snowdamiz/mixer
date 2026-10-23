import Foundation

// Test-only facts. Hooks count entry immediately before actual C enable, command
// admission and cleanup Task entry. No completion, enable or drain is fabricated.
enum EnableReviewHooks {
    struct State {
        var nativeEnables = 0
        var commands = 0
        var terminals = 0
        var cleanupSawTerminalCounts: [Int] = []
    }
    static let state = Locked(State())
    static func beforeNativeEnable() { state.withLock { $0.nativeEnables += 1 } }
    static func commandAdmitted() { state.withLock { $0.commands += 1 } }
    static func terminal() { state.withLock { $0.terminals += 1 } }
    static func cleanupEntered() { state.withLock { $0.cleanupSawTerminalCounts.append($0.terminals) } }
}

final class EnableDerivedSink: @unchecked Sendable, CapabilityBridgeTerminalObserver, CapabilityBridgeRetirementObserver {
    private let state = Locked((failures: [ExperimentalCapabilityFailure](), retires: 0, events: [String]()))
    func recordTerminalFailure(_ failure: ExperimentalCapabilityFailure) {
        state.withLock { $0.failures.append(failure); $0.events.append("terminal") }
        EnableReviewHooks.terminal()
    }
    func recordRetired() { state.withLock { $0.retires += 1; $0.events.append("retired") } }
    var value: (failures: [ExperimentalCapabilityFailure], retires: Int, events: [String]) { state.withLock { $0 } }
}
final class EnableDerivedGate: @unchecked Sendable {
    private let condition = NSCondition()
    private var open = false
    private var began = false
    var entered: Bool { condition.lock(); defer { condition.unlock() }; return began }
    func hold() {
        condition.lock(); began = true; let end = Date().addingTimeInterval(5)
        while !open { if !condition.wait(until: end) { break } }; condition.unlock()
    }
    func release() { condition.lock(); open = true; condition.broadcast(); condition.unlock() }
}
