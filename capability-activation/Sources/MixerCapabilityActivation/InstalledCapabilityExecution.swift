import Foundation
import MixerCapabilities
import MixerRuntimeIdentity
import MixerUpdates

/// An untrusted input file. Bounds and private copies are applied together when
/// the complete installed material set is admitted.
public struct CapabilityMaterialFile: Sendable {
    public enum Role: Sendable {
        case bridgePolicy
        case configuration(capabilityID: String)
        case installedGrant(capabilityID: String)
    }
    fileprivate let role: Role
    fileprivate let bytes: Data
    public init(role: Role, bytes: Data) { self.role = role; self.bytes = bytes }
}

/// Immutable installed material only. This value grants no release or execution
/// authority and creates no session, adapter, task, directory or file.
public struct InstalledCapabilityExecution: Sendable {
    public let runtimeFingerprint: String
    // Module-private state is retained for a future private coordinator. In
    // particular, copies preserve this verifier's opaque context identity.
    let installed: InstalledMaterial

    public init(identityJSON: Data, materials: [CapabilityMaterialFile], trustRootsJSON: Data, privateContainer: URL) throws {
        guard identityJSON.count <= 131_072, trustRootsJSON.count <= 65_536, materials.count <= 5 else { throw materialError("size") }
        var total = 0
        for file in materials {
            guard file.bytes.count <= 65_536 else { throw materialError("size") }
            total += file.bytes.count
        }
        guard total <= 327_680 else { throw materialError("size") }

        // The identity parser takes its own owned snapshot. All subsequent
        // descriptor reads use that value, never the caller-backed input again.
        let identity = try CapabilityRuntimeIdentity(json: identityJSON)
        try MaterialRules.linkedIdentity(identity)
        let expected = Set(["bridge"] + identity.capabilities.flatMap { ["configuration:" + $0.id, "grant:" + $0.id] })
        let capabilityIDs = Set(identity.capabilities.map(\.id))
        var files: [String: Data] = [:]
        for file in materials {
            let key: String
            switch file.role {
            case .bridgePolicy: key = "bridge"
            case let .configuration(id):
                try MaterialRules.roleID(id, known: capabilityIDs); key = "configuration:" + id
            case let .installedGrant(id):
                try MaterialRules.roleID(id, known: capabilityIDs); key = "grant:" + id
            }
            guard expected.contains(key), files[key] == nil else { throw materialError("roles") }
            files[key] = MaterialRules.snapshot(file.bytes)
        }
        guard Set(files.keys) == expected else { throw materialError("roles") }
        let bridgeBytes = files["bridge"]!
        let bridge = try MaterialRules.bridge(MaterialRules.document(bridgeBytes, digest: identity.capabilityExecution.bridgePolicySHA256))
        var configurations: [String: InstalledConfiguration] = [:], grants: [String: InstalledGrant] = [:]
        for capability in identity.capabilities {
            let config = try MaterialRules.document(files["configuration:" + capability.id]!, digest: capability.configurationSHA256)
            configurations[capability.id] = try MaterialRules.configuration(config, id: capability.id, requests: identity.capabilityExecution.maximumRequests)
            let grant = try MaterialRules.document(files["grant:" + capability.id]!, digest: capability.grantsSHA256)
            grants[capability.id] = try MaterialRules.grant(grant, id: capability.id, schema: capability.schemaSHA256)
        }
        let rootsBytes = MaterialRules.snapshot(trustRootsJSON)
        guard let build = identity.descriptor.object?["build"]?.object, let digest = build["trust_roots_sha256"]?.text,
              ReleaseVerifier.sha256(rootsBytes) == digest else { throw materialError("roots.digest") }
        let roots = try StrictJSON.decode([TrustRoot].self, from: rootsBytes, maximumBytes: 65_536)
        guard roots.count <= 128 else { throw materialError("roots.count") }
        let verifier = try ReleaseVerifierV3(host: identity.installedRuntime, roots: roots)
        runtimeFingerprint = identity.fingerprint
        installed = InstalledMaterial(identity: identity, files: files, rootsBytes: rootsBytes, privateContainer: privateContainer,
                                      bridge: bridge, configurations: configurations, grants: grants, verifier: verifier)
    }
}

