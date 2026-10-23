import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import Testing
@testable import MixerCapabilities
@testable import MixerExperimentalCapabilityRuntime

private final class BridgeInvalidationGate: @unchecked Sendable {
    private let condition = NSCondition()
    private var released = false
    private var began = false
    func hold() {
        condition.lock(); began = true
        let limit = Date().addingTimeInterval(5)
        while !released { if !condition.wait(until: limit) { break } }
        condition.unlock()
    }
    func release() { condition.lock(); released = true; condition.broadcast(); condition.unlock() }
    var entered: Bool { condition.lock(); defer { condition.unlock() }; return began }
}
private final class BridgeWeakSession {
    weak var value: ExperimentalCapabilitySession?
    init(_ value: ExperimentalCapabilitySession?) { self.value = value }
}
private final class BridgeHTTPFixtures: @unchecked Sendable {
    struct Value { let body: Data; let stall: Bool }
    private let values = Locked<[String: Value]>([:])
    func install(stall: Bool) -> String {
        let url = "https://api.example.test/bridge-" + UUID().uuidString.lowercased()
        values.withLock { $0[url] = Value(body: Data([0,1,254,255]), stall: stall) }; return url
    }
    func value(_ url: String) -> Value? { values.withLock { $0[url] } }
}
private final class BridgeInterceptedProtocol: URLProtocol {
    static let fixtures = BridgeHTTPFixtures()
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        guard let url = request.url, let value = Self.fixtures.value(url.absoluteString) else {
            client?.urlProtocol(self, didFailWithError: URLError(.badURL)); return
        }
        client?.urlProtocol(self, didReceive: HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: [:])!, cacheStoragePolicy: .notAllowed)
        if !value.stall { client?.urlProtocol(self, didLoad: value.body); client?.urlProtocolDidFinishLoading(self) }
    }
    override func stopLoading() {}
}
#if !canImport(FoundationNetworking)
extension BridgeInterceptedProtocol: @unchecked Sendable {}
#endif

private func httpBridge(_ url: String, transport: URLSessionHTTPTransport, timeout: UInt32,
                        hostTimeout: UInt32 = 30000, allow: Bool = true) async throws -> ExperimentalCapabilitySession {
    let origin = String(url.prefix { $0 != "?" }.split(separator: "/", omittingEmptySubsequences: false).prefix(3).joined(separator: "/"))
    let grant = CapabilityGrant(capabilityID: CapabilitySchemas.httpID, schemaSHA256: CapabilitySchemas.httpSHA256,
                                permissions: ["network.https"], origins: [origin], methods: ["GET"])
    let policy = try CapabilityPolicy(installed: [grant], manifest: allow ? [grant] : [])
    let arguments = try GuestCapabilityTransportCodecV1.encodeArguments(.http(HTTPRequestArguments(url: url, method: "GET", headers: [], bodyBase64: "", timeoutMilliseconds: timeout)))
    return try await ExperimentalCapabilitySession.prepare(module: GuestProgram.build(.single(0,arguments)), startupExport: "boot",
        configuration: .init(timeoutMilliseconds: hostTimeout), policy: policy, adapters: InstalledCapabilityAdapters(http: transport)).create()
}

