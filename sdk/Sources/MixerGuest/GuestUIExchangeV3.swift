import Foundation
import MixerUI

/// Explicitly unselected candidate. Reuses the existing single-slot arbitration,
/// actual ready claims, stop/intent and receipt machinery, without duplicating it.
/// V1 control values here are shared data-only types, never V1 wire selection.
@_spi(FeatureUIV3) public final class GuestUIExchangeV3: Sendable {
    private let core: GuestUIExchangeCore
    public let codec: FeatureDocumentV3
    public init(generation: UInt64, textValuePolicy: UITextValuePolicy) throws {
        codec = FeatureDocumentV3(textValuePolicy: textValuePolicy)
        core = try GuestUIExchangeCore(generation: generation, codec: .feature(codec))
    }
    public var deliveryWake: GuestUIWakeV1 { core.deliveryWake }
    public var coordinatorWake: GuestUIWakeV1 { core.coordinatorWake }
    public func takeNativeInputReadinessConsumer() throws -> GuestUINativeInputReadinessConsumerV1 {
        try core.takeNativeInputReadinessConsumer()
    }
    public func claimStartup() throws -> GuestUITurnClaimV1 { try core.claimStartup() }
    public func claimNextTurn(ready: Bool) throws -> GuestUITurnClaimV1? { try core.claimNextTurn(ready: ready) }
    public func finishReadyWithoutInvocation(_ claim: GuestUITurnClaimV1) throws { try core.finishReadyWithoutInvocation(claim) }
    public func finishTurn(_ claim: GuestUITurnClaimV1, documentBytes: Data) throws { try core.finishTurn(claim, documentBytes: documentBytes) }
#if os(macOS) && MIXER_PRIVATE_F10
    public func finishFieldLogHydration(_ claim: GuestUITurnClaimV1, documentBytes: Data, startupCutoff: UInt64) throws {
        try core.finishTurn(claim, documentBytes: documentBytes, startupCutoff: startupCutoff) { document in
            document.revision == 2 && document.root.properties["disabled"]?.bool != true
                && document.root.children.contains { node in
                    node.id == "workspace.queue" && node.kind == .button && node.properties["disabled"]?.bool != true
                        && node.actions.contains { $0.id == "workspace.queue" && $0.event == .activate }
                }
        }
    }
#endif
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
