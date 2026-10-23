import Foundation
import MixerUpdates

/// The single outer pool counts complete coordinator/attempt owners, including
/// idle, failed-init and closing owners. It is independent of the native16 pool.
final class CapabilityAttemptReservation: @unchecked Sendable {
    private struct State {
        var closing = false
        var quarantined = false
        var released = false
        var reclaiming = false
        var storeIssued = false
        var storeClaimed = false
        var nextID: UInt64 = 0
        var storeID: UInt64?
        var adapterID: UInt64?
        var storeRetiring = false
        var adapterRetiring = false
        var storeOwner: (any AnyObject & Sendable)?
        var adapterOwner: (any AnyObject & Sendable)?
    }
    private static let pool = CapabilityAttemptPool()
    private let lock = NSLock()
    private var state = State()
    private init() {}

    static func acquire() throws -> CapabilityAttemptReservation {
        try pool.acquire()
        return CapabilityAttemptReservation()
    }
    static var occupiedSlots: Int { pool.occupied }

    func issueStoreAdmission() throws -> CapabilityRecoveryStoreAdmission {
        let id: UInt64 = try locked { s in
            guard !s.closing, !s.quarantined, !s.released, !s.storeIssued else { throw reservationError("state") }
            let id = try Self.next(&s); s.storeIssued = true; s.storeID = id; return id
        }
        return CapabilityRecoveryStoreAdmission(reservation: self, id: id)
    }
    func reserveAdapterGroup() throws -> CapabilityAdapterObligation {
        let id: UInt64 = try locked { s in
            guard !s.closing, !s.quarantined, !s.released, s.adapterID == nil, !s.adapterRetiring else { throw reservationError("state") }
            let id = try Self.next(&s); s.adapterID = id; return id
        }
        return CapabilityAdapterObligation(reservation: self, id: id)
    }
    func beginClosing() {
        let release = locked { s in s.closing = true; return Self.releaseReady(&s) }
        if release { completeRelease() }
    }
    func quarantine() { locked { $0.quarantined = true; $0.closing = true } }
    var isQuarantined: Bool { locked { $0.quarantined } }
    var isReleased: Bool { locked { $0.released } }

    fileprivate func claimStore(_ id: UInt64) throws -> CapabilityStoreObligation {
        try locked { s in
            guard !s.closing, !s.quarantined, !s.released, s.storeID == id, !s.storeClaimed else { throw reservationError("state") }
            s.storeClaimed = true
        }
        return CapabilityStoreObligation(reservation: self, id: id)
    }
    fileprivate func unusedStore(_ id: UInt64) {
        let release = locked { s in
            guard s.storeID == id, !s.storeClaimed else { return false }
            s.storeID = nil; return Self.releaseReady(&s)
        }
        if release { completeRelease() }
    }
    fileprivate func hold(_ owner: any AnyObject & Sendable, id: UInt64, store: Bool) throws {
        try locked { s in
            let current = store ? s.storeID : s.adapterID
            let existing = store ? s.storeOwner : s.adapterOwner
            guard current == id, existing == nil, !s.released, !s.quarantined else { throw reservationError("state") }
            if store { s.storeOwner = owner } else { s.adapterOwner = owner }
        }
    }
    fileprivate func retire(_ id: UInt64, store: Bool) {
        // Count every moved-owner retirement until destruction actually returns.
        // Both kinds may retire concurrently; neither may release the other's
        // still-running destructor or permit another adapter group underneath it.
        var owner: (any AnyObject & Sendable)?
        let moved = locked { s in
            guard (store ? s.storeID : s.adapterID) == id else { return false }
            owner = store ? s.storeOwner : s.adapterOwner
            if store { s.storeRetiring = true; s.storeID = nil; s.storeOwner = nil }
            else { s.adapterRetiring = true; s.adapterID = nil; s.adapterOwner = nil }
            return true
        }
        guard moved else { return }
        withExtendedLifetime(owner) {}
        owner = nil // Final retained reference destruction is outside all locks.
        let release = locked { s in
            if store { s.storeRetiring = false } else { s.adapterRetiring = false }
            return Self.releaseReady(&s)
        }
        if release { completeRelease() }
    }
    private static func next(_ s: inout State) throws -> UInt64 {
        guard s.nextID < UInt64.max else { s.quarantined = true; s.closing = true; throw reservationError("exhausted") }
        s.nextID += 1; return s.nextID
    }
    private static func releaseReady(_ s: inout State) -> Bool {
        guard s.closing, !s.quarantined, !s.released, !s.reclaiming, s.storeID == nil, s.adapterID == nil, !s.storeRetiring, !s.adapterRetiring else { return false }
        s.reclaiming = true; return true
    }
    private func completeRelease() {
        locked { s in
            guard s.reclaiming, !s.released else { return }
            s.reclaiming = false
            guard !s.quarantined else { return }
            Self.pool.release(); s.released = true
        }
    }
    private func locked<T>(_ body: (inout State) throws -> T) rethrows -> T {
        lock.lock(); defer { lock.unlock() }; return try body(&state)
    }
    deinit {
        // No claimed I/O owner can normally reach this point because hold()
        // retains it. An abandoned claimed obligation pins the pool permanently.
        let release = locked { s in
            s.closing = true
            if s.storeID != nil || s.adapterID != nil || s.storeRetiring || s.adapterRetiring { s.quarantined = true }
            return Self.releaseReady(&s)
        }
        if release { completeRelease() }
    }
}

