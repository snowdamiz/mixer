import FieldLogInstalledGuest
import FieldLogStorage
import Foundation
import MixerCapabilities
import MixerUI

@main @MainActor struct EditorBindingProof {
    struct Failure: Error, CustomStringConvertible { let description: String }

    static func main() async throws {
        let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
        let repository = try WorkspaceRepository(directory: root)
        let editor = try await ProjectPresentation(repository: repository)
        let get = KVGetArguments(namespace: "fieldlog-task-v1", key: "selected-draft")

        try send(editor, "workspace.entries")
        do {
            _ = try await editor.attachSignedDraft()
            throw Failure(description: "Unsaved editor attached")
        } catch PublicHostError.action {}

        let first = try await save(editor, title: "First draft")
        let firstLease = try await editor.attachSignedDraft()
        let firstRead = try await firstLease.get(get)
        try check(firstRead.found, "Normal selected saved draft was not visible")
        try send(editor, "entry.new")
        try await denied { _ = try await firstLease.get(get) }

        let second = try await save(editor, title: "Second draft")
        let project = try require(editor.workspace.projects.first).id
        let binder = SelectedDraftBinding()
        binder.select(projectID: project, draftID: second)
        try await denied { _ = try await binder.attach(repository: repository, projectID: project, draftID: first) }
        try await denied { _ = try await binder.attach(repository: repository, projectID: UUID(), draftID: second) }
        let secondLease = try await editor.attachSignedDraft()
        let selected = try await secondLease.get(get)
        let raw = try require(Data(base64Encoded: selected.valueBase64))
        try check(raw.count == 9 && raw.last == 3, "Initial selected draft flags differ")
        var body = Data(raw.prefix(8))
        body.append(1)
        let mutation = KVPutArguments(namespace: "fieldlog-task-v1", key: "selected-draft",
                                      valueBase64: body.base64EncodedString())
        let committed = try await secondLease.put(mutation, maximumTotalBytes: 9, maximumEntries: 1)
        try check(committed.committed, "Optional follow-up did not commit")
        editor.detachSignedDraft()
        try await denied { _ = try await secondLease.put(mutation, maximumTotalBytes: 9, maximumEntries: 1) }
        try await editor.reloadChecklist()

        try send(editor, "entry." + second.uuidString.lowercased() + ".note", .textChange, .string("Ordinary offline edit"))
        try send(editor, "entry.saveDraft")
        try await editor.waitForSave()
        let saved = try await repository.readCommittedSnapshot()
        let unchanged = try require(saved.drafts.first { $0.id == first })
        let changed = try require(saved.drafts.first { $0.id == second })
        try check(unchanged.title == "First draft" && unchanged.followUpRequired == nil, "Wrong draft changed")
        try check(changed.note == "Ordinary offline edit" && changed.followUpRequired == true, "Ordinary save lost optional data")

        let again = try await editor.attachSignedDraft()
        try send(editor, "draft." + first.uuidString.lowercased())
        try await denied { _ = try await again.get(get) }
        let reselected = try await editor.attachSignedDraft()
        try await denied {
            _ = try await reselected.get(.init(namespace: "fieldlog-task-v1", key: second.uuidString))
        }
        try send(editor, "workspace.tasks")
        try await denied { _ = try await reselected.get(get) }

        try send(editor, "workspace.entries")
        let closing = try await editor.attachSignedDraft()
        await editor.close()
        try await denied { _ = try await closing.get(get) }
        let reopened = try WorkspaceRepository(directory: root)
        let cold = try await ProjectPresentation(repository: reopened)
        if cold.entryState?.draft.id != second {
            try send(cold, "workspace.entries")
            try send(cold, "draft." + second.uuidString.lowercased())
        }
        let coldLease = try await cold.attachSignedDraft()
        let readback = try await coldLease.get(get)
        let coldBytes = try require(Data(base64Encoded: readback.valueBase64))
        try check(coldBytes.last == 11, "Cold selection lost optional data")
        await cold.close()
        print("PASS ordinary navigation, wrong project/draft/key denial, stale lease revocation, selected write, offline save and cold readback")
    }

    private static func save(_ editor: ProjectPresentation, title: String) async throws -> UUID {
        let id = try require(editor.entryState).draft.id
        try send(editor, "entry." + id.uuidString.lowercased() + ".title", .textChange, .string(title))
        try send(editor, "entry.saveDraft")
        try await editor.waitForSave()
        try check(editor.workspace.drafts.contains { $0.id == id }, "Ordinary draft save failed")
        return id
    }

    private static func send(_ editor: ProjectPresentation, _ id: String, _ kind: UIEventKind = .activate,
                             _ value: UIValue = .null) throws {
        let snapshot = editor.snapshot
        let identity = try require(snapshot.identity(for: id))
        try editor.send(.init(revision: snapshot.document.revision, identity: identity, event: kind, value: value))
    }

    private static func require<T>(_ value: T?) throws -> T {
        guard let value else { throw Failure(description: "Expected value") }
        return value
    }

    private static func check(_ condition: Bool, _ message: String) throws {
        guard condition else { throw Failure(description: message) }
    }

    private static func denied(_ operation: () async throws -> Void) async throws {
        do {
            try await operation()
            throw Failure(description: "Refusal required")
        } catch CapabilityFailure.permissionDenied {}
    }
}
