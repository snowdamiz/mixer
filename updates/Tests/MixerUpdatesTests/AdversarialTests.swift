import Foundation
import Testing
import Crypto
@testable import MixerUpdates

private struct ReviewFixture: Decodable {
    let host: InstalledRuntime
    let roots: [TrustRoot]
    let payload: Data
    let signed_manifest: CanonicalValue
    let signed_assignment: CanonicalValue
    let installation: String
    let verification_time_unix: UInt64
    let last_sequence: UInt64
}

private func reviewFixture() throws -> ReviewFixture {
    let url = try #require(Bundle.module.url(forResource: "signed-release-v1", withExtension: "json", subdirectory: "Fixtures"))
    return try StrictJSON.decode(ReviewFixture.self, from: Data(contentsOf: url))
}

private func json<T: Encodable>(_ value: T) throws -> Data { try JSONEncoder().encode(value) }

private func expectUpdateError(_ code: String, _ operation: () throws -> Void) {
    do { try operation(); Issue.record("Expected rejection: \(code)") }
    catch let error as UpdateError { #expect(error.code == code) }
    catch { Issue.record("Unexpected error: \(error)") }
}

@Test func artifactTokensCannotTransferAuthorityBetweenVerifierConfigurations() throws {
    let fixture = try reviewFixture()
    let sourceVerifier = try ReleaseVerifier(host: fixture.host, roots: fixture.roots)
    let artifact = try sourceVerifier.verifyArtifact(signedManifest: json(fixture.signed_manifest), payload: fixture.payload, now: fixture.verification_time_unix)
    let artifactRoot = try #require(fixture.roots.first(where: { $0.artifact }))
    let assignmentRoots = fixture.roots.filter { !$0.artifact }
    let replacementKey = Curve25519.Signing.PrivateKey().publicKey.rawRepresentation
    let variants: [(TrustRoot?, String)] = [
        (nil, "signature.authority"),
        (TrustRoot(keyID: artifactRoot.keyID, publicKey: artifactRoot.publicKey, scope: artifactRoot.scope, artifact: true, assignment: false, revoked: true), "signature.authority"),
        (TrustRoot(keyID: artifactRoot.keyID, publicKey: replacementKey, scope: artifactRoot.scope, artifact: true, assignment: false), "signature.invalid"),
        (TrustRoot(keyID: artifactRoot.keyID, publicKey: artifactRoot.publicKey, scope: artifactRoot.scope, artifact: false, assignment: true), "signature.authority"),
        (TrustRoot(keyID: artifactRoot.keyID, publicKey: artifactRoot.publicKey, scope: artifactRoot.scope, artifact: true, assignment: false, notAfterUnix: fixture.verification_time_unix), "signature.authority"),
        (TrustRoot(keyID: artifactRoot.keyID, publicKey: artifactRoot.publicKey, scope: artifactRoot.scope, artifact: true, assignment: false, notBeforeUnix: fixture.verification_time_unix + 1), "signature.authority"),
    ]
    for (root, code) in variants {
        let currentVerifier = try ReleaseVerifier(host: fixture.host, roots: assignmentRoots + (root.map { [$0] } ?? []))
        expectUpdateError(code) {
            _ = try currentVerifier.verifyAssignment(signedAssignment: json(fixture.signed_assignment), artifact: artifact,
                channel: "beta", installation: fixture.installation, lastSequence: fixture.last_sequence, now: fixture.verification_time_unix)
        }
    }
}

@Test func newAssignmentsRecheckArtifactAuthorityAtCurrentTime() throws {
    let fixture = try reviewFixture()
    let roots = fixture.roots.map { root in
        TrustRoot(keyID: root.keyID, publicKey: root.publicKey, scope: root.scope, artifact: root.artifact,
            assignment: root.assignment, notAfterUnix: root.artifact ? fixture.verification_time_unix + 1 : 0)
    }
    let verifier = try ReleaseVerifier(host: fixture.host, roots: roots)
    let artifact = try verifier.verifyArtifact(signedManifest: json(fixture.signed_manifest), payload: fixture.payload, now: fixture.verification_time_unix)
    expectUpdateError("signature.authority") {
        _ = try verifier.verifyAssignment(signedAssignment: json(fixture.signed_assignment), artifact: artifact,
            channel: "beta", installation: fixture.installation, lastSequence: fixture.last_sequence, now: fixture.verification_time_unix + 1)
    }
}

@Test func pinnedConfigurationRejectsUnknownFieldsAtEveryObjectBoundary() throws {
    let fixture = try reviewFixture()
    let hostValue = try StrictJSON.decode(CanonicalValue.self, from: json(fixture.host))
    var host = try #require(hostValue.object)
    host["future_security_policy"] = .boolean(true)
    expectUpdateError("manifest.fields") { _ = try StrictJSON.decode(InstalledRuntime.self, from: json(CanonicalValue.object(host))) }
    host = try #require(hostValue.object)
    var scope = try #require(host["scope"]?.object); scope["tenant_alias"] = .text("other")
    host["scope"] = .object(scope)
    expectUpdateError("manifest.fields") { _ = try StrictJSON.decode(InstalledRuntime.self, from: json(CanonicalValue.object(host))) }
    host = try #require(hostValue.object)
    var limits = try #require(host["limits"]?.object); limits["allow_unmetered"] = .boolean(true)
    host["limits"] = .object(limits)
    expectUpdateError("manifest.fields") { _ = try StrictJSON.decode(InstalledRuntime.self, from: json(CanonicalValue.object(host))) }
    var root = try #require(StrictJSON.decode(CanonicalValue.self, from: json(fixture.roots[0])).object)
    root["delegate_all_roles"] = .boolean(true)
    expectUpdateError("manifest.fields") { _ = try StrictJSON.decode(TrustRoot.self, from: json(CanonicalValue.object(root))) }
}

private func signed(_ value: CanonicalValue, field: String, domain: String, key: Curve25519.Signing.PrivateKey) throws -> Data {
    let signature = try key.signature(for: Data(domain.utf8) + value.canonicalCBOR())
    return try json(CanonicalValue.object([field: value, "signature": .text(signature.base64EncodedString())]))
}

@Test func evenSharedKeysCannotCrossArtifactAndAssignmentSignatureDomains() throws {
    let fixture = try reviewFixture()
    // Ephemeral test key exists only in this test process and is never persisted.
    let key = Curve25519.Signing.PrivateKey()
    let root = TrustRoot(keyID: "review.shared", publicKey: key.publicKey.rawRepresentation, scope: fixture.host.scope, artifact: true, assignment: true)
    let verifier = try ReleaseVerifier(host: fixture.host, roots: [root])
    var manifest = try #require(fixture.signed_manifest.object?["manifest"]?.object)
    manifest["key_id"] = .text(root.keyID)
    let value = CanonicalValue.object(manifest)
    expectUpdateError("signature.invalid") {
        _ = try verifier.verifyArtifact(signedManifest: signed(value, field: "manifest", domain: "mixer.assignment.v1\0", key: key), payload: fixture.payload, now: fixture.verification_time_unix)
    }
    let artifact = try verifier.verifyArtifact(signedManifest: signed(value, field: "manifest", domain: "mixer.artifact.v1\0", key: key), payload: fixture.payload, now: fixture.verification_time_unix)
    var assignment = try #require(fixture.signed_assignment.object?["assignment"]?.object)
    assignment["key_id"] = .text(root.keyID); assignment["artifact_sha256"] = .text(artifact.artifactSHA256)
    expectUpdateError("signature.invalid") {
        _ = try verifier.verifyAssignment(signedAssignment: signed(.object(assignment), field: "assignment", domain: "mixer.artifact.v1\0", key: key), artifact: artifact,
            channel: "beta", installation: fixture.installation, lastSequence: fixture.last_sequence, now: fixture.verification_time_unix)
    }
    #expect(try verifier.verifyAssignment(signedAssignment: signed(.object(assignment), field: "assignment", domain: "mixer.assignment.v1\0", key: key), artifact: artifact,
        channel: "beta", installation: fixture.installation, lastSequence: fixture.last_sequence, now: fixture.verification_time_unix).sequence == 7)
}

