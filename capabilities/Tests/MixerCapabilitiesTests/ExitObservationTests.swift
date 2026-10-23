import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import Testing
@testable import MixerCapabilities

#if !os(WASI)
private final class ExitInbox: @unchecked Sendable {
    private let lock = NSLock()
    private var deliveries: [Data] = []
    private var exits = 0
    func receive(_ value: Data) { lock.lock(); deliveries.append(value); lock.unlock() }
    func exited() { lock.lock(); exits += 1; lock.unlock() }
    var count: Int { lock.lock(); defer { lock.unlock() }; return exits }
    var values: [Data] { lock.lock(); defer { lock.unlock() }; return deliveries }
}
private actor ExitInvocationGate {
    private var waiting: CheckedContinuation<Void, Never>?
    private(set) var entered = false
    func hold() async { await withCheckedContinuation { entered = true; waiting = $0 } }
    func release() { waiting?.resume(); waiting = nil }
}
// Holds the real invalidation delegate boundary, not a synthetic completion. Each
// gate has a bounded escape so a regression cannot hang the test process forever.
private final class ExitInvalidationGate: @unchecked Sendable {
    private let condition = NSCondition()
    private var open = false
    private var started = false
    private var expired = false
    func hold() {
        condition.lock(); started = true
        let deadline = Date().addingTimeInterval(10)
        while !open {
            if !condition.wait(until: deadline) { expired = true; break }
        }
        condition.unlock()
    }
    func release() { condition.lock(); open = true; condition.broadcast(); condition.unlock() }
    var entered: Bool { condition.lock(); defer { condition.unlock() }; return started }
    var timedOut: Bool { condition.lock(); defer { condition.unlock() }; return expired }
}
private final class ExitFixtureRegistry: @unchecked Sendable {
    private let lock = NSLock()
    private var fixtures: [String: ExitFixture] = [:]
    private var starts: Set<String> = []
    func install(stall: Bool = false, status: Int = 200, error: URLError.Code? = nil) -> String {
        let url = "https://api.example.test/exit-" + UUID().uuidString.lowercased()
        lock.lock(); fixtures[url] = ExitFixture(stall: stall, status: status, error: error); lock.unlock(); return url
    }
    func begin(_ url: String) -> ExitFixture? { lock.lock(); defer { lock.unlock() }; starts.insert(url); return fixtures[url] }
    func started(_ url: String) -> Bool { lock.lock(); defer { lock.unlock() }; return starts.contains(url) }
}
private struct ExitFixture: Sendable {
    let stall: Bool
    let status: Int
    let error: URLError.Code?
}
private final class ExitFixtureProtocol: URLProtocol {
    static let registry = ExitFixtureRegistry()
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        guard let url = request.url, let fixture = Self.registry.begin(url.absoluteString) else {
            client?.urlProtocol(self, didFailWithError: URLError(.badURL)); return
        }
        if let error = fixture.error { client?.urlProtocol(self, didFailWithError: URLError(error)); return }
        let response = HTTPURLResponse(url: url, statusCode: fixture.status, httpVersion: "HTTP/1.1", headerFields: ["Content-Length": "0"])!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        if !fixture.stall { client?.urlProtocolDidFinishLoading(self) }
    }
    override func stopLoading() {}
}
#if !canImport(FoundationNetworking)
extension ExitFixtureProtocol: @unchecked Sendable {}
#endif
private func exitPolicy(allow: Bool = true) throws -> CapabilityPolicy {
    let http = CapabilityGrant(capabilityID: CapabilitySchemas.httpID, schemaSHA256: CapabilitySchemas.httpSHA256,
                               permissions: ["network.https"], origins: ["https://api.example.test"], methods: ["GET"])
    let storage = CapabilityGrant(capabilityID: CapabilitySchemas.storageID, schemaSHA256: CapabilitySchemas.storageSHA256,
                                  permissions: ["storage.appPrivate"], namespaces: ["entries"])
    return try CapabilityPolicy(installed: [http, storage], manifest: allow ? [http, storage] : [])
}
private func exitCall(_ id: CapabilityRequestID, url: String, timeout: UInt32 = 1000) -> CapabilityCall {
    CapabilityCall(identity: id, operation: .http(HTTPRequestArguments(url: url, method: "GET", headers: [], bodyBase64: "", timeoutMilliseconds: timeout)))
}
private func exitTransport(_ gate: ExitInvalidationGate? = nil, capacity: Int = 64) throws -> URLSessionHTTPTransport {
    if let gate {
        return try URLSessionHTTPTransport(maximumConcurrentRequests: capacity, protocolClasses: [ExitFixtureProtocol.self],
                                           beforeInvalidation: { gate.hold() })
    }
    return try URLSessionHTTPTransport(maximumConcurrentRequests: capacity, protocolClasses: [ExitFixtureProtocol.self])
}
private final class ExitWeakHost {
    weak var value: CapabilityHost?
    init(_ host: CapabilityHost?) { value = host }
}
private final class ExitAdmissionClock: @unchecked Sendable {
    private let lock = NSLock()
    private let initial = ContinuousClock.now
    private var reads = 0
    func now() -> ContinuousClock.Instant {
        lock.lock(); defer { lock.unlock() }; reads += 1
        // Deadline construction and preflight admit, but exchange.start expires
        // before creating its session after the transport counter was acquired.
        return reads <= 2 ? initial : initial.advanced(by: .seconds(60))
    }
    var clock: HTTPTransportClock {
        HTTPTransportClock(now: { self.now() }, sleepUntil: { _ in try await Task.sleep(nanoseconds: 60_000_000_000) })
    }
}
private func eventuallyExit(_ condition: () async throws -> Bool) async throws {
    for _ in 0..<600 {
        if try await condition() { return }
        try await Task.sleep(nanoseconds: 5_000_000)
    }
    try #require(try await condition(), "native request exit observation did not reach expected state")
}
private func nextExitID(_ host: CapabilityHost) async throws -> CapabilityRequestID {
    var result: CapabilityRequestID?
    try await eventuallyExit { result = try? await host.issueRequestID(); return result != nil }
    return try #require(result)
}

