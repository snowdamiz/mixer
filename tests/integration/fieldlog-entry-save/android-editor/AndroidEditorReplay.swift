import FieldLogFeatures
import FieldLogHostTest
import FieldLogInstalledGuest
import FieldLogModels
import FieldLogStorage
import Foundation
import MixerUI
import MixerUpdates
import os

@MainActor enum AndroidEditorReplay {
    static let bundleID = "dev.mixer.fieldlog.saveddraft"
    private static let projectID = UUID(uuidString: "0576B7F3-9350-4AE6-8F1C-F219CE5CF4E3")!
    private static let draftID = UUID(uuidString: "D8E808D4-ACBE-4558-91C6-FAAB517C8DF3")!
    private static let otherID = UUID(uuidString: "19CBBA4C-3187-4A01-A348-97A2AB8DD47D")!
    private static let installation = UUID(uuidString: "5C409E93-88BD-41C1-B2BD-D589CCA0A4A0")!
    private static let title = "Inspect e\u{301} valve"
    private static let note = "Keep e\u{301}\r\nexactly. 🛠"
    private static let validDate = "2023-11-14T22:14:21Z"

    private enum Scenario: String, CaseIterable {
        case valid, ioFailure, blank, invalidDate, staleBeforeOpen, stale, editedAfterOpen

        var expectedFrame: String {
            switch self {
            case .valid: "Committed once"
            case .ioFailure: "Commit refused"
            case .blank: "Entry title can't be empty."
            case .invalidDate: "Choose a valid entry date."
            case .staleBeforeOpen, .stale, .editedAfterOpen: "Selected draft unavailable."
            }
        }
    }

    static func run(material: URL, directory: URL) async throws {
        try Host.check(mxish_start() == 0, "Host witness transport failed")
        for scenario in Scenario.allCases {
            do { try await run(scenario, material: material, root: directory.appendingPathComponent(scenario.rawValue)) }
            catch { throw TrialError("\(scenario.rawValue) editor replay: \(error)") }
        }
        try Host.check(mxish_destructors() == Scenario.allCases.count && mxish_live_allocations() == 0,
                       "The installed owners did not retire")
        print("editorOwners=\(mxish_destructors()) liveTransportAllocations=0")
    }

    static func sign(fixtures: URL, guests: URL, material: URL, archive: String, binary: String, sourceCommit: String) throws {
        try sign(fixtures: fixtures, guests: guests, material: material, archive: archive, binary: binary,
                 sourceCommit: sourceCommit, maximumRequests: 2, reservationBytes: 2_097_152)
        for (name, slots, budget) in [("one-slot", 1, 2_097_152), ("short-reservation", 2, 2_097_151)] {
            let control = material.deletingLastPathComponent().appendingPathComponent(name)
            try FileManager.default.createDirectory(at: control, withIntermediateDirectories: false)
            try sign(fixtures: fixtures, guests: guests, material: control, archive: archive, binary: binary,
                     sourceCommit: sourceCommit, maximumRequests: UInt64(slots), reservationBytes: UInt64(budget))
        }
    }

    private static func sign(fixtures: URL, guests: URL, material: URL, archive: String, binary: String,
                             sourceCommit: String, maximumRequests: UInt64, reservationBytes: UInt64) throws {
        try signReleases(fixtures: fixtures, guests: guests, output: material, archive: archive, binary: binary,
            variants: ["editor-commit"], deferredStartup: false,
            limits: (maximumRequests, reservationBytes), storageOnly: true, sourceCommit: sourceCommit)
        let files = FileManager.default
        for (old, new) in [("editor-commit.wasm", "entry-commit.wasm"), ("editor-commit.manifest.json", "entry-commit.manifest.json"),
                           ("sequence-1.assignment.json", "entry-commit.assignment.json")] {
            try files.moveItem(at: material.appendingPathComponent(old), to: material.appendingPathComponent(new))
        }
        try Data("fieldlog-entry-commit-v1\n".utf8).write(to: material.appendingPathComponent("entry-commit-v1.txt"), options: .withoutOverwriting)
        try Data("12345\n".utf8).write(to: material.appendingPathComponent("port.txt"), options: .withoutOverwriting)
    }

