#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
import Foundation
@_spi(GuestUIV1) import MixerGuest
import CMixerUITransport
import CMixerUIAndroidHostBridge

/// The acquired identity is created only by the real, admission-locked C call.
/// It is a one-shot start token, not a caller-selectable endpoint or Task.
final class CapabilityAndroidAcquiredEndpoint: @unchecked Sendable {
    let facade: UInt64
    let lifetime: CapabilityPresentationLifetimeID
    let endpoint: UInt64
    let facadeSlot: Int
    let gate: CapabilityAndroidReservedBindGate
    private let lock = NSLock()
    private var taken = false
    fileprivate init(facade: UInt64, lifetime: CapabilityPresentationLifetimeID, endpoint: UInt64, facadeSlot: Int, gate: CapabilityAndroidReservedBindGate) {
        self.facade = facade; self.lifetime = lifetime; self.endpoint = endpoint; self.facadeSlot = facadeSlot; self.gate = gate
    }
    func take() -> Bool {
        lock.lock(); defer { lock.unlock() }; guard !taken else { return false }; taken = true; return true
    }
}

/// Permanent sixteen-record storage. A record retains only data-only control,
/// scalar evidence and a weak resource box; the reservation owns resources.
final class CapabilityAndroidFacadeRecord: @unchecked Sendable {
    let lock = NSLock()
    var reserved = false
    var facade: UInt64 = 0
    weak var resources: CapabilityGuestUIAndroidResources?
    var published = false
    var facadeReclaimed = false
    var lookupEnabled = false
    var closing = false
    var quarantined = false
    var endpoint: UInt64 = 0
    var lifetime: CapabilityPresentationLifetimeID?
    var setupAliases = 0
    var uiAliases = 0
    var cleanupSerial: UInt64 = 0
    var cleanup: CapabilityAndroidHostFacadeCleanupEvidence?
    func withLock<T>(_ body: (CapabilityAndroidFacadeRecord) throws -> T) rethrows -> T {
        lock.lock(); defer { lock.unlock() }; return try body(self)
    }
}
private final class CapabilityAndroidEndpointRecord: @unchecked Sendable {
    var reserved = false
    var facade: UInt64 = 0
    var owner: UInt64 = 0
    var control: CapabilityAndroidLifetimeControl?
}

final class CapabilityAndroidRegistry: @unchecked Sendable {
    static let shared = CapabilityAndroidRegistry()
    private let admission = NSLock()
    private let facades = (0..<16).map { _ in CapabilityAndroidFacadeRecord() }
    private let endpoints = (0..<16).map { _ in CapabilityAndroidEndpointRecord() }
    private var fault: Int32 = 0
    private init() {}

