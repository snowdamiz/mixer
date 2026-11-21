import Foundation
import MixerUI

/// Explicitly unselected candidate. Reuses the existing single-slot arbitration,
/// actual ready claims, stop/intent and receipt machinery, without duplicating it.
/// V1 control values here are shared data-only types, never V1 wire selection.
@_spi(GuestUIV1) public final class GuestUIExchangeV1: Sendable {
    private let core: GuestUIExchangeCore
    public let allowsDeferredStartup: Bool
    public convenience init(generation: UInt64) throws {
        try self.init(generation: generation, allowsDeferredStartup: false)
    }
    public init(generation: UInt64, allowsDeferredStartup: Bool) throws {
        self.allowsDeferredStartup = allowsDeferredStartup
        core = try GuestUIExchangeCore(generation: generation, codec: .legacy)
    }
#if os(macOS) && MIXER_PRIVATE_FIELDLOG_EDITOR
    @_spi(PrivateFieldLogEditor)
    public init(fieldLogEditorGeneration generation: UInt64) throws {
        allowsDeferredStartup = false
        core = try GuestUIExchangeCore(generation: generation, codec: .fieldLogEditor)
    }

    @_spi(PrivateFieldLogEditor)
    public func offerFieldLogEditorAction(_ action: IssuedUIAction, generation: UInt64) -> GuestUIEventAdmissionV1 {
        guard core.requiresBoundedIssuedEvent else { return .invalid(.invalidValue) }
        return core.offerIssued(action, generation: generation)
    }

    @_spi(PrivateFieldLogEditor)
    public func completeUnchangedFieldLogEditorPresentation(_ claim: GuestUIPresentationClaimV1) -> Bool {
        core.requiresBoundedIssuedEvent && core.completeUnchangedPresentation(claim) != nil
    }
#endif
    public func finishStartupWithoutDocument(_ claim: GuestUITurnClaimV1) throws {
        guard allowsDeferredStartup else { throw GuestUIControlRejectionV1.staleClaim }
        try core.finishStartupWithoutDocument(claim)
    }
    public func finishHydrationHook(_ claim: GuestUITurnClaimV1) throws {
        guard allowsDeferredStartup else { throw GuestUIControlRejectionV1.staleClaim }
        try core.finishHydrationHook(claim)
    }
    public var deliveryWake: GuestUIWakeV1 { core.deliveryWake }
    public var coordinatorWake: GuestUIWakeV1 { core.coordinatorWake }
    public func takeNativeInputReadinessConsumer() throws -> GuestUINativeInputReadinessConsumerV1 {
        try core.takeNativeInputReadinessConsumer()
    }
    public func claimStartup() throws -> GuestUITurnClaimV1 { try core.claimStartup() }
    public func claimNextTurn(ready: Bool) throws -> GuestUITurnClaimV1? { try core.claimNextTurn(ready: ready) }
    public func finishReadyWithoutInvocation(_ claim: GuestUITurnClaimV1) throws { try core.finishReadyWithoutInvocation(claim) }
    public func finishTurn(_ claim: GuestUITurnClaimV1, documentBytes: Data) throws {
        try core.finishTurn(claim, documentBytes: documentBytes)
    }
    public func finishTurn(_ claim: GuestUITurnClaimV1, documentBytes: Data, startupCutoff: UInt64?) throws {
        try core.finishTurn(claim, documentBytes: documentBytes, startupCutoff: startupCutoff)
    }
    public func offer(_ event: UIEventEnvelope, generation: UInt64) -> GuestUIEventAdmissionV1 { core.offer(event, generation: generation) }
    public func offerNativeInput(_ event: UIEventEnvelope, generation: UInt64) -> GuestUINativeInputAdmissionV1 { core.offerNativeInput(event, generation: generation) }
    public func claimPresentation(generation: UInt64) -> GuestUIPresentationClaimV1? { core.claimPresentation(generation: generation) }
    public func completePresentation(_ claim: GuestUIPresentationClaimV1, snapshot: UIRenderSnapshot?) -> GuestUIPresentationTicketV1? {
        core.completePresentation(claim, snapshot: snapshot)
    }
    public func observePresentation(_ ticket: GuestUIPresentationTicketV1) -> Bool { core.observePresentation(ticket) }
    public func consumeObservedPresentation(generation: UInt64, frameSerial: UInt64) { core.consumeObservedPresentation(generation: generation, frameSerial: frameSerial) }
    public func enterEffectsIntent(generation: UInt64) throws { try core.enterEffectsIntent(generation: generation) }
    public func confirmEffectsEnabled(generation: UInt64) throws { try core.confirmEffectsEnabled(generation: generation) }
    public func requireCommitEntry(generation: UInt64) throws { try core.requireCommitEntry(generation: generation) }
    public func requireEffectAdmission(generation: UInt64) throws { try core.requireEffectAdmission(generation: generation) }
    public func recordProtocolFailure(_ failure: GuestUIProtocolFailureV1) { core.recordProtocolFailure(failure) }
    public func stop(_ cause: GuestUIExternalStopV1) { core.stop(cause) }
    public func snapshot() -> GuestUIExchangeSnapshotV1 { core.snapshot() }
}
