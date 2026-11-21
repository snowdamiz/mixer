import Dispatch
import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilities
@testable import MixerCapabilityActivation
@testable import MixerUI
import os

private struct ReplayFailure: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

@MainActor enum AppleEditorReplay {
    private static let bundleID = "dev.mixer.fieldlog"

    private enum Scenario: String, CaseIterable {
        case success, blank, stale, revoked, declined, doneBeforeCommit
        case bothProvisioned, optionalUnapplied, legacyDone, legacyRetry, joinedDone, joinedDoneSelectionChanged
        case legacyExplicitRetry, legacyOptionalConflict, legacyBooleanConflict
        case ordinaryClose, selectionChangedAfterRetirement, wrongAction
        case authorityReplay, authorityNoPoll

        var needsTools: Bool { self == .bothProvisioned || self == .optionalUnapplied }
        var legacyFollowUp: (entry: Bool?, draft: Bool?)? {
            switch self {
            case .legacyDone, .legacyRetry, .selectionChangedAfterRetirement: (nil, nil)
            case .legacyExplicitRetry: (true, true)
            case .legacyOptionalConflict: (nil, false)
            case .legacyBooleanConflict: (false, true)
            default: nil
            }
        }
        var isLegacyConflict: Bool { self == .legacyOptionalConflict || self == .legacyBooleanConflict }
        var needsAuthorityMaterial: Bool { self == .authorityReplay || self == .authorityNoPoll }
        var joinsAdmittedWrite: Bool { self == .joinedDone || self == .joinedDoneSelectionChanged }

        var frame: String? {
            switch self {
            case .success, .bothProvisioned, .legacyRetry, .legacyExplicitRetry,
                 .selectionChangedAfterRetirement, .authorityReplay: "Committed once"
            case .blank: "Entry title can't be empty."
            case .stale, .revoked: "Selected draft unavailable."
            case .declined, .authorityNoPoll: "Commit refused"
            case .doneBeforeCommit, .optionalUnapplied, .legacyDone, .joinedDone, .joinedDoneSelectionChanged,
                 .legacyOptionalConflict, .legacyBooleanConflict, .ordinaryClose, .wrongAction: nil
            }
        }
    }

    static func run(material: URL, root: URL, scenarioName: String?, draftTools: URL?) async throws {
        let scenarios: [Scenario]
        if let scenarioName, scenarioName != "all" {
            guard let scenario = Scenario(rawValue: scenarioName) else {
                throw ReplayFailure("Unknown scenario: \(scenarioName)")
            }
            guard !scenario.needsTools || draftTools != nil else {
                throw ReplayFailure("This scenario requires signed draft-tools material")
            }
            scenarios = [scenario]
        } else {
            scenarios = Scenario.allCases.filter { !$0.needsAuthorityMaterial && (!$0.needsTools || draftTools != nil) }
        }
        for scenario in scenarios {
            do {
                try await exercise(scenario, material: material, tools: draftTools,
                                   root: root.appendingPathComponent(scenario.rawValue))
            } catch {
                throw ReplayFailure("\(scenario.rawValue): \(error)")
            }
        }
    }

    private final class WriteBarrier: Sendable {
        private let writes = OSAllocatedUnfairLock(initialState: 0)
        let release = DispatchSemaphore(value: 0)

        var count: Int { writes.withLock { $0 } }

        func hold() throws {
            let first = writes.withLock { count in
                count += 1
                return count == 1
            }
            if first, release.wait(timeout: .now() + .seconds(10)) != .success {
                throw ReplayFailure("The admitted repository write was never released")
            }
        }
    }

