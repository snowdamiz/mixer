import Foundation
@_spi(GuestUIV1) import MixerGuest

#if canImport(SwiftUI) && canImport(MixerApple)
import SwiftUI
import MixerUI
import MixerApple

/// The displayed state of the privately bound guest screen. This model exposes
/// observation only; the signed activation coordinator owns its construction.
public enum GuestUIPresentationState: Sendable, Equatable {
    case waiting
    case displaying(revision: UInt64)
    case stopped
}

@MainActor
public final class GuestUIPresentation: ObservableObject {
    @Published public private(set) var state: GuestUIPresentationState = .waiting
    @Published internal private(set) var renderHost: MixerUIHost?
    @Published private var inputReady = false
    // Native representable attach/dismantle callbacks may run while SwiftUI is
    // invalidating its graph. Revoke attachment authority synchronously without
    // publishing back into that same graph. The sole consumer publishes ordinary
    // readiness changes; a new native subtree reads this gate after attachment.
    internal var inputEnabled: Bool {
        inputReady && attachment != nil && !pendingAttachmentInvariant && exchange?.snapshot().stop == nil
    }

    private var exchange: GuestUIExchangeV1?
    private var bindingIdentity: CapabilityGuestUIBindingIdentity?
    private var ticket: GuestUIPresentationTicketV1?
    private var observedNativeDisplay = false
    private var attachment: CapabilityGuestUIAttachmentIdentity?
    private var pendingAttachmentInvariant = false
    private weak var attachmentObserver: (any CapabilityGuestUIAttachmentObserver)?
    internal private(set) var lastEventResult: GuestUIEventResultV1?

    internal init() {}

    fileprivate func requireBindable() throws {
        guard bindingIdentity == nil else { throw GuestUIControlRejectionV1.busy }
    }

    fileprivate func bind(_ exchange: GuestUIExchangeV1,
                          identity: CapabilityGuestUIBindingIdentity) throws {
        guard bindingIdentity == nil else { throw GuestUIControlRejectionV1.busy }
        attachmentObserver?.invalidatePresentationProbe()
        renderHost = nil; ticket = nil; lastEventResult = nil
        inputReady = false; observedNativeDisplay = false
        self.exchange = exchange; bindingIdentity = identity; state = .waiting
        if pendingAttachmentInvariant {
            pendingAttachmentInvariant = false
            if exchange.snapshot().stop == nil {
                exchange.recordProtocolFailure(GuestUIProtocolFailureV1(phase: .presentation, code: .presentationInvariant))
            }
            state = .stopped
        }
        attachmentObserver?.presentationChanged()
    }

    /// Called by the sole consumer without suspension. No strong model or frame
    /// local escapes this helper into the next parked wake.
    fileprivate static func consume(_ box: CapabilityGuestUIWeakPresentation) {
        guard let model = box.model, model.bindingIdentity === box.identity,
              let exchange = model.exchange else { return }
        guard let claim = exchange.claimPresentation(generation: exchange.snapshot().generation) else { return }
        if let result = claim.eventResult { model.lastEventResult = result }
        if claim.stop != nil {
            _ = exchange.completePresentation(claim, snapshot: nil)
            model.retire(identity: box.identity)
            return
        }
        do {
            if let frame = claim.frame {
                model.attachmentObserver?.invalidatePresentationProbe()
                model.ticket = nil
                if let host = model.renderHost {
                    try host.update(frame.document.document)
                } else {
                    model.renderHost = try MixerUIHost(document: frame.document.document)
                }
            }
            let completed = exchange.completePresentation(claim, snapshot: model.renderHost?.snapshot)
            // Close may win while @Published or host reconciliation is running.
            // The same MainActor turn retires the transient admitted frame.
            guard exchange.snapshot().stop == nil else {
                // Preserve this binding until the final stop hint carries any
                // terminal result that was not part of the current claim.
                model.retireView(); return
            }
            if let completed { model.ticket = completed; model.state = .displaying(revision: completed.revision) }
            if let result = claim.eventResult { model.lastEventResult = result }
            model.refreshInput()
            model.attachmentObserver?.presentationChanged()
        } catch {
            exchange.recordProtocolFailure(GuestUIProtocolFailureV1(phase: .presentation, code: .presentationInvariant))
            _ = exchange.completePresentation(claim, snapshot: nil)
            model.retireView()
        }
    }

    fileprivate static func consumerFailed(_ box: CapabilityGuestUIWeakPresentation) {
        guard let model = box.model, model.bindingIdentity === box.identity, let exchange = model.exchange else { return }
        if exchange.snapshot().stop == nil {
            exchange.recordProtocolFailure(GuestUIProtocolFailureV1(phase: .presentation, code: .presentationInvariant))
        }
        model.retireView()
    }

    fileprivate static func finish(_ box: CapabilityGuestUIWeakPresentation) {
        guard let model = box.model, model.bindingIdentity === box.identity else { return }
        if let exchange = model.exchange, exchange.snapshot().stop == nil {
            exchange.recordProtocolFailure(GuestUIProtocolFailureV1(phase: .presentation, code: .presentationInvariant))
        }
        model.retire(identity: box.identity)
    }

