import CryptoKit
import FieldLogModels
import FieldLogStorage
import Foundation
import MixerApple
@_spi(FeatureUIV3) @_spi(GuestUIV1) import MixerGuest
import MixerUI
import XCTest

private enum FixtureError: Error { case storageDenied }

private struct ScopedQueuePage {
    let index: Int
    let bytes: Data

    func bounds() throws -> QueuePage {
        try bytes.withUnsafeBytes { buffer in
            var input = QueueBytes(buffer)
            let low = try XCTUnwrap(input.byte())
            let high = try XCTUnwrap(input.byte())
            return try XCTUnwrap(QueuePage(index: index, total: Int(low) + 256 * Int(high)))
        }
    }
}

@MainActor
private final class QueueReads {
    let repository: WorkspaceRepository
    private(set) var keys: [String] = []

    init(_ repository: WorkspaceRepository) { self.repository = repository }

    func get(namespace: String, key: String) async throws -> ScopedQueuePage {
        guard namespace == "material_test", ["queue-0", "queue-1"].contains(key) else {
            throw FixtureError.storageDenied
        }
        keys.append(key)
        let workspace = await repository.snapshot()
        let page = try XCTUnwrap(QueuePage(index: key == "queue-0" ? 0 : 1, total: workspace.outbox.count))
        var bytes = Data([UInt8(truncatingIfNeeded: page.total), UInt8(page.total >> 8)])
        for row in workspace.outbox.reversed().dropFirst(page.start).prefix(page.count) {
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
        return ScopedQueuePage(index: page.index, bytes: bytes)
    }
}

final class HistoricalQueueV3Tests: XCTestCase {
    @MainActor func testHistoricalQueueExchangeAndRenderOwnership() async throws {
        let root = URL(fileURLWithPath: try XCTUnwrap(ProcessInfo.processInfo.environment["FIELDLOG_F10_RUN"]))
        let directory = root.appendingPathComponent("workspace")
        let file = directory.appendingPathComponent("workspace.json")
        let persisted = try await seed(directory)
        let before = try Data(contentsOf: file)
        let repository = try WorkspaceRepository(directory: directory) { _ in
            XCTFail("The read-only fixture attempted to persist a mutation")
            throw FixtureError.storageDenied
        }
        let workspace = await repository.snapshot()
        XCTAssertEqual(workspace, persisted)
        let ordered = Array(workspace.outbox.reversed())
        XCTAssertEqual(ordered.count, 26)
        XCTAssertEqual(Set(ordered.map(\.kind)), [.projectCreated, .taskSaved, .taskOrderChanged, .entrySaved])
        let storage = QueueReads(repository)
        let initialPage = try await storage.get(namespace: "material_test", key: "queue-0")
        try await compare(workspace, storage: storage, initialPage: initialPage)
        XCTAssertEqual(storage.keys, ["queue-0", "queue-1", "queue-0"])
        await repository.close()

        let reopened = try WorkspaceRepository(directory: directory)
        let after = await reopened.snapshot()
        await reopened.close()
        let finalBytes = try Data(contentsOf: file)
        XCTAssertEqual(after, persisted)
        XCTAssertEqual(after.revision, 1)
        XCTAssertEqual(finalBytes, before)
        let sha = SHA256.hash(data: finalBytes).map { String(format: "%02x", $0) }.joined()
        print("F10 repository namespace=material_test reads=\(storage.keys) writes=0 revision=\(after.revision) pending=\(after.outbox.count) diskSHA256=\(sha)")
    }

    @MainActor private func seed(_ directory: URL) async throws -> Workspace {
        let repository = try WorkspaceRepository(directory: directory)
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
    }

