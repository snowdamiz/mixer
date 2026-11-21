#if os(macOS) && MIXER_PRIVATE_F10
import Crypto
import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilities
import MixerApple
@_spi(GuestUIV1) @_spi(FeatureUIV3) import MixerGuest
import MixerRuntimeIdentity
import MixerUI
import MixerUpdates
@testable import MixerCapabilityActivation
import XCTest

private enum FixtureError: Error { case denied, missingState, timeout }

private actor QueueRepository: InstalledApplicationStorageServing {
    let repository: WorkspaceRepository
    let durableState: URL
    private(set) var reads: [KVGetArguments] = []
    private(set) var writes = 0

    init(repository: WorkspaceRepository, durableState: URL) {
        self.repository = repository
        self.durableState = durableState
    }

    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        let state = try JSONSerialization.jsonObject(with: Data(contentsOf: durableState)) as? [String: Any]
        let attempt = state?["attempt"] as? [String: Any]
        guard attempt?["effectsMayHaveOpened"] as? Bool == true else { throw FixtureError.missingState }
        guard arguments == KVGetArguments(namespace: "material_test", key: "queue-0"), reads.isEmpty else {
            throw FixtureError.denied
        }
        reads.append(arguments)
        let workspace = await repository.snapshot()
        let count = workspace.outbox.count
        guard count <= 50_000 else { throw FixtureError.denied }
        var bytes = Data([UInt8(truncatingIfNeeded: count), UInt8(count >> 8)])
        for row in workspace.outbox.reversed().prefix(20) {
            bytes.append(contentsOf: row.id.uuidString.lowercased().utf8)
            switch row.kind {
            case .projectCreated: bytes.append(contentsOf: [0, 0])
            case .taskSaved:
                let title = workspace.tasks.first { $0.id == row.recordID }?.title ?? "Task"
                guard (1...240).contains(title.utf8.count) else { throw FixtureError.denied }
                bytes.append(contentsOf: [1, UInt8(title.utf8.count)])
                bytes.append(contentsOf: title.utf8)
            case .taskOrderChanged: bytes.append(contentsOf: [2, 0])
            case .entrySaved: bytes.append(contentsOf: [3, 0])
            }
        }
        return KVGetResponse(found: true, valueBase64: bytes.base64EncodedString())
    }

    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        writes += 1
        throw FixtureError.denied
    }

    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        writes += 1
        throw FixtureError.denied
    }
}

private actor SyntheticQueueRead: InstalledApplicationStorageServing {
    enum Reply { case missing, denied, failure, delayed }
    let reply: Reply
    private var pending: CheckedContinuation<KVGetResponse, Never>?
    private(set) var reads: [KVGetArguments] = []
    private(set) var writes = 0

    init(_ reply: Reply) { self.reply = reply }

    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        reads.append(arguments)
        switch reply {
        case .missing: return KVGetResponse(found: false, valueBase64: "")
        case .denied: throw CapabilityFailure.permissionDenied
        case .failure: throw CapabilityFailure.ioFailure
        case .delayed:
            return await withCheckedContinuation { pending = $0 }
        }
    }

    func finish() {
        let completion = pending
        pending = nil
        completion?.resume(returning: KVGetResponse(found: true, valueBase64: "AAA="))
    }

    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        writes += 1
        throw FixtureError.denied
    }

    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        writes += 1
        throw FixtureError.denied
    }
}

