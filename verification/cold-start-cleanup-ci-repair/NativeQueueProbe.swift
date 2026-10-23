import Foundation

// Verification-only observation AFTER the real DispatchQueue.async submission.
// It neither replaces that submission nor alters the queued native worker.
enum NativeSubmissionCIProbe {
    private final class State: @unchecked Sendable {
        let lock = NSLock()
        var value = 0
    }
    private static let state = State()
    static func reset() { state.lock.lock(); state.value = 0; state.lock.unlock() }
    static var count: Int { state.lock.lock(); defer { state.lock.unlock() }; return state.value }
    static func recordEnqueued() { state.lock.lock(); state.value += 1; state.lock.unlock() }
}
