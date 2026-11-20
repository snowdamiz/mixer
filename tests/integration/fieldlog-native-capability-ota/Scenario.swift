#if os(macOS) && canImport(MixerApple)
import MixerCapabilities
import MixerRuntimeIdentity

extension FieldLogCompletionTests {
    private typealias Fixture = FieldLogReleaseV3Fixture

    @MainActor
    func testOnlineNativeCapability() async throws {
        let run = try runDirectory()
        let directory = run.appendingPathComponent("online")
        let workspaceDirectory = directory.appendingPathComponent("workspace")
        let disk = workspaceDirectory.appendingPathComponent("workspace.json")
        let seed = try WorkspaceRepository(directory: workspaceDirectory)
        _ = try await RowStorage.seedCompletion(seed)
        await seed.close()
        let bytes = try Data(contentsOf: disk)
        try bytes.write(to: directory.appendingPathComponent("seed-workspace.json"))
        let repository = try WorkspaceRepository(directory: workspaceDirectory)
        let workspace = await repository.snapshot()
        let storage = RowStorage(repository)
        let env = ProcessInfo.processInfo.environment
        let old = try Fixture(run: run, storage: storage, archiveSHA256: XCTUnwrap(env["FIELDLOG_ROW_VM"]))
        let new = try newInstallation(old, directory: directory, storage: storage)
        let newHost = new.installed.identity.installedRuntime
        let key = try XCTUnwrap(old.signingKey)
        let installedRelease = old.reviewed
        let installedAssignment = old.assignments[1]
        let source = try XCTUnwrap(installedRelease.signedManifest.object?["manifest"]?.object)
        var manifest = source
        manifest["release_id"] = .text("fieldlog-completion-native-https")
        manifest["capability_hashes"] = .object(newHost.capabilityHashes.mapValues(CanonicalValue.text))
        var grants = try XCTUnwrap(manifest["capability_grants"]?.object)
        guard case let .array(entries) = grants["entries"] else { throw RowFailure("Missing calculation grants") }
        let httpGrant = try XCTUnwrap(new.installed.files["grant:" + CapabilitySchemas.httpID])
        let http = try StrictJSON.decode(CanonicalValue.self, from: httpGrant)
        grants["entries"] = .array([http] + entries)
        manifest["capability_grants"] = .object(grants)
        let initial = try XCTUnwrap(installedAssignment.object?["assignment"]?.object)
        let installedSequence = try XCTUnwrap(initial["sequence"]?.uint)
        let attemptedSequence = installedSequence + 1
        var assignment = initial
        assignment["sequence"] = .uint(attemptedSequence)
        assignment["release_id"] = manifest["release_id"]

        func signOffer(runtime: String) throws -> (digest: String, manifest: CanonicalValue, assignment: CanonicalValue) {
            var header = manifest
            header["runtime"] = .text(runtime)
            let value = CanonicalValue.object(header)
            let digest = ReleaseVerifier.sha256(try value.canonicalCBOR())
            var target = assignment
            target["runtime"] = .text(runtime)
            target["artifact_sha256"] = .text(digest)
            return (digest, try Fixture.sign(value, field: "manifest", domain: "artifact", key: key),
                    try Fixture.sign(.object(target), field: "assignment", domain: "assignment", key: key))
        }

        let refused = try signOffer(runtime: old.host.runtime)
        let compatible = try signOffer(runtime: newHost.runtime)
        let port = try XCTUnwrap(env["FIELDLOG_ROW_PORT"].flatMap(UInt16.init))
        let service = try ReleaseV3Loopback(executable: run.appendingPathComponent("mixer-service"), port: port,
            directory: directory, host: old.host, roots: old.execution.installed.rootsBytes,
            name: "service", actor: "fieldlog-test", additionalHosts: [newHost])

        func publish(digest: String, manifest: CanonicalValue, assignment: CanonicalValue, payload: Data,
                     name: String, uploadStatus: Int = 201) async throws -> Data {
            let response = try await service.request(service.project + "/artifacts/" + digest, status: uploadStatus,
                method: "PUT", body: .object(["signed_manifest": manifest, "payload": .text(payload.base64EncodedString())]),
                mutation: "upload-" + name)
            if uploadStatus == 201 {
                _ = try await service.request(service.project + "/releases/validate", status: 200, method: "POST",
                    body: .object(["artifact_sha256": .text(digest)]), mutation: "validate-" + name)
                _ = try await service.request(service.project + "/channels/beta/publish", status: 200, method: "POST",
                    body: .object(["signed_assignment": assignment]), mutation: "publish-" + name)
            }
            return response
        }

        func delivery(runtime: String, installation: String, digest: String, assignment: CanonicalValue)
        async throws -> (offer: Data, manifest: Data, assignment: Data, payload: Data) {
            let bytes = try await service.updates(installation: installation, runtime: runtime)
            let offer = try StrictJSON.decode(CanonicalValue.self, from: bytes)
            let scope = old.host.scope
            let expected = "/v3/artifacts/\(digest)?organization=\(scope.organization)&project=\(scope.project)"
            try require(offer.object?["artifact_url"]?.text == expected && offer.object?["signed_assignment"] == assignment,
                        "Delivery selected the wrong signed offer for \(runtime)")
            let artifact = try StrictJSON.decode(CanonicalValue.self, from: await service.request(expected, status: 200))
            return (bytes, try Fixture.encoder.encode(XCTUnwrap(artifact.object?["signed_manifest"])),
                    try Fixture.encoder.encode(assignment),
                    try XCTUnwrap(Data(base64Encoded: XCTUnwrap(artifact.object?["payload"]?.text))))
        }

        let result: Result<[String: Any], Error>
        do {
            let native = try nativeObservation(workspace)
            try await service.waitUntilReady()
            _ = try await publish(digest: installedRelease.digest, manifest: installedRelease.signedManifest,
                                  assignment: installedAssignment, payload: installedRelease.payload, name: "installed")
            _ = try await service.updates(installation: "fieldlog-native-https", status: 204, runtime: newHost.runtime)
            let baseline = try await delivery(runtime: old.host.runtime, installation: old.configuration.installation,
                                              digest: installedRelease.digest, assignment: installedAssignment)
            let healthy = try await withOwner(old) { owner in
                try await owner.beginDownload(signedManifest: baseline.manifest, signedAssignment: baseline.assignment)
                try await owner.appendDownload(baseline.payload, atOffset: 0)
                try await owner.finishDownload()
                let staged = await owner.recoverySnapshot()
                let candidate = try XCTUnwrap(staged.staged)
                return try await observe(owner, candidate: candidate, previous: nil, workspace: workspace,
                                         expected: native.maps, stage: "installed")
            }
            let candidate = try XCTUnwrap(healthy["candidate"] as? String)
            let stateURL = old.configuration.directory.appendingPathComponent("state.json")
            let before = try Data(contentsOf: stateURL)

            let error = try await publish(digest: refused.digest, manifest: refused.manifest, assignment: refused.assignment,
                                          payload: installedRelease.payload, name: "old-native-https", uploadStatus: 422)
            let detail = try XCTUnwrap(Fixture.object(error)["error"] as? [String: String])
            try require(detail["code"] == "artifact_invalid" && detail["message"] == "v3 host contract mismatch",
                        "The proposed OTA was refused for an unexpected reason")

            _ = try await publish(digest: compatible.digest, manifest: compatible.manifest, assignment: compatible.assignment,
                                  payload: installedRelease.payload, name: "new-native-https")
            let newDelivery = try await delivery(runtime: newHost.runtime, installation: "fieldlog-native-https",
                                                 digest: compatible.digest, assignment: compatible.assignment)
            let now = UInt64(Date().timeIntervalSince1970)
            let verified = try new.installed.verifier.verifyArtifact(signedManifest: newDelivery.manifest,
                                                                     payload: newDelivery.payload, now: now)
            let assigned = try new.installed.verifier.verifyAssignment(signedAssignment: newDelivery.assignment,
                artifact: verified, channel: "beta", installation: "fieldlog-native-https", lastSequence: 0, now: now)
            let policy = try CapabilityExecutionPolicy(installed: new.installed, artifact: verified, payload: newDelivery.payload, now: now)
            try require(assigned.sequence == attemptedSequence && newDelivery.payload == baseline.payload &&
                        policy.http?.methods == ["GET", "PUT"] &&
                        policy.http?.origins == ["https://a.example", "https://b.example:8443"],
                        "The new runtime did not verify the offer and admit the installed HTTPS adapter")

            let after = try await delivery(runtime: old.host.runtime, installation: old.configuration.installation,
                                          digest: installedRelease.digest, assignment: installedAssignment)
            try require(after.offer == baseline.offer && after.manifest == baseline.manifest && after.payload == baseline.payload,
                        "Old runtime delivery changed after the attempt and new-runtime publication")
            let retained = try await withOwner(old) { owner in
                let rejectedManifest = try Fixture.encoder.encode(refused.manifest)
                let rejectedAssignment = try Fixture.encoder.encode(refused.assignment)
                for (manifest, assignment) in [(rejectedManifest, rejectedAssignment), (newDelivery.manifest, newDelivery.assignment)] {
                    do {
                        try await owner.beginDownload(signedManifest: manifest, signedAssignment: assignment)
                        throw RowFailure("The old host accepted a native HTTPS candidate")
                    } catch let failure as UpdateError {
                        try require(failure.code == "v3.manifest.compatibility", "Unexpected client refusal \(failure.code)")
                    }
                }
                let snapshot = await owner.recoverySnapshot()
                try require(snapshot.acceptedSequence == installedSequence && snapshot.healthy == candidate &&
                            snapshot.downloading == nil && snapshot.staged == nil && (try Data(contentsOf: stateURL)) == before,
                            "Refusals changed the old host recovery state")
                return try await observe(owner, candidate: candidate, previous: nil, workspace: workspace,
                                         expected: native.maps, stage: "retained")
            }
            try checkNativeCapabilityState(old, candidate: candidate, sequence: installedSequence,
                                           artifact: installedRelease.digest, payload: baseline.payload)
            try await checkStorage(storage, expectedReads: 2)
            try require(try Data(contentsOf: disk) == bytes, "The old installation's workspace bytes changed")
            try require(await repository.snapshot() == workspace, "The old installation's workspace changed")
            result = .success([
                "pid": Int(getpid()), "runtime": old.host.runtime, "workspace": dataset(workspace, bytes: bytes),
                "native": native.scopes, "baseline": healthy, "retained": retained, "oldArtifact": installedRelease.digest,
                "oldPayload": ReleaseVerifier.sha256(baseline.payload), "oldSequence": installedSequence, "oldOfferUnchanged": true,
                "refusedArtifact": refused.digest, "oldOTAAttemptSequence": attemptedSequence, "uploadHTTP": 422, "uploadError": detail,
                "clientRefusals": ["oldRuntimeNewCapabilityMap": "v3.manifest.compatibility",
                                   "newRuntime": "v3.manifest.compatibility"], "recoveryBytesUnchangedOnRefusal": true,
                "newRuntime": newHost.runtime, "newArtifact": compatible.digest, "newSequence": assigned.sequence,
                "newPayload": ReleaseVerifier.sha256(newDelivery.payload),
                "oldCapabilities": old.host.capabilityHashes, "newCapabilities": newHost.capabilityHashes,
                "newHTTPSAdapterAdmitted": true,
            ])
        } catch { result = .failure(error) }
        await repository.close()
        try await service.stop()
        try Fixture.json(result.get()).write(to: directory.appendingPathComponent("outcome.json"))
    }