@MainActor final class PrivateFieldLogF10Tests: XCTestCase {
    func testSignedF10QueueCrossesVMAndMailbox() async throws {
        let run = try runDirectory()
        let root = run.appendingPathComponent("signed", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        let directory = root.appendingPathComponent("workspace", isDirectory: true)
        let file = directory.appendingPathComponent("workspace.json")
        let persisted = try await seed(directory)
        let before = try Data(contentsOf: file)
        let repository = try WorkspaceRepository(directory: directory) { _ in throw FixtureError.denied }
        let service = QueueRepository(repository: repository,
            durableState: root.appendingPathComponent("recovery/state.json"))
        let fixture = try fixture(root: root, repository: service)
        let presenter = F10HeadlessPresenter()
        let payload = try Data(contentsOf: run.appendingPathComponent("good.wasm"))
        let occupied = CapabilityAttemptReservation.occupiedSlots
        let runtime = try await CapabilityColdStartRuntime.openPrivateF10(configuration: fixture.configuration,
            execution: fixture.execution, presenter: presenter)
        do {
            let signed = try await stage(payload, fixture: fixture, runtime: runtime)
            let noReads = await service.reads
            XCTAssertEqual(noReads, [])
            let started = try await runtime.start()
            XCTAssertEqual(started.phase, .provisionalGuest)
            XCTAssertEqual(started.acceptedSequence, 1)
            XCTAssertTrue(started.effectsMayHaveOpened)
            let exchange = try XCTUnwrap(presenter.exchange)
            let generation = exchange.snapshot().generation
            XCTAssertEqual(generation, 1)
            XCTAssertEqual(presenter.inertRevision, 1)
            try await wait("hydrated frame queued", diagnostics: { String(describing: exchange.snapshot()) }) {
                exchange.snapshot().latestRevision == 2
            }
            let sharedRuntime = try XCTUnwrap(runtime as? CapabilityColdStartRuntime)
            do {
                try await sharedRuntime.reportMilestone("first_screen")
                XCTFail("Private F10 accepted a caller-reported first_screen")
            } catch let error as UpdateError {
                XCTAssertTrue(error.code.hasSuffix(".milestone"))
            }
            try await Task.sleep(for: .milliseconds(1_100))
            let unobserved = await runtime.recoverySnapshot()
            XCTAssertEqual(unobserved.activation.phase, .provisionalGuest)
            XCTAssertNil(unobserved.healthy)
            XCTAssertEqual(exchange.snapshot().displayedRevision, 1)
            XCTAssertNil(exchange.snapshot().pendingPresentationReceipt)
            try await wait("hydration", diagnostics: { String(describing: exchange.snapshot()) }) {
                try presenter.presentNext()
                return presenter.host?.snapshot.document.revision == 2
            }
            let host = try XCTUnwrap(presenter.host)
            XCTAssertEqual(host.snapshot.document.root.children.first?.properties["label"]?.string,
                "On device · 26 pending changes · Not sent")
            let identity = try XCTUnwrap(host.snapshot.identity(for: "workspace.queue"))
            let event = UIEventEnvelope(revision: 2, identity: identity, event: .activate)
            XCTAssertEqual(exchange.offer(event, generation: generation + 1), .stale)
            XCTAssertEqual(exchange.offer(event, generation: generation), .accepted(sequence: 1))
            try await wait("queue presentation", diagnostics: { String(describing: exchange.snapshot()) }) {
                try presenter.presentNext()
                return presenter.host?.snapshot.document.revision == 3
            }
            let displayed = host.snapshot.document
            XCTAssertEqual(displayed.revision, 3)
            try assertQueue(displayed, workspace: persisted)
            XCTAssertEqual(presenter.eventResult?.generation, generation)
            XCTAssertEqual(presenter.eventResult?.sequence, 1)
            XCTAssertEqual(presenter.eventResult?.outcome, .delivered)
            XCTAssertEqual(exchange.offer(event, generation: generation), .stale)
            let observed = exchange.snapshot()
            XCTAssertEqual(observed.generation, generation)
            XCTAssertEqual(observed.displayedRevision, 3)
            XCTAssertEqual(observed.counters.producedFrames, 3)
            XCTAssertEqual(observed.counters.acceptedEvents, 1)
            XCTAssertEqual(observed.counters.deliveredEvents, 1)
            XCTAssertEqual(observed.counters.terminalEvents, 0)
            let reads = await service.reads, writes = await service.writes
            XCTAssertEqual(reads, [.init(namespace: "material_test", key: "queue-0")])
            XCTAssertEqual(writes, 0)
            try await wait("durable health") {
                await runtime.recoverySnapshot().activation.phase == .healthyGuest
            }
            let health = await runtime.recoverySnapshot()
            XCTAssertEqual(health.healthy, started.candidateID)
            await runtime.close()
            try await requireRetirement(runtime, occupied: occupied)
            XCTAssertNil(presenter.exchange)
            XCTAssertEqual(exchange.offer(event, generation: generation), .closed)
            XCTAssertEqual(exchange.snapshot().stop, .closed)
            await repository.close()

            let reopened = try WorkspaceRepository(directory: directory)
            let after = await reopened.snapshot()
            await reopened.close()
            XCTAssertEqual(after, persisted)
            XCTAssertEqual(after.revision, 1)
            let final = try Data(contentsOf: file)
            XCTAssertEqual(final, before)
            let coldPresenter = F10HeadlessPresenter()
            let cold = try await CapabilityColdStartRuntime.openPrivateF10(configuration: fixture.configuration,
                execution: fixture.execution, presenter: coldPresenter)
            let coldState = await cold.recoverySnapshot()
            XCTAssertEqual(coldState.healthy, started.candidateID)
            XCTAssertEqual(coldState.acceptedSequence, 1)
            XCTAssertFalse(coldState.incompleteAttempt)
            await cold.close()
            try await requireRetirement(cold, occupied: occupied)
            print("F10 signed fingerprint=\(fixture.execution.runtimeFingerprint) manifestSHA256=\(signed.manifest) assignmentSHA256=\(signed.assignment) payloadSHA256=\(ReleaseVerifier.sha256(payload)) generation=\(generation) revisions=1,2,3 delivered=1 rows=20 reads=1 writes=0 workspaceRevision=1 workspaceSHA256=\(ReleaseVerifier.sha256(final)) unobservedHealth=false durableHealth=true retired=true")
        } catch {
            await runtime.close()
            do { try await requireRetirement(runtime, occupied: occupied) }
            catch { throw error }
            await repository.close()
            throw error
        }
    }

    func testSignedF10RequiresFoundResponseForExactRequest() async throws {
        let run = try runDirectory()
        for (label, reply, wasm, expectedReads) in [
            ("missing", SyntheticQueueRead.Reply.missing, "good", 1),
            ("failed", .failure, "good", 1),
            ("denied", .denied, "good", 1),
            ("wrong-request", .failure, "wrong-request", 0),
        ] {
            let root = run.appendingPathComponent("response-\(label)")
            try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
            let service = SyntheticQueueRead(reply)
            let fixture = try fixture(root: root, repository: service)
            let presenter = F10HeadlessPresenter()
            let payload = try Data(contentsOf: run.appendingPathComponent("\(wasm).wasm"))
            let occupied = CapabilityAttemptReservation.occupiedSlots
            let runtime = try await CapabilityColdStartRuntime.openPrivateF10(configuration: fixture.configuration,
                execution: fixture.execution, presenter: presenter)
            do {
                try await stage(payload, fixture: fixture, runtime: runtime)
                _ = try await runtime.start()
                let exchange = try XCTUnwrap(presenter.exchange)
                try await wait(label, diagnostics: { String(describing: exchange.snapshot()) }) {
                    await runtime.recoverySnapshot().activation.phase == .recoveryRequired
                }
                try presenter.presentNext()
                let stopped = exchange.snapshot()
                XCTAssertEqual(stopped.firstUIProtocolFailure?.failure, .init(phase: .wake, code: .document), label)
                XCTAssertEqual(stopped.firstUIProtocolFailure?.effectStage, .intentEntered, label)
                XCTAssertEqual(stopped.counters.producedFrames, 1, label)
                XCTAssertEqual(presenter.host?.snapshot.document.revision, 1, label)
                let reads = await service.reads, writes = await service.writes
                XCTAssertEqual(reads, Array(repeating: .init(namespace: "material_test", key: "queue-0"), count: expectedReads), label)
                XCTAssertEqual(writes, 0, label)
                let state = await runtime.recoverySnapshot()
                XCTAssertNil(state.healthy, label)
            } catch {
                await runtime.close()
                try await requireRetirement(runtime, occupied: occupied)
                throw error
            }
            await runtime.close()
            try await requireRetirement(runtime, occupied: occupied)
            print("F10 response \(label) frames=1 reads=\(expectedReads) writes=0 durableHealth=false retired=true")
        }
    }

    func testSignedF10RetiredOwnerIgnoresPendingReadCompletion() async throws {
        let run = try runDirectory()
        let root = run.appendingPathComponent("retired-response")
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        let service = SyntheticQueueRead(.delayed)
        let fixture = try fixture(root: root, repository: service)
        let presenter = F10HeadlessPresenter()
        let payload = try Data(contentsOf: run.appendingPathComponent("good.wasm"))
        let occupied = CapabilityAttemptReservation.occupiedSlots
        let runtime = try await CapabilityColdStartRuntime.openPrivateF10(configuration: fixture.configuration,
            execution: fixture.execution, presenter: presenter)
        do {
            try await stage(payload, fixture: fixture, runtime: runtime)
            _ = try await runtime.start()
            let exchange = try XCTUnwrap(presenter.exchange)
            try await wait("pending read") { await service.reads.count == 1 }
            XCTAssertEqual(exchange.snapshot().displayedRevision, 1)
            await runtime.close()
            await service.finish()
            try await requireRetirement(runtime, occupied: occupied)
            let stopped = exchange.snapshot()
            XCTAssertEqual(stopped.stop, .closed)
            XCTAssertEqual(stopped.counters.producedFrames, 1)
            XCTAssertNil(stopped.pendingPresentationReceipt)
            let state = await runtime.recoverySnapshot(), writes = await service.writes
            XCTAssertNil(state.healthy)
            XCTAssertEqual(writes, 0)
            print("F10 response retired frames=1 reads=1 writes=0 durableHealth=false retired=true")
        } catch {
            await runtime.close()
            await service.finish()
            try await requireRetirement(runtime, occupied: occupied)
            throw error
        }
    }

    func testSignedF10WrongDocumentStopsBeforeEffects() async throws {
        let run = try runDirectory()
        let root = run.appendingPathComponent("wrong-document", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        let repository = try WorkspaceRepository(directory: root.appendingPathComponent("workspace"))
        let service = QueueRepository(repository: repository,
            durableState: root.appendingPathComponent("recovery/state.json"))
        let fixture = try fixture(root: root, repository: service)
        let presenter = F10HeadlessPresenter()
        let payload = try Data(contentsOf: run.appendingPathComponent("wrong-document.wasm"))
        let occupied = CapabilityAttemptReservation.occupiedSlots
        let runtime = try await CapabilityColdStartRuntime.openPrivateF10(configuration: fixture.configuration,
            execution: fixture.execution, presenter: presenter)
        do {
            try await stage(payload, fixture: fixture, runtime: runtime)
            let started = try await runtime.start()
            XCTAssertEqual(started.phase, .nativeFallback)
            XCTAssertFalse(started.effectsMayHaveOpened)
            let stopped = try XCTUnwrap(presenter.exchange?.snapshot())
            XCTAssertEqual(stopped.firstUIProtocolFailure?.failure, .init(phase: .startup, code: .document))
            XCTAssertEqual(stopped.firstUIProtocolFailure?.effectStage, .beforeIntent)
            XCTAssertEqual(stopped.counters.producedFrames, 0)
            XCTAssertNil(presenter.inertRevision)
            let reads = await service.reads, writes = await service.writes
            XCTAssertEqual(reads, [])
            XCTAssertEqual(writes, 0)
            print("F10 wrong document startup/document beforeIntent reads=0 writes=0")
        } catch {
            await runtime.close()
            try await requireRetirement(runtime, occupied: occupied)
            await repository.close()
            throw error
        }
        await runtime.close()
        try await requireRetirement(runtime, occupied: occupied)
        await repository.close()
    }

    func testF10PrivateAdmissionRejectsWrongAndMixedBindings() async throws {
        let root = try runDirectory().appendingPathComponent("admission")
        let repository = try WorkspaceRepository(directory: root.appendingPathComponent("workspace"))
        let service = QueueRepository(repository: repository, durableState: root)
        XCTAssertThrowsError(try fixture(root: root, repository: service, variant: .wrongDigest))
        XCTAssertThrowsError(try fixture(root: root, repository: service, variant: .mixed))
        XCTAssertThrowsError(try fixture(root: root, repository: service, variant: .ordinary))
        let fixture = try fixture(root: root, repository: service)
        XCTAssertThrowsError(try CapabilityInstalledExecutionMode.requireGuestUI(fixture.execution.installed.identity,
            milestones: ["feature_started", "first_screen"]))
        XCTAssertThrowsError(try CapabilityInstalledExecutionMode.requireCapabilityOnly(fixture.execution.installed.identity))
        let reads = await service.reads
        XCTAssertEqual(reads, [])
        await repository.close()
        print("F10 private identity refused wrong digest, mixed V1/V3, ordinary admission and both ordinary execution modes")
    }

    private enum Admission { case exact, wrongDigest, mixed, ordinary }

    private func fixture(root: URL, repository: any InstalledApplicationStorageServing,
                         variant: Admission = .exact) throws -> GuestUISignedFixture {
        let key = Curve25519.Signing.PrivateKey()
        let scope = UpdateScope(organization: "material-test", project: "material-test", app: "material-test",
            environment: "development", platform: "macos")
        let roots = try JSONEncoder().encode([TrustRoot(keyID: "guest-ui-signed-test",
            publicKey: key.publicKey.rawRepresentation, scope: scope, artifact: true, assignment: true,
            notBeforeUnix: 1, notAfterUnix: 0)])
        func resource(_ name: String) throws -> Data {
            try Data(contentsOf: XCTUnwrap(Bundle.module.url(forResource: name, withExtension: nil, subdirectory: "Fixtures")))
        }
        typealias Object = [String: Any]
        var identity = try XCTUnwrap(JSONSerialization.jsonObject(with: resource("identity.json")) as? Object)
        var build = try XCTUnwrap(identity["build"] as? Object)
        build["trust_roots_sha256"] = ReleaseVerifier.sha256(roots)
        identity["build"] = build
        #if arch(arm64)
        let architecture = "arm64"
        #else
        let architecture = "x86_64"
        #endif
        identity["platform"] = ["os": "macos", "architecture": architecture, "environment": "device",
            "minimum_os": "14.0", "target": "\(architecture)-apple-macosx14.0"]
        let mode = CapabilityInstalledExecutionMode.self
        var engine = try XCTUnwrap(identity["engine"] as? Object)
        engine["ui_schema"] = 3
        engine["ui_contract_sha256"] = mode.f10WireSHA256
        let vm = try runDirectory().appendingPathComponent("rust/release/libmixer_vm.a")
        engine["artifact_sha256"] = try ReleaseVerifier.sha256(Data(contentsOf: vm))
        engine["source_sha256"] = try XCTUnwrap(ProcessInfo.processInfo.environment["MIXER_F10_SOURCE_SHA256"])
        identity["engine"] = engine
        var execution = try XCTUnwrap(identity["execution"] as? Object)
        execution["startup_export"] = mode.f10Startup
        identity["execution"] = execution
        var dependencies = [
            ["id": mode.f10WireID, "version": "3", "artifact_sha256": mode.f10WireSHA256],
            ["id": mode.f10HeaderID, "version": "3",
             "artifact_sha256": variant == .wrongDigest ? String(repeating: "0", count: 64) : mode.f10HeaderSHA256],
        ]
        if variant == .mixed {
            dependencies.append(["id": mode.contractID, "version": "1", "artifact_sha256": mode.contractSHA256])
        }
        identity["dependencies"] = dependencies.sorted { $0["id"]! < $1["id"]! }
        identity["capabilities"] = try XCTUnwrap(identity["capabilities"] as? [Object]).filter {
            $0["id"] as? String == CapabilitySchemas.storageID
        }
        let identityJSON = try JSONSerialization.data(withJSONObject: identity, options: [.sortedKeys])
        let materials: [CapabilityMaterialFile] = [
            .init(role: .bridgePolicy, bytes: try resource("bridge.json")),
            .init(role: .configuration(capabilityID: CapabilitySchemas.storageID), bytes: try resource("storage.json")),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.storageID), bytes: try resource("storage-grant.json")),
        ]
        if variant == .ordinary {
            let ordinary = try InstalledCapabilityExecution(identityJSON: identityJSON, materials: materials,
                trustRootsJSON: roots, privateContainer: root)
            return GuestUISignedFixture(root: root, execution: ordinary, key: key)
        }
        let installed = try InstalledCapabilityExecution(privateDevelopmentF10JSON: identityJSON, materials: materials,
            trustRootsJSON: roots, privateContainer: root, repository: repository)
        return GuestUISignedFixture(root: root, execution: installed, key: key)
    }