    func acquireFacade() throws -> (Int, UInt64) {
        admission.lock(); defer { admission.unlock() }
        guard fault == 0, let index = facades.firstIndex(where: { !$0.reserved }) else { throw coldStartError("android_facade_capacity") }
        let record = facades[index]
        record.reserved = true // Reserved before C issue: no second admission can steal it.
        var facade: UInt64 = 0
        let result = mxuit_facade_acquire(&facade)
        guard result == Int32(MXUIT_OK.rawValue), facade > 0 else {
            // Only a proven empty acquisition may roll back its Swift reservation.
            if facade == 0 { record.reserved = false }
            else { record.withLock { $0.facade = facade; $0.quarantined = true } }
            throw coldStartError("android_facade_acquire_\(result)")
        }
        record.withLock {
            $0.facade = facade; $0.resources = nil; $0.published = false; $0.facadeReclaimed = false; $0.lookupEnabled = false
            $0.closing = false; $0.quarantined = false; $0.endpoint = 0; $0.lifetime = nil
            $0.setupAliases = 0; $0.uiAliases = 0; $0.cleanupSerial = 0; $0.cleanup = nil
        }
        return (index, facade)
    }
    func record(slot: Int, facade: UInt64) -> CapabilityAndroidFacadeRecord? {
        guard facades.indices.contains(slot) else { return nil }
        let record = facades[slot]
        return record.withLock { $0.facade == facade ? record : nil }
    }
    func publishResources(slot: Int, facade: UInt64, resources: CapabilityGuestUIAndroidResources,
                          obligation: CapabilityPresentationObligation) throws {
        guard let record = record(slot: slot, facade: facade) else { throw coldStartError("android_facade_stale") }
        try record.withLock {
            guard !$0.published, !$0.quarantined, $0.setupAliases == 0 else { throw coldStartError("android_resource_publish") }
            $0.setupAliases = 1
        }
        // No facade lock spans reservation ownership transfer.
        do { try obligation.retainOwner(resources) }
        catch { record.withLock { $0.setupAliases = 0; $0.quarantined = true }; throw error }
        record.withLock { $0.resources = resources; $0.published = true; $0.lookupEnabled = true }
    }
    func endSetupAlias(slot: Int, facade: UInt64) {
        record(slot: slot, facade: facade)?.withLock { precondition($0.setupAliases == 1); $0.setupAliases = 0 }
    }
    func acquireEndpoint(slot: Int, facade: UInt64, terminal: Bool) throws -> CapabilityAndroidAcquiredEndpoint {
        admission.lock(); defer { admission.unlock() }
        guard fault == 0, facades.indices.contains(slot),
              let available = endpoints.first(where: { !$0.reserved }) else { throw coldStartError("android_endpoint_capacity") }
        let record = facades[slot]
        let allowed = record.withLock { $0.facade == facade && !$0.quarantined && $0.endpoint == 0 && $0.closing == terminal }
        guard allowed else { throw coldStartError("android_endpoint_state") }
        available.reserved = true; available.facade = facade
        let lifetime: CapabilityPresentationLifetimeID
        do { lifetime = try CapabilityPresentationLifetimeID.issue() }
        catch { available.reserved = false; available.facade = 0; throw error }
        let gate = CapabilityAndroidLifetimeControl.reserveBindGate()
        // The Swift record, fresh lifetime and empty bind gate exist before C can issue an ID.
        var owner: UInt64 = 0
        let result = mxuit_acquire_for_facade(facade, UInt32(terminal ? UInt32(MXUIT_TERMINAL.rawValue) : UInt32(MXUIT_ATTEMPT.rawValue)), &owner)
        guard result == Int32(MXUIT_OK.rawValue), owner > 0 else {
            if owner == 0 { available.reserved = false; available.facade = 0 }
            else { available.owner = owner; record.withLock { $0.quarantined = true; $0.endpoint = owner; $0.lifetime = lifetime } }
            throw coldStartError("android_endpoint_acquire_\(result)")
        }
        available.owner = owner
        record.withLock { $0.endpoint = owner; $0.lifetime = lifetime }
        return CapabilityAndroidAcquiredEndpoint(facade: facade, lifetime: lifetime, endpoint: owner, facadeSlot: slot, gate: gate)
    }
    func publishControl(_ control: CapabilityAndroidLifetimeControl) -> Bool {
        admission.lock(); defer { admission.unlock() }
        guard let record = endpoints.first(where: { $0.reserved && $0.owner == control.key.endpoint && $0.facade == control.key.facade }), record.control == nil else { return false }
        record.control = control; return fault == 0
    }
    func control(owner: UInt64) -> CapabilityAndroidLifetimeControl? {
        admission.lock(); defer { admission.unlock() }
        return endpoints.first(where: { $0.reserved && $0.owner == owner })?.control
    }
    func close(slot: Int, facade: UInt64) -> CapabilityAndroidLifetimeControl? {
        guard let record = record(slot: slot, facade: facade) else { return nil }
        record.withLock { $0.closing = true }
        admission.lock()
        let control = endpoints.first(where: { $0.reserved && $0.facade == facade })?.control
        admission.unlock()
        return control
    }
    /// Called only by the one native join owner, after Task.value and RETIRE.
    func reclaimEndpoint(_ key: CapabilityAndroidHostLifetimeKey) -> Int32 {
        admission.lock(); defer { admission.unlock() }
        guard fault == 0 else { return fault }
        guard endpoints.contains(where: { $0.reserved && $0.owner == key.endpoint && $0.facade == key.facade }) else { return Int32(MXUIT_STALE.rawValue) }
        return mxuit_try_reclaim(key.endpoint)
    }
    func removeEndpoint(_ key: CapabilityAndroidHostLifetimeKey, slot: Int) -> Bool {
        admission.lock(); defer { admission.unlock() }
        guard let endpoint = endpoints.first(where: { $0.reserved && $0.owner == key.endpoint && $0.facade == key.facade }) else { return false }
        let removed = facades[slot].withLock { r -> Bool in
            guard r.facade == key.facade, r.endpoint == key.endpoint, r.lifetime == key.lifetime else { return false }
            r.endpoint = 0; r.lifetime = nil; return true
        }
        guard removed else { return false }
        endpoint.control = nil; endpoint.owner = 0; endpoint.facade = 0; endpoint.reserved = false
        return true
    }
    func reclaimFacade(slot: Int, facade: UInt64) -> Int32 {
        admission.lock(); defer { admission.unlock() }
        guard fault == 0 else { return fault }
        let allowed = facades[slot].withLock {
            $0.facade == facade && !$0.quarantined && $0.closing && $0.cleanup != nil && !$0.lookupEnabled &&
                $0.endpoint == 0 && $0.setupAliases == 0 && $0.uiAliases == 0
        }
        guard allowed else { return Int32(MXUIT_BUSY.rawValue) }
        return mxuit_facade_try_reclaim(facade)
    }
    func removeFacade(slot: Int, facade: UInt64) -> Bool {
        admission.lock(); defer { admission.unlock() }
        let record = facades[slot]
        let removed = record.withLock { r -> Bool in
            guard r.facade == facade, r.cleanup != nil, !r.lookupEnabled, r.endpoint == 0,
                  r.setupAliases == 0, r.uiAliases == 0, !r.quarantined else { return false }
            r.facadeReclaimed = true; r.resources = nil; return true
        }
        return removed
    }
    func releaseFacadeReservation(slot: Int, facade: UInt64) -> Bool {
        admission.lock(); defer { admission.unlock() }
        let record = facades[slot]
        let removed = record.withLock { r -> Bool in
            guard r.facade == facade, r.facadeReclaimed, r.cleanup != nil, !r.lookupEnabled,
                  r.endpoint == 0, r.setupAliases == 0, r.uiAliases == 0 else { return false }
            r.facade = 0; r.cleanup = nil; return true
        }
        if removed { record.reserved = false }
        return removed
    }
    func quarantine(slot: Int, facade: UInt64) {
        record(slot: slot, facade: facade)?.withLock { $0.quarantined = true; $0.closing = true }
    }
    /// Sticky admission closes before any exact data wait is resumed.
    func quarantineAll(_ code: Int32) -> [CapabilityAndroidLifetimeControl] {
        admission.lock()
        if fault == 0 { fault = code == 0 ? Int32(MXUIT_IO.rawValue) : code }
        for record in facades where record.reserved { record.withLock { $0.quarantined = true; $0.closing = true } }
        let controls = endpoints.compactMap { $0.control }
        admission.unlock(); return controls
    }
}
#endif