struct InstalledMaterial: Sendable {
    let identity: CapabilityRuntimeIdentity
    let files: [String: Data]
    let rootsBytes: Data
    let privateContainer: URL
    let bridge: InstalledBridgePolicy
    let configurations: [String: InstalledConfiguration]
    let grants: [String: InstalledGrant]
    let verifier: ReleaseVerifierV3
}
struct InstalledBridgePolicy: Sendable { let burst: UInt32; let startsPerSecond: UInt32 }
enum InstalledConfiguration: Sendable {
    case http(maximumConcurrentRequests: UInt32)
    case storage(directoryComponent: String, maximumTotalBytes: Int, maximumEntries: Int)
}
struct InstalledGrant: Sendable {
    let capabilityID: String
    let schemaSHA256: String
    let permissions: [String]
    let origins: [String]
    let methods: [String]
    let namespaces: [String]
}

enum MaterialRules {
    static let semantic = "ca53c3c2ea1d8f08020468cc5d458d86542e0806d6494840557e591342f1154e"
    static let native = "4fcc770e62d39b415e657ce03aa11fa7fb83ee8bfe1a99567716e9b4372d1c59"
    static let schemas = ["network.http.v1": "fa1549c0a1e2e6b3bf4a83af1a6d37730bbefc8cddc3ffbe3c807d5e7af503f3",
                          "storage.keyValue.v1": "4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"]
    static func snapshot(_ data: Data) -> Data {
        data.withUnsafeBytes { bytes in bytes.isEmpty ? Data() : Data(bytes: bytes.baseAddress!, count: bytes.count) }
    }
    static func roleID(_ id: String, known: Set<String>) throws {
        // Inspect at most129 UTF-8 bytes before hashing or concatenating an
        // arbitrary caller String. Known identity IDs are bounded to128 bytes.
        let prefix = id.utf8.prefix(129)
        guard !prefix.isEmpty, prefix.count <= 128,
              prefix.allSatisfy({ (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || [45, 46, 95].contains($0) }),
              known.contains(id) else { throw materialError("roles") }
    }
    static func linkedIdentity(_ identity: CapabilityRuntimeIdentity) throws {
        guard CapabilityNativeIdentity.sha256 == native, CapabilitySchemas.contractSHA256 == semantic,
              CapabilitySchemas.httpID == "network.http.v1", CapabilitySchemas.storageID == "storage.keyValue.v1",
              schemas[CapabilitySchemas.httpID] == CapabilitySchemas.httpSHA256,
              schemas[CapabilitySchemas.storageID] == CapabilitySchemas.storageSHA256,
              identity.capabilities.allSatisfy({ $0.nativeSHA256 == CapabilityNativeIdentity.sha256 && schemas[$0.id] == $0.schemaSHA256 }) else {
            throw materialError("linked_identity")
        }
    }
    static func document(_ bytes: Data, digest: String) throws -> [String: CanonicalValue] {
        guard ReleaseVerifier.sha256(bytes) == digest else { throw materialError("digest") }
        let value = try MaterialJSON.decode(bytes)
        guard let fields = value.object, fields.keys.allSatisfy({ $0.utf8.allSatisfy({ $0 < 128 }) }),
              MaterialJSON.canonical(value) == bytes else { throw materialError("canonical") }
        return fields
    }
    static func exact(_ fields: [String: CanonicalValue], _ keys: Set<String>) throws {
        guard Set(fields.keys) == keys else { throw materialError("fields") }
    }
    static func text(_ fields: [String: CanonicalValue], _ key: String) throws -> String {
        guard let value = fields[key]?.text else { throw materialError("type") }; return value
    }
    static func number(_ fields: [String: CanonicalValue], _ key: String, _ range: ClosedRange<UInt64>) throws -> UInt64 {
        guard let value = fields[key]?.uint, range.contains(value) else { throw materialError("number") }; return value
    }
    static func bridge(_ fields: [String: CanonicalValue]) throws -> InstalledBridgePolicy {
        try exact(fields, ["schema", "burst", "starts_per_second"])
        _ = try number(fields, "schema", 1...1)
        return try InstalledBridgePolicy(burst: UInt32(number(fields, "burst", 1...8)), startsPerSecond: UInt32(number(fields, "starts_per_second", 1...32)))
    }
    static func configuration(_ fields: [String: CanonicalValue], id: String, requests: UInt32) throws -> InstalledConfiguration {
        if id == "network.http.v1" {
            try exact(fields, ["schema", "implementation", "maximum_concurrent_requests"])
            _ = try number(fields, "schema", 1...1)
            let concurrency = try number(fields, "maximum_concurrent_requests", 1...8)
            guard try text(fields, "implementation") == "urlsession-normal-tls-v1", concurrency == UInt64(requests) else { throw materialError("http") }
            return .http(maximumConcurrentRequests: UInt32(concurrency))
        }
        try exact(fields, ["schema", "implementation", "container", "directory_component", "maximum_total_bytes", "maximum_entries"])
        _ = try number(fields, "schema", 1...1)
        let component = try text(fields, "directory_component")
        guard id == "storage.keyValue.v1", try text(fields, "implementation") == "app-private-kv-v1",
              try text(fields, "container") == "application-private", namespace(component) else { throw materialError("storage") }
        return try .storage(directoryComponent: component, maximumTotalBytes: Int(number(fields, "maximum_total_bytes", 1...4_194_304)), maximumEntries: Int(number(fields, "maximum_entries", 1...1024)))
    }
    static func strings(_ fields: [String: CanonicalValue], _ key: String, maximum: Int) throws -> [String] {
        guard case let .array(values) = fields[key], values.count <= maximum else { throw materialError("grant") }
        var previous: String?, result: [String] = []
        for value in values {
            guard let text = value.text, !text.isEmpty, text.utf8.count <= 4096, text.utf8.allSatisfy({ (33...126).contains($0) }),
                  previous.map({ $0.utf8.lexicographicallyPrecedes(text.utf8) }) ?? true else { throw materialError("grant") }
            previous = text; result.append(text)
        }
        return result
    }
    static func grant(_ fields: [String: CanonicalValue], id: String, schema: String) throws -> InstalledGrant {
        try exact(fields, ["capability_id", "schema_sha256", "permissions", "origins", "methods", "namespaces"])
        guard try text(fields, "capability_id") == id, try text(fields, "schema_sha256") == schema else { throw materialError("grant") }
        let permissions = try strings(fields, "permissions", maximum: 1), origins = try strings(fields, "origins", maximum: 32)
        let methods = try strings(fields, "methods", maximum: 6), namespaces = try strings(fields, "namespaces", maximum: 32)
        if id == "network.http.v1" {
            guard permissions.allSatisfy({ $0 == "network.https" }), namespaces.isEmpty, origins.allSatisfy(origin),
                  methods.allSatisfy({ ["DELETE", "GET", "HEAD", "PATCH", "POST", "PUT"].contains($0) }) else { throw materialError("grant") }
        } else {
            guard id == "storage.keyValue.v1", permissions.allSatisfy({ $0 == "storage.appPrivate" }), origins.isEmpty, methods.isEmpty,
                  namespaces.allSatisfy(namespace) else { throw materialError("grant") }
        }
        return InstalledGrant(capabilityID: id, schemaSHA256: schema, permissions: permissions, origins: origins, methods: methods, namespaces: namespaces)
    }
    static func namespace(_ text: String) -> Bool {
        (1...64).contains(text.utf8.count) && text.utf8.allSatisfy { (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || [45, 95].contains($0) }
    }
    static func origin(_ text: String) -> Bool {
        guard text.hasPrefix("https://"), text.utf8.count <= 267 else { return false }
        let parts = text.dropFirst(8).split(separator: ":", omittingEmptySubsequences: false)
        guard (1...2).contains(parts.count), !parts[0].isEmpty, parts[0].utf8.count <= 253 else { return false }
        let labels = parts[0].split(separator: ".", omittingEmptySubsequences: false)
        guard labels.allSatisfy({ label in !label.isEmpty && label.utf8.count <= 63 && label.first != "-" && label.last != "-" && label.utf8.allSatisfy { (97...122).contains($0) || (48...57).contains($0) || $0 == 45 } }) else { return false }
        if parts.count == 2 {
            guard let port = UInt16(parts[1]), port > 0, port != 443, String(port) == parts[1] else { return false }
        }
        return true
    }
}