    @discardableResult
    private func stage(_ payload: Data, fixture: GuestUISignedFixture, runtime: any F10InstalledColdStart) async throws
        -> (manifest: String, assignment: String) {
        let (manifest, assignment) = try fixture.documents(payload, startupMilliseconds: 5_000, storage: true,
            memoryBytes: 1_310_720, fuel: 1_000_000,
            sourceCommit: "552559d2d3278abb9b1aa7dcf0288102c09a202b")
        try await runtime.beginDownload(signedManifest: manifest, signedAssignment: assignment)
        try await runtime.appendDownload(payload, atOffset: 0)
        try await runtime.finishDownload()
        return (ReleaseVerifier.sha256(manifest), ReleaseVerifier.sha256(assignment))
    }

    private func runDirectory() throws -> URL {
        URL(fileURLWithPath: try XCTUnwrap(ProcessInfo.processInfo.environment["MIXER_F10_RUN"]))
    }

    private func requireRetirement(_ runtime: any F10InstalledColdStart, occupied: Int) async throws {
        try await wait("attempt retirement") {
            let snapshot = await runtime.recoverySnapshot()
            return snapshot.closed && !snapshot.busy && !snapshot.activation.cleanupPending
                && !snapshot.incompleteAttempt && CapabilityAttemptReservation.occupiedSlots == occupied
        }
    }

