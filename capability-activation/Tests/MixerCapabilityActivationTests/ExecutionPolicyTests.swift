import Foundation
import CryptoKit
import XCTest
import MixerCapabilities
@_spi(CapabilityDurableV3) import MixerUpdates
@testable import MixerCapabilityActivation

final class ExecutionPolicyTests: XCTestCase {
    func testSignedSetsIntersectInstalledMaterialAndKeepConcreteQuotas() throws {
        let f = try PolicyFixture(), installed = try f.installed()
        var grants = try f.grants()
        grants[0]["origins"] = ["https://a.example", "https://outside.example"]
        grants[0]["methods"] = ["GET", "POST"]
        grants[1]["namespaces"] = ["Material_test", "material_test", "outside"]
        let signed = try f.signed(installed: installed, grants: grants)
        let value = try CapabilityExecutionPolicy(installed: installed, artifact: signed.artifact, payload: f.payload, now: 100)
        XCTAssertEqual(value.http?.origins, ["https://a.example"])
        XCTAssertEqual(value.http?.methods, ["GET"])
        XCTAssertEqual(value.http?.maximumConcurrentRequests, 8)
        XCTAssertEqual(value.storage?.namespaces, ["material_test"])
        XCTAssertEqual(value.storage?.directoryComponent, "material_test")
        XCTAssertEqual(value.storage?.maximumTotalBytes, 4_194_304)
        XCTAssertEqual(value.storage?.maximumEntries, 1024)
        XCTAssertFalse(FileManager.default.fileExists(atPath: installed.privateContainer.path))
    }

    func testEveryEmptySignedDimensionDeniesItsAdapter() throws {
        let f = try PolicyFixture(), installed = try f.installed()
        for (index, field) in [(0, "permissions"), (0, "origins"), (0, "methods"), (1, "permissions"), (1, "namespaces")] {
            var grants = try f.grants(); grants[index][field] = [String]()
            let signed = try f.signed(installed: installed, grants: grants)
            let p = try CapabilityExecutionPolicy(installed: installed, artifact: signed.artifact, payload: f.payload, now: 100)
            if index == 0 { XCTAssertNil(p.http, field); XCTAssertNotNil(p.storage) }
            else { XCTAssertNil(p.storage, field); XCTAssertNotNil(p.http) }
        }
        let empty = try f.signed(installed: installed, grants: [])
        let p = try CapabilityExecutionPolicy(installed: installed, artifact: empty.artifact, payload: f.payload, now: 100)
        XCTAssertNil(p.http); XCTAssertNil(p.storage)
    }

    func testEveryEmptyInstalledDimensionRemainsADenial() throws {
        for (name, field) in [("http-grant.json", "permissions"), ("http-grant.json", "origins"), ("http-grant.json", "methods"),
                              ("storage-grant.json", "permissions"), ("storage-grant.json", "namespaces")] {
            var f = try PolicyFixture(); let signedGrants = try f.grants()
            var grant = try f.object(name); grant[field] = [String](); try f.bind(name, grant)
            let installed = try f.installed(), signed = try f.signed(installed: installed, grants: signedGrants)
            let p = try CapabilityExecutionPolicy(installed: installed, artifact: signed.artifact, payload: f.payload, now: 100)
            if name.hasPrefix("http") { XCTAssertNil(p.http, field) } else { XCTAssertNil(p.storage, field) }
        }
    }

    func testDisjointAndCaseSensitiveSetsNeverAllocateFallbackConfiguration() throws {
        let f = try PolicyFixture(), installed = try f.installed()
        var grants = try f.grants(); grants[0]["origins"] = ["https://outside.example"]
        grants[1]["namespaces"] = ["Material_test"]
        let signed = try f.signed(installed: installed, grants: grants)
        let p = try CapabilityExecutionPolicy(installed: installed, artifact: signed.artifact, payload: f.payload, now: 100)
        XCTAssertNil(p.http); XCTAssertNil(p.storage)
    }

