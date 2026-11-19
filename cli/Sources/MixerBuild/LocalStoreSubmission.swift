#if MIXER_LOCAL_STORE_FIXTURE
import CryptoKit
import Darwin
import Foundation
import MixerCore

package enum LocalStoreSubmission {
    fileprivate struct Identity: Codable, Equatable {
        let provider: String
        let applicationID: String
        var appID: String? = nil
        var buildID: String? = nil
        var versionCode: Int32? = nil
        var track: String? = nil
    }

    fileprivate struct Submission: Codable {
        let schema: Int
        let identity: Identity
        let artifactSHA256: String
    }

    private struct Acceptance: Decodable {
        let submission: Submission
        let submissionID: UUID
    }

    package struct Report: Encodable {
        package let exitCode: Int32
        let qualification = "local-provider-fixture-only"
        let status: String
        let code: String?
        let submissionID: UUID?
        fileprivate let submission: Submission
    }

    package static func run(
        create: Bool, options: [String: String], directory: URL, artifact: URL
    ) async throws -> Report {
        let config = try ApplicationConfiguration.load(directory)
        let providerOptions = options.filter { $0.key != "--artifact" }
        let identity: Identity
        let target: String
        switch options["--provider"] {
        case "app-store-connect":
            let request = try StoreStatusRequest.parse(words: ["submit", "status"], options: providerOptions)
            let bundleID = config.applicationIdentifier(for: "ios")
            guard config.targets.contains("ios"), bundleID.utf8.count <= 256 else {
                throw MixerFailure("store.fixture-project", "A valid iOS application identity is required.")
            }
            identity = Identity(provider: "app-store-connect", applicationID: bundleID,
                                appID: request.appID, buildID: request.buildID)
            target = "/ios/\(request.appID)/\(request.buildID)"
        case "play":
            let request = try PlayTestingRequest.parse(words: ["submit", "testing-status"],
                                                       options: providerOptions, applicationID: config.applicationIdentifier(for: "android"))
            guard config.targets.contains("android") else {
                throw MixerFailure("store.fixture-project", "An Android target is required.")
            }
            identity = Identity(provider: "play", applicationID: request.applicationID,
                                versionCode: request.versionCode, track: request.track)
            target = "/android/\(request.applicationID)/\(request.track)/\(request.versionCode)"
        default:
            throw MixerFailure("store.fixture-provider", "Select app-store-connect or play.")
        }
        guard ![target, identity.applicationID].contains(where: { $0.contains(LocalStoreFixture.token) }) else {
            throw MixerFailure("store.fixture-identity", "The application identity overlaps the fixture token.")
        }
        let submission = Submission(schema: 1, identity: identity, artifactSHA256: try digest(artifact))
        let url = try LocalStoreFixture.submissionURL(target: target)
        let configuration = URLSessionConfiguration.ephemeral
        configuration.urlCache = nil
        configuration.httpCookieStorage = nil
        configuration.urlCredentialStorage = nil
        configuration.httpShouldSetCookies = false
        configuration.timeoutIntervalForRequest = 5
        configuration.timeoutIntervalForResource = 5
        configuration.waitsForConnectivity = false
        LocalStoreFixture.configure(configuration)
        let session = URLSession(configuration: configuration, delegate: StoreRedirectRefusal(), delegateQueue: nil)
        defer { session.invalidateAndCancel() }

        do {
            let existing = try await exchange(url, session: session, submission: submission)
            if existing.status != "not-observed" || !create { return existing }

            // A competing writer can win after the lookup. Only the provider's
            // atomic create-if-absent decides which request owns this identity.
            let created = try await exchange(url, session: session, submission: submission, create: true)
            if created.code == "store.fixture-create-race" {
                return try await exchange(url, session: session, submission: submission)
            }
            return created
        } catch {
            return Report(exitCode: 1, status: "unresolved", code: "store.fixture-transport",
                          submissionID: nil, submission: submission)
        }
    }

    private static func exchange(
        _ url: URL, session: URLSession, submission: Submission, create: Bool = false
    ) async throws -> Report {
        func report(_ status: String, code: String? = nil, exit: Int32 = 1, id: UUID? = nil) -> Report {
            Report(exitCode: exit, status: status, code: code, submissionID: id, submission: submission)
        }
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData)
        request.httpMethod = create ? "PUT" : "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("Bearer " + LocalStoreFixture.token, forHTTPHeaderField: "Authorization")
        if create {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.setValue("*", forHTTPHeaderField: "If-None-Match")
            request.httpBody = try JSONFile.data(submission)
        }
        let (stream, response) = try await session.bytes(for: request)
        guard let http = response as? HTTPURLResponse, http.url == url else {
            return report("unresolved", code: "store.fixture-response")
        }
        switch http.statusCode {
        case 404 where !create: return report("not-observed", exit: 2)
        case 412 where create: return report("unresolved", code: "store.fixture-create-race")
        case 422 where create: return report("rejected", code: "store.fixture-rejected")
        case 300...399: return report("unresolved", code: "store.fixture-redirect")
        case create ? 201 : 200: break
        default: return report("unresolved", code: "store.fixture-provider-error")
        }
        let maxBytes = 4_096
        guard http.mimeType == "application/json", http.expectedContentLength <= Int64(maxBytes) else {
            return report("unresolved", code: "store.fixture-response")
        }
        var body = Data()
        for try await byte in stream {
            guard body.count < maxBytes else { return report("unresolved", code: "store.fixture-response") }
            body.append(byte)
        }
        let acceptance: Acceptance
        do {
            try JSONInputGuard.validate(body, limits: .init(maximumBytes: maxBytes, maximumDepth: 8, maximumValues: 64))
            acceptance = try JSONDecoder().decode(Acceptance.self, from: body)
        } catch {
            return report("unresolved", code: "store.fixture-response")
        }
        guard acceptance.submission.schema == submission.schema else {
            return report("unresolved", code: "store.fixture-response")
        }
        guard acceptance.submission.identity == submission.identity else {
            return report("unresolved", code: "store.fixture-identity-mismatch")
        }
        guard acceptance.submission.artifactSHA256 == submission.artifactSHA256 else {
            return report("unresolved", code: "store.fixture-stale-artifact")
        }
        return report("accepted", exit: 0, id: acceptance.submissionID)
    }

    private static func digest(_ artifact: URL) throws -> String {
        let failure = MixerFailure("store.fixture-artifact", "Supply a readable regular development artifact between 1 byte and 128 MiB.")
        let descriptor = Darwin.open(artifact.path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK)
        guard descriptor >= 0 else { throw failure }
        let handle = FileHandle(fileDescriptor: descriptor, closeOnDealloc: true)
        defer { try? handle.close() }
        var info = stat()
        guard fstat(descriptor, &info) == 0, (info.st_mode & S_IFMT) == S_IFREG,
              (1...(128 * 1024 * 1024)).contains(info.st_size) else { throw failure }
        do {
            var remaining = Int(info.st_size)
            var hash = SHA256()
            while remaining > 0 {
                guard let chunk = try handle.read(upToCount: min(remaining, 65_536)), !chunk.isEmpty else {
                    throw failure
                }
                hash.update(data: chunk)
                remaining -= chunk.count
            }
            var after = stat()
            guard (try handle.read(upToCount: 1))?.isEmpty ?? true,
                  fstat(descriptor, &after) == 0,
                  after.st_size == info.st_size,
                  after.st_mtimespec.tv_sec == info.st_mtimespec.tv_sec,
                  after.st_mtimespec.tv_nsec == info.st_mtimespec.tv_nsec,
                  after.st_ctimespec.tv_sec == info.st_ctimespec.tv_sec,
                  after.st_ctimespec.tv_nsec == info.st_ctimespec.tv_nsec else { throw failure }
            return hash.finalize().map { String(format: "%02x", $0) }.joined()
        } catch { throw failure }
    }
}
#endif
