import Foundation
import MixerUpdates
import MixerRuntimeIdentity

@main struct VerifyDelivery {
    static func main() throws {
        guard CommandLine.arguments.count == 6 else {
            throw UpdateError("fieldlog.arguments", "Expected delivery, prior identity, prior root pin, former development roots and fresh host installation")
        }
        let delivery = URL(fileURLWithPath: CommandLine.arguments[1])
        func read(_ name: String) throws -> Data {
            try Data(contentsOf: delivery.appendingPathComponent(name))
        }
        let installed = try CapabilityRuntimeIdentity(json: read("Installed/identity.json")).installedRuntime
        let prior = try CapabilityRuntimeIdentity(
            json: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[2]))).installedRuntime
        let hostBytes = try read("host.json")
        let host = try StrictJSON.decode(InstalledRuntime.self, from: hostBytes)
        let rootBytes = try read("Installed/roots.json")
        let roots = try StrictJSON.decode([TrustRoot].self, from: rootBytes)
        let oldRoots = try StrictJSON.decode([TrustRoot].self, from: Data(contentsOf:
            URL(fileURLWithPath: CommandLine.arguments[4])))
        guard roots.count == 1, installed.runtime != prior.runtime, host.runtime == installed.runtime,
              host.scope == installed.scope, ReleaseVerifier.sha256(rootBytes) != CommandLine.arguments[3]
        else { throw UpdateError("fieldlog.freshness", "Delivery runtime or trust did not rotate") }

        let verifier = try ReleaseVerifierV3(host: installed, roots: roots)
        let oldVerifier = try ReleaseVerifierV3(host: prior, roots: roots)
        let oldKeyVerifier = try ReleaseVerifierV3(host: installed, roots: oldRoots)
        let foreignScope = UpdateScope(organization: installed.scope.organization, project: "foreign-fixture",
            app: installed.scope.app, environment: installed.scope.environment, platform: installed.scope.platform)
        let foreignRoots = roots.map {
            TrustRoot(keyID: $0.keyID, publicKey: $0.publicKey, scope: foreignScope,
                artifact: $0.artifact, assignment: $0.assignment, notBeforeUnix: $0.notBeforeUnix)
        }
        let foreignVerifier = try ReleaseVerifierV3(host: installed, roots: foreignRoots)
        let utc = UInt64(Date().timeIntervalSince1970)
        let installation = CommandLine.arguments[5]
        guard UUID(uuidString: installation)?.uuidString.lowercased() == installation else {
            throw UpdateError("fieldlog.installation", "Expected a canonical host replay installation UUID")
        }
        let variants = ["baseline", "optional", "baseline", "optional"]
        var artifactDigests = [String]()
        for (index, variant) in variants.enumerated() {
            let sequence = UInt64(index + 1)
            let manifest = try read("\(variant).manifest.json")
            let payload = try read("\(variant).wasm")
            let assignment = try read("sequence-\(sequence).assignment.json")
            let artifact = try verifier.verifyArtifact(signedManifest: manifest, payload: payload, now: utc)
            var altered = payload
            altered[altered.startIndex] ^= 1
            try expectDenial("v3.payload.integrity") {
                _ = try verifier.verifyArtifact(signedManifest: manifest, payload: altered, now: utc)
            }
            let offer = try verifier.verifyAssignment(signedAssignment: assignment, artifact: artifact,
                channel: "beta", installation: installation, lastSequence: sequence - 1, now: utc)
            guard offer.sequence == sequence else {
                throw UpdateError("fieldlog.sequence", "Assignment decoded with unexpected sequence")
            }
            try expectDenial("v3.assignment.replay") {
                _ = try verifier.verifyAssignment(signedAssignment: assignment, artifact: artifact,
                    channel: "beta", installation: installation, lastSequence: sequence, now: utc)
            }
            try expectDenial("v3.manifest.compatibility") {
                _ = try oldVerifier.verifyArtifact(signedManifest: manifest, payload: payload, now: utc)
            }
            try expectDenial("v3.assignment.binding") {
                _ = try verifier.verifyAssignment(signedAssignment: assignment, artifact: artifact,
                    channel: "other-fixture", installation: installation, lastSequence: sequence - 1, now: utc)
            }
            try expectDenial("v3.signature.authority") {
                _ = try foreignVerifier.verifyArtifact(signedManifest: manifest, payload: payload, now: utc)
            }
            try expectDenial("v3.signature.invalid") {
                _ = try oldKeyVerifier.verifyArtifact(signedManifest: manifest, payload: payload, now: utc)
            }
            artifactDigests.append(artifact.artifactSHA256)
            print("\(sequence) \(variant) \(artifact.artifactSHA256)")
        }
        guard artifactDigests[0] == artifactDigests[2], artifactDigests[1] == artifactDigests[3],
              artifactDigests[0] != artifactDigests[1] else {
            throw UpdateError("fieldlog.rollback", "Wrong baseline and optional digests")
        }
        print("PASS four v3 assignments, previous runtime and stale sequence rejected at \(utc)")
    }

    static func expectDenial(_ expected: String, _ operation: () throws -> Void) throws {
        do {
            try operation()
        } catch let error as UpdateError where error.code == expected {
            return
        }
        throw UpdateError("fieldlog.expected-denial", "Expected \(expected)")
    }
}
