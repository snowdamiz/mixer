import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilities
@_spi(GuestUIV1) import MixerGuest
import MixerUI
import MixerUpdates
import XCTest
@testable import MixerCapabilityActivation

private actor QueueRepositoryView: InstalledApplicationStorageServing {
    let repository: WorkspaceRepository
    private(set) var readKeys: [String] = []
    private(set) var refusedWrites = 0

    init(_ repository: WorkspaceRepository) { self.repository = repository }

    static func payload(_ workspace: Workspace, page: Int) throws -> Data {
        let slice = try XCTUnwrap(QueuePage(index: page, total: workspace.outbox.count))
        var bytes = Data([UInt8(truncatingIfNeeded: slice.total), UInt8(slice.total >> 8)])
        for row in workspace.outbox.reversed().dropFirst(slice.start).prefix(slice.count) {
            bytes.append(contentsOf: row.id.uuidString.lowercased().utf8)
            switch row.kind {
            case .projectCreated: bytes.append(contentsOf: [0, 0])
            case .taskSaved:
                let title = workspace.tasks.first { $0.id == row.recordID }?.title ?? "Task"
                bytes.append(contentsOf: [1, UInt8(title.utf8.count)])
                bytes.append(contentsOf: title.utf8)
            case .taskOrderChanged: bytes.append(contentsOf: [2, 0])
            case .entrySaved: bytes.append(contentsOf: [3, 0])
            }
        }
        return bytes
    }

    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        readKeys.append(arguments.key)
        guard arguments.namespace == "material_test", arguments.key.hasPrefix("queue-"),
              let page = Int(arguments.key.dropFirst(6)), arguments.key == "queue-\(page)" else {
            throw CapabilityFailure.permissionDenied
        }
        let workspace = await repository.snapshot()
        return try KVGetResponse(found: true, valueBase64: Self.payload(workspace, page: page).base64EncodedString())
    }

    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        refusedWrites += 1
        throw CapabilityFailure.permissionDenied
    }

    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        refusedWrites += 1
        throw CapabilityFailure.permissionDenied
    }
}

