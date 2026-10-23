#if !os(WASI)
import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// An explicitly installed native HTTP adapter. Grant authorization belongs to
/// CapabilityHost; this type is not a grant, signature verifier or guest import.
/// Each request uses one ephemeral session and normal system TLS validation.
public final class URLSessionHTTPTransport: BoundedHTTPServing, @unchecked Sendable {
    private let leases: HTTPTransportLeases
    private let protocolClasses: [AnyClass]?
    private let clock: HTTPTransportClock

    public convenience init(maximumConcurrentRequests: Int = 64) throws {
        try self.init(maximumConcurrentRequests: maximumConcurrentRequests, protocolClasses: nil)
    }

    // Native test seam only. Public callers cannot supply a session, delegate,
    // credential store, URL protocol, certificate or trust-evaluation override.
    init(maximumConcurrentRequests: Int, protocolClasses: [AnyClass]?, clock: HTTPTransportClock = .continuous) throws {
        guard (1...256).contains(maximumConcurrentRequests) else { throw CapabilityWireError.invalid("HTTP concurrency") }
        leases = HTTPTransportLeases(capacity: maximumConcurrentRequests)
        self.protocolClasses = protocolClasses
        self.clock = clock
    }

    public func request(_ arguments: HTTPRequestArguments) async throws -> HTTPResponse {
        let deadline = clock.now().advanced(by: .milliseconds(Int64(arguments.timeoutMilliseconds)))
        guard arguments.url.utf8.prefix(4097).count <= 4096, arguments.method.utf8.prefix(7).count <= 6,
              arguments.bodyBase64.utf8.prefix(87385).count <= 87384, arguments.headers.count <= 32,
              arguments.headers.allSatisfy({ $0.name.utf8.prefix(65).count <= 64 && $0.value.utf8.prefix(4097).count <= 4096 }) else {
            throw CapabilityWireError.invalid("HTTP request bounds")
        }
        _ = try HTTPRequestArguments(wire: arguments.wire)
        guard let url = URL(string: arguments.url), url.scheme == "https", url.absoluteString == arguments.url else {
            throw CapabilityWireError.invalid("HTTP URL representation")
        }
        guard !Task.isCancelled else { throw CapabilityFailure.cancelled }
        guard clock.now() < deadline else { throw CapabilityFailure.deadlineExceeded }
        try leases.acquire()
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData,
                                 timeoutInterval: Double(arguments.timeoutMilliseconds) / 1000)
        request.httpMethod = arguments.method
        request.httpShouldHandleCookies = false
        for header in arguments.headers { request.setValue(header.value, forHTTPHeaderField: header.name) }
        // Avoid ambient locale/user-agent disclosure and transparent compression.
        // Explicit guest values remain explicit; encoded responses are rejected.
        if request.value(forHTTPHeaderField: "Accept-Encoding") == nil { request.setValue("identity", forHTTPHeaderField: "Accept-Encoding") }
        if request.value(forHTTPHeaderField: "Accept-Language") == nil { request.setValue("", forHTTPHeaderField: "Accept-Language") }
        if request.value(forHTTPHeaderField: "User-Agent") == nil { request.setValue("MixerCapabilitiesHTTP/1", forHTTPHeaderField: "User-Agent") }
        if !arguments.bodyBase64.isEmpty { request.httpBody = Data(base64Encoded: arguments.bodyBase64)! }
        let exchange = HTTPTransportExchange(request: request, deadline: deadline, clock: clock,
                                             configuration: configuration(timeoutMilliseconds: arguments.timeoutMilliseconds), leases: leases)
        return try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { exchange.start($0) }
        } onCancel: {
            exchange.fail(.cancelled)
        }
    }

    func configuration(timeoutMilliseconds: UInt32) -> URLSessionConfiguration {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.urlCache = nil
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.urlCredentialStorage = nil
        configuration.httpCookieStorage = nil
        configuration.httpShouldSetCookies = false
        configuration.httpCookieAcceptPolicy = .never
        configuration.httpAdditionalHeaders = [:]
        configuration.httpMaximumConnectionsPerHost = 1
        configuration.timeoutIntervalForRequest = Double(timeoutMilliseconds) / 1000
        configuration.timeoutIntervalForResource = Double(timeoutMilliseconds) / 1000
        if let protocolClasses { configuration.protocolClasses = protocolClasses }
        return configuration
    }

    // Read-only internal test observation. A cancelled operation retains this
    // native lease until URLSession acknowledges invalidation, not merely until
    // the awaiting Swift task receives its terminal result.
    var activeRequests: Int { leases.count }
}