    @MainActor
    func testOfflineNativeCapability() async throws {
        let run = try runDirectory()
        let directory = run.appendingPathComponent("online")
        let online = try Fixture.object(Fixture.read(directory, "outcome.json"))
        let baseline = try XCTUnwrap(online["baseline"] as? [String: Any])
        let candidate = try XCTUnwrap(baseline["candidate"] as? String)
        let sequence = try XCTUnwrap((online["oldSequence"] as? NSNumber)?.uint64Value)
        let artifact = try XCTUnwrap(online["oldArtifact"] as? String)
        let retained = try XCTUnwrap(online["retained"] as? [String: Any])
        let workspaceDirectory = directory.appendingPathComponent("workspace")
        let expected = try Fixture.read(directory, "seed-workspace.json")
        let repository = try WorkspaceRepository(directory: workspaceDirectory)
        let storage = RowStorage(repository)
        let result: Result<[String: Any], Error>
        do {
            let workspace = await repository.snapshot()
            let native = try nativeObservation(workspace)
            let old = try Fixture(run: run, storage: storage)
            let payload = try Fixture.read(run, "reviewed.wasm")
            try checkNativeCapabilityState(old, candidate: candidate, sequence: sequence, artifact: artifact, payload: payload)
            let observation = try await withOwner(old) { owner in
                try await observe(owner, candidate: candidate, previous: nil, workspace: workspace,
                                  expected: native.maps, stage: "offline")
            }
            try require(observation["launchID"] as? String != retained["launchID"] as? String,
                        "Cold boot did not launch a fresh attempt")
            try checkNativeCapabilityState(old, candidate: candidate, sequence: sequence, artifact: artifact, payload: payload)
            try await checkStorage(storage, expectedReads: 1)
            try require(try Data(contentsOf: workspaceDirectory.appendingPathComponent("workspace.json")) == expected,
                        "Cold reopen changed the workspace bytes")
            result = .success(["pid": Int(getpid()), "runtime": old.host.runtime, "workspace": dataset(workspace, bytes: expected),
                               "observation": observation, "sequence": sequence])
        } catch { result = .failure(error) }
        await repository.close()
        try Fixture.json(result.get()).write(to: run.appendingPathComponent("offline/outcome.json"))
    }

