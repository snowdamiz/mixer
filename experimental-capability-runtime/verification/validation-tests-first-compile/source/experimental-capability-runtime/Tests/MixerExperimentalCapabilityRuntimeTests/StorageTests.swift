import Foundation
import Testing
import MixerCapabilities
@testable import MixerExperimentalCapabilityRuntime

func bridgeEventually(_ condition: () async throws -> Bool) async throws {
    for _ in 0..<800 {
        if try await condition() { return }
        try await Task.sleep(for: .milliseconds(5))
    }
    try #require(try await condition(), "bounded bridge transition did not finish")
}
func bridgePolicy(allow: Bool = true) throws -> CapabilityPolicy {
    let grant = CapabilityGrant(capabilityID: CapabilitySchemas.storageID, schemaSHA256: CapabilitySchemas.storageSHA256,
                                permissions: ["storage.appPrivate"], namespaces: ["entries"])
    return try CapabilityPolicy(installed: [grant], manifest: allow ? [grant] : [])
}
func bridgeSession(_ module: Data, store: AppPrivateKeyValueStore, allow: Bool = true,
                   configuration: ExperimentalCapabilityConfiguration = .init()) async throws -> ExperimentalCapabilitySession {
    try await ExperimentalCapabilitySession.prepare(module: module, startupExport: "boot", configuration: configuration,
        policy: bridgePolicy(allow: allow), adapters: InstalledCapabilityAdapters(storage: store)).create()
}
func guestOutcome(_ session: ExperimentalCapabilitySession, stage: Int, operation: GuestCapabilityOperationV1) async throws -> GuestCapabilityCompletionV1 {
    let word = try await session.readMemory(offset: UInt32(124 + 4 * stage), count: 4)
    let count = word.enumerated().reduce(UInt32(0)) { $0 | UInt32($1.element) << UInt32($1.offset * 8) }
    return try GuestCapabilityTransportCodecV1.decodeCompletion(try await session.readMemory(offset: UInt32(stage * 4096), count: Int(count)), expectedOperation: operation)
}

extension ExperimentalBridgeTests {
    @Test func realWasmPerformsConcreteStoragePutGetDeleteAndMissing() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-real-wasm-" + UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = try AppPrivateKeyValueStore(directory: directory, namespaces: ["entries"])
        let session = try await bridgeSession(GuestProgram.build(), store: store)
        defer { session.close() }
        _ = try await session.startup(); try await session.enableEffects()
        #expect(try await session.invoke("run").value == .i32(0))
        try await bridgeEventually { try await session.invoke("stage").value == .i32(5) }
        #expect(try await guestOutcome(session, stage: 1, operation: .storagePut) == .success(.put(KVMutationResponse(committed: true))))
        #expect(try await guestOutcome(session, stage: 2, operation: .storageGet) == .success(.get(KVGetResponse(found: true, valueBase64: "AAH+/w=="))))
        #expect(try await guestOutcome(session, stage: 3, operation: .storageDelete) == .success(.delete(KVMutationResponse(committed: true))))
        #expect(try await guestOutcome(session, stage: 4, operation: .storageGet) == .success(.get(KVGetResponse(found: false, valueBase64: ""))))
        #expect(try await store.get(KVGetArguments(namespace: "entries", key: "binary")).found == false)
        session.close()
        try await bridgeEventually { session.status.drained }
        #expect(session.status.acknowledgements == 4)
        #expect(session.status.failure == nil)
        await store.close()
    }
    @Test func trappedEnqueueCannotStartConcreteStorage() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-trap-wasm-" + UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = try AppPrivateKeyValueStore(directory: directory, namespaces: ["entries"])
        let session = try await bridgeSession(GuestProgram.build(.trap), store: store)
        _ = try await session.startup(); try await session.enableEffects()
        await #expect(throws: ExperimentalCapabilityError.self) { try await session.invoke("run") }
        try await bridgeEventually { session.status.drained }
        #expect(session.status.acceptedCalls == 0)
        #expect(try await store.get(KVGetArguments(namespace: "entries", key: "binary")).found == false)
        await store.close()
    }
    @Test func malformedArgumentsRejectThroughGuestWithoutStoreMutation() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-malformed-wasm-" + UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = try AppPrivateKeyValueStore(directory: directory, namespaces: ["entries"])
        let session = try await bridgeSession(GuestProgram.build(.single(2,Data(#"{"namespace":"entries","key":"binary","key":"other","valueBase64":"YQ=="}"#.utf8))), store: store)
        _ = try await session.startup(); try await session.enableEffects(); _ = try await session.invoke("run")
        try await bridgeEventually { try await session.invoke("stage").value == .i32(5) }
        #expect(try await guestOutcome(session, stage: 1, operation: .storagePut) == .rejected(.invalidArguments))
        #expect(try FileManager.default.contentsOfDirectory(atPath: directory.path) == [".lock"])
        session.close(); try await bridgeEventually { session.status.drained }
        #expect(session.status.acknowledgements == 1)
        await store.close()
    }
}