// Internal deterministic test seam. Production always uses ContinuousClock; no
// external caller can alter either deadline authority or watchdog scheduling.
struct HTTPTransportClock: Sendable {
    let now: @Sendable () -> ContinuousClock.Instant
    let sleepUntil: @Sendable (ContinuousClock.Instant) async throws -> Void
    static let continuous = HTTPTransportClock(now: { ContinuousClock.now }, sleepUntil: { try await ContinuousClock().sleep(until: $0) })
}

// @unchecked Sendable protects only the counter, using one lock. No URLSession
// callbacks, continuations or application code run while this lock is held.
private final class HTTPTransportLeases: @unchecked Sendable {
    private let lock = NSLock()
    private let capacity: Int
    private var active = 0
    init(capacity: Int) { self.capacity = capacity }
    var count: Int { lock.lock(); defer { lock.unlock() }; return active }
    func acquire() throws {
        lock.lock(); defer { lock.unlock() }
        guard active < capacity else { throw CapabilityFailure.quotaExceeded }
        active += 1
    }
    func release() { lock.lock(); defer { lock.unlock() }; precondition(active > 0); active -= 1 }
}

// The lock protects all request state against cancellation/timer/delegate races.
// URLSession owns its delegate until invalidation; invalidation breaks our session
// reference and releases the native lease exactly once. Delegate delivery is serial.
private final class HTTPTransportExchange: NSObject, URLSessionDataDelegate, @unchecked Sendable {
    private static let maximumBodyBytes = 262144
    private static let strippedHeaders: Set<String> = ["host", "connection", "content-length", "transfer-encoding", "proxy-authorization", "proxy-authenticate", "cookie", "set-cookie", "keep-alive", "te", "trailer", "upgrade"]
    private let lock = NSLock()
    private let request: URLRequest
    private let deadline: ContinuousClock.Instant
    private let clock: HTTPTransportClock
    private let configuration: URLSessionConfiguration
    private let leases: HTTPTransportLeases
    private var session: URLSession?
    private var task: URLSessionDataTask?
    private var timer: Task<Void, Never>?
    private var continuation: CheckedContinuation<HTTPResponse, any Error>?
    private var terminal: Result<HTTPResponse, any Error>?
    private var released = false
    private var response: (status: UInt32, headers: [Header])?
    private var expectedBytes: Int?
    private var body = Data()

    init(request: URLRequest, deadline: ContinuousClock.Instant, clock: HTTPTransportClock, configuration: URLSessionConfiguration, leases: HTTPTransportLeases) {
        self.request = request; self.deadline = deadline; self.clock = clock
        self.configuration = configuration; self.leases = leases
    }

    func start(_ continuation: CheckedContinuation<HTTPResponse, any Error>) {
        lock.lock()
        if terminal == nil, clock.now() >= deadline { terminal = .failure(CapabilityFailure.deadlineExceeded) }
        if let terminal {
            released = true
            lock.unlock()
            leases.release()
            continuation.resume(with: terminal)
            return
        }
        self.continuation = continuation
        let queue = OperationQueue()
        queue.maxConcurrentOperationCount = 1
        queue.qualityOfService = .utility
        let session = URLSession(configuration: configuration, delegate: self, delegateQueue: queue)
        let task = session.dataTask(with: request)
        self.session = session; self.task = task
        timer = Task.detached { [weak self, clock, deadline] in
            do { try await clock.sleepUntil(deadline) }
            catch { return }
            self?.fail(.deadlineExceeded)
        }
        lock.unlock()
        if clock.now() >= deadline { fail(.deadlineExceeded); return }
        task.resume()
    }

    func fail(_ failure: CapabilityFailure) { finish(.failure(failure), cancel: true) }

