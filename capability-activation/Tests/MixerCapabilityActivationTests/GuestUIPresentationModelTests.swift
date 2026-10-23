#if canImport(SwiftUI) && canImport(MixerApple)
import Foundation
import Combine
import Testing
import MixerUI
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

// Original, literal UI protocol fixture. It is not serialized by the runtime.
internal func presentationDocument(_ revision: UInt64 = 1, text: String = "Ready") -> Data {
    Data("{\"schemaVersion\":1,\"revision\":\(revision),\"root\":{\"id\":\"root\",\"kind\":\"vStack\",\"properties\":{},\"actions\":[],\"children\":[{\"id\":\"status\",\"kind\":\"text\",\"properties\":{\"text\":\"\(text)\"},\"children\":[],\"actions\":[]},{\"id\":\"save\",\"kind\":\"button\",\"properties\":{\"label\":\"Save sample\"},\"children\":[],\"actions\":[{\"id\":\"sample.save\",\"event\":\"activate\"}]}]}}".utf8)
}

internal func startPresentationExchange(_ exchange: GuestUIExchangeV1, confirm: Bool = true) throws {
    let startup = try exchange.claimStartup()
    try exchange.finishTurn(startup, documentBytes: presentationDocument())
    if confirm {
        try exchange.enterEffectsIntent(generation: exchange.snapshot().generation)
        try exchange.confirmEffectsEnabled(generation: exchange.snapshot().generation)
    }
}

@MainActor
internal func awaitPresentation(_ condition: @MainActor () -> Bool) async throws {
    let deadline = ContinuousClock.now + .seconds(5)
    while !condition(), ContinuousClock.now < deadline { try await Task.sleep(for: .milliseconds(2)) }
    try #require(condition(), "presentation state failed to settle within five seconds")
}

@MainActor
private final class PresentationWeakReferences {
    weak var model: GuestUIPresentation?
    weak var exchange: GuestUIExchangeV1?
    init(model: GuestUIPresentation?, exchange: GuestUIExchangeV1?) {
        self.model = model; self.exchange = exchange
    }
}

@Suite(.serialized)
@MainActor
struct GuestUIPresentationModelTests {
    @Test func confirmationControlsPresentationAndNoHostUpdateEarnsReceipt() async throws {
        let binding = CapabilityGuestUIPresentationBinding()
        let exchange = try GuestUIExchangeV1(generation: 41)
        let consumer = try await binding.bind(exchange)
        try startPresentationExchange(exchange, confirm: false)
        try await Task.sleep(for: .milliseconds(10))
        #expect(binding.presentation.state == .waiting)
        #expect(binding.presentation.renderHost == nil)
        try exchange.enterEffectsIntent(generation: 41)
        try exchange.confirmEffectsEnabled(generation: 41)
        try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
        #expect(binding.presentation.renderHost?.snapshot.document.revision == 1)
        #expect(exchange.snapshot().pendingPresentationReceipt == nil)
        #expect(!binding.presentation.inputEnabled) // No native attachment.
        exchange.stop(.closed); await consumer.value
        #expect(binding.presentation.state == .stopped)
        #expect(binding.presentation.renderHost == nil)
    }

    @Test func synchronousActionUsesSoleSlotAndResultWithoutNewFrameReenablesInput() async throws {
        let binding = CapabilityGuestUIPresentationBinding()
        let exchange = try GuestUIExchangeV1(generation: 7)
        let consumer = try await binding.bind(exchange)
        try startPresentationExchange(exchange)
        try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
        let attachment = try #require(binding.presentation.claimNativeAttachment())
        let host = try #require(binding.presentation.renderHost)
        let identity = try #require(host.snapshot.identity(for: "save"))
        let action = try host.route(UIEventEnvelope(revision: 1, identity: identity, event: .activate))
        let callback = binding.presentation.actionHandler(host: host, attachment: attachment)
        #expect(binding.presentation.inputEnabled)
        callback(action)
        #expect(!binding.presentation.inputEnabled)
        callback(action)
        #expect(exchange.snapshot().counters.acceptedEvents == 1)
        let turn = try #require(try exchange.claimNextTurn(ready: true))
        guard case .event(sequence: 1, _) = turn.kind else { Issue.record("ready wake overtook accepted input"); return }
        try exchange.finishTurn(turn, documentBytes: presentationDocument())
        try await awaitPresentation { binding.presentation.lastEventResult?.outcome == .delivered }
        #expect(binding.presentation.inputEnabled)
        #expect(exchange.snapshot().counters.producedFrames == 1)
        #expect(!exchange.snapshot().eventOutstanding)
        binding.presentation.detachNativeAttachment(attachment)
        callback(action)
        #expect(exchange.snapshot().counters.acceptedEvents == 1)
        exchange.stop(.closed); await consumer.value
    }

