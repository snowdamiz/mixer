import Foundation
import XCTest
import MixerCapabilities
import MixerRuntimeIdentity
import MixerUpdates
@testable import MixerCapabilityActivation

final class InstalledMaterialTests: XCTestCase {
    func testOriginalRealNativePreimageAndZeroOneTwoCapabilities() throws {
        let preimage = try Fixture.resource("native-preimage.json")
        XCTAssertNotEqual(preimage.last, 10)
        XCTAssertEqual(ReleaseVerifier.sha256(preimage), CapabilityNativeIdentity.sha256)
        XCTAssertEqual(CapabilityNativeIdentity.sha256, MaterialRules.native)
        XCTAssertEqual(CapabilitySchemas.contractSHA256, MaterialRules.semantic)
        for ids in [[], [Fixture.http], [Fixture.storage], [Fixture.http, Fixture.storage]] {
            var fixture = try Fixture()
            fixture.keep(ids)
            let policy = try fixture.admit()
            XCTAssertEqual(policy.runtimeFingerprint, try CapabilityRuntimeIdentity(json: fixture.identityBytes).fingerprint)
            XCTAssertEqual(policy.installed.configurations.count, ids.count)
            XCTAssertEqual(policy.installed.files.count, 1 + 2 * ids.count)
        }
    }

    func testEveryRoleRequiredUniqueAndUsed() throws {
        let fixture = try Fixture(), files = fixture.materials
        for index in files.indices {
            var missing = files; missing.remove(at: index)
            XCTAssertThrowsError(try fixture.admit(materials: missing))
            var duplicate = files; duplicate[index] = files[(index + 1) % files.count]
            XCTAssertThrowsError(try fixture.admit(materials: duplicate))
        }
        var unknown = files
        unknown[0] = .init(role: .configuration(capabilityID: "uninstalled"), bytes: fixture.files["bridge.json"]!)
        XCTAssertThrowsError(try fixture.admit(materials: unknown))
        unknown[0] = .init(role: .installedGrant(capabilityID: String(repeating: "x", count: 131_073)), bytes: Data())
        XCTAssertThrowsError(try fixture.admit(materials: unknown))
        for roleID in ["", String(repeating: "x", count: 128), String(repeating: "x", count: 129),
                       Fixture.http + String(repeating: "x", count: 1_048_576), "network.http.v1é", "network/http/v1"] {
            unknown[0] = .init(role: .configuration(capabilityID: roleID), bytes: Data())
            XCTAssertThrowsError(try fixture.admit(materials: unknown))
        }
        XCTAssertThrowsError(try fixture.admit(materials: files + [files[0]]))
    }

    func testExactHashBeforeSchemaForEachMaterial() throws {
        for name in Fixture.materialNames {
            var fixture = try Fixture()
            fixture.files[name]!.append(32)
            XCTAssertThrowsError(try fixture.admit()) { error in XCTAssertEqual((error as? UpdateError)?.code, "installed.capability.digest") }
        }
        var fixture = try Fixture()
        fixture.roots.append(32)
        XCTAssertThrowsError(try fixture.admit()) { error in XCTAssertEqual((error as? UpdateError)?.code, "installed.capability.roots.digest") }
    }

