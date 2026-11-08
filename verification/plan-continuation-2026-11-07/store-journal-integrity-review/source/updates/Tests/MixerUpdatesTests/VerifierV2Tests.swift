import Foundation
import Testing
import Crypto
@testable import MixerUpdates

private struct GrantVector: Decodable {
    let test_only: Bool
    let host: InstalledRuntime
    let roots: [TrustRoot]
    let payload: Data
    let signed_manifest: CanonicalValue
    let signed_assignment: CanonicalValue
    let artifact_sha256: String
    let manifest_cbor_hex: String
    let assignment_cbor_hex: String
    let grant_descriptor: CanonicalValue
    let grant_descriptor_cbor_hex: String
    let installation: String
    let cohort_bucket: UInt64
    let verification_time_unix: UInt64
    let last_sequence: UInt64
}
private struct GrantDocumentCase: Decodable {
    let name: String
    let accepted: Bool
    let signed_manifest_json: String
}
private struct GrantRuleCase: Decodable { let value: String; let accepted: Bool }
private struct GrantCorpus: Decodable {
    let test_only: Bool
    let cases: [GrantDocumentCase]
    let origin_cases: [GrantRuleCase]
    let namespace_cases: [GrantRuleCase]
}
private func grantFixture<T: Decodable>(_ name: String, as type: T.Type) throws -> T {
    let file = try #require(Bundle.module.url(forResource: name, withExtension: "json", subdirectory: "Fixtures"))
    return try StrictJSON.decode(type, from: Data(contentsOf: file))
}
private func grantEncoded<T: Encodable>(_ value: T) throws -> Data { try JSONEncoder().encode(value) }
private func grantHex(_ data: Data) -> String { data.map { String(format: "%02x", $0) }.joined() }
private func grantHost(_ h: InstalledRuntime, protocolVersion: UInt64) -> InstalledRuntime {
    InstalledRuntime(scope: h.scope, runtime: h.runtime, protocolVersion: protocolVersion, guestABI: h.guestABI, uiSchema: h.uiSchema,
        capabilityHashes: h.capabilityHashes, stateVersion: h.stateVersion, maxPayloadBytes: h.maxPayloadBytes, limits: h.limits)
}
private func grantSign(_ value: CanonicalValue, field: String, domain: String, key: Curve25519.Signing.PrivateKey) throws -> Data {
    let signature = try key.signature(for: Data(domain.utf8) + value.canonicalCBOR())
    return try grantEncoded(CanonicalValue.object([field: value, "signature": .text(signature.base64EncodedString())]))
}

@Test func signedV2GoVectorAndDescriptorMatchSwiftCanonicalBytes() throws {
    let v = try grantFixture("signed-release-v2", as: GrantVector.self)
    #expect(v.test_only)
    let manifest = try #require(v.signed_manifest.object?["manifest"])
    let assignment = try #require(v.signed_assignment.object?["assignment"])
    #expect(try grantHex(manifest.canonicalCBOR()) == v.manifest_cbor_hex)
    #expect(try grantHex(assignment.canonicalCBOR()) == v.assignment_cbor_hex)
    #expect(try grantHex(v.grant_descriptor.canonicalCBOR()) == v.grant_descriptor_cbor_hex)
    #expect(try ReleaseVerifier.sha256(v.grant_descriptor.canonicalCBOR()) == VerifiedCapabilityGrants.descriptorSHA256)
    let verifier = try ReleaseVerifier(host: v.host, roots: v.roots)
    let artifact = try verifier.verifyArtifact(signedManifest: grantEncoded(v.signed_manifest), payload: v.payload, now: v.verification_time_unix)
    #expect(artifact.artifactSHA256 == v.artifact_sha256)
    #expect(artifact.resourceLimits == ResourceLimits(memoryBytes: 1_048_576, fuel: 1_000, startupMilliseconds: 1_000))
    let grants = try #require(artifact.capabilityGrants)
    #expect(grants.schema == 1 && grants.schemaSHA256 == VerifiedCapabilityGrants.descriptorSHA256)
    #expect(grants.entries.map(\.capabilityID) == ["network.http.v1", "storage.keyValue.v1"])
    #expect(grants.entries[0].permissions == ["network.https"])
    #expect(grants.entries[0].origins == ["https://api.fieldlog.example", "https://uploads.fieldlog.example:8443"])
    #expect(grants.entries[0].methods == ["GET", "POST"] && grants.entries[0].namespaces.isEmpty)
    #expect(grants.entries[1].permissions == ["storage.appPrivate"])
    #expect(grants.entries[1].namespaces == ["Drafts", "drafts", "outbox"])
    let verified = try verifier.verifyAssignment(signedAssignment: grantEncoded(v.signed_assignment), artifact: artifact,
        channel: "beta", installation: v.installation, lastSequence: v.last_sequence, now: v.verification_time_unix)
    #expect(verified.sequence == 7 && verified.cohortBucket == v.cohort_bucket)
}

