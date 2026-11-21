import Foundation
import MixerUpdates

package enum LocalUpdateRelease {
    package enum Action: String, Encodable {
        case publish, promote, rollback, halt
    }

    package struct Receipt: Encodable {
        let status = "ok"
        let action: Action
        let artifactSHA256: String
        let sequence: UInt64
        let rolloutBasisPoints: UInt64
        let delivery: String
        var health: ReleaseRESTV3.Health?

        enum CodingKeys: String, CodingKey {
            case status, action, sequence, delivery, health
            case artifactSHA256 = "artifact_sha256"
            case rolloutBasisPoints = "rollout_basis_points"
        }
    }

    package struct StageReceipt: Encodable {
        struct Variant: Encodable {
            let sequence: UInt64
            let artifactSHA256: String
            let rolloutBasisPoints: UInt64

            enum CodingKeys: String, CodingKey {
                case sequence
                case artifactSHA256 = "artifact_sha256"
                case rolloutBasisPoints = "rollout_basis_points"
            }

            func matches(_ response: ReleaseRESTV3.StagePromotionVariant) -> Bool {
                sequence == response.sequence && artifactSHA256 == response.artifactSHA256 &&
                    rolloutBasisPoints == response.rolloutBasisPoints
            }
        }

        let status = "ok"
        let action = "promote-environment"
        let directionID: String
        let ios: Variant
        let android: Variant
        let delivery: String

        enum CodingKeys: String, CodingKey {
            case status, action, ios, android, delivery
            case directionID = "direction_id"
        }
    }

    package static func promoteEnvironment(arguments: [String]) async throws -> StageReceipt {
        let required: Set<String> = [
            "--organization", "--project", "--application", "--reason",
            "--source-ios-sequence", "--source-android-sequence", "--ios-assignment", "--android-assignment",
        ]
        let usage = MixerFailure("update.arguments", "Run mixer help for the local update promote-environment syntax.")
        let (direction, values) = try optionValues(arguments, allowed: required, required: required, usage: usage)
        guard ReleaseV3Wire.validID(direction),
              let org = values["--organization"], ReleaseV3Wire.validID(org),
              let projectID = values["--project"], ReleaseV3Wire.validID(projectID),
              let app = values["--application"], ReleaseV3Wire.validID(app),
              let iosSequence = positiveSequence(values["--source-ios-sequence"]),
              let androidSequence = positiveSequence(values["--source-android-sequence"]),
              let iosPath = values["--ios-assignment"], let androidPath = values["--android-assignment"],
              let reason = values["--reason"] else { throw usage }
        guard validReason(reason) else {
            throw MixerFailure("update.reason", "Supply a promotion reason of 1–512 printable ASCII bytes without surrounding spaces.")
        }
        let project = ReleaseRESTV3.Project(organizationID: org, projectID: projectID)
        let client = try makeClient()
        defer { client.session.invalidateAndCancel() }
        let ios = try ReleaseRESTV3.SignedAssignment(
            read(fileURL(iosPath), maximum: ReleaseRESTV3.signedDocumentMaximumBytes))
        let android = try ReleaseRESTV3.SignedAssignment(
            read(fileURL(androidPath), maximum: ReleaseRESTV3.signedDocumentMaximumBytes))
        let iosIntent = try stageVariant(ios, platform: "ios", project: project, app: app)
        let androidIntent = try stageVariant(android, platform: "android", project: project, app: app)
        guard ios.value["scope"]?.object?["environment"] == android.value["scope"]?.object?["environment"],
              ios.value["release_id"] == android.value["release_id"] else {
            throw MixerFailure("update.intent", "Both assignments must name the same destination environment and release.")
        }
        let operation = try ReleaseRESTV3.stagePromote(
            project, applicationID: app, directionID: direction,
            body: .init(sourceIosSequence: iosSequence, sourceAndroidSequence: androidSequence,
                        iosSignedAssignment: ios, androidSignedAssignment: android),
            reason: reason)
        let response = try await client.send(operation)
        guard response.delivery == "local_only", iosIntent.matches(response.ios),
              androidIntent.matches(response.android) else { throw invalidResponse(operation.stage) }
        return StageReceipt(directionID: direction, ios: iosIntent, android: androidIntent, delivery: response.delivery)
    }

    package static func run(_ action: Action, arguments: [String]) async throws -> Receipt {
        let options = try Options(action, arguments)
        let client = try makeClient()
        defer { client.session.invalidateAndCancel() }
        let signedAssignment = try ReleaseRESTV3.SignedAssignment(
            read(options.assignment, maximum: ReleaseRESTV3.signedDocumentMaximumBytes))
        let assignment = signedAssignment.value
        guard let scope = assignment["scope"]?.object,
              scope["organization"]?.text == options.organization, scope["project"]?.text == options.project else {
            throw MixerFailure("update.scope", "The signed assignment must match --organization and --project.")
        }
        guard let channel = assignment["channel"]?.text, ReleaseV3Wire.validID(channel),
              let artifact = assignment["artifact_sha256"]?.text, ReleaseV3Wire.validDigest(artifact),
              let sequence = assignment["sequence"]?.uint, sequence > 0,
              let rollout = assignment["rollout_basis_points"]?.uint, rollout <= 10_000,
              let runtime = assignment["runtime"]?.text, ReleaseV3Wire.validDigest(runtime),
              let releaseID = assignment["release_id"]?.text, ReleaseV3Wire.validID(releaseID) else {
            throw MixerFailure("update.assignment", "The signed v3 assignment lacks valid release coordinates.")
        }
        guard options.channel.map({ $0 == channel }) ?? true,
              options.rollout.map({ $0 == rollout }) ?? true,
              action == .publish || options.target == artifact else {
            throw MixerFailure("update.intent", "The signed assignment must match the requested channel, rollout and artifact.")
        }

        let project = ReleaseRESTV3.Project(organizationID: options.organization, projectID: options.project)

        if action == .publish {
            let candidate = fileURL(options.target)
            let signedManifest = try ReleaseRESTV3.SignedManifest(
                read(candidate.appendingPathComponent("signed-manifest.json"),
                     maximum: ReleaseRESTV3.signedDocumentMaximumBytes))
            let manifest = signedManifest.value
            guard manifest["scope"] == assignment["scope"], manifest["runtime"]?.text == runtime,
                  manifest["release_id"]?.text == releaseID,
                  try SourceDigest.sha256(CanonicalValue.object(manifest).canonicalCBOR()) == artifact else {
                throw MixerFailure("update.intent", "The signed manifest must match the assignment's artifact, scope, runtime and release.")
            }
            let payload = try read(candidate.appendingPathComponent("payload.wasm"), maximum: 4 * 1_048_576)
            let upload = try await client.send(ReleaseRESTV3.upload(
                project, manifestSHA256: artifact, body: .init(signedManifest: signedManifest, payload: payload)))
            guard upload.artifactSHA256 == artifact, upload.immutable else { throw invalidResponse("upload") }
            let validation = try await client.send(ReleaseRESTV3.validate(project, body: .init(artifactSHA256: artifact)))
            guard validation.artifactSHA256 == artifact, validation.protocolValid else { throw invalidResponse("validate") }
        }

        if let file = options.health {
            guard rollout == 0 else {
                throw MixerFailure("update.intent", "Halt requires a signed zero-percent assignment.")
            }
            let bytes = try read(file, maximum: 4096)
            guard let sample = try? StrictJSON.decode(ReleaseRESTV3.Health.self, from: bytes, maximumBytes: 4096),
                  sample.sequence > 0, sample.sequence < sequence, sample.adverseSignals > 0 else {
                throw MixerFailure("update.health", "Supply a health sample for an earlier positive sequence with activated, pending and positive adverse_signals counts.")
            }
            let response = try await client.send(ReleaseRESTV3.halt(
                project, channel: channel, body: .init(health: sample, signedAssignment: signedAssignment)))
            guard response.scope == scope, response.runtime == runtime, response.channel == channel,
                  response.artifactSHA256 == artifact, response.haltSequence == sequence,
                  response.health == sample else { throw invalidResponse("halt") }
            return Receipt(action: action, artifactSHA256: artifact, sequence: sequence,
                           rolloutBasisPoints: rollout, delivery: "local_only", health: sample)
        }

        let body = ReleaseRESTV3.AssignmentRequest(signedAssignment: signedAssignment)
        let result: ReleaseRESTV3.ChannelResponse
        switch action {
        case .publish:
            result = try await client.send(ReleaseRESTV3.publish(project, channel: channel, body: body))
        case .promote:
            result = try await client.send(ReleaseRESTV3.promote(project, channel: channel, body: body))
        case .rollback:
            guard let reason = options.reason else { throw invalidArguments(action) }
            result = try await client.send(ReleaseRESTV3.rollback(project, channel: channel, body: body, reason: reason))
        case .halt:
            throw invalidArguments(action)
        }
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
        let health: URL?
        let channel: String?
        let rollout: UInt64?
        let reason: String?

        init(_ action: Action, _ arguments: [String]) throws {
            let common: Set<String> = ["--organization", "--project", "--assignment"]
            let specific: Set<String> = switch action {
            case .publish: ["--channel", "--rollout"]
            case .promote: ["--rollout"]
            case .rollback: ["--reason"]
            case .halt: ["--health", "--channel"]
            }
            let required = common.union(specific)
            let usage = invalidArguments(action)
            let (target, values) = try optionValues(
                arguments, allowed: required.union(["--channel"]), required: required, usage: usage)
            guard let org = values["--organization"], ReleaseV3Wire.validID(org),
                  let project = values["--project"], ReleaseV3Wire.validID(project),
                  let assignment = values["--assignment"],
                  action == .publish || ReleaseV3Wire.validDigest(target) else { throw usage }
            self.target = target
            organization = org
            self.project = project
            self.assignment = fileURL(assignment)
            health = values["--health"].map(fileURL)
            channel = values["--channel"]
            if let channel, !ReleaseV3Wire.validID(channel) { throw usage }
            if let percent = values["--rollout"] {
                guard percent.utf8.allSatisfy({ (48...57).contains($0) }),
                      let value = UInt64(percent), (1...100).contains(value) else { throw usage }
                rollout = value * 100
            } else {
                rollout = nil
            }
            reason = values["--reason"]
            if let reason, !validReason(reason) {
                throw MixerFailure("update.reason", "Supply a rollback reason of 1–512 printable ASCII bytes without surrounding spaces.")
            }
        }
    }

    private static func optionValues(
        _ arguments: [String], allowed: Set<String>, required: Set<String>, usage: MixerFailure
    ) throws -> (String, [String: String]) {
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
        guard required.isSubset(of: values.keys) else { throw usage }
        return (target, values)
    }

    private static func positiveSequence(_ text: String?) -> UInt64? {
        guard let text, text.utf8.allSatisfy({ (48...57).contains($0) }),
              let value = UInt64(text), value > 0 else { return nil }
        return value
    }

    private static func validReason(_ reason: String) -> Bool {
        (1...512).contains(reason.utf8.count) && reason.first != " " && reason.last != " " &&
            reason.utf8.allSatisfy { (32...126).contains($0) }
    }

    private static func stageVariant(
        _ signed: ReleaseRESTV3.SignedAssignment, platform: String, project: ReleaseRESTV3.Project, app: String
    ) throws -> StageReceipt.Variant {
        let assignment = signed.value
        guard let scope = assignment["scope"]?.object,
              scope["organization"]?.text == project.organizationID, scope["project"]?.text == project.projectID,
              scope["app"]?.text == app, scope["platform"]?.text == platform,
              let environment = scope["environment"]?.text, ReleaseV3Wire.validID(environment),
              let release = assignment["release_id"]?.text, ReleaseV3Wire.validID(release),
              let artifact = assignment["artifact_sha256"]?.text, ReleaseV3Wire.validDigest(artifact),
              let sequence = assignment["sequence"]?.uint, sequence > 0,
              let rollout = assignment["rollout_basis_points"]?.uint, rollout <= 10_000 else {
            throw MixerFailure("update.assignment", "The signed \(platform) assignment must match the requested organization, project and application.")
        }
        return StageReceipt.Variant(sequence: sequence, artifactSHA256: artifact, rolloutBasisPoints: rollout)
    }

    private static func makeClient() throws -> Client {
        let environment = ProcessInfo.processInfo.environment
        let origin = try localOrigin(environment["MIXER_RELEASE_ORIGIN"])
        guard let token = environment["MIXER_RELEASE_TOKEN"], !token.isEmpty, token.utf8.count <= 4089,
              token.utf8.allSatisfy({ (33...126).contains($0) }) else {
            throw MixerFailure("update.credential", "Set MIXER_RELEASE_TOKEN to the scoped local publisher bearer token.")
        }
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
        return Client(session: session, origin: origin, token: token)
    }

    private struct Client {
        let session: URLSession
        let origin: URL
        let token: String

        func send<T>(_ operation: ReleaseV3Operation<T>) async throws -> T {
            let stage = operation.stage
            let request = operation.urlRequest(origin: origin, token: token)

            let response: URLResponse
            let stream: URLSession.AsyncBytes
            do {
                (stream, response) = try await session.bytes(for: request)
            } catch {
                throw transportFailure(stage)
            }
            let maximum = ReleaseRESTV3.responseMaximumBytes
            guard let http = response as? HTTPURLResponse, http.url == request.url,
                  http.mimeType == ReleaseRESTV3.mediaType, http.expectedContentLength <= maximum else {
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

            guard operation.statuses.contains(http.statusCode) else {
                let error = try? StrictJSON.decode(ServiceError.self, from: data, maximumBytes: maximum)
                let detail = error.map { " (\($0.error.code.rawValue))" } ?? ""
                throw MixerFailure("update.\(stage).rejected", "Local v3 origin returned HTTP \(http.statusCode)\(detail).")
            }
            guard let value = try? operation.decodeSuccess(data) else {
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
            case invalid_health, invalid_halt, stale_rollout
            case assignment_rejected, invalid_promotion, invalid_rollback, idempotency_conflict
            case storage_unavailable, local_capacity, rate_limit, concurrency_limit, not_found
        }
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

    private static func invalidArguments(_ action: Action) -> MixerFailure {
        MixerFailure("update.arguments", "Run mixer help for the local update \(action.rawValue) syntax.")
    }

    private static func invalidResponse(_ stage: String) -> MixerFailure {
        MixerFailure("update.\(stage).response", "Unexpected local v3 response. Retry the same signed inputs and options to resolve the outcome.")
    }

    private static func transportFailure(_ stage: String) -> MixerFailure {
        MixerFailure("update.\(stage).transport", "Local v3 request could not be completed. Retry the same signed inputs and options to resolve the outcome.")
    }
}
