import Foundation
import Testing
import MixerCapabilities

#if !os(WASI)
private final class CarriedInbox: @unchecked Sendable {
    private let lock = NSLock()
    private var deliveries: [Data] = []
    private var exits = 0
    func receive(_ data: Data) { lock.lock(); deliveries.append(data); lock.unlock() }
    func exited() { lock.lock(); exits += 1; lock.unlock() }
    var values: [Data] { lock.lock(); defer { lock.unlock() }; return deliveries }
    var exitCount: Int { lock.lock(); defer { lock.unlock() }; return exits }
}

// A test-only synchronous actor hold models queue delay. It has a bounded escape
// and is always released; no production hooks, clocks or adapters are replaced.
private final class CarriedActorGate: @unchecked Sendable {
    private let condition = NSCondition()
    private var open = false
    private var started = false
    private var expired = false
    func hold() {
        condition.lock(); started = true
        let escape = Date().addingTimeInterval(5)
        while !open {
            if !condition.wait(until: escape) { expired = true; break }
        }
        condition.unlock()
    }
    func release() { condition.lock(); open = true; condition.broadcast(); condition.unlock() }
    var entered: Bool { condition.lock(); defer { condition.unlock() }; return started }
    var timedOut: Bool { condition.lock(); defer { condition.unlock() }; return expired }
}
private func holdStorage(_ store: isolated AppPrivateKeyValueStore, gate: CarriedActorGate) { gate.hold() }
private func carriedPolicy() throws -> CapabilityPolicy {
    let grant = CapabilityGrant(capabilityID: CapabilitySchemas.storageID,
                                schemaSHA256: CapabilitySchemas.storageSHA256,
                                permissions: ["storage.appPrivate"], namespaces: ["entries"])
    return try CapabilityPolicy(installed: [grant], manifest: [grant])
}
private func carriedEventually(_ condition: () async throws -> Bool) async throws {
    for _ in 0..<600 {
        if try await condition() { return }
        try await Task.sleep(nanoseconds: 5_000_000)
    }
    try #require(try await condition(), "carried deadline did not reach its bounded transition")
}
private func carriedNextID(_ host: CapabilityHost) async throws -> CapabilityRequestID {
    var next: CapabilityRequestID?
    try await carriedEventually { next = try? await host.issueRequestID(); return next != nil }
    return try #require(next)
}
private func carriedDirectory() -> URL {
    FileManager.default.temporaryDirectory.appendingPathComponent("mixer-carried-" + UUID().uuidString)
}
private func carriedGet(_ identity: CapabilityRequestID) -> CapabilityCall {
    CapabilityCall(identity: identity, operation: .get(KVGetArguments(namespace: "entries", key: "absent")))
}
private func carriedPut(_ identity: CapabilityRequestID) -> CapabilityCall {
    CapabilityCall(identity: identity, operation: .put(KVPutArguments(namespace: "entries", key: "must-not-exist", valueBase64: "YQ==")))
}

@Suite(.serialized)
struct CapabilityCarriedDeadlineTests {
    @Test func expiredCapAvoidsStorageMutationAndExitsExactlyOnce() async throws {
        let directory = carriedDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = try AppPrivateKeyValueStore(directory: directory, namespaces: ["entries"])
        let host = try CapabilityHost(policy: carriedPolicy(), maximumRequests: 1,
                                      installedAdapters: InstalledCapabilityAdapters(storage: store))
        let inbox = CarriedInbox(), call = carriedPut(try await host.issueRequestID())
        try await host.submitObserved(CapabilityCodec.encodeCall(call), noLaterThan: .now.advanced(by: .seconds(-1)),
                                      deliver: inbox.receive, didExit: inbox.exited)
        try await carriedEventually { inbox.values.count == 1 && inbox.exitCount == 1 }
        #expect(try CapabilityCodec.decodeCompletion(#require(inbox.values.first), expected: call).outcome == .failure(.deadlineExceeded))
        #expect(try await store.get(KVGetArguments(namespace: "entries", key: "must-not-exist")).found == false)
        #expect(try FileManager.default.contentsOfDirectory(atPath: directory.path) == [".lock"])
        let next = try await carriedNextID(host)
        #expect(next.slot == call.identity.slot && next.generation == call.identity.generation + 1)
        await host.close()
        #expect(inbox.values.count == 1 && inbox.exitCount == 1)
        await store.close()
    }

