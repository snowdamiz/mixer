#if os(macOS) && canImport(MixerApple)
import FieldLogModels
import FieldLogStorage
import Foundation
import MixerUI
import MixerUpdates
import XCTest
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

final class FieldLogCompletionTests: XCTestCase {
    @MainActor
    func testOnline() async throws {
        let run = try runDirectory()
        let directory = run.appendingPathComponent("online")
        let store = directory.appendingPathComponent("workspace")
        let disk = store.appendingPathComponent("workspace.json")
        let seed = try WorkspaceRepository(directory: store)
        _ = try await RowStorage.seedCompletion(seed)
        await seed.close()
        let originalBytes = try Data(contentsOf: disk)
        try originalBytes.write(to: directory.appendingPathComponent("seed-workspace.json"), options: .withoutOverwriting)

        let repository = try WorkspaceRepository(directory: store)
        let workspace = await repository.snapshot()
        try require(try JSONDecoder().decode(Workspace.self, from: originalBytes) == workspace,
                    "Native repository did not reopen the committed fixture")
        let native = try nativeObservation(workspace)
        let storage = RowStorage(repository)
        let env = ProcessInfo.processInfo.environment
        let fixture = try FieldLogReleaseV3Fixture(run: run, storage: storage, archiveSHA256: XCTUnwrap(env["FIELDLOG_ROW_VM"]))
        let port = try XCTUnwrap(env["FIELDLOG_ROW_PORT"].flatMap(UInt16.init))
        let service = try FieldLogReleaseV3Loopback(executable: run.appendingPathComponent("mixer-service"),
                                                   port: port, directory: directory, fixture: fixture)
        let result: Result<[String: Any], Error>
        do {
            try await service.waitUntilReady()
            try await service.upload(fixture.baseline)
            try await service.upload(fixture.reviewed)

            var previous: String?
            var observations: [[String: Any]] = []
            for sequence in 1...3 {
                let release = sequence == 2 ? fixture.reviewed : fixture.baseline
                let expected = sequence == 2 ? native.maps : ["0%", "100%", "0%"]
                try await service.publish(sequence: sequence, operation: sequence == 3 ? "rollback" : "publish")
                let offer = try await service.fetch(release, sequence: sequence)
                let observation = try await withOwner(fixture) { owner in
                    try await owner.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment)
                    try await owner.appendDownload(offer.payload, atOffset: 0)
                    try await owner.finishDownload()
                    let staged = await owner.recoverySnapshot()
                    try require(staged.acceptedSequence == UInt64(sequence), "Wrong signed assignment high-water mark")
                    let candidate = try XCTUnwrap(staged.staged)
                    return try await observe(owner, candidate: candidate, previous: previous, workspace: workspace,
                                             expected: expected, stage: sequence == 1 ? "baseline" : sequence == 2 ? "fixed" : "rollback")
                }
                previous = observation["candidate"] as? String
                try require(try Data(contentsOf: disk) == originalBytes, "Release \(sequence) rewrote the workspace")
                try require(await repository.snapshot() == workspace, "Release \(sequence) mutated the workspace")
                observations.append(observation.merging([
                    "sequence": sequence, "releaseID": release.name, "artifactSHA256": release.digest,
                    "payloadSHA256": ReleaseVerifier.sha256(offer.payload),
                    "workspaceSHA256": ReleaseVerifier.sha256(originalBytes),
                ]) { _, new in new })
            }
            let candidates = try observations.map { try XCTUnwrap($0["candidate"] as? String) }
            try require(Set(candidates).count == 3, "Signed assignments did not get separate candidate identities")
            try require(native.maps[0] != (observations[0]["guest"] as? [String])?.first,
                        "The saved mixed project did not discriminate the bug")
            try await checkStorage(storage, expectedReads: 3)
            try checkRecovery(fixture, rollback: candidates[2], previous: candidates[1])
            result = .success([
                "pid": Int(getpid()), "runtime": fixture.host.runtime, "workspace": dataset(workspace, bytes: originalBytes),
                "native": native.scopes, "observations": observations, "ownersRetired": 3, "workspaceReads": 3,
            ])
        } catch { result = .failure(error) }
        await repository.close()
        do { try await service.stop() }
        catch { throw RowFailure("Service did not close: \(error); scenario: \(result)") }
        try FieldLogReleaseV3Fixture.json(result.get()).write(to: directory.appendingPathComponent("outcome.json"))
    }

    @MainActor
    func testOffline() async throws {
        let run = try runDirectory()
        let directory = run.appendingPathComponent("online")
        let online = try FieldLogReleaseV3Fixture.object(FieldLogReleaseV3Fixture.read(directory, "outcome.json"))
        try require(online["pid"] as? Int != Int(getpid()), "Cold reopen ran in the online process")
        let observations = try XCTUnwrap(online["observations"] as? [[String: Any]])
        let previous = try XCTUnwrap(observations[1]["candidate"] as? String)
        let rollback = try XCTUnwrap(observations[2]["candidate"] as? String)
        let expectedBytes = try FieldLogReleaseV3Fixture.read(directory, "seed-workspace.json")
        let original = try JSONDecoder().decode(Workspace.self, from: expectedBytes)
        let store = directory.appendingPathComponent("workspace")
        let disk = store.appendingPathComponent("workspace.json")
        let repository = try WorkspaceRepository(directory: store)
        let storage = RowStorage(repository)
        let result: Result<[String: Any], Error>
        do {
            let reopened = await repository.snapshot()
            try require(reopened == original && (try Data(contentsOf: disk)) == expectedBytes,
                        "Cold repository did not reopen exact seeded bytes and state")
            let fixture = try FieldLogReleaseV3Fixture(run: run, storage: storage)
            try checkRecovery(fixture, rollback: rollback, previous: previous)
            let bundle = directory.appendingPathComponent("public-fixtures")
            let updateManifest = try FieldLogReleaseV3Fixture.read(bundle, "reviewed.manifest.json")
            let updateAssignment = try FieldLogReleaseV3Fixture.read(bundle, "sequence-2.assignment.json")
            let observation = try await withOwner(fixture) { owner in
                do {
                    try await owner.beginDownload(signedManifest: updateManifest, signedAssignment: updateAssignment)
                    throw RowFailure("The prior signed update was accepted after rollback")
                } catch let error as UpdateError {
                    try require(error.code == "v3.assignment.replay", "Wrong rejection for older signed update")
                }
                return try await observe(owner, candidate: rollback, previous: previous, workspace: reopened,
                                         expected: ["0%", "100%", "0%"], stage: "offline")
            }
            try checkRecovery(fixture, rollback: rollback, previous: previous)
            try require(try Data(contentsOf: disk) == expectedBytes, "Offline guest startup rewrote the workspace")
            try require(await repository.snapshot() == original, "Offline guest startup mutated the workspace")
            try await checkStorage(storage, expectedReads: 1)
            result = .success([
                "pid": Int(getpid()), "runtime": fixture.host.runtime, "workspace": dataset(reopened, bytes: expectedBytes),
                "native": try nativeObservation(reopened).scopes,
                "observation": observation, "sequence": 3, "ownerRetired": true,
                "signedAssignmentReplay": "v3.assignment.replay", "workspaceReads": 1,
            ])
        } catch { result = .failure(error) }
        await repository.close()
        try FieldLogReleaseV3Fixture.json(result.get()).write(to: run.appendingPathComponent("offline/outcome.json"))
    }

    private func nativeObservation(_ workspace: Workspace) throws -> (scopes: [[String: Any]], maps: [String]) {
        let scopes = RowStorage.completionProjects.map { id -> [String: Any] in
            let tasks = workspace.tasks(for: id)
            let fraction = workspace.progress(for: id) // Used directly by ordinary FieldLog's ProjectDetail.
            return ["projectID": id.uuidString, "projectTitle": workspace.projects.first { $0.id == id }?.title ?? "",
                    "completed": tasks.filter(\.completed).count, "total": tasks.count, "fraction": fraction,
                    "wholePercent": Int(fraction * 100)]
        }
        let percents = try scopes.map { try XCTUnwrap($0["wholePercent"] as? Int) }
        try require(percents == [33, 100, 0] && scopes.compactMap { $0["total"] as? Int } == [3, 2, 0] &&
                    scopes.compactMap { $0["completed"] as? Int } == [1, 2, 0],
                    "The ordinary FieldLog oracle did not see the saved mixed, all-completed and empty projects")
        return (scopes, percents.map { "\($0)%" })
    }

    private func dataset(_ state: Workspace, bytes: Data) -> [String: Any] {
        ["id": state.id.uuidString, "revision": state.revision, "bytes": bytes.count,
         "sha256": ReleaseVerifier.sha256(bytes), "openDraft": RowStorage.draft.uuidString,
         "outboxIDs": state.outbox.map { $0.id.uuidString },
         "taskIDsByProject": RowStorage.completionProjects.map { id in state.tasks(for: id).map { $0.id.uuidString } },
         "completionFlagsByProject": RowStorage.completionProjects.map { id in state.tasks(for: id).map(\.completed) }]
    }

    @MainActor
    private func checkStorage(_ storage: RowStorage, expectedReads: Int) async throws {
        let reads = await storage.reads
        let moves = await storage.moves
        try require(reads == expectedReads && moves.isEmpty, "Progress hydration was not read-only")
    }

    @MainActor
    private func withOwner<Value>(_ fixture: FieldLogReleaseV3Fixture,
                                  _ body: (CapabilityGuestUIRuntime) async throws -> Value) async throws -> Value {
        let slots = CapabilityAttemptReservation.occupiedSlots
        let owner = try await CapabilityGuestUIRuntime.open(configuration: fixture.configuration, execution: fixture.execution)
        let result: Result<Value, Error>
        do { result = .success(try await body(owner)) }
        catch { result = .failure(error) }
        await owner.close()
        try await eventually("Owned VM and presentation did not retire") { owner.ownerRetired }
        let state = await owner.recoverySnapshot()
        try require(state.closed && !state.activation.cleanupPending && !state.incompleteAttempt &&
                    CapabilityAttemptReservation.occupiedSlots == slots, "Owner resources remained after retirement")
        return try result.get()
    }

    @MainActor
    private func observe(_ owner: CapabilityGuestUIRuntime, candidate: String, previous: String?, workspace: Workspace,
                         expected: [String], stage: String) async throws -> [String: Any] {
        let model = owner.presentation
        let attachment = try XCTUnwrap(model.claimNativeAttachment())
        defer { model.detachNativeAttachment(attachment) }
        let started = try await owner.start()
        try require(started.phase == .provisionalGuest && started.candidateID == candidate,
                    "\(stage) did not launch the expected signed guest")
        do {
            try await eventually("\(stage) did not produce a first frame") { model.state == .displaying(revision: 1) }
        } catch {
            let activation = await owner.recoverySnapshot().activation
            print("FIELDLOG first frame", stage, "presentation", model.state, "phase", activation.phase,
                  "terminal", String(describing: activation.terminalCause),
                  "bridge", String(describing: activation.firstBridgeFailure),
                  "protocol", String(describing: activation.firstUIProtocolFailure))
            throw error
        }
        let document = try XCTUnwrap(model.renderHost?.snapshot.document)
        let counts = document.root.children.filter { $0.id.hasPrefix("completion-") }
        try require(counts.map(\.id) == ["completion-0", "completion-1", "completion-2"] &&
                    counts.allSatisfy { $0.kind == .text }, "Guest document lost completion scope identities")
        let actual = try counts.map { try XCTUnwrap($0.properties["text"]?.string) }
        try require(actual == expected, "\(stage) displayed \(actual), expected \(expected)")
        let rows = document.root.children.filter { $0.id.hasPrefix("row-") }
        let saved = workspace.tasks(for: RowStorage.project)
        try require(rows.map(\.id) == saved.map { "row-" + $0.id.uuidString } &&
                    rows.compactMap { $0.children.first?.properties["text"]?.string } == saved.map(\.title),
                    "Saved task IDs, order or titles were lost during feature rendering")
        let beforeWitness = await owner.recoverySnapshot()
        if stage != "offline" {
            try require(beforeWitness.healthy != candidate, "A new candidate earned health before the display witness")
        }
        let ticket = try XCTUnwrap(model.nativeDisplayTicket(attachment: attachment))
        try require(model.observeNativeDisplay(ticket), "The host display witness was refused")
        try await eventually("\(stage) guest did not become healthy") {
            let health = await owner.recoverySnapshot()
            return health.activation.phase == .healthyGuest && health.healthy == candidate
        }
        let state = await owner.recoverySnapshot()
        try require(state.previousHealthy == previous, "The previous healthy candidate did not match")
        print("FIELDLOG COMPLETION \(stage) candidate=\(candidate) guest=\(actual)")
        return ["stage": stage, "candidate": candidate, "launchID": try XCTUnwrap(started.launchID),
                "guest": actual, "documentRevision": document.revision, "healthy": true]
    }

    private func checkRecovery(_ fixture: FieldLogReleaseV3Fixture, rollback: String, previous: String) throws {
        let bytes = try FieldLogReleaseV3Fixture.read(fixture.configuration.directory, "state.json")
        let state = try StrictJSON.decode(CapabilityRecoveryState.self, from: bytes)
        try require(state.fingerprint == fixture.host.runtime && state.installation == fixture.configuration.installation &&
                    state.acceptedSequence == 3 && state.healthy?.candidateID == rollback &&
                    state.previousHealthy?.candidateID == previous &&
                    state.healthy?.completedMilestones == ["feature_started", "first_screen"] &&
                    state.attempt == nil && state.pending == nil && state.staged == nil,
                    "The durable rollback assignment did not recover cleanly")
    }

    private func runDirectory() throws -> URL {
        URL(fileURLWithPath: try XCTUnwrap(ProcessInfo.processInfo.environment["FIELDLOG_ROW_RUN"]), isDirectory: true)
    }

    @MainActor
    private func eventually(_ label: String, _ ready: () async -> Bool) async throws {
        let deadline = ContinuousClock.now + .seconds(7)
        while !(await ready()) {
            try require(ContinuousClock.now < deadline, label)
            try await Task.sleep(for: .milliseconds(10))
        }
    }

    private func require(_ condition: Bool, _ message: String) throws {
        guard condition else { throw RowFailure(message) }
    }
}
#endif
