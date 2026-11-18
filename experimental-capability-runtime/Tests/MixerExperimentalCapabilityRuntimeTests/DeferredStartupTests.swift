import Dispatch
import Foundation
import Testing
@_spi(InstalledApplicationStorage) import MixerCapabilities
@_spi(GuestUIV1) import MixerGuest
import MixerUI
@_spi(GuestUIV1) @_spi(CapabilityLifecycle) @testable import MixerExperimentalCapabilityRuntime

private actor HydrationRepository: InstalledApplicationStorageServing {
    var reads = 0
    var writes: [Int] = []
    let delayed: Bool

    init(delayed: Bool = false) { self.delayed = delayed }

    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        reads += 1
        #expect(arguments == KVGetArguments(namespace: "entries", key: "snapshot"))
        if delayed { try await Task.sleep(for: .seconds(3)) }
        return KVGetResponse(found: true, valueBase64: "AQ==")
    }

    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        writes = [maximumTotalBytes, maximumEntries]
        throw CapabilityFailure.quotaExceeded
    }

    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        Issue.record("unexpected delete")
        return KVMutationResponse(committed: false)
    }
}

private enum HydrationGuest {
    static let startup = "mixer_guest_ui_start_v1"
    static let hook = "mixer_guest_ui_hydrate_v1"