    @Test func actorQueueTimeCannotRenewCarriedBudget() async throws {
        let directory = carriedDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = try AppPrivateKeyValueStore(directory: directory, namespaces: ["entries"])
        let host = try CapabilityHost(policy: carriedPolicy(), maximumRequests: 2,
                                      installedAdapters: InstalledCapabilityAdapters(storage: store))
        let blocker = CarriedInbox(), target = CarriedInbox(), gate = CarriedActorGate()
        defer { gate.release() }
        let first = carriedGet(try await host.issueRequestID())
        let late = carriedPut(try await host.issueRequestID())
        try await host.submitObserved(CapabilityCodec.encodeCall(first), deliver: { blocker.receive($0); gate.hold() }, didExit: blocker.exited)
        try await carriedEventually { gate.entered }
        let cutoff = ContinuousClock.now.advanced(by: .milliseconds(100))
        let bytes = try CapabilityCodec.encodeCall(late)
        let admission = Task { try await host.submitObserved(bytes, noLaterThan: cutoff, deliver: target.receive, didExit: target.exited) }
        try await ContinuousClock().sleep(until: cutoff.advanced(by: .milliseconds(30)))
        #expect(target.values.isEmpty && target.exitCount == 0)
        gate.release()
        try await admission.value
        try await carriedEventually { target.values.count == 1 && target.exitCount == 1 && blocker.exitCount == 1 }
        #expect(try CapabilityCodec.decodeCompletion(#require(target.values.first), expected: late).outcome == .failure(.deadlineExceeded))
        #expect(try await store.get(KVGetArguments(namespace: "entries", key: "must-not-exist")).found == false)
        #expect(!gate.timedOut)
        await host.close()
        #expect(target.values.count == 1 && target.exitCount == 1)
        await store.close()
    }

    private func queuedStorageDeadline(hostTimeout: UInt32, carriedMilliseconds: Int64?) async throws {
        let directory = carriedDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = try AppPrivateKeyValueStore(directory: directory, namespaces: ["entries"])
        let gate = CarriedActorGate()
        defer { gate.release() }
        let hold = Task.detached { await holdStorage(store, gate: gate) }
        try await carriedEventually { gate.entered }
        let host = try CapabilityHost(policy: carriedPolicy(), maximumRequests: 1, timeoutMilliseconds: hostTimeout,
                                      installedAdapters: InstalledCapabilityAdapters(storage: store))
        let inbox = CarriedInbox(), call = carriedGet(try await host.issueRequestID())
        let acceptedBy = ContinuousClock.now
        if let carriedMilliseconds {
            try await host.submitObserved(CapabilityCodec.encodeCall(call), noLaterThan: acceptedBy.advanced(by: .milliseconds(carriedMilliseconds)),
                                          deliver: inbox.receive, didExit: inbox.exited)
        } else {
            try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited)
        }
        try await carriedEventually { inbox.values.count == 1 }
        #expect(try CapabilityCodec.decodeCompletion(#require(inbox.values.first), expected: call).outcome == .failure(.deadlineExceeded))
        #expect(ContinuousClock.now < acceptedBy.advanced(by: .seconds(1)))
        #expect(inbox.exitCount == 0)
        await #expect(throws: CapabilityWireError.self) { try await host.issueRequestID() }
        gate.release()
        await hold.value
        try await carriedEventually { inbox.exitCount == 1 }
        let next = try await carriedNextID(host)
        #expect(next.slot == call.identity.slot && next.generation == call.identity.generation + 1)
        await host.close()
        #expect(inbox.values.count == 1 && inbox.exitCount == 1 && !gate.timedOut)
        await store.close()
    }

    @Test func earlierCapWinsWhileInstalledStorageIsQueued() async throws {
        try await queuedStorageDeadline(hostTimeout: 2000, carriedMilliseconds: 100)
    }
    @Test func futureCapCannotExtendHostDefault() async throws {
        try await queuedStorageDeadline(hostTimeout: 50, carriedMilliseconds: 2000)
    }
    @Test func originalObservedOverloadKeepsItsDefaultDeadlineAndExitJoin() async throws {
        try await queuedStorageDeadline(hostTimeout: 50, carriedMilliseconds: nil)
    }
    @Test func timelyFirstTerminalSurvivesCapAndClose() async throws {
        let directory = carriedDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = try AppPrivateKeyValueStore(directory: directory, namespaces: ["entries"])
        let host = try CapabilityHost(policy: carriedPolicy(), installedAdapters: InstalledCapabilityAdapters(storage: store))
        let inbox = CarriedInbox(), call = carriedGet(try await host.issueRequestID())
        let cutoff = ContinuousClock.now.advanced(by: .milliseconds(500))
        try await host.submitObserved(CapabilityCodec.encodeCall(call), noLaterThan: cutoff,
                                      deliver: inbox.receive, didExit: inbox.exited)
        try await carriedEventually { inbox.values.count == 1 && inbox.exitCount == 1 }
        #expect(try CapabilityCodec.decodeCompletion(#require(inbox.values.first), expected: call).outcome == .success(.get(KVGetResponse(found: false, valueBase64: ""))))
        try await ContinuousClock().sleep(until: cutoff.advanced(by: .milliseconds(20)))
        await host.close()
        #expect(inbox.values.count == 1 && inbox.exitCount == 1)
        await store.close()
    }
}
#endif
