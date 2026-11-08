import Foundation
import MixerCore

// Official contract: developer.apple.com/documentation/appstoreconnectapi/get-v1-builds-_id_
// Numeric limits are development hypotheses, not provider guarantees.
public struct AppStoreConnectBuildStatus: Sendable {
    public static let maximumResponseBytes = 262_144
    public static let timeoutSeconds: TimeInterval = 30
    private let configuration: URLSessionConfiguration

    public init() { configuration = .ephemeral }
    init(configuration: URLSessionConfiguration) { self.configuration = configuration }

    func read(buildID: String, appID: String, bundleID: String, token: String) throws -> StoreBuildObservation.ProviderValue {
        guard !token.isEmpty, token.utf8.count <= 16_384,
              token.utf8.allSatisfy({ (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || [45, 46, 95, 126, 43, 47, 61].contains($0) }) else {
            throw StoreQueryFailure.credentialRequired
        }
        guard ![buildID, appID, bundleID].contains(where: { $0.contains(token) }) else { throw StoreQueryFailure.redactedResponse }
        var components = URLComponents(string: "https://api.appstoreconnect.apple.com/v1/builds/\(buildID)")!
        components.queryItems = [URLQueryItem(name: "fields[builds]", value: "version,processingState,app"), URLQueryItem(name: "include", value: "app"), URLQueryItem(name: "fields[apps]", value: "bundleId")]
        let url = components.url!
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: Self.timeoutSeconds)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        let config = configuration.copy() as! URLSessionConfiguration
        config.urlCache = nil; config.httpCookieStorage = nil; config.urlCredentialStorage = nil
        config.httpShouldSetCookies = false; config.httpAdditionalHeaders = [:]
        config.timeoutIntervalForRequest = Self.timeoutSeconds
        config.timeoutIntervalForResource = Self.timeoutSeconds
        config.waitsForConnectivity = false
        let receiver = ASCResponseReceiver(expectedURL: url)
        let session = URLSession(configuration: config, delegate: receiver, delegateQueue: nil)
        defer { session.invalidateAndCancel() }
        session.dataTask(with: request).resume()
        guard receiver.finished.wait(timeout: .now() + Self.timeoutSeconds) == .success else { throw StoreQueryFailure.timeout }
        let bytes = try receiver.result()
        do {
            try JSONInputGuard.validate(bytes, limits: JSONInputLimits(maximumBytes: Self.maximumResponseBytes, maximumDepth: 16, maximumValues: 4096, maximumStringBytes: 4096))
            let response = try JSONDecoder().decode(ASCBuildResponse.self, from: bytes)
            guard response.data.type == "builds", response.data.id == buildID,
                  response.data.relationships.app.data.type == "apps", response.data.relationships.app.data.id == appID else { throw StoreQueryFailure.identityMismatch }
            let apps = response.included.filter { $0.type == "apps" }
            guard apps.count == 1, let app = apps.first, app.id == appID, app.attributes.bundleId == bundleID else { throw StoreQueryFailure.identityMismatch }
            let version = response.data.attributes.version, state = response.data.attributes.processingState
            guard !version.isEmpty, version.utf8.count <= 256, !version.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }),
                  !state.isEmpty, state.utf8.count <= 128, !state.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else { throw StoreQueryFailure.malformedResponse }
            guard ![version, state, app.id, app.attributes.bundleId, response.data.id].contains(where: { $0.contains(token) }) else { throw StoreQueryFailure.redactedResponse }
            return .init(version: version, processingState: state)
        } catch let failure as StoreQueryFailure { throw failure }
        catch { throw StoreQueryFailure.malformedResponse }
    }
}

private struct ASCBuildResponse: Decodable {
    struct Linkage: Decodable { let type: String; let id: String }
    struct Build: Decodable {
        struct Attributes: Decodable { let version: String; let processingState: String }
        struct Relationships: Decodable {
            struct App: Decodable { let data: Linkage }
            let app: App
        }
        let type: String; let id: String; let attributes: Attributes; let relationships: Relationships
    }
    struct App: Decodable {
        struct Attributes: Decodable { let bundleId: String }
        let type: String; let id: String; let attributes: Attributes
    }
    let data: Build
    let included: [App]
}

// Delegate callbacks are serialized by URLSession; result access is fenced by the semaphore.
private final class ASCResponseReceiver: NSObject, URLSessionDataDelegate, @unchecked Sendable {
    let finished = DispatchSemaphore(value: 0)
    private let expectedURL: URL
    private var body = Data()
    private var failure: StoreQueryFailure?
    init(expectedURL: URL) { self.expectedURL = expectedURL }
    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive response: URLResponse, completionHandler: @escaping @Sendable (URLSession.ResponseDisposition) -> Void) {
        guard let http = response as? HTTPURLResponse, http.url == expectedURL else {
            failure = .invalidResponse; completionHandler(.cancel); return
        }
        switch http.statusCode {
        case 200: break
        case 300...399: failure = .redirectRefused
        case 401: failure = .authenticationRejected
        case 403: failure = .accessForbidden
        case 404: failure = .notFound
        case 429: failure = .rateLimited
        default: failure = .providerRejected
        }
        if response.expectedContentLength > Int64(AppStoreConnectBuildStatus.maximumResponseBytes) { failure = .responseTooLarge }
        if failure == nil, http.mimeType?.lowercased() != "application/json" { failure = .invalidResponse }
        completionHandler(failure == nil ? .allow : .cancel)
    }
    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        guard failure == nil else { return }
        guard data.count <= AppStoreConnectBuildStatus.maximumResponseBytes - body.count else { failure = .responseTooLarge; dataTask.cancel(); return }
        body.append(data)
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
        failure = .redirectRefused; completionHandler(nil)
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping @Sendable (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        completionHandler(challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust ? .performDefaultHandling : .cancelAuthenticationChallenge, nil)
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        if failure == nil, let error { failure = (error as? URLError)?.code == .timedOut ? .timeout : .transportFailed }
        finished.signal()
    }
    func result() throws -> Data { if let failure { throw failure }; return body }
}

public enum StoreQueryFailure: String, Error, Codable, Sendable {
    case credentialRequired = "store.credential-required"
    case authenticationRejected = "store.authentication-rejected"
    case accessForbidden = "store.access-forbidden"
    case notFound = "store.not-found"
    case rateLimited = "store.rate-limited"
    case providerRejected = "store.provider-rejected"
    case timeout = "store.timeout"
    case transportFailed = "store.transport-failed"
    case redirectRefused = "store.redirect-refused"
    case responseTooLarge = "store.response-too-large"
    case malformedResponse = "store.malformed-response"
    case invalidResponse = "store.invalid-response"
    case identityMismatch = "store.identity-mismatch"
    case redactedResponse = "store.redacted-response"
}