private final class CapabilityAttemptPool: @unchecked Sendable {
    private let lock = NSLock()
    private var count = 0
    var occupied: Int { lock.lock(); defer { lock.unlock() }; return count }
    func acquire() throws {
        lock.lock(); defer { lock.unlock() }
        guard count < 16 else { throw reservationError("busy") }
        count += 1
    }
    func release() {
        lock.lock(); defer { lock.unlock() }
        // Only a reservation's one-shot release transition reaches here.
        precondition(count > 0); count -= 1
    }
}

final class CapabilityRecoveryStoreAdmission: @unchecked Sendable {
    private let lock = NSLock()
    private var consumed = false
    private let reservation: CapabilityAttemptReservation
    private let id: UInt64
    fileprivate init(reservation: CapabilityAttemptReservation, id: UInt64) { self.reservation = reservation; self.id = id }
    func claimStore() throws -> CapabilityStoreObligation {
        lock.lock(); defer { lock.unlock() }
        guard !consumed else { throw reservationError("consumed") }
        let obligation = try reservation.claimStore(id)
        consumed = true; return obligation
    }
    deinit { if !consumed { reservation.unusedStore(id) } }
}

/// Actual retirement is an assertion by the trusted owner, not a deinit effect.
/// Dropping a claimed obligation without retire quarantines its outer slot.
final class CapabilityStoreObligation: @unchecked Sendable {
    private let lock = NSLock()
    private var retired = false
    private let reservation: CapabilityAttemptReservation
    private let id: UInt64
    fileprivate init(reservation: CapabilityAttemptReservation, id: UInt64) { self.reservation = reservation; self.id = id }
    func retainOwner(_ owner: any AnyObject & Sendable) throws { try reservation.hold(owner, id: id, store: true) }
    func retire() {
        lock.lock(); let first = !retired; retired = true; lock.unlock()
        if first { reservation.retire(id, store: true) }
    }
    func quarantine() { reservation.quarantine() }
    deinit { if !retired { reservation.quarantine() } }
}
final class CapabilityAdapterObligation: @unchecked Sendable {
    private let lock = NSLock()
    private var retired = false
    private let reservation: CapabilityAttemptReservation
    private let id: UInt64
    fileprivate init(reservation: CapabilityAttemptReservation, id: UInt64) { self.reservation = reservation; self.id = id }
    func retainOwner(_ owner: any AnyObject & Sendable) throws { try reservation.hold(owner, id: id, store: false) }
    func retire() {
        lock.lock(); let first = !retired; retired = true; lock.unlock()
        if first { reservation.retire(id, store: false) }
    }
    func quarantine() { reservation.quarantine() }
    deinit { if !retired { reservation.quarantine() } }
}
private func reservationError(_ code: String) -> UpdateError {
    UpdateError("capability.attempt.\(code)", "Capability attempt reservation rejected")
}
