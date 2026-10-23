import Foundation
import Dispatch
import Testing
import MixerCapabilities
import MixerUI
@_spi(GuestUIV1) import MixerGuest
@_spi(GuestUIV1) @_spi(CapabilityLifecycle) @testable import MixerExperimentalCapabilityRuntime

private struct GuestUIHarness {
    let directory: URL
    let store: AppPrivateKeyValueStore
    let observer: LifecycleRecorder
    let group: OwnedCapabilityAdapterGroup
    let exchange: GuestUIExchangeV1
    let session: ExperimentalCapabilitySession
    static func make(_ mode: GuestUIProgram.Mode = .normal, revision: UInt64 = 1, allow: Bool = true) async throws -> Self {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-guest-ui-" + UUID().uuidString)
        let store = try lifecycleStore(directory)
        let observer = LifecycleRecorder()
        let group = OwnedCapabilityAdapterGroup(storage: store, terminal: observer, retirement: observer)
        let exchange = try GuestUIExchangeV1(generation: 1)
        let construction = try ExperimentalCapabilitySession.prepareOwnedGuestUIV1(module: GuestUIProgram.build(mode, initialRevision: revision),
            configuration: .init(), policy: bridgePolicy(allow: allow), adapterGroup: group, exchange: exchange)
        let session = try await construction.create()
        return Self(directory: directory, store: store, observer: observer, group: group, exchange: exchange, session: session)
    }
    func enable() async throws {
        try await session.startupGuestUIV1()
        try exchange.enterEffectsIntent(generation: 1)
        try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: DispatchTime.now().uptimeNanoseconds + 5_000_000_000)
        try exchange.confirmEffectsEnabled(generation: 1)
    }
    func present() throws -> UIEventEnvelope {
        let claim = try #require(exchange.claimPresentation(generation: 1))
        let frame = try #require(claim.frame)
        var reconciler = UIReconciler()
        _ = try reconciler.apply(frame.document.document)
        let snapshot = try reconciler.currentSnapshot()
        #expect(exchange.completePresentation(claim, snapshot: snapshot) != nil)
        let identity = try #require(snapshot.identity(for: "save"))
        return UIEventEnvelope(revision: frame.document.document.revision, identity: identity, event: .activate)
    }
    func accept(_ envelope: UIEventEnvelope) async throws {
        // A concurrent no-op ready claim can legitimately win the shared guard.
        // Retry only that local busy rejection; never replay an accepted event.
        try await bridgeEventually {
            let admission = exchange.offer(envelope, generation: 1)
            if admission == .busy { return false }
            #expect(admission == .accepted(sequence: 1))
            return true
        }
    }
    func cleanup() async throws {
        session.close()
        try await bridgeEventually { session.status.drained && observer.retired == 1 }
        #expect(group.core.cleanupJobCount == 1)
        try? FileManager.default.removeItem(at: directory)
    }
}