    func testExactMemoryFloorAndInstalledOnlySchedulerLimits() throws {
        let f = try PolicyFixture(), installed = try f.installed()
        for (bytes, pages): (UInt64, UInt32) in [(1,0), (65_535,0), (65_536,1), (65_537,1), (4_194_304,64)] {
            let signed = try f.signed(installed: installed, limits: .init(memoryBytes: bytes, fuel: 777, startupMilliseconds: 9))
            let p = try CapabilityExecutionPolicy(installed: installed, artifact: signed.artifact, payload: f.payload, now: 100)
            XCTAssertEqual(p.native.memoryPages, pages); XCTAssertEqual(p.native.fuel, 777); XCTAssertEqual(p.startupMilliseconds, 9)
            XCTAssertEqual(p.native.operandStack, 4096); XCTAssertEqual(p.native.callDepth, 64); XCTAssertEqual(p.native.hostCalls, 1024)
            XCTAssertEqual(p.native.maximumRequests, 8); XCTAssertEqual(p.native.reservationBytes, 8_388_608)
            XCTAssertEqual(p.native.timeoutMilliseconds, 30000); XCTAssertEqual(p.native.turnMilliseconds, 50)
            XCTAssertEqual(p.native.dispatchBurst, 8); XCTAssertEqual(p.native.dispatchesPerSecond, 32)
            XCTAssertEqual(p.native.batchTurns, 4); XCTAssertEqual(p.native.batchMilliseconds, 8)
        }
    }

    func testForeignContextCorruptionAndExpiredFreshAuthorityReject() throws {
        let f = try PolicyFixture(), installed = try f.installed(), foreign = try f.installed()
        let signed = try f.signed(installed: installed)
        XCTAssertThrowsError(try CapabilityExecutionPolicy(installed: foreign, artifact: signed.artifact, payload: f.payload, now: 100))
        XCTAssertThrowsError(try CapabilityExecutionPolicy(installed: installed, artifact: signed.artifact, payload: Data([0]), now: 100))
        XCTAssertThrowsError(try CapabilityExecutionPolicy(installed: installed, artifact: signed.artifact, payload: f.payload, now: 201))
        let copy = installed
        XCTAssertNoThrow(try CapabilityExecutionPolicy(installed: copy, artifact: signed.artifact, payload: f.payload, now: 100))
        let retained = try installed.verifier._verifyRetainedHealthySnapshotV3(exactManifest: signed.manifest,
            exactAssignment: signed.assignment, payload: f.payload, channel: "beta", installation: "policy-test", storedSequence: 7, acceptedSequence: 9)
        let p = try CapabilityExecutionPolicy(installed: installed, retained: retained, payload: f.payload)
        XCTAssertNotNil(p.http); XCTAssertNotNil(p.storage)
        XCTAssertThrowsError(try CapabilityExecutionPolicy(installed: foreign, retained: retained, payload: f.payload))
        XCTAssertThrowsError(try CapabilityExecutionPolicy(installed: installed, retained: retained, payload: Data()))
        // This helper does not claim that the synthetic retained record was healthy.
    }

    func testSDKDispatchUsesTheSameIntersection() async throws {
        let f = try PolicyFixture(), installed = try f.installed()
        var grants = try f.grants(); grants[0]["origins"] = ["https://a.example", "https://outside.example"]
        grants[0]["methods"] = ["GET", "POST"]
        let signed = try f.signed(installed: installed, grants: grants)
        let p = try CapabilityExecutionPolicy(installed: installed, artifact: signed.artifact, payload: f.payload, now: 100)
        let host = try CapabilityHost(policy: p.policy)
        for (url, method, expected) in [("https://a.example/x", "GET", CapabilityFailure.unavailable),
                                        ("https://a.example/x", "POST", .permissionDenied),
                                        ("https://outside.example/x", "GET", .permissionDenied),
                                        ("https://b.example:8443/x", "GET", .permissionDenied)] {
            let call = CapabilityCall(identity: try await host.issueRequestID(), operation: .http(.init(url: url, method: method, headers: [], bodyBase64: "", timeoutMilliseconds: 1000)))
            let bytes = try CapabilityCodec.encodeCall(call)
            let result: Data = try await withCheckedThrowingContinuation { continuation in
                Task {
                    do { try await host.submit(bytes) { continuation.resume(returning: $0) } }
                    catch { continuation.resume(throwing: error) }
                }
            }
            let completion = try CapabilityCodec.decodeCompletion(result, expected: call)
            XCTAssertEqual(completion.outcome, .failure(expected))
        }
        await host.close()
    }
}