    @MainActor private func compare(_ workspace: Workspace, storage: QueueReads, initialPage: ScopedQueuePage) async throws {
        let generation: UInt64 = 1
        let exchange = try GuestUIExchangeV3(generation: generation, textValuePolicy: .standard)
        defer { exchange.stop(.closed) }
        var navigation = QueueNavigation()
        var revision: UInt64 = 1
        var page = initialPage
        let tasksBytes = try render(navigation, revision: revision, page: page)
        let startup = try exchange.claimStartup()
        try exchange.finishTurn(startup, documentBytes: exchange.codec.encode(UIDocument.decode(tasksBytes)))
        let startupPresentation = try XCTUnwrap(exchange.claimPresentation(generation: generation))
        let tasks = try XCTUnwrap(startupPresentation.frame).document.document
        let host = try MixerUIHost(document: tasks, validator: exchange.codec.validator)
        let firstTicket = try XCTUnwrap(exchange.completePresentation(startupPresentation, snapshot: host.snapshot))
        XCTAssertFalse(exchange.observePresentation(firstTicket))
        let open = try envelope(.open, host)
        XCTAssertEqual(exchange.offer(open, generation: generation), .busy)
        try exchange.enterEffectsIntent(generation: generation)
        try exchange.confirmEffectsEnabled(generation: generation)
        observe(firstTicket)
        XCTAssertEqual(tasks.root.kind, .vStack)
        XCTAssertEqual(tasks.root.children.first?.properties["label"]?.string, "On device · 26 pending changes · Not sent")
        print("F10 frame=1 root=vStack pendingRows=0")

        func observe(_ ticket: GuestUIPresentationTicketV1) {
            XCTAssertTrue(exchange.observePresentation(ticket))
            XCTAssertEqual(exchange.snapshot().pendingPresentationReceipt?.revision, ticket.revision)
            exchange.consumeObservedPresentation(generation: generation, frameSerial: ticket.frameSerial)
            XCTAssertNil(exchange.snapshot().pendingPresentationReceipt)
        }

        func turn(_ claim: GuestUITurnClaimV1, loading: Bool, delivered: UInt64?) throws -> UIDocument {
            revision += 1
            let bytes = try render(navigation, revision: revision, page: page, loading: loading)
            let expected = try UIDocument.decode(bytes)
            try exchange.finishTurn(claim, documentBytes: exchange.codec.encode(expected))
            let presentation = try XCTUnwrap(exchange.claimPresentation(generation: generation))
            XCTAssertEqual(presentation.eventResult?.sequence, delivered)
            XCTAssertEqual(presentation.eventResult?.outcome, delivered.map { _ in .delivered })
            XCTAssertNil(presentation.stop)
            let document = try XCTUnwrap(presentation.frame).document.document
            try host.update(document)
            XCTAssertEqual(host.snapshot.document, expected)
            let ticket = try XCTUnwrap(exchange.completePresentation(presentation, snapshot: host.snapshot))
            observe(ticket)
            XCTAssertEqual(exchange.snapshot().displayedRevision, revision)
            if navigation.screen == .queue { try assertQueue(document, workspace: workspace, page: page.index) }
            let count = flatten(document.root).filter { $0.id.hasPrefix("pending.") }.count
            print("F10 frame=\(revision) root=\(document.root.kind) pendingRows=\(count)")
            return document
        }

        let actions: [QueueAction] = [.open, .next, .tasks, .open, .previous, .entries]
        let expectedRevisions: [UInt64] = [2, 4, 5, 6, 8, 9]
        var pageOne: UIDocument?
        var pageTwo: UIDocument?
        var retiredNext: UIEventEnvelope?
        for (index, action) in actions.enumerated() {
            let input = try envelope(action, host)
            let sequence = UInt64(index + 1)
            XCTAssertEqual(exchange.offer(input, generation: generation), .accepted(sequence: sequence))
            let claim = try XCTUnwrap(exchange.claimNextTurn(ready: false))
            guard case .event(let claimedSequence, let bytes) = claim.kind else { return XCTFail("Missing event turn") }
            let node = try XCTUnwrap(flatten(host.snapshot.document.root).first { $0.id == input.identity.id })
            let event = try GuestUIEventCodecV3.decode(bytes, node: node, textValuePolicy: .standard)
            XCTAssertThrowsError(try GuestUIEventCodecV1.decode(bytes))
            XCTAssertEqual(claimedSequence, sequence)
            XCTAssertEqual(event.sequence, sequence)
            XCTAssertEqual(event.revision, revision)
            XCTAssertEqual(event.nodeID, input.identity.id)
            XCTAssertEqual(event.actionID, String(describing: action.id))
            guard case .activate = event.payload else { return XCTFail("Wrong V3 event payload") }
            if index == 1 {
                var wrongAction = navigation
                XCTAssertTrue(try route(String(describing: QueueAction.entries.id), page: page, navigation: &wrongAction))
                XCTAssertEqual(wrongAction.screen, .entries)
                XCTAssertEqual(wrongAction.page, 0)

                // The same 20 rows form a complete, single-page payload with this count.
                var singlePageBytes = page.bytes
                singlePageBytes.replaceSubrange(0..<2, with: [UInt8(QueuePage.size), 0])
                let singlePage = ScopedQueuePage(index: page.index, bytes: singlePageBytes)
                var wrongPage = navigation
                XCTAssertFalse(try route(event.actionID, page: singlePage, navigation: &wrongPage))
                XCTAssertEqual(wrongPage.screen, .queue)
                XCTAssertEqual(wrongPage.page, 0)
                print("F10 routing control: substituted Entries routes to Entries; a single-page payload refuses Next")
            }
            XCTAssertTrue(try route(event.actionID, page: page, navigation: &navigation))
            let changingPage = page.index != navigation.page
            var displayed = try turn(claim, loading: changingPage, delivered: sequence)
            if changingPage {
                for edge in [QueueAction.previous, .next] {
                    XCTAssertEqual(exchange.offer(try envelope(edge, host), generation: generation), .invalid(.disabledNode))
                }
                XCTAssertNil(try exchange.claimNextTurn(ready: false))
                page = try await storage.get(namespace: "material_test", key: "queue-\(navigation.page)")
                let ready = try XCTUnwrap(exchange.claimNextTurn(ready: true))
                guard case .ready = ready.kind else { return XCTFail("Missing ready turn") }
                displayed = try turn(ready, loading: false, delivered: nil)
            }
            XCTAssertEqual(displayed.revision, expectedRevisions[index])
            switch index {
            case 0:
                pageOne = displayed
                retiredNext = try envelope(.next, host)
                XCTAssertEqual(exchange.offer(try envelope(.previous, host), generation: generation), .invalid(.disabledNode))
            case 1:
                pageTwo = displayed
                XCTAssertEqual(exchange.offer(try XCTUnwrap(retiredNext), generation: generation), .stale)
                XCTAssertEqual(exchange.offer(try envelope(.next, host), generation: generation), .invalid(.disabledNode))
            case 2:
                XCTAssertEqual(displayed.root, tasks.root)
            case 3:
                XCTAssertEqual(displayed.root, try XCTUnwrap(pageTwo).root)
                let old = try XCTUnwrap(retiredNext).identity
                XCTAssertNotEqual(try envelope(.next, host).identity, old)
                XCTAssertEqual(exchange.offer(.init(revision: revision, identity: old, event: .activate), generation: generation), .invalid(.staleIdentity))
            case 4:
                XCTAssertEqual(displayed.root, try XCTUnwrap(pageOne).root)
            default:
                XCTAssertEqual(displayed.root.kind, .vStack)
                XCTAssertEqual(displayed.root.children.map(\.id), ["workspace.entries.destination"])
            }
            print("F10 delivered=\(sequence) action=\(event.actionID)")
        }
        let v3 = exchange.snapshot()
        XCTAssertEqual(v3.counters.producedFrames, 9)
        XCTAssertEqual(v3.counters.acceptedEvents, 6)
        XCTAssertEqual(v3.counters.deliveredEvents, 6)
        XCTAssertEqual(v3.counters.terminalEvents, 0)
        XCTAssertFalse(v3.eventOutstanding)
        XCTAssertNil(v3.stop)
        try refuseInV1(tasksBytes: tasksBytes, queue: XCTUnwrap(pageOne), generation: generation)
    }

