#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
import Foundation
import CMixerUITransport
import CMixerUIAndroidHostBridge

struct CapabilityAndroidProgressSnapshot: Sendable {
    let sequence: UInt64
    let callbackFence: UInt64
    let entryFence: UInt64
    let fault: Int32
}
/// Permanent process storage: no facade/resource reference survives a hook.
final class CapabilityAndroidProgressCell: @unchecked Sendable {
    private let lock = NSLock()
    private var sequence: UInt64 = 0
    private var issued: UInt64 = 0
    private var callbackFence: UInt64 = 0
    private var entryFence: UInt64 = 0
    private var fault: Int32 = 0
    private var waiter: (UInt64, CheckedContinuation<Void, Never>)?
    var snapshot: CapabilityAndroidProgressSnapshot {
        lock.lock(); defer { lock.unlock() }
        return .init(sequence: sequence, callbackFence: callbackFence, entryFence: entryFence, fault: fault)
    }
    @inline(never)
    func register(after expected: UInt64, _ incoming: CheckedContinuation<Void, Never>) -> UInt64? {
        lock.lock(); defer { lock.unlock() }
        guard fault == 0, sequence == expected else { return nil }
        guard waiter == nil else { fault = Int32(MXUIT_INVALID.rawValue); return nil }
        guard issued < .max else { fault = Int32(MXUIT_EXHAUSTED.rawValue); return nil }
        issued += 1; waiter = (issued, incoming); return issued
    }
    func cancel(_ token: UInt64) -> CheckedContinuation<Void, Never>? {
        lock.lock(); defer { lock.unlock() }
        guard waiter?.0 == token else { return nil }; let result = waiter?.1; waiter = nil; return result
    }
    func merge(callback: UInt64, entry: UInt64, fault incoming: Int32) -> CheckedContinuation<Void, Never>? {
        lock.lock(); defer { lock.unlock() }
        callbackFence = max(callbackFence, callback); entryFence = max(entryFence, entry)
        if fault == 0, incoming != 0 { fault = incoming }
        if sequence < .max { sequence += 1 } else if fault == 0 { fault = Int32(MXUIT_EXHAUSTED.rawValue) }
        let result = waiter?.1; waiter = nil; return result
    }
}
private final class CapabilityAndroidReclaimAttempt: @unchecked Sendable {
    private let lock = NSLock()
    private var result: Int32?
    func set(_ value: Int32) { lock.lock(); result = value; lock.unlock() }
    var value: Int32? { lock.lock(); defer { lock.unlock() }; return result }
}
final class CapabilityAndroidProgress: Sendable {
    static let shared = CapabilityAndroidProgress()
    let cells = (0..<16).map { _ in CapabilityAndroidProgressCell() }
    private init() {}
    /// Registration plus mandatory second actual reclaim defeats both lost-wake
    /// windows. The loop advances only on a real sequence notification.
    func waitEndpoint(_ key: CapabilityAndroidHostLifetimeKey, slot: Int) async -> Int32 {
        await wait(slot: slot, endpoint: key, facade: key.facade)
    }
    func waitFacade(_ facade: UInt64, slot: Int) async -> Int32 {
        await wait(slot: slot, endpoint: nil, facade: facade)
    }
    static func failClosed(_ code: Int32) {
        let controls = CapabilityAndroidRegistry.shared.quarantineAll(code)
        var outgoing: [CheckedContinuation<Void, Never>] = []
        // Publish the fault in every permanent cell before any data/progress
        // continuation wakes. Admission already irreversibly rejected new work.
        for cell in shared.cells {
            if let continuation = cell.merge(callback: 0, entry: 0, fault: code) { outgoing.append(continuation) }
        }
        for control in controls { control.transportFault(code) }
        for continuation in outgoing { continuation.resume() }
    }
    private func reclaim(slot: Int, endpoint: CapabilityAndroidHostLifetimeKey?, facade: UInt64) -> Int32 {
        if let endpoint { return CapabilityAndroidRegistry.shared.reclaimEndpoint(endpoint) }
        return CapabilityAndroidRegistry.shared.reclaimFacade(slot: slot, facade: facade)
    }
    private func wait(slot: Int, endpoint: CapabilityAndroidHostLifetimeKey?, facade: UInt64) async -> Int32 {
        let cell = cells[slot]
        while true {
            let before = cell.snapshot
            if before.fault != 0 { return before.fault }
            let first = reclaim(slot: slot, endpoint: endpoint, facade: facade)
            if first != Int32(MXUIT_BUSY.rawValue) { return first }
            let attempted = CapabilityAndroidReclaimAttempt()
            await withCheckedContinuation { continuation in
                guard let token = cell.register(after: before.sequence, continuation) else {
                    let failure = cell.snapshot.fault
                    if failure != 0 { Self.failClosed(failure) }
                    continuation.resume(); return
                }
                let second = reclaim(slot: slot, endpoint: endpoint, facade: facade)
                attempted.set(second)
                if second != Int32(MXUIT_BUSY.rawValue) { cell.cancel(token)?.resume() }
            }
            if let second = attempted.value, second != Int32(MXUIT_BUSY.rawValue) { return second }
            let outcome = cell.snapshot
            if outcome.fault != 0 { return outcome.fault }
        }
    }
}

@_cdecl("mxuit_drain")
func capabilityAndroidDrain(_ owner: UInt64, _ waiter: UInt64, _ kind: UInt32) -> Int32 {
    guard let control = CapabilityAndroidRegistry.shared.control(owner: owner), control.matches(waiter: waiter, kind: kind) else { return Int32(MXUIT_DRAIN_FAILED.rawValue) }
    return CapabilityGuestUIAndroidResources.drain(control: control, waiter: waiter, kind: kind)
}
@_cdecl("mxuit_complete")
func capabilityAndroidComplete(_ owner: UInt64, _ waiter: UInt64, _ kind: UInt32, _ result: Int32) {
    CapabilityAndroidRegistry.shared.control(owner: owner)?.complete(waiter: waiter, kind: kind, result: result)
}
@_cdecl("mxuit_progress")
func capabilityAndroidProgress(_ callbackFence: UInt64, _ uiEntryFence: UInt64, _ stickyFault: Int32) {
    // Healthy publication uses permanent cells only. A checked Swift sequence
    // overflow takes the same fail-closed data/progress fanout as a C fault.
    if stickyFault != 0 { CapabilityAndroidProgress.failClosed(stickyFault); return }
    var outgoing: [CheckedContinuation<Void, Never>] = []
    var checkedFault: Int32 = 0
    for cell in CapabilityAndroidProgress.shared.cells {
        if let continuation = cell.merge(callback: callbackFence, entry: uiEntryFence, fault: 0) { outgoing.append(continuation) }
        let fault = cell.snapshot.fault
        if checkedFault == 0, fault != 0 { checkedFault = fault }
    }
    if checkedFault != 0 { CapabilityAndroidProgress.failClosed(checkedFault) }
    for continuation in outgoing { continuation.resume() }
    // This post-resume tail can access only consumed continuations/process data.
}
#endif
