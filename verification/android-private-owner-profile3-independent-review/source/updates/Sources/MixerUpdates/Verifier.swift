import Foundation
import Crypto

public struct UpdateScope: Codable, Equatable, Sendable {
    public let organization: String
    public let project: String
    public let app: String
    public let environment: String
    public let platform: String
    public init(organization: String, project: String, app: String, environment: String, platform: String) {
        self.organization = organization; self.project = project; self.app = app; self.environment = environment; self.platform = platform
    }
    enum CodingKeys: String, CodingKey, CaseIterable { case organization, project, app, environment, platform }
    public init(from decoder: any Decoder) throws {
        try requireConfigurationFields(decoder, Set(CodingKeys.allCases.map(\.stringValue)))
        let fields = try decoder.container(keyedBy: CodingKeys.self)
        organization = try fields.decode(String.self, forKey: .organization)
        project = try fields.decode(String.self, forKey: .project)
        app = try fields.decode(String.self, forKey: .app)
        environment = try fields.decode(String.self, forKey: .environment)
        platform = try fields.decode(String.self, forKey: .platform)
    }
    var canonical: CanonicalValue { .object(["organization": .text(organization), "project": .text(project), "app": .text(app), "environment": .text(environment), "platform": .text(platform)]) }
    func validate() throws {
        guard [organization, project, app, environment].allSatisfy(validID), ["ios", "android"].contains(platform) else { throw UpdateError("scope.invalid", "Invalid application scope") }
    }
}
public struct ResourceLimits: Codable, Equatable, Sendable {
    public let memoryBytes: UInt64
    public let fuel: UInt64
    public let startupMilliseconds: UInt64
    public init(memoryBytes: UInt64, fuel: UInt64, startupMilliseconds: UInt64) { self.memoryBytes = memoryBytes; self.fuel = fuel; self.startupMilliseconds = startupMilliseconds }
    enum CodingKeys: String, CodingKey, CaseIterable { case memoryBytes = "memory_bytes", fuel, startupMilliseconds = "startup_milliseconds" }
    public init(from decoder: any Decoder) throws {
        try requireConfigurationFields(decoder, Set(CodingKeys.allCases.map(\.stringValue)))
        let fields = try decoder.container(keyedBy: CodingKeys.self)
        memoryBytes = try fields.decode(UInt64.self, forKey: .memoryBytes)
        fuel = try fields.decode(UInt64.self, forKey: .fuel)
        startupMilliseconds = try fields.decode(UInt64.self, forKey: .startupMilliseconds)
    }
}
public struct InstalledRuntime: Codable, Equatable, Sendable {
    public let scope: UpdateScope
    public let runtime: String
    public let protocolVersion: UInt64
    public let guestABI: UInt64
    public let uiSchema: UInt64
    public let capabilityHashes: [String: String]
    public let stateVersion: UInt64
    public let maxPayloadBytes: UInt64
    public let limits: ResourceLimits
    public init(scope: UpdateScope, runtime: String, protocolVersion: UInt64 = 1, guestABI: UInt64 = 1, uiSchema: UInt64 = 1,
                capabilityHashes: [String: String], stateVersion: UInt64, maxPayloadBytes: UInt64, limits: ResourceLimits) {
        self.scope = scope; self.runtime = runtime; self.protocolVersion = protocolVersion; self.guestABI = guestABI; self.uiSchema = uiSchema
        self.capabilityHashes = capabilityHashes; self.stateVersion = stateVersion; self.maxPayloadBytes = maxPayloadBytes; self.limits = limits
    }
    enum CodingKeys: String, CodingKey, CaseIterable { case scope, runtime, limits; case protocolVersion = "protocol", guestABI = "guest_abi", uiSchema = "ui_schema", capabilityHashes = "capability_hashes", stateVersion = "state_version", maxPayloadBytes = "max_payload_bytes" }
    public init(from decoder: any Decoder) throws {
        try requireConfigurationFields(decoder, Set(CodingKeys.allCases.map(\.stringValue)))
        let fields = try decoder.container(keyedBy: CodingKeys.self)
        scope = try fields.decode(UpdateScope.self, forKey: .scope)
        runtime = try fields.decode(String.self, forKey: .runtime)
        protocolVersion = try fields.decode(UInt64.self, forKey: .protocolVersion)
        guestABI = try fields.decode(UInt64.self, forKey: .guestABI)
        uiSchema = try fields.decode(UInt64.self, forKey: .uiSchema)
        capabilityHashes = try fields.decode([String: String].self, forKey: .capabilityHashes)
        stateVersion = try fields.decode(UInt64.self, forKey: .stateVersion)
        maxPayloadBytes = try fields.decode(UInt64.self, forKey: .maxPayloadBytes)
        limits = try fields.decode(ResourceLimits.self, forKey: .limits)
    }
}
public struct TrustRoot: Codable, Sendable {
    public let keyID: String
    public let publicKey: Data
    public let scope: UpdateScope
    public let artifact: Bool
    public let assignment: Bool
    public let revoked: Bool
    public let notBeforeUnix: UInt64
    public let notAfterUnix: UInt64
    public init(keyID: String, publicKey: Data, scope: UpdateScope, artifact: Bool, assignment: Bool, revoked: Bool = false, notBeforeUnix: UInt64 = 0, notAfterUnix: UInt64 = 0) {
        self.keyID = keyID; self.publicKey = publicKey; self.scope = scope; self.artifact = artifact; self.assignment = assignment; self.revoked = revoked; self.notBeforeUnix = notBeforeUnix; self.notAfterUnix = notAfterUnix
    }
    enum CodingKeys: String, CodingKey, CaseIterable { case scope, artifact, assignment, revoked; case keyID = "key_id", publicKey = "public_key", notBeforeUnix = "not_before_unix", notAfterUnix = "not_after_unix" }
    public init(from decoder: any Decoder) throws {
        try requireConfigurationFields(decoder, Set(CodingKeys.allCases.map(\.stringValue)))
        let fields = try decoder.container(keyedBy: CodingKeys.self)
        keyID = try fields.decode(String.self, forKey: .keyID)
        let encodedKey = try fields.decode(String.self, forKey: .publicKey)
        guard let key = Data(base64Encoded: encodedKey), key.base64EncodedString() == encodedKey else { throw UpdateError("trust.encoding", "Expected canonical base64 public key") }
        publicKey = key
        scope = try fields.decode(UpdateScope.self, forKey: .scope)
        artifact = try fields.decode(Bool.self, forKey: .artifact)
        assignment = try fields.decode(Bool.self, forKey: .assignment)
        revoked = try fields.decode(Bool.self, forKey: .revoked)
        notBeforeUnix = try fields.decode(UInt64.self, forKey: .notBeforeUnix)
        notAfterUnix = try fields.decode(UInt64.self, forKey: .notAfterUnix)
    }
}

