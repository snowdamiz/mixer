import FieldLogFeatures
import FieldLogModels
import FieldLogStorage
import Foundation
@testable @_spi(PrivateFieldLogEditor) import MixerCapabilityActivation
@testable @_spi(GuestUIV1) import MixerGuest
import MixerUpdates

@MainActor
final class F11HostActions {
    enum Action: String {
        case save = "entry.saveDraft"
        case commit = "entry.commit"

        var expectedRevision: UInt64 { self == .save ? 1 : 2 }
        var kind: EntrySaveIntent.Kind { self == .save ? .draft : .commit }
    }

    private let model: GuestUIPresentation
    private let display: CapabilityGuestUIDisplayTicket
    private let repository: WorkspaceRepository
    private let action: Action
    private(set) var transactionAttempts = 0

    private init(model: GuestUIPresentation, display: CapabilityGuestUIDisplayTicket,
                 repository: WorkspaceRepository, action: Action) {
        self.model = model
        self.display = display
        self.repository = repository
        self.action = action
    }

    // The host consumes the bound action synchronously on MainActor. The
    // repository independently checks the captured revision at transaction time.
    private func perform(_ requested: Action, from owner: GuestUIPresentation,
                         frame: CapabilityGuestUIDisplayTicket, workspace: UUID,
                         expectedRevision: UInt64, note: Data) async throws -> Workspace? {
        guard transactionAttempts == 0, action == requested, owner === model,
              frame.binding === display.binding, frame.attachment === display.attachment,
              frame.ticket.generation == display.ticket.generation,
              frame.ticket.frameSerial == display.ticket.frameSerial,
              frame.ticket.revision == display.ticket.revision,
              workspace == NoteStorage.workspaceID, expectedRevision == action.expectedRevision,
              model.f11OwnsActionDisplay(display),
              let document = model.renderHost?.snapshot.document,
              document.revision == 2,
              let field = document.root.children.first, field.id == GuestUIFieldLogNoteFixture.field,
              let displayed = field.properties["value"]?.string,
              note == Data(displayed.utf8), note == Data(GuestUIFieldLogNoteFixture.edited.utf8)
        else { return nil }

        transactionAttempts += 1
        let kind = action.kind
        return try await repository.transact(expectedRevision: expectedRevision) { live in
            guard live.id == workspace, live.restoration.selectedProjectID == NoteStorage.projectID,
                  live.restoration.openDraftID == NoteStorage.draftID,
                  !live.entries.contains(where: { $0.id == NoteStorage.draftID }),
                  var draft = live.drafts.first(where: { $0.id == NoteStorage.draftID }),
                  draft.projectID == NoteStorage.projectID,
                  draft.note.utf8.elementsEqual((kind == .draft
                    ? GuestUIFieldLogNoteFixture.original : GuestUIFieldLogNoteFixture.edited).utf8)
            else { throw FieldLogError.missingRecord }
            draft.note = displayed
            if kind == .draft { draft.updatedAt = Date() }
            try EntrySaveIntent(projectID: NoteStorage.projectID, draft: draft, kind: kind).apply(to: &live)
        }
    }

