import Foundation
import Crypto
import Testing
import MixerUpdates

@Test func v3VerifierCopiesShareContextWhileFreshVerifierMustReverifySignedBytes() throws {
    let f = try V3LocalFixture(), verifier = try f.verifier(), artifact = try f.artifact(verifier)
    let copy = verifier, signed = try f.signed(f.assignment,assignment:true)
    _ = try copy.verifyAssignment(signedAssignment:signed,artifact:artifact,channel:"beta",installation:"a",lastSequence:8,now:f.now)
    let fresh = try f.verifier()
    do {
        _ = try fresh.verifyAssignment(signedAssignment:signed,artifact:artifact,channel:"beta",installation:"a",lastSequence:8,now:f.now)
        Issue.record("separate context accepted old proof")
    } catch let error as UpdateError { #expect(error.code == "v3.proof.context") }
    #expect(throws:UpdateError.self) { try fresh.revalidateArtifact(artifact,payload:f.payload,now:f.now) }
    let newArtifact = try f.artifact(fresh)
    _ = try fresh.verifyAssignment(signedAssignment:signed,artifact:newArtifact,channel:"beta",installation:"a",lastSequence:8,now:f.now)
}

@Test func v3ArtifactRevalidationChecksCurrentAuthorityAndExactPayload() throws {
    let f = try V3LocalFixture(), verifier = try f.verifier(), artifact = try f.artifact(verifier)
    let renewed = try verifier.revalidateArtifact(artifact,payload:f.payload,now:f.now+1)
    #expect(renewed.artifactSHA256 == artifact.artifactSHA256)
    #expect(throws:UpdateError.self) { try verifier.revalidateArtifact(artifact,payload:f.payload+Data([0]),now:f.now) }
    #expect(throws:UpdateError.self) { try verifier.revalidateArtifact(artifact,payload:f.payload,now:20_000) }
    #expect(throws:UpdateError.self) { try verifier.revalidateArtifact(artifact,payload:f.payload,now:0) }
}

@Test func v3AssignmentReauthorizesExpiredArtifactEvenWhenAssignmentKeyIsCurrent() throws {
    let f = try V3LocalFixture()
    let other = try Curve25519.Signing.PrivateKey(rawRepresentation:Data(repeating:0x27,count:32))
    let roots = [TrustRoot(keyID:"v3-test",publicKey:f.key.publicKey.rawRepresentation,scope:f.host.scope,artifact:true,assignment:false,notBeforeUnix:1,notAfterUnix:f.now+5),
                 TrustRoot(keyID:"assignment",publicKey:other.publicKey.rawRepresentation,scope:f.host.scope,artifact:false,assignment:true,notBeforeUnix:1,notAfterUnix:20_000)]
    let verifier = try f.verifier(roots:roots), artifact = try f.artifact(verifier)
    let assignment = try v3Changed(f.assignment) { $0["key_id"] = .text("assignment") }
    let signed = try f.signed(assignment,assignment:true,signingKey:other)
    _ = try verifier.verifyAssignment(signedAssignment:signed,artifact:artifact,channel:"beta",installation:"a",lastSequence:8,now:f.now)
    do {
        _ = try verifier.verifyAssignment(signedAssignment:signed,artifact:artifact,channel:"beta",installation:"a",lastSequence:8,now:f.now+5)
        Issue.record("assignment skipped artifact authority expiry")
    } catch let error as UpdateError { #expect(error.code == "v3.signature.authority") }
}

@Test func v3PrivateContextOwnsKeyBytesIndependentlyOfExternalNoCopyBuffer() throws {
    let f = try V3LocalFixture(), r = f.roots[0]
    let pointer = UnsafeMutableRawPointer.allocate(byteCount:32,alignment:1)
    defer { pointer.deallocate() }
    r.publicKey.withUnsafeBytes { source in pointer.copyMemory(from:source.baseAddress!,byteCount:32) }
    let external = Data(bytesNoCopy:pointer,count:32,deallocator:.none)
    let root = TrustRoot(keyID:r.keyID,publicKey:external,scope:r.scope,artifact:true,assignment:true,notBeforeUnix:1,notAfterUnix:20_000)
    let verifier = try f.verifier(roots:[root])
    pointer.initializeMemory(as:UInt8.self,repeating:0,count:32)
    #expect(root.publicKey == Data(repeating:0,count:32))
    _ = try f.artifact(verifier)
}

@Test func v3SignedAssignmentBindingReplayAndCohortAreIndependentChecks() throws {
    let f = try V3LocalFixture(), verifier = try f.verifier(), artifact = try f.artifact(verifier)
    let signed = try f.signed(f.assignment,assignment:true)
    for high in [UInt64(9),UInt64.max] {
        #expect(throws:UpdateError.self) { try verifier.verifyAssignment(signedAssignment:signed,artifact:artifact,channel:"beta",installation:"a",lastSequence:high,now:f.now) }
    }
    #expect(throws:UpdateError.self) { try verifier.verifyAssignment(signedAssignment:signed,artifact:artifact,channel:"other",installation:"a",lastSequence:8,now:f.now) }
    for (field,value) in ["schema":CanonicalValue.uint(2),"runtime":.text(String(repeating:"f",count:64)),"artifact_sha256":.text(String(repeating:"f",count:64)),"release_id":.text("other"),"rollout_basis_points":.uint(0),"extra":.uint(1)] {
        let bad = try v3Changed(f.assignment) { $0[field]=value }
        #expect(throws:(any Error).self) { try verifier.verifyAssignment(signedAssignment:f.signed(bad,assignment:true),artifact:artifact,channel:"beta",installation:"a",lastSequence:8,now:f.now) }
    }
}

@Test func v3ImmutableVerifierContextSupportsConcurrentValueCopies() async throws {
    let f = try V3LocalFixture(), verifier = try f.verifier(), manifest = try f.signed(f.manifest), payload = f.payload, now = f.now
    let successes = try await withThrowingTaskGroup(of:Int.self) { group in
        for _ in 0..<32 {
            group.addTask { let copy = verifier; return try copy.verifyArtifact(signedManifest:manifest,payload:payload,now:now).capabilityGrants.entries.count == 2 ? 1 : 0 }
        }
        var total = 0
        for try await value in group { total += value }
        return total
    }
    #expect(successes == 32)
}