final class PendingQueueTests: XCTestCase {
    @MainActor func testSignedHistoricalPendingQueue() async throws {
        let root = URL(fileURLWithPath: try XCTUnwrap(ProcessInfo.processInfo.environment["FIELDLOG_F10_RUN"]))
        let local = root.appendingPathComponent("workspace")
        let file = local.appendingPathComponent("workspace.json")
        let seeder = try WorkspaceRepository(directory: local)
        let persisted = try await seeder.transact { workspace in
            let sameTime = Date(timeIntervalSince1970: 1_000_000)
            let primary = try workspace.createProject(title: "Inspection", site: "", now: sameTime)
            let other = try workspace.createProject(title: "Warehouse", site: "", now: sameTime)
            for number in 0..<21 {
                let title = number == 20 ? "Valve \"🧪\" \\ north\nZoë" : String(repeating: "🧪", count: 60)
                try workspace.saveTask(projectID: number == 0 ? other : primary, title: title, responsible: "", now: sameTime)
            }
            try workspace.toggleTask(workspace.tasks[0].id, now: sameTime)
            try workspace.reorderTasks(projectID: primary, ids: workspace.tasks(for: primary).map(\.id).reversed(), now: sameTime)
            let draft = EntryDraft(projectID: primary, title: "Meter result", occurredAt: sameTime, updatedAt: sameTime)
            try workspace.saveDraft(draft)
            try workspace.commitDraft(draft.id, now: sameTime)
            let unsaved = EntryDraft(projectID: primary, title: "Still a draft", occurredAt: sameTime, updatedAt: sameTime)
            try workspace.saveDraft(unsaved)
            workspace.restoration.selectedProjectID = primary
            workspace.restoration.openDraftID = unsaved.id
        }
        await seeder.close()
        let original = try Data(contentsOf: file)
        let readOnly = try WorkspaceRepository(directory: local) { _ in throw CapabilityFailure.permissionDenied }
        let snapshot = await readOnly.snapshot()
        XCTAssertEqual(snapshot, persisted)
        let store = QueueRepositoryView(readOnly)
        let ordered = Array(snapshot.outbox.reversed())
        XCTAssertEqual(ordered.count, 26)
        XCTAssertEqual(Set(ordered.map(\.kind)), [.projectCreated, .taskSaved, .taskOrderChanged, .entrySaved])

        let lastPage = try XCTUnwrap(QueuePage(index: 1, total: ordered.count))
        var native = QueueNavigation()
        XCTAssertTrue(native.activate(.open, current: lastPage))
        let installedKinds = UIValidator(limits: .init(maximumMessageBytes: 65_536, maximumNodes: 256,
            maximumDepth: 16, maximumChildrenPerNode: 64, maximumStringBytes: 4_096),
            supportedKinds: [.vStack, .text, .button])
        var ordinaryRoots: [UINode] = []
        for page in 0...1 {
            let compact = try ordinaryFrame(native, workspace: snapshot, page: page, historical: false)
            try assertQueue(compact, snapshot, ordered, page)
            ordinaryRoots.append(compact.root)
            _ = try installedKinds.validate(compact)
            let historical = try ordinaryFrame(native, workspace: snapshot, page: page, historical: true)
            XCTAssertEqual(historical.root.kind, .navigation)
            try assertQueue(historical, snapshot, ordered, page)
            XCTAssertThrowsError(try installedKinds.validate(historical)) {
                XCTAssertEqual($0 as? UIValidationError, .unsupportedNode(.navigation))
            }
        }
        print("F10 ordinary shared projection: 26 real unsent rows across pages 20+6; installed validator rejects navigation; disk sha256=\(ReleaseVerifier.sha256(original))")
        try await signed(root, store, historical: false) { runtime in
            let attachment = try XCTUnwrap(runtime.presentation.claimNativeAttachment())
            try await wait("first page data hydrated") { self.frame(runtime)?.revision == 1 }
            XCTAssertEqual(self.frame(runtime)?.root.children.first?.properties["label"]?.string, "On device · 26 pending changes · Not sent")
            try self.activate("workspace.queue", runtime, attachment)
            try await self.wait("queue page 1") { self.frame(runtime)?.revision == 2 }
            XCTAssertEqual(self.frame(runtime)?.root, ordinaryRoots[0])
            XCTAssertThrowsError(try self.activate("queue.previous", runtime, attachment))

            let host = try XCTUnwrap(runtime.presentation.renderHost)
            let old = UIEventEnvelope(revision: 2, identity: try XCTUnwrap(host.snapshot.identity(for: "queue.next")), event: .activate)
            try self.activate("queue.next", runtime, attachment)
            try await self.wait("queue page 2") { self.frame(runtime)?.revision == 4 }
            XCTAssertEqual(self.frame(runtime)?.root, ordinaryRoots[1])
            XCTAssertThrowsError(try runtime.presentation.renderHost?.route(old))
            XCTAssertThrowsError(try self.activate("queue.next", runtime, attachment))
            try self.activate("workspace.back", runtime, attachment)
            try await self.wait("tasks return") { self.frame(runtime)?.revision == 5 }
            try self.activate("workspace.queue", runtime, attachment)
            try await self.wait("saved queue page cursor") { self.frame(runtime)?.revision == 6 }
            XCTAssertEqual(self.frame(runtime)?.root, ordinaryRoots[1])
            try self.activate("queue.previous", runtime, attachment)
            try await self.wait("queue previous") { self.frame(runtime)?.revision == 8 }
            XCTAssertEqual(self.frame(runtime)?.root, ordinaryRoots[0])
            try self.activate("workspace.entries", runtime, attachment)
            try await self.wait("entries route handoff") { self.frame(runtime)?.revision == 9 }
            XCTAssertEqual(self.frame(runtime)?.root.children.first?.id, "workspace.entries.destination")
            let lifecycle = try XCTUnwrap(runtime.presentation.lifecycleObservation)
            let counters = lifecycle.counters
            XCTAssertEqual(counters.acceptedEvents, 6)
            XCTAssertEqual(counters.deliveredEvents, 6)
            XCTAssertEqual(counters.terminalEvents, 0)
            XCTAssertFalse(lifecycle.eventOutstanding)
            XCTAssertNil(lifecycle.stop)
            print("F10 compact signed route: revisions 1–9, exact ordinary roots; accepted=\(counters.acceptedEvents) delivered=\(counters.deliveredEvents) terminatedEarly=\(counters.terminalEvents)")
        }
        try await signed(root, store, historical: true) { runtime in
            let attachment = try XCTUnwrap(runtime.presentation.claimNativeAttachment())
            try await wait("historical control start") { self.frame(runtime)?.revision == 1 }
            try self.activate("workspace.queue", runtime, attachment)
            try await self.wait("historical installed document refusal") {
                await runtime.recoverySnapshot().activation.firstUIProtocolFailure != nil
            }
            let result = await runtime.recoverySnapshot()
            XCTAssertEqual(result.activation.firstUIProtocolFailure?.failure, .init(phase: .event, code: .document))
            XCTAssertTrue(result.activation.effectsMayHaveOpened)
            XCTAssertNil(result.activation.firstBridgeFailure)
            XCTAssertNil(result.healthy)
            print("F10 historical signed topology refused: event/document after repository hydration and queue activation")
        }

        let requests = await store.readKeys
        let writes = await store.refusedWrites
        XCTAssertEqual(requests, ["queue-0", "queue-1", "queue-0", "queue-0"])
        XCTAssertEqual(writes, 0)
        await readOnly.close()
        let reopened = try WorkspaceRepository(directory: local)
        let after = await reopened.snapshot()
        await reopened.close()
        XCTAssertEqual(after, persisted)
        let finalBytes = try Data(contentsOf: file)
        XCTAssertEqual(finalBytes, original)
        print("F10 reopened exact revision=\(after.revision), pending=\(after.outbox.count), reads=\(requests), write attempts=\(writes), disk sha256=\(ReleaseVerifier.sha256(finalBytes))")
    }

