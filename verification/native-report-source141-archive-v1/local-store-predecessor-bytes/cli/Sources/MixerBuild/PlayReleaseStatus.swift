import Foundation
import MixerCore

public enum PlayStatusFailure: String, Error, Codable, Sendable {
    case invalidRequest, credentialRequired, redactedResponse, authenticationRejected, accessForbidden
    case notFound, rateLimited, providerRejected, timeout, transportFailed, redirectRefused
    case responseTooLarge, malformedResponse, identityMismatch, unknownState, contradictoryResponse
}

public struct PlayTestingRequest: Equatable, Encodable, Sendable {
    public let applicationID: String
    public let versionCode: Int32
    public let track: String

    public init(applicationID: String, versionCode: String, track: String) throws {
        let parts = applicationID.split(separator: ".", omittingEmptySubsequences: false)
        guard applicationID.utf8.count <= 256, parts.count >= 2,
              parts.allSatisfy({ part in
                  guard let first = part.utf8.first, Self.letter(first) else { return false }
                  return part.utf8.allSatisfy { Self.letter($0) || (48...57).contains($0) || $0 == 95 }
              }), let code = Int32(versionCode), code > 0, String(code) == versionCode,
              !track.isEmpty, track.utf8.count <= 100,
              track.utf8.allSatisfy({ Self.letter($0) || (48...57).contains($0) || [45, 95, 58].contains($0) }) else {
            throw PlayStatusFailure.invalidRequest
        }
        self.applicationID = applicationID; self.versionCode = code; self.track = track
    }

    public static func parse(words: [String], options: [String: String], applicationID: String) throws -> Self {
        guard words == ["submit", "testing-status"], options["--provider"] == "play",
              Set(options.keys).isSubset(of: ["--provider", "--version-code", "--track", "--directory"]),
              let version = options["--version-code"], let track = options["--track"] else {
            throw PlayStatusFailure.invalidRequest
        }
        return try Self(applicationID: applicationID, versionCode: version, track: track)
    }

    public var url: URL {
        URL(string: "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/\(applicationID)/tracks/\(track)/releases")!
    }

    private static func letter(_ c: UInt8) -> Bool { (65...90).contains(c) || (97...122).contains(c) }
}

// Official contract: developers.google.com/android-publisher/api-ref/rest/v3/applications.tracks.releases
public enum PlayReleaseLifecycle: String, Codable, Sendable {
    case draft = "RELEASE_LIFECYCLE_STATE_DRAFT"
    case notSentForReview = "RELEASE_LIFECYCLE_STATE_NOT_SENT_FOR_REVIEW"
    case inReview = "RELEASE_LIFECYCLE_STATE_IN_REVIEW"
    case approvedNotPublished = "RELEASE_LIFECYCLE_STATE_APPROVED_NOT_PUBLISHED"
    case notApproved = "RELEASE_LIFECYCLE_STATE_NOT_APPROVED"
    case published = "RELEASE_LIFECYCLE_STATE_PUBLISHED"
}

public struct PlayReleaseObservation: Encodable, Sendable {
    public let identity: PlayTestingRequest
    public let lifecycle: PlayReleaseLifecycle
    public let observedAt: Date
    fileprivate init(identity: PlayTestingRequest, lifecycle: PlayReleaseLifecycle) {
        self.identity = identity; self.lifecycle = lifecycle; observedAt = Date()
    }
}

public struct PlayTestingReport: Encodable, Sendable {
    public enum Status: String, Encodable, Sendable {
        case draft, inReview = "in-review", awaitingReviewSubmission = "awaiting-review-submission"
        case awaitingPublication = "awaiting-publication", rejected, publishedOnTrack = "published-on-track"
        case notObserved = "not-observed", unresolved
    }
    public let provider = "play"
    public let qualification = "provider-observation-only"
    public let identity: PlayTestingRequest
    public let status: Status
    public let code: PlayStatusFailure?
    public let observation: PlayReleaseObservation?
    public let observationFreshness: String
    public let testingReadiness = "unverified"
    public let testLinks = "unverified"
    public let productionAvailability = "unverified"
    public let exitCode: Int32
    public let nextStep: String

    fileprivate init(identity: PlayTestingRequest, current: PlayReleaseObservation?, previous: PlayReleaseObservation?, failure: PlayStatusFailure?) {
        self.identity = identity; code = failure
        observation = current ?? (previous?.identity == identity ? previous : nil)
        observationFreshness = current != nil ? "current-provider-observation" : observation == nil ? "no-observation" : "retained-previous-observation"
        if let failure {
            status = .unresolved; exitCode = 1
            switch failure {
            case .authenticationRejected, .credentialRequired:
                nextStep = "Supply an authorized short-lived Play bearer token and reconcile this same version again."
            case .accessForbidden:
                nextStep = "Inspect Play Console access and account actions; this response does not identify an agreement or identity-verification requirement."
            default:
                nextStep = "Reconcile this exact application, version and track again. Historical observations do not establish current status; do not blindly upload or submit again."
            }
        } else if let current {
            switch current.lifecycle {
            case .draft: status = .draft
            case .notSentForReview: status = .awaitingReviewSubmission
            case .inReview: status = .inReview
            case .approvedNotPublished: status = .awaitingPublication
            case .notApproved: status = .rejected
            case .published: status = .publishedOnTrack
            }
            exitCode = current.lifecycle == .published ? 0 : current.lifecycle == .notApproved ? 1 : 2
            switch current.lifecycle {
            case .notSentForReview: nextStep = "A developer must decide whether to send this release for review in Play Console."
            case .approvedNotPublished: nextStep = "Review passed; a developer must decide whether to publish this release in Play Console."
            case .notApproved: nextStep = "Inspect this exact release's rejection details in Play Console before preparing a correction."
            case .published: nextStep = "PUBLISHED includes halted and partial rollouts. Verify serving state and tester access separately; this is not a testing-ready or production qualification."
            default: nextStep = "Reconcile this release's lifecycle again; no upload, review submission or publication was performed."
            }
        } else {
            status = .notObserved; exitCode = 2
            nextStep = "This version was not observed among the track's non-obsolete releases. Reconcile or inspect Play Console; absence does not prove upload failure or permit resubmission."
        }
    }
}

