#if os(macOS) && canImport(MixerApple)
import Foundation
import MixerUpdates
import XCTest

/// Runs the repository's developer release service on the selected loopback port.
/// Only the publisher helper sees the ephemeral bearer. Delivery reads are public.
@MainActor
final class ReleaseV3Loopback {
    private let child: FieldLogReleaseV3Child
    private let session: URLSession
    private let baseURL: URL
    private let port: UInt16
    private let host: InstalledRuntime
    private let bearer = UUID().uuidString

    init(executable: URL, port: UInt16, directory: URL, host: InstalledRuntime, roots: Data,
         name: String, actor: String) throws {
        self.host = host
        self.port = port
        baseURL = try XCTUnwrap(URL(string: "http://127.0.0.1:\(port)"))
        let sessionConfiguration = URLSessionConfiguration.ephemeral
        sessionConfiguration.timeoutIntervalForRequest = 2
        sessionConfiguration.timeoutIntervalForResource = 3
        sessionConfiguration.connectionProxyDictionary = [:]
        session = URLSession(configuration: sessionConfiguration)
        let hostObject = try FieldLogReleaseV3Fixture.object(FieldLogReleaseV3Fixture.encoder.encode(host))
        let scope = host.scope
        let configuration: [String: Any] = [
            "developer_mode": true, "listen": "127.0.0.1:\(port)",
            "data_directory": directory.appendingPathComponent("release-store").path,
            "tokens": [["sha256": ReleaseVerifier.sha256(Data(bearer.utf8)), "role": "publisher",
                        "organization": scope.organization, "project": scope.project, "actor": actor]],
            "hosts": [hostObject], "roots": try JSONSerialization.jsonObject(with: roots),
        ]
        let config = directory.appendingPathComponent("\(name)-config.json")
        try JSONSerialization.data(withJSONObject: configuration, options: .sortedKeys).write(to: config)
        child = try FieldLogReleaseV3Child(executable, environment: ["MIXER_SERVICE_CONFIG": config.path],
                                            directory: directory.appendingPathComponent("custody"), name: name)
    }

    func waitUntilReady() async throws {
        let deadline = ContinuousClock.now + .seconds(5)
        while ContinuousClock.now < deadline {
            if let data = try? await request("/healthz", status: 200),
               let value = try? FieldLogReleaseV3Fixture.object(data),
               value["mode"] as? String == "developer", value["production_ready"] as? Bool == false {
                return
            }
            try await Task.sleep(for: .milliseconds(50))
        }
        throw UpdateError("test.loopback", "Developer release service failed to listen")
    }

    func stop() async throws {
        session.invalidateAndCancel()
        try await child.finish(stop: true)
    }

    func runMixerUpdateHalt(_ executable: URL, artifact: String, assignment: Data, health: CanonicalValue,
                            directory: URL, name: String, expectedExitCode: Int32) async throws -> CanonicalValue {
        let assignmentFile = directory.appendingPathComponent(name + "-assignment.json")
        let healthFile = directory.appendingPathComponent(name + "-health.json")
        try assignment.write(to: assignmentFile, options: .withoutOverwriting)
        try FieldLogReleaseV3Fixture.encoder.encode(health).write(to: healthFile, options: .withoutOverwriting)
        let custody = directory.appendingPathComponent("custody")
        let scope = host.scope
        try requireOwnedListener()
        let command = try FieldLogReleaseV3Child(executable, arguments: [
            "update", "halt", artifact, "--channel", "beta", "--health", healthFile.path,
            "--organization", scope.organization, "--project", scope.project, "--assignment", assignmentFile.path,
        ], environment: ["MIXER_RELEASE_ORIGIN": baseURL.absoluteString, "MIXER_RELEASE_TOKEN": bearer],
            directory: custody, name: name)
        try await command.finish(expectedExitCode: expectedExitCode)
        try requireOwnedListener()
        let result = try Data(contentsOf: custody.appendingPathComponent(name + ".log"))
        return try StrictJSON.decode(CanonicalValue.self, from: result, maximumBytes: 4096)
    }

    private func requireOwnedListener() throws {
        guard child.ownsLoopbackListener(port: port) else {
            throw UpdateError("test.loopback", "The owned release service has no listener on its assigned port")
        }
    }

    var project: String {
        let scope = host.scope
        return "/v3/orgs/\(scope.organization)/projects/\(scope.project)"
    }

