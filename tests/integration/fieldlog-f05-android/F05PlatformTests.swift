import Foundation
import Testing
@_spi(PrivateFieldLogEditor) @_spi(CapabilityDurableV3) import MixerUpdates

@Test func f05PrivatePlatformMatchesInstalledScope() throws {
    let packet = URL(fileURLWithPath: try #require(ProcessInfo.processInfo.environment["F05_FIXTURE_PACKET"]))
    func read(_ file: String) throws -> Data {
        try Data(contentsOf: packet.appendingPathComponent(file))
    }
    let roots = try JSONDecoder().decode([TrustRoot].self, from: read("roots.json"))
    let scope = FieldLogEditorDevelopment.scope
    #expect(scope.platform == "android")
    let manifest = try read("manifest.json")
    let assignment = try read("assignment.json")
    let payload = try read("editor.wasm")
    let metadata = try #require(JSONDecoder().decode(CanonicalValue.self, from: manifest).object?["manifest"]?.object)
    let runtime = try #require(metadata["runtime"]?.text)
    let limits = ResourceLimits(memoryBytes: 4_194_304, fuel: 1_000_000, startupMilliseconds: 5_000)
    func host(_ scope: UpdateScope) -> InstalledRuntime {
        InstalledRuntime(scope: scope, runtime: runtime, protocolVersion: 3, guestABI: 2, uiSchema: 1,
                         capabilityHashes: ["storage.keyValue.v1": "4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"],
                         stateVersion: 0, maxPayloadBytes: 4_194_304, limits: limits)
    }
    let cutoff = try #require(roots.first?.notAfterUnix)
    let now = cutoff - 6 * 24 * 60 * 60
    let verifier = try ReleaseVerifierV3(privateDevelopmentFieldLogEditor: host(scope), roots: roots)
    let artifact = try verifier.verifyArtifact(signedManifest: manifest, payload: payload, now: now)
    let accepted = try verifier.verifyAssignment(signedAssignment: assignment, artifact: artifact, channel: "beta",
                                                 installation: "fieldlog-f05-android", lastSequence: 0, now: now)
    let offered = try verifier._authorizeOfferV3(exactManifest: manifest, exactAssignment: assignment, channel: "beta",
                                                 installation: "fieldlog-f05-android", lastSequence: 0, now: now)
    let retained = try verifier._verifyRetainedHealthySnapshotV3(exactManifest: manifest, exactAssignment: assignment,
        payload: payload, channel: "beta", installation: "fieldlog-f05-android", storedSequence: 1, acceptedSequence: 1)
    #expect(accepted.sequence == 1 && offered.sequence == 1 && retained.sequence == 1)
    #expect(artifact.artifactSHA256 == offered.artifactSHA256 && artifact.artifactSHA256 == retained.artifactSHA256)
    #expect(artifact.capabilityGrants.entries.count == 1)
    #expect(artifact.capabilityGrants.entries.first?.namespaces == ["fieldlog_editor"])
    let otherScopes = [
        UpdateScope(organization: "other-org", project: scope.project, app: scope.app, environment: scope.environment, platform: scope.platform),
        UpdateScope(organization: scope.organization, project: "other-project", app: scope.app, environment: scope.environment, platform: scope.platform),
        UpdateScope(organization: scope.organization, project: scope.project, app: "other-app", environment: scope.environment, platform: scope.platform),
        UpdateScope(organization: scope.organization, project: scope.project, app: scope.app, environment: "production", platform: scope.platform),
        UpdateScope(organization: scope.organization, project: scope.project, app: scope.app, environment: scope.environment, platform: "ios"),
    ]
    for other in otherScopes {
        #expect(throws: UpdateError.self) {
            _ = try ReleaseVerifierV3(privateDevelopmentFieldLogEditor: host(other), roots: roots)
        }
        let mismatchedRoots = roots.map { root in
            TrustRoot(keyID: root.keyID, publicKey: root.publicKey, scope: other, artifact: root.artifact,
                assignment: root.assignment, revoked: root.revoked, notBeforeUnix: root.notBeforeUnix, notAfterUnix: root.notAfterUnix)
        }
        #expect(throws: UpdateError.self) {
            _ = try ReleaseVerifierV3(privateDevelopmentFieldLogEditor: host(scope), roots: mismatchedRoots)
        }
    }
}