    private func route(_ actionID: String, page: ScopedQueuePage, navigation: inout QueueNavigation) throws -> Bool {
        let actions: [QueueAction] = [.open, .tasks, .entries, .previous, .next]
        let action = try XCTUnwrap(actions.first { String(describing: $0.id) == actionID })
        return try navigation.activate(action, current: page.bounds())
    }

    @MainActor private func refuseInV1(tasksBytes: Data, queue: UIDocument, generation: UInt64) throws {
        let exchange = try GuestUIExchangeV1(generation: generation, allowsDeferredStartup: true)
        try exchange.finishStartupWithoutDocument(exchange.claimStartup())
        try exchange.enterEffectsIntent(generation: generation)
        try exchange.confirmEffectsEnabled(generation: generation)
        try exchange.finishHydrationHook(XCTUnwrap(exchange.claimNextTurn(ready: true)))
        try exchange.finishTurn(XCTUnwrap(exchange.claimNextTurn(ready: true)), documentBytes: tasksBytes)
        let first = try XCTUnwrap(exchange.claimPresentation(generation: generation))
        let host = try MixerUIHost(document: XCTUnwrap(first.frame).document.document)
        let ticket = try XCTUnwrap(exchange.completePresentation(first, snapshot: host.snapshot))
        XCTAssertTrue(exchange.observePresentation(ticket))
        exchange.consumeObservedPresentation(generation: generation, frameSerial: ticket.frameSerial)
        XCTAssertEqual(exchange.snapshot().displayedRevision, 1)
        let open = try envelope(.open, host)
        XCTAssertEqual(exchange.offer(open, generation: generation), .accepted(sequence: 1))
        let turn = try XCTUnwrap(exchange.claimNextTurn(ready: false))
        guard case .event(let sequence, let bytes) = turn.kind else { return XCTFail("Missing V1 event turn") }
        XCTAssertEqual(sequence, 1)
        XCTAssertEqual(try GuestUIEventCodecV1.decode(bytes), try GuestUIEventV1(sequence: 1, revision: 1,
            nodeID: "workspace.queue", actionID: "workspace.queue"))
        // Use schema-1 bytes for the same tree. Passing a V3 envelope here would test a different refusal.
        let historical = try GuestUICodec(validator: UIValidator()).encode(queue)
        let expected = GuestUIProtocolFailureV1(phase: .event, code: .document)
        XCTAssertThrowsError(try exchange.finishTurn(turn, documentBytes: historical)) {
            XCTAssertEqual($0 as? GuestUIProtocolFailureV1, expected)
        }
        let stopped = exchange.snapshot()
        let failure = try XCTUnwrap(stopped.firstUIProtocolFailure)
        XCTAssertEqual(failure.failure, expected)
        XCTAssertEqual(failure.effectStage, .intentEntered)
        XCTAssertEqual(stopped.stop, .protocolViolation(failure))
        XCTAssertNil(stopped.displayedRevision)
        XCTAssertNil(stopped.pendingPresentationReceipt)
        let terminal = try XCTUnwrap(exchange.claimPresentation(generation: generation))
        XCTAssertNil(terminal.frame)
        XCTAssertEqual(terminal.eventResult?.outcome, .terminal(turnBegan: true))
        XCTAssertNil(exchange.completePresentation(terminal, snapshot: nil))
        XCTAssertFalse(exchange.snapshot().eventOutstanding)
        XCTAssertEqual(exchange.offer(open, generation: generation), .closed)
        print("F10 V1 event/document stop displayedRevision=\(String(describing: stopped.displayedRevision)) terminalTurn=true")
    }