    private static func exercise(_ scenario: Scenario, material: URL, tools: URL?, root: URL) async throws {
        let fault = OSAllocatedUnfairLock<Int?>(initialState: nil)
        let barrier = WriteBarrier()
        let holdAdmittedWrite = OSAllocatedUnfairLock(initialState: false)
        let repositoryFault: WorkspaceRepository.Fault = { point in
            guard point == "before_write" else { return }
            if holdAdmittedWrite.withLock({ armed in
                let hold = armed
                armed = false
                return hold
            }) { try barrier.hold() }
            if fault.withLock({ hits in
                guard let count = hits else { return false }
                hits = count + 1
                return true
            }) {
                throw FieldLogError.storage("Private disk details")
            }
        }
        let initial = try WorkspaceRepository(directory: root, fault: repositoryFault)
        let project = UUID()
        let date = Date(timeIntervalSince1970: 1_700_000_061)
        let other = EntryDraft(projectID: project, title: "Other draft", note: "Keep separate", occurredAt: date, updatedAt: date)
        let draft = EntryDraft(projectID: project, title: scenario == .blank ? " \t " : "Inspect e\u{301} valve",
                               note: "Keep e\u{301}\r\nexactly. 🛠", occurredAt: date, updatedAt: date)
        _ = try await initial.transact(expectedRevision: 0) { workspace in
            try workspace.createProject(id: project, title: "North plant", site: "Pump 4", now: date)
            try workspace.saveDraft(draft)
            try workspace.saveDraft(other)
            workspace.restoration.selectedProjectID = project
            workspace.restoration.openDraftID = draft.id
        }
        let repository: WorkspaceRepository
        let snapshotPath = root.appendingPathComponent("workspace.json")
        var seeded = try await initial.readCommittedSnapshot()
        if let followUp = scenario.legacyFollowUp {
            // A snapshot written by an older app can contain both the original draft and its entry.
            var legacy = seeded
            guard let draftIndex = legacy.drafts.firstIndex(where: { $0.id == draft.id }) else {
                throw ReplayFailure("Missing draft for legacy pair")
            }
            legacy.drafts[draftIndex].followUpRequired = followUp.entry
            try legacy.commitDraft(draft.id, now: date)
            legacy.revision += 1
            legacy.drafts = seeded.drafts
            legacy.drafts[draftIndex].followUpRequired = followUp.draft
            legacy.restoration = seeded.restoration
            await initial.close()
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
            try encoder.encode(legacy).write(to: snapshotPath, options: .atomic)
            repository = try WorkspaceRepository(directory: root, fault: repositoryFault)
            seeded = try await repository.readCommittedSnapshot()
        } else {
            repository = initial
            if !scenario.needsTools && scenario != .ordinaryClose {
                let selection = try await repository.selectSavedDraft(projectID: project, draftID: draft.id)
                seeded = try await repository.updateSelectedDraftFollowUp(selection, expectedRevision: 1) { $0 = true }
            }
        }
        let model = WorkspaceModel(repository: repository)
        await model.open()
        model.selectDraftEditor(draft)
        let closeEditor = ordinarySheetDismissal(model)
        if scenario == .ordinaryClose {
            closeEditor()
            await model.flush()
            await repository.close()
            let cold = try WorkspaceRepository(directory: root)
            let reopened = try await cold.readCommittedSnapshot()
            await cold.close()
            var expected = seeded
            expected.revision += 1
            expected.restoration.openDraftID = nil
            try check(reopened == expected, "Ordinary dismissal did not clear exactly its own restoration")
            print("case=ordinaryClose revision=\(seeded.revision)->\(reopened.revision) restorationCleared=true coldReopen=true")
            return
        }
        var editorDraft = draft
        if scenario.needsTools, let tools {
            if scenario == .bothProvisioned {
                editorDraft.title = "  Revised e\u{301} valve  "
                editorDraft.note = "Operator e\u{301}\r\nedit 🛠"
                let retained = await model.keepDraft(editorDraft)
                try check(retained, "The editor did not save its changes before the optional tool opened")
                seeded = try await repository.readCommittedSnapshot()
            }
            if scenario == .optionalUnapplied {
                editorDraft.note = String(repeating: "x", count: 100_001)
                await model.keepDraft(editorDraft)
                try check(model.unsavedDrafts[draft.id]?.note == editorDraft.note, "Expected retained editor input")
            }
            seeded = try await exerciseDraftTools(tools, model: model, draft: draft, root: root, initial: seeded,
                                                  repository: repository)
            if scenario == .optionalUnapplied {
                try check(model.unsavedDrafts[draft.id]?.note == editorDraft.note, "Closing tools discarded editor input")
                try check(model.saveError != nil, "Closing tools discarded the unsaved draft error")
                let other = try await model.attachDraftGuest(projectID: draft.projectID, draftID: draft.id)
                _ = await model.finishDraftGuest(other, owner: nil)
                await repository.close()
                print("case=optionalUnapplied retained=true revision=\(seeded.revision) selectionPreserved=true")
                return
            }
        }
        let initialBytes = try Data(contentsOf: snapshotPath)

        if scenario == .success {
            try await requireDenied(model, draft: other)
            var unstaged = draft
            unstaged.title = "Unsaved editor value"
            try await requireDenied(model, draft: unstaged)
            let access = try await model.attachDraftCommit(draft)
            do {
                _ = try await InstalledDraftGuest.open(materials: material, workspaceDirectory: root,
                                                       storage: access, bundleID: "dev.mixer.wrong")
                throw ReplayFailure("Wrong app identity opened")
            } catch CapabilityFailure.permissionDenied {}
            let refused = await model.finishDraftGuest(access, owner: nil)
            try check(refused == .closed, "Wrong app identity changed the editor")
            try check(try Data(contentsOf: snapshotPath) == initialBytes, "Denied open changed workspace bytes")
            print("attachControls=wrong-selection,unsaved-editor,wrong-bundle denied=true")
        }

        let access = try await model.attachDraftCommit(editorDraft)
        let slots = CapabilityAttemptReservation.occupiedSlots
        let owner: CapabilityGuestUIRuntime
        do {
            owner = try await InstalledDraftGuest.open(materials: material, workspaceDirectory: root,
                                                       storage: access, bundleID: bundleID)
        } catch {
            _ = await model.finishDraftGuest(access, owner: nil)
            throw error
        }
        let baseline: Data
        let closed: WorkspaceModel.DraftGuestClose
        var resultFrame: String?
        do {
            try await InstalledDraftGuest.stage(1, kind: .entryCommit, in: material, on: owner)
            let started = try await owner.start()
            try check(started.phase == .provisionalGuest, "Signed guest did not start")
            try await eventually("Apple Commit control did not become ready") {
                owner.presentation.state == .displaying(revision: 1)
            }
            let presentation = owner.presentation
            guard let attachment = presentation.claimNativeAttachment(), let host = presentation.renderHost,
                  let identity = host.snapshot.identity(for: "toggle")
            else { throw ReplayFailure("Missing Apple Commit control") }
            let event = try host.route(UIEventEnvelope(revision: 1, identity: identity, event: .activate))
            let action = presentation.actionHandler(host: host, attachment: attachment)
            try await eventually("Apple Commit control did not accept input") { presentation.inputEnabled }

            if scenario == .stale {
                _ = try await repository.transact(expectedRevision: seeded.revision) { $0.projects[0].site = "New revision" }
            }
            if scenario == .revoked { model.selectDraftEditor(other) }
            if scenario == .declined { fault.withLock { $0 = 0 } }
            baseline = try Data(contentsOf: snapshotPath)
            if scenario == .wrongAction {
                try check(event.actionID == "entry.commit" && event.nodeID == "toggle" && event.event == .activate,
                          "The current UI did not route the exact entry commit action")
                let wrong: [RoutedUIAction] = [
                    .init(revision: 1, nodeID: "toggle", actionID: "entry.check", event: .activate, value: .null),
                    .init(revision: 1, nodeID: "status", actionID: "entry.commit", event: .activate, value: .null),
                    .init(revision: 2, nodeID: "toggle", actionID: "entry.commit", event: .activate, value: .null),
                    .init(revision: 1, nodeID: "toggle", actionID: "entry.commit", event: .submit, value: .null),
                    .init(revision: 1, nodeID: "toggle", actionID: "entry.commit", event: .activate, value: .bool(true)),
                ]
                for alternative in wrong {
                    action(alternative)
                    try check(presentation.inputEnabled && presentation.state == .displaying(revision: 1),
                              "A wrong action obtained the current presentation's input authority")
                }
                print("actionControls=wrong-action,wrong-node,wrong-revision,wrong-event,wrong-value denied=true")
            }
            if scenario.frame != nil || scenario.isLegacyConflict {
                action(event)
                do {
                    try await eventually("Missing Apple result frame") {
                        presentation.state == .displaying(revision: 2)
                    }
                } catch {
                    let failed = await owner.recoverySnapshot()
                    throw ReplayFailure("\(error), presentation=\(presentation.state), activation=\(failed.activation)")
                }
                if case .string(let message)? = presentation.renderHost?.snapshot.document.root.children.first?.properties["text"] {
                    resultFrame = message
                }
                if let frame = scenario.frame {
                    try check(resultFrame == frame, "Apple result frame was \(resultFrame ?? "missing"), expected \(frame)")
                }
                try check(model.workspace == seeded, "The editor refreshed before Done retired its owner")
            }

            if scenario.joinsAdmittedWrite {
                holdAdmittedWrite.withLock { $0 = true }
                closed = try await joinDoneDuringWrite(
                    action: { action(event) }, barrier: barrier, model: model,
                    access: access, owner: owner, newSelection: scenario == .joinedDoneSelectionChanged ? other : nil)
                try check(barrier.count == 1, "Joined Done attempted more than one write")
            } else {
                let closing = Task { await model.finishDraftGuest(access, owner: owner) }
                closing.cancel()
                closed = await closing.value
            }
            let retired = await owner.recoverySnapshot()
            try check(owner.ownerRetired && retired.closed && !retired.activation.cleanupPending
                && presentation.state == .stopped && CapabilityAttemptReservation.occupiedSlots == slots,
                "Done retirement result=\(closed) ownerRetired=\(owner.ownerRetired) closed=\(retired.closed) " +
                "cleanupPending=\(retired.activation.cleanupPending) presentation=\(presentation.state) " +
                "slots=\(CapabilityAttemptReservation.occupiedSlots) expectedSlots=\(slots)")
            action(event)
            presentation.detachNativeAttachment(attachment)
        } catch {
            _ = await model.finishDraftGuest(access, owner: owner)
            throw error
        }

        let afterGuest = try Data(contentsOf: snapshotPath)
        var expectedLatest: Workspace?
        if scenario == .selectionChangedAfterRetirement {
            // Reopen the same record with a fresh presentation generation before the old callback.
            model.selectDraftEditor(draft)
            expectedLatest = seeded
        }
        let editorDismissed = finishOrdinaryEditor(closed, model: model, closeSheet: closeEditor)
        if expectedLatest != nil {
            #if !FIELDLOG_DISMISSAL_BASELINE
            closeEditor()
            try check(model.draftEditor?.draft.id == draft.id, "A stale ordinary callback released the latest editor")
            #endif
        }
        await model.flush()
        let observedBytes = try Data(contentsOf: snapshotPath)
        await repository.close()
        let cold = try WorkspaceRepository(directory: root)
        let reopened = try await cold.readCommittedSnapshot()
        await cold.close()
        let commits = reopened.outbox.filter { $0.kind == .entrySaved }
        if scenario.legacyFollowUp != nil {
            try check(afterGuest == initialBytes, "The inner guest sheet changed the legacy workspace bytes")
            print("legacyInnerBytesUnchanged=true ordinaryEditorDismissed=\(editorDismissed) " +
                  "ordinaryBytesUnchanged=\(observedBytes == initialBytes) revision=\(seeded.revision)->\(reopened.revision) " +
                  "restorationPreserved=\(reopened.restoration == seeded.restoration) frame=\(resultFrame ?? "none")")
            if scenario.isLegacyConflict {
                try check(resultFrame == "Commit refused" && closed == .closed && !editorDismissed,
                          "Signed Commit accepted a changed optional follow-up value")
            } else if scenario == .legacyDone {
                try check(closed == .closed, "Done reported success from the pre-existing entry without a press")
            } else if let expectedLatest {
                try check(!editorDismissed && reopened == expectedLatest, "Old Done closed the newest editor")
            } else {
                try check(editorDismissed && isCommit(closed, alreadyPresent: true),
                          "Authorized legacy retry did not complete as already present")
            }
            try check(observedBytes == initialBytes && reopened == seeded && commits.count == 1,
                      "Ordinary dismissal changed legacy workspace bytes, restoration, revision, or outbox")
        } else if scenario == .success || scenario == .bothProvisioned || scenario.joinsAdmittedWrite || scenario == .authorityReplay {
            if scenario == .joinedDoneSelectionChanged {
                try check(closed == .closed && !editorDismissed,
                          "The retired presentation published success over a newer selection")
            } else {
                try check(editorDismissed && isCommit(closed, alreadyPresent: false),
                          "Done did not dismiss the editor after the authorized commit")
                try check(model.workspace == reopened, "Done did not publish the durable revision")
            }
            guard let entry = reopened.entries.first else { throw ReplayFailure("Missing durable entry") }
            let openDraftID: UUID? = scenario == .joinedDoneSelectionChanged ? other.id : nil
            let revisions: UInt64 = scenario == .joinedDoneSelectionChanged ? 2 : 1
            try check(observedBytes == afterGuest && reopened.revision == seeded.revision + revisions
                && reopened.restoration.openDraftID == openDraftID
                && reopened.entries == [entry] && reopened.drafts == [other]
                && entry.id == draft.id && entry.projectID == project
                && entry.title.utf8.elementsEqual(editorDraft.title.trimmingCharacters(in: .whitespacesAndNewlines).utf8)
                && entry.note.utf8.elementsEqual(editorDraft.note.utf8)
                && entry.category == editorDraft.category && entry.occurredAt == date && entry.followUpRequired == true
                && Array(reopened.outbox.dropLast()) == seeded.outbox
                && commits.count == 1 && commits.first?.recordID == draft.id,
                "The exact edit and its one outbox operation did not survive cold reopen")
        } else {
            let result: WorkspaceModel.DraftGuestClose = scenario == .declined ? .workspaceUnavailable : .closed
            try check(closed == result && !editorDismissed,
                      "Unexpected close result: \(closed), expected \(result), saveError=\(model.saveError ?? "none")")
            try check(reopened.entries.isEmpty && commits.isEmpty, "Refused Commit added an entry or outbox event")
            try check(reopened.drafts == seeded.drafts, "Refused Commit changed the saved drafts")
            try check(reopened.outbox == seeded.outbox, "Refused Commit changed the outbox")
            try check(observedBytes == baseline, "Refused Commit changed the workspace bytes")
            if scenario == .declined {
                try check(fault.withLock { $0 } == 1 && model.saveError == "Reopen FieldLog to check whether the entry was saved.",
                          "Declined write diagnostics or attempt count differed")
            }
        }
        let newEntryEvents = commits.count - seeded.outbox.filter { $0.kind == .entrySaved }.count
        print("case=\(scenario.rawValue) frame=\(resultFrame ?? "none") revision=\(seeded.revision)->\(reopened.revision) "
            + "newEntrySaved=\(newEntryEvents) ordinaryEditorDismissed=\(editorDismissed) retired=true coldReopen=true")
        if scenario == .blank {
            try await verifyNativeFallback(root: root, draft: draft, observedBytes: observedBytes)
        }
    }

