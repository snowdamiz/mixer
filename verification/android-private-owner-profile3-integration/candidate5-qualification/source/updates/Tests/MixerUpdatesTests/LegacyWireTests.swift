import Foundation
import Testing
@testable import MixerUpdates

private struct LegacyWireDocument: Decodable { let name: String; let kind: String; let accepted: Bool; let json: String }
private struct LegacyWireCorpus: Decodable {
    let test_only: Bool
    let host: InstalledRuntime
    let roots: [TrustRoot]
    let payload: Data
    let signed_manifest: CanonicalValue
    let signed_assignment: CanonicalValue
    let verification_time_unix: UInt64
    let installation: String
    let last_sequence: UInt64
    let artifact_sha256: String
    let manifest_cbor_hex: String
    let assignment_cbor_hex: String
    let documents: [LegacyWireDocument]
}
private func legacyWireFixture() throws -> LegacyWireCorpus {
    let file = try #require(Bundle.module.url(forResource: "legacy-v1-wire-cases", withExtension: "json", subdirectory: "Fixtures"))
    return try StrictJSON.decode(LegacyWireCorpus.self, from: Data(contentsOf: file))
}
private func legacyWireEncoded<T: Encodable>(_ value: T) throws -> Data { try JSONEncoder().encode(value) }
private func legacyWireHex(_ data: Data) -> String { data.map { String(format: "%02x", $0) }.joined() }

@Test func legacyV1SharedStrictWireCorpusMatchesGoAndKeepsDynamicMapKeys() throws {
    let v = try legacyWireFixture()
    #expect(v.test_only && v.documents.count == 271)
    let verifier = try ReleaseVerifier(host: v.host, roots: v.roots)
    let manifestData = try legacyWireEncoded(v.signed_manifest)
    let artifact = try verifier.verifyArtifact(signedManifest: manifestData, payload: v.payload, now: v.verification_time_unix)
    #expect(artifact.artifactSHA256 == v.artifact_sha256 && artifact.capabilityGrants == nil)
    #expect(v.host.capabilityHashes.keys.sorted() == ["SCHEMA", "Schema", "schema", "state"])
    #expect(try legacyWireHex(#require(v.signed_manifest.object?["manifest"]).canonicalCBOR()) == v.manifest_cbor_hex)
    #expect(try legacyWireHex(#require(v.signed_assignment.object?["assignment"]).canonicalCBOR()) == v.assignment_cbor_hex)
    for document in v.documents {
        do {
            let data = Data(document.json.utf8)
            switch document.kind {
            case "manifest":
                _ = try verifier.verifyArtifact(signedManifest: data, payload: v.payload, now: v.verification_time_unix)
            case "assignment":
                _ = try verifier.verifyAssignment(signedAssignment: data, artifact: artifact, channel: "beta", installation: v.installation,
                    lastSequence: v.last_sequence, now: v.verification_time_unix)
            case "host":
                let host = try StrictJSON.decode(InstalledRuntime.self, from: data)
                _ = try ReleaseVerifier(host: host, roots: v.roots).verifyArtifact(signedManifest: manifestData, payload: v.payload, now: v.verification_time_unix)
            case "root":
                let root = try StrictJSON.decode(TrustRoot.self, from: data)
                _ = try ReleaseVerifier(host: v.host, roots: [root, v.roots[1]]).verifyArtifact(signedManifest: manifestData, payload: v.payload, now: v.verification_time_unix)
            default: Issue.record("Unknown legacy wire fixture kind"); continue
            }
            #expect(document.accepted, "Unexpected acceptance of \(document.kind) case \(document.name)")
        } catch {
            #expect(!document.accepted, "Unexpected rejection of \(document.kind) case \(document.name): \(error)")
        }
    }
}

@Test func legacySignedDocumentByteBoundsAndCanonicalEscapedTransportStayStable() throws {
    let v = try legacyWireFixture(), verifier = try ReleaseVerifier(host: v.host, roots: v.roots)
    let raw = try legacyWireEncoded(v.signed_manifest)
    let exact = raw + Data(repeating: 32, count: 1_048_576 - raw.count)
    #expect(try verifier.verifyArtifact(signedManifest: exact, payload: v.payload, now: v.verification_time_unix).artifactSHA256 == v.artifact_sha256)
    #expect(throws: UpdateError.self) { try verifier.verifyArtifact(signedManifest: exact + Data([32]), payload: v.payload, now: v.verification_time_unix) }
    // Decoded JSON names, rather than the textual spelling of their escapes,
    // determine the closed model field or dynamic dictionary key.
    for name in ["single-escaped-model-key", "single-escaped-dynamic-map-key"] {
        let document = try #require(v.documents.first(where: { $0.name == name }))
        #expect(try verifier.verifyArtifact(signedManifest: Data(document.json.utf8), payload: v.payload, now: v.verification_time_unix).artifactSHA256 == v.artifact_sha256)
    }
}
