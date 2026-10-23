#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
import Foundation
@_spi(GuestUIV1) import MixerGuest
import MixerUI
import CMixerUITransport
import CMixerUIAndroidHostBridge

struct CapabilityAndroidHostFacadeCleanupEvidence: Sendable, Equatable {
    let key: CapabilityAndroidHostLifetimeKey
    let cleanupSerial: UInt64
    let finalEntrySerial: UInt64
    let bridgeSlotGeneration: UInt64
    let clearedExchangeGeneration: UInt64?
    let clearedResourceStageRevision: UInt64
    fileprivate init(key: CapabilityAndroidHostLifetimeKey, cleanupSerial: UInt64, finalEntrySerial: UInt64,
                     bridgeSlotGeneration: UInt64, clearedExchangeGeneration: UInt64?, clearedResourceStageRevision: UInt64) {
        self.key = key; self.cleanupSerial = cleanupSerial; self.finalEntrySerial = finalEntrySerial
        self.bridgeSlotGeneration = bridgeSlotGeneration; self.clearedExchangeGeneration = clearedExchangeGeneration
        self.clearedResourceStageRevision = clearedResourceStageRevision
    }
}

/// Exactly one persistent strong reference belongs to the reservation. Setup and
/// UI helpers promote it only in synchronous inner frames, counted outside them.
final class CapabilityGuestUIAndroidResources: @unchecked Sendable {
    private let facade: UInt64
    private var bridgeGeneration: UInt64 = 0
    private var revision: UInt64 = 1
    private var exchange: GuestUIExchangeV1?
    private var reconciler = UIReconciler()
    private var snapshot: UIRenderSnapshot?
    private var ticket: GuestUIPresentationTicketV1?
    private var lastEvent: GuestUIEventResultV1?
    private var pendingPacket: Data?
    private var attachment: UInt64 = 0
    private var input: UInt64 = 0
    private var probe: UInt64 = 0
    init(facade: UInt64) { self.facade = facade }

    static func installExchange(_ exchange: GuestUIExchangeV1, key: CapabilityAndroidHostLifetimeKey, slot: Int) throws {
        guard let record = CapabilityAndroidRegistry.shared.record(slot: slot, facade: key.facade) else { throw coldStartError("android_resource_stale") }
        let entered = record.withLock { r -> Bool in
            guard !r.closing, !r.quarantined, r.lookupEnabled, r.endpoint == key.endpoint,
                  r.lifetime == key.lifetime, r.setupAliases == 0, r.uiAliases == 0 else { return false }
            r.setupAliases = 1; return true
        }
        guard entered else { throw coldStartError("android_resource_alias") }
        do { try installInner(exchange, record: record) }
        catch { record.withLock { $0.setupAliases = 0 }; throw error }
        // Strong resource locals have actually returned before the count drops.
        record.withLock { precondition($0.setupAliases == 1); $0.setupAliases = 0 }
    }
    @inline(never)
    private static func installInner(_ exchange: GuestUIExchangeV1, record: CapabilityAndroidFacadeRecord) throws {
        guard let resources = record.resources else { throw coldStartError("android_missing_resources") }
        guard resources.exchange == nil, resources.revision < .max else { throw coldStartError("android_resource_state") }
        resources.exchange = exchange; resources.revision += 1
    }