    private func finish(_ proposed: Result<HTTPResponse, any Error>, cancel proposedCancel: Bool) {
        lock.lock()
        guard terminal == nil else { lock.unlock(); return }
        var result = proposed
        var cancel = proposedCancel
        if case .success = proposed, clock.now() >= deadline {
            result = .failure(CapabilityFailure.deadlineExceeded)
            cancel = true
        }
        terminal = result
        let continuation = self.continuation
        self.continuation = nil
        let timer = self.timer; self.timer = nil
        let session = self.session
        body.removeAll(keepingCapacity: false)
        lock.unlock()
        timer?.cancel()
        if cancel { session?.invalidateAndCancel() } else { session?.finishTasksAndInvalidate() }
        continuation?.resume(with: result)
    }

    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive response: URLResponse,
                    completionHandler: @escaping @Sendable (URLSession.ResponseDisposition) -> Void) {
        do {
            guard clock.now() < deadline else { throw CapabilityFailure.deadlineExceeded }
            guard let http = response as? HTTPURLResponse, (200...599).contains(http.statusCode) else { throw CapabilityFailure.invalidResponse }
            guard !(300...399).contains(http.statusCode) else { throw CapabilityFailure.redirectDenied }
            guard http.url == request.url, http.allHeaderFields.count <= 32 else { throw CapabilityFailure.invalidResponse }
            var headers: [Header] = []
            var seen: Set<String> = []
            var length: UInt64?
            for (rawName, rawValue) in http.allHeaderFields {
                guard let originalName = rawName as? String, let value = rawValue as? String,
                      originalName.utf8.count <= 64, value.utf8.count <= 4096,
                      originalName.utf8.allSatisfy({ (33...126).contains($0) }), value.utf8.allSatisfy({ (32...126).contains($0) }) else { throw CapabilityFailure.invalidResponse }
                let name = originalName.lowercased()
                guard seen.insert(name).inserted else { throw CapabilityFailure.invalidResponse }
                if name == "content-encoding", value.lowercased() != "identity" { throw CapabilityFailure.invalidResponse }
                if name == "content-length" {
                    guard !value.isEmpty, value.utf8.allSatisfy({ (48...57).contains($0) }), let bytes = UInt64(value) else { throw CapabilityFailure.invalidResponse }
                    length = bytes
                }
                if !Self.strippedHeaders.contains(name) { headers.append(try Header(wire: ["name": .string(name), "value": .string(value)])) }
            }
            let noBody = request.httpMethod == "HEAD" || http.statusCode == 204 || http.statusCode == 304
            guard noBody || length.map({ $0 <= Self.maximumBodyBytes }) ?? true,
                  noBody || response.expectedContentLength <= Self.maximumBodyBytes else { throw CapabilityFailure.quotaExceeded }
            lock.lock()
            guard terminal == nil, self.response == nil else {
                let duplicate = terminal == nil
                lock.unlock(); completionHandler(.cancel)
                if duplicate { fail(.invalidResponse) }
                return
            }
            self.response = (UInt32(http.statusCode), headers.sorted { $0.name < $1.name })
            expectedBytes = noBody ? 0 : length.map(Int.init)
            lock.unlock()
            completionHandler(.allow)
        } catch let failure as CapabilityFailure {
            fail(failure); completionHandler(.cancel)
        } catch {
            fail(.invalidResponse); completionHandler(.cancel)
        }
    }

    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        lock.lock()
        guard terminal == nil else { lock.unlock(); return }
        guard clock.now() < deadline else { lock.unlock(); fail(.deadlineExceeded); return }
        guard response != nil else { lock.unlock(); fail(.invalidResponse); return }
        guard data.count <= Self.maximumBodyBytes - body.count else { lock.unlock(); fail(.quotaExceeded); return }
        if let expectedBytes, data.count > expectedBytes - body.count { lock.unlock(); fail(.invalidResponse); return }
        body.append(data)
        lock.unlock()
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: (any Error)?) {
        if let error {
            let failure: CapabilityFailure = (error as? URLError)?.code == .timedOut ? .deadlineExceeded : .ioFailure
            fail(failure)
            return
        }
        lock.lock()
        guard terminal == nil else { lock.unlock(); return }
        guard let response, expectedBytes.map({ $0 == body.count }) ?? true else { lock.unlock(); fail(.invalidResponse); return }
        let result = HTTPResponse(status: response.status, headers: response.headers, bodyBase64: body.base64EncodedString())
        lock.unlock()
        finish(.success(result), cancel: false)
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
        fail(.redirectDenied)
        completionHandler(nil)
    }

    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, willCacheResponse proposedResponse: CachedURLResponse,
                    completionHandler: @escaping @Sendable (CachedURLResponse?) -> Void) { completionHandler(nil) }

    func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping @Sendable (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        authentication(challenge, completionHandler: completionHandler)
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping @Sendable (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        authentication(challenge, completionHandler: completionHandler)
    }
    private func authentication(_ challenge: URLAuthenticationChallenge,
                                completionHandler: @Sendable (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        #if canImport(Security)
        if challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust {
            completionHandler(.performDefaultHandling, nil)
            return
        }
        #endif
        // FoundationNetworking performs ordinary TLS verification in its native
        // backend; Darwin's server-trust challenge API is unavailable there.
        // All application/proxy credential negotiation fails closed everywhere.
        fail(.ioFailure)
        completionHandler(.cancelAuthenticationChallenge, nil)
    }

    func urlSession(_ session: URLSession, didBecomeInvalidWithError error: (any Error)?) {
        lock.lock()
        self.session = nil; task = nil
        let release = !released; released = true
        let unfinished = terminal == nil
        lock.unlock()
        if unfinished { fail(.ioFailure) }
        if release { leases.release() }
    }
}
#endif