    @MainActor private func envelope(_ action: QueueAction, _ host: MixerUIHost) throws -> UIEventEnvelope {
        let identity = try XCTUnwrap(host.snapshot.identity(for: String(describing: action.id)))
        return .init(revision: host.snapshot.document.revision, identity: identity, event: .activate)
    }

    private func render(_ state: QueueNavigation, revision: UInt64, page: ScopedQueuePage, loading: Bool = false) throws -> Data {
        var output = Data(count: 32_768)
        let count = output.withUnsafeMutableBytes { buffer in
            page.bytes.withUnsafeBytes { state.render(revision: revision, pageIndex: page.index, payload: $0,
                into: buffer, loading: loading, historicalLayout: true) }
        }
        return try XCTUnwrap(count > 0 ? output.prefix(count) : nil)
    }

    private func assertQueue(_ document: UIDocument, workspace: Workspace, page: Int) throws {
        XCTAssertEqual(document.root.kind, .navigation)
        XCTAssertEqual(document.root.id, "task.screen")
        XCTAssertEqual(document.root.children.map(\.id), ["task.form"])
        let list = try XCTUnwrap(document.root.children.first)
        XCTAssertEqual(list.kind, .list)
        XCTAssertEqual(list.children.map(\.id), ["queue.summary", "queue.changes"])
        XCTAssertEqual(list.children.map(\.kind), [.section, .section])
        let changes = try XCTUnwrap(list.children.last)
        XCTAssertEqual(changes.properties["title"]?.string, "Pending changes (26)")
        XCTAssertEqual(changes.children.first?.properties["text"]?.string,
            page == 0 ? "Page 1 of 2 · Changes 1–20 of 26 · Newest first" : "Page 2 of 2 · Changes 21–26 of 26 · Newest first")
        let pending = changes.children.filter { $0.id.hasPrefix("pending.") }
        let expected = Array(workspace.outbox.reversed().dropFirst(page * 20).prefix(20))
        XCTAssertEqual(pending.map(\.id), expected.map { "pending." + $0.id.uuidString.lowercased() })
        let labels = expected.map { row -> String in
            let label: String
            switch row.kind {
            case .projectCreated: label = "Project created"
            case .taskSaved: label = "Task updated: " + (workspace.tasks.first { $0.id == row.recordID }?.title ?? "Task")
            case .taskOrderChanged: label = "Checklist reordered"
            case .entrySaved: label = "Entry saved"
            }
            return label + " — Saved on device · Not sent"
        }
        XCTAssertEqual(pending.compactMap { $0.properties["text"]?.string }.map { Array($0.utf8) }, labels.map { Array($0.utf8) })
    }

    private func flatten(_ node: UINode) -> [UINode] { [node] + node.children.flatMap(flatten) }
}
