#if canImport(SwiftUI) && canImport(MixerApple)
import Foundation
import XCTest
import MixerUI
import MixerApple
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

final class GuestUIReadyInputTests: XCTestCase, @unchecked Sendable {
    @MainActor private func withModel(_ body: (CapabilityGuestUIPresentationBinding, GuestUIExchangeV1) async throws -> Void) async throws {
        let reservation = try CapabilityAttemptReservation.acquire()
        let prepared = try await CapabilityGuestUIPresentationBinding.prepare(reservation: reservation)
        let control = CapabilityColdStartControl(reservation: reservation)
        try prepared.transfer(to: control)
        let binding = prepared.binding, exchange = try GuestUIExchangeV1(generation: 7)
        let installation = try await binding.bind(exchange)
        func finish() async {
            exchange.stop(.closed)
            let consumer = await installation.finish()
            XCTAssertTrue(consumer.isRetired)
            binding.requestFinalClose(.closed)
            let facade = await binding.finishFinalClose(using: binding.takeFinalJoinPermit())
            XCTAssertTrue(facade.isRetired)
            reservation.beginClosing()
            XCTAssertTrue(reservation.isReleased)
        }
        do {
            try startPresentationExchange(exchange)
            try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
            try await body(binding, exchange)
        } catch { await finish(); throw error }
        await finish()
    }
    @MainActor private func input(_ model: GuestUIPresentation) throws -> (CapabilityGuestUIAttachmentIdentity, MixerUIHost, RoutedUIAction) {
        let attachment = try XCTUnwrap(model.claimNativeAttachment()), host = try XCTUnwrap(model.renderHost)
        let identity = try XCTUnwrap(host.snapshot.identity(for: "save"))
        return (attachment, host, try host.route(UIEventEnvelope(revision: 1, identity: identity, event: .activate)))
    }
    @MainActor func testReadyCompletionRetainsExactlyOneIntentWithoutNewFrame() async throws {
        for invoke in [false, true] {
            try await withModel { binding, exchange in
                let model = binding.presentation, (attachment, host, action) = try input(binding.presentation)
                let callback = model.actionHandler(host: host, attachment: attachment)
                let ready = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
                XCTAssertTrue(model.inputEnabled)
                callback(action); callback(action)
                XCTAssertFalse(model.inputEnabled)
                XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 0)
                XCTAssertFalse(exchange.snapshot().eventOutstanding)
                if invoke { try exchange.finishTurn(ready, documentBytes: presentationDocument()) }
                else { try exchange.finishReadyWithoutInvocation(ready) }
                try await awaitPresentation { exchange.snapshot().counters.acceptedEvents == 1 }
                XCTAssertFalse(model.inputEnabled)
                XCTAssertEqual(exchange.snapshot().counters.producedFrames, 1)
                XCTAssertNil(exchange.snapshot().pendingPresentationReceipt)
                let event = try XCTUnwrap(try exchange.claimNextTurn(ready: false))
                guard case .event(sequence: 1, _) = event.kind else { return XCTFail("Deferred intent not delivered as one ordinary event") }
                try exchange.finishTurn(event, documentBytes: presentationDocument())
                try await awaitPresentation { model.lastEventResult?.outcome == .delivered && model.inputEnabled }
                XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 1)
                XCTAssertEqual(exchange.snapshot().counters.deliveredEvents, 1)
                XCTAssertEqual(exchange.snapshot().counters.producedFrames, 1)
                XCTAssertNil(exchange.snapshot().pendingPresentationReceipt)
                XCTAssertThrowsError(try exchange.finishReadyWithoutInvocation(ready))
                let duplicateReady = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
                try exchange.finishReadyWithoutInvocation(duplicateReady)
                await Task.yield()
                XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 1)
            }
        }
    }
    @MainActor func testNewRevisionCancelsPendingAndRejectsLateCallback() async throws {
        try await withModel { binding, exchange in
            let model = binding.presentation, (attachment, host, action) = try input(binding.presentation)
            let callback = model.actionHandler(host: host, attachment: attachment)
            let ready = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
            callback(action)
            try exchange.finishTurn(ready, documentBytes: presentationDocument(2))
            try await awaitPresentation { model.state == .displaying(revision: 2) && model.inputEnabled }
            let nextAction = try host.route(UIEventEnvelope(revision: 2, identity: XCTUnwrap(host.snapshot.identity(for: "save")), event: .activate))
            callback(action); callback(nextAction)
            XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 0)
            XCTAssertEqual(exchange.snapshot().counters.producedFrames, 2)
            XCTAssertNil(exchange.snapshot().pendingPresentationReceipt)
        }
    }
    @MainActor func testDetachAndForeignAttachmentCancelAuthority() async throws {
        try await withModel { binding, exchange in
            let model = binding.presentation, (attachment, host, action) = try input(binding.presentation)
            let old = model.actionHandler(host: host, attachment: attachment)
            let foreignHost = try MixerUIHost(document: GuestUICodec().decode(presentationDocument()).document)
            let foreign = model.actionHandler(host: foreignHost, attachment: attachment)
            let ready = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
            foreign(action)
            old(action)
            model.detachNativeAttachment(attachment)
            let next = try XCTUnwrap(model.claimNativeAttachment())
            old(action)
            try exchange.finishReadyWithoutInvocation(ready)
            try await awaitPresentation { model.inputEnabled }
            XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 0)
            model.actionHandler(host: host, attachment: next)(action)
            XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 1)
        }
    }
    @MainActor func testStopCloseAndTerminalFailureDiscardPendingAndFinishObserver() async throws {
        for cause in 0...2 {
            try await withModel { binding, exchange in
                let model = binding.presentation, (attachment, host, action) = try input(binding.presentation)
                let callback = model.actionHandler(host: host, attachment: attachment)
                let ready = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
                callback(action)
                if cause == 0 { exchange.stop(.closed) }
                else if cause == 1 { exchange.stop(.cancelled) }
                else { exchange.recordProtocolFailure(.init(phase: .presentation, code: .presentationInvariant)) }
                try await awaitPresentation { model.state == .stopped }
                callback(action)
                XCTAssertThrowsError(try exchange.finishReadyWithoutInvocation(ready))
                XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 0)
                XCTAssertFalse(model.inputEnabled)
            }
        }
    }
    @MainActor func testOutstandingEventCancelsPendingRatherThanReplayingAcceptedInput() async throws {
        try await withModel { binding, exchange in
            let model = binding.presentation, (attachment, host, action) = try input(binding.presentation)
            let callback = model.actionHandler(host: host, attachment: attachment)
            let ready = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
            callback(action)
            try exchange.finishReadyWithoutInvocation(ready)
            let envelope = UIEventEnvelope(revision: 1, identity: try XCTUnwrap(host.snapshot.identity(for: "save")), event: .activate)
            XCTAssertEqual(exchange.offer(envelope, generation: 7), .accepted(sequence: 1))
            callback(action)
            let event = try XCTUnwrap(try exchange.claimNextTurn(ready: false))
            try exchange.finishTurn(event, documentBytes: presentationDocument())
            try await awaitPresentation { model.inputEnabled && model.lastEventResult?.outcome == .delivered }
            let extra = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
            try exchange.finishReadyWithoutInvocation(extra)
            await Task.yield()
            XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 1)
            XCTAssertEqual(exchange.snapshot().counters.deliveredEvents, 1)
        }
    }
    @MainActor func testOwnerGenerationChangeRejectsCapturedInput() async throws {
        let reservation = try CapabilityAttemptReservation.acquire()
        let prepared = try await CapabilityGuestUIPresentationBinding.prepare(reservation: reservation)
        try prepared.transfer(to: CapabilityColdStartControl(reservation: reservation))
        let binding = prepared.binding
        let old = try GuestUIExchangeV1(generation: 7), first = try await binding.bind(old)
        try startPresentationExchange(old)
        try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
        let (attachment, host, action) = try input(binding.presentation)
        let callback = binding.presentation.actionHandler(host: host, attachment: attachment)
        _ = try XCTUnwrap(try old.claimNextTurn(ready: true)); callback(action)
        old.stop(.closed)
        let firstStatus = await first.finish(); XCTAssertTrue(firstStatus.isRetired)
        let next = try GuestUIExchangeV1(generation: 8), second = try await binding.bind(next)
        try startPresentationExchange(next)
        try await awaitPresentation { binding.presentation.state == .displaying(revision: 1) }
        callback(action)
        XCTAssertEqual(next.snapshot().counters.acceptedEvents, 0)
        XCTAssertEqual(old.snapshot().counters.acceptedEvents, 0)
        next.stop(.closed)
        let secondStatus = await second.finish(); XCTAssertTrue(secondStatus.isRetired)
        binding.requestFinalClose(.closed)
        let final = await binding.finishFinalClose(using: binding.takeFinalJoinPermit()); XCTAssertTrue(final.isRetired)
        reservation.beginClosing(); XCTAssertTrue(reservation.isReleased)
    }
    @MainActor func testSDKReadyBusyClassificationAndObserverDoNotPublishLegacyFrames() async throws {
        let exchange = try GuestUIExchangeV1(generation: 7)
        let readiness = try exchange.takeNativeInputReadinessConsumer()
        XCTAssertThrowsError(try exchange.takeNativeInputReadinessConsumer())
        try startPresentationExchange(exchange)
        let claim = try XCTUnwrap(exchange.claimPresentation(generation: 7))
        let host = try MixerUIHost(document: XCTUnwrap(claim.frame).document.document)
        _ = try XCTUnwrap(exchange.completePresentation(claim, snapshot: host.snapshot))
        let node = try XCTUnwrap(host.snapshot.identity(for: "save"))
        let envelope = UIEventEnvelope(revision: 1, identity: node, event: .activate)
        for invoke in [false, true] {
            let ready = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
            XCTAssertEqual(exchange.offer(envelope, generation: 7), .busy)
            XCTAssertEqual(exchange.offerNativeInput(envelope, generation: 7), .readyBusy)
            XCTAssertEqual(exchange.offerNativeInput(envelope, generation: 8), .offered(.stale))
            XCTAssertEqual(exchange.offerNativeInput(UIEventEnvelope(revision: 2, identity: node, event: .activate), generation: 7), .offered(.stale))
            XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 0)
            if invoke { try exchange.finishTurn(ready, documentBytes: presentationDocument()) }
            else { try exchange.finishReadyWithoutInvocation(ready) }
            let signalled = try await readiness.next(); XCTAssertTrue(signalled)
            XCTAssertNil(exchange.claimPresentation(generation: 7))
            XCTAssertEqual(exchange.snapshot().counters.producedFrames, 1)
            XCTAssertNil(exchange.snapshot().pendingPresentationReceipt)
        }
        readiness.cancel()
        let finished = try await readiness.next(); XCTAssertFalse(finished)
        exchange.stop(.closed)
    }
    func testOwnerRetirementUsesCurrentOwnerAcrossMovingAndStablePoolCounts() throws {
        let initial = CapabilityAttemptReservation.occupiedSlots
        let prior = try CapabilityAttemptReservation.acquire(), priorHold = try prior.reservePresentation()
        let priorControl = CapabilityColdStartControl(reservation: prior)
        priorControl.requestClose(.closed); prior.beginClosing()
        let baseline = CapabilityAttemptReservation.occupiedSlots
        let current = try CapabilityAttemptReservation.acquire(), currentHold = try current.reservePresentation()
        let currentControl = CapabilityColdStartControl(reservation: current)
        currentControl.requestClose(.closed); current.beginClosing()
        defer { priorHold.retire(); currentHold.retire() }
        priorHold.retire()
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, baseline)
        XCTAssertFalse(currentControl.ownerRetired)
        XCTAssertFalse(current.isReleased); XCTAssertTrue(currentControl.snapshot.cleanupPending)
        currentHold.retire()
        XCTAssertNotEqual(CapabilityAttemptReservation.occupiedSlots, baseline)
        XCTAssertTrue(currentControl.ownerRetired)
        XCTAssertTrue(current.isReleased); XCTAssertFalse(currentControl.snapshot.cleanupPending)
        let stable = try CapabilityAttemptReservation.acquire(), stableHold = try stable.reservePresentation()
        stable.beginClosing()
        let stableBaseline = CapabilityAttemptReservation.occupiedSlots
        let next = try CapabilityAttemptReservation.acquire(), nextHold = try next.reservePresentation()
        let nextControl = CapabilityColdStartControl(reservation: next)
        nextControl.requestClose(.closed); next.beginClosing(); nextHold.retire()
        XCTAssertTrue(nextControl.ownerRetired)
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, stableBaseline)
        XCTAssertFalse(stable.isReleased)
        stableHold.retire()
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, initial)
    }
    @MainActor func testForeignHostAfterPendingInvalidatesWithoutAdmission() async throws {
        for releaseHost in [false, true] {
            try await withModel { binding, exchange in
                let model = binding.presentation, (attachment, host, action) = try input(binding.presentation)
                var foreignHost: MixerUIHost? = try MixerUIHost(document: GuestUICodec().decode(presentationDocument()).document)
                let current = model.actionHandler(host: host, attachment: attachment)
                let foreign = model.actionHandler(host: try XCTUnwrap(foreignHost), attachment: attachment)
                if releaseHost { foreignHost = nil }
                let ready = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
                current(action); foreign(action)
                XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 0)
                try exchange.finishReadyWithoutInvocation(ready)
                try await awaitPresentation { model.inputEnabled }
                XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 0)
                XCTAssertFalse(exchange.snapshot().eventOutstanding)
                XCTAssertEqual(exchange.snapshot().counters.producedFrames, 1)
                XCTAssertNil(exchange.snapshot().pendingPresentationReceipt)
                current(action)
                XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 1)
                let event = try XCTUnwrap(try exchange.claimNextTurn(ready: false))
                try exchange.finishTurn(event, documentBytes: presentationDocument())
                try await awaitPresentation { model.lastEventResult?.outcome == .delivered && model.inputEnabled }
                withExtendedLifetime(foreignHost) {}
            }
        }
    }
    @MainActor func testCurrentValidDuplicatePreservesFirstPendingIntent() async throws {
        try await withModel { binding, exchange in
            let model = binding.presentation, (attachment, host, action) = try input(binding.presentation)
            let callback = model.actionHandler(host: host, attachment: attachment)
            let ready = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
            callback(action)
            for _ in 0..<4 { callback(action) }
            XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 0)
            XCTAssertFalse(model.inputEnabled)
            try exchange.finishReadyWithoutInvocation(ready)
            try await awaitPresentation { exchange.snapshot().counters.acceptedEvents == 1 }
            let event = try XCTUnwrap(try exchange.claimNextTurn(ready: false))
            guard case .event(sequence: 1, let bytes) = event.kind else { return XCTFail("First retained intent was not delivered") }
            let delivered = try GuestUIEventCodecV1.decode(bytes)
            XCTAssertEqual(delivered.nodeID, "save"); XCTAssertEqual(delivered.actionID, "sample.save")
            try exchange.finishTurn(event, documentBytes: presentationDocument())
            try await awaitPresentation { model.lastEventResult?.outcome == .delivered && model.inputEnabled }
            let later = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
            try exchange.finishReadyWithoutInvocation(later)
            await Task.yield()
            XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 1)
            XCTAssertEqual(exchange.snapshot().counters.deliveredEvents, 1)
            XCTAssertEqual(exchange.snapshot().counters.producedFrames, 1)
            XCTAssertNil(exchange.snapshot().pendingPresentationReceipt)
        }
    }
    @MainActor func testForeignAndRetiredAttachmentInvalidateCurrentPendingIntent() async throws {
        for retireAttachment in [false, true] {
            try await withModel { binding, exchange in
                let model = binding.presentation, (attachment, host, action) = try input(binding.presentation)
                let foreignIdentity = retireAttachment ? attachment : CapabilityGuestUIAttachmentIdentity()
                let foreign = model.actionHandler(host: host, attachment: foreignIdentity)
                var currentIdentity = attachment
                if retireAttachment {
                    model.detachNativeAttachment(attachment)
                    currentIdentity = try XCTUnwrap(model.claimNativeAttachment())
                }
                let current = model.actionHandler(host: host, attachment: currentIdentity)
                let ready = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
                current(action); foreign(action)
                try exchange.finishReadyWithoutInvocation(ready)
                try await awaitPresentation { model.inputEnabled }
                XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 0)
                XCTAssertFalse(exchange.snapshot().eventOutstanding)
                XCTAssertEqual(exchange.snapshot().counters.producedFrames, 1)
                XCTAssertNil(exchange.snapshot().pendingPresentationReceipt)
            }
        }
    }
    @MainActor func testInvalidCurrentRouteInvalidatesPendingBeforeDuplicateGate() async throws {
        for field in ["nodeID", "actionID", "revision"] {
            try await withModel { binding, exchange in
                let model = binding.presentation, (attachment, host, action) = try input(binding.presentation)
                var fields = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(action)) as? [String: Any])
                if field == "revision" { fields[field] = 2 }
                else { fields[field] = "foreign" }
                let invalid = try JSONDecoder().decode(RoutedUIAction.self, from: JSONSerialization.data(withJSONObject: fields))
                let callback = model.actionHandler(host: host, attachment: attachment)
                let ready = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
                callback(action); callback(invalid)
                try exchange.finishReadyWithoutInvocation(ready)
                try await awaitPresentation { model.inputEnabled }
                XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 0)
                XCTAssertFalse(exchange.snapshot().eventOutstanding)
                XCTAssertEqual(exchange.snapshot().counters.producedFrames, 1)
                XCTAssertNil(exchange.snapshot().pendingPresentationReceipt)
            }
        }
    }
    @MainActor func testStaleFrameCallbackInvalidatesNewRevisionPendingIntent() async throws {
        try await withModel { binding, exchange in
            let model = binding.presentation, (attachment, host, action) = try input(binding.presentation)
            let stale = model.actionHandler(host: host, attachment: attachment)
            let first = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
            try exchange.finishTurn(first, documentBytes: presentationDocument(2))
            try await awaitPresentation { model.state == .displaying(revision: 2) && model.inputEnabled }
            let next = try host.route(UIEventEnvelope(revision: 2, identity: XCTUnwrap(host.snapshot.identity(for: "save")), event: .activate))
            let current = model.actionHandler(host: host, attachment: attachment)
            let ready = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
            current(next); stale(action)
            try exchange.finishReadyWithoutInvocation(ready)
            try await awaitPresentation { model.inputEnabled }
            XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 0)
            XCTAssertEqual(exchange.snapshot().counters.producedFrames, 2)
            XCTAssertFalse(exchange.snapshot().eventOutstanding)
            XCTAssertNil(exchange.snapshot().pendingPresentationReceipt)
        }
    }
    @MainActor func testStaleOwnerCallbackInvalidatesNewOwnerPendingWithSameNumbers() async throws {
        let reservation = try CapabilityAttemptReservation.acquire()
        let prepared = try await CapabilityGuestUIPresentationBinding.prepare(reservation: reservation)
        try prepared.transfer(to: CapabilityColdStartControl(reservation: reservation))
        let binding = prepared.binding, model = binding.presentation
        var exchange = try GuestUIExchangeV1(generation: 7)
        var installation = try await binding.bind(exchange)
        func cleanup() async {
            exchange.stop(.closed)
            let joined = await installation.finish(); XCTAssertTrue(joined.isRetired)
            binding.requestFinalClose(.closed)
            let final = await binding.finishFinalClose(using: binding.takeFinalJoinPermit()); XCTAssertTrue(final.isRetired)
            reservation.beginClosing(); XCTAssertTrue(reservation.isReleased)
        }
        do {
            try startPresentationExchange(exchange)
            try await awaitPresentation { model.state == .displaying(revision: 1) }
            let (attachment, oldHost, action) = try input(model)
            let stale = model.actionHandler(host: oldHost, attachment: attachment)
            let old = exchange
            old.stop(.closed)
            let joined = await installation.finish(); XCTAssertTrue(joined.isRetired)
            exchange = try GuestUIExchangeV1(generation: 7)
            installation = try await binding.bind(exchange)
            try startPresentationExchange(exchange)
            try await awaitPresentation { model.state == .displaying(revision: 1) }
            let host = try XCTUnwrap(model.renderHost)
            XCTAssertFalse(host === oldHost)
            let currentAction = try host.route(UIEventEnvelope(revision: 1, identity: XCTUnwrap(host.snapshot.identity(for: "save")), event: .activate))
            let current = model.actionHandler(host: host, attachment: attachment)
            let ready = try XCTUnwrap(try exchange.claimNextTurn(ready: true))
            current(currentAction); stale(action)
            try exchange.finishReadyWithoutInvocation(ready)
            try await awaitPresentation { model.inputEnabled }
            XCTAssertEqual(old.snapshot().counters.acceptedEvents, 0)
            XCTAssertEqual(exchange.snapshot().counters.acceptedEvents, 0)
            XCTAssertFalse(exchange.snapshot().eventOutstanding)
            XCTAssertEqual(exchange.snapshot().counters.producedFrames, 1)
            XCTAssertNil(exchange.snapshot().pendingPresentationReceipt)
        } catch { await cleanup(); throw error }
        await cleanup()
    }

}
#endif