    func testCanonicalFormsRejectEvenWhenIdentityHashesMatch() throws {
        let malformed: [Data] = [
            Data("{\"schema\":1,\"burst\":8,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":8, \"schema\":1,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":8,\"schema\":1,\"starts_per_second\":32}".utf8),
            Data("{\"burst\":8,\"schema\":1,\"starts_per_second\":32}\r\n".utf8),
            Data("{\"burst\":8,\"schema\":1,\"starts_per_second\":32}\n\n".utf8),
            Data("{\"burst\":8,\"schema\":1,\"schema\":1,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":8,\"sche\\u006da\":1,\"schema\":1,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":8,\"sche\\u006da\":1,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":08,\"schema\":1,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":8.0,\"schema\":1,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":8e0,\"schema\":1,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":-1,\"schema\":1,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":+8,\"schema\":1,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":null,\"schema\":1,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":true,\"schema\":1,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":8,\"schema\":1,\"starts_per_second\":32}\n{}".utf8),
            Data("{/*comment*/\"burst\":8,\"schema\":1,\"starts_per_second\":32}\n".utf8),
            Data([0xef, 0xbb, 0xbf]) + Data("{}\n".utf8),
            Data("{\"burst\":\"\\ud800\",\"schema\":1,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":\"".utf8) + Data([0xff]) + Data("\",\"schema\":1,\"starts_per_second\":32}\n".utf8),
            Data("{\"burst\":18446744073709551616,\"schema\":1,\"starts_per_second\":32}\n".utf8),
        ]
        for (index, bytes) in malformed.enumerated() {
            var fixture = try Fixture(); fixture.bind("bridge.json", bytes)
            XCTAssertThrowsError(try fixture.admit(), "canonical/malformed case \(index)")
        }
        var fixture = try Fixture()
        let escapedSlashes = String(decoding: fixture.files["http-grant.json"]!, as: UTF8.self).replacingOccurrences(of: "/", with: "\\/")
        fixture.bind("http-grant.json", Data(escapedSlashes.utf8))
        XCTAssertThrowsError(try fixture.admit())
    }

    func testClosedMandatorySchemasForEveryMaterial() throws {
        for name in Fixture.materialNames {
            let original = try Fixture().object(name)
            for key in original.keys {
                var fields = original; fields.removeValue(forKey: key)
                var fixture = try Fixture(); fixture.bind(name, try Fixture.encode(fields))
                XCTAssertThrowsError(try fixture.admit(), "missing \(name).\(key)")
                fields = original; fields[key] = NSNull()
                fixture = try Fixture(); fixture.bind(name, try Fixture.encode(fields))
                XCTAssertThrowsError(try fixture.admit(), "null \(name).\(key)")
            }
            var fields = original; fields["unexpected"] = 1
            var fixture = try Fixture(); fixture.bind(name, try Fixture.encode(fields))
            XCTAssertThrowsError(try fixture.admit(), "unknown \(name)")
        }
    }

    func testConfigurationLimitsAndImplementationBinding() throws {
        let changes: [(String, String, Any)] = [
            ("bridge.json", "schema", 2), ("bridge.json", "burst", 0), ("bridge.json", "burst", 9),
            ("bridge.json", "starts_per_second", 0), ("bridge.json", "starts_per_second", 33),
            ("http.json", "maximum_concurrent_requests", 0), ("http.json", "maximum_concurrent_requests", 9),
            ("http.json", "maximum_concurrent_requests", 7), ("http.json", "implementation", "arbitrary-http"),
            ("storage.json", "implementation", "other-kv"), ("storage.json", "container", "arbitrary"),
            ("storage.json", "maximum_total_bytes", 0), ("storage.json", "maximum_total_bytes", 4_194_305),
            ("storage.json", "maximum_entries", 0), ("storage.json", "maximum_entries", 1025),
        ]
        for (name, key, value) in changes {
            var fixture = try Fixture(); var fields = try fixture.object(name); fields[key] = value
            fixture.bind(name, try Fixture.encode(fields)); XCTAssertThrowsError(try fixture.admit(), "\(name).\(key)=\(value)")
        }
        var fixture = try Fixture()
        for name in ["bridge.json", "storage.json"] {
            var fields = try fixture.object(name)
            if name == "bridge.json" { fields["burst"] = 1; fields["starts_per_second"] = 1 }
            else { fields["maximum_total_bytes"] = 1; fields["maximum_entries"] = 1 }
            fixture.bind(name, try Fixture.encode(fields))
        }
        _ = try fixture.admit()
    }