    private func newInstallation(_ old: Fixture, directory: URL, storage: RowStorage) throws -> InstalledCapabilityExecution {
        let reference = try XCTUnwrap(Bundle.module.url(forResource: "Fixtures", withExtension: nil))
        let fixture = try Fixture.object(Fixture.read(reference, "identity.json"))
        let added = try XCTUnwrap((fixture["capabilities"] as? [[String: Any]])?.first { $0["id"] as? String == CapabilitySchemas.httpID })
        let bundle = directory.appendingPathComponent("public-fixtures")
        var updated = try Fixture.object(Fixture.read(bundle, "identity.json"))
        let capabilities = try XCTUnwrap(updated["capabilities"] as? [[String: Any]])
        try require(old.host.capabilityHashes.keys.sorted() == [CapabilitySchemas.storageID], "Old runtime already has HTTPS")
        updated["capabilities"] = [added] + capabilities
        let identity = try Fixture.json(updated)
        let runtime = try CapabilityRuntimeIdentity(json: identity).installedRuntime
        try require(runtime.runtime != old.host.runtime &&
                    runtime.capabilityHashes == old.host.capabilityHashes.merging([CapabilitySchemas.httpID: CapabilitySchemas.httpSHA256]) { first, _ in first },
                    "The added installed capability did not change the runtime fingerprint")
        let files = try Fixture.materials.map { name, role in
            CapabilityMaterialFile(role: role, bytes: try Fixture.read(name.hasPrefix("http") ? reference : bundle, name))
        }
        return try InstalledCapabilityExecution(identityJSON: identity, materials: files,
            trustRootsJSON: old.execution.installed.rootsBytes, privateContainer: directory,
            applicationStorage: .init(runtimeFingerprint: runtime.runtime, namespace: RowStorage.namespace,
                                      service: storage, allowsDeferredGuestUIStartup: true))
    }

    private func checkNativeCapabilityState(_ old: Fixture, candidate: String, sequence: UInt64,
                                            artifact: String, payload: Data) throws {
        let bytes = try Fixture.read(old.configuration.directory, "state.json")
        let state = try StrictJSON.decode(CapabilityRecoveryState.self, from: bytes)
        let record = try XCTUnwrap(state.candidates[candidate])
        try require(state.fingerprint == old.host.runtime && state.installation == old.configuration.installation &&
                    state.acceptedSequence == sequence && state.healthy?.candidateID == candidate &&
                    state.healthy?.completedMilestones == ["feature_started", "first_screen"] &&
                    record.sequence == sequence && record.artifactSHA256 == artifact &&
                    record.payloadSHA256 == ReleaseVerifier.sha256(payload) &&
                    state.pending == nil && state.staged == nil && state.attempt == nil,
                    "The old installation lost the committed signed candidate")
    }
}
#endif
