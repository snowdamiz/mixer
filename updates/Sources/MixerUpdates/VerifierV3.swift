import Foundation
import Crypto

/// Signed v3 values are readable, but only the enclosing artifact carries the
/// verifier/payload binding. Native policy must independently narrow these sets.
public struct VerifiedCapabilityGrantV3: Sendable {
    public let capabilityID: String
    public let schemaSHA256: String
    public let permissions: [String]
    public let origins: [String]
    public let methods: [String]
    public let namespaces: [String]
    fileprivate init(id: String, hash: String, permissions: [String], origins: [String], methods: [String], namespaces: [String]) {
        capabilityID = id; schemaSHA256 = hash; self.permissions = permissions
        self.origins = origins; self.methods = methods; self.namespaces = namespaces
    }
}

public struct VerifiedCapabilityGrantsV3: Sendable {
    public static let descriptorSHA256 = "b394ffd165ef28977de9743b1c1a98c419504787f2912e30d419cfb1582e15e1"
    public let schema: UInt64 = 1
    public let schemaSHA256: String = Self.descriptorSHA256
    public let entries: [VerifiedCapabilityGrantV3]
    fileprivate let context: V3VerificationContext
    fileprivate let artifactSHA256: String
    fileprivate init(entries: [VerifiedCapabilityGrantV3], context: V3VerificationContext, artifactSHA256: String) {
        self.entries = entries; self.context = context; self.artifactSHA256 = artifactSHA256
    }
}

/// Proves signed metadata and exact payload length/hash under one captured v3
/// verifier. It is neither executable validation nor a durable rollout selection.
public struct VerifiedArtifactV3: Sendable {
    public let manifest: CanonicalValue
    public let artifactSHA256: String
    public let payloadSHA256: String
    public let releaseID: String
    public let payloadBytes: UInt64
    public let resourceLimits: ResourceLimits
    public let capabilityGrants: VerifiedCapabilityGrantsV3
    fileprivate let evidence: V3ArtifactEvidence
    fileprivate init(manifest: CanonicalValue, digest: String, parsed: V3Manifest,
                     context: V3VerificationContext, signed: Data, signature: Data) {
        self.manifest = manifest; artifactSHA256 = digest; payloadSHA256 = parsed.payloadHash
        releaseID = parsed.releaseID; payloadBytes = parsed.payloadBytes; resourceLimits = parsed.limits
        capabilityGrants = VerifiedCapabilityGrantsV3(entries: parsed.grants, context: context, artifactSHA256: digest)
        evidence = V3ArtifactEvidence(context: context, signed: signed, signature: signature)
    }
}

/// Eligibility against the supplied high-water is not its durable reservation.
public struct VerifiedAssignmentV3: Sendable {
    public let assignment: CanonicalValue
    public let artifactSHA256: String
    public let sequence: UInt64
    public let cohortBucket: UInt64
    fileprivate let context: V3VerificationContext
    fileprivate let channel: String
    fileprivate let installation: String
    fileprivate let signature: Data
    fileprivate init(assignment: CanonicalValue, artifact: VerifiedArtifactV3, sequence: UInt64,
                     bucket: UInt64, channel: String, installation: String, signature: Data) {
        self.assignment = assignment; artifactSHA256 = artifact.artifactSHA256
        self.sequence = sequence; cohortBucket = bucket; context = artifact.evidence.context
        self.channel = channel; self.installation = installation; self.signature = signature
    }
}

/// Explicit protocol3 / guestABI2 entrypoint. Legacy ReleaseVerifier is unchanged.
/// Methods do bounded synchronous verification and schedule no background work.
public struct ReleaseVerifierV3: Sendable {
    public let host: InstalledRuntime
    private let context: V3VerificationContext