    private static func run(_ scenario: Scenario, material: URL, root: URL) async throws {
        let directory = root.appendingPathComponent("workspace")
        let file = directory.appendingPathComponent("workspace.json")
        let original = EntryDraft(id: draftID, projectID: projectID, title: "Saved draft",
                                  note: "Saved note", occurredAt: Date(timeIntervalSince1970: 1_700_000_000))
        let other = EntryDraft(id: otherID, projectID: projectID, title: "Previously restored draft")
        let faultHits = OSAllocatedUnfairLock<Int?>(initialState: nil)
        let repository = try WorkspaceRepository(directory: directory) { point in
            guard point == "before_write", faultHits.withLock({ hits in
                guard let count = hits else { return false }
                hits = count + 1
                return true
            }) else { return }
            throw FieldLogError.storage("Injected precommit storage failure with private details")
        }
        let seeded = try await repository.transact(expectedRevision: 0) { workspace in
            try workspace.createProject(id: original.projectID, title: "North plant", site: "Pump 4")
            try workspace.saveDraft(original)
            try workspace.saveDraft(other)
            workspace.restoration.selectedProjectID = original.projectID
            workspace.restoration.openDraftID = other.id
        }
        let editor = try await ProjectPresentation(repository: repository)
        do {
            try await exercise(scenario, editor: editor, repository: repository, seeded: seeded, original: original,
                               other: other, material: material, root: root, file: file, faultHits: faultHits)
        } catch {
            await editor.close()
            throw error
        }
    }

