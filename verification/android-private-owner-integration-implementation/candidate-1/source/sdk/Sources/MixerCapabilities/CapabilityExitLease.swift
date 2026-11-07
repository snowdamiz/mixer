#if !os(WASI)
import Foundation

// A per-call native identity, never a guest-provided token. Neither terminal
// delivery nor worker return alone establishes the installed adapter's exit.
// All callbacks run after unlocking, and the observer is removed exactly once.
final class CapabilityExitLease: @unchecked Sendable {
    private let lock = NSLock()
    private var invocationHasReturned = false
    private var adapterHasExited = false
    private var observer: (@Sendable (CapabilityExitLease) -> Void)?

    init(observer: @escaping @Sendable (CapabilityExitLease) -> Void) { self.observer = observer }

    func invocationReturned() { report(invocationReturned: true) }
    func adapterExited() { report(invocationReturned: false) }

    private func report(invocationReturned: Bool) {
        lock.lock()
        if invocationReturned { invocationHasReturned = true } else { adapterHasExited = true }
        let callback: (@Sendable (CapabilityExitLease) -> Void)?
        if invocationHasReturned && adapterHasExited { callback = observer; observer = nil }
        else { callback = nil }
        lock.unlock()
        callback?(self)
    }
}
#endif