/// Closed, signed grant values. There is no public constructor or decoder: these
/// are available only through a successfully verified artifact. The native host
/// must still intersect them with its installed capability policy.
public struct VerifiedCapabilityGrant: Equatable, Sendable {
    public let capabilityID: String
    public let schemaSHA256: String
    public let permissions: [String]
    public let origins: [String]
    public let methods: [String]
    public let namespaces: [String]
    fileprivate init(capabilityID: String, schemaSHA256: String, permissions: [String], origins: [String], methods: [String], namespaces: [String]) {
        self.capabilityID = capabilityID; self.schemaSHA256 = schemaSHA256; self.permissions = permissions
        self.origins = origins; self.methods = methods; self.namespaces = namespaces
    }
}
public struct VerifiedCapabilityGrants: Equatable, Sendable {
    public static let descriptorSHA256 = "b394ffd165ef28977de9743b1c1a98c419504787f2912e30d419cfb1582e15e1"
    public let schema: UInt64
    public let schemaSHA256: String
    public let entries: [VerifiedCapabilityGrant]
    fileprivate init(entries: [VerifiedCapabilityGrant]) {
        schema = 1; schemaSHA256 = Self.descriptorSHA256; self.entries = entries
    }
}

public struct VerifiedArtifact: Sendable {
    public let manifest: CanonicalValue
    public let artifactSHA256: String
    public let payloadSHA256: String
    public let releaseID: String
    public let payloadBytes: UInt64
    public let resourceLimits: ResourceLimits
    /// nil for strict release-v1; schema2 carries an explicit value even when no
    /// entries are granted. Hash-only v1 metadata never grants native authority.
    public let capabilityGrants: VerifiedCapabilityGrants?
    // Signing evidence is retained privately; a token is not transferable authority
    // under another pinned configuration or after a signing-key validity change.
    fileprivate let artifactSignature: Data
}
public struct VerifiedAssignment: Sendable {
    public let assignment: CanonicalValue
    public let artifactSHA256: String
    public let sequence: UInt64
    public let cohortBucket: UInt64
}