    public init(host: InstalledRuntime, roots: [TrustRoot]) throws {
        try V3Rules.scope(host.scope)
        guard V3Rules.digest(host.runtime), host.protocolVersion == 3, host.guestABI == 2, host.uiSchema == 1,
              (1...V3Rules.payloadMaximum).contains(host.maxPayloadBytes),
              (1...V3Rules.payloadMaximum).contains(host.limits.memoryBytes),
              (1...1_000_000).contains(host.limits.fuel), (1...60_000).contains(host.limits.startupMilliseconds),
              host.capabilityHashes.count <= 2,
              host.capabilityHashes.allSatisfy({ V3Rules.schemas[$0.key] == $0.value }) else {
            throw V3Rules.error("host.invalid", "Expected the exact bounded protocol3/ABI2 installed host")
        }
        guard !roots.isEmpty, roots.count <= 128, Set(roots.map(\.keyID)).count == roots.count else {
            throw V3Rules.error("trust.invalid", "Pinned roots must have bounded unique key IDs")
        }
        var captured: [String: TrustRoot] = [:]
        for root in roots {
            try V3Rules.scope(root.scope)
            guard V3Rules.identifier(root.keyID), root.publicKey.count == 32, root.artifact || root.assignment,
                  root.notAfterUnix == 0 || root.notAfterUnix > root.notBeforeUnix else {
                throw V3Rules.error("trust.invalid", "Invalid pinned root configuration")
            }
            captured[root.keyID] = TrustRoot(keyID: root.keyID, publicKey: V3Rules.snapshot(root.publicKey), scope: root.scope,
                artifact: root.artifact, assignment: root.assignment, revoked: root.revoked,
                notBeforeUnix: root.notBeforeUnix, notAfterUnix: root.notAfterUnix)
        }
        self.host = host; context = V3VerificationContext(host: host, roots: captured)
    }

    public func verifyArtifact(signedManifest: Data, payload: Data, now: UInt64) throws -> VerifiedArtifactV3 {
        guard UInt64(payload.count) <= host.maxPayloadBytes else { throw V3Rules.error("payload.size", "Payload exceeds installed limit") }
        let signed = try document(signedManifest)
        let (manifest, signature) = try envelope(signed, field: "manifest")
        let parsed = try manifestObject(manifest)
        let canonical = try manifest.canonicalCBOR()
        try authorize(parsed.fields, canonical: canonical, signature: signature, artifact: true, now: now)
        let bytes = V3Rules.snapshot(payload)
        guard UInt64(bytes.count) == parsed.payloadBytes, V3Rules.hash(bytes) == parsed.payloadHash else {
            throw V3Rules.error("payload.integrity", "Payload differs from signed length or hash")
        }
        return VerifiedArtifactV3(manifest: manifest, digest: V3Rules.hash(canonical), parsed: parsed,
            context: context, signed: signed, signature: signature)
    }

    public func revalidateArtifact(_ artifact: VerifiedArtifactV3, payload: Data, now: UInt64) throws -> VerifiedArtifactV3 {
        try sameContext(artifact)
        return try verifyArtifact(signedManifest: artifact.evidence.signed, payload: payload, now: now)
    }

    public func verifyAssignment(signedAssignment: Data, artifact: VerifiedArtifactV3, channel: String,
                                 installation: String, lastSequence: UInt64, now: UInt64) throws -> VerifiedAssignmentV3 {
        try sameContext(artifact)
        guard V3Rules.identifier(channel), V3Rules.identifier(installation) else {
            throw V3Rules.error("assignment.identity", "Invalid channel or installation")
        }
        // Recheck artifact compatibility and signing authority at this acceptance.
        let parsed = try manifestObject(artifact.manifest)
        let canonical = try artifact.manifest.canonicalCBOR()
        guard V3Rules.hash(canonical) == artifact.artifactSHA256 else { throw V3Rules.error("proof.binding", "Artifact evidence disagrees") }
        try authorize(parsed.fields, canonical: canonical, signature: artifact.evidence.signature, artifact: true, now: now)
        let (assignment, signature) = try envelope(document(signedAssignment), field: "assignment")
        let fields = try V3Rules.object(assignment, keys: V3Rules.assignmentKeys)
        try scopeObject(fields.required("scope"))
        guard try fields.uint("schema") == 3, try fields.text("cohort") == "sha256-v1",
              try fields.uint("created_at_unix") > 0, try fields.uint("rollout_basis_points") <= 10_000,
              try V3Rules.identifier(fields.text("key_id")), try V3Rules.identifier(fields.text("release_id")),
              try V3Rules.digest(fields.text("runtime")), try V3Rules.digest(fields.text("artifact_sha256")) else {
            throw V3Rules.error("assignment.profile", "Invalid v3 assignment shape")
        }
        guard try fields.required("scope") == host.scope.canonical, try fields.text("runtime") == host.runtime,
              try fields.text("release_id") == artifact.releaseID, try fields.text("artifact_sha256") == artifact.artifactSHA256,
              try fields.text("channel") == channel else {
            throw V3Rules.error("assignment.binding", "Assignment does not bind artifact, host and channel")
        }
        let sequence = try fields.uint("sequence")
        guard sequence > lastSequence else { throw V3Rules.error("assignment.replay", "Assignment sequence must increase") }
        try authorize(fields, canonical: assignment.canonicalCBOR(), signature: signature, artifact: false, now: now)
        let bucket = try ReleaseVerifier.cohort(scope: host.scope, channel: channel, installation: installation)
        guard try bucket < fields.uint("rollout_basis_points") else { throw V3Rules.error("assignment.cohort", "Installation is outside rollout") }
        return VerifiedAssignmentV3(assignment: assignment, artifact: artifact, sequence: sequence,
            bucket: bucket, channel: channel, installation: installation, signature: signature)
    }

