import Foundation
import MixerUpdates

package enum LocalUpdateRelease {
    package enum Action: String, Encodable {
        case publish, promote, rollback
    }

    package struct Receipt: Encodable {
        let status = "ok"
        let action: Action
        let artifactSHA256: String
        let sequence: UInt64
        let rolloutBasisPoints: UInt64
        let delivery: String

        enum CodingKeys: String, CodingKey {
            case status, action, sequence, delivery
            case artifactSHA256 = "artifact_sha256"
            case rolloutBasisPoints = "rollout_basis_points"
        }
    }

    package static func run(_ action: Action, arguments: [String]) async throws -> Receipt {
        let options = try Options(action, arguments)
        let environment = ProcessInfo.processInfo.environment
        let origin = try localOrigin(environment["MIXER_RELEASE_ORIGIN"])
        guard let token = environment["MIXER_RELEASE_TOKEN"], !token.isEmpty, token.utf8.count <= 4089,
              token.utf8.allSatisfy({ (33...126).contains($0) }) else {
            throw MixerFailure("update.credential", "Set MIXER_RELEASE_TOKEN to the scoped local publisher bearer token.")
        }
        let (signedAssignment, assignment) = try signedDocument(options.assignment, field: "assignment")
        guard let scope = assignment["scope"]?.object,
              scope["organization"]?.text == options.organization, scope["project"]?.text == options.project else {
            throw MixerFailure("update.scope", "The signed assignment must match --organization and --project.")
        }
        guard let channel = assignment["channel"]?.text, validID(channel),
              let artifact = assignment["artifact_sha256"]?.text, validDigest(artifact),
              let sequence = assignment["sequence"]?.uint, sequence > 0,
              let rollout = assignment["rollout_basis_points"]?.uint, rollout <= 10_000,
              let runtime = assignment["runtime"]?.text, validDigest(runtime),
              let releaseID = assignment["release_id"]?.text, validID(releaseID) else {
            throw MixerFailure("update.assignment", "The signed v3 assignment lacks valid release coordinates.")
        }
        guard options.channel.map({ $0 == channel }) ?? true,
              options.rollout.map({ $0 == rollout }) ?? true,
              action == .publish || options.target == artifact else {
            throw MixerFailure("update.intent", "The signed assignment must match the requested channel, rollout and artifact.")
        }

        let base = "/v3/orgs/\(options.organization)/projects/\(options.project)"
        let assignmentBody = Data("{\"signed_assignment\":".utf8) + signedAssignment + Data("}".utf8)
        let configuration = URLSessionConfiguration.ephemeral
        configuration.urlCache = nil
        configuration.urlCredentialStorage = nil
        configuration.httpShouldSetCookies = false
        configuration.timeoutIntervalForRequest = 30
        configuration.timeoutIntervalForResource = 30
        configuration.waitsForConnectivity = false
        configuration.connectionProxyDictionary = [
            "HTTPEnable": 0, "HTTPSEnable": 0, "SOCKSEnable": 0, "ProxyAutoConfigEnable": 0,
            "ProxyAutoDiscoveryEnable": 0,
        ]
        let session = URLSession(configuration: configuration, delegate: StoreRedirectRefusal(), delegateQueue: nil)
        defer { session.invalidateAndCancel() }
        let client = Client(session: session, origin: origin, token: token)

        if action == .publish {
            let candidate = fileURL(options.target)
            let (signedManifest, manifest) = try signedDocument(
                candidate.appendingPathComponent("signed-manifest.json"), field: "manifest")
            guard manifest["scope"] == assignment["scope"], manifest["runtime"]?.text == runtime,
                  manifest["release_id"]?.text == releaseID,
                  try SourceDigest.sha256(CanonicalValue.object(manifest).canonicalCBOR()) == artifact else {
                throw MixerFailure("update.intent", "The signed manifest must match the assignment's artifact, scope, runtime and release.")
            }
            let payload = try read(candidate.appendingPathComponent("payload.wasm"), maximum: 4 * 1_048_576)
            let uploadBody = Data("{\"signed_manifest\":".utf8) + signedManifest
                + Data(",\"payload\":\"".utf8) + payload.base64EncodedData() + Data("\"}".utf8)
            let upload: ArtifactResponse = try await client.send(
                "PUT", base + "/artifacts/" + artifact, stage: "upload", body: uploadBody, statuses: [200, 201])
            guard upload.artifactSHA256 == artifact, upload.immutable == true else { throw invalidResponse("upload") }
            let validation: ArtifactResponse = try await client.send(
                "POST", base + "/releases/validate", stage: "validate",
                body: JSONFile.data(["artifact_sha256": artifact]))
            guard validation.artifactSHA256 == artifact, validation.protocolValid == true else { throw invalidResponse("validate") }
        }

        let result: ChannelResponse = try await client.send(
            "POST", base + "/channels/" + channel + "/" + action.rawValue,
            stage: action.rawValue, body: assignmentBody, reason: options.reason)
        guard result.artifactSHA256 == artifact, result.sequence == sequence,
              result.rolloutBasisPoints == rollout, result.delivery == "local_only" else {
            throw invalidResponse(action.rawValue)
        }
        return Receipt(action: action, artifactSHA256: artifact, sequence: sequence,
                       rolloutBasisPoints: rollout, delivery: result.delivery)
    }

    private struct Options {
        let target: String
        let organization: String
        let project: String
        let assignment: URL
        let channel: String?
        let rollout: UInt64?
        let reason: String?

        init(_ action: Action, _ arguments: [String]) throws {
            let common: Set<String> = ["--organization", "--project", "--assignment"]
            let specific: Set<String> = switch action {
            case .publish: ["--channel", "--rollout"]
            case .promote: ["--rollout"]
            case .rollback: ["--reason"]
            }
            let required = common.union(specific)
            let allowed = required.union(["--channel"])
            let usage = MixerFailure("update.arguments", "Run mixer help for the local update \(action.rawValue) syntax.")
            guard let target = arguments.first, !target.isEmpty, !target.hasPrefix("--"),
                  arguments.count % 2 == 1 else { throw usage }
            var values: [String: String] = [:]
            for index in stride(from: 1, to: arguments.count, by: 2) {
                let name = arguments[index]
                let value = arguments[index + 1]
                guard allowed.contains(name), values[name] == nil, !value.isEmpty,
                      name == "--reason" || !value.hasPrefix("--") else { throw usage }
                values[name] = value
            }
            guard required.isSubset(of: values.keys),
                  let org = values["--organization"], validID(org),
                  let project = values["--project"], validID(project),
                  let assignment = values["--assignment"],
                  action == .publish || validDigest(target) else { throw usage }
            self.target = target
            organization = org
            self.project = project
            self.assignment = fileURL(assignment)
            channel = values["--channel"]
            if let channel, !validID(channel) { throw usage }
            if let percent = values["--rollout"] {
                guard percent.utf8.allSatisfy({ (48...57).contains($0) }),
                      let value = UInt64(percent), (1...100).contains(value) else { throw usage }
                rollout = value * 100
            } else {
                rollout = nil
            }
            reason = values["--reason"]
            if let reason {
                guard reason.utf8.count <= 512, reason.first != " ", reason.last != " ",
                      reason.utf8.allSatisfy({ (32...126).contains($0) }) else {
                    throw MixerFailure("update.reason", "Supply a rollback reason of 1–512 printable ASCII bytes without surrounding spaces.")
                }
            }
        }
    }

    private struct ArtifactResponse: Decodable {
        let artifactSHA256: String
        let immutable: Bool?
        let protocolValid: Bool?

        enum CodingKeys: String, CodingKey {
            case artifactSHA256 = "artifact_sha256"
            case immutable
            case protocolValid = "protocol_valid"
        }
    }

    private struct ChannelResponse: Decodable {
        let artifactSHA256: String
        let sequence: UInt64
        let rolloutBasisPoints: UInt64
        let delivery: String

        enum CodingKeys: String, CodingKey {
            case artifactSHA256 = "artifact_sha256"
            case sequence, delivery
            case rolloutBasisPoints = "rollout_basis_points"
        }
    }

    private struct Client {
        let session: URLSession
        let origin: URL
        let token: String

        func send<T: Decodable>(_ method: String, _ path: String, stage: String, body: Data,
                                statuses: Set<Int> = [200], reason: String? = nil) async throws -> T {
            let url = origin.appending(path: path)
            var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData)
            request.httpMethod = method
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
            request.setValue(reason, forHTTPHeaderField: "X-Mixer-Reason")

            // The origin deduplicates exact method, path and body in the tenant.
            // Include the reason here because the origin reads it from a header.
            let intent = Data("mixer-local-release-v3\u{0}\(method)\u{0}\(path)\u{0}\(reason ?? "")\u{0}".utf8)
            request.setValue(SourceDigest.sha256(intent + body), forHTTPHeaderField: "Idempotency-Key")

            let response: URLResponse
            let stream: URLSession.AsyncBytes
            do {
                (stream, response) = try await session.bytes(for: request)
            } catch {
                throw transportFailure(stage)
            }
            let maximum = 4096
            guard let http = response as? HTTPURLResponse, http.url == url,
                  http.mimeType == "application/json", http.expectedContentLength <= maximum else {
                throw invalidResponse(stage)
            }
            var data = Data()
            do {
                for try await byte in stream {
                    data.append(byte)
                    if data.count > maximum { break }
                }
            } catch {
                throw transportFailure(stage)
            }
            guard data.count <= maximum else { throw invalidResponse(stage) }

            guard statuses.contains(http.statusCode) else {
                let error = try? StrictJSON.decode(ServiceError.self, from: data, maximumBytes: maximum)
                let detail = error.map { " (\($0.error.code.rawValue))" } ?? ""
                throw MixerFailure("update.\(stage).rejected", "Local v3 origin returned HTTP \(http.statusCode)\(detail).")
            }
            guard let value = try? StrictJSON.decode(T.self, from: data, maximumBytes: maximum) else {
                throw invalidResponse(stage)
            }
            return value
        }
    }

    private struct ServiceError: Decodable {
        let error: Detail

        struct Detail: Decodable {
            let code: Code
        }

        enum Code: String, Decodable {
            case unauthenticated, scope_denied, role_denied, protocol_mismatch, unknown_runtime
            case invalid_json, artifact_invalid, digest_mismatch, immutable_conflict, not_validated
            case assignment_rejected, invalid_promotion, invalid_rollback, idempotency_conflict
            case storage_unavailable, local_capacity, rate_limit, concurrency_limit, not_found
        }
    }

    private static func signedDocument(_ url: URL, field: String) throws -> (Data, [String: CanonicalValue]) {
        let maximum = 65_536
        let bytes = try read(url, maximum: maximum)
        guard let document = try? StrictJSON.decode(CanonicalValue.self, from: bytes, maximumBytes: maximum),
              let envelope = document.object, Set(envelope.keys) == [field, "signature"],
              let value = envelope[field]?.object, value["schema"]?.uint == 3,
              let signature = envelope["signature"]?.text,
              let decoded = Data(base64Encoded: signature), decoded.count == 64,
              decoded.base64EncodedString() == signature else {
            throw MixerFailure("update.signed-input", "Expected a bounded v3 signed \(field) JSON document.")
        }
        return (bytes, value)
    }

    private static func read(_ url: URL, maximum: Int) throws -> Data {
        do { return try UpdateInputFile.read(url, maximumBytes: maximum) }
        catch { throw MixerFailure("update.input", "Cannot read \(url.lastPathComponent) as a bounded regular file.") }
    }

    private static func localOrigin(_ value: String?) throws -> URL {
        guard let value, let parts = URLComponents(string: value), parts.scheme == "http",
              parts.percentEncodedHost == "127.0.0.1", let port = parts.port, (1...65535).contains(port),
              parts.user == nil, parts.password == nil, parts.query == nil, parts.fragment == nil,
              parts.percentEncodedPath.isEmpty || parts.percentEncodedPath == "/",
              let url = URL(string: "http://127.0.0.1:\(port)") else {
            throw MixerFailure("update.origin", "Set MIXER_RELEASE_ORIGIN to http://127.0.0.1:PORT for a local v3 origin.")
        }
        return url
    }

    private static func fileURL(_ path: String) -> URL {
        URL(fileURLWithPath: path, relativeTo: URL(fileURLWithPath: FileManager.default.currentDirectoryPath, isDirectory: true))
            .standardizedFileURL
    }

    private static func validID(_ value: String) -> Bool {
        (1...128).contains(value.utf8.count) && value != "." && value != ".." &&
            value.utf8.allSatisfy { (48...57).contains($0) || (65...90).contains($0) ||
                (97...122).contains($0) || $0 == 45 || $0 == 46 || $0 == 95 }
    }

    private static func validDigest(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }

    private static func invalidResponse(_ stage: String) -> MixerFailure {
        MixerFailure("update.\(stage).response", "Unexpected local v3 response. Retry the same signed inputs and options to resolve the outcome.")
    }

    private static func transportFailure(_ stage: String) -> MixerFailure {
        MixerFailure("update.\(stage).transport", "Local v3 request could not be completed. Retry the same signed inputs and options to resolve the outcome.")
    }
}
