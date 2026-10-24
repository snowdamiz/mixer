import Foundation

/// Verification-only scheduling around the real beginNotification boundary.
/// It changes no admission predicate, reported milestone, timer, or store effect.
final class MilestoneCIProbe: @unchecked Sendable {
    static let shared = MilestoneCIProbe()
    private let lock = NSLock()
    private weak var control: CapabilityColdStartControl?
    private var signals: CapabilityAttemptSignals?
    private var armed = false, entered = false, released = false
    private var busy = 0, retries = 0
    private var reports: [String] = []
    func install(_ control: CapabilityColdStartControl, _ signals: CapabilityAttemptSignals) {
        lock.lock(); self.control = control; self.signals = signals; lock.unlock()
    }
    func arm() { lock.lock(); armed = true; entered = false; released = false; busy = 0; retries = 0; reports = []; lock.unlock() }
    private func enter() -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard armed else { return false }; armed = false; entered = true; return true
    }
    private var wasReleased: Bool { lock.lock(); defer { lock.unlock() }; return released }
    var isEntered: Bool { lock.lock(); defer { lock.unlock() }; return entered }
    var retryCount: Int { lock.lock(); defer { lock.unlock() }; return retries }
    var actualBusyCount: Int { lock.lock(); defer { lock.unlock() }; return busy }
    var reported: [String] { lock.lock(); defer { lock.unlock() }; return reports }
    var timerFired: Bool { lock.lock(); let value = control; lock.unlock(); return value?.timerFired == true }
    func wake() { lock.lock(); let value = signals; lock.unlock(); if let value { value.recordControlWake(expectedGeneration: value.generation) } }
    func pauseNotification() async {
        guard enter() else { return }
        print("MILESTONE_CI notification-admitted timerFired=\(timerFired)")
        while !wasReleased { try? await Task.sleep(for: .milliseconds(1)) }
    }
    func recordBusy(_ kind: CapabilityColdStartOperationKind) {
        guard case .milestone = kind else { return }
        lock.lock(); busy += 1; let first = busy == 1, held = entered && !released; lock.unlock()
        if first { print("MILESTONE_CI actual-busy held=\(held)") }
    }
    func recordRetry() { lock.lock(); retries += 1; lock.unlock() }
    func recordReport(_ id: String) { lock.lock(); reports.append(id); lock.unlock(); print("MILESTONE_CI actual-report \(id)") }
    func release() { lock.lock(); released = true; lock.unlock() }
    func reset() { release(); lock.lock(); control = nil; signals = nil; lock.unlock() }
}
