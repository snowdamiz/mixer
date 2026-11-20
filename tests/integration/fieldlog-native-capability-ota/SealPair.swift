import CryptoKit
import Foundation
@_spi(CapabilityDurableV3) import MixerUpdates
import MixerRuntimeIdentity

@main struct SealPair {
    static func main() throws {
        let args = CommandLine.arguments
        guard args.count == 5 || args.count == 6 else {
            throw failure("Expected packet, manifest template, successor Wasm, source revision and optional baseline Wasm")
        }
        let packet = URL(fileURLWithPath: args[1], isDirectory: true)
        let template = try object(Data(contentsOf: URL(fileURLWithPath: args[2])))
        let payload = try Data(contentsOf: URL(fileURLWithPath: args[3]))
        let baseline = args.count == 6 ? try Data(contentsOf: URL(fileURLWithPath: args[5])) : payload
        guard args.count == 5 || baseline != payload else { throw failure("Expected distinct compiled guests") }
        let identity = try ["old", "successor"].map {
            try CapabilityRuntimeIdentity(json: read(packet.appendingPathComponent($0), "identity-input.json"))
        }
        let scope = identity[0].installedRuntime.scope
        guard scope == identity[1].installedRuntime.scope, scope.platform == "android", scope.environment == "development",
              let storage = identity[0].installedRuntime.capabilityHashes["storage.keyValue.v1"],
              let https = identity[1].installedRuntime.capabilityHashes["network.http.v1"],
              identity[0].installedRuntime.capabilityHashes == ["storage.keyValue.v1": storage],
              identity[1].installedRuntime.capabilityHashes == ["storage.keyValue.v1": storage, "network.http.v1": https],
              template["scope"] == (try StrictJSON.decode(CanonicalValue.self, from: encoder.encode(scope)))
        else { throw failure("Unexpected Android identity or manifest scope") }

        let secret = Curve25519.Signing.PrivateKey()
        let key = "fieldlog-android-native-https-local"
        let roots = [TrustRoot(keyID: key, publicKey: secret.publicKey.rawRepresentation,
            scope: scope, artifact: true, assignment: true, notBeforeUnix: 1)]
        let rootBytes = try encoder.encode(roots)
        let verifiers = try zip(["old", "successor"], identity).map { label, input in
            let directory = packet.appendingPathComponent(label)
            let installed = directory.appendingPathComponent("Installed")
            guard var descriptor = input.descriptor.object, var build = descriptor["build"]?.object else {
                throw failure("Missing native build")
            }
            build["trust_roots_sha256"] = .text(ReleaseVerifier.sha256(rootBytes))
            descriptor["build"] = .object(build)
            let bytes = try encoder.encode(CanonicalValue.object(descriptor))
            let host = try CapabilityRuntimeIdentity(json: bytes).installedRuntime
            try write(rootBytes, installed, "roots.json")
            try write(bytes, installed, "identity.json")
            try write(encoder.encode(host), directory, "host.json")
            return try ReleaseVerifierV3(host: host, roots: roots)
        }

        let (old, successor) = (verifiers[0], verifiers[1])
        let now = UInt64(Date().timeIntervalSince1970)
        let installation = "1f0d30b5-6e05-4e49-b928-a40bc95cb7ce"
        let signedScope = try StrictJSON.decode(CanonicalValue.self, from: encoder.encode(scope))
        struct Offer {
            let manifest: Data
            let assignment: Data
            let payload: Data
        }
        func issue(_ label: String, host: InstalledRuntime, withHTTPS: Bool, sequence: UInt64) throws -> Offer {
            let guest = withHTTPS ? payload : baseline
            let materials = packet.appendingPathComponent(withHTTPS ? "successor" : "old").appendingPathComponent("Installed")
            let names = withHTTPS ? ["http-grant.json", "storage-grant.json"] : ["storage-grant.json"]
            let grants = try names.map { try StrictJSON.decode(CanonicalValue.self, from: read(materials, $0)) }
            guard var grantSet = template["capability_grants"]?.object else { throw failure("Missing grant schema") }
            grantSet["entries"] = .array(grants)
            var body = template
            body["capability_grants"] = .object(grantSet)
            body["capability_hashes"] = .object((withHTTPS ? successor.host : old.host).capabilityHashes.mapValues(CanonicalValue.text))
            body["release_id"] = .text("fieldlog-calculation-" + label)
            body["source_commit"] = .text(args[4])
            body["provenance_id"] = .text("fieldlog-local-native-https-" + host.runtime.prefix(24))
            body["runtime"] = .text(host.runtime)
            body["payload_sha256"] = .text(ReleaseVerifier.sha256(guest))
            body["compressed_bytes"] = .uint(UInt64(guest.count))
            body["expanded_bytes"] = .uint(UInt64(guest.count))
            body["key_id"] = .text(key)
            body["created_at_unix"] = .uint(now)
            let manifest = CanonicalValue.object(body)
            let digest = ReleaseVerifier.sha256(try manifest.canonicalCBOR())
            let assignment = CanonicalValue.object([
                "schema": .uint(3), "scope": signedScope, "channel": .text("beta"), "cohort": .text("sha256-v1"),
                "rollout_basis_points": .uint(10000), "sequence": .uint(sequence), "release_id": body["release_id"]!,
                "artifact_sha256": .text(digest), "runtime": .text(host.runtime), "key_id": .text(key), "created_at_unix": .uint(now),
            ])
            let offer = try Offer(manifest: sign(manifest, key: secret, field: "manifest", domain: "artifact"),
                                  assignment: sign(assignment, key: secret, field: "assignment", domain: "assignment"),
                                  payload: guest)
            let directory = packet.appendingPathComponent(label)
            try write(offer.manifest, directory, "manifest.json")
            try write(offer.assignment, directory, "assignment.json")
            return offer
        }

        func verify(_ verifier: ReleaseVerifierV3, _ offer: Offer, after: UInt64) throws -> VerifiedAssignmentV3 {
            let artifact = try verifier.verifyArtifact(signedManifest: offer.manifest, payload: offer.payload, now: now)
            return try verifier.verifyAssignment(signedAssignment: offer.assignment, artifact: artifact,
                channel: "beta", installation: installation, lastSequence: after, now: now)
        }
        let retained = try issue("old", host: old.host, withHTTPS: false, sequence: 2)
        let candidate = try issue("successor", host: successor.host, withHTTPS: true, sequence: 3)
        let incompatible = try issue("refused", host: old.host, withHTTPS: true, sequence: 3)
        let first = try verify(old, retained, after: 1)
        let second = try verify(successor, candidate, after: 0)
        guard old.host.runtime != successor.host.runtime, first.sequence == 2, second.sequence == 3,
              first.cohortBucket == second.cohortBucket else { throw failure("Runtime, sequence or cohort drift") }

        for (host, offer) in [(old, incompatible), (old, candidate), (successor, retained)] {
            do {
                _ = try verify(host, offer, after: 0)
                throw failure("A foreign capability map or runtime was accepted")
            } catch let error as UpdateError where error.code == "v3.manifest.compatibility" {}
        }
        let artifact = try old.verifyArtifact(signedManifest: retained.manifest, payload: retained.payload, now: now)
        do {
            _ = try old.verifyAssignment(signedAssignment: candidate.assignment, artifact: artifact,
                channel: "beta", installation: installation, lastSequence: 2, now: now)
            throw failure("A foreign assignment was accepted")
        } catch let error as UpdateError where error.code == "v3.assignment.binding" {}
        let report = ["installation": installation, "bucket": String(first.cohortBucket),
                      "manifestRefusal": "v3.manifest.compatibility", "assignmentRefusal": "v3.assignment.binding"]
        try write(encoder.encode(report), packet, "verifier.json")
    }

    private static var encoder: JSONEncoder {
        let value = JSONEncoder()
        value.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return value
    }

    private static func sign(_ body: CanonicalValue, key: Curve25519.Signing.PrivateKey,
                             field: String, domain: String) throws -> Data {
        let signature = try key.signature(for: Data("mixer.\(domain).v3\0".utf8) + body.canonicalCBOR())
        return try encoder.encode(CanonicalValue.object([field: body, "signature": .text(signature.base64EncodedString())]))
    }

    private static func object(_ bytes: Data) throws -> [String: CanonicalValue] {
        guard let value = try StrictJSON.decode(CanonicalValue.self, from: bytes).object else {
            throw failure("Expected a JSON object")
        }
        return value
    }

    private static func read(_ directory: URL, _ name: String) throws -> Data {
        try Data(contentsOf: directory.appendingPathComponent(name))
    }

    private static func write(_ data: Data, _ directory: URL, _ name: String) throws {
        try data.write(to: directory.appendingPathComponent(name), options: .withoutOverwriting)
    }

    private static func failure(_ message: String) -> UpdateError {
        UpdateError("fieldlog.nativeHTTPS.fixture", message)
    }
}