    private func sameContext(_ artifact: VerifiedArtifactV3) throws {
        guard artifact.evidence.context === context, artifact.capabilityGrants.context === context,
              artifact.capabilityGrants.artifactSHA256 == artifact.artifactSHA256 else {
            throw V3Rules.error("proof.context", "Reverify signed bytes with this verifier instead of retargeting a proof")
        }
    }
    private func document(_ bytes: Data) throws -> Data {
        guard bytes.count <= 65_536 else { throw V3Rules.error("document.size", "Signed document exceeds 64 KiB") }
        return V3Rules.snapshot(bytes)
    }
    private func envelope(_ bytes: Data, field: String) throws -> (CanonicalValue, Data) {
        let value = try StrictJSON.decode(CanonicalValue.self, from: bytes, maximumBytes: 65_536)
        let fields = try V3Rules.object(value, keys: [field, "signature"])
        let text = try fields.text("signature")
        guard let signature = Data(base64Encoded: text), signature.count == 64, signature.base64EncodedString() == text else {
            throw V3Rules.error("signature.encoding", "Expected canonical base64 Ed25519 signature")
        }
        return (try fields.required(field), signature)
    }
    private func authorize(_ fields: [String: CanonicalValue], canonical: Data, signature: Data, artifact: Bool, now: UInt64) throws {
        let id = try fields.text("key_id")
        guard let root = context.roots[id], !root.revoked, root.scope == host.scope,
              artifact ? root.artifact : root.assignment,
              now >= root.notBeforeUnix, root.notAfterUnix == 0 || now < root.notAfterUnix else {
            throw V3Rules.error("signature.authority", "Pinned signing authority denied")
        }
        let domain = artifact ? "mixer.artifact.v3\0" : "mixer.assignment.v3\0"
        let key = try Curve25519.Signing.PublicKey(rawRepresentation: root.publicKey)
        guard key.isValidSignature(signature, for: Data(domain.utf8) + canonical) else {
            throw V3Rules.error("signature.invalid", "Ed25519 signature verification failed")
        }
    }
    private func manifestObject(_ value: CanonicalValue) throws -> V3Manifest {
        let fields = try V3Rules.object(value, keys: V3Rules.manifestKeys)
        try scopeObject(fields.required("scope"))
        guard try fields.uint("schema") == 3, try fields.uint("protocol") == 3, try fields.uint("guest_abi") == 2, try fields.uint("ui_schema") == 1 else {
            throw V3Rules.error("manifest.version", "Expected exact v3/ABI2/UI1 tuple")
        }
        for field in ["release_id", "provenance_id", "key_id"] {
            guard try V3Rules.identifier(fields.text(field)) else { throw V3Rules.error("manifest.identity", "Invalid signed identifier") }
        }
        for field in ["runtime", "payload_sha256", "source_map_sha256"] {
            guard try V3Rules.digest(fields.text(field)) else { throw V3Rules.error("manifest.digest", "Invalid signed digest") }
        }
        let source = try fields.text("source_commit")
        guard [40, 64].contains(source.utf8.count), source.utf8.allSatisfy(V3Rules.hex),
              try fields.uint("created_at_unix") > 0, try fields.uint("state_min") <= fields.uint("state_max") else {
            throw V3Rules.error("manifest.identity", "Invalid source, audit time or state interval")
        }
        let count = try fields.uint("compressed_bytes")
        guard count > 0, try count == fields.uint("expanded_bytes"), count <= host.maxPayloadBytes,
              count <= V3Rules.payloadMaximum, try fields.text("compression") == "none", try fields.object("asset_hashes").isEmpty else {
            throw V3Rules.error("manifest.payload", "Unsupported payload size, compression or assets")
        }
        let hashes = try fields.object("capability_hashes")
        guard try fields.required("scope") == host.scope.canonical, try fields.text("runtime") == host.runtime,
              hashes.count <= 2, hashes == host.capabilityHashes.mapValues(CanonicalValue.text),
              try host.stateVersion >= fields.uint("state_min"), try host.stateVersion <= fields.uint("state_max") else {
            throw V3Rules.error("manifest.compatibility", "Scope, runtime, state or capability map differs from installed host")
        }
        let limits = try fields.object("limits")
        _ = try V3Rules.object(.object(limits), keys: ["memory_bytes", "fuel", "startup_milliseconds"])
        let memory = try limits.uint("memory_bytes"), fuel = try limits.uint("fuel"), startup = try limits.uint("startup_milliseconds")
        guard (1...V3Rules.payloadMaximum).contains(memory), memory <= host.limits.memoryBytes,
              (1...1_000_000).contains(fuel), fuel <= host.limits.fuel,
              (1...60_000).contains(startup), startup <= host.limits.startupMilliseconds else {
            throw V3Rules.error("manifest.resources", "Signed limits exceed installed or frozen ceilings")
        }
        return try V3Manifest(fields: fields, payloadHash: fields.text("payload_sha256"), payloadBytes: count,
            releaseID: fields.text("release_id"), limits: ResourceLimits(memoryBytes: memory, fuel: fuel, startupMilliseconds: startup),
            grants: grants(fields.required("capability_grants"), hashes: hashes))
    }
    private func scopeObject(_ value: CanonicalValue) throws {
        let fields = try V3Rules.object(value, keys: ["organization", "project", "app", "environment", "platform"])
        for field in ["organization", "project", "app", "environment"] {
            guard try V3Rules.identifier(fields.text(field)) else { throw V3Rules.error("scope.invalid", "Invalid scope identifier") }
        }
        guard try ["ios", "android"].contains(fields.text("platform")) else { throw V3Rules.error("scope.invalid", "Invalid platform") }
    }
    private func grants(_ value: CanonicalValue, hashes: [String: CanonicalValue]) throws -> [VerifiedCapabilityGrantV3] {
        let fields = try V3Rules.object(value, keys: ["schema", "schema_sha256", "entries"])
        guard try fields.uint("schema") == 1, try fields.text("schema_sha256") == VerifiedCapabilityGrantsV3.descriptorSHA256,
              case let .array(entries) = try fields.required("entries"), entries.count <= 2 else {
            throw V3Rules.error("manifest.grants", "Unsupported grant descriptor")
        }
        var previous: String?, result: [VerifiedCapabilityGrantV3] = []
        for value in entries {
            let entry = try V3Rules.object(value, keys: ["capability_id", "schema_sha256", "permissions", "origins", "methods", "namespaces"])
            let id = try entry.text("capability_id"), hash = try entry.text("schema_sha256")
            guard V3Rules.schemas[id] == hash, hashes[id]?.text == hash,
                  previous.map({ $0.utf8.lexicographicallyPrecedes(id.utf8) }) ?? true else {
                throw V3Rules.error("manifest.grants", "Unknown, unbound, unsorted or duplicate grant")
            }
            previous = id
            let permissions = try strings(entry.required("permissions"), maximum: 1)
            let origins = try strings(entry.required("origins"), maximum: 32)
            let methods = try strings(entry.required("methods"), maximum: 6)
            let namespaces = try strings(entry.required("namespaces"), maximum: 32)
            if id == "network.http.v1" {
                guard permissions.allSatisfy({ $0 == "network.https" }), namespaces.isEmpty,
                      origins.allSatisfy(V3Rules.origin), methods.allSatisfy({ V3Rules.methods.contains($0) }) else {
                    throw V3Rules.error("manifest.grants", "Invalid HTTP grant")
                }
            } else {
                guard permissions.allSatisfy({ $0 == "storage.appPrivate" }), origins.isEmpty, methods.isEmpty,
                      namespaces.allSatisfy(V3Rules.namespace) else { throw V3Rules.error("manifest.grants", "Invalid storage grant") }
            }
            result.append(VerifiedCapabilityGrantV3(id: id, hash: hash, permissions: permissions, origins: origins, methods: methods, namespaces: namespaces))
        }
        return result
    }
    private func strings(_ value: CanonicalValue, maximum: Int) throws -> [String] {
        guard case let .array(items) = value, items.count <= maximum else { throw V3Rules.error("manifest.grants", "Invalid grant collection") }
        var previous: String?, result: [String] = []
        for value in items {
            guard let text = value.text, !text.isEmpty, text.utf8.count <= 4096,
                  text.utf8.allSatisfy({ (33...126).contains($0) }),
                  previous.map({ $0.utf8.lexicographicallyPrecedes(text.utf8) }) ?? true else {
                throw V3Rules.error("manifest.grants", "Grant strings must be sorted unique ASCII")
            }
            previous = text; result.append(text)
        }
        return result
    }
}

