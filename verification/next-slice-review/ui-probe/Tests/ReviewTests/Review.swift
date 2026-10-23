import Combine
import Foundation
import Testing
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

@Suite(.serialized) @MainActor struct Review {
    @Test func prebindingDuplicateCannotBeErasedByDetach() async throws {
        let owner = CapabilityGuestUIPresentationBinding()
        let model = owner.presentation
        var publications = 0
        let observation = model.objectWillChange.sink { publications += 1 }
        let first = try #require(model.claimNativeAttachment())
        #expect(model.claimNativeAttachment() == nil)
        model.detachNativeAttachment(first)
        let replacement = try #require(model.claimNativeAttachment())
        model.detachNativeAttachment(first)
        #expect(publications == 0)
        #expect(!model.inputEnabled)
        let exchange = try GuestUIExchangeV1(generation: 23)
        let task = try await owner.bind(exchange)
        #expect(exchange.snapshot().firstUIProtocolFailure?.failure.code == .presentationInvariant)
        #expect(model.state == .stopped)
        await task.value
        #expect(!model.inputEnabled)
        model.detachNativeAttachment(replacement)
        withExtendedLifetime(observation) {}
    }
    @Test func terminalStopIsVisibleBeforeConsumerRetiresAndStaleDetachIsIgnored() async throws {
        let owner = CapabilityGuestUIPresentationBinding()
        let model = owner.presentation
        let exchange = try GuestUIExchangeV1(generation: 24)
        let task = try await owner.bind(exchange)
        let turn = try exchange.claimStartup()
        let document = Data(#"{"schemaVersion":1,"revision":1,"root":{"id":"root","kind":"text","properties":{"text":"Ready"},"actions":[],"children":[]}}"#.utf8)
        try exchange.finishTurn(turn, documentBytes: document)
        try exchange.enterEffectsIntent(generation: 24)
        try exchange.confirmEffectsEnabled(generation: 24)
        let deadline = ContinuousClock.now + .seconds(5)
        while model.state != .displaying(revision: 1), ContinuousClock.now < deadline { try await Task.sleep(for: .milliseconds(2)) }
        #expect(model.state == .displaying(revision: 1))
        let first = try #require(model.claimNativeAttachment())
        #expect(model.inputEnabled)
        model.detachNativeAttachment(first)
        let next = try #require(model.claimNativeAttachment())
        model.detachNativeAttachment(first)
        #expect(model.inputEnabled)
        let ticket = try #require(model.nativeDisplayTicket(attachment: next))
        exchange.stop(.closed)
        #expect(!model.inputEnabled)
        #expect(!model.isCurrentNativeDisplay(ticket))
        #expect(!model.observeNativeDisplay(ticket))
        await task.value
        #expect(model.state == .stopped)
        model.detachNativeAttachment(next)
    }
}