    private func retire(identity: CapabilityGuestUIBindingIdentity) {
        guard bindingIdentity === identity else { return }
        retireView()
        exchange = nil; bindingIdentity = nil; observedNativeDisplay = false
    }

    private func retireView() {
        attachmentObserver?.invalidatePresentationProbe()
        inputReady = false; ticket = nil; renderHost = nil
        state = .stopped
    }

    fileprivate func retireKnownEmpty() -> Bool {
        guard bindingIdentity == nil, exchange == nil else { return false }
        retireView(); return true
    }

    private func refreshInput() {
        guard let exchange, renderHost != nil else { inputReady = false; return }
        let snapshot = exchange.snapshot()
        inputReady = snapshot.stop == nil && snapshot.effectsConfirmed && !snapshot.guestTurnInFlight &&
            !snapshot.eventOutstanding && snapshot.displayedRevision != nil &&
            snapshot.displayedRevision == snapshot.latestRevision
    }

    /// Claim before constructing a hosting controller or a platform probe.
    internal func claimNativeAttachment() -> CapabilityGuestUIAttachmentIdentity? {
        guard attachment == nil else {
            if let exchange {
                if exchange.snapshot().stop == nil {
                    exchange.recordProtocolFailure(GuestUIProtocolFailureV1(phase: .presentation, code: .presentationInvariant))
                }
            } else if state == .waiting {
                // A facade may be attached before its first signed attempt.
                // Preserve one typed failure for that attempt's exact exchange.
                pendingAttachmentInvariant = true
            }
            attachmentObserver?.invalidatePresentationProbe()
            return nil
        }
        let identity = CapabilityGuestUIAttachmentIdentity()
        attachment = identity; return identity
    }

    internal func installNativeAttachment(_ observer: any CapabilityGuestUIAttachmentObserver,
                                          identity: CapabilityGuestUIAttachmentIdentity) {
        guard attachment === identity else { return }
        attachmentObserver = observer
        observer.presentationChanged()
    }

    internal func detachNativeAttachment(_ identity: CapabilityGuestUIAttachmentIdentity) {
        guard attachment === identity else { return }
        attachmentObserver?.invalidatePresentationProbe()
        attachmentObserver = nil; attachment = nil
    }

    internal func nativeDisplayTicket(attachment identity: CapabilityGuestUIAttachmentIdentity)
        -> CapabilityGuestUIDisplayTicket? {
        guard attachment === identity, !observedNativeDisplay, let bindingIdentity, let ticket else { return nil }
        let value = CapabilityGuestUIDisplayTicket(binding: bindingIdentity, attachment: identity, ticket: ticket)
        return isCurrentNativeDisplay(value) ? value : nil
    }

    internal func isCurrentNativeDisplay(_ value: CapabilityGuestUIDisplayTicket) -> Bool {
        guard value.binding === bindingIdentity, value.attachment === attachment,
              let ticket, let exchange,
              ticket.generation == value.ticket.generation, ticket.frameSerial == value.ticket.frameSerial,
              ticket.revision == value.ticket.revision else { return false }
        let snapshot = exchange.snapshot()
        return snapshot.stop == nil && snapshot.effectsConfirmed && snapshot.generation == ticket.generation &&
            snapshot.displayedRevision == ticket.revision
    }

    // Only the private native platform probes call this after actual native
    // appearance/layout/display. Neither a document update nor start() calls it.
    internal func observeNativeDisplay(_ value: CapabilityGuestUIDisplayTicket) -> Bool {
        guard isCurrentNativeDisplay(value), !observedNativeDisplay, let exchange else { return false }
        guard exchange.observePresentation(value.ticket) else { return false }
        observedNativeDisplay = true
        return true
    }

    internal func actionHandler(host: MixerUIHost, attachment identity: CapabilityGuestUIAttachmentIdentity)
        -> @MainActor (RoutedUIAction) -> Void {
        guard let exchange else { return { _ in } }
        // Each callback retains its exact data-only exchange. It never rebuilds
        // an old callback against a host installed by a later binding.
        return { [weak self, weak host, exchange] action in
            guard let self, let host, self.exchange === exchange, self.renderHost === host,
                  self.attachment === identity else { return }
            guard let node = host.snapshot.identity(for: action.nodeID) else { return }
            let envelope = UIEventEnvelope(revision: action.revision, identity: node,
                                           event: action.event, value: action.value)
            guard (try? host.route(envelope)) == action else { return }
            _ = exchange.offer(envelope, generation: exchange.snapshot().generation)
            self.refreshInput()
        }
    }
}

internal final class CapabilityGuestUIBindingIdentity: Sendable {}
internal final class CapabilityGuestUIAttachmentIdentity: Sendable {}
internal struct CapabilityGuestUIDisplayTicket: Sendable {
    let binding: CapabilityGuestUIBindingIdentity
    let attachment: CapabilityGuestUIAttachmentIdentity
    let ticket: GuestUIPresentationTicketV1
}