/// Publicly reproducible test-only key and independently built signed envelopes.
private struct PolicyFixture {
    let key: Curve25519.Signing.PrivateKey
    let payload = Data("policy metadata test, not executable wasm".utf8)
    var identity: [String: Any]
    var files: [String: Data]
    let roots: Data
    init() throws {
        key = try Curve25519.Signing.PrivateKey(rawRepresentation: Data(SHA256.hash(data: Data("Mixer TEST ONLY execution policy fixture".utf8))))
        identity = try JSONSerialization.jsonObject(with: Self.resource("identity.json")) as! [String: Any]
        files = try Dictionary(uniqueKeysWithValues: ["bridge.json", "http.json", "http-grant.json", "storage.json", "storage-grant.json"].map { ($0, try Self.resource($0)) })
        var root = (try JSONSerialization.jsonObject(with: Self.resource("roots.json")) as! [[String: Any]])[0]
        root["public_key"] = key.publicKey.rawRepresentation.base64EncodedString(); root["not_after_unix"] = 200
        roots = try Self.encode([root]); var build = identity["build"] as! [String: Any]
        build["trust_roots_sha256"] = ReleaseVerifier.sha256(roots); identity["build"] = build
    }
    static func resource(_ name: String) throws -> Data { try Data(contentsOf: Bundle.module.url(forResource: name, withExtension: nil, subdirectory: "Fixtures")!) }
    static func encode(_ value: Any) throws -> Data { try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes]) + Data([10]) }
    func object(_ name: String) throws -> [String: Any] { try JSONSerialization.jsonObject(with: files[name]!) as! [String: Any] }
    func grants() throws -> [[String: Any]] { try [object("http-grant.json"), object("storage-grant.json")] }
    mutating func bind(_ name: String, _ value: [String: Any]) throws {
        files[name] = try Self.encode(value)
        var capabilities = identity["capabilities"] as! [[String: Any]]
        let index = name.hasPrefix("http") ? 0 : 1
        capabilities[index]["grants_sha256"] = ReleaseVerifier.sha256(files[name]!)
        identity["capabilities"] = capabilities
    }
    func installed() throws -> InstalledMaterial {
        let materials: [CapabilityMaterialFile] = [.init(role: .bridgePolicy, bytes: files["bridge.json"]!),
            .init(role: .configuration(capabilityID: CapabilitySchemas.httpID), bytes: files["http.json"]!),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.httpID), bytes: files["http-grant.json"]!),
            .init(role: .configuration(capabilityID: CapabilitySchemas.storageID), bytes: files["storage.json"]!),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.storageID), bytes: files["storage-grant.json"]!)]
        return try InstalledCapabilityExecution(identityJSON: Self.encode(identity), materials: materials, trustRootsJSON: roots,
            privateContainer: FileManager.default.temporaryDirectory.appendingPathComponent("mixer-policy-no-io-" + UUID().uuidString)).installed
    }
    func signed(installed: InstalledMaterial, grants: [[String: Any]]? = nil,
                limits: ResourceLimits = .init(memoryBytes: 1_048_576, fuel: 1000, startupMilliseconds: 1000)) throws -> (manifest: Data, assignment: Data, artifact: VerifiedArtifactV3) {
        let host = installed.identity.installedRuntime
        let scope = try JSONSerialization.jsonObject(with: JSONEncoder().encode(host.scope))
        let fields: [String: Any] = ["schema": 3, "scope": scope, "release_id": "policy-test", "source_commit": String(repeating: "a", count: 40),
            "provenance_id": "policy-test", "runtime": host.runtime, "protocol": 3, "guest_abi": 2, "ui_schema": 1,
            "capability_hashes": host.capabilityHashes,
            "capability_grants": ["schema": 1, "schema_sha256": VerifiedCapabilityGrantsV3.descriptorSHA256, "entries": try grants ?? self.grants()],
            "state_min": host.stateVersion, "state_max": host.stateVersion, "payload_sha256": ReleaseVerifier.sha256(payload),
            "compressed_bytes": payload.count, "expanded_bytes": payload.count, "compression": "none", "asset_hashes": [String: String](),
            "source_map_sha256": ReleaseVerifier.sha256(Data()), "limits": ["memory_bytes": limits.memoryBytes, "fuel": limits.fuel, "startup_milliseconds": limits.startupMilliseconds],
            "key_id": "material-test-root", "created_at_unix": 1]
        func envelope(_ fields: [String: Any], field: String, domain: String) throws -> Data {
            let value = try JSONDecoder().decode(CanonicalValue.self, from: Self.encode(fields))
            let signature = try key.signature(for: Data((domain + "\0").utf8) + value.canonicalCBOR())
            return try JSONEncoder().encode(CanonicalValue.object([field: value, "signature": .text(signature.base64EncodedString())]))
        }
        let manifest = try envelope(fields, field: "manifest", domain: "mixer.artifact.v3")
        let artifact = try installed.verifier.verifyArtifact(signedManifest: manifest, payload: payload, now: 100)
        let assignment = try envelope(["schema": 3, "scope": scope, "channel": "beta", "cohort": "sha256-v1", "rollout_basis_points": 10000,
            "sequence": 7, "release_id": "policy-test", "artifact_sha256": artifact.artifactSHA256, "runtime": host.runtime,
            "key_id": "material-test-root", "created_at_unix": 1], field: "assignment", domain: "mixer.assignment.v3")
        return (manifest, assignment, artifact)
    }
}