@Test func sharedSignedGrantCorpusRejectsHostileValuesWithoutNormalizing() throws {
    let v = try grantFixture("signed-release-v2", as: GrantVector.self)
    let corpus = try grantFixture("capability-grant-cases-v1", as: GrantCorpus.self)
    #expect(corpus.test_only && corpus.cases.count == 115)
    let verifier = try ReleaseVerifier(host: v.host, roots: v.roots)
    for item in corpus.cases {
        do {
            let artifact = try verifier.verifyArtifact(signedManifest: Data(item.signed_manifest_json.utf8), payload: v.payload, now: v.verification_time_unix)
            #expect(item.accepted, "Unexpected acceptance of shared case \(item.name)")
            #expect(artifact.capabilityGrants != nil)
            if item.name == "empty-entries-deny" { #expect(artifact.capabilityGrants?.entries.isEmpty == true) }
        } catch {
            #expect(!item.accepted, "Unexpected rejection of shared case \(item.name): \(error)")
        }
    }
}

@Test func releaseV1MetadataHasLimitsAndNeverAcquiresGrantAuthority() throws {
    struct V1: Decodable { let host: InstalledRuntime; let roots: [TrustRoot]; let payload: Data; let signed_manifest: CanonicalValue; let verification_time_unix: UInt64 }
    let v = try grantFixture("signed-release-v1", as: V1.self)
    let artifact = try ReleaseVerifier(host: v.host, roots: v.roots).verifyArtifact(signedManifest: grantEncoded(v.signed_manifest), payload: v.payload, now: v.verification_time_unix)
    #expect(artifact.capabilityGrants == nil)
    #expect(artifact.resourceLimits == ResourceLimits(memoryBytes: 1_048_576, fuel: 1_000, startupMilliseconds: 1_000))
}

@Test func releaseProtocolNegotiationAndV2DocumentBoundsFailClosed() throws {
    let v = try grantFixture("signed-release-v2", as: GrantVector.self)
    let verifier = try ReleaseVerifier(host: v.host, roots: v.roots)
    let raw = try grantEncoded(v.signed_manifest)
    let exact = raw + Data(repeating: 32, count: 65_536 - raw.count)
    #expect(try verifier.verifyArtifact(signedManifest: exact, payload: v.payload, now: v.verification_time_unix).capabilityGrants != nil)
    #expect(throws: UpdateError.self) { try verifier.verifyArtifact(signedManifest: exact + Data([32]), payload: v.payload, now: v.verification_time_unix) }
    let v1 = try ReleaseVerifier(host: grantHost(v.host, protocolVersion: 1), roots: v.roots)
    #expect(throws: UpdateError.self) { try v1.verifyArtifact(signedManifest: raw, payload: v.payload, now: v.verification_time_unix) }
    #expect(throws: UpdateError.self) { try ReleaseVerifier(host: grantHost(v.host, protocolVersion: 3), roots: v.roots) }
    let key = Curve25519.Signing.PrivateKey()
    let roots = [TrustRoot(keyID: "fixture-v2-artifact", publicKey: key.publicKey.rawRepresentation, scope: v.host.scope, artifact: true, assignment: true)]
    var manifest = try #require(v.signed_manifest.object?["manifest"]?.object)
    manifest["schema"] = .uint(1); manifest["protocol"] = .uint(1); manifest.removeValue(forKey: "capability_grants")
    let legacy = try grantSign(.object(manifest), field: "manifest", domain: "mixer.artifact.v1\0", key: key)
    let legacyVerifier = try ReleaseVerifier(host: grantHost(v.host, protocolVersion: 1), roots: roots)
    #expect(try legacyVerifier.verifyArtifact(signedManifest: legacy, payload: v.payload, now: v.verification_time_unix).capabilityGrants == nil)
    #expect(throws: UpdateError.self) { try ReleaseVerifier(host: v.host, roots: roots).verifyArtifact(signedManifest: legacy, payload: v.payload, now: v.verification_time_unix) }
    manifest["capability_grants"] = v.signed_manifest.object?["manifest"]?.object?["capability_grants"]
    let sidecar = try grantSign(.object(manifest), field: "manifest", domain: "mixer.artifact.v1\0", key: key)
    #expect(throws: UpdateError.self) { try legacyVerifier.verifyArtifact(signedManifest: sidecar, payload: v.payload, now: v.verification_time_unix) }
}

@Test func v2AssignmentsRejectReplayAllowFreshRollbackAndRecheckArtifactAuthority() throws {
    let v = try grantFixture("signed-release-v2", as: GrantVector.self)
    let key = Curve25519.Signing.PrivateKey()
    let roots = v.roots.map { root in
        root.assignment ? TrustRoot(keyID: root.keyID, publicKey: key.publicKey.rawRepresentation, scope: root.scope, artifact: false, assignment: true) : root
    }
    let verifier = try ReleaseVerifier(host: v.host, roots: roots)
    let artifact = try verifier.verifyArtifact(signedManifest: grantEncoded(v.signed_manifest), payload: v.payload, now: v.verification_time_unix)
    var assignment = try #require(v.signed_assignment.object?["assignment"]?.object)
    assignment["sequence"] = .uint(8)
    let rollback = try grantSign(.object(assignment), field: "assignment", domain: "mixer.assignment.v2\0", key: key)
    #expect(try verifier.verifyAssignment(signedAssignment: rollback, artifact: artifact, channel: "beta", installation: v.installation, lastSequence: 7, now: v.verification_time_unix).sequence == 8)
    #expect(throws: UpdateError.self) { try verifier.verifyAssignment(signedAssignment: rollback, artifact: artifact, channel: "beta", installation: v.installation, lastSequence: 8, now: v.verification_time_unix) }
    let rollbackEnvelope = try StrictJSON.decode(CanonicalValue.self, from: rollback)
    let signatureText = try #require(rollbackEnvelope.object?["signature"]?.text)
    let signatureBytes = try #require(Data(base64Encoded: signatureText))
    let alphabet = Array("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".utf8)
    var padBits = Array(signatureText.utf8)
    padBits[padBits.count - 3] = alphabet[try #require(alphabet.firstIndex(of: padBits[padBits.count - 3])) + 1]
    let newline = String(signatureText.prefix(16)) + "\n" + String(signatureText.dropFirst(16))
    for signature in [CanonicalValue.array(signatureBytes.map { .uint(UInt64($0)) }), .text(newline), .text(String(decoding: padBits, as: UTF8.self))] {
        let raw = try grantEncoded(CanonicalValue.object(["assignment": .object(assignment), "signature": signature]))
        #expect(throws: UpdateError.self) { try verifier.verifyAssignment(signedAssignment: raw, artifact: artifact, channel: "beta", installation: v.installation, lastSequence: 7, now: v.verification_time_unix) }
    }
    var maximum = assignment; maximum["sequence"] = .uint(UInt64.max)
    let lastSequence = try grantSign(.object(maximum), field: "assignment", domain: "mixer.assignment.v2\0", key: key)
    #expect(try verifier.verifyAssignment(signedAssignment: lastSequence, artifact: artifact, channel: "beta", installation: v.installation, lastSequence: UInt64.max - 1, now: v.verification_time_unix).sequence == UInt64.max)
    #expect(throws: UpdateError.self) { try verifier.verifyAssignment(signedAssignment: lastSequence, artifact: artifact, channel: "beta", installation: v.installation, lastSequence: UInt64.max, now: v.verification_time_unix) }
    for domain in ["mixer.assignment.v1\0", "mixer.artifact.v2\0"] {
        let wrongDomain = try grantSign(.object(assignment), field: "assignment", domain: domain, key: key)
        #expect(throws: UpdateError.self) { try verifier.verifyAssignment(signedAssignment: wrongDomain, artifact: artifact, channel: "beta", installation: v.installation, lastSequence: 7, now: v.verification_time_unix) }
    }
    assignment["schema"] = .uint(1)
    let wrongSchema = try grantSign(.object(assignment), field: "assignment", domain: "mixer.assignment.v2\0", key: key)
    #expect(throws: UpdateError.self) { try verifier.verifyAssignment(signedAssignment: wrongSchema, artifact: artifact, channel: "beta", installation: v.installation, lastSequence: 7, now: v.verification_time_unix) }
    for revoked in [false, true] {
        let denied = roots.map { root in
            root.artifact ? TrustRoot(keyID: root.keyID, publicKey: root.publicKey, scope: root.scope, artifact: true, assignment: false, revoked: revoked, notAfterUnix: revoked ? 0 : v.verification_time_unix) : root
        }
        let current = try ReleaseVerifier(host: v.host, roots: denied)
        #expect(throws: UpdateError.self) { try current.verifyAssignment(signedAssignment: rollback, artifact: artifact, channel: "beta", installation: v.installation, lastSequence: 7, now: v.verification_time_unix) }
    }
}

@Test func signedV2HostBudgetsAndPayloadIntegrityRemainMandatory() throws {
    let v = try grantFixture("signed-release-v2", as: GrantVector.self), h = v.host
    let hosts = [
        InstalledRuntime(scope: h.scope, runtime: String(repeating: "0", count: 64), protocolVersion: 2, capabilityHashes: h.capabilityHashes, stateVersion: h.stateVersion, maxPayloadBytes: h.maxPayloadBytes, limits: h.limits),
        InstalledRuntime(scope: h.scope, runtime: h.runtime, protocolVersion: 2, capabilityHashes: [:], stateVersion: h.stateVersion, maxPayloadBytes: h.maxPayloadBytes, limits: h.limits),
        InstalledRuntime(scope: h.scope, runtime: h.runtime, protocolVersion: 2, capabilityHashes: h.capabilityHashes, stateVersion: 2, maxPayloadBytes: h.maxPayloadBytes, limits: h.limits),
        InstalledRuntime(scope: h.scope, runtime: h.runtime, protocolVersion: 2, capabilityHashes: h.capabilityHashes, stateVersion: h.stateVersion, maxPayloadBytes: 1, limits: h.limits),
        InstalledRuntime(scope: h.scope, runtime: h.runtime, protocolVersion: 2, capabilityHashes: h.capabilityHashes, stateVersion: h.stateVersion, maxPayloadBytes: h.maxPayloadBytes, limits: ResourceLimits(memoryBytes: 1, fuel: h.limits.fuel, startupMilliseconds: h.limits.startupMilliseconds)),
        InstalledRuntime(scope: h.scope, runtime: h.runtime, protocolVersion: 2, capabilityHashes: h.capabilityHashes, stateVersion: h.stateVersion, maxPayloadBytes: h.maxPayloadBytes, limits: ResourceLimits(memoryBytes: h.limits.memoryBytes, fuel: 1, startupMilliseconds: h.limits.startupMilliseconds)),
        InstalledRuntime(scope: h.scope, runtime: h.runtime, protocolVersion: 2, capabilityHashes: h.capabilityHashes, stateVersion: h.stateVersion, maxPayloadBytes: h.maxPayloadBytes, limits: ResourceLimits(memoryBytes: h.limits.memoryBytes, fuel: h.limits.fuel, startupMilliseconds: 1))
    ]
    for host in hosts {
        #expect(throws: UpdateError.self) { try ReleaseVerifier(host: host, roots: v.roots).verifyArtifact(signedManifest: grantEncoded(v.signed_manifest), payload: v.payload, now: v.verification_time_unix) }
    }
    let verifier = try ReleaseVerifier(host: h, roots: v.roots)
    #expect(throws: UpdateError.self) { try verifier.verifyArtifact(signedManifest: grantEncoded(v.signed_manifest), payload: v.payload + Data([0]), now: v.verification_time_unix) }
    var tampered = v.payload; tampered[0] ^= 1
    #expect(throws: UpdateError.self) { try verifier.verifyArtifact(signedManifest: grantEncoded(v.signed_manifest), payload: tampered, now: v.verification_time_unix) }
}

@Test func signedV2ManifestAndNestedObjectsRequireEveryClosedField() throws {
    let v = try grantFixture("signed-release-v2", as: GrantVector.self)
    let key = Curve25519.Signing.PrivateKey()
    let verifier = try ReleaseVerifier(host: v.host, roots: [TrustRoot(keyID: "fixture-v2-artifact", publicKey: key.publicKey.rawRepresentation, scope: v.host.scope, artifact: true, assignment: false)])
    let original = try #require(v.signed_manifest.object?["manifest"]?.object)
    let valid = try grantSign(.object(original), field: "manifest", domain: "mixer.artifact.v2\0", key: key)
    #expect(try verifier.verifyArtifact(signedManifest: valid, payload: v.payload, now: v.verification_time_unix).capabilityGrants != nil)
    for field in original.keys {
        var changed = original; changed.removeValue(forKey: field)
        let raw = try grantSign(.object(changed), field: "manifest", domain: "mixer.artifact.v2\0", key: key)
        #expect(throws: UpdateError.self) { try verifier.verifyArtifact(signedManifest: raw, payload: v.payload, now: v.verification_time_unix) }
    }
    for field in ["scope", "limits"] {
        let nested = try #require(original[field]?.object)
        for keyToRemove in nested.keys {
            var changed = original, inner = nested; inner.removeValue(forKey: keyToRemove); changed[field] = .object(inner)
            let raw = try grantSign(.object(changed), field: "manifest", domain: "mixer.artifact.v2\0", key: key)
            #expect(throws: UpdateError.self) { try verifier.verifyArtifact(signedManifest: raw, payload: v.payload, now: v.verification_time_unix) }
        }
    }
}

@Test func v2AssignmentsRequireEveryFieldAndExactArtifactScopeBinding() throws {
    let v = try grantFixture("signed-release-v2", as: GrantVector.self)
    let key = Curve25519.Signing.PrivateKey()
    let roots = v.roots.map { $0.assignment ? TrustRoot(keyID: $0.keyID, publicKey: key.publicKey.rawRepresentation, scope: $0.scope, artifact: false, assignment: true) : $0 }
    let verifier = try ReleaseVerifier(host: v.host, roots: roots)
    let artifact = try verifier.verifyArtifact(signedManifest: grantEncoded(v.signed_manifest), payload: v.payload, now: v.verification_time_unix)
    let original = try #require(v.signed_assignment.object?["assignment"]?.object)
    for field in original.keys {
        var changed = original; changed.removeValue(forKey: field)
        let raw = try grantSign(.object(changed), field: "assignment", domain: "mixer.assignment.v2\0", key: key)
        #expect(throws: UpdateError.self) { try verifier.verifyAssignment(signedAssignment: raw, artifact: artifact, channel: "beta", installation: v.installation, lastSequence: 6, now: v.verification_time_unix) }
    }
    for field in ["artifact_sha256", "runtime", "release_id", "channel", "SCHEMA"] {
        var changed = original
        changed[field] = ["artifact_sha256", "runtime"].contains(field) ? .text(String(repeating: "0", count: 64)) : field == "SCHEMA" ? .uint(2) : .text("another")
        let raw = try grantSign(.object(changed), field: "assignment", domain: "mixer.assignment.v2\0", key: key)
        #expect(throws: UpdateError.self) { try verifier.verifyAssignment(signedAssignment: raw, artifact: artifact, channel: "beta", installation: v.installation, lastSequence: 6, now: v.verification_time_unix) }
    }
    var noRollout = original; noRollout["rollout_basis_points"] = .uint(0)
    let raw = try grantSign(.object(noRollout), field: "assignment", domain: "mixer.assignment.v2\0", key: key)
    #expect(throws: UpdateError.self) { try verifier.verifyAssignment(signedAssignment: raw, artifact: artifact, channel: "beta", installation: v.installation, lastSequence: 6, now: v.verification_time_unix) }
}

private final class GrantStoreClock: @unchecked Sendable {
    private let lock = NSLock()
    private var value: UInt64 = 1_000
    func now() -> UInt64 { lock.lock(); defer { lock.unlock() }; return value }
    func advance() { lock.lock(); value += 10_000_000_000; lock.unlock() }
}
private final class GrantStoreFault: @unchecked Sendable {
    private let lock = NSLock()
    private var point: DurabilityFaultPoint?
    func arm(_ value: DurabilityFaultPoint?) { lock.lock(); point = value; lock.unlock() }
    func check(_ value: DurabilityFaultPoint) throws { lock.lock(); let hit = point == value; lock.unlock(); if hit { throw UpdateError("v2.test.interruption", value.rawValue) } }
}
private struct GrantStoreOffer { let manifest: Data; let assignment: Data; let payload: Data; let digest: String }
private struct GrantStoreFixture {
    let vector: GrantVector
    let key = Curve25519.Signing.PrivateKey()
    let clock = GrantStoreClock()
    let fault = GrantStoreFault()
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-v2-store-\(UUID().uuidString)")
    init() throws { vector = try grantFixture("signed-release-v2", as: GrantVector.self) }
    func verifier() throws -> ReleaseVerifier {
        try ReleaseVerifier(host: vector.host, roots: [TrustRoot(keyID: "v2.store.test", publicKey: key.publicKey.rawRepresentation, scope: vector.host.scope, artifact: true, assignment: true)])
    }
    func configuration() -> ColdStartConfiguration {
        ColdStartConfiguration(directory: directory, channel: "beta", installation: vector.installation, failureThreshold: 1,
            reserveDiskBytes: 0, monotonicNanoseconds: { clock.now() }, fault: { try fault.check($0) })
    }
    func open() throws -> ColdStartUpdater {
        try ColdStartUpdater.open(configuration: configuration(), verifier: verifier(), executableValidator: { payload, artifact in
            // Explicit protocol/store-test validator; this is not a Wasm pass.
            guard payload.starts(with: Data("v2-store-".utf8)), artifact.capabilityGrants != nil else { throw UpdateError("v2.test.profile", "Protocol fixture denied") }
        })
    }
    func offer(_ sequence: UInt64, release: UInt64, empty: Bool = false) throws -> GrantStoreOffer {
        let payload = Data("v2-store-\(release)".utf8)
        var manifest = try #require(vector.signed_manifest.object?["manifest"]?.object)
        manifest["key_id"] = .text("v2.store.test"); manifest["release_id"] = .text("v2-store-\(release)")
        manifest["payload_sha256"] = .text(ReleaseVerifier.sha256(payload)); manifest["compressed_bytes"] = .uint(UInt64(payload.count)); manifest["expanded_bytes"] = .uint(UInt64(payload.count))
        if empty { var grants = try #require(manifest["capability_grants"]?.object); grants["entries"] = .array([]); manifest["capability_grants"] = .object(grants) }
        let value = CanonicalValue.object(manifest), digest = try ReleaseVerifier.sha256(value.canonicalCBOR())
        var assignment = try #require(vector.signed_assignment.object?["assignment"]?.object)
        assignment["key_id"] = .text("v2.store.test"); assignment["release_id"] = .text("v2-store-\(release)"); assignment["artifact_sha256"] = .text(digest); assignment["sequence"] = .uint(sequence)
        return try GrantStoreOffer(manifest: grantSign(value, field: "manifest", domain: "mixer.artifact.v2\0", key: key),
            assignment: grantSign(.object(assignment), field: "assignment", domain: "mixer.assignment.v2\0", key: key), payload: payload, digest: digest)
    }
    func stage(_ offer: GrantStoreOffer, on store: ColdStartUpdater) async throws {
        try await store.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: vector.verification_time_unix)
        try await store.appendDownload(offer.payload, atOffset: 0, now: vector.verification_time_unix)
        try await store.finishDownload(now: vector.verification_time_unix)
    }
    func remove() { try? FileManager.default.removeItem(at: directory) }
}

@Test func signedV2GrantsSurviveResumeHealthRecoveryAndFreshRollback() async throws {
    let f = try GrantStoreFixture(); defer { f.remove() }
    let first = try f.offer(1, release: 1), second = try f.offer(2, release: 2, empty: true)
    var store = try f.open()
    #expect(try await store.selectAtColdStart(now: f.vector.verification_time_unix).verifiedArtifact == nil)
    try await store.beginDownload(signedManifest: first.manifest, signedAssignment: first.assignment, now: f.vector.verification_time_unix)
    try await store.appendDownload(first.payload.prefix(3), atOffset: 0, now: f.vector.verification_time_unix)
    await store.close(); store = try f.open()
    #expect(try await store.downloadOffset() == 3)
    try await store.appendDownload(first.payload.dropFirst(3), atOffset: 3, now: f.vector.verification_time_unix)
    try await store.finishDownload(now: f.vector.verification_time_unix)
    let provisional = try await store.selectAtColdStart(now: f.vector.verification_time_unix)
    #expect(provisional.source == .provisional && provisional.verifiedArtifact?.capabilityGrants?.entries.count == 2)
    f.clock.advance()
    try await store.markHealthy(launchID: #require(provisional.launchID), now: f.vector.verification_time_unix, completedMilestones: ["feature_started", "first_screen"])
    await store.close(); store = try f.open()
    let healthy = try await store.selectAtColdStart(now: UInt64.max)
    #expect(healthy.source == .healthy && healthy.payload == first.payload)
    #expect(healthy.verifiedArtifact?.artifactSHA256 == first.digest)
    #expect(healthy.verifiedArtifact?.resourceLimits.fuel == 1000)
    #expect(healthy.verifiedArtifact?.capabilityGrants == provisional.verifiedArtifact?.capabilityGrants)
    try await f.stage(second, on: store)
    await store.close(); store = try f.open()
    let candidate = try await store.selectAtColdStart(now: f.vector.verification_time_unix)
    #expect(candidate.source == .provisional && candidate.verifiedArtifact?.capabilityGrants?.entries.isEmpty == true)
    let recovered = try await store.reportFailure(launchID: #require(candidate.launchID), reason: .deterministicTrap)
    #expect(recovered.source == .healthy && recovered.payload == first.payload)
    #expect(recovered.verifiedArtifact?.capabilityGrants == provisional.verifiedArtifact?.capabilityGrants)
    #expect(await store.snapshot().quarantine[second.digest] == "deterministicTrap")
    await store.close(); store = try f.open()
    let rollback = try f.offer(3, release: 1)
    #expect(rollback.digest == first.digest)
    try await f.stage(rollback, on: store)
    await store.close(); store = try f.open()
    let restored = try await store.selectAtColdStart(now: f.vector.verification_time_unix)
    #expect(restored.source == .provisional && restored.payload == first.payload)
    #expect(restored.verifiedArtifact?.capabilityGrants == provisional.verifiedArtifact?.capabilityGrants)
    #expect(await store.snapshot().acceptedSequence == 3)
    await store.close()
    let wrongHost = try ReleaseVerifier(host: grantHost(f.vector.host, protocolVersion: 1), roots: [TrustRoot(keyID: "v2.store.test", publicKey: f.key.publicKey.rawRepresentation, scope: f.vector.host.scope, artifact: true, assignment: true)])
    #expect(throws: UpdateError.self) { try ColdStartUpdater.open(configuration: f.configuration(), verifier: wrongHost, executableValidator: { _, _ in }) }
}

@Test(arguments: [DurabilityFaultPoint.beforeStateRename, .afterStateRename])
func v2SequenceInterruptionNeverConvertsSignedGrantsIntoPayloadAuthority(_ point: DurabilityFaultPoint) async throws {
    let f = try GrantStoreFixture(); defer { f.remove() }; let offer = try f.offer(1, release: 1)
    var store = try f.open(); f.fault.arm(point)
    do { try await store.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: f.vector.verification_time_unix); Issue.record("Expected interrupted sequence commit") }
    catch let error as UpdateError { #expect(error.code == "v2.test.interruption") }
    await store.close(); f.fault.arm(nil); store = try f.open()
    #expect(await store.snapshot().acceptedSequence == (point == .afterStateRename ? 1 : 0))
    #expect(try await store.selectAtColdStart(now: f.vector.verification_time_unix).verifiedArtifact == nil)
    if point == .afterStateRename {
        try await store.cancelDownload()
        do { try await store.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment, now: f.vector.verification_time_unix); Issue.record("Expected replay rejection") }
        catch let error as UpdateError { #expect(error.code == "assignment.replay") }
    }
    await store.close()
}