    private static func ordinarySheetDismissal(_ model: WorkspaceModel) -> () -> Void {
        #if FIELDLOG_DISMISSAL_BASELINE
        // Baseline WorkspaceView's binding setter, then its onDismiss after the item becomes nil.
        return {
            model.selectDraftEditor(nil)
            model.closeDraft()
        }
        #else
        let sheet = model.draftEditorSheet
        return { sheet.wrappedValue = nil }
        #endif
    }

    private static func finishOrdinaryEditor(
        _ close: WorkspaceModel.DraftGuestClose, model: WorkspaceModel, closeSheet: () -> Void
    ) -> Bool {
        #if FIELDLOG_DISMISSAL_BASELINE
        // Baseline InstalledDraftGuestView success followed by EntryEditor's nested onDismiss.
        guard case .committed(let selection) = close, model.isDraftEditorSelected(selection) else { return false }
        closeSheet()
        return true
        #else
        let wasPresented = model.draftEditor != nil
        model.finishDraftEditorAfterGuest(close)
        guard wasPresented, model.draftEditor == nil else { return false }
        closeSheet()
        return true
        #endif
    }

    private static func isCommit(_ close: WorkspaceModel.DraftGuestClose, alreadyPresent: Bool) -> Bool {
        #if FIELDLOG_DISMISSAL_BASELINE
        if case .committed = close { return true }
        return false
        #else
        guard case .commit(let outcome, _) = close else { return false }
        return outcome == (alreadyPresent ? .alreadyPresent : .committedNow)
        #endif
    }

