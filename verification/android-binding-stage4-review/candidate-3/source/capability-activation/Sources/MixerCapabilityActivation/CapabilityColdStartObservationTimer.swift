import Foundation
import Dispatch

/// One one-shot source per enabled attempt. The handlers capture signals and a
/// bounded completion latch. Its one waiter may retain a counted closing frame;
/// that frame must first return/drop all concrete resource aliases.
final class CapabilityColdStartObservationTimer: @unchecked Sendable {
    private static let queue = DispatchQueue(label: "mixer.capability.observation", qos: .utility)
    private let source: any DispatchSourceTimer
    private let completion: CapabilityColdStartTimerCompletion
    init(seconds: UInt64, signals: CapabilityAttemptSignals) throws {
        let nanos = seconds.multipliedReportingOverflow(by: 1_000_000_000)
        let end = DispatchTime.now().uptimeNanoseconds.addingReportingOverflow(nanos.partialValue)
        guard !nanos.overflow, !end.overflow else { throw coldStartError("observation_clock") }
        let completion = CapabilityColdStartTimerCompletion(), generation = signals.generation
        let source = DispatchSource.makeTimerSource(queue: Self.queue)
        self.source = source; self.completion = completion
        source.setEventHandler { [completion, signals] in
            completion.didFire()
            signals.recordControlWake(expectedGeneration: generation)
        }
        source.setCancelHandler { [completion] in completion.didCancel() }
        source.schedule(deadline: DispatchTime(uptimeNanoseconds: end.partialValue), repeating: .never)
        source.activate()
    }
    var fired: Bool { completion.fired }
    func cancel() { source.cancel() }
    func waitForCancellation() async { await completion.wait() }
    deinit { source.cancel() }
}

private final class CapabilityColdStartTimerCompletion: @unchecked Sendable {
    private let lock = NSLock()
    private var didFireValue = false
    private var cancelled = false
    private var waitIssued = false
    private var waiter: CheckedContinuation<Void, Never>?
    var fired: Bool { lock.lock(); defer { lock.unlock() }; return didFireValue }
    func didFire() { lock.lock(); didFireValue = true; lock.unlock() }
    func didCancel() {
        lock.lock(); cancelled = true; let old = waiter; waiter = nil; lock.unlock()
        old?.resume()
    }
    func wait() async {
        await withCheckedContinuation { continuation in
            lock.lock(); precondition(!waitIssued); waitIssued = true
            if cancelled { lock.unlock(); continuation.resume() }
            else { waiter = continuation; lock.unlock() }
        }
    }
}