    @Test func freshBindingResetsHostAndRejectsCallbacksWithIdenticalNumericIdentity() async throws {
        let binding = CapabilityGuestUIPresentationBinding()
        let old = try GuestUIExchangeV1(generation: 1)
        let first = try await binding.bind(old)
        try startPresentationExchange(old)
        try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
        let attachment = try #require(binding.presentation.claimNativeAttachment())
        let oldHost = try #require(binding.presentation.renderHost)
        let oldTicket = try #require(binding.presentation.nativeDisplayTicket(attachment: attachment))
        let oldIdentity = try #require(oldHost.snapshot.identity(for: "save"))
        let oldAction = try oldHost.route(UIEventEnvelope(revision: 1, identity: oldIdentity, event: .activate))
        let oldCallback = binding.presentation.actionHandler(host: oldHost, attachment: attachment)
        old.stop(.closed); await first.value
        let next = try GuestUIExchangeV1(generation: 1)
        let second = try await binding.bind(next)
        try startPresentationExchange(next)
        try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
        let newHost = try #require(binding.presentation.renderHost)
        #expect(newHost !== oldHost)
        #expect(newHost.snapshot.identity(for: "save") == oldIdentity)
        #expect(!binding.presentation.isCurrentNativeDisplay(oldTicket))
        oldCallback(oldAction)
        #expect(next.snapshot().counters.acceptedEvents == 0)
        let newAction = try newHost.route(UIEventEnvelope(revision: 1, identity: oldIdentity, event: .activate))
        binding.presentation.actionHandler(host: newHost, attachment: attachment)(newAction)
        #expect(next.snapshot().counters.acceptedEvents == 1)
        next.stop(.closed); await second.value
    }

    @Test func closeBeforeApplyAndCloseDuringPublishedApplyRetireBeforeConsumerReturns() async throws {
        do {
            let binding = CapabilityGuestUIPresentationBinding()
            let exchange = try GuestUIExchangeV1(generation: 1)
            let consumer = try await binding.bind(exchange)
            try startPresentationExchange(exchange)
            exchange.stop(.closed)
            await consumer.value
            #expect(binding.presentation.state == .stopped)
            #expect(binding.presentation.renderHost == nil)
            #expect(exchange.snapshot().displayedRevision == nil)
        }
        do {
            let binding = CapabilityGuestUIPresentationBinding()
            let exchange = try GuestUIExchangeV1(generation: 2)
            let consumer = try await binding.bind(exchange)
            var stoppedAtPublish = false
            let subscription = binding.presentation.objectWillChange.sink {
                if !stoppedAtPublish { stoppedAtPublish = true; exchange.stop(.closed) }
            }
            try startPresentationExchange(exchange)
            await consumer.value
            withExtendedLifetime(subscription) {}
            #expect(stoppedAtPublish)
            #expect(binding.presentation.state == .stopped)
            #expect(binding.presentation.renderHost == nil)
            #expect(exchange.snapshot().pendingPresentationReceipt == nil)
        }
    }