    private static func exerciseDraftTools(
        _ material: URL, model: WorkspaceModel, draft: EntryDraft, root: URL,
        initial: Workspace, repository: WorkspaceRepository
    ) async throws -> Workspace {
        let access = try await model.attachDraftGuest(projectID: draft.projectID, draftID: draft.id)
        let owner: CapabilityGuestUIRuntime
        do {
            owner = try await InstalledDraftGuest.open(materials: material, workspaceDirectory: root,
                                                       storage: access, bundleID: bundleID)
        } catch {
            _ = await model.finishDraftGuest(access, owner: nil)
            throw error
        }
        do {
            for sequence in 1...3 { try await InstalledDraftGuest.stage(sequence, in: material, on: owner) }
            _ = try await owner.start()
            let presentation = owner.presentation
            try await eventually("Signed optional field was not ready") {
                presentation.state == .displaying(revision: 1)
            }
            guard let attachment = presentation.claimNativeAttachment(), let host = presentation.renderHost,
                  let identity = host.snapshot.identity(for: "toggle")
            else { throw ReplayFailure("Missing signed optional field control") }
            defer { presentation.detachNativeAttachment(attachment) }
            try await eventually("Signed optional field did not accept input") { presentation.inputEnabled }
            let event = try host.route(UIEventEnvelope(revision: 1, identity: identity, event: .activate))
            presentation.actionHandler(host: host, attachment: attachment)(event)
            try await eventually("Signed optional field did not update") {
                presentation.state == .displaying(revision: 2) &&
                presentation.renderHost?.snapshot.document.root.children.contains {
                    $0.id == "follow-up" && $0.properties["text"] == .string("Follow-up required")
                } == true
            }
            let saved = try await repository.readCommittedSnapshot()
            guard let draftIndex = initial.drafts.firstIndex(where: { $0.id == draft.id }) else {
                throw ReplayFailure("Missing selected draft")
            }
            var expected = initial
            expected.revision += 1
            expected.drafts[draftIndex].followUpRequired = true
            try check(saved == expected, "Optional tools rewrote data outside the selected draft's follow-up")
            let closing = Task { await model.finishDraftGuest(access, owner: owner) }
            closing.cancel()
            let closed = await closing.value
            let retired = await owner.recoverySnapshot()
            try check(closed == .closed && retired.closed && !retired.activation.cleanupPending,
                      "Optional tools did not retire before close")
            print("optionalRevision=\(initial.revision)->\(saved.revision) editorRevision=\(model.workspace?.revision ?? 0) retired=true")
            try check(model.workspace == saved, "Closing signed optional tools left the live editor at the old revision")
            return saved
        } catch {
            _ = await model.finishDraftGuest(access, owner: owner)
            throw error
        }
    }