@Suite(.serialized)
struct NativeCapabilityExitTests {
    @Test func rejectsUntrustedObservedCallsBeforeAcceptingReservationOrObserver() async throws {
        let inbox = ExitInbox()
        let legacy = try CapabilityHost(policy: exitPolicy(), http: { _ in Issue.record("legacy work started"); throw CapabilityFailure.ioFailure })
        let oldCall = exitCall(try await legacy.issueRequestID(), url: ExitFixtureProtocol.registry.install())
        await #expect(throws: CapabilityWireError.self) { try await legacy.submitObserved(CapabilityCodec.encodeCall(oldCall), deliver: inbox.receive, didExit: inbox.exited) }
        let gate = ExitInvocationGate()
        let installed = InstalledCapabilityAdapters(hooks: InstalledCapabilityExecutionHooks(beforeInvocation: { await gate.hold() }))
        let host = try CapabilityHost(policy: exitPolicy(), maximumRequests: 1, installedAdapters: installed)
        let call = exitCall(try await host.issueRequestID(), url: ExitFixtureProtocol.registry.install())
        await #expect(throws: CapabilityWireError.self) { try await host.submitObserved(Data("{}".utf8), deliver: inbox.receive, didExit: inbox.exited) }
        await #expect(throws: CapabilityWireError.self) { try await host.submitObserved(CapabilityCodec.encodeCancel(call), deliver: inbox.receive, didExit: inbox.exited) }
        await #expect(throws: CapabilityWireError.self) { try await host.submitObserved(CapabilityCodec.encodeCall(oldCall), deliver: inbox.receive, didExit: inbox.exited) }
        #expect(inbox.count == 0)
        try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited)
        await #expect(throws: CapabilityWireError.self) { try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited) }
        try await eventuallyExit { await gate.entered }
        await gate.release()
        try await eventuallyExit { inbox.count == 1 }
        let next = try await nextExitID(host)
        #expect(next.generation == call.identity.generation + 1)
        await #expect(throws: CapabilityWireError.self) { try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited) }
        await host.close()
        await #expect(throws: CapabilityWireError.self) { try await host.submitObserved(CapabilityCodec.encodeCall(exitCall(next, url: callURL(call))), deliver: inbox.receive, didExit: inbox.exited) }
        #expect(inbox.count == 1)
        await legacy.close()
    }

    @Test func deniedAndUnavailableCallsResolveNoIOExitOnce() async throws {
        for allow in [false, true] {
            let inbox = ExitInbox()
            let host = try CapabilityHost(policy: exitPolicy(allow: allow), maximumRequests: 1, installedAdapters: InstalledCapabilityAdapters())
            let call = exitCall(try await host.issueRequestID(), url: ExitFixtureProtocol.registry.install())
            try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited)
            try await eventuallyExit { inbox.count == 1 && inbox.values.count == 1 }
            #expect(try CapabilityCodec.decodeCompletion(#require(inbox.values.first), expected: call).outcome == .failure(allow ? .unavailable : .permissionDenied))
            _ = try await nextExitID(host)
            await host.close()
            #expect(inbox.count == 1)
            #expect(!ExitFixtureProtocol.registry.started(callURL(call)))
        }
    }

    @Test func cancelledUnusedReservationCreatesNoObserverObligation() async throws {
        let inbox = ExitInbox()
        let host = try CapabilityHost(policy: exitPolicy(), maximumRequests: 1, installedAdapters: InstalledCapabilityAdapters())
        let call = exitCall(try await host.issueRequestID(), url: ExitFixtureProtocol.registry.install())
        try await host.submit(CapabilityCodec.encodeCancel(call), deliver: inbox.receive)
        await #expect(throws: CapabilityWireError.self) { try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited) }
        let next = try await host.issueRequestID()
        #expect(next.generation == call.identity.generation + 1)
        #expect(inbox.count == 0 && inbox.values.isEmpty)
        await host.close()
    }

    @Test func cancellationBeforeInvocationExitsWithoutStartingNativeIO() async throws {
        let gate = ExitInvocationGate(), inbox = ExitInbox()
        let transport = try exitTransport()
        let adapters = InstalledCapabilityAdapters(http: transport, hooks: InstalledCapabilityExecutionHooks(beforeInvocation: { await gate.hold() }))
        let host = try CapabilityHost(policy: exitPolicy(), maximumRequests: 1, installedAdapters: adapters)
        let call = exitCall(try await host.issueRequestID(), url: ExitFixtureProtocol.registry.install())
        try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited)
        try await eventuallyExit { await gate.entered }
        try await host.submit(CapabilityCodec.encodeCancel(call), deliver: { _ in Issue.record("cancel stole delivery") })
        #expect(inbox.count == 0 && inbox.values.count == 1)
        await #expect(throws: CapabilityWireError.self) { try await host.issueRequestID() }
        await gate.release()
        try await eventuallyExit { inbox.count == 1 }
        #expect(!ExitFixtureProtocol.registry.started(callURL(call)))
        #expect(transport.activeRequests == 0)
        _ = try await nextExitID(host)
        await host.close()
    }

    @Test func successAndOrdinarySubmitRetainHostCapacityUntilInvalidation() async throws {
        for observed in [true, false] {
            let gate = ExitInvalidationGate(), inbox = ExitInbox()
            defer { gate.release() }
            let transport = try exitTransport(gate)
            let host = try CapabilityHost(policy: exitPolicy(), maximumRequests: 1, installedAdapters: InstalledCapabilityAdapters(http: transport))
            let call = exitCall(try await host.issueRequestID(), url: ExitFixtureProtocol.registry.install())
            if observed { try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited) }
            else { try await host.submit(CapabilityCodec.encodeCall(call), deliver: inbox.receive) }
            try await eventuallyExit { gate.entered && inbox.values.count == 1 }
            #expect(inbox.count == 0 && transport.activeRequests == 1)
            #expect(try CapabilityCodec.decodeCompletion(#require(inbox.values.first), expected: call).outcome == .success(.http(HTTPResponse(status: 200, headers: [], bodyBase64: ""))))
            await #expect(throws: CapabilityWireError.self) { try await host.issueRequestID() }
            gate.release()
            let next = try await nextExitID(host)
            #expect(next.generation == 2 && transport.activeRequests == 0)
            #expect(inbox.count == (observed ? 1 : 0))
            #expect(!gate.timedOut)
            await host.close()
        }
    }

    @Test func invalidationBeforeInvocationReturnStillCannotReleaseHostCapacity() async throws {
        let gate = ExitInvocationGate(), inbox = ExitInbox()
        let transport = try exitTransport()
        let adapters = InstalledCapabilityAdapters(http: transport, hooks: InstalledCapabilityExecutionHooks(afterInvocation: { await gate.hold() }))
        let host = try CapabilityHost(policy: exitPolicy(), maximumRequests: 1, installedAdapters: adapters)
        let call = exitCall(try await host.issueRequestID(), url: ExitFixtureProtocol.registry.install())
        try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited)
        try await eventuallyExit { await gate.entered && transport.activeRequests == 0 }
        #expect(inbox.count == 0 && inbox.values.isEmpty)
        await #expect(throws: CapabilityWireError.self) { try await host.issueRequestID() }
        await gate.release()
        try await eventuallyExit { inbox.count == 1 && inbox.values.count == 1 }
        _ = try await nextExitID(host)
        await host.close()
    }

    @Test func cancellationAndDeadlineDeliverBeforeNativeExit() async throws {
        for deadline in [false, true] {
            let gate = ExitInvalidationGate(), inbox = ExitInbox()
            defer { gate.release() }
            let transport = try exitTransport(gate)
            let host = try CapabilityHost(policy: exitPolicy(), maximumRequests: 1, timeoutMilliseconds: deadline ? 30 : 1000,
                                          installedAdapters: InstalledCapabilityAdapters(http: transport))
            let call = exitCall(try await host.issueRequestID(), url: ExitFixtureProtocol.registry.install(stall: true))
            try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited)
            try await eventuallyExit { ExitFixtureProtocol.registry.started(callURL(call)) }
            if !deadline { try await host.submit(CapabilityCodec.encodeCancel(call), deliver: { _ in }) }
            try await eventuallyExit { inbox.values.count == 1 && gate.entered }
            #expect(try CapabilityCodec.decodeCompletion(#require(inbox.values.first), expected: call).outcome == .failure(deadline ? .deadlineExceeded : .cancelled))
            #expect(inbox.count == 0 && transport.activeRequests == 1)
            await #expect(throws: CapabilityWireError.self) { try await host.issueRequestID() }
            gate.release()
            try await eventuallyExit { inbox.count == 1 && transport.activeRequests == 0 }
            _ = try await nextExitID(host)
            #expect(inbox.values.count == 1 && !gate.timedOut)
            await host.close()
        }
    }

    @Test func redirectAndNativeFailureRetainExitLeaseUntilInvalidation() async throws {
        for redirect in [false, true] {
            let gate = ExitInvalidationGate(), inbox = ExitInbox()
            defer { gate.release() }
            let transport = try exitTransport(gate)
            let host = try CapabilityHost(policy: exitPolicy(), maximumRequests: 1, installedAdapters: InstalledCapabilityAdapters(http: transport))
            let url = ExitFixtureProtocol.registry.install(status: redirect ? 302 : 200, error: redirect ? nil : .cannotConnectToHost)
            let call = exitCall(try await host.issueRequestID(), url: url)
            try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited)
            try await eventuallyExit { inbox.values.count == 1 && gate.entered }
            #expect(try CapabilityCodec.decodeCompletion(#require(inbox.values.first), expected: call).outcome == .failure(redirect ? .redirectDenied : .ioFailure))
            #expect(inbox.count == 0 && transport.activeRequests == 1)
            await #expect(throws: CapabilityWireError.self) { try await host.issueRequestID() }
            gate.release()
            try await eventuallyExit { inbox.count == 1 && transport.activeRequests == 0 }
            _ = try await nextExitID(host)
            #expect(!gate.timedOut)
            await host.close()
        }
    }

    @Test func closeAndDeinitDoNotLoseExitObserverOrRetainHost() async throws {
        for explicitClose in [false, true] {
            let gate = ExitInvalidationGate(), inbox = ExitInbox()
            defer { gate.release() }
            let transport = try exitTransport(gate)
            var host: CapabilityHost? = try CapabilityHost(policy: exitPolicy(), installedAdapters: InstalledCapabilityAdapters(http: transport))
            let weakHost = ExitWeakHost(host)
            let call = exitCall(try await #require(host).issueRequestID(), url: ExitFixtureProtocol.registry.install(stall: true))
            try await #require(host).submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited)
            try await eventuallyExit { ExitFixtureProtocol.registry.started(callURL(call)) }
            if explicitClose { await host?.close() }
            host = nil
            try await eventuallyExit { weakHost.value == nil && gate.entered }
            #expect(inbox.count == 0 && transport.activeRequests == 1)
            #expect(inbox.values.count == (explicitClose ? 1 : 0))
            gate.release()
            try await eventuallyExit { inbox.count == 1 && transport.activeRequests == 0 }
            #expect(inbox.values.count == (explicitClose ? 1 : 0) && !gate.timedOut)
        }
    }

    @Test func transportPreflightQuotaAndCancelledAdmissionResolveObserver() async throws {
        let transport = try exitTransport(capacity: 1)
        let invalid = HTTPRequestArguments(url: "http://api.example.test/", method: "GET", headers: [], bodyBase64: "", timeoutMilliseconds: 1000)
        let invalidInbox = ExitInbox()
        await #expect(throws: CapabilityWireError.self) { try await transport.request(invalid, didExit: invalidInbox.exited) }
        #expect(invalidInbox.count == 1 && transport.activeRequests == 0)
        let clock = ExitAdmissionClock(), expiryInbox = ExitInbox()
        let expiring = try URLSessionHTTPTransport(maximumConcurrentRequests: 1, protocolClasses: [ExitFixtureProtocol.self], clock: clock.clock)
        let expiryURL = ExitFixtureProtocol.registry.install()
        let expiryArgs = HTTPRequestArguments(url: expiryURL, method: "GET", headers: [], bodyBase64: "", timeoutMilliseconds: 1000)
        await #expect(throws: CapabilityFailure.deadlineExceeded) { try await expiring.request(expiryArgs, didExit: expiryInbox.exited) }
        #expect(expiryInbox.count == 1 && expiring.activeRequests == 0 && !ExitFixtureProtocol.registry.started(expiryURL))
        let url = ExitFixtureProtocol.registry.install(stall: true)
        let args = HTTPRequestArguments(url: url, method: "GET", headers: [], bodyBase64: "", timeoutMilliseconds: 1000)
        let firstInbox = ExitInbox()
        let first = Task { try await transport.request(args, didExit: firstInbox.exited) }
        try await eventuallyExit { ExitFixtureProtocol.registry.started(url) }
        let quotaInbox = ExitInbox()
        await #expect(throws: CapabilityFailure.quotaExceeded) { try await transport.request(args, didExit: quotaInbox.exited) }
        #expect(quotaInbox.count == 1 && transport.activeRequests == 1)
        let cancellationGate = ExitInvocationGate(), cancelledInbox = ExitInbox()
        let cancelled = Task {
            await cancellationGate.hold()
            return try await transport.request(args, didExit: cancelledInbox.exited)
        }
        try await eventuallyExit { await cancellationGate.entered }
        cancelled.cancel(); await cancellationGate.release()
        await #expect(throws: CapabilityFailure.cancelled) { try await cancelled.value }
        #expect(cancelledInbox.count == 1)
        first.cancel()
        _ = try? await first.value
        try await eventuallyExit { firstInbox.count == 1 && transport.activeRequests == 0 }
    }

    @Test func serialStoreExitKeepsSharedStoreUsableAndCommittedDataVisible() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-exit-store-" + UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = try AppPrivateKeyValueStore(directory: directory, namespaces: ["entries"])
        let host = try CapabilityHost(policy: exitPolicy(), maximumRequests: 1, installedAdapters: InstalledCapabilityAdapters(storage: store))
        let data = Data("persisted".utf8).base64EncodedString()
        let operations: [CapabilityOperation] = [.put(KVPutArguments(namespace: "entries", key: "one", valueBase64: data)),
                                                .get(KVGetArguments(namespace: "entries", key: "one")),
                                                .delete(KVDeleteArguments(namespace: "entries", key: "one"))]
        var id = try await host.issueRequestID()
        for operation in operations {
            let inbox = ExitInbox(), call = CapabilityCall(identity: id, operation: operation)
            try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited)
            try await eventuallyExit { inbox.count == 1 && inbox.values.count == 1 }
            let result = try CapabilityCodec.decodeCompletion(#require(inbox.values.first), expected: call).outcome
            switch operation {
            case .get: #expect(result == .success(.get(KVGetResponse(found: true, valueBase64: data))))
            case .put: #expect(result == .success(.put(KVMutationResponse(committed: true))))
            case .delete: #expect(result == .success(.delete(KVMutationResponse(committed: true))))
            default: Issue.record("unexpected operation")
            }
            id = try await nextExitID(host)
        }
        await host.close()
        #expect(try await store.get(KVGetArguments(namespace: "entries", key: "one")).found == false)
        await store.close()
        let reopened = try AppPrivateKeyValueStore(directory: directory, namespaces: ["entries"])
        #expect(try await reopened.get(KVGetArguments(namespace: "entries", key: "one")).found == false)
        await reopened.close()
    }

    @Test func duplicateAndConcurrentLeaseReportsOnlyEmitJoinedExitOnce() async throws {
        for firstIsInvocation in [true, false] {
            let inbox = ExitInbox(), lease = CapabilityExitLease { _ in inbox.exited() }
            if firstIsInvocation { lease.invocationReturned() } else { lease.adapterExited() }
            #expect(inbox.count == 0)
            await withTaskGroup(of: Void.self) { group in
                for n in 0..<128 {
                    group.addTask { if n.isMultiple(of: 2) { lease.adapterExited() } else { lease.invocationReturned() } }
                }
            }
            #expect(inbox.count == 1)
        }
    }

    @Test func cancellationSuccessAndCloseRacesEmitOneExitPerAcceptedCall() async throws {
        let transport = try exitTransport()
        for _ in 0..<48 {
            let inbox = ExitInbox()
            let host = try CapabilityHost(policy: exitPolicy(), maximumRequests: 1, installedAdapters: InstalledCapabilityAdapters(http: transport))
            let call = exitCall(try await host.issueRequestID(), url: ExitFixtureProtocol.registry.install())
            try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: inbox.receive, didExit: inbox.exited)
            await withTaskGroup(of: Void.self) { group in
                group.addTask { try? await host.submit(CapabilityCodec.encodeCancel(call), deliver: { _ in }) }
                group.addTask { await host.close() }
            }
            try await eventuallyExit { inbox.count == 1 }
            #expect(inbox.values.count == 1)
        }
        try await eventuallyExit { transport.activeRequests == 0 }
    }
}
private func callURL(_ call: CapabilityCall) -> String {
    guard case .http(let arguments) = call.operation else { return "" }
    return arguments.url
}
#endif