    private static func exercise(_ scenario: Scenario, editor: ProjectPresentation, repository: WorkspaceRepository,
                                 seeded: Workspace, original: EntryDraft, other: EntryDraft,
                                 material: URL, root: URL, file: URL, faultHits: OSAllocatedUnfairLock<Int?>) async throws {
        try Host.check(editor.entryState?.draft.id == otherID, "The editor did not restore the other draft")
        do { try send(editor, "draft." + draftID.uuidString.lowercased()) }
        catch { throw TrialError("select draft: \(error)") }
        // All values and the open action are routed from one native snapshot.
        let snapshot = editor.snapshot
        let edits = [
            try event(snapshot, field("title"), .textChange, .string(scenario == .blank ? " \t " : title)),
            try event(snapshot, field("note"), .textChange, .string(note)),
            try event(snapshot, field("date"), .textChange, .string(scenario == .invalidDate ? "2023-02-29T00:00:00Z" : validDate)),
        ]
        if scenario == .staleBeforeOpen {
            try editor.sendBatch(edits, from: snapshot)
            let updated = try await repository.transact(expectedRevision: 1) { $0.projects[0].site = "Updated before open" }
            try await editor.reloadChecklist()
            try Host.check(editor.workspace.revision == updated.revision && editor.entryState?.draft.note.utf8.elementsEqual(note.utf8) == true,
                           "Workspace refresh did not retain the stale editor text")
            try send(editor, SignedEntryCommit.editorAction)
        } else {
            try editor.sendBatch(edits + [event(snapshot, SignedEntryCommit.editorAction)], from: snapshot)
        }
        try Host.check(editor.takeSignedEntryCommitRequest() && !editor.takeSignedEntryCommitRequest(), "Editor request was absent or reusable")

        let missing = material.appendingPathComponent("missing")
        do {
            _ = try await editor.openSignedEntryCommit(material: missing, directory: root.appendingPathComponent("rejected"),
                bundleID: bundleID, installation: installation)
            throw TrialError("Uninstalled fixture opened")
        } catch let error as TrialError {
            throw error
        } catch {
            do { try send(editor, SignedEntryCommit.editorAction) }
            catch { throw TrialError("retry editor action: \(error)") }
            try Host.check(editor.takeSignedEntryCommitRequest(), "Could not retry the named editor action")
        }
        if scenario == .valid {
            for name in ["one-slot", "short-reservation"] {
                let control = material.deletingLastPathComponent().appendingPathComponent(name)
                do {
                    let wrong = try await editor.openSignedEntryCommit(material: control, directory: root.appendingPathComponent(name),
                        bundleID: bundleID, installation: installation)
                    _ = await wrong.close()
                    throw TrialError("Installed fixture accepted \(name)")
                } catch let failure as UpdateError {
                    try Host.check(failure.code == "installed.capability.application_storage_commit_limits",
                                   "Unexpected installed limits refusal \(failure.code)")
                }
                try send(editor, SignedEntryCommit.editorAction)
                try Host.check(editor.takeSignedEntryCommitRequest(), "Could not retry after the limits refusal")
                print("installedLimitControl=\(name) refused=true")
            }
        }
        let owner: FieldLogSignedTask
        do {
            owner = try await editor.openSignedEntryCommit(material: material, directory: root.appendingPathComponent("installed"),
                bundleID: bundleID, installation: installation)
        } catch { throw TrialError("open installed fixture: \(error)") }
        do {
            let launch = try await owner.start()
            try Host.check(launch == "Signed entry commit", "Unexpected installed start")
            let facade = owner.hostFacade
            try await Host.eventually("No signed editor frame") { mxfield_recorded_probe(facade) > 0 }
            try Host.check(try Host.frame(facade) == ["Ready to commit", "Commit"], "The named guest Commit was absent")
            try await Host.witness(facade, command: 10)
            if scenario == .stale {
                _ = try await repository.transact(expectedRevision: 1) { $0.projects[0].site = "Updated separately" }
            }
            if scenario == .editedAfterOpen {
                try send(editor, field("note"), .textChange, .string("A newer native edit"))
            }
            let before = try Data(contentsOf: file)
            let workspacePath = file.deletingLastPathComponent().path
            let beforeFiles = try FileManager.default.contentsOfDirectory(atPath: workspacePath).sorted()
            if scenario == .ioFailure { faultHits.withLock { $0 = 0 } }
            try await Host.tap(facade, expected: [scenario.expectedFrame])

            // Done follows the observed frame, then joins the owner and retires the host registration.
            let destructors = mxish_destructors()
            editor.detachSignedEntryCommit()
            try Host.check(await owner.close(), "Installed owner did not settle")
            try Host.check(mxish_destructors() == destructors + 1 && mxish_live_allocations() == 0
                && mxish_last_id(facade, 1) == 0, "Host registration survived joined retirement")

            let saved: Workspace
            if scenario == .ioFailure {
                // A repository with an interrupted write requires a cold reopen.
                saved = await repository.snapshot()
                try Host.check(faultHits.withLock { $0 } == 1 && saved == seeded
                    && FileManager.default.contentsOfDirectory(atPath: workspacePath).sorted() == beforeFiles,
                    "The injected write failure did not preserve the workspace")
            } else {
                try await editor.reloadChecklist()
                saved = try await repository.readCommittedSnapshot()
            }
            let commits = saved.outbox.filter { $0.kind == .entrySaved }
            if scenario == .valid {
                guard let entry = editor.entryState?.committed else { throw TrialError("The native editor did not show the saved entry") }
                try Host.check(entry.id == draftID && entry.projectID == projectID
                    && entry.title.utf8.elementsEqual(title.utf8) && entry.note.utf8.elementsEqual(note.utf8)
                    && entry.occurredAt == Date(timeIntervalSince1970: 1_700_000_061)
                    && saved.entries == [entry] && saved.drafts == [other] && saved.revision == 2
                    && commits.count == 1 && commits[0].recordID == draftID && Array(saved.outbox.dropLast()) == seeded.outbox,
                    "The guest did not commit the exact native intent once")
            } else {
                try Host.check(saved.drafts.count == 2 && saved.drafts.contains(original) && saved.drafts.contains(other)
                    && saved.entries.isEmpty && saved.outbox == seeded.outbox && Data(contentsOf: file) == before,
                    "A refused guest action changed the repository")
            }
            if scenario == .invalidDate || scenario == .editedAfterOpen {
                if scenario == .invalidDate { try send(editor, field("date"), .textChange, .string(validDate)) }
                try send(editor, "entry.saveDraft")
                try await editor.waitForSave()
                let native = try await repository.readCommittedSnapshot()
                let nativeNote = scenario == .editedAfterOpen ? "A newer native edit" : note
                try Host.check(native.drafts.first(where: { $0.id == draftID })?.note.utf8.elementsEqual(nativeNote.utf8) == true,
                               "The normal native draft save lost the editor's current text")
            }
            let bytes = try Data(contentsOf: file)
            let final = scenario == .ioFailure ? saved : try await repository.readCommittedSnapshot()
            await editor.close()
            let cold = try WorkspaceRepository(directory: file.deletingLastPathComponent())
            let reopened = try? await cold.readCommittedSnapshot()
            await cold.close()
            try Host.check(reopened == final && Data(contentsOf: file) == bytes, "Cold reopen changed the workspace")
            if scenario == .ioFailure {
                print("editorWriteFault=before_write hits=1 durableWrites=0 outboxDelta=0 privateDetailsDisplayed=false doneAfterFrame=true joinedRetirement=true hostRegistrationRemoved=true")
            }
            print("editorCase=\(scenario.rawValue) guest=\(scenario.expectedFrame) revision=\(saved.revision) entrySaved=\(commits.count) coldReopen=true")
        } catch {
            editor.detachSignedEntryCommit()
            let closed = await owner.close()
            throw TrialError("installed owner closed=\(closed): \(error)")
        }
    }

    private static func field(_ name: String) -> String { "entry." + draftID.uuidString.lowercased() + "." + name }

    private static func send(_ editor: ProjectPresentation, _ id: String,
                             _ kind: UIEventKind = .activate, _ value: UIValue = .null) throws {
        try editor.send(event(editor.snapshot, id, kind, value))
    }

    private static func event(_ snapshot: UIRenderSnapshot, _ id: String,
                              _ kind: UIEventKind = .activate, _ value: UIValue = .null) throws -> UIEventEnvelope {
        guard let identity = snapshot.identity(for: id) else { throw TrialError("Missing editor action \(id)") }
        return .init(revision: snapshot.document.revision, identity: identity, event: kind, value: value)
    }
}
