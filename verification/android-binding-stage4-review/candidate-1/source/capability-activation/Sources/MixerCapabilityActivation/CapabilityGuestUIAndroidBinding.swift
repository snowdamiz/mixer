#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
import Foundation
@_spi(GuestUIV1) import MixerGuest
import CMixerUITransport
import CMixerUIAndroidHostBridge

enum CapabilityAndroidHostFailureCode: Sendable, Equatable {
    case invalidState, unavailable, transportIO, retireFailed
    case missingPublishedResources, identityExhausted, setupFailed, cleanupPending
}
struct CapabilityAndroidHostFailure: Sendable, Equatable {
    let key: CapabilityAndroidHostLifetimeKey?
    let code: CapabilityAndroidHostFailureCode
    init(key: CapabilityAndroidHostLifetimeKey?, code: CapabilityAndroidHostFailureCode) { self.key = key; self.code = code }
}
struct CapabilityAndroidHostFinalReceipt: Sendable, Equatable {
    let facade: UInt64
    let lastLifetime: CapabilityAndroidHostLifetimeReceipt
    let facadeCleanup: CapabilityAndroidHostFacadeCleanupReceipt
    let facadeReturnFence: UInt64
    fileprivate init(facade: UInt64, lastLifetime: CapabilityAndroidHostLifetimeReceipt,
                     facadeCleanup: CapabilityAndroidHostFacadeCleanupReceipt, facadeReturnFence: UInt64) {
        self.facade = facade; self.lastLifetime = lastLifetime; self.facadeCleanup = facadeCleanup; self.facadeReturnFence = facadeReturnFence
    }
}
enum CapabilityAndroidHostFinalCloseStatus: Sendable, Equatable {
    case pending, finished(CapabilityAndroidHostFinalReceipt)
    case quarantined(CapabilityAndroidHostFailure), invariant(CapabilityPresentationInvariant)
}

/// Fixed final-obligation cells retain actual uncertain ARC ownership, not only
/// a pool count. A facade's Swift reservation remains occupied until this cell
/// clears after synchronous resource destruction. No resource is retained here
/// directly, and quarantine never allocates or replaces another identity.
private final class CapabilityAndroidHostFinalObligations: @unchecked Sendable {
    static let shared = CapabilityAndroidHostFinalObligations()
    private let lock = NSLock()
    private var cells: [(UInt64, CapabilityPresentationObligation)?] = Array(repeating: nil, count: 16)
    private init() {}
    func claim(slot: Int, facade: UInt64, obligation: CapabilityPresentationObligation) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard cells[slot] == nil else { return false }
        cells[slot] = (facade, obligation); return true
    }
    func clearAfterRetirement(slot: Int, facade: UInt64) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard cells[slot]?.0 == facade else { return false }
        cells[slot] = nil; return true
    }
}

