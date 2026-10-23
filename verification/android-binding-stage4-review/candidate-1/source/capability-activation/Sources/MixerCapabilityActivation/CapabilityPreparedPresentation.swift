import Foundation
@_spi(GuestUIV1) import MixerGuest

/// Explicit async-open guard. Its armed state owns the initial permit until the
/// core's control accepts that same move. Deinit quarantines; it never spawns work.
final class CapabilityPreparedPresentation: @unchecked Sendable {
    let binding: CapabilityGuestUIPresentationBinding
    private let reservation: CapabilityAttemptReservation
    private let lock = NSLock()
    private var installation: CapabilityPresentationInstallation?
    private var armed = true
    init(binding: CapabilityGuestUIPresentationBinding, reservation: CapabilityAttemptReservation,
         installation: CapabilityPresentationInstallation) {
        self.binding = binding; self.reservation = reservation; self.installation = installation
    }
    func transfer(to core: CapabilityColdStartCloseCore) throws {
        guard core.guestUIBinding === binding else { throw coldStartError("presentation_core") }
        try transfer(to: core.control)
    }
    func transfer(to control: CapabilityColdStartControl) throws {
        lock.lock(); defer { lock.unlock() }
        guard armed, reservation === control.reservation, let installation,
              control.acceptPreparedPresentation(binding, installation: installation) else { throw coldStartError("presentation_transfer") }
        self.installation = nil; armed = false
    }
    private func takeCleanup() -> (Bool, CapabilityPresentationJoinPermit?) {
        lock.lock(); defer { lock.unlock() }
        guard armed else { return (false, nil) }
        armed = false
        let permit = installation?.takePermit(); installation = nil
        return (true, permit)
    }
    func cleanupAfterFailure() async -> CapabilityPresentationJoinStatus {
        let (first, permit) = takeCleanup()
        guard first else { return binding.finalStatus }
        binding.requestFinalClose(.closed)
        return await binding.finishFinalClose(using: permit)
    }
    deinit { if armed { reservation.quarantine() } }
}

/// All nonisolated state is data and move cells. Apple model access remains on
/// MainActor. Future Android resources do not enter this common gate.
final class CapabilityPresentationBindingGate: @unchecked Sendable {
    private let lock = NSLock()
    private let obligation: CapabilityPresentationObligation
    private var current: CapabilityGuestUIPresentationLifetime?
    private var coreInstallation: CapabilityPresentationInstallation?
    private var accepted = false
    private var closed = false
    private var finalJoining = false
    private var finalResult: CapabilityPresentationJoinStatus = .pending
    init(obligation: CapabilityPresentationObligation) { self.obligation = obligation }
    func initial(retirement: any CapabilityPresentationRetirement) throws -> CapabilityPresentationInstallation {
        lock.lock(); defer { lock.unlock() }
        guard current == nil, !closed else { throw coldStartError("presentation_initial") }
        let lifetime = CapabilityGuestUIPresentationLifetime(id: try .issue(), facade: current?.facade, retirement: retirement)
        let installation = try lifetime.installation(); current = lifetime; return installation
    }
    func accept(_ initial: CapabilityPresentationInstallation) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard !closed, !accepted, current === initial.lifetime, let moved = initial.move() else { return false }
        coreInstallation = moved; accepted = true; return true
    }
    func beginBind(retirement: any CapabilityPresentationRetirement) throws -> CapabilityPresentationInstallation {
        lock.lock(); defer { lock.unlock() }
        guard !closed, accepted else { throw coldStartError("presentation_closed") }
        if let initial = coreInstallation {
            guard let moved = initial.move() else { throw coldStartError("presentation_permit") }
            coreInstallation = nil; return moved
        }
        // The exact prior immutable receipt is observed before replacing its
        // record. A task-return hint alone cannot admit the next lifetime.
        guard current?.status.isRetired == true else { throw GuestUIControlRejectionV1.busy }
        let lifetime = CapabilityGuestUIPresentationLifetime(id: try .issue(), facade: current?.facade, retirement: retirement)
        let installation = try lifetime.installation(); current = lifetime; return installation
    }
    func requestClose(_ cause: CapabilityAttemptLocalStop) {
        lock.lock(); closed = true; let lifetime = current; lock.unlock()
        lifetime?.requestStop(cause)
    }
    func takeCorePermit() -> CapabilityPresentationJoinPermit? {
        lock.lock(); defer { lock.unlock() }
        let permit = coreInstallation?.takePermit(); coreInstallation = nil; return permit
    }
    var status: CapabilityPresentationJoinStatus { lock.lock(); defer { lock.unlock() }; return finalResult }
    private func beginFinal() -> (CapabilityGuestUIPresentationLifetime?, CapabilityPresentationJoinStatus?) {
        lock.lock(); defer { lock.unlock() }
        guard closed else { return (nil, .invariant(.invalidState)) }
        if finalResult != .pending { return (nil, finalResult) }
        if finalJoining { return (nil, .pending) }
        finalJoining = true; return (current, nil)
    }
    private func publishFinal(_ value: CapabilityPresentationJoinStatus) {
        lock.lock(); finalResult = value; finalJoining = false; lock.unlock()
    }
    func finish(using permit: CapabilityPresentationJoinPermit?) async -> CapabilityPresentationJoinStatus {
        let (lifetime, early) = beginFinal()
        if let early { return early }
        let result: CapabilityPresentationJoinStatus
        if let lifetime {
            if let permit { result = await lifetime.finish(using: permit) }
            else {
                let status = lifetime.status
                result = status.isRetired ? status : .invariant(.wrongJoinOwner)
            }
        } else { result = .invariant(.invalidState) }
        // No reusable reservation state is released on pending/invariant/failure.
        // Apple has no reservation-owned model alias and makes no destructor claim.
        if result.isRetired { obligation.retire() } else { obligation.quarantine() }
        publishFinal(result); return result
    }
    func quarantine() { obligation.quarantine() }
}
