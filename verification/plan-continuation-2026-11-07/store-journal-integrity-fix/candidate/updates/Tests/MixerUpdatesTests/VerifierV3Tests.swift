import Foundation
import Crypto
import Testing
import MixerUpdates

// Public test-only Ed25519 seed. Never used for installed signing authority.
struct V3LocalFixture {
    let key: Curve25519.Signing.PrivateKey
    let host: InstalledRuntime
    let roots: [TrustRoot]
    let payload: Data
    let manifest: CanonicalValue
    let assignment: CanonicalValue
    let now: UInt64 = 10_000

    init(payload: Data = Data("v3-independent-swift-payload".utf8), host supplied: InstalledRuntime? = nil) throws {
        key = try Curve25519.Signing.PrivateKey(rawRepresentation: Data(repeating: 0x63, count: 32))
        host = supplied ?? Self.installed()
        roots = [TrustRoot(keyID: "v3-test", publicKey: key.publicKey.rawRepresentation, scope: host.scope,
            artifact: true, assignment: true, notBeforeUnix: 1, notAfterUnix: 20_000)]
        self.payload = payload
        let http = Self.grant("network.http.v1", "fa1549c0a1e2e6b3bf4a83af1a6d37730bbefc8cddc3ffbe3c807d5e7af503f3",
            permission: "network.https", origins: ["https://api.example.test:8443"], methods: ["GET", "POST"], namespaces: [])
        let storage = Self.grant("storage.keyValue.v1", "4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd",
            permission: "storage.appPrivate", origins: [], methods: [], namespaces: ["Drafts", "outbox"])
        manifest = .object([
            "schema":.uint(3),"scope":Self.scope(host.scope),"release_id":.text("local-v3"),
            "source_commit":.text(String(repeating:"a",count:40)),"provenance_id":.text("test-provenance"),
            "runtime":.text(host.runtime),"protocol":.uint(3),"guest_abi":.uint(2),"ui_schema":.uint(1),
            "capability_hashes":.object(host.capabilityHashes.mapValues(CanonicalValue.text)),
            "state_min":.uint(2),"state_max":.uint(8),"payload_sha256":.text(ReleaseVerifier.sha256(payload)),
            "compressed_bytes":.uint(UInt64(payload.count)),"expanded_bytes":.uint(UInt64(payload.count)),
            "compression":.text("none"),"asset_hashes":.object([:]),"source_map_sha256":.text(String(repeating:"b",count:64)),
            "limits":.object(["memory_bytes":.uint(min(65_536,host.limits.memoryBytes)),"fuel":.uint(min(1000,host.limits.fuel)),"startup_milliseconds":.uint(min(500,host.limits.startupMilliseconds))]),
            "key_id":.text("v3-test"),"created_at_unix":.uint(9999),
            "capability_grants":.object(["schema":.uint(1),"schema_sha256":.text(VerifiedCapabilityGrantsV3.descriptorSHA256),"entries":.array(host.capabilityHashes.isEmpty ? [] : [http,storage])])
        ])
        assignment = .object([
            "schema":.uint(3),"scope":Self.scope(host.scope),"channel":.text("beta"),"cohort":.text("sha256-v1"),
            "rollout_basis_points":.uint(10_000),"sequence":.uint(9),"release_id":.text("local-v3"),
            "artifact_sha256":.text(try ReleaseVerifier.sha256(manifest.canonicalCBOR())),"runtime":.text(host.runtime),
            "key_id":.text("v3-test"),"created_at_unix":.uint(9999)
        ])
    }
    static func installed(protocolVersion: UInt64 = 3, abi: UInt64 = 2, ui: UInt64 = 1,
                          caps: [String:String]? = nil, payload: UInt64 = 4096,
                          limits: ResourceLimits = .init(memoryBytes: 131_072,fuel: 10_000,startupMilliseconds: 1000)) -> InstalledRuntime {
        InstalledRuntime(scope:.init(organization:"mixer",project:"proof",app:"app",environment:"test",platform:"ios"),
            runtime:String(repeating:"c",count:64),protocolVersion:protocolVersion,guestABI:abi,uiSchema:ui,
            capabilityHashes:caps ?? ["network.http.v1":"fa1549c0a1e2e6b3bf4a83af1a6d37730bbefc8cddc3ffbe3c807d5e7af503f3","storage.keyValue.v1":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"],
            stateVersion:4,maxPayloadBytes:payload,limits:limits)
    }
    static func scope(_ s: UpdateScope) -> CanonicalValue { .object(["organization":.text(s.organization),"project":.text(s.project),"app":.text(s.app),"environment":.text(s.environment),"platform":.text(s.platform)]) }
    static func grant(_ id: String,_ hash: String,permission: String,origins:[String],methods:[String],namespaces:[String]) -> CanonicalValue {
        .object(["capability_id":.text(id),"schema_sha256":.text(hash),"permissions":.array([.text(permission)]),"origins":.array(origins.map(CanonicalValue.text)),"methods":.array(methods.map(CanonicalValue.text)),"namespaces":.array(namespaces.map(CanonicalValue.text))])
    }
    func verifier(roots: [TrustRoot]? = nil) throws -> ReleaseVerifierV3 { try ReleaseVerifierV3(host:host,roots:roots ?? self.roots) }
    func signed(_ value: CanonicalValue, assignment: Bool = false, domain: String? = nil,
                signingKey: Curve25519.Signing.PrivateKey? = nil) throws -> Data {
        let prefix = domain ?? (assignment ? "mixer.assignment.v3\0" : "mixer.artifact.v3\0")
        let signature = try (signingKey ?? key).signature(for: Data(prefix.utf8) + value.canonicalCBOR())
        return try v3JSON(.object([assignment ? "assignment":"manifest":value,"signature":.text(signature.base64EncodedString())]))
    }
    func artifact(_ verifier: ReleaseVerifierV3) throws -> VerifiedArtifactV3 {
        try verifier.verifyArtifact(signedManifest:signed(manifest),payload:payload,now:now)
    }
}
func v3JSON(_ value: CanonicalValue) throws -> Data { try JSONEncoder().encode(value) }
func v3Changed(_ value: CanonicalValue,_ update:(inout [String:CanonicalValue]) throws -> Void) throws -> CanonicalValue {
    var fields = try #require(value.object); try update(&fields); return .object(fields)
}

@Test func v3LocalProofContainsMandatoryBoundedSignedGrantsAndOldVerifierRejectsHost() throws {
    let f = try V3LocalFixture(), verifier = try f.verifier(), artifact = try f.artifact(verifier)
    #expect(artifact.payloadBytes == UInt64(f.payload.count) && artifact.releaseID == "local-v3")
    #expect(artifact.capabilityGrants.schema == 1 && artifact.capabilityGrants.schemaSHA256 == VerifiedCapabilityGrants.descriptorSHA256)
    #expect(artifact.capabilityGrants.entries.map(\.capabilityID) == ["network.http.v1","storage.keyValue.v1"])
    #expect(artifact.capabilityGrants.entries[1].namespaces == ["Drafts","outbox"])
    let result = try verifier.verifyAssignment(signedAssignment:f.signed(f.assignment,assignment:true),artifact:artifact,
        channel:"beta",installation:"install-a",lastSequence:8,now:f.now)
    #expect(result.sequence == 9 && result.artifactSHA256 == artifact.artifactSHA256)
    #expect(throws:UpdateError.self) { try ReleaseVerifier(host:f.host,roots:f.roots) }
    let empty = try V3LocalFixture(host:V3LocalFixture.installed(caps:[:]))
    #expect(try empty.artifact(empty.verifier()).capabilityGrants.entries.isEmpty)
}

@Test func v3HostRejectsEveryWidenedTupleCapabilityAndResource() throws {
    let f = try V3LocalFixture()
    var invalid = [V3LocalFixture.installed(protocolVersion:1),V3LocalFixture.installed(protocolVersion:2),V3LocalFixture.installed(protocolVersion:4),
                   V3LocalFixture.installed(abi:1),V3LocalFixture.installed(abi:3),V3LocalFixture.installed(ui:0),V3LocalFixture.installed(ui:2),
                   V3LocalFixture.installed(caps:["unknown.v1":String(repeating:"a",count:64)]),V3LocalFixture.installed(caps:["network.http.v1":String(repeating:"a",count:64)]),
                   V3LocalFixture.installed(payload:0),V3LocalFixture.installed(payload:4_194_305)]
    for limits in [ResourceLimits(memoryBytes:0,fuel:1,startupMilliseconds:1),.init(memoryBytes:4_194_305,fuel:1,startupMilliseconds:1),
                   .init(memoryBytes:1,fuel:0,startupMilliseconds:1),.init(memoryBytes:1,fuel:1_000_001,startupMilliseconds:1),
                   .init(memoryBytes:1,fuel:1,startupMilliseconds:0),.init(memoryBytes:1,fuel:1,startupMilliseconds:60_001)] {
        invalid.append(V3LocalFixture.installed(limits:limits))
    }
    for h in invalid { #expect(throws:UpdateError.self) { try ReleaseVerifierV3(host:h,roots:f.roots) } }
    _ = try ReleaseVerifierV3(host:V3LocalFixture.installed(payload:1,limits:.init(memoryBytes:1,fuel:1,startupMilliseconds:1)),roots:f.roots)
}

@Test func v3RootsRequireBoundedUniqueWellFormedAuthority() throws {
    let f = try V3LocalFixture(), r = f.roots[0]
    let badRoots: [[TrustRoot]] = [[],Array(repeating:r,count:129),[r,r],
        [.init(keyID:r.keyID,publicKey:Data(repeating:0,count:31),scope:r.scope,artifact:true,assignment:true)],
        [.init(keyID:r.keyID,publicKey:r.publicKey,scope:r.scope,artifact:false,assignment:false)],
        [.init(keyID:r.keyID,publicKey:r.publicKey,scope:r.scope,artifact:true,assignment:true,notBeforeUnix:10,notAfterUnix:10)],
        [.init(keyID:"bad key",publicKey:r.publicKey,scope:r.scope,artifact:true,assignment:true)]]
    for roots in badRoots { #expect(throws:UpdateError.self) { try f.verifier(roots:roots) } }
}

@Test func v3SignedNestedShapeVersionsStateAndGlobalLimitsAreChecked() throws {
    let f = try V3LocalFixture(), verifier = try f.verifier()
    var mutations: [CanonicalValue] = []
    for (field,value) in ["schema":CanonicalValue.uint(2),"protocol":.uint(2),"guest_abi":.uint(1),"ui_schema":.uint(2),"state_min":.uint(5),"state_max":.uint(3),"created_at_unix":.uint(0),"asset_hashes":.object(["asset":.text(String(repeating:"e",count:64))]),"compression":.text("gzip"),"surprise":.uint(1),"capability_hashes":.object([:])] {
        mutations.append(try v3Changed(f.manifest) { $0[field]=value })
    }
    for field in ["scope","limits","capability_grants"] {
        mutations.append(try v3Changed(f.manifest) { root in root[field] = try v3Changed(try #require(root[field])) { $0["surprise"] = .uint(1) } })
    }
    for (field,value) in ["memory_bytes":UInt64(4_194_305),"fuel":1_000_001,"startup_milliseconds":60_001] {
        mutations.append(try v3Changed(f.manifest) { root in root["limits"] = try v3Changed(try #require(root["limits"])) { $0[field] = .uint(value) } })
    }
    for m in mutations { #expect(throws:(any Error).self) { try verifier.verifyArtifact(signedManifest:f.signed(m),payload:f.payload,now:f.now) } }
}

@Test func v3ExactDocumentAndPayloadBoundariesUseGlobalAndInstalledCeilings() throws {
    let bytes = Data(repeating:0x5a,count:4_194_304)
    let f = try V3LocalFixture(payload:bytes,host:V3LocalFixture.installed(payload:4_194_304,limits:.init(memoryBytes:4_194_304,fuel:1_000_000,startupMilliseconds:60_000)))
    let verifier = try f.verifier(), signed = try f.signed(f.manifest)
    let exact = signed + Data(repeating:32,count:65_536-signed.count)
    let artifact = try verifier.verifyArtifact(signedManifest:exact,payload:bytes,now:f.now)
    #expect(artifact.payloadBytes == 4_194_304)
    #expect(throws:UpdateError.self) { try verifier.verifyArtifact(signedManifest:exact+Data([32]),payload:bytes,now:f.now) }
    #expect(throws:UpdateError.self) { try verifier.verifyArtifact(signedManifest:exact,payload:bytes+Data([0]),now:f.now) }
    let assignment = try f.signed(f.assignment,assignment:true)
    let exactAssignment = assignment + Data(repeating:32,count:65_536-assignment.count)
    _ = try verifier.verifyAssignment(signedAssignment:exactAssignment,artifact:artifact,channel:"beta",installation:"install",lastSequence:8,now:f.now)
    #expect(throws:UpdateError.self) { try verifier.verifyAssignment(signedAssignment:exactAssignment+Data([32]),artifact:artifact,channel:"beta",installation:"install",lastSequence:8,now:f.now) }
}

@Test func v3WrongSignatureDomainsAndAmbiguousRawDocumentsFailClosed() throws {
    let f = try V3LocalFixture(), verifier = try f.verifier(), good = try f.signed(f.manifest)
    for domain in ["mixer.artifact.v1\0","mixer.artifact.v2\0","mixer.assignment.v3\0","mixer.artifact.v3\\0"] {
        #expect(throws:UpdateError.self) { try verifier.verifyArtifact(signedManifest:f.signed(f.manifest,domain:domain),payload:f.payload,now:f.now) }
    }
    let text = String(decoding:good,as:UTF8.self)
    for raw in ["\u{feff}"+text,text+"{}",text.replacingOccurrences(of:"\"schema\":3",with:"\"schema\":3,\"\\u0073chema\":3"),
                text.replacingOccurrences(of:"\"schema\":3",with:"\"schema\":3.0"),text.replacingOccurrences(of:"\"schema\":3",with:"\"schema\":true"),
                text.replacingOccurrences(of:"\"schema\":3",with:"\"schema\":3e0"),text.replacingOccurrences(of:"\"capability_hashes\":",with:"\"capability_hashes\":null,\"unused\":")] {
        #expect(throws:(any Error).self) { try verifier.verifyArtifact(signedManifest:Data(raw.utf8),payload:f.payload,now:f.now) }
    }
    let badUTF8 = Data([0xff])+good
    #expect(throws:(any Error).self) { try verifier.verifyArtifact(signedManifest:badUTF8,payload:f.payload,now:f.now) }
}

@Test func v3SignedGrantFamilyAndOrderCannotBeBypassedByValidSignature() throws {
    let f = try V3LocalFixture(), verifier = try f.verifier()
    let grant = try #require(f.manifest.object?["capability_grants"]), entries = try #require(grant.object?["entries"])
    guard case let .array(items) = entries else { Issue.record("fixture entries absent"); return }
    var badEntries: [[CanonicalValue]] = [[items[1],items[0]],[items[0],items[0]]]
    for (field,value) in ["permissions":CanonicalValue.array([.text("storage.appPrivate")]),"origins":.array([.text("https://UPPER.test")]),"methods":.array([.text("POST"),.text("GET")]),"namespaces":.array([.text("outbox")]),"surprise":.uint(1)] {
        badEntries.append([try v3Changed(items[0]) { $0[field]=value },items[1]])
    }
    for list in badEntries {
        let changed = try v3Changed(f.manifest) { root in root["capability_grants"] = try v3Changed(grant) { $0["entries"] = .array(list) } }
        #expect(throws:(any Error).self) { try verifier.verifyArtifact(signedManifest:f.signed(changed),payload:f.payload,now:f.now) }
    }
    let denied = try v3Changed(f.manifest) { root in root["capability_grants"] = try v3Changed(grant) { $0["entries"] = .array([]) } }
    #expect(try verifier.verifyArtifact(signedManifest:f.signed(denied),payload:f.payload,now:f.now).capabilityGrants.entries.isEmpty)
}

private struct V3SharedVector: Decodable {
    let test_only: Bool
    let host: InstalledRuntime
    let roots: [TrustRoot]
    let payload: Data
    let signed_manifest: CanonicalValue
    let signed_assignment: CanonicalValue
    let manifest_cbor_hex: String
    let assignment_cbor_hex: String
    let manifest_message_hex: String
    let assignment_message_hex: String
    let artifact_sha256: String
    let grant_descriptor: CanonicalValue
    let grant_descriptor_cbor_hex: String
    let installation: String
    let cohort_bucket: UInt64
    let verification_time_unix: UInt64
    let last_sequence: UInt64
}
private struct V3ManifestCase: Decodable { let name: String; let accepted: Bool; let signed_manifest_json: String }
private struct V3AssignmentCase: Decodable { let name: String; let accepted: Bool; let signed_assignment_json: String }
private struct V3StringCase: Decodable { let value: String; let accepted: Bool }
private struct V3SharedCases: Decodable {
    let test_only: Bool
    let cases: [V3ManifestCase]
    let assignment_cases: [V3AssignmentCase]
    let origin_cases: [V3StringCase]
    let namespace_cases: [V3StringCase]
}
private func v3Shared<T:Decodable>(_ name:String,_ type:T.Type) throws -> T {
    let file = try #require(Bundle.module.url(forResource:name,withExtension:"json",subdirectory:"Fixtures"))
    return try StrictJSON.decode(type,from:Data(contentsOf:file))
}
private func v3Hex(_ bytes:Data) -> String { bytes.map { String(format:"%02x",$0) }.joined() }

@Test func v3SharedGoVectorMatchesCanonicalMessagesSignaturesAndArtifactIdentity() throws {
    let v = try v3Shared("signed-release-v3",V3SharedVector.self)
    #expect(v.test_only)
    let manifest = try #require(v.signed_manifest.object?["manifest"]), assignment = try #require(v.signed_assignment.object?["assignment"])
    let mc = try manifest.canonicalCBOR(), ac = try assignment.canonicalCBOR()
    #expect(v3Hex(mc) == v.manifest_cbor_hex && v3Hex(ac) == v.assignment_cbor_hex)
    #expect(v3Hex(Data("mixer.artifact.v3\0".utf8)+mc) == v.manifest_message_hex)
    #expect(v3Hex(Data("mixer.assignment.v3\0".utf8)+ac) == v.assignment_message_hex)
    #expect(try v3Hex(v.grant_descriptor.canonicalCBOR()) == v.grant_descriptor_cbor_hex)
    #expect(try ReleaseVerifier.sha256(v.grant_descriptor.canonicalCBOR()) == VerifiedCapabilityGrantsV3.descriptorSHA256)
    let verifier = try ReleaseVerifierV3(host:v.host,roots:v.roots)
    let artifact = try verifier.verifyArtifact(signedManifest:v3JSON(v.signed_manifest),payload:v.payload,now:v.verification_time_unix)
    #expect(artifact.artifactSHA256 == v.artifact_sha256 && artifact.capabilityGrants.entries.count == 2)
    let selected = try verifier.verifyAssignment(signedAssignment:v3JSON(v.signed_assignment),artifact:artifact,
        channel:"beta",installation:v.installation,lastSequence:v.last_sequence,now:v.verification_time_unix)
    #expect(selected.sequence == 7 && selected.cohortBucket == v.cohort_bucket)
}

@Test func v3SharedRawCorpusChecksEveryManifestAssignmentAndGrantGrammarCase() throws {
    let v = try v3Shared("signed-release-v3",V3SharedVector.self), corpus = try v3Shared("release-v3-cases",V3SharedCases.self)
    #expect(corpus.test_only && corpus.cases.count == 154 && corpus.assignment_cases.count == 36)
    #expect(corpus.origin_cases.count == 39 && corpus.namespace_cases.count == 14)
    let verifier = try ReleaseVerifierV3(host:v.host,roots:v.roots)
    let artifact = try verifier.verifyArtifact(signedManifest:v3JSON(v.signed_manifest),payload:v.payload,now:v.verification_time_unix)
    for item in corpus.cases {
        do {
            _ = try verifier.verifyArtifact(signedManifest:Data(item.signed_manifest_json.utf8),payload:v.payload,now:v.verification_time_unix)
            #expect(item.accepted,"Unexpected v3 manifest acceptance: \(item.name)")
        } catch { #expect(!item.accepted,"Unexpected v3 manifest rejection: \(item.name): \(error)") }
    }
    for item in corpus.assignment_cases {
        do {
            _ = try verifier.verifyAssignment(signedAssignment:Data(item.signed_assignment_json.utf8),artifact:artifact,
                channel:"beta",installation:v.installation,lastSequence:v.last_sequence,now:v.verification_time_unix)
            #expect(item.accepted,"Unexpected v3 assignment acceptance: \(item.name)")
        } catch { #expect(!item.accepted,"Unexpected v3 assignment rejection: \(item.name): \(error)") }
    }
    // Independently sign each grammar value with the local test-only Swift key,
    // so a malformed grant is not rejected merely for a stale Go signature.
    let f = try V3LocalFixture(), local = try f.verifier(), grants = try #require(f.manifest.object?["capability_grants"])
    guard case let .array(entries) = grants.object?["entries"] else { Issue.record("local fixture grants absent"); return }
    for (items,index,field) in [(corpus.origin_cases,0,"origins"),(corpus.namespace_cases,1,"namespaces")] {
        for item in items {
            var changedEntries = entries
            changedEntries[index] = try v3Changed(entries[index]) { $0[field] = .array([.text(item.value)]) }
            let changed = try v3Changed(f.manifest) { root in root["capability_grants"] = try v3Changed(grants) { $0["entries"] = .array(changedEntries) } }
            do {
                _ = try local.verifyArtifact(signedManifest:f.signed(changed),payload:f.payload,now:f.now)
                #expect(item.accepted,"Unexpected v3 \(field) acceptance: \(item.value)")
            } catch { #expect(!item.accepted,"Unexpected v3 \(field) rejection: \(item.value): \(error)") }
        }
    }
    print("V3_SHARED_CORPUS manifests=154 assignments=36 origins=39 namespaces=14")
}