public struct ReleaseVerifier: Sendable {
    public let host: InstalledRuntime
    private let roots: [String: TrustRoot]
    public init(host: InstalledRuntime, roots: [TrustRoot]) throws {
        try host.scope.validate()
        guard validDigest(host.runtime), [1, 2].contains(host.protocolVersion), host.guestABI == 1, host.uiSchema == 1,
              host.maxPayloadBytes > 0, host.maxPayloadBytes <= 16 * 1_048_576,
              host.limits.memoryBytes > 0, host.limits.fuel > 0, host.limits.startupMilliseconds > 0,
              host.capabilityHashes.count <= 128, host.capabilityHashes.allSatisfy({ validID($0.key) && validDigest($0.value) }) else { throw UpdateError("host.invalid", "Unsupported or invalid installed runtime contract") }
        guard !roots.isEmpty, roots.count <= 128, Set(roots.map(\.keyID)).count == roots.count else { throw UpdateError("trust.invalid", "Trust roots must be bounded and have unique key IDs") }
        for root in roots {
            try root.scope.validate()
            guard validID(root.keyID), root.publicKey.count == 32, root.artifact || root.assignment, root.notAfterUnix == 0 || root.notAfterUnix > root.notBeforeUnix else { throw UpdateError("trust.invalid", "Invalid pinned trust root") }
        }
        self.host = host; self.roots = Dictionary(uniqueKeysWithValues: roots.map { ($0.keyID, $0) })
    }

    /// Verifies artifact bytes only. It does not authorize rollout, validate Wasm,
    /// prove policy eligibility, or activate a feature implementation.
    public func verifyArtifact(signedManifest: Data, payload: Data, now: UInt64) throws -> VerifiedArtifact {
        let (manifest, signature) = try signed(signedManifest, field: "manifest")
        let fields = try manifestObject(manifest)
        try authorize(fields: fields, value: manifest, signature: signature, artifact: true, now: now)
        let count = (try fields.uint("compressed_bytes"))
        let digest = (try fields.text("payload_sha256"))
        guard UInt64(payload.count) == count, Self.sha256(payload) == digest else { throw UpdateError("payload.integrity", "Payload length or SHA-256 mismatch") }
        return VerifiedArtifact(manifest: manifest, artifactSHA256: Self.sha256(try manifest.canonicalCBOR()), payloadSHA256: digest, releaseID: (try fields.text("release_id")), payloadBytes: count,
            resourceLimits: try resourceLimits(fields), capabilityGrants: try capabilityGrants(fields), artifactSignature: signature)
    }

    /// `lastSequence` must come from durable app/runtime/channel state. A rollback
    /// points at old content with a fresh greater sequence.
    public func verifyAssignment(signedAssignment: Data, artifact: VerifiedArtifact, channel: String, installation: String, lastSequence: UInt64, now: UInt64) throws -> VerifiedAssignment {
        try verifyAssignmentMetadata(signedAssignment: signedAssignment, artifactManifest: artifact.manifest,
            artifactSignature: artifact.artifactSignature, artifactDigest: artifact.artifactSHA256, releaseID: artifact.releaseID,
            channel: channel, installation: installation, lastSequence: lastSequence, now: now)
    }