extension ExperimentalBridgeTests {
    @Test func guestUIValidatorUsesCheckedRequiredExportDomainAndSameCapacity() async throws {
        let valid = try ExperimentalCapabilityValidator.prepareGuestUIV1(module: GuestUIProgram.build(), configuration: .init())
        try await valid.validate()
        let missing = try ExperimentalCapabilityValidator.prepareGuestUIV1(module: ValidationGuest.build(), configuration: .init())
        do { try await missing.validate(); Issue.record("missing fixed UI exports accepted") }
        catch let failure as GuestUIProtocolFailureV1 { #expect(failure.phase == .validation && failure.code == .requiredExport) }
        let malformed = try ExperimentalCapabilityValidator.prepareGuestUIV1(module: Data([0]), configuration: .init())
        do { try await malformed.validate(); Issue.record("malformed module accepted") }
        catch let failure as ExperimentalCapabilityError { #expect(failure.failure.operation == .validation && failure.failure.kind == .validation(.malformed)) }
        let first = try ExperimentalCapabilityValidator.prepareGuestUIV1(module: GuestUIProgram.build(), configuration: .init())
        let second = try ExperimentalCapabilityValidator.prepare(module: ValidationGuest.build(), startupExport: "boot")
        #expect(throws: ExperimentalCapabilityError("validation_busy")) { try ExperimentalCapabilityValidator.prepareGuestUIV1(module: Data(), configuration: .init()) }
        first.cancel(); second.cancel()
    }

    @Test func guestUIConstructionRevalidatesAndRetiresWithoutFabricatedBridgeFailure() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-ui-create-" + UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let observer = LifecycleRecorder()
        let group = OwnedCapabilityAdapterGroup(storage: try lifecycleStore(directory), terminal: observer, retirement: observer)
        let exchange = try GuestUIExchangeV1(generation: 1)
        let construction = try ExperimentalCapabilitySession.prepareOwnedGuestUIV1(module: ValidationGuest.build(), configuration: .init(),
            policy: bridgePolicy(), adapterGroup: group, exchange: exchange)
        await #expect(throws: GuestUIProtocolFailureV1.self) { try await construction.create() }
        try await bridgeEventually { observer.retired == 1 }
        #expect(observer.failures.isEmpty && group.core.cleanupJobCount == 1)
        #expect(exchange.snapshot().firstUIProtocolFailure?.failure.code == .requiredExport)
        try await lifecycleReopens(directory)
    }

    @Test func guestUIHeaderPreflightChecksUnalignedFieldsOverflowOverlapAndImmutability() throws {
        let bytes = GuestUIProgram.header(document: 1024, length: 64)
        let valid = try GuestUIControlHeader.decode(bytes, headerOffset: 7, phase: .startup)
        #expect(valid.documentOffset == 1024 && valid.eventOffset == 4096)
        for (header, offset, code) in [(GuestUIProgram.header(document: 7, length: 64), UInt32(7), GuestUIProtocolCodeV1.memoryRange),
                                       (GuestUIProgram.header(document: 4090, length: 64), 7, .memoryRange),
                                       (GuestUIProgram.header(document: .max - 5, length: 64), 7, .memoryRange),
                                       (GuestUIProgram.header(document: 1024, length: 0), 7, .header),
                                       (GuestUIProgram.header(document: 1024, length: 64, magic: 0), 7, .header),
                                       (bytes, .max - 15, .memoryRange)] {
            do { _ = try GuestUIControlHeader.decode(header, headerOffset: offset, phase: .startup); Issue.record("bad header accepted") }
            catch let failure as GuestUIProtocolFailureV1 { #expect(failure.phase == .startup && failure.code == code) }
        }
    }

    @Test func guestUIStartupIsAtomicAndGenericOperationsCannotBypassTurnGuard() async throws {
        let h = try await GuestUIHarness.make()
        try await h.enable()
        #expect(h.exchange.snapshot().latestRevision == 1)
        await #expect(throws: ExperimentalCapabilityError.self) { try await h.session.startup() }
        await #expect(throws: ExperimentalCapabilityError.self) { try await h.session.invoke("mixer_guest_ui_event_v1", arguments: [.i32(0)]) }
        await #expect(throws: ExperimentalCapabilityError.self) { try await h.session.readMemory(offset: 7, count: 32) }
        await #expect(throws: ExperimentalCapabilityError.self) { try await h.session.writeMemory(offset: 4096, bytes: GuestUIProgram.event) }
        await #expect(throws: ExperimentalCapabilityError.self) { try await h.session.enableEffects() }
        #expect(!h.session.status.closed && h.session.status.failure == nil)
        let envelope = try h.present()
        try await h.accept(envelope)
        #expect(h.exchange.offer(envelope, generation: 1) == .busy)
        try await bridgeEventually { h.exchange.snapshot().latestRevision == 2 }
        #expect(try await h.store.get(KVGetArguments(namespace: "entries", key: "binary")).valueBase64 == "AAH+/w==")
        #expect(h.session.status.failure == nil && h.exchange.snapshot().firstUIProtocolFailure == nil)
        #expect(h.session.status.maximumBatchTurns <= 4 && h.session.status.maximumWorkers <= 8)
        let counters = h.exchange.snapshot().counters
        #expect(counters.acceptedEvents == 1 && counters.deliveredEvents == 1)
        #expect(counters.maximumEventSlots == 1 && counters.maximumEventBytes <= 4096)
        #expect(counters.maximumPendingFrames == 1 && counters.maximumClaimedFrames == 1 && counters.maximumRawDocumentBytes <= 65536)
        try await h.cleanup()
    }

    @Test func guestUIFailedStorageCompletionCannotPublishSavedDocument() async throws {
        let h = try await GuestUIHarness.make(allow: false)
        try await h.enable()
        try await h.accept(try h.present())
        try await bridgeEventually { h.session.status.acknowledgements == 1 }
        #expect(h.exchange.snapshot().latestRevision == 1 && h.exchange.snapshot().stop == nil)
        #expect(try await h.store.get(KVGetArguments(namespace: "entries", key: "binary")).found == false)
        try await h.cleanup()
    }

    @Test func guestUIRepeatedActualReadyTurnsRespectExistingBatchLimit() async throws {
        let h = try await GuestUIHarness.make(.unconsumed)
        try await h.enable()
        try await h.accept(try h.present())
        try await bridgeEventually { h.session.status.turns >= 20 }
        #expect(h.session.status.maximumBatchTurns <= 4 && h.session.status.yields > 0)
        #expect(h.exchange.snapshot().latestRevision == 1 && h.exchange.snapshot().firstUIProtocolFailure == nil)
        #expect(h.exchange.snapshot().counters.successfulTurns >= 20)
        try await h.cleanup()
    }

    @Test func guestUIInvalidInitialHeaderStopsBeforeIntentAndNativeMemoryFailureKeepsBridgeDomain() async throws {
        for (mode, code) in [(GuestUIProgram.Mode.invalidStartupHeader, GuestUIProtocolCodeV1.header), (.overlappingRanges, .memoryRange)] {
            let h = try await GuestUIHarness.make(mode)
            do { try await h.session.startupGuestUIV1(); Issue.record("invalid initial UI accepted") }
            catch let failure as GuestUIProtocolFailureV1 { #expect(failure.phase == .startup && failure.code == code) }
            try await bridgeEventually { h.session.status.drained }
            #expect(h.exchange.snapshot().firstUIProtocolFailure?.effectStage == .beforeIntent)
            #expect(h.session.status.turns == 1) // Native startup ran before the bad harvest.
            #expect(h.session.status.acceptedCalls == 0 && h.observer.failures.isEmpty)
            try await h.cleanup()
        }
        let h = try await GuestUIHarness.make(.outsideMemory)
        do { try await h.session.startupGuestUIV1(); Issue.record("outside memory read accepted") }
        catch let failure as ExperimentalCapabilityError {
            #expect(failure.nativeStatus == 3 && failure.failure.operation == .readMemory && failure.failure.kind == .callerAPI(.invalidNativeArguments))
        }
        try await bridgeEventually { h.session.status.drained }
        #expect(h.exchange.snapshot().firstUIProtocolFailure == nil)
        #expect(h.observer.failures.count == 1 && h.observer.failures[0].kind == .callerAPI(.invalidNativeArguments))
        try await h.cleanup()
    }

    @Test func guestUIInvalidEventTurnCannotAdmitItsStorageCalls() async throws {
        for (mode, code) in [(GuestUIProgram.Mode.invalidEventDocument, GuestUIProtocolCodeV1.document), (.nonzeroEvent, .eventResult)] {
            let h = try await GuestUIHarness.make(mode)
            try await h.enable()
            try await h.accept(try h.present())
            try await bridgeEventually { h.session.status.drained }
            let terminal = try #require(h.exchange.snapshot().firstUIProtocolFailure)
            #expect(terminal.failure.phase == .event && terminal.failure.code == code && terminal.effectStage == .intentEntered)
            #expect(h.session.status.acceptedCalls == 0 && h.observer.failures.isEmpty)
            #expect(h.session.status.turns == 2) // Startup plus native event, despite invalid UI.
            #expect(try FileManager.default.contentsOfDirectory(atPath: h.directory.path) == [".lock"])
            try await h.cleanup()
        }
    }

    @Test func guestUIHarvestsEveryActualReadyWakeBeforeTakingItsNewStorageCall() async throws {
        for (mode, code, revision) in [(GuestUIProgram.Mode.invalidWakeDocument, GuestUIProtocolCodeV1.document, UInt64(1)),
                                       (.changedWakeBuffer, .bufferChanged, 1), (.regressedWake, .revisionRegressed, 2), (.sameRevisionWake, .sameRevisionMutation, 1)] {
            let h = try await GuestUIHarness.make(mode, revision: revision)
            try await h.enable()
            try await h.accept(try h.present())
            try await bridgeEventually { h.session.status.drained }
            let terminal = try #require(h.exchange.snapshot().firstUIProtocolFailure)
            #expect(terminal.failure.phase == .wake && terminal.failure.code == code)
            #expect(h.session.status.acceptedCalls == 1 && h.observer.failures.isEmpty)
            #expect(h.exchange.snapshot().latestRevision == revision)
            try await h.cleanup()
        }
    }

    @Test func guestUIIdlePollingCloseAndAcceptedInputRaceRemainBounded() async throws {
        let h = try await GuestUIHarness.make()
        try await h.enable()
        let envelope = try h.present()
        let pollingGate = GuestUIQueueGate()
        ExperimentalQueues.guest.async { pollingGate.hold() }
        defer { pollingGate.release() }
        try await bridgeEventually { pollingGate.entered }
        let ticks = h.session.status.timerTicks
        try await Task.sleep(for: .milliseconds(35))
        #expect(h.session.status.timerTicks == ticks)
        pollingGate.release()
        // Dispatch timer delivery is asynchronous, including on a loaded CI host.
        // Keep the required observed tick; wait within the existing bounded helper.
        try await bridgeEventually { h.session.status.timerTicks > ticks }
        #expect(h.session.status.timerTicks > ticks)
        await withTaskGroup(of: Void.self) { group in
            for index in 0..<32 {
                group.addTask {
                    if index.isMultiple(of: 2) { _ = h.exchange.offer(envelope, generation: 1) }
                    else { h.session.close() }
                }
            }
        }
        try await h.cleanup()
        #expect(h.exchange.snapshot().stop != nil && !h.exchange.snapshot().guestTurnInFlight)
        #expect(h.session.status.maximumBatchTurns <= 4 && h.observer.failures.isEmpty)
    }

    @Test func guestUIQueuedCancellationRetainsConstructionUntilItsActualTail() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-ui-cancel-" + UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let observer = LifecycleRecorder()
        let group = OwnedCapabilityAdapterGroup(storage: try lifecycleStore(directory), terminal: observer, retirement: observer)
        let exchange = try GuestUIExchangeV1(generation: 1)
        let gate = GuestUIQueueGate()
        ExperimentalQueues.construction.async { gate.hold() }
        defer { gate.release() }
        try await bridgeEventually { gate.entered }
        let construction = try ExperimentalCapabilitySession.prepareOwnedGuestUIV1(module: GuestUIProgram.build(), configuration: .init(),
            policy: bridgePolicy(), adapterGroup: group, exchange: exchange)
        let pending = Task { try await construction.create() }
        try await Task.sleep(for: .milliseconds(20))
        pending.cancel()
        try await bridgeEventually { exchange.snapshot().stop == .cancelled }
        #expect(observer.retired == 0 && group.core.cleanupJobCount == 0)
        gate.release()
        await #expect(throws: CancellationError.self) { try await pending.value }
        try await bridgeEventually { observer.retired == 1 }
        #expect(observer.failures.isEmpty && group.core.cleanupJobCount == 1 && group.core.constructorTailObserved)
        try await lifecycleReopens(directory)
    }

    @Test func guestUIOwnedEnablePreservesAbsoluteDeadlineAndTypedStop() async throws {
        let h = try await GuestUIHarness.make()
        try await h.session.startupGuestUIV1()
        try h.exchange.enterEffectsIntent(generation: 1)
        do { try await h.session.enableOwnedEffects(noLaterThanUptimeNanoseconds: 0); Issue.record("expired UI enable succeeded") }
        catch let error as ExperimentalCapabilityError { #expect(error.failure.kind == .deadlineExceeded) }
        try await bridgeEventually { h.session.status.drained }
        #expect(h.exchange.snapshot().stop == .deadline && h.exchange.snapshot().effectsMayHaveOpened)
        #expect(!h.exchange.snapshot().effectsConfirmed && h.exchange.snapshot().firstUIProtocolFailure == nil)
        #expect(h.observer.failures.count == 1 && h.observer.failures[0].kind == .deadlineExceeded)
        try await h.cleanup()
    }

    @Test func guestUIActualNativeEnableWaitsForSharedConfirmationBeforeNewIO() async throws {
        let h = try await GuestUIHarness.make(.confirmationWindow)
        try await h.session.startupGuestUIV1()
        try h.exchange.enterEffectsIntent(generation: 1)
        try await h.session.enableOwnedEffects(noLaterThanUptimeNanoseconds: DispatchTime.now().uptimeNanoseconds + 5_000_000_000)
        // Pre-enable guest requests complete locally inside the native mailbox
        // and never appear as C call takes. The first enabled take is paused.
        try await bridgeEventually { h.session.status.acceptedCalls >= 1 }
        try await Task.sleep(for: .milliseconds(40))
        #expect(h.exchange.snapshot().stop == nil && !h.exchange.snapshot().effectsConfirmed)
        #expect(try await h.store.get(KVGetArguments(namespace: "entries", key: "binary")).found == false)
        try h.exchange.confirmEffectsEnabled(generation: 1)
        try await bridgeEventually { try await h.store.get(KVGetArguments(namespace: "entries", key: "binary")).found }
        #expect(h.session.status.failure == nil && h.exchange.snapshot().firstUIProtocolFailure == nil)
        try await h.cleanup()
    }
}

private final class GuestUIQueueGate: @unchecked Sendable {
    private let condition = NSCondition()
    private var began = false
    private var open = false
    var entered: Bool { condition.lock(); defer { condition.unlock() }; return began }
    func hold() {
        condition.lock(); began = true
        let deadline = Date().addingTimeInterval(5)
        while !open { if !condition.wait(until: deadline) { break } }
        condition.unlock()
    }
    func release() { condition.lock(); open = true; condition.broadcast(); condition.unlock() }
}