    static func drain(control: CapabilityAndroidLifetimeControl, waiter: UInt64, kind: UInt32) -> Int32 {
        let key = control.key
        var entry: UInt64 = 0
        guard mxuit_ui_enter(key.facade, key.endpoint, waiter,
                             kind == UInt32(MXUIT_RETIRE.rawValue) ? UInt32(MXUIT_UI_RETIRE.rawValue) : UInt32(MXUIT_UI_PRESENT.rawValue), &entry) == Int32(MXUIT_OK.rawValue) else { return Int32(MXUIT_DRAIN_FAILED.rawValue) }
        guard let record = CapabilityAndroidRegistry.shared.record(slot: control.facadeSlot, facade: key.facade) else {
            _ = mxuit_ui_leave(key.facade, entry); return Int32(MXUIT_DRAIN_FAILED.rawValue)
        }
        let entered = record.withLock { r -> Bool in
            guard r.lookupEnabled, r.published, !r.quarantined, r.endpoint == key.endpoint, r.lifetime == key.lifetime,
                  r.uiAliases == 0, r.setupAliases == 0 else { return false }
            r.uiAliases = 1; return true
        }
        let result: Int32
        if entered {
            result = drainInner(key: key, entry: entry, kind: kind, record: record)
            // No owner/resource reference exists in this outer return tail.
            record.withLock { precondition($0.uiAliases == 1); $0.uiAliases = 0 }
        } else { result = Int32(MXUIT_DRAIN_FAILED.rawValue) }
        let leave = mxuit_ui_leave(key.facade, entry)
        if result != Int32(MXUIT_DRAIN_OK.rawValue) || leave != Int32(MXUIT_OK.rawValue) {
            CapabilityAndroidRegistry.shared.quarantine(slot: control.facadeSlot, facade: key.facade)
            return Int32(MXUIT_DRAIN_FAILED.rawValue)
        }
        return result
    }
    @inline(never)
    private static func drainInner(key: CapabilityAndroidHostLifetimeKey, entry: UInt64, kind: UInt32,
                                   record: CapabilityAndroidFacadeRecord) -> Int32 {
        guard let resources = record.resources else {
            record.withLock { $0.quarantined = true }; return Int32(MXUIT_DRAIN_FAILED.rawValue)
        }
        do {
            try resources.ensureNative(entry: entry)
            if kind == UInt32(MXUIT_RETIRE.rawValue) { return try resources.retire(key: key, entry: entry, record: record) }
            return try resources.present(key: key, entry: entry, record: record)
        } catch { record.withLock { $0.quarantined = true }; return Int32(MXUIT_DRAIN_FAILED.rawValue) }
    }
    private func ensureNative(entry: UInt64) throws {
        if bridgeGeneration == 0 {
            var issued: UInt64 = 0
            guard mxis_host_slot_acquire(facade, entry, &issued) == Int32(MXUIT_OK.rawValue), issued > 0 else { throw coldStartError("android_host_slot") }
            bridgeGeneration = issued
        }
        var actual = mxis_host_snapshot()
        guard mxis_host_inspect(facade, entry, &actual) == Int32(MXUIT_OK.rawValue),
              actual.facade == facade, actual.generation == bridgeGeneration, actual.published == 1,
              actual.cleared == 0, actual.weak_owner_live == 1 else { throw coldStartError("android_missing_native") }
    }
    private func present(key: CapabilityAndroidHostLifetimeKey, entry: UInt64, record: CapabilityAndroidFacadeRecord) throws -> Int32 {
        guard let exchange else { throw coldStartError("android_missing_exchange") }
        let generation = exchange.snapshot().generation
        guard let claim = exchange.claimPresentation(generation: generation) else { return Int32(MXUIT_DRAIN_OK.rawValue) }
        if let event = claim.eventResult { lastEvent = event }
        if claim.stop != nil {
            _ = exchange.completePresentation(claim, snapshot: nil)
            return Int32(MXUIT_DRAIN_OK.rawValue)
        }
        if let frame = claim.frame {
            _ = try reconciler.apply(frame.document.document)
            snapshot = try reconciler.currentSnapshot()
            // The host fixture consumes the independently validated wire tree;
            // it is bounded by the exchange's 65,536-byte document limit.
            pendingPacket = try JSONEncoder().encode(frame.document.document)
            guard let packet = pendingPacket, packet.count <= 65536 else { throw coldStartError("android_packet") }
            guard attachment < UInt64(Int64.max), input < UInt64(Int64.max), probe < UInt64(Int64.max) else { throw coldStartError("android_ui_identity") }
            attachment += 1; input += 1; probe += 1
            let applied = packet.withUnsafeBytes { bytes in
                mxis_apply(facade, entry, attachment, input, probe, bytes.bindMemory(to: UInt8.self).baseAddress, UInt32(bytes.count))
            }
            pendingPacket = nil
            guard applied == Int32(MXUIT_OK.rawValue) else { throw coldStartError("android_native_apply") }
        }
        ticket = exchange.completePresentation(claim, snapshot: snapshot)
        let state = exchange.snapshot()
        let closed = record.withLock { $0.closing || $0.quarantined }
        let enabled: UInt32 = !closed && state.stop == nil && state.effectsConfirmed && !state.guestTurnInFlight &&
            !state.eventOutstanding && state.displayedRevision != nil && state.displayedRevision == state.latestRevision ? 1 : 0
        guard mxis_interaction(facade, entry, enabled) == Int32(MXUIT_OK.rawValue) else { throw coldStartError("android_native_interaction") }
        // Reentrant scalar close cannot retain input authority in this lease.
        if record.withLock({ $0.closing || $0.quarantined }), enabled != 0 {
            guard mxis_interaction(facade, entry, 0) == Int32(MXUIT_OK.rawValue) else { throw coldStartError("android_native_postcheck") }
        }
        return Int32(MXUIT_DRAIN_OK.rawValue)
    }
    private func retire(key: CapabilityAndroidHostLifetimeKey, entry: UInt64,
                        record: CapabilityAndroidFacadeRecord) throws -> Int32 {
        // This exact sample decides whether late final close needs TERMINAL.
        let final = record.withLock { $0.closing }
        let generation = exchange?.snapshot().generation
        guard mxis_retire(facade, entry, final ? 1 : 0) == Int32(MXUIT_OK.rawValue) else { throw coldStartError("android_retire") }
        exchange = nil; reconciler = UIReconciler(); snapshot = nil; ticket = nil
        pendingPacket = nil; lastEvent = nil; attachment = 0; input = 0; probe = 0
        guard revision < .max else { throw coldStartError("android_stage_exhausted") }; revision += 1
        if final {
            var native = mxis_host_snapshot()
            guard mxis_host_inspect(facade, entry, &native) == Int32(MXUIT_OK.rawValue),
                  native.facade == facade, native.generation == bridgeGeneration, native.published == 1,
                  native.cleared == 1, native.final_entry == entry,
                  native.tree_live == 0, native.listener_live == 0, native.weak_owner_live == 0,
                  native.packet_bytes == 0, native.interaction == 0,
                  mxuit_ui_validate(facade, entry) == Int32(MXUIT_OK.rawValue) else { throw coldStartError("android_retire_postcondition") }
            try record.withLock { r in
                guard r.facade == key.facade, r.endpoint == key.endpoint, r.lifetime == key.lifetime,
                      r.closing, !r.quarantined, r.cleanup == nil, r.lookupEnabled, r.uiAliases == 1,
                      r.cleanupSerial < .max else { throw coldStartError("android_cleanup_state") }
                r.cleanupSerial += 1
                let evidence = CapabilityAndroidHostFacadeCleanupEvidence(key: key, cleanupSerial: r.cleanupSerial,
                    finalEntrySerial: entry, bridgeSlotGeneration: bridgeGeneration,
                    clearedExchangeGeneration: generation, clearedResourceStageRevision: revision)
                // Atomic receipt/lookup-disable: no future entry can promote.
                r.cleanup = evidence; r.lookupEnabled = false
            }
        }
        return Int32(MXUIT_DRAIN_OK.rawValue)
    }
    deinit {
        if bridgeGeneration > 0 {
            // Called by the actual reservation-owned destructor after C facade
            // reclaim. This host-only operation cannot generate a receipt.
            precondition(mxis_host_release_destroyed(facade, bridgeGeneration) == Int32(MXUIT_OK.rawValue))
        }
    }
}
#endif
