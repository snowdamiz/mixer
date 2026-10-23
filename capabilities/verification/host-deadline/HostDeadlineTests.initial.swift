import Foundation
import Testing
import MixerCapabilities

private final class DeadlineInbox: @unchecked Sendable {
    private let lock = NSLock()
    private var deliveries: [Data] = []
    func receive(_ data: Data) { lock.lock(); deliveries.append(data); lock.unlock() }
    var values: [Data] { lock.lock(); defer { lock.unlock() }; return deliveries }
}

// Intentionally models delayed actor scheduling with a slow synchronous callback.
// A bounded escape and unconditional release prevent a failing test from hanging.
private final class DeadlineDeliveryGate: @unchecked Sendable {
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

private actor DeadlineResponses {
    private var waiters: [String: CheckedContinuation<HTTPResponse, Never>] = [:]
    func request(_ arguments: HTTPRequestArguments) async -> HTTPResponse {
        await withCheckedContinuation { waiters[arguments.url] = $0 }
    }
    func has(_ url: String) -> Bool { waiters[url] != nil }
    func finish(_ url: String) { waiters.removeValue(forKey: url)?.resume(returning: HTTPResponse(status: 200, headers: [], bodyBase64: "")) }
    func finishAll() {
        let pending = waiters; waiters.removeAll()
        for waiter in pending.values { waiter.resume(returning: HTTPResponse(status: 200, headers: [], bodyBase64: "")) }
    }
}

private func deadlineEventually(_ condition: () async -> Bool) async throws {
    for _ in 0..<400 {
        if await condition() { return }
        try await Task.sleep(nanoseconds: 5_000_000)
    }
    try #require(await condition(), "deadline test did not reach its bounded transition")
}

@Suite(.serialized)
struct CapabilityHostDeadlineTests {
    @Test func delayedActorRejectsLateResultAndPreservesEarlierSuccess() async throws {
        let grant = CapabilityGrant(capabilityID: CapabilitySchemas.httpID, schemaSHA256: CapabilitySchemas.httpSHA256,
                                    permissions: ["network.https"], origins: ["https://api.example.test"], methods: ["GET"])
        let policy = try CapabilityPolicy(installed: [grant], manifest: [grant])
        let responses = DeadlineResponses()
        let host = try CapabilityHost(policy: policy, maximumRequests: 2, timeoutMilliseconds: 1000,
                                      http: { await responses.request($0) })
        let first = DeadlineInbox(), late = DeadlineInbox(), delivery = DeadlineDeliveryGate()
        defer {
            delivery.release()
            Task { await responses.finishAll(); await host.close() }
        }
        func call(_ identity: CapabilityRequestID, suffix: String) -> CapabilityCall {
            CapabilityCall(identity: identity, operation: .http(HTTPRequestArguments(
                url: "https://api.example.test/" + suffix, method: "GET", headers: [], bodyBase64: "", timeoutMilliseconds: 5000)))
        }
        let earlyCall = call(try await host.issueRequestID(), suffix: "early")
        let lateCall = call(try await host.issueRequestID(), suffix: "late")
        try await host.submit(CapabilityCodec.encodeCall(earlyCall), deliver: { first.receive($0); delivery.hold() })
        try await host.submit(CapabilityCodec.encodeCall(lateCall), deliver: late.receive)
        let admittedBy = ContinuousClock.now
        try await deadlineEventually { await responses.has("https://api.example.test/early") && responses.has("https://api.example.test/late") }
        await responses.finish("https://api.example.test/early")
        try await deadlineEventually { delivery.entered }
        #expect(try CapabilityCodec.decodeCompletion(#require(first.values.first), expected: earlyCall).outcome == .success(.http(HTTPResponse(status: 200, headers: [], bodyBase64: ""))))
        await responses.finish("https://api.example.test/late")
        // Both the result and watchdog may now be ready, but neither can enter
        // the actor until after the host's narrowed (not HTTP's5000ms) deadline.
        try await ContinuousClock().sleep(until: admittedBy.advanced(by: .milliseconds(1200)))
        #expect(late.values.isEmpty)
        delivery.release()
        try await deadlineEventually { late.values.count == 1 }
        #expect(try CapabilityCodec.decodeCompletion(#require(late.values.first), expected: lateCall).outcome == .failure(.deadlineExceeded))
        #expect(first.values.count == 1)
        #expect(!delivery.timedOut)
        await host.close()
        #expect(late.values.count == 1)
    }
}