/// Resource-free standalone host shell. It is deliberately a different type
/// from the existing Apple binding/Prepared/core installation path.
final class CapabilityGuestUIAndroidBinding: @unchecked Sendable {
    let facade: UInt64
    private let slot: Int
    private let obligation: CapabilityPresentationObligation
    private let lock = NSLock()
    private var closing = false
    private var transferred = false
    private var binding = false
    private var finalJoining = false
    private var initial: CapabilityAndroidHostInstallation?
    private var current: CapabilityAndroidHostInstallation?
    private var result: CapabilityAndroidHostFinalCloseStatus = .pending
    private init(slot: Int, facade: UInt64, obligation: CapabilityPresentationObligation) {
        self.slot = slot; self.facade = facade; self.obligation = obligation
    }
    static func prepareHost(reservation: CapabilityAttemptReservation) async throws -> CapabilityAndroidHostPreparedPresentation {
        let obligation = try reservation.reservePresentation() // Before any facade/resource/Task.
        let acquired: (Int, UInt64)
        do { acquired = try CapabilityAndroidRegistry.shared.acquireFacade() }
        catch { obligation.retire(); throw error }
        let binding = CapabilityGuestUIAndroidBinding(slot: acquired.0, facade: acquired.1, obligation: obligation)
        guard CapabilityAndroidHostFinalObligations.shared.claim(slot: acquired.0, facade: acquired.1, obligation: obligation) else {
            binding.quarantine(.invalidState); throw coldStartError("android_final_cell")
        }
        do {
            try binding.createResources()
            let initial = try binding.makeInstallation(terminal: false)
            binding.setCurrent(initial)
            let prepared = CapabilityAndroidHostPreparedPresentation(binding: binding, reservation: reservation, initial: initial)
            do { try Task.checkCancellation(); return prepared }
            catch { _ = await prepared.cleanupAfterFailure(); throw error }
        } catch {
            // A live acquired C identity or published resource cannot be rolled
            // back as empty or retired by deinit. Its uncertain obligation pins.
            if case .finished = binding.finalStatus {} else { binding.quarantine(.setupFailed) }; throw error
        }
    }
    @inline(never)
    private func createResources() throws {
        let resources = CapabilityGuestUIAndroidResources(facade: facade)
        try CapabilityAndroidRegistry.shared.publishResources(slot: slot, facade: facade, resources: resources, obligation: obligation)
        // The inner creation frame returns before the alias decrement below.
    }
    private func makeInstallation(terminal: Bool) throws -> CapabilityAndroidHostInstallation {
        // Before first endpoint admission the setup creator has really returned.
        if let record = CapabilityAndroidRegistry.shared.record(slot: slot, facade: facade), record.withLock({ $0.setupAliases == 1 }) {
            CapabilityAndroidRegistry.shared.endSetupAlias(slot: slot, facade: facade)
        }
        let endpoint = try CapabilityAndroidRegistry.shared.acquireEndpoint(slot: slot, facade: facade, terminal: terminal)
        let capsule = try CapabilityAndroidLifetimeControl.spawn(endpoint)
        return try CapabilityGuestUIPresentationLifetime.consumeAndroidHost(capsule)
    }
    private func setCurrent(_ installation: CapabilityAndroidHostInstallation) { lock.lock(); current = installation; lock.unlock() }
    fileprivate func acceptPrepared(_ installation: CapabilityAndroidHostInstallation) throws {
        lock.lock(); defer { lock.unlock() }
        guard !transferred, !finalJoining, result == .pending, current?.key == installation.key,
              let moved = installation.move() else { throw coldStartError("android_prepared_move") }
        transferred = true; initial = moved; current = moved
    }
    private func beginBind() throws -> CapabilityAndroidHostInstallation? {
        lock.lock(); defer { lock.unlock() }
        guard transferred, !closing, !binding, !finalJoining, result == .pending else { throw coldStartError("android_bind_gate") }
        if let initial {
            guard let moved = initial.move() else { throw coldStartError("android_initial_move") }
            self.initial = nil; binding = true; return moved
        }
        if let current {
            guard case .finished(.retired) = current.status else { throw coldStartError("android_previous_join") }
        }
        binding = true; return nil
    }
    private func endBind(_ installation: CapabilityAndroidHostInstallation) -> Bool {
        lock.lock(); current = installation; binding = false; let live = !closing; lock.unlock(); return live
    }
    func bindHost(_ exchange: GuestUIExchangeV1) async throws -> CapabilityAndroidHostInstallation {
        let existing: CapabilityAndroidHostInstallation?
        do { existing = try beginBind() }
        catch { exchange.stop(.closed); throw error }
        let installation: CapabilityAndroidHostInstallation
        do { installation = try existing ?? makeInstallation(terminal: false) }
        catch { finishFailedAdmission(); exchange.stop(.closed); throw error }
        do {
            try installation.bind(exchange)
            guard endBind(installation) else { throw coldStartError("android_close_won_bind") }
            return installation
        } catch {
            exchange.stop(.closed); installation.requestStop(.closed)
            _ = endBind(installation)
            let joined = await installation.finish()
            if case .finished(.retired) = joined {} else { quarantine(.cleanupPending) }
            throw error
        }
    }
    private func finishFailedAdmission() { lock.lock(); binding = false; lock.unlock(); quarantine(.cleanupPending) }
    func requestFinalClose(_ cause: CapabilityAttemptLocalStop) {
        lock.lock(); closing = true; let current = current; lock.unlock()
        let control = CapabilityAndroidRegistry.shared.close(slot: slot, facade: facade)
        _ = mxuit_facade_begin_close(facade)
        current?.requestStop(cause); control?.requestStop(cause)
    }
    private enum FinalAdmission {
        case owner(CapabilityAndroidHostInstallation?, CapabilityAndroidHostInstallation?)
        case early(CapabilityAndroidHostFinalCloseStatus)
    }
    private func beginFinal(_ supplied: CapabilityAndroidHostInstallation?) -> FinalAdmission {
        lock.lock(); defer { lock.unlock() }
        if result != .pending { return .early(result) }
        if finalJoining || binding { return .early(.pending) }
        guard closing else { return .early(.invariant(.invalidState)) }
        if let supplied {
            guard supplied.key == current?.key, let moved = supplied.move() else { return .early(.invariant(.wrongJoinOwner)) }
            finalJoining = true; return .owner(moved, current)
        }
        if let initial {
            guard let moved = initial.move() else { return .early(.invariant(.wrongJoinOwner)) }
            self.initial = nil; finalJoining = true; return .owner(moved, current)
        }
        guard let current, case .finished = current.status else { return .early(.invariant(.wrongJoinOwner)) }
        finalJoining = true; return .owner(nil, current)
    }
    func finishFinalClose(using installation: CapabilityAndroidHostInstallation?) async -> CapabilityAndroidHostFinalCloseStatus {
        requestFinalClose(.closed)
        let owned: CapabilityAndroidHostInstallation?
        let readback: CapabilityAndroidHostInstallation?
        switch beginFinal(installation) {
        case .early(let value): return value
        case .owner(let owner, let current): owned = owner; readback = current
        }
        let joined: CapabilityAndroidHostJoinStatus
        if let owned { joined = await owned.finish() }
        else { joined = readback?.status ?? .invariant(.wrongJoinOwner) }
        guard case .finished(.retired(let oldReceipt)) = joined else { return quarantine(.cleanupPending) }
        var last = oldReceipt
        if last.facadeCleanup == nil {
            // Exactly one fresh sequential terminal endpoint after prior Task
            // return and endpoint reclaim; no exchange or guest is restarted.
            let terminal: CapabilityAndroidHostInstallation
            do { terminal = try makeInstallation(terminal: true); setCurrent(terminal) }
            catch { return quarantine(.cleanupPending) }
            terminal.requestStop(.closed)
            guard case .finished(.retired(let receipt)) = await terminal.finish(), receipt.facadeCleanup != nil else { return quarantine(.cleanupPending) }
            last = receipt
        }
        guard let cleanup = last.facadeCleanup,
              let record = CapabilityAndroidRegistry.shared.record(slot: slot, facade: facade),
              record.withLock({ $0.cleanup?.key == last.key && $0.cleanup?.cleanupSerial == cleanup.cleanupSerial &&
                  $0.cleanup?.finalEntrySerial == cleanup.finalEntrySerial && !$0.lookupEnabled && $0.endpoint == 0 &&
                  $0.setupAliases == 0 && $0.uiAliases == 0 && !$0.quarantined }) else { return quarantine(.missingPublishedResources) }
        let reclaimed = await CapabilityAndroidProgress.shared.waitFacade(facade, slot: slot)
        guard reclaimed == Int32(MXUIT_OK.rawValue) else { return quarantine(.cleanupPending) }
        var transport = mxuit_snapshot()
        guard mxuit_inspect(&transport) == Int32(MXUIT_OK.rawValue),
              transport.ui_entry_fenced >= cleanup.finalEntrySerial,
              CapabilityAndroidRegistry.shared.removeFacade(slot: slot, facade: facade) else { return quarantine(.invalidState) }
        // No strong resource aliases exist in this frame. retire() moves the
        // sole retained resource and waits for its actual destructor to return.
        obligation.retire()
        guard CapabilityAndroidHostFinalObligations.shared.clearAfterRetirement(slot: slot, facade: facade),
              CapabilityAndroidRegistry.shared.releaseFacadeReservation(slot: slot, facade: facade) else { return quarantine(.invalidState) }
        let receipt = CapabilityAndroidHostFinalReceipt(facade: facade, lastLifetime: last,
            facadeCleanup: cleanup, facadeReturnFence: transport.ui_entry_fenced)
        return publishFinal(receipt)
    }
    private func publishFinal(_ receipt: CapabilityAndroidHostFinalReceipt) -> CapabilityAndroidHostFinalCloseStatus {
        lock.lock(); result = .finished(receipt); finalJoining = false; let value = result; lock.unlock(); return value
    }
    @discardableResult private func quarantine(_ code: CapabilityAndroidHostFailureCode) -> CapabilityAndroidHostFinalCloseStatus {
        CapabilityAndroidRegistry.shared.quarantine(slot: slot, facade: facade); obligation.quarantine()
        lock.lock()
        if result == .pending { result = .quarantined(.init(key: current?.key, code: code)) }
        finalJoining = false; let value = result; lock.unlock(); return value
    }
    var finalStatus: CapabilityAndroidHostFinalCloseStatus { lock.lock(); defer { lock.unlock() }; return result }
    deinit { if case .finished = result {} else { obligation.quarantine() } }
}