    func testDirectoryComponentRejectsAllPathForms() throws {
        for component in ["", ".", "..", "a/b", "a\\b", "/tmp", "a.b", "a b", "é", "a\n", String(repeating: "x", count: 65)] {
            var fixture = try Fixture(); var fields = try fixture.object("storage.json"); fields["directory_component"] = component
            fixture.bind("storage.json", try Fixture.encode(fields)); XCTAssertThrowsError(try fixture.admit(), component)
        }
        for component in ["a", String(repeating: "A", count: 64), "09_-azAZ"] {
            var fixture = try Fixture(); var fields = try fixture.object("storage.json"); fields["directory_component"] = component
            fixture.bind("storage.json", try Fixture.encode(fields)); _ = try fixture.admit()
        }
    }

    func testGrantDenialsRetainedWithoutInventedPermissionsOrNamespaces() throws {
        var fixture = try Fixture()
        for name in ["http-grant.json", "storage-grant.json"] {
            var fields = try fixture.object(name)
            for key in ["permissions", "origins", "methods", "namespaces"] { fields[key] = [String]() }
            fixture.bind(name, try Fixture.encode(fields))
        }
        let policy = try fixture.admit()
        for grant in policy.installed.grants.values {
            XCTAssertTrue(grant.permissions.isEmpty); XCTAssertTrue(grant.namespaces.isEmpty)
            XCTAssertTrue(grant.origins.isEmpty); XCTAssertTrue(grant.methods.isEmpty)
        }
    }

    func testGrantFamilyRulesOrderingAndBounds() throws {
        let changes: [(String, String, Any)] = [
            ("http-grant.json", "capability_id", Fixture.storage), ("http-grant.json", "schema_sha256", String(repeating: "0", count: 64)),
            ("http-grant.json", "permissions", ["storage.appPrivate"]), ("http-grant.json", "permissions", ["network.https", "network.https"]),
            ("http-grant.json", "namespaces", ["x"]), ("http-grant.json", "methods", ["get"]),
            ("http-grant.json", "methods", ["PUT", "GET"]), ("http-grant.json", "methods", ["GET", "GET"]),
            ("http-grant.json", "origins", Array(repeating: "https://a.example", count: 33)),
            ("storage-grant.json", "origins", ["https://a.example"]), ("storage-grant.json", "methods", ["GET"]),
            ("storage-grant.json", "permissions", ["network.https"]), ("storage-grant.json", "namespaces", ["../x"]),
            ("storage-grant.json", "namespaces", [String(repeating: "x", count: 65)]), ("storage-grant.json", "namespaces", ["b", "a"]),
            ("storage-grant.json", "namespaces", ["a", "a"]), ("storage-grant.json", "namespaces", ["é"]),
        ]
        for (name, key, value) in changes {
            var fixture = try Fixture(); var fields = try fixture.object(name); fields[key] = value
            fixture.bind(name, try Fixture.encode(fields)); XCTAssertThrowsError(try fixture.admit(), "\(name).\(key)=\(value)")
        }
        var fixture = try Fixture(); var fields = try fixture.object("storage-grant.json")
        fields["namespaces"] = (0..<32).map { String(format: "ns%02d", $0) }; fixture.bind("storage-grant.json", try Fixture.encode(fields)); _ = try fixture.admit()
    }

    func testOriginGrammarHasNoURLNormalization() throws {
        let bad = ["http://a.example", "https://A.example", "https://a.example/", "https://a.example:443", "https://a.example:0443",
                   "https://a.example:0", "https://a.example:65536", "https://-a.example", "https://a-.example", "https://a..example",
                   "https://a.example?x", "https://a.example#x", "https://u@a.example", "https://[::1]", "https://a.example:",
                   "https://" + String(repeating: "a", count: 64) + ".example", "https://é.example"]
        for origin in bad {
            var fixture = try Fixture(); var fields = try fixture.object("http-grant.json"); fields["origins"] = [origin]
            fixture.bind("http-grant.json", try Fixture.encode(fields)); XCTAssertThrowsError(try fixture.admit(), origin)
        }
        var fixture = try Fixture(); var fields = try fixture.object("http-grant.json")
        fields["origins"] = ["https://a", "https://a.example:1", "https://a.example:65535"]
        fixture.bind("http-grant.json", try Fixture.encode(fields)); _ = try fixture.admit()
    }