@MainActor
internal protocol CapabilityGuestUIAttachmentObserver: AnyObject {
    func invalidatePresentationProbe()
    func presentationChanged()
}

@MainActor
private final class CapabilityGuestUIWeakPresentation: Sendable {
    weak var model: GuestUIPresentation?
    let identity: CapabilityGuestUIBindingIdentity
    init(_ model: GuestUIPresentation, identity: CapabilityGuestUIBindingIdentity) {
        self.model = model; self.identity = identity
    }
}

@MainActor
internal final class CapabilityGuestUIPresentationBinding: Sendable, CapabilityPresentationRetirement {
    let presentation: GuestUIPresentation
    nonisolated private let gate: CapabilityPresentationBindingGate
    private init(obligation: CapabilityPresentationObligation) {
        gate = CapabilityPresentationBindingGate(obligation: obligation)
        presentation = GuestUIPresentation()
    }
    nonisolated static func prepare(reservation: CapabilityAttemptReservation) async throws -> CapabilityPreparedPresentation {
        let obligation = try reservation.reservePresentation() // Before model allocation.
        do {
            let binding = await CapabilityGuestUIPresentationBinding(obligation: obligation)
            let initial = try binding.gate.initial(retirement: binding)
            let prepared = CapabilityPreparedPresentation(binding: binding, reservation: reservation, installation: initial)
            do { try Task.checkCancellation(); return prepared }
            catch { _ = await prepared.cleanupAfterFailure(); throw error }
        } catch {
            // If no guard was returned, no Task or model binding could exist.
            obligation.retire(); throw error
        }
    }
    nonisolated func acceptPrepared(_ initial: CapabilityPresentationInstallation) -> Bool { gate.accept(initial) }
    nonisolated func requestFinalClose(_ cause: CapabilityAttemptLocalStop) { gate.requestClose(cause) }
    nonisolated func takeFinalJoinPermit() -> CapabilityPresentationJoinPermit? { gate.takeCorePermit() }
    nonisolated func finishFinalClose(using permit: CapabilityPresentationJoinPermit?) async -> CapabilityPresentationJoinStatus {
        await gate.finish(using: permit)
    }
    nonisolated var finalStatus: CapabilityPresentationJoinStatus { gate.status }
    func retireEmptyPresentation() async -> Bool { presentation.retireKnownEmpty() }

    func bind(_ exchange: GuestUIExchangeV1) async throws -> CapabilityPresentationInstallation {
        let installation = try gate.beginBind(retirement: self)
        do {
            try presentation.requireBindable()
            let reader = try exchange.deliveryWake.takeConsumer()
            let identity = CapabilityGuestUIBindingIdentity()
            try presentation.bind(exchange, identity: identity)
            let box = CapabilityGuestUIWeakPresentation(presentation, identity: identity)
            let task = Task.detached { [reader, box] in
                while true {
                    do {
                        guard try await reader.next() else { break }
                        await GuestUIPresentation.consume(box)
                    } catch {
                        // Keep this sole existing reader for the bounded terminal hint.
                        await GuestUIPresentation.consumerFailed(box)
                    }
                }
                await GuestUIPresentation.finish(box)
            }
            // The local installation owns the permit until control accepts it.
            // Close can latch during @Published, but cannot take this authority.
            guard installation.lifetime?.attach(task, exchange: exchange) == true else {
                exchange.stop(.closed); await task.value
                gate.quarantine(); throw coldStartError("presentation_attach")
            }
            return installation
        } catch {
            exchange.stop(.closed)
            let result = await installation.finish()
            if !result.isRetired { gate.quarantine() }
            throw error
        }
    }
}
#else
/// Portable activation code can retain this type without importing Apple UI.
/// The bound native screen profile is unsupported on these platforms.
internal final class CapabilityGuestUIPresentationBinding: Sendable {
    private init() {}
    static func prepare(reservation: CapabilityAttemptReservation) async throws -> CapabilityPreparedPresentation {
        let obligation = try reservation.reservePresentation()
        // Stage 2 deliberately allocates no facade, endpoint, resource owner,
        // model or Task on Android. The unused obligation has an explicit end.
        obligation.retire()
        throw GuestUIProtocolFailureV1(phase: .presentation, code: .presentationInvariant)
    }
    func acceptPrepared(_ initial: CapabilityPresentationInstallation) -> Bool { false }
    func requestFinalClose(_ cause: CapabilityAttemptLocalStop) {}
    func takeFinalJoinPermit() -> CapabilityPresentationJoinPermit? { nil }
    func finishFinalClose(using permit: CapabilityPresentationJoinPermit?) async -> CapabilityPresentationJoinStatus { .invariant(.invalidState) }
    var finalStatus: CapabilityPresentationJoinStatus { .invariant(.invalidState) }
    func bind(_ exchange: GuestUIExchangeV1) async throws -> CapabilityPresentationInstallation {
        throw GuestUIProtocolFailureV1(phase: .presentation, code: .presentationInvariant)
    }
}
#endif
