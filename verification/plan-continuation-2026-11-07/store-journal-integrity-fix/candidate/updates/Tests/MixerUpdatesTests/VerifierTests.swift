import Foundation
import Testing
import Crypto
@testable import MixerUpdates

private struct Fixture: Decodable {
    let host: InstalledRuntime
    let roots: [TrustRoot]
    let payload: Data
    let signed_manifest: CanonicalValue
    let signed_assignment: CanonicalValue
    let artifact_sha256: String
    let manifest_cbor_hex: String
    let assignment_cbor_hex: String
    let installation: String
    let cohort_bucket: UInt64
    let verification_time_unix: UInt64
    let last_sequence: UInt64
}
private func fixture() throws -> Fixture {
    let file = try #require(Bundle.module.url(forResource: "signed-release-v1", withExtension: "json", subdirectory: "Fixtures"))
    return try StrictJSON.decode(Fixture.self, from: Data(contentsOf: file))
}
private func encoded<T: Encodable>(_ value: T) throws -> Data { try JSONEncoder().encode(value) }
private func hex(_ bytes: Data) -> String { bytes.map { String(format: "%02x", $0) }.joined() }

@Test func independentlyAuthoredGoVectorMatchesSwiftCryptoAndCanonicalization() throws {
    let vector = try fixture()
    let manifest = try #require(vector.signed_manifest.object?["manifest"])
    let assignment = try #require(vector.signed_assignment.object?["assignment"])
    #expect(try hex(manifest.canonicalCBOR()) == vector.manifest_cbor_hex)
    #expect(try hex(assignment.canonicalCBOR()) == vector.assignment_cbor_hex)
    let verifier = try ReleaseVerifier(host: vector.host, roots: vector.roots)
    let artifact = try verifier.verifyArtifact(signedManifest: encoded(vector.signed_manifest), payload: vector.payload, now: vector.verification_time_unix)
    #expect(artifact.artifactSHA256 == vector.artifact_sha256)
    let verified = try verifier.verifyAssignment(signedAssignment: encoded(vector.signed_assignment), artifact: artifact, channel: "beta", installation: vector.installation, lastSequence: vector.last_sequence, now: vector.verification_time_unix)
    #expect(verified.sequence == 7)
    #expect(verified.cohortBucket == vector.cohort_bucket)
}

@Test func tamperingReplayScopeAndAuthorityFailClosed() throws {
    let vector = try fixture()
    let verifier = try ReleaseVerifier(host: vector.host, roots: vector.roots)
    let signed = try encoded(vector.signed_manifest)
    #expect(throws: UpdateError.self) { try verifier.verifyArtifact(signedManifest: signed, payload: vector.payload + Data([0]), now: vector.verification_time_unix) }
    var envelope = try #require(vector.signed_manifest.object)
    var manifest = try #require(envelope["manifest"]?.object)
    manifest["surprise"] = .boolean(true); envelope["manifest"] = .object(manifest)
    #expect(throws: UpdateError.self) { try verifier.verifyArtifact(signedManifest: encoded(CanonicalValue.object(envelope)), payload: vector.payload, now: vector.verification_time_unix) }
    let artifact = try verifier.verifyArtifact(signedManifest: signed, payload: vector.payload, now: vector.verification_time_unix)
    #expect(throws: UpdateError.self) { try verifier.verifyAssignment(signedAssignment: encoded(vector.signed_assignment), artifact: artifact, channel: "production", installation: vector.installation, lastSequence: 6, now: vector.verification_time_unix) }
    #expect(throws: UpdateError.self) { try verifier.verifyAssignment(signedAssignment: encoded(vector.signed_assignment), artifact: artifact, channel: "beta", installation: vector.installation, lastSequence: 7, now: vector.verification_time_unix) }
    let revoked = vector.roots.map { TrustRoot(keyID: $0.keyID, publicKey: $0.publicKey, scope: $0.scope, artifact: $0.artifact, assignment: $0.assignment, revoked: true) }
    let revokedVerifier = try ReleaseVerifier(host: vector.host, roots: revoked)
    #expect(throws: UpdateError.self) { try revokedVerifier.verifyArtifact(signedManifest: signed, payload: vector.payload, now: vector.verification_time_unix) }
    let expired = vector.roots.map { TrustRoot(keyID: $0.keyID, publicKey: $0.publicKey, scope: $0.scope, artifact: $0.artifact, assignment: $0.assignment, notAfterUnix: vector.verification_time_unix) }
    #expect(throws: UpdateError.self) { try ReleaseVerifier(host: vector.host, roots: expired).verifyArtifact(signedManifest: signed, payload: vector.payload, now: vector.verification_time_unix) }
    #expect(throws: UpdateError.self) { try ReleaseVerifier(host: vector.host, roots: vector.roots + [vector.roots[0]]) }
}

@Test func strictJSONRejectsAmbiguousAndUnboundedDocuments() throws {
    for json in ["{\"a\":1,\"a\":2}", "{\"a\":{\"x\":1,\"\\u0078\":2}}", "{\"n\":-1}", "{\"n\":1.0}", "{\"n\":01}", "{} {}", "[true,]"] {
        #expect(throws: (any Error).self) { try StrictJSON.decode(CanonicalValue.self, from: Data(json.utf8)) }
    }
    let deep = String(repeating: "[", count: 34) + "0" + String(repeating: "]", count: 34)
    #expect(throws: UpdateError.self) { try StrictJSON.decode(CanonicalValue.self, from: Data(deep.utf8)) }
    #expect(throws: UpdateError.self) { try StrictJSON.decode(CanonicalValue.self, from: Data("{}".utf8), maximumBytes: 1) }
}

@Test func canonicalIntegerBoundariesAndMapOrder() throws {
    let values: [(UInt64, String)] = [(0, "00"), (23, "17"), (24, "1818"), (255, "18ff"), (256, "190100"), (65536, "1a00010000"), (UInt64.max, "1bffffffffffffffff")]
    for (number, expected) in values { #expect(try hex(CanonicalValue.uint(number).canonicalCBOR()) == expected) }
    #expect(try hex(CanonicalValue.object(["b": .uint(1), "a": .uint(2)]).canonicalCBOR()) == "a2616102616201")
}

@Test func wrongRuntimeAndCapabilityBudgetRejectEvenValidSignatures() throws {
    let vector = try fixture()
    let h = vector.host
    let wrongRuntime = InstalledRuntime(scope: h.scope, runtime: String(repeating: "0", count: 64), capabilityHashes: h.capabilityHashes, stateVersion: h.stateVersion, maxPayloadBytes: h.maxPayloadBytes, limits: h.limits)
    let wrongCaps = InstalledRuntime(scope: h.scope, runtime: h.runtime, capabilityHashes: [:], stateVersion: h.stateVersion, maxPayloadBytes: h.maxPayloadBytes, limits: h.limits)
    let wrongState = InstalledRuntime(scope: h.scope, runtime: h.runtime, capabilityHashes: h.capabilityHashes, stateVersion: 2, maxPayloadBytes: h.maxPayloadBytes, limits: h.limits)
    for host in [wrongRuntime, wrongCaps, wrongState] {
        #expect(throws: UpdateError.self) { try ReleaseVerifier(host: host, roots: vector.roots).verifyArtifact(signedManifest: encoded(vector.signed_manifest), payload: vector.payload, now: vector.verification_time_unix) }
    }
}