    func testKnownNativeSchemaAndContractSubstitutionFails() throws {
        for field in ["native_sha256", "schema_sha256", "id"] {
            var fixture = try Fixture(); var capabilities = fixture.identity["capabilities"] as! [[String: Any]]
            capabilities[0][field] = field == "id" ? "network.unknown.v1" : String(repeating: "0", count: 64)
            fixture.identity["capabilities"] = capabilities; XCTAssertThrowsError(try fixture.admit(), field)
        }
        var fixture = try Fixture(); var execution = fixture.identity["capability_execution"] as! [String: Any]
        execution["contract_sha256"] = String(repeating: "0", count: 64); fixture.identity["capability_execution"] = execution
        XCTAssertThrowsError(try fixture.admit())
    }

    func testRawRootsAreBoundBeforeStrictClosedDecoding() throws {
        var fixture = try Fixture()
        fixture.bindRoots(Data(" \n".utf8) + fixture.roots + Data(" \n".utf8))
        _ = try fixture.admit() // Exact raw binding; roots have no material canonical rule.
        var roots = try JSONSerialization.jsonObject(with: fixture.roots) as! [[String: Any]]
        let original = roots[0]
        for key in original.keys {
            var root = original; root.removeValue(forKey: key)
            fixture = try Fixture(); fixture.bindRoots(try Fixture.encode([root])); XCTAssertThrowsError(try fixture.admit(), key)
        }
        let modifications: [(String, Any)] = [("unexpected", 1), ("public_key", "AA=="), ("public_key", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"),
            ("artifact", false), ("not_before_unix", 100), ("scope", ["organization":"bad/"])]
        for (key, value) in modifications {
            var root = original; root[key] = value
            if key == "artifact" { root["assignment"] = false }
            if key == "not_before_unix" { root["not_after_unix"] = 99 }
            fixture = try Fixture(); fixture.bindRoots(try Fixture.encode([root])); XCTAssertThrowsError(try fixture.admit(), key)
        }
        fixture = try Fixture(); fixture.bindRoots(try Fixture.encode([original, original])); XCTAssertThrowsError(try fixture.admit())
        fixture.bindRoots(Data("[]".utf8)); XCTAssertThrowsError(try fixture.admit())
        fixture.bindRoots(try Fixture.encode(original)); XCTAssertThrowsError(try fixture.admit())
        roots = (0..<128).map { index in var root = original; root["key_id"] = "root-\(index)"; return root }
        fixture = try Fixture(); fixture.bindRoots(try Fixture.encode(roots)); _ = try fixture.admit()
        roots.append(original); fixture.bindRoots(try Fixture.encode(roots)); XCTAssertThrowsError(try fixture.admit())
    }

    func testSizesAndBoundedScannerEdges() throws {
        let fixture = try Fixture()
        XCTAssertThrowsError(try fixture.admit(identityBytes: Data(repeating: 32, count: 131_073)))
        XCTAssertThrowsError(try fixture.admit(rootsBytes: Data(repeating: 32, count: 65_537)))
        XCTAssertThrowsError(try fixture.admit(materials: [.init(role: .bridgePolicy, bytes: Data(repeating: 32, count: 65_537))]))
        // At each exact byte limit, ordinary bounded parsing, rather than the
        // pre-copy size guard, decides validity.
        var paddedIdentity = fixture.identityBytes
        paddedIdentity.append(Data(repeating: 32, count: 131_072 - paddedIdentity.count))
        _ = try fixture.admit(identityBytes: paddedIdentity)
        var paddedRoots = fixture.roots
        paddedRoots.append(Data(repeating: 32, count: 65_536 - paddedRoots.count))
        var rebound = fixture; rebound.bindRoots(paddedRoots); _ = try rebound.admit()
        XCTAssertNoThrow(try MaterialJSON.decode(Data(("{\"x\":\"" + String(repeating: "a", count: 65_527) + "\"}\n").utf8)))
        let depth8 = "{\"x\":" + String(repeating: "[", count: 7) + "0" + String(repeating: "]", count: 7) + "}\n"
        XCTAssertNoThrow(try MaterialJSON.decode(Data(depth8.utf8)))
        let depth9 = "{\"x\":" + String(repeating: "[", count: 8) + "0" + String(repeating: "]", count: 8) + "}\n"
        XCTAssertThrowsError(try MaterialJSON.decode(Data(depth9.utf8)))
        for count in [8190, 8191] {
            let bytes = Data(("{\"x\":[" + Array(repeating: "0", count: count).joined(separator: ",") + "]}\n").utf8)
            if count == 8190 { XCTAssertNoThrow(try MaterialJSON.decode(bytes)) }
            else { XCTAssertThrowsError(try MaterialJSON.decode(bytes)) }
        }
        for bytes in [Data(depth9.utf8), Data(("{\"x\":[" + Array(repeating: "0", count: 8191).joined(separator: ",") + "]}\n").utf8)] {
            var rebound = fixture; rebound.bind("bridge.json", bytes); XCTAssertThrowsError(try rebound.admit())
        }
    }

    func testExternallyBackedInputMutationCannotChangeCapturedValues() throws {
        var fixture = try Fixture()
        var allocations: [UnsafeMutableRawPointer] = []
        func external(_ bytes: Data) -> Data {
            let pointer = UnsafeMutableRawPointer.allocate(byteCount: bytes.count, alignment: 1)
            bytes.copyBytes(to: pointer.assumingMemoryBound(to: UInt8.self), count: bytes.count)
            allocations.append(pointer)
            return Data(bytesNoCopy: pointer, count: bytes.count, deallocator: .none)
        }
        defer { allocations.forEach { $0.deallocate() } }
        for name in Fixture.materialNames { fixture.files[name] = external(fixture.files[name]!) }
        fixture.roots = external(fixture.roots)
        let identity = external(fixture.identityBytes)
        let policy = try fixture.admit(identityBytes: identity)
        let expectedFiles = policy.installed.files, expectedRoots = policy.installed.rootsBytes
        for (index, pointer) in allocations.enumerated() { pointer.storeBytes(of: UInt8(index), as: UInt8.self) }
        XCTAssertEqual(policy.installed.files, expectedFiles)
        XCTAssertEqual(policy.installed.rootsBytes, expectedRoots)
        XCTAssertEqual(policy.runtimeFingerprint, policy.installed.identity.fingerprint)
        XCTAssertEqual(policy.installed.bridge.burst, 8)
        XCTAssertEqual(policy.installed.grants[Fixture.storage]?.namespaces, ["material_test"])
    }

    func testInitializationDoesNotCreatePrivateContainerOrStorage() throws {
        let path = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-material-no-io-" + UUID().uuidString, isDirectory: true)
        XCTAssertFalse(FileManager.default.fileExists(atPath: path.path))
        let policy = try Fixture().admit(container: path)
        XCTAssertEqual(policy.installed.privateContainer, path)
        XCTAssertFalse(FileManager.default.fileExists(atPath: path.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: path.appendingPathComponent("material_test").path))
    }

    func testConcurrentImmutableConstructionAndValueCopies() throws {
        let fixture = try Fixture(), identity = fixture.identityBytes, roots = fixture.roots, files = fixture.materials
        let expected = try fixture.admit().runtimeFingerprint
        DispatchQueue.concurrentPerform(iterations: 32) { _ in
            do {
                let value = try InstalledCapabilityExecution(identityJSON: identity, materials: files, trustRootsJSON: roots,
                                                             privateContainer: URL(fileURLWithPath: "/never-created-material-concurrency"))
                let copy = value
                XCTAssertEqual(copy.runtimeFingerprint, expected)
                XCTAssertEqual(copy.installed.grants[Fixture.storage]?.namespaces, ["material_test"])
            } catch { XCTFail("Concurrent immutable admission failed: \(error)") }
        }
    }
}

private struct Fixture {
    static let http = "network.http.v1", storage = "storage.keyValue.v1"
    static let materialNames = ["bridge.json", "http.json", "http-grant.json", "storage.json", "storage-grant.json"]
    var identity: [String: Any]
    var files: [String: Data]
    var roots: Data
    init() throws {
        identity = try JSONSerialization.jsonObject(with: Self.resource("identity.json")) as! [String: Any]
        files = try Dictionary(uniqueKeysWithValues: Self.materialNames.map { ($0, try Self.resource($0)) })
        roots = try Self.resource("roots.json")
    }
    static func resource(_ name: String) throws -> Data {
        try Data(contentsOf: Bundle.module.url(forResource: name, withExtension: nil, subdirectory: "Fixtures")!)
    }
    static func encode(_ value: Any) throws -> Data {
        try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes]) + Data([10])
    }
    var identityBytes: Data { try! Self.encode(identity) }
    func object(_ name: String) throws -> [String: Any] { try JSONSerialization.jsonObject(with: files[name]!) as! [String: Any] }
    mutating func keep(_ ids: [String]) {
        identity["capabilities"] = (identity["capabilities"] as! [[String: Any]]).filter { ids.contains($0["id"] as! String) }
    }
    mutating func bind(_ name: String, _ bytes: Data) {
        files[name] = bytes
        let digest = ReleaseVerifier.sha256(bytes)
        if name == "bridge.json" {
            var value = identity["capability_execution"] as! [String: Any]; value["bridge_policy_sha256"] = digest; identity["capability_execution"] = value
        } else {
            var capabilities = identity["capabilities"] as! [[String: Any]]
            let id = name.hasPrefix("http") ? Self.http : Self.storage
            let index = capabilities.firstIndex { $0["id"] as? String == id }!
            capabilities[index][name.contains("grant") ? "grants_sha256" : "configuration_sha256"] = digest
            identity["capabilities"] = capabilities
        }
    }
    mutating func bindRoots(_ bytes: Data) {
        roots = bytes; var build = identity["build"] as! [String: Any]
        build["trust_roots_sha256"] = ReleaseVerifier.sha256(bytes); identity["build"] = build
    }
    var materials: [CapabilityMaterialFile] {
        var result = [CapabilityMaterialFile(role: .bridgePolicy, bytes: files["bridge.json"]!)]
        let ids = (identity["capabilities"] as! [[String: Any]]).map { $0["id"] as! String }
        for id in ids {
            let prefix = id == Self.http ? "http" : "storage"
            result.append(.init(role: .configuration(capabilityID: id), bytes: files[prefix + ".json"]!))
            result.append(.init(role: .installedGrant(capabilityID: id), bytes: files[prefix + "-grant.json"]!))
        }
        return result
    }
    func admit(materials: [CapabilityMaterialFile]? = nil, identityBytes: Data? = nil, rootsBytes: Data? = nil,
               container: URL = URL(fileURLWithPath: "/mixer-material-test-never-created")) throws -> InstalledCapabilityExecution {
        try InstalledCapabilityExecution(identityJSON: identityBytes ?? self.identityBytes, materials: materials ?? self.materials,
                                         trustRootsJSON: rootsBytes ?? roots, privateContainer: container)
    }
}