    private static func joinDoneDuringWrite(
        action: () -> Void, barrier: WriteBarrier, model: WorkspaceModel,
        access: SelectedDraftGuestAccess, owner: CapabilityGuestUIRuntime, newSelection: EntryDraft?
    ) async throws -> WorkspaceModel.DraftGuestClose {
        defer { barrier.release.signal() }
        action()
        try await eventually("The signed transaction never reached the admitted write") { barrier.count == 1 }
        var closingStarted = false
        var closingFinished = false
        let closing = Task {
            closingStarted = true
            let result = await model.finishDraftGuest(access, owner: owner)
            closingFinished = true
            return result
        }
        closing.cancel()
        do {
            try await eventually("Done was never requested") { closingStarted }
            try check(!closingFinished, "Done returned while the admitted write remained blocked")
            if let newSelection {
                model.selectDraftEditor(newSelection)
                model.openDraft(newSelection.id)
            }
        } catch {
            barrier.release.signal()
            _ = await closing.value
            throw error
        }
        barrier.release.signal()
        return await closing.value
    }

    private static func verifyNativeFallback(root: URL, draft: EntryDraft, observedBytes: Data) async throws {
        let repository = try WorkspaceRepository(directory: root)
        let model = WorkspaceModel(repository: repository)
        await model.open()
        var edited = draft
        edited.title = "Native corrected title"
        let saved = await model.commit(edited)
        await repository.close()
        let reopened = try WorkspaceRepository(directory: root)
        let snapshot = try await reopened.readCommittedSnapshot()
        let bytes = try Data(contentsOf: root.appendingPathComponent("workspace.json"))
        await reopened.close()
        try check(saved && bytes != observedBytes && snapshot.entries.count == 1
            && snapshot.entries.first?.id == draft.id && snapshot.entries.first?.title == edited.title
            && snapshot.entries.first?.followUpRequired == true
            && snapshot.outbox.filter({ $0.kind == .entrySaved }).count == 1,
            "Ordinary Save entry did not remain available after signed refusal")
        print("nativeFallback=ordinary-save entrySaved=1 coldReopen=true")
    }

    private static func requireDenied(_ model: WorkspaceModel, draft: EntryDraft) async throws {
        do {
            let access = try await model.attachDraftCommit(draft)
            _ = await model.finishDraftGuest(access, owner: nil)
            throw ReplayFailure("Unexpected draft attached")
        } catch CapabilityFailure.permissionDenied {}
    }

    private static func check(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
        guard try condition() else { throw ReplayFailure(message) }
    }

    private static func eventually(_ message: String, _ check: () -> Bool) async throws {
        let deadline = ContinuousClock.now + .seconds(8)
        while !check() {
            guard ContinuousClock.now < deadline else { throw ReplayFailure(message) }
            try await Task.sleep(for: .milliseconds(10))
        }
    }
}
