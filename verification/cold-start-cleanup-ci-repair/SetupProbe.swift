import Foundation

// Verification-only scheduling gate in the retained derived activation module.
// It changes no stopped/current/retirement predicate or return value.
actor ColdStartSetupCIHooks {
    static let shared = ColdStartSetupCIHooks()
    private var armed = false
    private(set) var isEntered = false
    private var pending: CheckedContinuation<Void, Never>?
    func arm() { armed = true; isEntered = false }
    func pauseAfterKVSetup() async {
        guard armed else { return }
        await withCheckedContinuation { continuation in
            isEntered = true
            pending = continuation
        }
    }
    func release() {
        armed = false
        let continuation = pending
        pending = nil
        continuation?.resume()
    }
}
