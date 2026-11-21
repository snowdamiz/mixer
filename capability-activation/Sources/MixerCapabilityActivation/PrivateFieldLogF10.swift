#if os(macOS) && MIXER_PRIVATE_F10
import Foundation
import MixerCapabilities
import MixerApple
@_spi(GuestUIV1) @_spi(FeatureUIV3) import MixerGuest
import MixerUI

struct F10ReadOnlyStorage: InstalledApplicationStorageServing {
    let repository: any InstalledApplicationStorageServing

    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        guard arguments.namespace == "material_test", arguments.key == "queue-0" else {
            throw materialError("private_f10_storage")
        }
        return try await repository.get(arguments)
    }

    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        throw materialError("private_f10_storage")
    }

    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        throw materialError("private_f10_storage")
    }
}

/// Trusted headless test embedding. The activation owner stops the exchange and
/// joins the attempt. This binding owns only the render snapshot and exchange.
@MainActor final class F10HeadlessPresenter: CapabilityColdStartPresentation {
    private(set) var exchange: GuestUIExchangeV3?
    private(set) var host: MixerUIHost?
    private(set) var eventResult: GuestUIEventResultV1?
    private(set) var inertRevision: UInt64?

    func bind(_ exchange: GuestUIExchangeV3) throws {
        guard self.exchange == nil || self.exchange?.snapshot().stop != nil else { throw coldStartError("presentation") }
        self.exchange = exchange
        host = nil
        inertRevision = nil
        eventResult = nil
    }

    func presentInert(_ exchange: GuestUIExchangeV3) throws {
        let state = exchange.snapshot()
        guard self.exchange === exchange, !state.effectsMayHaveOpened,
              let claim = exchange.claimPresentation(generation: state.generation),
              let document = claim.frame?.document.document,
              document.revision == 1, document.root.id == "f10.loading", document.root.kind == .text,
              document.root.actions.isEmpty, document.root.children.isEmpty,
              document.root.properties["text"]?.string == "Loading pending changes…" else {
            throw coldStartError("private_f10_inert_presentation")
        }
        _ = try render(exchange, claim: claim, document: document)
        inertRevision = document.revision
    }

    func presentNext() throws {
        guard let exchange else { return }
        let state = exchange.snapshot()
        guard state.effectsConfirmed, let claim = exchange.claimPresentation(generation: state.generation) else { return }
        if let result = claim.eventResult { eventResult = result }
        guard let document = claim.frame?.document.document, claim.stop == nil else {
            _ = exchange.completePresentation(claim, snapshot: nil)
            return
        }
        let ticket = try render(exchange, claim: claim, document: document)
        if ticket.revision == 2, !exchange.observePresentation(ticket) { throw coldStartError("presentation") }
    }

    private func render(_ exchange: GuestUIExchangeV3, claim: GuestUIPresentationClaimV1,
                        document: UIDocument) throws -> GuestUIPresentationTicketV1 {
        if let host { try host.update(document) }
        else { host = try MixerUIHost(document: document, validator: exchange.codec.validator) }
        guard let host, let ticket = exchange.completePresentation(claim, snapshot: host.snapshot) else {
            throw coldStartError("presentation")
        }
        return ticket
    }

    nonisolated func bindForStartup(_ exchange: GuestUIExchangeV1) async throws -> any CapabilityObservedPresentation {
        throw coldStartError("installed_mode")
    }

    nonisolated func requestFinalClose(_ cause: CapabilityAttemptLocalStop) {
        // The shared activation control owns the synchronous stop latch.
    }

    func finishForClose() async -> Bool {
        let stopped = exchange == nil || exchange?.snapshot().stop != nil
        exchange = nil
        host = nil
        return stopped
    }
}
#endif