    private func verifyAssignmentMetadata(signedAssignment: Data, artifactManifest: CanonicalValue, artifactSignature: Data,
                                         artifactDigest: String, releaseID: String, channel: String, installation: String,
                                         lastSequence: UInt64, now: UInt64) throws -> VerifiedAssignment {
        guard validID(channel), validID(installation) else { throw UpdateError("assignment.identity", "Invalid channel or app-private installation ID") }
        let (assignment, signature) = try signed(signedAssignment, field: "assignment")
        guard let fields = assignment.object else { throw UpdateError("assignment.shape", "Assignment must be an object") }
        try fields.exactKeys(["schema", "scope", "channel", "cohort", "rollout_basis_points", "sequence", "release_id", "artifact_sha256", "runtime", "key_id", "created_at_unix"])
        try validateScope((try fields.required("scope")))
        guard (try fields.uint("schema")) == host.protocolVersion, (try fields.text("cohort")) == "sha256-v1", (try fields.uint("created_at_unix")) > 0,
              (try fields.uint("rollout_basis_points")) <= 10_000, validID((try fields.text("key_id"))), validID((try fields.text("release_id"))),
              validDigest((try fields.text("runtime"))), validDigest((try fields.text("artifact_sha256"))) else { throw UpdateError("assignment.profile", "Unsupported assignment profile") }
        let manifest = try manifestObject(artifactManifest)
        // A caller may hold an older token or pass one from another verifier.
        // Recheck build authority under this verifier's current roots and time.
        try authorize(fields: manifest, value: artifactManifest, signature: artifactSignature, artifact: true, now: now)
        guard (try fields.required("scope")) == host.scope.canonical, (try fields.text("runtime")) == host.runtime,
              (try fields.text("release_id")) == releaseID, (try fields.text("artifact_sha256")) == artifactDigest,
              (try fields.text("channel")) == channel, (try fields.required("scope")) == (try manifest.required("scope")) else { throw UpdateError("assignment.binding", "Assignment does not bind this artifact, host, and channel") }
        let sequence = (try fields.uint("sequence"))
        guard sequence > lastSequence else { throw UpdateError("assignment.replay", "Assignment sequence must increase") }
        try authorize(fields: fields, value: assignment, signature: signature, artifact: false, now: now)
        let bucket = try Self.cohort(scope: host.scope, channel: channel, installation: installation)
        guard bucket < ((try fields.uint("rollout_basis_points"))) else { throw UpdateError("assignment.cohort", "Installation is outside the signed rollout") }
        return VerifiedAssignment(assignment: assignment, artifactSHA256: artifactDigest, sequence: sequence, cohortBucket: bucket)
    }

    // Header authorization deliberately returns an offer, never a payload-verified
    // artifact token. The durable store may reserve a sequence before downloading.
    func authorizeOffer(manifest data: Data, assignment: Data, channel: String, installation: String,
                        lastSequence: UInt64, now: UInt64) throws -> UpdateOffer {
        let (manifest, signature) = try signed(data, field: "manifest")
        let fields = try manifestObject(manifest)
        try authorize(fields: fields, value: manifest, signature: signature, artifact: true, now: now)
        let digest = Self.sha256(try manifest.canonicalCBOR())
        let verified = try verifyAssignmentMetadata(signedAssignment: assignment, artifactManifest: manifest,
            artifactSignature: signature, artifactDigest: digest, releaseID: fields.text("release_id"),
            channel: channel, installation: installation, lastSequence: lastSequence, now: now)
        let (_, assignmentSignature) = try signed(assignment, field: "assignment")
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let compactManifest = try encoder.encode(CanonicalValue.object(["manifest": manifest, "signature": .text(signature.base64EncodedString())]))
        let compactAssignment = try encoder.encode(CanonicalValue.object(["assignment": verified.assignment, "signature": .text(assignmentSignature.base64EncodedString())]))
        return UpdateOffer(candidate: StoredUpdateCandidate(digest: digest, sequence: verified.sequence,
            signedManifest: compactManifest, signedAssignment: compactAssignment),
            payloadBytes: try fields.uint("compressed_bytes"), payloadSHA256: try fields.text("payload_sha256"))
    }