final class CapabilityAndroidHostPreparedPresentation: @unchecked Sendable {
    let binding: CapabilityGuestUIAndroidBinding
    private let reservation: CapabilityAttemptReservation
    private let lock = NSLock()
    private var initial: CapabilityAndroidHostInstallation?
    private var transferred = false
    fileprivate init(binding: CapabilityGuestUIAndroidBinding, reservation: CapabilityAttemptReservation,
                     initial: CapabilityAndroidHostInstallation) {
        self.binding = binding; self.reservation = reservation; self.initial = initial
    }
    func transferToBinding() throws {
        lock.lock(); defer { lock.unlock() }
        guard !transferred, let initial else { throw coldStartError("android_prepared_consumed") }
        try binding.acceptPrepared(initial); self.initial = nil; transferred = true
    }
    private func take() -> CapabilityAndroidHostInstallation? {
        lock.lock(); defer { lock.unlock() }
        guard !transferred, let moved = initial?.move() else { return nil }; initial = nil; transferred = true; return moved
    }
    func cleanupAfterFailure() async -> CapabilityAndroidHostFinalCloseStatus {
        guard let installation = take() else { return .invariant(.wrongJoinOwner) }
        binding.requestFinalClose(.closed)
        return await binding.finishFinalClose(using: installation)
    }
    deinit {
        if !transferred { binding.requestFinalClose(.closed); reservation.quarantine() }
    }
}
#endif