@Test func boundedInputReadsExactLimitsAndRejectsGrowthAndNonregularFiles() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-update-review-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: directory) }
    let file = directory.appendingPathComponent("input.json")
    try Data(repeating: 0x41, count: 128).write(to: file)
    #expect(try UpdateInputFile.read(file, maximumBytes: 128).count == 128)
    expectUpdateError("file.size") { _ = try UpdateInputFile.read(file, maximumBytes: 127) }
    expectUpdateError("file.kind") { _ = try UpdateInputFile.read(directory, maximumBytes: 128) }
    expectUpdateError("file.limit") { _ = try UpdateInputFile.read(file, maximumBytes: 0) }
    expectUpdateError("file.limit") { _ = try UpdateInputFile.read(file, maximumBytes: Int.max) }
    // Exercise the actual bounded reader independently of the early stat check,
    // as if a file grew between checking metadata and opening its current contents.
    try Data(repeating: 0x41, count: 129).write(to: file)
    let handle = try FileHandle(forReadingFrom: file)
    defer { try? handle.close() }
    expectUpdateError("file.size") { _ = try UpdateInputFile.read(handle, maximumBytes: 128) }
}

@Test func strictTransportRejectsMalformedUnicodeAndUnsignedIntegerAmbiguity() throws {
    for raw in [#"{"a":1,"\u0061":2}"#, #"{"a":"\ud800"}"#, #"{"a":"\udc00"}"#,
                #"{"a":18446744073709551616}"#, #"{"a":1e0}"#, #"{"a":1.0}"#,
                #"{"a":+1}"#, #"{"a":null}"#] {
        #expect(throws: (any Error).self) { try StrictJSON.decode(CanonicalValue.self, from: Data(raw.utf8)) }
    }
    #expect(throws: (any Error).self) { try StrictJSON.decode(CanonicalValue.self, from: Data([0x22, 0xff, 0x22])) }
    #expect(throws: UpdateError.self) { try StrictJSON.decode(CanonicalValue.self, from: Data(repeating: 0x20, count: 1_048_577)) }
    #expect(try StrictJSON.decode(CanonicalValue.self, from: Data("18446744073709551615".utf8)) == .uint(UInt64.max))
    #expect(try StrictJSON.decode(CanonicalValue.self, from: Data(#""\ud83d\ude00""#.utf8)) == .text("😀"))
}

@Test func canonicalEncoderRejectsOversizedAndDeepValuesAndOrdersEncodedKeys() throws {
    #expect(try CanonicalValue.object(["aa": .uint(1), "b": .uint(2)]).canonicalCBOR() == Data([0xa2, 0x61, 0x62, 0x02, 0x62, 0x61, 0x61, 0x01]))
    expectUpdateError("manifest.string") { _ = try CanonicalValue.text(String(repeating: "x", count: 65_537)).canonicalCBOR() }
    expectUpdateError("manifest.array") { _ = try CanonicalValue.array(Array(repeating: .uint(0), count: 4097)).canonicalCBOR() }
    let chunk = CanonicalValue.text(String(repeating: "x", count: 65_536))
    expectUpdateError("manifest.size") { _ = try CanonicalValue.array(Array(repeating: chunk, count: 17)).canonicalCBOR() }
    var deep = CanonicalValue.uint(0)
    for _ in 0..<34 { deep = .array([deep]) }
    expectUpdateError("manifest.depth") { _ = try deep.canonicalCBOR() }
}
