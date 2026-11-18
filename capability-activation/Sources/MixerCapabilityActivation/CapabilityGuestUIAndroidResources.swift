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
    private var tokenSerial: UInt64 = 0
    private var attachment: UInt64 = 0
    private var input: UInt64 = 0
    private var probe: UInt64 = 0
    private var observedProbe: UInt64 = 0
    private var observedFirstScreen = false
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
    /// Future JNI entry edges may reuse this synchronous engine helper with
    /// separately reviewed native witnesses. This host path grants no event or
    /// observation authority. Even lookup-disabled cleanup takes a real C lease.
    static func scalarEntry(facade: UInt64, slot: Int, kind: UInt32) -> Int32 {
        guard kind == UInt32(MXUIT_UI_INGRESS.rawValue) || kind == UInt32(MXUIT_UI_CLEANUP.rawValue) else { return Int32(MXUIT_INVALID.rawValue) }
        var entry: UInt64 = 0
        let admitted = mxuit_ui_enter(facade, 0, 0, kind, &entry)
        guard admitted == Int32(MXUIT_OK.rawValue) else { return admitted }
        guard let record = CapabilityAndroidRegistry.shared.record(slot: slot, facade: facade) else {
            _ = mxuit_ui_leave(facade, entry); return Int32(MXUIT_STALE.rawValue)
        }
        let state = record.withLock { r -> Int32 in
            if !r.lookupEnabled { return Int32(MXUIT_CLOSED.rawValue) }
            guard r.published, !r.quarantined, !r.facadeReclaimed,
                  kind != UInt32(MXUIT_UI_INGRESS.rawValue) || !r.closing else { return Int32(MXUIT_CLOSED.rawValue) }
            guard r.setupAliases == 0, r.uiAliases == 0 else { return Int32(MXUIT_BUSY.rawValue) }
            r.uiAliases = 1; return Int32(MXUIT_OK.rawValue)
        }
        var result = state
        if state == Int32(MXUIT_OK.rawValue) {
            result = scalarEntryInner(facade: facade, entry: entry, record: record)
            record.withLock { precondition($0.uiAliases == 1); $0.uiAliases = 0 }
        }
        let leave = mxuit_ui_leave(facade, entry)
        if leave != Int32(MXUIT_OK.rawValue) || result == Int32(MXUIT_IO.rawValue) {
            CapabilityAndroidRegistry.shared.quarantine(slot: slot, facade: facade)
            CapabilityGuestUIAndroidBinding.quarantineHostOwner(slot: slot, facade: facade)
            let control = CapabilityAndroidRegistry.shared.close(slot: slot, facade: facade)
            _ = mxuit_facade_begin_close(facade); control?.requestStop(.closed)
            return leave == Int32(MXUIT_OK.rawValue) ? result : leave
        }
        return result
    }
    @inline(never)
    private static func scalarEntryInner(facade: UInt64, entry: UInt64, record: CapabilityAndroidFacadeRecord) -> Int32 {
        guard let resources = record.resources else {
            record.withLock { $0.quarantined = true; $0.closing = true }
            return Int32(MXUIT_IO.rawValue)
        }
        do {
            try resources.ensureNative(entry: entry)
            guard mxis_interaction(facade, entry, 0) == Int32(MXUIT_OK.rawValue) else { throw coldStartError("android_entry_native") }
            if record.withLock({ $0.closing || $0.quarantined }) {
                guard mxis_interaction(facade, entry, 0) == Int32(MXUIT_OK.rawValue) else { throw coldStartError("android_entry_postcheck") }
            }
            return Int32(MXUIT_OK.rawValue)
        } catch {
            record.withLock { $0.quarantined = true; $0.closing = true }; return Int32(MXUIT_IO.rawValue)
        }
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
            guard tokenSerial <= UInt64(Int64.max) - 3 else { throw coldStartError("android_ui_identity") }
            attachment = tokenSerial + 1; input = tokenSerial + 2; probe = tokenSerial + 3; tokenSerial += 3
            let applied = packet.withUnsafeBytes { bytes in
                mxis_apply(facade, entry, attachment, input, probe, bytes.bindMemory(to: UInt8.self).baseAddress, UInt32(bytes.count))
            }
            pendingPacket = nil
            guard applied == Int32(MXUIT_OK.rawValue) else { throw coldStartError("android_native_apply") }
        }
        let appliedTicket = exchange.completePresentation(claim, snapshot: snapshot)
        if claim.frame != nil { ticket = appliedTicket }
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
    // Only the restricted native bridge calls this after its own attachment and
    // draw/click checks. Neither operation may use a stale presentation tuple.
    static func nativeWitness(facade: UInt64, attachment: UInt64, token: UInt64, display: Bool) -> Int32 {
        guard attachment > 0, token > 0 else { return Int32(MXUIT_INVALID.rawValue) }
        var entry: UInt64 = 0
        let admitted = mxuit_ui_enter(facade, 0, 0, UInt32(MXUIT_UI_INGRESS.rawValue), &entry)
        guard admitted == Int32(MXUIT_OK.rawValue) else { return admitted }
        let result = witnessWhileEntered(facade: facade, attachment: attachment, token: token, display: display)
        // A failed wake on leave publishes the transport fault and closes admission.
        let leave = mxuit_ui_leave(facade, entry)
        return leave == Int32(MXUIT_OK.rawValue) ? result : leave
    }

    private static func witnessWhileEntered(facade: UInt64, attachment: UInt64, token: UInt64, display: Bool) -> Int32 {
        for slot in 0..<16 {
            guard let record = CapabilityAndroidRegistry.shared.record(slot: slot, facade: facade) else { continue }
            let acquired = record.withLock { r -> Bool in
                guard r.lookupEnabled, r.published, !r.closing, !r.quarantined,
                      r.setupAliases == 0, r.uiAliases == 0 else { return false }
                r.uiAliases = 1
                return true
            }
            guard acquired else { return Int32(MXUIT_CLOSED.rawValue) }
            let result = witnessInner(record, attachment: attachment, token: token, display: display)
            record.withLock { precondition($0.uiAliases == 1); $0.uiAliases = 0 }
            return result
        }
        return Int32(MXUIT_STALE.rawValue)
    }

    @inline(never)
    private static func witnessInner(_ record: CapabilityAndroidFacadeRecord, attachment: UInt64,
                                     token: UInt64, display: Bool) -> Int32 {
        guard let resources = record.resources, resources.attachment == attachment,
              let exchange = resources.exchange, let ticket = resources.ticket else { return Int32(MXUIT_STALE.rawValue) }
        if display {
            let current = exchange.snapshot()
            guard resources.probe == token, resources.observedProbe != token, current.stop == nil,
                  current.effectsConfirmed, current.latestRevision == ticket.revision,
                  current.displayedRevision == ticket.revision else { return Int32(MXUIT_STALE.rawValue) }
            if !resources.observedFirstScreen {
                guard exchange.observePresentation(ticket) else { return Int32(MXUIT_STALE.rawValue) }
                resources.observedFirstScreen = true
            }
            resources.observedProbe = token
            return Int32(MXUIT_OK.rawValue)
        }
        guard resources.input == token, resources.probe == resources.observedProbe,
              let snapshot = resources.snapshot,
              let identity = snapshot.identity(for: "toggle") else { return Int32(MXUIT_STALE.rawValue) }
        let event = UIEventEnvelope(revision: snapshot.document.revision, identity: identity, event: .activate)
        if case .offered(.accepted) = exchange.offerNativeInput(event, generation: ticket.generation) {
            return Int32(MXUIT_OK.rawValue)
        }
        return Int32(MXUIT_BUSY.rawValue)
    }

    private func retire(key: CapabilityAndroidHostLifetimeKey, entry: UInt64,
                        record: CapabilityAndroidFacadeRecord) throws -> Int32 {
        // This exact sample decides whether late final close needs TERMINAL.
        let final = record.withLock { $0.closing }
        let generation = exchange?.snapshot().generation
        guard mxis_retire(facade, entry, final ? 1 : 0) == Int32(MXUIT_OK.rawValue) else { throw coldStartError("android_retire") }
        exchange = nil; reconciler = UIReconciler(); snapshot = nil; ticket = nil
        pendingPacket = nil; lastEvent = nil; attachment = 0; input = 0; probe = 0; observedProbe = 0; observedFirstScreen = false
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

@_cdecl("mxis_guest_ui_witness")
func guestUIWitness(_ facade: UInt64, _ attachment: UInt64, _ token: UInt64, _ kind: UInt32) -> Int32 {
    let drawn = UInt32(MXIS_WITNESS_DRAWN.rawValue)
    guard kind == drawn || kind == UInt32(MXIS_WITNESS_TOGGLE_TAPPED.rawValue) else {
        return Int32(MXUIT_INVALID.rawValue)
    }
    return CapabilityGuestUIAndroidResources.nativeWitness(facade: facade, attachment: attachment,
        token: token, display: kind == drawn)
}

#if MIXER_FIELDLOG_ANDROID_TRIAL
@_cdecl("mxfield_witness")
func fieldLogNativeWitness(_ facade: UInt64, _ attachment: UInt64, _ token: UInt64, _ display: UInt32) -> Int32 {
    guard display <= 1 else { return Int32(MXUIT_INVALID.rawValue) }
    let kind = display == 1 ? MXIS_WITNESS_DRAWN : MXIS_WITNESS_TOGGLE_TAPPED
    return guestUIWitness(facade, attachment, token, UInt32(kind.rawValue))
}
#endif
#endif