public struct PlayReleaseStatus: Sendable {
    public static let maximumResponseBytes = 262_144
    public static let timeoutSeconds: TimeInterval = 30
    private let configuration: URLSessionConfiguration
    public init() { configuration = .ephemeral }
    init(configuration: URLSessionConfiguration) { self.configuration = configuration }

    public func status(request identity: PlayTestingRequest, token: String, previous: PlayReleaseObservation? = nil) async throws -> PlayTestingReport {
        // A reflected identity cannot safely be included even in a failure report.
        guard token.isEmpty || ![identity.applicationID, String(identity.versionCode), identity.track].contains(where: { $0.contains(token) }) else {
            throw PlayStatusFailure.redactedResponse
        }
        do {
            guard !token.isEmpty, token.utf8.count <= 16_384,
                  token.utf8.allSatisfy({ (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || [45, 46, 95, 126, 43, 47, 61].contains($0) }) else {
                throw PlayStatusFailure.credentialRequired
            }
            var request = URLRequest(url: identity.url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: Self.timeoutSeconds)
            request.httpMethod = "GET"
            request.setValue("application/json", forHTTPHeaderField: "Accept")
            request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
            let config = configuration.copy() as! URLSessionConfiguration
            config.urlCache = nil; config.httpCookieStorage = nil; config.urlCredentialStorage = nil
            config.httpShouldSetCookies = false; config.httpAdditionalHeaders = [:]
            config.timeoutIntervalForRequest = Self.timeoutSeconds; config.timeoutIntervalForResource = Self.timeoutSeconds
            config.waitsForConnectivity = false
            let session = URLSession(configuration: config, delegate: PlayRedirectRefusal(), delegateQueue: nil)
            defer { session.invalidateAndCancel() }
            let (stream, response) = try await session.bytes(for: request)
            guard let response = response as? HTTPURLResponse, response.url?.absoluteString == identity.url.absoluteString else {
                throw PlayStatusFailure.identityMismatch
            }
            switch response.statusCode {
            case 200: break
            case 300..<400: throw PlayStatusFailure.redirectRefused
            case 401: throw PlayStatusFailure.authenticationRejected
            case 403: throw PlayStatusFailure.accessForbidden
            case 404: throw PlayStatusFailure.notFound
            case 429: throw PlayStatusFailure.rateLimited
            default: throw PlayStatusFailure.providerRejected
            }
            guard response.mimeType?.lowercased() == "application/json" else { throw PlayStatusFailure.malformedResponse }
            guard response.expectedContentLength <= Int64(Self.maximumResponseBytes) else { throw PlayStatusFailure.responseTooLarge }
            var bytes = Data()
            for try await byte in stream {
                guard bytes.count < Self.maximumResponseBytes else { throw PlayStatusFailure.responseTooLarge }
                bytes.append(byte)
            }
            let current = try Self.observation(bytes, identity: identity)
            return .init(identity: identity, current: current, previous: previous, failure: nil)
        } catch {
            let failure: PlayStatusFailure
            if let known = error as? PlayStatusFailure { failure = known }
            else if let url = error as? URLError, url.code == .timedOut { failure = .timeout }
            else { failure = .transportFailed }
            return .init(identity: identity, current: nil, previous: previous, failure: failure)
        }
    }

    private static func observation(_ bytes: Data, identity: PlayTestingRequest) throws -> PlayReleaseObservation? {
        do {
            try JSONInputGuard.validate(bytes, limits: .init(maximumBytes: maximumResponseBytes, maximumDepth: 12, maximumValues: 4096, maximumStringBytes: 4096))
            let response = try JSONDecoder().decode(PlayReleaseList.self, from: bytes)
            let releases = response.releases ?? []
            guard releases.count <= 20 else { throw PlayStatusFailure.malformedResponse }
            var matching: PlayReleaseLifecycle?
            for release in releases {
                guard release.track == identity.track else { throw PlayStatusFailure.identityMismatch }
                guard let state = PlayReleaseLifecycle(rawValue: release.releaseLifecycleState) else { throw PlayStatusFailure.unknownState }
                let codes = (release.activeArtifacts ?? []).map(\.versionCode)
                guard codes.allSatisfy({ $0 > 0 }), Set(codes).count == codes.count else { throw PlayStatusFailure.contradictoryResponse }
                if codes.contains(identity.versionCode) {
                    guard matching == nil else { throw PlayStatusFailure.contradictoryResponse }
                    matching = state
                }
            }
            return matching.map { PlayReleaseObservation(identity: identity, lifecycle: $0) }
        } catch let failure as PlayStatusFailure { throw failure }
        catch { throw PlayStatusFailure.malformedResponse }
    }
}

private struct PlayReleaseList: Decodable {
    struct Release: Decodable {
        struct Artifact: Decodable { let versionCode: Int32 }
        let track: String
        let activeArtifacts: [Artifact]?
        let releaseLifecycleState: String
    }
    let releases: [Release]?
}

private final class PlayRedirectRefusal: NSObject, URLSessionTaskDelegate, Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}
