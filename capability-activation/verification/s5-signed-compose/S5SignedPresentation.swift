#if MIXER_S5_SIGNED_COMPOSE
import Foundation
@_spi(GuestUIV1) @_spi(S5SignedCompose) import MixerGuest
import MixerUI

/// The window bridge supplies the queued-buffer acknowledgment. The delivery
/// consumer can prepare snapshots and advance a previously admitted Save.
@_spi(S5SignedCompose)
public final class S5SignedPresentation: @unchecked Sendable {
    public struct Frame: Sendable {
        public let id: UUID
        public let snapshot: UIRenderSnapshot
    }

    private struct Pending {
        let frame: Frame
        let claim: GuestUIPresentationClaimV1
    }

    private enum Save {
        case offerDraft(UIEventEnvelope, UIEventEnvelope)
        case awaitDraft(UInt64, UIEventEnvelope)
        case offerSave(UIEventEnvelope)
        case awaitSave(UInt64)
        case awaitSaveFrame
    }

    private let lock = NSLock()
    private var exchange: GuestUIExchangeV1?
    private var reconciler = UIReconciler()
    private var pending: Pending?
    private var shown: Frame?
    private var save: Save?
    private var closing = false
    private var healthy = false

    public init() {}

    public var deliveredEvents: UInt64 {
        lock.withLock { exchange?.snapshot().counters.deliveredEvents ?? 0 }
    }

    public func frame() -> Frame? {
        lock.withLock { pending?.frame }
    }

    public func enableInputAfterHealth() -> Bool {
        lock.withLock {
            guard !closing, let exchange, exchange.snapshot().stop == nil, shown != nil else { return false }
            healthy = true
            return true
        }
    }

    public func present(_ id: UUID) -> Bool {
        lock.withLock {
            guard !closing, let exchange, let pending, id == pending.frame.id,
                  exchange.snapshot().effectsConfirmed, exchange.snapshot().stop == nil,
                  let ticket = exchange.completePresentation(pending.claim, snapshot: pending.frame.snapshot),
                  exchange.observePresentation(ticket) else { return false }
            shown = pending.frame
            self.pending = nil
            if case .awaitSaveFrame = save { save = nil }
            return true
        }
    }

    public func discard(_ id: UUID) -> Bool {
        lock.withLock {
            guard !closing, let exchange, let pending, pending.frame.id == id else { return false }
            if healthy {
                guard exchange.cancelS5PresentationV1(pending.claim, snapshot: pending.frame.snapshot) else { return false }
                if case .awaitSaveFrame = save { save = nil }
            } else {
                // A lost first frame cannot earn health or admit input.
                exchange.stop(.closed)
                _ = exchange.completePresentation(pending.claim, snapshot: nil)
                shown = nil
                save = nil
            }
            self.pending = nil
            return true
        }
    }

    public func submit(_ draft: UIEventEnvelope, save activation: UIEventEnvelope, from id: UUID) -> Bool {
        lock.withLock {
            guard !closing, healthy, let exchange, exchange.snapshot().stop == nil,
                  pending == nil, save == nil, let shown, shown.id == id,
                  let change = try? shown.snapshot.route(draft), change.nodeID == "title",
                  change.event == .textChange, let title = change.value.string,
                  (1...512).contains(title.utf8.count), title.utf8.allSatisfy({ $0 >= 32 }),
                  let action = try? shown.snapshot.route(activation), action.nodeID == "save",
                  action.event == .activate else { return false }
            save = .offerDraft(draft, activation)
            offerQueued(on: exchange)
            return save != nil
        }
    }

    private func receive(_ exchange: GuestUIExchangeV1) {
        lock.withLock {
            guard !closing, self.exchange === exchange else { return }
            let generation = exchange.snapshot().generation
            if let claim = exchange.claimPresentation(generation: generation) {
                if claim.stop != nil {
                    _ = exchange.completePresentation(claim, snapshot: nil)
                    pending = nil
                    shown = nil
                    save = nil
                    return
                }
                if let event = claim.eventResult, event.outcome == .delivered {
                    if case .awaitDraft(let sequence, let activation) = save, event.sequence == sequence {
                        save = .offerSave(activation)
                    }
                    if case .awaitSave(let sequence) = save, event.sequence == sequence { save = .awaitSaveFrame }
                }
                if let document = claim.frame?.document.document {
                    do {
                        _ = try reconciler.apply(document)
                        let frame = Frame(id: UUID(), snapshot: try reconciler.currentSnapshot())
                        pending = Pending(frame: frame, claim: claim)
                    } catch {
                        _ = exchange.completePresentation(claim, snapshot: nil)
                    }
                } else {
                    _ = exchange.completePresentation(claim, snapshot: nil)
                }
            }
            offerQueued(on: exchange)
        }
    }

    /// Before an event is admitted, an internal ready turn may make the slot
    /// temporarily busy. The embedding polls this same owner without reissuing
    /// either input after its exact sequence was accepted.
    public func pump() {
        lock.withLock {
            if !closing, let exchange { offerQueued(on: exchange) }
        }
    }

    private func offerQueued(on exchange: GuestUIExchangeV1) {
        let generation = exchange.snapshot().generation
        switch save {
        case .offerDraft(let draft, let activation):
            switch exchange.offerNativeInput(draft, generation: generation) {
            case .offered(.accepted(let sequence)): save = .awaitDraft(sequence, activation)
            case .offered(.busy), .readyBusy: break
            default: save = nil
            }
        case .offerSave(let activation):
            switch exchange.offerNativeInput(activation, generation: generation) {
            case .offered(.accepted(let sequence)): save = .awaitSave(sequence)
            case .offered(.busy), .readyBusy: break
            default: save = nil
            }
        default: break
        }
    }
}

extension S5SignedPresentation: CapabilityColdStartPresentation, CapabilityPresentationRetirement {
    func bindForStartup(_ exchange: GuestUIExchangeV1) async throws -> any CapabilityObservedPresentation {
        guard exchange.s5UsesEditorV2 else { throw coldStartError("installed_mode") }
        let reader = try exchange.deliveryWake.takeConsumer()
        let lifetime = CapabilityGuestUIPresentationLifetime(id: try .issue(), retirement: self)
        let installation = try lifetime.installation()
        try lock.withLock {
            guard !closing, self.exchange == nil else { throw coldStartError("presentation") }
            self.exchange = exchange
        }
        let task = Task { [weak self] in
            do {
                while try await reader.next() { self?.receive(exchange) }
            } catch {
                exchange.recordProtocolFailure(.init(phase: .presentation, code: .presentationInvariant))
            }
        }
        guard lifetime.attach(task, exchange: exchange) else {
            exchange.stop(.closed)
            await task.value
            _ = await installation.finish()
            throw coldStartError("presentation")
        }
        return installation
    }

    func requestFinalClose(_ cause: CapabilityAttemptLocalStop) {
        lock.withLock {
            closing = true
            exchange?.stop(.closed)
        }
    }

    func finishForClose() async -> Bool { lock.withLock { exchange == nil } }
    func retireEmptyPresentation() async -> Bool {
        lock.withLock {
            exchange = nil
            pending = nil
            shown = nil
            save = nil
            reconciler = UIReconciler()
            return true
        }
    }
}
#endif