    private func wait(_ label: String, diagnostics: () -> String = { "" },
                      until: () async throws -> Bool) async throws {
        let end = ContinuousClock.now + .seconds(3)
        while ContinuousClock.now < end {
            if try await until() { return }
            try await Task.sleep(for: .milliseconds(10))
        }
        XCTFail("Timed out waiting for \(label) \(diagnostics())")
        throw FixtureError.timeout
    }

    private func seed(_ directory: URL) async throws -> Workspace {
        let repository = try WorkspaceRepository(directory: directory)
        do {
            let persisted = try await repository.transact { workspace in
                let now = Date(timeIntervalSince1970: 1_000_000)
                let primary = try workspace.createProject(title: "Inspection", site: "", now: now)
                let other = try workspace.createProject(title: "Warehouse", site: "", now: now)
                for number in 0..<21 {
                    let title = number == 20 ? "Valve \"🧪\" \\ north\nZoë" : String(repeating: "🧪", count: 60)
                    try workspace.saveTask(projectID: number == 0 ? other : primary, title: title, responsible: "", now: now)
                }
                try workspace.toggleTask(workspace.tasks[0].id, now: now)
                try workspace.reorderTasks(projectID: primary, ids: workspace.tasks(for: primary).map(\.id).reversed(), now: now)
                let draft = EntryDraft(projectID: primary, title: "Meter result", occurredAt: now, updatedAt: now)
                try workspace.saveDraft(draft)
                try workspace.commitDraft(draft.id, now: now)
                let unsaved = EntryDraft(projectID: primary, title: "Still a draft", occurredAt: now, updatedAt: now)
                try workspace.saveDraft(unsaved)
                workspace.restoration.selectedProjectID = primary
                workspace.restoration.openDraftID = unsaved.id
            }
            await repository.close()
            return persisted
        } catch {
            await repository.close()
            throw error
        }
    }