    static func exercise(owner: CapabilityGuestUIRuntime, work: URL, repository: WorkspaceRepository,
                         attachment: CapabilityGuestUIAttachmentIdentity,
                         initial: CapabilityGuestUIDisplayTicket, lost: Bool) async throws -> [String: Any] {
        let model = owner.presentation
        let display = try need(model.f11ActionDisplay(attachment: attachment), "Revised native display authority")
        let workspace = work.appendingPathComponent("workspace")
        let bytes = Data(GuestUIFieldLogNoteFixture.edited.utf8)
        let before = try read(workspace, "workspace.json")
        let save = F11HostActions(model: model, display: display, repository: repository, action: .save)
        if lost {
            model.detachNativeAttachment(attachment)
            let refusal = try await save.perform(.save, from: model, frame: display, workspace: NoteStorage.workspaceID,
                                                 expectedRevision: 1, note: bytes)
            try check(refusal == nil && save.transactionAttempts == 0
                && before == read(workspace, "workspace.json"), "Lost display reached persistence")
            return ["refused": "detached revision 2 display", "transactionAttempts": 0]
        }

        struct Case {
            var name: String
            var action: Action = .save
            var owner: GuestUIPresentation
            var frame: CapabilityGuestUIDisplayTicket
            var workspace: UUID = NoteStorage.workspaceID
            var revision: UInt64 = 1
            var bytes: Data
        }
        let changed = Data(GuestUIFieldLogNoteFixture.edited.precomposedStringWithCanonicalMapping.utf8)
        try check(changed != bytes, "Wrong-bytes control must be canonically equivalent but byte-distinct")
        let wrongAttachment = CapabilityGuestUIDisplayTicket(binding: display.binding,
            attachment: .init(), ticket: display.ticket)
        let cases = [
            Case(name: "stale frame", owner: model, frame: initial, bytes: bytes),
            Case(name: "wrong owner", owner: GuestUIPresentation(), frame: display, bytes: bytes),
            Case(name: "wrong attachment", owner: model, frame: wrongAttachment, bytes: bytes),
            Case(name: "wrong workspace", owner: model, frame: display, workspace: UUID(), bytes: bytes),
            Case(name: "wrong revision", owner: model, frame: display, revision: 2, bytes: bytes),
            Case(name: "wrong action", action: .commit, owner: model, frame: display, bytes: bytes),
            Case(name: "wrong UTF-8", owner: model, frame: display, bytes: changed),
        ]
        for test in cases {
            let refusal = try await save.perform(test.action, from: test.owner, frame: test.frame,
                workspace: test.workspace, expectedRevision: test.revision, note: test.bytes)
            try check(refusal == nil && save.transactionAttempts == 0
                && before == read(workspace, "workspace.json"), "Negative control wrote: \(test.name)")
        }

        let saved = try await save.perform(.save, from: model, frame: display, workspace: NoteStorage.workspaceID,
                                          expectedRevision: 1, note: bytes)
        try check(saved?.revision == 2 && save.transactionAttempts == 1, "Save did not advance to revision 2")
        let savedBytes = try read(workspace, "workspace.json")
        let duplicateSave = try await save.perform(.save, from: model, frame: display,
            workspace: NoteStorage.workspaceID, expectedRevision: 1, note: bytes)
        try check(duplicateSave == nil && save.transactionAttempts == 1
            && savedBytes == read(workspace, "workspace.json"), "Repeated Save touched persistence")
        try savedBytes.write(to: work.appendingPathComponent("saved.json"), options: .withoutOverwriting)

        await repository.close()
        let reopened = try WorkspaceRepository(directory: workspace)
        let result: Result<[String: Any], Error>
        do {
            let restored = await reopened.snapshot()
            let draft = try need(restored.drafts.first { $0.id == restored.restoration.openDraftID }, "Cold draft")
            try check(restored.id == NoteStorage.workspaceID && restored.revision == 2
                && draft.id == NoteStorage.draftID && draft.projectID == NoteStorage.projectID
                && Data(draft.note.utf8) == bytes && savedBytes == read(workspace, "workspace.json"),
                "Cold restore differed from saved draft")
            do {
                _ = try await reopened.transact(expectedRevision: 1) { _ in
                    throw UpdateError("f11.unexpected", "Stale revision reached mutation")
                }
                throw UpdateError("f11.unexpected", "Stale revision was accepted")
            } catch FieldLogError.staleRevision {}
            try check(savedBytes == read(workspace, "workspace.json"), "Stale repository revision wrote")

            let commit = F11HostActions(model: model, display: display, repository: reopened, action: .commit)
            let committed = try await commit.perform(.commit, from: model, frame: display,
                workspace: NoteStorage.workspaceID, expectedRevision: 2, note: bytes)
            try check(committed?.revision == 3 && commit.transactionAttempts == 1, "Commit did not advance to revision 3")
            let committedBytes = try read(workspace, "workspace.json")
            let duplicate = try await commit.perform(.commit, from: model, frame: display,
                workspace: NoteStorage.workspaceID, expectedRevision: 2, note: bytes)
            try check(duplicate == nil && commit.transactionAttempts == 1
                && committedBytes == read(workspace, "workspace.json"), "Repeated Commit touched persistence")
            result = .success([
                "negativeControls": cases.map(\.name) + ["repeat Save", "stale repository revision", "repeat Commit"],
                "transactions": [Action.save.rawValue: save.transactionAttempts,
                                 Action.commit.rawValue: commit.transactionAttempts],
                "frameRevision": display.ticket.revision, "frameSerial": display.ticket.frameSerial,
                "coldDraftRevision": restored.revision, "committedRevision": 3,
                "coldDraftSHA256": ReleaseVerifier.sha256(savedBytes),
                "commitSHA256": ReleaseVerifier.sha256(committedBytes),
            ])
        } catch { result = .failure(error) }
        await reopened.close()
        return try result.get()
    }

    static func coldCommitted(_ directory: URL) async throws {
        let repository = try WorkspaceRepository(directory: directory)
        let restored = await repository.snapshot()
        await repository.close()
        let entry = try need(restored.entries.first { $0.id == NoteStorage.draftID }, "Cold committed entry")
        let event = try need(restored.outbox.last, "Cold committed event")
        try check(restored.id == NoteStorage.workspaceID && restored.revision == 3
            && restored.restoration.openDraftID == nil && entry.projectID == NoteStorage.projectID
            && entry.note.utf8.elementsEqual(GuestUIFieldLogNoteFixture.edited.utf8)
            && event.recordID == entry.id && event.kind == .entrySaved && event.revision == 3,
            "Cold committed entry or linked event differed")
        print(ReleaseVerifier.sha256(try read(directory, "workspace.json")))
    }
}