    func retainedHealthyAuthorityVerifier() throws -> ReleaseVerifier {
        let retained = roots.values.map { root in
            TrustRoot(keyID: root.keyID, publicKey: root.publicKey, scope: root.scope, artifact: root.artifact,
                assignment: root.assignment, revoked: false, notBeforeUnix: 0, notAfterUnix: 0)
        }
        return try ReleaseVerifier(host: host, roots: retained)
    }

    public static func cohort(scope: UpdateScope, channel: String, installation: String) throws -> UInt64 {
        try scope.validate()
        guard validID(channel), validID(installation) else { throw UpdateError("cohort.identity", "Invalid cohort identity") }
        let value = CanonicalValue.object(["organization": .text(scope.organization), "project": .text(scope.project), "app": .text(scope.app), "environment": .text(scope.environment), "channel": .text(channel), "installation": .text(installation)])
        return SHA256.hash(data: try value.canonicalCBOR()).reduce(UInt64(0)) { ($0 * 256 + UInt64($1)) % 10_000 }
    }
    public static func sha256(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }

    private func signed(_ data: Data, field: String) throws -> (CanonicalValue, Data) {
        let envelope = try StrictJSON.decode(CanonicalValue.self, from: data, maximumBytes: host.protocolVersion == 2 ? 65_536 : 1_048_576)
        guard let values = envelope.object else { throw UpdateError("signature.envelope", "Signed document must be an object") }
        try values.exactKeys([field, "signature"])
        let encodedSignature = try values.text("signature")
        guard let signature = Data(base64Encoded: encodedSignature), signature.count == 64,
              signature.base64EncodedString() == encodedSignature else { throw UpdateError("signature.encoding", "Expected a canonical base64 Ed25519 signature") }
        return (try values.required(field), signature)
    }

    private func authorize(fields: [String: CanonicalValue], value: CanonicalValue, signature: Data, artifact: Bool, now: UInt64) throws {
        let keyID = (try fields.text("key_id"))
        guard let root = roots[keyID], !root.revoked, root.scope == host.scope,
              artifact ? root.artifact : root.assignment,
              now >= root.notBeforeUnix, root.notAfterUnix == 0 || now < root.notAfterUnix else { throw UpdateError("signature.authority", "Pinned signing authority denied") }
        let key = try Curve25519.Signing.PublicKey(rawRepresentation: root.publicKey)
        let domain = artifact ? "mixer.artifact.v\(host.protocolVersion)\0" : "mixer.assignment.v\(host.protocolVersion)\0"
        let message = Data(domain.utf8) + (try value.canonicalCBOR())
        guard key.isValidSignature(signature, for: message) else { throw UpdateError("signature.invalid", "Ed25519 signature verification failed") }
    }