    private func assertQueue(_ document: UIDocument, workspace: Workspace) throws {
        XCTAssertEqual(workspace.outbox.count, 26)
        XCTAssertEqual(document.root.kind, .navigation)
        XCTAssertEqual(document.root.id, "task.screen")
        XCTAssertEqual(document.root.children.map(\.id), ["task.form"])
        let list = try XCTUnwrap(document.root.children.first)
        XCTAssertEqual(list.kind, .list)
        XCTAssertEqual(list.children.map(\.id), ["queue.summary", "queue.changes"])
        XCTAssertEqual(list.children.map(\.kind), [.section, .section])
        let changes = try XCTUnwrap(list.children.last)
        XCTAssertEqual(changes.properties["title"]?.string, "Pending changes (26)")
        XCTAssertEqual(changes.children.first?.properties["text"]?.string, "Page 1 of 2 · Changes 1–20 of 26 · Newest first")
        let rows = changes.children.filter { $0.id.hasPrefix("pending.") }
        let expected = workspace.outbox.reversed().prefix(20)
        XCTAssertEqual(rows.map(\.id), expected.map { "pending." + $0.id.uuidString.lowercased() })
        let labels = expected.map { row in
            let prefix: String
            switch row.kind {
            case .projectCreated: prefix = "Project created"
            case .taskSaved: prefix = "Task updated: " + (workspace.tasks.first { $0.id == row.recordID }?.title ?? "Task")
            case .taskOrderChanged: prefix = "Checklist reordered"
            case .entrySaved: prefix = "Entry saved"
            }
            return Array((prefix + " — Saved on device · Not sent").utf8)
        }
        XCTAssertEqual(rows.compactMap { $0.properties["text"]?.string }.map { Array($0.utf8) }, labels)
    }
}
#endif
