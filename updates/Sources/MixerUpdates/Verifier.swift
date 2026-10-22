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
    enum CodingKeys: String, CodingKey { case memoryBytes = "memory_bytes", fuel, startupMilliseconds = "startup_milliseconds" }
}
public struct InstalledRuntime: Codable, Sendable {
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
    enum CodingKeys: String, CodingKey { case scope, runtime, limits; case protocolVersion = "protocol", guestABI = "guest_abi", uiSchema = "ui_schema", capabilityHashes = "capability_hashes", stateVersion = "state_version", maxPayloadBytes = "max_payload_bytes" }
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
    enum CodingKeys: String, CodingKey { case scope, artifact, assignment, revoked; case keyID = "key_id", publicKey = "public_key", notBeforeUnix = "not_before_unix", notAfterUnix = "not_after_unix" }
}

public struct VerifiedArtifact: Sendable {
    public let manifest: CanonicalValue
    public let artifactSHA256: String
    public let payloadSHA256: String
    public let releaseID: String
    public let payloadBytes: UInt64
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
        guard validDigest(host.runtime), host.protocolVersion == 1, host.guestABI == 1, host.uiSchema == 1,
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
        return VerifiedArtifact(manifest: manifest, artifactSHA256: Self.sha256(try manifest.canonicalCBOR()), payloadSHA256: digest, releaseID: (try fields.text("release_id")), payloadBytes: count)
    }

    /// `lastSequence` must come from durable app/runtime/channel state. A rollback
    /// points at old content with a fresh greater sequence.
    public func verifyAssignment(signedAssignment: Data, artifact: VerifiedArtifact, channel: String, installation: String, lastSequence: UInt64, now: UInt64) throws -> VerifiedAssignment {
        guard validID(channel), validID(installation) else { throw UpdateError("assignment.identity", "Invalid channel or app-private installation ID") }
        let (assignment, signature) = try signed(signedAssignment, field: "assignment")
        guard let fields = assignment.object else { throw UpdateError("assignment.shape", "Assignment must be an object") }
        try fields.exactKeys(["schema", "scope", "channel", "cohort", "rollout_basis_points", "sequence", "release_id", "artifact_sha256", "runtime", "key_id", "created_at_unix"])
        try validateScope((try fields.required("scope")))
        guard (try fields.uint("schema")) == 1, (try fields.text("cohort")) == "sha256-v1", (try fields.uint("created_at_unix")) > 0,
              (try fields.uint("rollout_basis_points")) <= 10_000, validID((try fields.text("key_id"))), validID((try fields.text("release_id"))),
              validDigest((try fields.text("runtime"))), validDigest((try fields.text("artifact_sha256"))) else { throw UpdateError("assignment.profile", "Unsupported assignment profile") }
        let manifest = try manifestObject(artifact.manifest)
        guard (try fields.required("scope")) == host.scope.canonical, (try fields.text("runtime")) == host.runtime,
              (try fields.text("release_id")) == artifact.releaseID, (try fields.text("artifact_sha256")) == artifact.artifactSHA256,
              (try fields.text("channel")) == channel, (try fields.required("scope")) == (try manifest.required("scope")) else { throw UpdateError("assignment.binding", "Assignment does not bind this artifact, host, and channel") }
        let sequence = (try fields.uint("sequence"))
        guard sequence > lastSequence else { throw UpdateError("assignment.replay", "Assignment sequence must increase") }
        try authorize(fields: fields, value: assignment, signature: signature, artifact: false, now: now)
        let bucket = try Self.cohort(scope: host.scope, channel: channel, installation: installation)
        guard bucket < ((try fields.uint("rollout_basis_points"))) else { throw UpdateError("assignment.cohort", "Installation is outside the signed rollout") }
        return VerifiedAssignment(assignment: assignment, artifactSHA256: artifact.artifactSHA256, sequence: sequence, cohortBucket: bucket)
    }

    public static func cohort(scope: UpdateScope, channel: String, installation: String) throws -> UInt64 {
        try scope.validate()
        guard validID(channel), validID(installation) else { throw UpdateError("cohort.identity", "Invalid cohort identity") }
        let value = CanonicalValue.object(["organization": .text(scope.organization), "project": .text(scope.project), "app": .text(scope.app), "environment": .text(scope.environment), "channel": .text(channel), "installation": .text(installation)])
        return SHA256.hash(data: try value.canonicalCBOR()).reduce(UInt64(0)) { ($0 * 256 + UInt64($1)) % 10_000 }
    }
    public static func sha256(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }

    private func signed(_ data: Data, field: String) throws -> (CanonicalValue, Data) {
        let envelope = try StrictJSON.decode(CanonicalValue.self, from: data)
        guard let values = envelope.object else { throw UpdateError("signature.envelope", "Signed document must be an object") }
        try values.exactKeys([field, "signature"])
        guard let signature = Data(base64Encoded: try values.text("signature")), signature.count == 64 else { throw UpdateError("signature.encoding", "Expected a base64 Ed25519 signature") }
        return (try values.required(field), signature)
    }

    private func authorize(fields: [String: CanonicalValue], value: CanonicalValue, signature: Data, artifact: Bool, now: UInt64) throws {
        let keyID = (try fields.text("key_id"))
        guard let root = roots[keyID], !root.revoked, root.scope == host.scope,
              artifact ? root.artifact : root.assignment,
              now >= root.notBeforeUnix, root.notAfterUnix == 0 || now < root.notAfterUnix else { throw UpdateError("signature.authority", "Pinned signing authority denied") }
        let key = try Curve25519.Signing.PublicKey(rawRepresentation: root.publicKey)
        let message = Data((artifact ? "mixer.artifact.v1\0" : "mixer.assignment.v1\0").utf8) + (try value.canonicalCBOR())
        guard key.isValidSignature(signature, for: message) else { throw UpdateError("signature.invalid", "Ed25519 signature verification failed") }
    }

    private func manifestObject(_ value: CanonicalValue) throws -> [String: CanonicalValue] {
        guard let fields = value.object else { throw UpdateError("manifest.shape", "Manifest must be an object") }
        try fields.exactKeys(["schema", "scope", "release_id", "source_commit", "provenance_id", "runtime", "protocol", "guest_abi", "ui_schema", "capability_hashes", "state_min", "state_max", "payload_sha256", "compressed_bytes", "expanded_bytes", "compression", "asset_hashes", "source_map_sha256", "limits", "key_id", "created_at_unix"])
        try validateScope((try fields.required("scope")))
        for key in ["schema", "protocol", "guest_abi", "ui_schema"] { guard (try fields.uint(key)) == 1 else { throw UpdateError("manifest.version", "Unsupported \(key)") } }
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
    private func validateScope(_ scope: CanonicalValue) throws {
        guard let fields = scope.object else { throw UpdateError("scope.shape", "Scope must be an object") }
        try fields.exactKeys(["organization", "project", "app", "environment", "platform"])
        for key in ["organization", "project", "app", "environment"] { guard validID((try fields.text(key))) else { throw UpdateError("scope.identity", "Invalid scope identifier") } }
        guard ["ios", "android"].contains((try fields.text("platform"))) else { throw UpdateError("scope.platform", "Unsupported platform") }
    }
}

private func validID(_ value: String) -> Bool { !value.isEmpty && value.utf8.count <= 128 && value.utf8.allSatisfy { (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || [45, 46, 95].contains($0) } }
private func validDigest(_ value: String) -> Bool { value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) } }