    private func manifestObject(_ value: CanonicalValue) throws -> [String: CanonicalValue] {
        guard let fields = value.object else { throw UpdateError("manifest.shape", "Manifest must be an object") }
        var keys: Set<String> = ["schema", "scope", "release_id", "source_commit", "provenance_id", "runtime", "protocol", "guest_abi", "ui_schema", "capability_hashes", "state_min", "state_max", "payload_sha256", "compressed_bytes", "expanded_bytes", "compression", "asset_hashes", "source_map_sha256", "limits", "key_id", "created_at_unix"]
        if host.protocolVersion == 2 { keys.insert("capability_grants") }
        try fields.exactKeys(keys)
        try validateScope((try fields.required("scope")))
        for key in ["schema", "protocol"] { guard (try fields.uint(key)) == host.protocolVersion else { throw UpdateError("manifest.version", "Unsupported \(key)") } }
        for key in ["guest_abi", "ui_schema"] { guard (try fields.uint(key)) == 1 else { throw UpdateError("manifest.version", "Unsupported \(key)") } }
        for key in ["release_id", "provenance_id", "key_id"] { guard validID((try fields.text(key))) else { throw UpdateError("manifest.identity", "Invalid \(key)") } }
        for key in ["runtime", "payload_sha256", "source_map_sha256"] { guard validDigest((try fields.text(key))) else { throw UpdateError("manifest.digest", "Invalid \(key)") } }
        let source = (try fields.text("source_commit"))
        guard [40, 64].contains(source.count), source.allSatisfy({ "0123456789abcdef".contains($0) }),
              (try fields.uint("created_at_unix")) > 0, (try fields.uint("state_min")) <= (try fields.uint("state_max")) else { throw UpdateError("manifest.identity", "Invalid source, audit time or state range") }
        let compressed = (try fields.uint("compressed_bytes")), expanded = (try fields.uint("expanded_bytes"))
        guard compressed > 0, compressed == expanded, expanded <= host.maxPayloadBytes, expanded <= 16 * 1_048_576,
              (try fields.text("compression")) == "none", (try fields.object("asset_hashes")).isEmpty else { throw UpdateError("manifest.payload", "Unsupported payload size, compression or assets") }
        let capabilities = (try fields.object("capability_hashes"))
        guard capabilities.count <= 128 else { throw UpdateError("manifest.capabilities", "Too many capabilities") }
        for (key, value) in capabilities { guard validID(key), let digest = value.text, validDigest(digest) else { throw UpdateError("manifest.capabilities", "Invalid capability schema digest") } }
        _ = try capabilityGrants(fields)
        let limits = (try fields.object("limits"))
        try limits.exactKeys(["memory_bytes", "fuel", "startup_milliseconds"])
        guard (try limits.uint("memory_bytes")) > 0, (try limits.uint("memory_bytes")) <= host.limits.memoryBytes,
              (try limits.uint("fuel")) > 0, (try limits.uint("fuel")) <= host.limits.fuel,
              (try limits.uint("startup_milliseconds")) > 0, (try limits.uint("startup_milliseconds")) <= host.limits.startupMilliseconds else { throw UpdateError("manifest.resources", "Host resource budget exceeded") }
        let expectedCapabilities = host.capabilityHashes.mapValues(CanonicalValue.text)
        guard (try fields.required("scope")) == host.scope.canonical, (try fields.text("runtime")) == host.runtime,
              capabilities == expectedCapabilities, host.stateVersion >= (try fields.uint("state_min")), host.stateVersion <= (try fields.uint("state_max")) else { throw UpdateError("manifest.compatibility", "Installed runtime/capability/state contract mismatch") }
        return fields
    }
    private func resourceLimits(_ fields: [String: CanonicalValue]) throws -> ResourceLimits {
        let limits = try fields.object("limits")
        return try ResourceLimits(memoryBytes: limits.uint("memory_bytes"), fuel: limits.uint("fuel"), startupMilliseconds: limits.uint("startup_milliseconds"))
    }
    private func capabilityGrants(_ fields: [String: CanonicalValue]) throws -> VerifiedCapabilityGrants? {
        guard host.protocolVersion == 2 else { return nil }
        let grants = try fields.object("capability_grants")
        try grants.exactKeys(["schema", "schema_sha256", "entries"])
        guard try grants.uint("schema") == 1, try grants.text("schema_sha256") == VerifiedCapabilityGrants.descriptorSHA256,
              case let .array(entries) = try grants.required("entries"), entries.count <= 2 else { throw UpdateError("manifest.grants", "Unsupported capability grant descriptor") }
        let hashes = try fields.object("capability_hashes")
        var previous = "", verified: [VerifiedCapabilityGrant] = []
        for entry in entries {
            guard let grant = entry.object else { throw UpdateError("manifest.grants", "Grant entry must be an object") }
            try grant.exactKeys(["capability_id", "schema_sha256", "permissions", "origins", "methods", "namespaces"])
            let id = try grant.text("capability_id"), hash = try grant.text("schema_sha256")
            let http = id == "network.http.v1"
            let expectedHash = http ? "fa1549c0a1e2e6b3bf4a83af1a6d37730bbefc8cddc3ffbe3c807d5e7af503f3" : "4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"
            guard validID(id), id > previous, http || id == "storage.keyValue.v1", hash == expectedHash, hashes[id]?.text == hash else { throw UpdateError("manifest.grants", "Unknown, unsorted, duplicate or unbound capability grant") }
            previous = id
            let permissions = try grantStrings(grant, "permissions", maximum: 1)
            let origins = try grantStrings(grant, "origins", maximum: 32)
            let methods = try grantStrings(grant, "methods", maximum: 6)
            let namespaces = try grantStrings(grant, "namespaces", maximum: 32)
            let permission = http ? "network.https" : "storage.appPrivate"
            guard permissions.allSatisfy({ $0 == permission }) else { throw UpdateError("manifest.grants", "Unsupported capability permission") }
            if http {
                guard namespaces.isEmpty, origins.allSatisfy(validGrantOrigin), methods.allSatisfy({ ["DELETE", "GET", "HEAD", "PATCH", "POST", "PUT"].contains($0) }) else { throw UpdateError("manifest.grants", "Invalid HTTP grant") }
            } else {
                guard origins.isEmpty, methods.isEmpty, namespaces.allSatisfy({ value in
                    (1...64).contains(value.utf8.count) && value.utf8.allSatisfy { (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || [45, 95].contains($0) }
                }) else { throw UpdateError("manifest.grants", "Invalid storage grant") }
            }
            verified.append(VerifiedCapabilityGrant(capabilityID: id, schemaSHA256: hash, permissions: permissions, origins: origins, methods: methods, namespaces: namespaces))
        }
        return VerifiedCapabilityGrants(entries: verified)
    }
    private func grantStrings(_ fields: [String: CanonicalValue], _ key: String, maximum: Int) throws -> [String] {
        guard case let .array(values) = try fields.required(key), values.count <= maximum else { throw UpdateError("manifest.grants", "Grant array exceeds its bound or has wrong type") }
        var previous = "", strings: [String] = []
        for value in values {
            guard let string = value.text, string.utf8.count <= 4096, string.utf8.allSatisfy({ (33...126).contains($0) }), string > previous else { throw UpdateError("manifest.grants", "Grant arrays must be strictly sorted unique ASCII strings") }
            previous = string; strings.append(string)
        }
        return strings
    }
    private func validGrantOrigin(_ value: String) -> Bool {
        guard value.hasPrefix("https://"), value.utf8.count <= 267 else { return false }
        let parts = value.dropFirst(8).split(separator: ":", omittingEmptySubsequences: false)
        guard (1...2).contains(parts.count), !parts[0].isEmpty, parts[0].utf8.count <= 253 else { return false }
        let labels = parts[0].split(separator: ".", omittingEmptySubsequences: false)
        guard labels.allSatisfy({ label in
            !label.isEmpty && label.utf8.count <= 63 && label.first != "-" && label.last != "-" && label.utf8.allSatisfy { (97...122).contains($0) || (48...57).contains($0) || $0 == 45 }
        }) else { return false }
        if parts.count == 2 {
            guard let port = UInt16(parts[1]), port > 0, port != 443, String(port) == parts[1] else { return false }
        }
        return true
    }
    private func validateScope(_ scope: CanonicalValue) throws {
        guard let fields = scope.object else { throw UpdateError("scope.shape", "Scope must be an object") }
        try fields.exactKeys(["organization", "project", "app", "environment", "platform"])
        for key in ["organization", "project", "app", "environment"] { guard validID((try fields.text(key))) else { throw UpdateError("scope.identity", "Invalid scope identifier") } }
        guard ["ios", "android"].contains((try fields.text("platform"))) else { throw UpdateError("scope.platform", "Unsupported platform") }
    }
}

private func validID(_ value: String) -> Bool { !value.isEmpty && value.utf8.count <= 128 && value.utf8.allSatisfy { (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || [45, 46, 95].contains($0) } }
private func validDigest(_ value: String) -> Bool { value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) } }