    static func build(hookType: UInt8 = 2) throws -> Data {
        let u = GuestProgram.u, i = GuestProgram.i, text = GuestProgram.text, section = GuestProgram.section
        let request = Data(#"{"namespace":"entries","key":"snapshot"}"#.utf8)
        let put = Data(#"{"namespace":"entries","key":"binary","valueBase64":"AAH+/w=="}"#.utf8)
        let completion = try GuestCapabilityTransportCodecV1.encodeCompletion(
            .success(.get(KVGetResponse(found: true, valueBase64: "AQ=="))), operation: .storageGet)
        let frame = GuestUIProgram.document(revision: 9, label: "Hydrated")
        let types = [
            GuestProgram.sig([0x7f, 0x7f, 0x7f], 0x7f),
            GuestProgram.sig([0x7e, 0x7f, 0x7f, 0x7f], 0x7f),
            GuestProgram.sig([], 0x7f),
            GuestProgram.sig([0x7f], 0x7f),
            GuestProgram.sig([], nil),
        ]
        var imports = u(3)
        for (name, type): (String, UInt8) in [("storage_get", 0), ("poll", 1), ("storage_put", 0)] {
            imports += text("mixer.capability.v1") + text(name) + [0, type]
        }
        let functions = [startup, "mixer_guest_ui_event_v1", "mixer_guest_capability_ready_v1", hook]
        var exports = u(4)
        for (offset, name) in functions.enumerated() {
            exports += text(name) + [0] + u(UInt32(3 + offset))
        }
        func enqueue(_ address: Int32, count: Int, token: Int32, importIndex: UInt8) -> [UInt8] {
            i(address) + i(Int32(count)) + i(token) + [0x10, importIndex, 0x1a]
        }
        func store(_ address: Int32, _ value: Int32) -> [UInt8] {
            i(address) + i(value) + [0x36, 0, 0]
        }
        var ready = i(128) + [0x29, 0, 0]
        ready += i(10000) + i(2048) + i(160) + [0x10, 1, 0x45, 0x04, 0x40]
        ready += i(160) + [0x28, 0, 0] + i(Int32(completion.count)) + [0x46, 0x04, 0x40]
        for (index, byte) in completion.enumerated() {
            ready += i(10000 + Int32(index)) + [0x2d, 0, 0] + i(Int32(byte)) + [0x47, 0x04, 0x40, 0x00, 0x0b]
        }
        ready += store(15, 1024) + store(19, Int32(frame.count))
        ready += [0x0b, 0x0b, 0x0b]
        let end: [UInt8] = [0x0b]
        let event = enqueue(9200, count: put.count, token: 144, importIndex: 2) + i(0) + end
        let hydrate = if hookType == 2 {
            enqueue(9000, count: request.count, token: 128, importIndex: 0) + i(0) + end
        } else {
            end
        }
        let bodies = [i(7) + end, event, ready, hydrate]
        var code = u(4)
        for body in bodies { code += u(UInt32(body.count + 1)) + [0] + body }
        var data = u(4)
        let header = GuestUIProgram.header(document: 0, length: 0)
        for (offset, bytes): (Int32, Data) in [(7, header), (1024, frame), (9000, request), (9200, put)] {
            data += [0] + i(offset) + [0x0b] + u(UInt32(bytes.count)) + Array(bytes)
        }
        var module: [UInt8] = [0, 97, 115, 109, 1, 0, 0, 0]
        module += section(1, u(UInt32(types.count)) + types.flatMap { $0 })
        module += section(2, imports) + section(3, [4, 2, 3, 4, hookType]) + section(5, [1, 1, 1, 1])
        module += section(7, exports) + section(10, code) + section(11, data)
        return Data(module)
    }
}

extension ExperimentalBridgeTests {
    @Test func deferredStartupPublishesOnlyFromConfirmedReadAndPassesQuotasOnEvent() async throws {
        let repository = HydrationRepository()
        let (session, exchange, observer) = try await hydrationSession(repository)
        defer { session.close() }
        try await session.startupGuestUIV1()
        #expect(exchange.snapshot().latestRevision == nil)
        #expect(await repository.reads == 0)
        try exchange.enterEffectsIntent(generation: 1)
        try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: DispatchTime.now().uptimeNanoseconds + 2_000_000_000)
        #expect(await repository.reads == 0)
        #expect(exchange.claimPresentation(generation: 1) == nil)
        try exchange.confirmEffectsEnabled(generation: 1)
        try await bridgeEventually { exchange.snapshot().latestRevision == 9 }
        #expect(await repository.reads == 1)
        let claim = try #require(exchange.claimPresentation(generation: 1))
        let frame = try #require(claim.frame)
        var reconciler = UIReconciler()
        _ = try reconciler.apply(frame.document.document)
        let snapshot = try reconciler.currentSnapshot()
        _ = exchange.completePresentation(claim, snapshot: snapshot)
        let event = UIEventEnvelope(revision: 9, identity: try #require(snapshot.identity(for: "save")), event: .activate)
        #expect(exchange.offer(event, generation: 1) == .accepted(sequence: 1))
        try await bridgeEventually { await repository.writes == [128, 2] }
        session.close()
        try await bridgeEventually { session.status.drained && observer.retired == 1 }
    }

    @Test func deferredStartupDeadlineStopsAndRetiresWithoutPublishing() async throws {
        let repository = HydrationRepository(delayed: true)
        let (session, exchange, observer) = try await hydrationSession(repository)
        defer { session.close() }
        try await session.startupGuestUIV1()
        try exchange.enterEffectsIntent(generation: 1)
        try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: DispatchTime.now().uptimeNanoseconds + 300_000_000)
        try exchange.confirmEffectsEnabled(generation: 1)
        try await bridgeEventually { session.status.drained && observer.retired == 1 }
        #expect(await repository.reads == 1)
        #expect(exchange.snapshot().latestRevision == nil)
        #expect(exchange.snapshot().firstUIProtocolFailure?.failure.code == .startupDeadline)
    }

    @Test func deferredStartupHookValidationIsOptInAndRequiresDefinedSignature() async throws {
        let configuration = ExperimentalCapabilityConfiguration()
        let wrongSignature = try HydrationGuest.build(hookType: 4)
        try NativeCapabilitySession.validateGuestUI(module: wrongSignature, configuration: configuration)
        for wrong in [wrongSignature, GuestUIProgram.build()] {
            #expect(throws: GuestUIProtocolFailureV1(phase: .validation, code: .requiredExport)) {
                try NativeCapabilitySession.validateGuestUI(module: wrong, configuration: configuration, deferredStartup: true)
            }
        }
        let (legacy, exchange, observer) = try await hydrationSession(HydrationRepository(), deferred: false)
        defer { legacy.close() }
        await #expect(throws: GuestUIProtocolFailureV1(phase: .startup, code: .header)) {
            try await legacy.startupGuestUIV1()
        }
        try await bridgeEventually { legacy.status.drained && observer.retired == 1 }
        #expect(exchange.snapshot().latestRevision == nil)
    }

    @Test func hydrationPostDistinguishesDiscardedNativeCompletion() throws {
        let native = try NativeCapabilitySession(module: HydrationGuest.build(), startup: HydrationGuest.startup, configuration: .init())
        defer { try? native.close() }
        _ = try native.startup()
        try native.enable()
        _ = try native.invoke(HydrationGuest.hook, arguments: [])
        guard case .call(let token, .storageGet, _) = try native.take() else {
            Issue.record("expected hydration request")
            return
        }
        let reply = try GuestCapabilityTransportCodecV1.encodeCompletion(
            .success(.get(KVGetResponse(found: true, valueBase64: "AQ=="))), operation: .storageGet)
        #expect(try native.post(token: token, operation: .storageGet, data: reply))
        #expect(try !native.post(token: token, operation: .storageGet, data: reply))
        try native.ack(token: token, operation: .storageGet)
    }

    private func hydrationSession(_ repository: HydrationRepository, deferred: Bool = true) async throws
        -> (ExperimentalCapabilitySession, GuestUIExchangeV1, LifecycleRecorder) {
        let observer = LifecycleRecorder()
        let adapter = InstalledApplicationStorageAdapter(service: repository, maximumTotalBytes: 128, maximumEntries: 2)
        let group = OwnedCapabilityAdapterGroup(http: nil, applicationStorage: adapter, terminal: observer, retirement: observer)
        let exchange = try GuestUIExchangeV1(generation: 1, allowsDeferredStartup: deferred)
        let construction = try ExperimentalCapabilitySession.prepareOwnedGuestUIV1(module: HydrationGuest.build(),
            configuration: .init(), policy: bridgePolicy(), adapterGroup: group, exchange: exchange)
        return (try await construction.create(), exchange, observer)
    }
}