    func updates(installation: String, status: Int = 200) async throws -> Data {
        let scope = host.scope
        let path = "/v3/updates?organization=\(scope.organization)&project=\(scope.project)&app=\(scope.app)" +
            "&environment=\(scope.environment)&platform=\(scope.platform)&runtime=\(host.runtime)" +
            "&channel=beta&installation=\(installation)"
        return try await request(path, status: status)
    }

    func request(_ path: String, status: Int, method: String = "GET",
                         body: CanonicalValue? = nil, mutation: String? = nil, authenticated: Bool = false) async throws -> Data {
        try requireOwnedListener()
        let url = try XCTUnwrap(URL(string: baseURL.absoluteString + path))
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData)
        request.httpMethod = method
        if let body, let mutation {
            request.httpBody = try FieldLogReleaseV3Fixture.encoder.encode(body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.setValue(mutation, forHTTPHeaderField: "Idempotency-Key")
        }
        if mutation != nil || authenticated { request.setValue("Bearer " + bearer, forHTTPHeaderField: "Authorization") }
        let (data, response) = try await session.data(for: request)
        let actual = (response as? HTTPURLResponse)?.statusCode
        guard response.url == url, actual == status, data.count <= 65_536 else {
            throw UpdateError("test.http", "\(method) \(path) expected \(status), received \(String(describing: actual)): \(String(decoding: data.prefix(512), as: UTF8.self))")
        }
        print("FIELDLOG HTTP \(method) \(path.split(separator: "?")[0]) \(status)")
        return data
    }
}

@MainActor
final class FieldLogReleaseV3Loopback {
    private let service: ReleaseV3Loopback
    private let fixture: FieldLogReleaseV3Fixture

    init(executable: URL, port: UInt16, directory: URL, fixture: FieldLogReleaseV3Fixture) throws {
        self.fixture = fixture
        let roots = try Data(contentsOf: directory.appendingPathComponent("public-fixtures/roots.json"))
        service = try ReleaseV3Loopback(executable: executable, port: port, directory: directory,
            host: fixture.host, roots: roots, name: "service", actor: "fieldlog-test")
    }

    func waitUntilReady() async throws { try await service.waitUntilReady() }
    func stop() async throws { try await service.stop() }

    func upload(_ release: FieldLogReleaseV3Fixture.Release) async throws {
        let body = CanonicalValue.object([
            "signed_manifest": release.signedManifest, "payload": .text(release.payload.base64EncodedString()),
        ])
        _ = try await service.request(service.project + "/artifacts/" + release.digest, status: 201, method: "PUT",
                              body: body, mutation: "upload-" + release.name)
        _ = try await service.request(service.project + "/releases/validate", status: 200, method: "POST",
                              body: .object(["artifact_sha256": .text(release.digest)]), mutation: "validate-" + release.name)
    }

    func publish(sequence: Int, operation: String) async throws {
        let body = CanonicalValue.object(["signed_assignment": fixture.assignments[sequence - 1]])
        _ = try await service.request(service.project + "/channels/beta/" + operation, status: 200, method: "POST",
                              body: body, mutation: "\(operation)-\(sequence)")
    }

    func fetch(_ release: FieldLogReleaseV3Fixture.Release, sequence: Int) async throws -> (manifest: Data, assignment: Data, payload: Data) {
        let scope = fixture.host.scope
        let offer = try StrictJSON.decode(CanonicalValue.self,
            from: await service.updates(installation: fixture.configuration.installation))
        let assignment = try XCTUnwrap(offer.object?["signed_assignment"])
        XCTAssertEqual(assignment, fixture.assignments[sequence - 1])
        let expectedPath = "/v3/artifacts/\(release.digest)?organization=\(scope.organization)&project=\(scope.project)"
        guard offer.object?["artifact_url"]?.text == expectedPath else {
            throw UpdateError("test.delivery", "Published artifact URL escaped its expected scoped loopback route")
        }
        let artifact = try StrictJSON.decode(CanonicalValue.self, from: await service.request(expectedPath, status: 200))
        let manifest = try XCTUnwrap(artifact.object?["signed_manifest"])
        let payload = try XCTUnwrap(Data(base64Encoded: try XCTUnwrap(artifact.object?["payload"]?.text)))
        XCTAssertEqual(manifest, release.signedManifest)
        XCTAssertEqual(payload, release.payload)
        return (try FieldLogReleaseV3Fixture.encoder.encode(manifest), try FieldLogReleaseV3Fixture.encoder.encode(assignment), payload)
    }
}
#endif
