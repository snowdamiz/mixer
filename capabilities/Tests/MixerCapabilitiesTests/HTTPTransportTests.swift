import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import Testing
@testable import MixerCapabilities

#if !os(WASI)
// URLProtocol replaces network I/O only inside this test module. Production has
// no session/trust/protocol injection API; these cases do not qualify wire TLS.
private struct HTTPFixture: Sendable {
    var status = 200
    var headers: [String: String] = [:]
    var chunks: [Data] = []
    var stall = false
    var error: URLError.Code?
    var nonHTTP = false
    var beforeResponse: (@Sendable () -> Void)?
}
private final class HTTPFixtureRegistry: @unchecked Sendable {
    private let lock = NSLock()
    private var fixtures: [String: HTTPFixture] = [:]
    private var requests: [String: [URLRequest]] = [:]
    private var stops: [String: Int] = [:]
    func install(_ fixture: HTTPFixture) -> String {
        let url = "https://api.example.test/" + UUID().uuidString.lowercased()
        lock.lock(); fixtures[url] = fixture; lock.unlock()
        return url
    }
    func begin(_ request: URLRequest) -> HTTPFixture? {
        let url = request.url!.absoluteString
        lock.lock(); defer { lock.unlock() }
        requests[url, default: []].append(request)
        return fixtures[url]
    }
    func stopped(_ url: String) { lock.lock(); stops[url, default: 0] += 1; lock.unlock() }
    func observed(_ url: String) -> [URLRequest] { lock.lock(); defer { lock.unlock() }; return requests[url] ?? [] }
    func stopCount(_ url: String) -> Int { lock.lock(); defer { lock.unlock() }; return stops[url] ?? 0 }
}
private final class HTTPFixtureProtocol: URLProtocol {
    static let registry = HTTPFixtureRegistry()
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        guard let fixture = Self.registry.begin(request), let url = request.url else {
            client?.urlProtocol(self, didFailWithError: URLError(.badURL)); return
        }
        if let error = fixture.error { client?.urlProtocol(self, didFailWithError: URLError(error)); return }
        let response: URLResponse = fixture.nonHTTP
            ? URLResponse(url: url, mimeType: nil, expectedContentLength: -1, textEncodingName: nil)
            : HTTPURLResponse(url: url, statusCode: fixture.status, httpVersion: "HTTP/1.1", headerFields: fixture.headers)!
        fixture.beforeResponse?()
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        for chunk in fixture.chunks { client?.urlProtocol(self, didLoad: chunk) }
        if !fixture.stall { client?.urlProtocolDidFinishLoading(self) }
    }
    override func stopLoading() { Self.registry.stopped(request.url!.absoluteString) }
}
#if !canImport(FoundationNetworking)
extension HTTPFixtureProtocol: @unchecked Sendable {}
#endif
private func nativeTransport(capacity: Int = 64, clock: HTTPTransportClock = .continuous) throws -> URLSessionHTTPTransport {
    try URLSessionHTTPTransport(maximumConcurrentRequests: capacity, protocolClasses: [HTTPFixtureProtocol.self], clock: clock)
}
private func httpArguments(_ url: String, method: String = "GET", headers: [Header] = [], body: Data = Data(), timeout: UInt32 = 1000) -> HTTPRequestArguments {
    HTTPRequestArguments(url: url, method: method, headers: headers, bodyBase64: body.base64EncodedString(), timeoutMilliseconds: timeout)
}
private func eventuallyHTTP(_ predicate: () -> Bool) async throws {
    for _ in 0..<400 {
        if predicate() { return }
        try await Task.sleep(nanoseconds: 5_000_000)
    }
    try #require(predicate(), "native transport did not acknowledge bounded cleanup")
}
private func requireHTTPFailure(_ expected: CapabilityFailure, transport: URLSessionHTTPTransport, arguments: HTTPRequestArguments) async {
    do { _ = try await transport.request(arguments); Issue.record("expected native HTTP failure \(expected)") }
    catch let actual as CapabilityFailure { #expect(actual == expected) }
    catch { Issue.record("unexpected native HTTP error \(error)") }
}
private final class NativeHTTPInbox: @unchecked Sendable {
    private let lock = NSLock()
    private var values: [Data] = []
    func receive(_ value: Data) { lock.lock(); values.append(value); lock.unlock() }
    func snapshot() -> [Data] { lock.lock(); defer { lock.unlock() }; return values }
}
private final class HeldWatchdogClock: @unchecked Sendable {
    private let lock = NSLock()
    private var instant = ContinuousClock.now
    private var expireOnRead = false
    func expireAfterNextRead() { lock.lock(); expireOnRead = true; lock.unlock() }
    func now() -> ContinuousClock.Instant {
        lock.lock(); defer { lock.unlock() }
        let value = instant
        if expireOnRead { instant = instant.advanced(by: .seconds(60)); expireOnRead = false }
        return value
    }
    var clock: HTTPTransportClock {
        HTTPTransportClock(now: { self.now() }, sleepUntil: { _ in
            // A scheduler-delayed watchdog cannot authorize a late success.
            try await Task.sleep(nanoseconds: 60_000_000_000)
        })
    }
}

@Suite(.serialized)
struct NativeHTTPTransportTests {
    @Test func privateConfigurationHasNoAmbientAuthority() throws {
        let transport = try URLSessionHTTPTransport()
        let configuration = transport.configuration(timeoutMilliseconds: 50)
        #expect(configuration.urlCache == nil)
        #expect(configuration.urlCredentialStorage == nil)
        #expect(configuration.httpCookieStorage == nil)
        #expect(!configuration.httpShouldSetCookies)
        #expect(configuration.httpCookieAcceptPolicy == .never)
        #expect(configuration.requestCachePolicy == .reloadIgnoringLocalCacheData)
        #expect(configuration.protocolClasses?.contains(where: { $0 == HTTPFixtureProtocol.self }) != true)
        #expect(configuration.httpAdditionalHeaders?.isEmpty == true)
        #expect(configuration.timeoutIntervalForResource == 0.05)
        for capacity in [0, -1, 257, Int.max] {
            #expect(throws: CapabilityWireError.self) { try URLSessionHTTPTransport(maximumConcurrentRequests: capacity) }
        }
    }

    @Test func directTypedInputsAreValidatedBeforeAnyTaskIsCreated() async throws {
        let transport = try nativeTransport()
        let url = HTTPFixtureProtocol.registry.install(HTTPFixture())
        let invalid = [
            httpArguments(url.replacingOccurrences(of: "https:", with: "http:")),
            httpArguments("https://u@api.example.test/"),
            httpArguments(url, method: "CONNECT"),
            httpArguments(url, method: "get"),
            httpArguments(url, headers: [Header(name: "cookie", value: "secret")]),
            httpArguments(url, headers: [Header(name: "x-a", value: "a"), Header(name: "x-a", value: "b")]),
            httpArguments(url, headers: [Header(name: "x-a", value: "x\r\ny")]),
            httpArguments(url, headers: [Header(name: "x-a", value: String(repeating: "x", count: 4097))]),
            httpArguments(url, headers: (0..<33).map { Header(name: "x-\($0)", value: "a") }),
            httpArguments(url, body: Data(repeating: 1, count: 65537)),
            httpArguments(url, timeout: 0), httpArguments(url, timeout: 30001),
            HTTPRequestArguments(url: url, method: "GET", headers: [], bodyBase64: "Zh==", timeoutMilliseconds: 1),
            httpArguments("https://api.example.test/" + String(repeating: "x", count: 4096))
        ]
        for arguments in invalid {
            await #expect(throws: CapabilityWireError.self) { try await transport.request(arguments) }
        }
        #expect(HTTPFixtureProtocol.registry.observed(url).isEmpty)
        #expect(transport.activeRequests == 0)
    }

    @Test func exactBodyBoundsExplicitRequestAndFilteredResponse() async throws {
        let transport = try nativeTransport()
        let bytes = Data(repeating: 0xa5, count: 262144)
        let chunks = stride(from: 0, to: bytes.count, by: 16384).map { bytes.subdata(in: $0..<min($0 + 16384, bytes.count)) }
        let url = HTTPFixtureProtocol.registry.install(HTTPFixture(headers: ["Content-Length": "262144", "Set-Cookie": "ambient=denied", "Connection": "close", "X-Reply": "yes"], chunks: chunks))
        let body = Data(repeating: 0x5a, count: 65536)
        let response = try await transport.request(httpArguments(url, method: "POST", headers: [Header(name: "authorization", value: "Bearer explicit-fixture")], body: body))
        #expect(Data(base64Encoded: response.bodyBase64) == bytes)
        #expect(response.status == 200)
        #expect(response.headers == [Header(name: "x-reply", value: "yes")])
        let request = try #require(HTTPFixtureProtocol.registry.observed(url).only)
        #expect(request.httpMethod == "POST")
        // URLProtocol may expose a body stream instead of body Data on some OSes.
        if let retained = request.httpBody { #expect(retained == body) }
        #expect(request.value(forHTTPHeaderField: "Authorization") == "Bearer explicit-fixture")
        #expect(request.value(forHTTPHeaderField: "Accept-Encoding") == "identity")
        #expect(request.value(forHTTPHeaderField: "User-Agent") == "MixerCapabilitiesHTTP/1")
        #expect(request.value(forHTTPHeaderField: "Accept-Language") ?? "" == "")
        #expect(request.value(forHTTPHeaderField: "Cookie") == nil)
        #expect(!request.httpShouldHandleCookies)
        try await eventuallyHTTP { transport.activeRequests == 0 }
    }

    @Test func zeroBodyHeadAndNoContentAreNotInventedPayloads() async throws {
        let transport = try nativeTransport()
        for (method, status, length) in [("GET", 200, "0"), ("GET", 204, "0"), ("HEAD", 200, "9999999999999999999")] {
            let url = HTTPFixtureProtocol.registry.install(HTTPFixture(status: status, headers: ["Content-Length": length]))
            let response = try await transport.request(httpArguments(url, method: method))
            #expect(response.bodyBase64.isEmpty)
            #expect(response.status == status)
        }
        try await eventuallyHTTP { transport.activeRequests == 0 }
    }

    @Test func deceptiveAndOversizedLengthsNeverBecomeSuccessfulBodies() async throws {
        let transport = try nativeTransport()
        let cases: [(HTTPFixture, CapabilityFailure)] = [
            (HTTPFixture(headers: ["Content-Length": "262145"]), .quotaExceeded),
            (HTTPFixture(headers: ["Content-Length": "0"], chunks: [Data([1])]), .invalidResponse),
            (HTTPFixture(headers: ["Content-Length": "3"], chunks: [Data([1, 2])]), .invalidResponse),
            (HTTPFixture(headers: ["Content-Length": "1"], chunks: [Data([1, 2])]), .invalidResponse),
            (HTTPFixture(headers: ["Content-Length": "-1"]), .invalidResponse),
            (HTTPFixture(headers: ["Content-Length": "1, 1"]), .invalidResponse),
            (HTTPFixture(headers: ["Content-Length": "18446744073709551616"]), .invalidResponse),
            (HTTPFixture(chunks: [Data(repeating: 0, count: 262144), Data([1])]), .quotaExceeded),
            (HTTPFixture(chunks: [Data(repeating: 0, count: 262145)]), .quotaExceeded),
            (HTTPFixture(status: 204, chunks: [Data([1])]), .invalidResponse)
        ]
        for (fixture, expected) in cases {
            let url = HTTPFixtureProtocol.registry.install(fixture)
            await requireHTTPFailure(expected, transport: transport, arguments: httpArguments(url))
            try await eventuallyHTTP { transport.activeRequests == 0 }
            #expect(HTTPFixtureProtocol.registry.observed(url).count == 1)
        }
    }

    @Test func redirectsMalformedHeadersCompressionAndNativeErrorsFailClosed() async throws {
        let transport = try nativeTransport()
        let cases: [(HTTPFixture, CapabilityFailure)] = [
            (HTTPFixture(status: 302, headers: ["Location": "https://other.example.test/"]), .redirectDenied),
            (HTTPFixture(status: 304), .redirectDenied),
            (HTTPFixture(status: 199), .invalidResponse),
            (HTTPFixture(headers: ["X_Bad": "x"]), .invalidResponse),
            (HTTPFixture(headers: ["X-Value": String(repeating: "x", count: 4097)]), .invalidResponse),
            (HTTPFixture(headers: Dictionary(uniqueKeysWithValues: (0..<33).map { ("X-\($0)", "x") })), .invalidResponse),
            (HTTPFixture(headers: ["Content-Encoding": "gzip"], chunks: [Data([1, 2])]), .invalidResponse),
            (HTTPFixture(error: .cannotConnectToHost), .ioFailure),
            (HTTPFixture(error: .timedOut), .deadlineExceeded),
            (HTTPFixture(nonHTTP: true), .invalidResponse)
        ]
        for (fixture, expected) in cases {
            let url = HTTPFixtureProtocol.registry.install(fixture)
            await requireHTTPFailure(expected, transport: transport, arguments: httpArguments(url))
            try await eventuallyHTTP { transport.activeRequests == 0 }
            #expect(HTTPFixtureProtocol.registry.observed(url).count == 1)
        }
    }

    @Test func cancellationDeadlineAndQuotaReleaseTheirNativeTasks() async throws {
        let transport = try nativeTransport(capacity: 1)
        let url = HTTPFixtureProtocol.registry.install(HTTPFixture(stall: true))
        let pending = Task { try await transport.request(httpArguments(url)) }
        try await eventuallyHTTP { !HTTPFixtureProtocol.registry.observed(url).isEmpty }
        #expect(transport.activeRequests == 1)
        await requireHTTPFailure(.quotaExceeded, transport: transport, arguments: httpArguments(url))
        pending.cancel()
        do { _ = try await pending.value; Issue.record("cancelled HTTP task succeeded") }
        catch let failure as CapabilityFailure { #expect(failure == .cancelled) }
        try await eventuallyHTTP { transport.activeRequests == 0 && HTTPFixtureProtocol.registry.stopCount(url) == 1 }
        #expect(HTTPFixtureProtocol.registry.observed(url).count == 1)
        let deadline = HTTPFixtureProtocol.registry.install(HTTPFixture(stall: true))
        await requireHTTPFailure(.deadlineExceeded, transport: transport, arguments: httpArguments(deadline, timeout: 30))
        try await eventuallyHTTP { transport.activeRequests == 0 && HTTPFixtureProtocol.registry.stopCount(deadline) == 1 }
        let success = HTTPFixtureProtocol.registry.install(HTTPFixture())
        #expect(try await transport.request(httpArguments(success)).status == 200)
        try await eventuallyHTTP { transport.activeRequests == 0 }
    }

    @Test func cancellationSuccessRaceCannotLeakOrDoubleResume() async throws {
        let transport = try nativeTransport()
        var started = 0
        for index in 0..<100 {
            let url = HTTPFixtureProtocol.registry.install(HTTPFixture(chunks: [Data([1])], stall: index % 3 == 2))
            let task = Task { try await transport.request(httpArguments(url)) }
            if index % 3 != 0 {
                try await eventuallyHTTP { !HTTPFixtureProtocol.registry.observed(url).isEmpty }
                started += 1
            }
            task.cancel()
            do { let response = try await task.value; #expect(response.bodyBase64 == "AQ==") }
            catch let failure as CapabilityFailure { #expect(failure == .cancelled) }
        }
        #expect(started == 66)
        try await eventuallyHTTP { transport.activeRequests == 0 }
    }

    @Test func lateSuccessFailsEvenWhenWatchdogHasNotRun() async throws {
        let clock = HeldWatchdogClock()
        let transport = try nativeTransport(clock: clock.clock)
        // Arm at native response delivery. Its admission check sees the old
        // instant; completion sees expiry while the watchdog is still held.
        let url = HTTPFixtureProtocol.registry.install(HTTPFixture(beforeResponse: { clock.expireAfterNextRead() }))
        await requireHTTPFailure(.deadlineExceeded, transport: transport, arguments: httpArguments(url))
        try await eventuallyHTTP { transport.activeRequests == 0 }
        #expect(HTTPFixtureProtocol.registry.observed(url).count == 1)
    }

    @Test func deadlineIncludesPreflightAndRejectsExpiredAdmissionWithoutIO() async throws {
        let clock = HeldWatchdogClock()
        clock.expireAfterNextRead()
        let transport = try nativeTransport(clock: clock.clock)
        let url = HTTPFixtureProtocol.registry.install(HTTPFixture())
        await requireHTTPFailure(.deadlineExceeded, transport: transport, arguments: httpArguments(url))
        #expect(HTTPFixtureProtocol.registry.observed(url).isEmpty)
        #expect(transport.activeRequests == 0)
    }

    @Test func installedHostHookAuthorizesBeforeIOAndOwnsCancellationCompletion() async throws {
        let grant = CapabilityGrant(capabilityID: CapabilitySchemas.httpID, schemaSHA256: CapabilitySchemas.httpSHA256,
                                    permissions: ["network.https"], origins: ["https://api.example.test"], methods: ["GET"])
        let transport = try nativeTransport()
        let host = try CapabilityHost(policy: CapabilityPolicy(installed: [grant], manifest: [grant]), http: { try await transport.request($0) })
        let deniedURL = HTTPFixtureProtocol.registry.install(HTTPFixture())
        let denied = CapabilityCall(identity: try await host.issueRequestID(), operation: .http(httpArguments(deniedURL, method: "POST")))
        let inbox = NativeHTTPInbox()
        try await host.submit(CapabilityCodec.encodeCall(denied), deliver: inbox.receive)
        try await eventuallyHTTP { inbox.snapshot().count == 1 }
        #expect(try CapabilityCodec.decodeCompletion(#require(inbox.snapshot().first), expected: denied).outcome == .failure(.permissionDenied))
        #expect(HTTPFixtureProtocol.registry.observed(deniedURL).isEmpty)
        let url = HTTPFixtureProtocol.registry.install(HTTPFixture(stall: true))
        let call = CapabilityCall(identity: try await host.issueRequestID(), operation: .http(httpArguments(url)))
        try await host.submit(CapabilityCodec.encodeCall(call), deliver: inbox.receive)
        try await eventuallyHTTP { !HTTPFixtureProtocol.registry.observed(url).isEmpty }
        try await host.submit(CapabilityCodec.encodeCancel(call), deliver: { _ in Issue.record("cancellation replaced original delivery owner") })
        try await eventuallyHTTP { inbox.snapshot().count == 2 && transport.activeRequests == 0 }
        #expect(try CapabilityCodec.decodeCompletion(#require(inbox.snapshot().last), expected: call).outcome == .failure(.cancelled))
        await host.close()
        try await Task.sleep(nanoseconds: 20_000_000)
        #expect(inbox.snapshot().count == 2)
        #expect(HTTPFixtureProtocol.registry.observed(url).count == 1)
    }
}

#if os(macOS) && MIXER_HTTP_LOCAL_TLS_TEST
@Test func systemTLSRejectsUntrustedLocalCertificate() async throws {
    // Only the evidence runner enables this test while owning an isolated local
    // TLS server. No trust store is modified and no trust override is installed.
    let url = try #require(ProcessInfo.processInfo.environment["MIXER_HTTP_UNTRUSTED_TLS_URL"])
    let transport = try URLSessionHTTPTransport()
    await requireHTTPFailure(.ioFailure, transport: transport, arguments: httpArguments(url, timeout: 3000))
    try await eventuallyHTTP { transport.activeRequests == 0 }
}
#endif
private extension Array { var only: Element? { count == 1 ? first : nil } }
#endif