    @MainActor private func signed(_ root: URL, _ store: QueueRepositoryView, historical: Bool,
                                  _ body: (CapabilityGuestUIRuntime) async throws -> Void) async throws {
        let name = historical ? "historical" : "compact"
        let directory = root.appendingPathComponent(name)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
        let fixture = try GuestUISignedFixture(root: directory, deferredService: store)
        let payload = try Data(contentsOf: root.deletingLastPathComponent().appendingPathComponent(name + ".wasm"))
        let docs = try fixture.documents(payload, storage: true)
        let before = CapabilityAttemptReservation.occupiedSlots
        let runtime = try await CapabilityGuestUIRuntime.open(configuration: fixture.configuration, execution: fixture.execution)
        var bodyError: (any Error)?
        do {
            try await runtime.beginDownload(signedManifest: docs.0, signedAssignment: docs.1)
            try await runtime.appendDownload(payload, atOffset: 0)
            try await runtime.finishDownload()
            let start = try await runtime.start()
            print("F10 \(name) start phase=\(start.phase) cause=\(String(describing: start.terminalCause)) bridge=\(String(describing: start.firstBridgeFailure)) ui=\(String(describing: start.firstUIProtocolFailure))")
            XCTAssertEqual(start.phase, .provisionalGuest)
            try await body(runtime)
        } catch {
            bodyError = error
            let status = await runtime.recoverySnapshot()
            print("F10 \(name) failure state=\(status.activation.phase) cause=\(String(describing: status.activation.terminalCause)) bridge=\(String(describing: status.activation.firstBridgeFailure)) ui=\(String(describing: status.activation.firstUIProtocolFailure)) reads=\(await store.readKeys)")
        }
        await runtime.close()
        try await wait("owner retired") { runtime.ownerRetired }
        let closed = await runtime.recoverySnapshot()
        XCTAssertTrue(closed.closed)
        XCTAssertFalse(closed.activation.cleanupPending)
        XCTAssertNil(closed.healthy)
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, before)
        print("F10 \(name) owner retired, closed, reservation count=\(before)")
        if let bodyError { throw bodyError }
    }

    private func ordinaryFrame(_ state: QueueNavigation, workspace: Workspace, page: Int, historical: Bool) throws -> UIDocument {
        let bytes = try QueueRepositoryView.payload(workspace, page: page)
        var out = Data(count: 32_768)
        let count = out.withUnsafeMutableBytes { output in
            bytes.withUnsafeBytes { state.render(revision: 1, pageIndex: page, payload: $0, into: output, historicalLayout: historical) }
        }
        XCTAssertGreaterThan(count, 0)
        return try UIDocument.decode(out.prefix(count))
    }

    private func assertQueue(_ document: UIDocument, _ snapshot: Workspace, _ ordered: [PendingChange], _ page: Int) throws {
        let all = flatten(document.root)
        let pending = all.filter { $0.id.hasPrefix("pending.") }
        let expected = Array(ordered.dropFirst(page * 20).prefix(20))
        XCTAssertEqual(pending.map(\.id), expected.map { "pending." + $0.id.uuidString.lowercased() })
        let labels = expected.map { row -> String in
            let label: String
            switch row.kind {
            case .projectCreated: label = "Project created"
            case .taskSaved: label = "Task updated: " + (snapshot.tasks.first { $0.id == row.recordID }?.title ?? "Task")
            case .taskOrderChanged: label = "Checklist reordered"
            case .entrySaved: label = "Entry saved"
            }
            return label + " — Saved on device · Not sent"
        }
        XCTAssertEqual(pending.compactMap { $0.properties["text"]?.string }, labels)
        let summary = try XCTUnwrap(all.first { $0.id == "queue.changes" })
        XCTAssertEqual(summary.properties["text"]?.string ?? summary.properties["title"]?.string, "Pending changes (26)")
        XCTAssertEqual(all.first { $0.id == "queue.position" }?.properties["text"]?.string,
                       page == 0 ? "Page 1 of 2 · Changes 1–20 of 26 · Newest first" : "Page 2 of 2 · Changes 21–26 of 26 · Newest first")
    }

    private func flatten(_ node: UINode) -> [UINode] { [node] + node.children.flatMap(flatten) }

    @MainActor private func frame(_ runtime: CapabilityGuestUIRuntime) -> UIDocument? {
        runtime.presentation.renderHost?.snapshot.document
    }

    @MainActor private func activate(_ id: String, _ runtime: CapabilityGuestUIRuntime,
                                     _ attachment: CapabilityGuestUIAttachmentIdentity) throws {
        let model = runtime.presentation
        let host = try XCTUnwrap(model.renderHost)
        let identity = try XCTUnwrap(host.snapshot.identity(for: id))
        let action = try host.route(.init(revision: host.snapshot.document.revision, identity: identity, event: .activate))
        XCTAssertTrue(model.inputEnabled)
        model.actionHandler(host: host, attachment: attachment)(action)
    }

    @MainActor private func wait(_ label: String, _ predicate: () async -> Bool) async throws {
        let end = ContinuousClock.now + .seconds(5)
        while !(await predicate()) {
            guard ContinuousClock.now < end else { throw NSError(domain: label, code: 1) }
            try await Task.sleep(for: .milliseconds(3))
        }
    }
}