extension ExperimentalBridgeTests {
    @Test func publicOwnerDeinitRetainsActualNativeExitAndConstructionBudget() async throws {
        let gate = BridgeInvalidationGate(); defer { gate.release() }
        let transport = try URLSessionHTTPTransport(maximumConcurrentRequests: 8, protocolClasses: [BridgeInterceptedProtocol.self], beforeInvalidation: { gate.hold() })
        var session: ExperimentalCapabilitySession? = try await httpBridge(BridgeInterceptedProtocol.fixtures.install(stall: true), transport: transport, timeout: 50)
        let weakSession = BridgeWeakSession(session)
        _ = try await session!.startup(); try await session!.enableEffects(); _ = try await session!.invoke("run")
        try await bridgeEventually { gate.entered && transport.activeRequests == 1 }
        session!.close(); session = nil
        #expect(weakSession.value == nil)
        let policy = try CapabilityPolicy(installed: [], manifest: [])
        var held: [ExperimentalCapabilityConstruction] = []
        for _ in 0..<15 { held.append(try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())) }
        #expect(throws: ExperimentalCapabilityError("construction_busy")) {
            try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
        }
        gate.release()
        var reclaimed: ExperimentalCapabilityConstruction?
        try await bridgeEventually {
            reclaimed = try? ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "boot", policy: policy, adapters: InstalledCapabilityAdapters())
            return reclaimed != nil
        }
        #expect(transport.activeRequests == 0)
        reclaimed?.cancel(); held.removeAll()
    }
    @Test func interceptedHTTPUsesRealHostAdapterAndStrictGuestConversion() async throws {
        // Framework interception, deliberately not a real-network success claim.
        let url = BridgeInterceptedProtocol.fixtures.install(stall: false)
        let transport = try URLSessionHTTPTransport(maximumConcurrentRequests: 8, protocolClasses: [BridgeInterceptedProtocol.self])
        let session = try await httpBridge(url, transport: transport, timeout: 2000)
        _ = try await session.startup(); try await session.enableEffects(); _ = try await session.invoke("run")
        try await bridgeEventually { try await session.invoke("stage").value == .i32(5) }
        guard case .success(.http(let response)) = try await guestOutcome(session, stage: 1, operation: .httpRequest) else { Issue.record("missing typed HTTP success"); session.close(); return }
        #expect(response.status == 200 && response.bodyBase64 == "AAH+/w==")
        session.close(); try await bridgeEventually { session.status.drained }
        #expect(transport.activeRequests == 0 && session.status.acknowledgements == 1)
    }
    @Test func HTTPEnqueueTimeoutAndHostCapDeliverBeforeNativeExit() async throws {
        for (httpTimeout, hostTimeout) in [(UInt32(50),UInt32(2000)),(UInt32(2000),UInt32(50))] {
            let gate = BridgeInvalidationGate(); defer { gate.release() }
            let transport = try URLSessionHTTPTransport(maximumConcurrentRequests: 8, protocolClasses: [BridgeInterceptedProtocol.self], beforeInvalidation: { gate.hold() })
            let session = try await httpBridge(BridgeInterceptedProtocol.fixtures.install(stall: true), transport: transport, timeout: httpTimeout, hostTimeout: hostTimeout)
            _ = try await session.startup(); try await session.enableEffects(); _ = try await session.invoke("run")
            try await bridgeEventually { try await session.invoke("stage").value == .i32(5) }
            #expect(try await guestOutcome(session, stage: 1, operation: .httpRequest) == .failure(.deadlineExceeded))
            try await bridgeEventually { gate.entered }
            #expect(session.status.retainedExits == 1 && transport.activeRequests == 1)
            session.close()
            try await Task.sleep(for: .milliseconds(15))
            #expect(!session.status.drained)
            gate.release(); try await bridgeEventually { session.status.drained }
            #expect(transport.activeRequests == 0 && session.status.acknowledgements == 1)
        }
    }
    @Test func policyDeniedInlineCallbacksStillResolveOneTakenExit() async throws {
        let transport = try URLSessionHTTPTransport()
        let session = try await httpBridge("https://api.example.test/denied", transport: transport, timeout: 2000, allow: false)
        _ = try await session.startup(); try await session.enableEffects(); _ = try await session.invoke("run")
        try await bridgeEventually { try await session.invoke("stage").value == .i32(5) }
        #expect(try await guestOutcome(session, stage: 1, operation: .httpRequest) == .failure(.permissionDenied))
        session.close(); try await bridgeEventually { session.status.drained }
        #expect(transport.activeRequests == 0 && session.status.acknowledgements == 1)
    }
    #if os(macOS) && MIXER_EXPERIMENTAL_LOCAL_TLS_TEST
    @Test func realWasmNormalTrustRejectsActualLoopbackTLSCertificate() async throws {
        let url = try #require(ProcessInfo.processInfo.environment["MIXER_EXPERIMENTAL_TLS_URL"])
        let transport = try URLSessionHTTPTransport()
        let session = try await httpBridge(url, transport: transport, timeout: 3000)
        _ = try await session.startup(); try await session.enableEffects(); _ = try await session.invoke("run")
        try await bridgeEventually { try await session.invoke("stage").value == .i32(5) }
        #expect(try await guestOutcome(session, stage: 1, operation: .httpRequest) == .failure(.ioFailure))
        session.close(); try await bridgeEventually { session.status.drained }
        #expect(transport.activeRequests == 0 && session.status.acknowledgements == 1)
    }
    #endif
}