    @Test func rebindingRequiresPreviousRetirementWithoutStealingNextReader() async throws {
        let binding = CapabilityGuestUIPresentationBinding()
        let old = try GuestUIExchangeV1(generation: 1)
        let first = try await binding.bind(old)
        let next = try GuestUIExchangeV1(generation: 2)
        await #expect(throws: GuestUIControlRejectionV1.busy) { try await binding.bind(next) }
        old.stop(.closed); await first.value
        let second = try await binding.bind(next)
        next.stop(.closed); await second.value
        #expect(binding.presentation.state == .stopped)
    }

    @Test func parkedConsumerRetainsNeitherModelNorExchange() async throws {
        var binding: CapabilityGuestUIPresentationBinding? = CapabilityGuestUIPresentationBinding()
        var exchange: GuestUIExchangeV1? = try GuestUIExchangeV1(generation: 1)
        let weakReferences = PresentationWeakReferences(model: binding?.presentation, exchange: exchange)
        let wake = try #require(exchange?.deliveryWake)
        let consumer = try await #require(binding).bind(try #require(exchange))
        binding = nil; exchange = nil
        #expect(weakReferences.model == nil)
        #expect(weakReferences.exchange == nil)
        wake.signal(); wake.finish()
        await consumer.value
    }

    @Test func duplicateAttachmentFailsTypedAndStopInvalidatesCapturedTicket() async throws {
        let binding = CapabilityGuestUIPresentationBinding()
        let exchange = try GuestUIExchangeV1(generation: 1)
        let consumer = try await binding.bind(exchange)
        try startPresentationExchange(exchange)
        try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
        let attachment = try #require(binding.presentation.claimNativeAttachment())
        let ticket = try #require(binding.presentation.nativeDisplayTicket(attachment: attachment))
        #expect(binding.presentation.claimNativeAttachment() == nil)
        #expect(exchange.snapshot().firstUIProtocolFailure?.failure ==
                GuestUIProtocolFailureV1(phase: .presentation, code: .presentationInvariant))
        #expect(!binding.presentation.isCurrentNativeDisplay(ticket))
        #expect(exchange.snapshot().pendingPresentationReceipt == nil)
        await consumer.value
        #expect(binding.presentation.state == .stopped)
    }

    @Test func duplicateAttachmentBeforeBindingBecomesTypedFailureOnFreshExchange() async throws {
        let binding = CapabilityGuestUIPresentationBinding()
        let attachment = try #require(binding.presentation.claimNativeAttachment())
        #expect(binding.presentation.claimNativeAttachment() == nil)
        #expect(binding.presentation.state == .stopped)
        let exchange = try GuestUIExchangeV1(generation: 1)
        let consumer = try await binding.bind(exchange)
        #expect(exchange.snapshot().firstUIProtocolFailure?.failure ==
                GuestUIProtocolFailureV1(phase: .presentation, code: .presentationInvariant))
        #expect(exchange.snapshot().firstUIProtocolFailure?.effectStage == .beforeIntent)
        #expect(!exchange.snapshot().hasStarted)
        await consumer.value
        #expect(binding.presentation.renderHost == nil)
        // The rejected second attachment is not an attachment queue, and the
        // one failure does not poison a subsequently authorized fallback bind.
        let next = try GuestUIExchangeV1(generation: 2)
        let second = try await binding.bind(next)
        try startPresentationExchange(next)
        try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
        #expect(next.snapshot().firstUIProtocolFailure == nil)
        binding.presentation.detachNativeAttachment(attachment)
        next.stop(.closed); await second.value
    }

    @Test func revisionChangeInvalidatesUnobservedNativeTicket() async throws {
        let binding = CapabilityGuestUIPresentationBinding()
        let exchange = try GuestUIExchangeV1(generation: 1)
        let consumer = try await binding.bind(exchange)
        try startPresentationExchange(exchange)
        try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
        let attachment = try #require(binding.presentation.claimNativeAttachment())
        let oldTicket = try #require(binding.presentation.nativeDisplayTicket(attachment: attachment))
        let turn = try #require(try exchange.claimNextTurn(ready: true))
        try exchange.finishTurn(turn, documentBytes: presentationDocument(2, text: "Saved"))
        #expect(!binding.presentation.inputEnabled || exchange.snapshot().displayedRevision != exchange.snapshot().latestRevision)
        try await awaitPresentation { binding.presentation.state == .displaying(revision: 2) }
        #expect(!binding.presentation.isCurrentNativeDisplay(oldTicket))
        #expect(binding.presentation.nativeDisplayTicket(attachment: attachment)?.ticket.revision == 2)
        #expect(exchange.snapshot().pendingPresentationReceipt == nil)
        exchange.stop(.closed); await consumer.value
    }

    @Test func terminalEventSurvivesCloseAfterUncompletedPresentationClaim() async throws {
        for eventStage in 0...2 {
            let binding = CapabilityGuestUIPresentationBinding()
            let exchange = try GuestUIExchangeV1(generation: UInt64(eventStage + 1))
            let consumer = try await binding.bind(exchange)
            try startPresentationExchange(exchange)
            try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
            let attachment = try #require(binding.presentation.claimNativeAttachment())
            let host = try #require(binding.presentation.renderHost)
            let identity = try #require(host.snapshot.identity(for: "save"))
            let action = try host.route(UIEventEnvelope(revision: 1, identity: identity, event: .activate))
            binding.presentation.actionHandler(host: host, attachment: attachment)(action)
            if eventStage > 0 {
                let turn = try #require(try exchange.claimNextTurn(ready: false))
                if eventStage == 2 { try exchange.finishTurn(turn, documentBytes: presentationDocument()) }
            }
            // Hold an ordinary presentation claim while close changes a queued,
            // running or delivered event into its final terminal diagnostic.
            let partial = try #require(exchange.claimPresentation(generation: UInt64(eventStage + 1)))
            #expect(partial.eventResult?.outcome == (eventStage == 2 ? .delivered : nil))
            exchange.stop(.closed)
            _ = exchange.completePresentation(partial, snapshot: nil)
            await consumer.value
            #expect(binding.presentation.state == .stopped)
            #expect(binding.presentation.lastEventResult?.sequence == 1)
            #expect(binding.presentation.lastEventResult?.outcome == .terminal(turnBegan: eventStage > 0))
            #expect(exchange.snapshot().counters.terminalEvents == 1)
            #expect(!exchange.snapshot().eventOutstanding)
        }
    }

    @Test func reconciliationFailureRetiresViewAndPreservesUnseenTerminalEvent() async throws {
        let binding = CapabilityGuestUIPresentationBinding()
        let exchange = try GuestUIExchangeV1(generation: 1)
        let consumer = try await binding.bind(exchange)
        try startPresentationExchange(exchange)
        try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
        let attachment = try #require(binding.presentation.claimNativeAttachment())
        let host = try #require(binding.presentation.renderHost)
        let identity = try #require(host.snapshot.identity(for: "save"))
        let action = try host.route(UIEventEnvelope(revision: 1, identity: identity, event: .activate))
        binding.presentation.actionHandler(host: host, attachment: attachment)(action)
        let turn = try #require(try exchange.claimNextTurn(ready: false))
        let next = presentationDocument(2, text: "Saving")
        try exchange.finishTurn(turn, documentBytes: next)
        // Fault the test-owned private host using its existing reconciler API.
        // No production hook or native receipt is introduced. The actual fixed
        // consumer's next update now throws revisionNotIncreasing.
        try host.update(GuestUICodec().decode(next).document)
        await consumer.value
        #expect(binding.presentation.state == .stopped)
        #expect(binding.presentation.renderHost == nil)
        #expect(!binding.presentation.inputEnabled)
        #expect(exchange.snapshot().firstUIProtocolFailure?.failure ==
                GuestUIProtocolFailureV1(phase: .presentation, code: .presentationInvariant))
        #expect(binding.presentation.lastEventResult?.sequence == 1)
        #expect(binding.presentation.lastEventResult?.outcome == .terminal(turnBegan: true))
        #expect(!exchange.snapshot().eventOutstanding)
    }
}
#endif
