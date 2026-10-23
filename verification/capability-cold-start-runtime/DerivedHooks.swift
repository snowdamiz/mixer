import Foundation

/// Captured-copy controls only. No accepting validation or replacement adapter.
enum ColdStartDerivedHooks {
    static let startupFailure = ColdStartDerivedGate()
    static let ordinaryTail = ColdStartDerivedGate()
    static let adapterRetirement = ColdStartDerivedSyncGate()
}
final class ColdStartDerivedSyncGate: @unchecked Sendable {
    private let condition = NSCondition(); private var armed = false, entered = false, released = false
    func arm() { condition.lock(); armed = true; entered = false; released = false; condition.unlock() }
    var reached: Bool { condition.lock(); defer { condition.unlock() }; return entered }
    func hold() {
        condition.lock(); guard armed else { condition.unlock(); return }; entered = true
        while !released { condition.wait() }
        armed = false; condition.unlock()
    }
    func release() { condition.lock(); released = true; condition.broadcast(); condition.unlock() }
}
actor ColdStartDerivedGate {
    private var armed = false, entered = false, released = false
    func arm() { armed = true; entered = false; released = false }
    func hold() async {
        guard armed else { return }
        entered = true
        while !released { await Task.yield() }
        armed = false
    }
    func wait() async throws {
        let deadline = ContinuousClock.now.advanced(by: .seconds(8))
        while !entered {
            guard ContinuousClock.now < deadline else { throw NSError(domain: "derived.gate",code: 1) }
            await Task.yield()
        }
    }
    func release() { released = true }
}
