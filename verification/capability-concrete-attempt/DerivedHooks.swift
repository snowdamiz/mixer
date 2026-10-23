import Foundation
import MixerUpdates

// Fixed derived-only scheduling/fault controls. No service, validator, result or
// exit callback is accepted and no production build contains these hooks.
enum ConcreteProbeHooks {
    private static let lock = NSLock()
    nonisolated(unsafe) private static var setupGate: ConcreteProbeGate?
    nonisolated(unsafe) private static var methodGate: ConcreteProbeGate?
    nonisolated(unsafe) private static var storageFault = false
    nonisolated(unsafe) private static var bridges = 0
    nonisolated(unsafe) private static var waiters = 0
    static func holdSetup(_ gate: ConcreteProbeGate) { lock.lock(); setupGate = gate; lock.unlock() }
    static func holdMethod(_ gate: ConcreteProbeGate) { lock.lock(); methodGate = gate; lock.unlock() }
    static func failAfterStorage() { lock.lock(); storageFault = true; lock.unlock() }
    static func afterStorage() throws {
        lock.lock(); let fail = storageFault; lock.unlock()
        if fail { throw UpdateError("test.concrete.partial", "Fixed derived fault after returned KV initializer") }
    }
    static func afterSetupSession() async { if let gate = lockedSetup() { await gate.pause() } }
    static func afterStartup() async { if let gate = lockedMethod() { await gate.pause() } }
    private static func lockedSetup() -> ConcreteProbeGate? { lock.lock(); defer { lock.unlock() }; return setupGate }
    private static func lockedMethod() -> ConcreteProbeGate? { lock.lock(); defer { lock.unlock() }; return methodGate }
    static func bridgeRetired() { lock.lock(); bridges += 1; lock.unlock() }
    static func waiterInstalled() { lock.lock(); waiters += 1; lock.unlock() }
    static var observations: (bridges: Int,waiters: Int) { lock.lock(); defer { lock.unlock() }; return (bridges,waiters) }
}
final class ConcreteProbeGate: @unchecked Sendable {
    private let lock = NSLock()
    private var began = false, open = false
    private var waiter: CheckedContinuation<Void,Never>?
    var entered: Bool { lock.lock(); defer { lock.unlock() }; return began }
    func pause() async {
        await withCheckedContinuation { continuation in
            lock.lock(); began = true
            if open { lock.unlock(); continuation.resume() }
            else { precondition(waiter == nil); waiter = continuation; lock.unlock() }
        }
    }
    func release() { lock.lock(); open = true; let c = waiter; waiter = nil; lock.unlock(); c?.resume() }
}
