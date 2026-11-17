#if canImport(Crypto)
import Foundation
import Crypto
import MixerUI

// Only exchange admission can emit this signal. Backend errors retain their cause.
internal enum SwiftFeatureInputRefusal: Error { case invalidOrStale }

/// Internal exchange engine. Scope is the sole admission, scheduling and close owner.
@MainActor internal final class SwiftFeatureSession {
    private let exchange: GuestUIExchangeCore
    private let lease: SwiftFeatureLease
    private let presenter: any SwiftFeatureNativePresenter
    private let startup: GuestUITurnClaimV1
    private var presentation: Task<NativeDisplayAcknowledgement, any Error>?
    private var retired = false
    init(exchange: GuestUIExchangeCore, startup: GuestUITurnClaimV1, lease: SwiftFeatureLease, presenter: any SwiftFeatureNativePresenter) {
        self.exchange = exchange; self.startup = startup; self.lease = lease; self.presenter = presenter
    }
    static func prepare(_ packet: Data, grant: ReviewedDevelopmentGrant) throws -> (GuestUIExchangeCore, GuestUITurnClaimV1) {
        try Task.checkCancellation()
        let codec = FeatureDocumentV3(textValuePolicy: .standard)
        guard packet.count > 0, packet.count <= 64 * 1024 * 1024,
              grant.surfaceKinds.isSuperset(of: codec.validator.supportedKinds),
              artifactDigest(packet) == grant.artifactSHA256 else { throw SwiftFeatureError.grant }
        guard grant.executionProfile == .development256 else { throw SwiftFeatureError.grant }
        let exchange = try GuestUIExchangeCore(generation: 1, codec: .feature(codec))
        return (exchange, try exchange.claimStartup())
    }
    static func artifactDigest(_ bytes: Data) -> String {
        SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }
    private func requireActive() throws {
        try Task.checkCancellation()
        guard !retired else { throw CancellationError() }
    }
    func start() async throws -> UIRenderSnapshot {
        try requireActive()
        let bytes = try lease.frame()
        try requireActive()
        try exchange.finishTurn(startup, documentBytes: bytes)
        return try await present(startup: true)
    }
    func send(_ action: IssuedUIAction) async throws -> UIRenderSnapshot {
        try requireActive()
        guard case .accepted = exchange.offerIssued(action, generation: 1),
              let claim = try exchange.claimNextTurn(ready: false),
              case .event(_, let bytes) = claim.kind else { throw SwiftFeatureInputRefusal.invalidOrStale }
        try requireActive()
        try lease.event(bytes)
        try requireActive()
        let documentBytes = try lease.frame()
        try requireActive()
        try exchange.finishTurn(claim, documentBytes: documentBytes)
        return try await present(startup: false)
    }
    private func present(startup: Bool) async throws -> UIRenderSnapshot {
        try requireActive()
        guard let claim = exchange.claimPresentation(generation: 1) else { throw SwiftFeatureError.presentation }
        guard let frame = claim.frame else {
            guard !startup, let unchanged = exchange.completeUnchangedPresentation(claim) else { throw SwiftFeatureError.presentation }
            return unchanged
        }
        let request = NativePresentationRequest(document: frame.document)
        let task = Task { @MainActor in
            try self.requireActive()
            return try await self.presenter.present(request)
        }
        presentation = task
        defer { presentation = nil }
        let acknowledgement = try await withTaskCancellationHandler {
            try await task.value
        } onCancel: { task.cancel() }
        try requireActive()
        guard request.accepts(acknowledgement) else { throw SwiftFeatureError.presentation }
        if startup { try exchange.enterEffectsIntent(generation: 1); try exchange.confirmEffectsEnabled(generation: 1) }
        guard let ticket = exchange.completePresentation(claim, snapshot: acknowledgement.snapshot), exchange.observePresentation(ticket) else { throw SwiftFeatureError.presentation }
        exchange.consumeObservedPresentation(generation: 1, frameSerial: ticket.frameSerial)
        return acknowledgement.snapshot
    }
    func cancelPresentation() {
        retired = true
        presentation?.cancel()
    }
    func consume() -> SwiftFeatureCloseOutcome { cancelPresentation(); exchange.stop(.closed); return lease.consume() }
}
#endif