fileprivate final class V3VerificationContext: Sendable {
    let host: InstalledRuntime
    let roots: [String: TrustRoot]
    init(host: InstalledRuntime, roots: [String: TrustRoot]) { self.host = host; self.roots = roots }
}
fileprivate struct V3ArtifactEvidence: Sendable {
    let context: V3VerificationContext
    let signed: Data
    let signature: Data
}
fileprivate struct V3Manifest {
    let fields: [String: CanonicalValue]
    let payloadHash: String
    let payloadBytes: UInt64
    let releaseID: String
    let limits: ResourceLimits
    let grants: [VerifiedCapabilityGrantV3]
}
private enum V3Rules {
    static let payloadMaximum: UInt64 = 4_194_304
    static let schemas = ["network.http.v1": "fa1549c0a1e2e6b3bf4a83af1a6d37730bbefc8cddc3ffbe3c807d5e7af503f3",
                          "storage.keyValue.v1": "4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"]
    static let methods: Set<String> = ["DELETE", "GET", "HEAD", "PATCH", "POST", "PUT"]
    static let manifestKeys: Set<String> = ["schema", "scope", "release_id", "source_commit", "provenance_id", "runtime", "protocol", "guest_abi", "ui_schema", "capability_hashes", "state_min", "state_max", "payload_sha256", "compressed_bytes", "expanded_bytes", "compression", "asset_hashes", "source_map_sha256", "limits", "key_id", "created_at_unix", "capability_grants"]
    static let assignmentKeys: Set<String> = ["schema", "scope", "channel", "cohort", "rollout_basis_points", "sequence", "release_id", "artifact_sha256", "runtime", "key_id", "created_at_unix"]
    static func error(_ code: String, _ message: String) -> UpdateError { UpdateError("v3." + code, message) }
    static func hex(_ byte: UInt8) -> Bool { (48...57).contains(byte) || (97...102).contains(byte) }
    static func digest(_ text: String) -> Bool { text.utf8.count == 64 && text.utf8.allSatisfy(hex) }
    static func identifier(_ text: String) -> Bool {
        (1...128).contains(text.utf8.count) && text.utf8.allSatisfy { (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || [45,46,95].contains($0) }
    }
    static func scope(_ scope: UpdateScope) throws {
        guard [scope.organization,scope.project,scope.app,scope.environment].allSatisfy(identifier), ["ios","android"].contains(scope.platform) else {
            throw error("scope.invalid", "Invalid application scope")
        }
    }
    static func object(_ value: CanonicalValue, keys: Set<String>) throws -> [String: CanonicalValue] {
        guard let fields = value.object, Set(fields.keys) == keys else { throw error("document.fields", "Missing, unknown or non-object fields") }
        return fields
    }
    static func hash(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
    static func snapshot(_ data: Data) -> Data {
        data.withUnsafeBytes { bytes in bytes.isEmpty ? Data() : Data(bytes: bytes.baseAddress!, count: bytes.count) }
    }
    static func namespace(_ text: String) -> Bool {
        (1...64).contains(text.utf8.count) && text.utf8.allSatisfy { (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || [45,95].contains($0) }
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
