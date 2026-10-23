import Foundation
import Testing
import FieldLogModels
import FieldLogStorage
import FieldLogFeatures

private actor ReviewSaves {
    struct Input: Equatable, Sendable { let title: String; let responsible: String }
    private(set) var inputs: [Input] = []
    private(set) var cancellationObserved = false
    private var pending: [Int: CheckedContinuation<TaskSaveResult, Never>] = [:]
    func save(_ title: String, _ responsible: String) async -> TaskSaveResult {
        let index = inputs.count
        inputs.append(Input(title: title, responsible: responsible))
        return await withCheckedContinuation { pending[index] = $0 }
    }
    func finish(_ index: Int, _ result: TaskSaveResult) { pending.removeValue(forKey: index)?.resume(returning: result) }
    func observedCancellation() { cancellationObserved = true }
}
private final class ReviewFault: @unchecked Sendable {
    private let lock = NSLock()
    private var point: String?
    func arm(_ point: String) { lock.lock(); self.point = point; lock.unlock() }
    func check(_ point: String) throws {
        lock.lock(); defer { lock.unlock() }
        if self.point == point { self.point = nil; throw FieldLogError.storage("independent injected \(point)") }
    }
}
@MainActor private func reviewWait(_ condition: () async -> Bool) async throws {
    for _ in 0..<400 {
        if await condition() { return }
        try await Task.sleep(nanoseconds: 5_000_000)
    }
    try #require(await condition(), "independent bounded transition timeout")
}
@MainActor private final class WeakEditor {
    weak var value: TaskEditor?
    init(_ value: TaskEditor?) { self.value = value }
}

@Suite(.serialized)
@MainActor struct IndependentTaskEditorTests {
    @Test func unicodeByteLimitsAndNulAreRejectedBeforeSavingWithoutLosingText() async throws {
        let saves = ReviewSaves()
        let editor = try TaskEditor { await saves.save($0, $1) }
        for (title, responsible) in [(String(repeating: "é", count: 121), "Rae"),
                                     ("Valid", String(repeating: "é", count: 81)),
                                     ("Null\0title", "Rae"), ("Valid", "Null\0person")] {
            try editor.changeTitle(title)
            try editor.changeResponsible(responsible)
            try editor.submit()
            #expect(editor.state.title == title && editor.state.responsible == responsible)
            #expect(editor.state.failure != nil && !editor.state.saving && !editor.state.saved)
        }
        #expect(await saves.inputs.isEmpty)
        try editor.changeTitle(String(repeating: "é", count: 120))
        try editor.changeResponsible(String(repeating: "é", count: 80))
        try editor.submit()
        try await reviewWait { await saves.inputs.count == 1 }
        await saves.finish(0, .saved)
        await editor.waitForSave()
        #expect(editor.state.saved)
        try editor.close()
    }

    @Test func failedSaveCanActuallyRetryAfterEditingAndSuccessCannotRepeat() async throws {
        let saves = ReviewSaves()
        let editor = try TaskEditor { await saves.save($0, $1) }
        try editor.changeTitle("  First  日本語  ")
        try editor.changeResponsible("  Rae  ")
        try editor.submit()
        try await reviewWait { await saves.inputs.count == 1 }
        for _ in 0..<20 { try editor.submit(); try editor.changeResponsible("forbidden mutation") }
        #expect(editor.state.responsible == "  Rae  ")
        await saves.finish(0, .failed("temporary storage failure"))
        await editor.waitForSave()
        #expect(editor.state.failure == "temporary storage failure" && editor.state.canSubmit)
        try editor.changeTitle("Second\nline  preserved")
        #expect(editor.state.failure == nil)
        try editor.submit()
        try await reviewWait { await saves.inputs.count == 2 }
        let expected = ReviewSaves.Input(title: "Second\nline  preserved", responsible: "  Rae  ")
        #expect(await saves.inputs.last == expected)
        await saves.finish(1, .saved)
        await editor.waitForSave()
        let saved = editor.state
        for _ in 0..<20 { try editor.submit(); try editor.changeTitle("after success") }
        #expect(editor.state == saved && saved.saved && !saved.canSubmit && !saved.saving)
        #expect(await saves.inputs.count == 2)
        try editor.close()
    }

    @Test func removedObserversAndClosedOldOwnerCannotAffectNewEditor() async throws {
        let saves = ReviewSaves()
        let old = try TaskEditor { await saves.save($0, $1) }
        var removedValues: [TaskEditorState] = []
        let observer = old.observe { removedValues.append($0) }
        #expect(removedValues.count == 1)
        old.removeObserver(observer)
        try old.changeTitle("old task")
        try old.submit()
        try await reviewWait { await saves.inputs.count == 1 }
        let closed = old.state
        try old.close(); try old.close()
        for action in [{ try old.submit() }, { try old.changeTitle("late") }, { try old.changeResponsible("late") }] {
            #expect(throws: (any Error).self, performing: action)
        }
        let next = try TaskEditor { await saves.save($0, $1) }
        try next.changeTitle("new task")
        try next.submit()
        try await reviewWait { await saves.inputs.count == 2 }
        await saves.finish(0, .failed("old owner failure must not cross"))
        await saves.finish(1, .saved)
        await next.waitForSave()
        for _ in 0..<10 { await Task.yield() }
        #expect(old.state == closed && !old.state.saved)
        #expect(next.state.saved && next.state.failure == nil)
        #expect(removedValues.count == 1)
        try next.close()
    }

    @Test func releasedEditorCancelsCooperativeWorkAndDoesNotRetainOwner() async throws {
        let saves = ReviewSaves()
        var owner: TaskEditor? = try TaskEditor { title, responsible in
            let result = await saves.save(title, responsible)
            if Task.isCancelled { await saves.observedCancellation(); return .failed("cancelled owner") }
            return result
        }
        let released = WeakEditor(owner)
        try owner?.changeTitle("deinit owner")
        try owner?.submit()
        try await reviewWait { await saves.inputs.count == 1 }
        owner = nil
        #expect(released.value == nil)
        await saves.finish(0, .saved)
        try await reviewWait { await saves.cancellationObserved }
        #expect(released.value == nil)
    }

    @Test func synchronousSavedObserverCanRemoveItselfAndCloseWithoutReenteringReducer() async throws {
        let saves = ReviewSaves()
        let editor = try TaskEditor { await saves.save($0, $1) }
        var token: UUID?
        var notifications = 0
        var reentrantDispatchRejected = false
        token = editor.observe { state in
            notifications += 1
            if state.saving {
                do { try editor.changeTitle("reentrant edit must fail") }
                catch { reentrantDispatchRejected = true }
            }
            if state.saved {
                if let token { editor.removeObserver(token) }
                do { try editor.close() } catch { Issue.record("saved observer cleanup failed: \(error)") }
            }
        }
        try editor.changeTitle("saved observer cleanup")
        try editor.submit()
        try await reviewWait { await saves.inputs.count == 1 }
        await saves.finish(0, .saved)
        await editor.waitForSave()
        #expect(reentrantDispatchRejected && notifications == 4)
        #expect(editor.state.saved && editor.state.title == "saved observer cleanup")
        #expect(throws: (any Error).self) { try editor.submit() }
        if let token { editor.removeObserver(token) }
    }

    @Test func closingUnsavedFormNeverInvokesSave() async throws {
        let saves = ReviewSaves()
        let editor = try TaskEditor { await saves.save($0, $1) }
        try editor.changeTitle("cancel this unsaved task")
        try editor.changeResponsible("Rae")
        let input = editor.state
        try editor.close(); try editor.close()
        for _ in 0..<10 { await Task.yield() }
        #expect(editor.state == input && !editor.state.saved)
        #expect(await saves.inputs.isEmpty)
        #expect(throws: (any Error).self) { try editor.submit() }
    }

    @Test func validationFailureNeverMutatesExistingWorkspaceAndMissingProjectIsExplained() async throws {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent("fieldlog-review-validation-\(UUID())")
        defer { try? FileManager.default.removeItem(at: folder) }
        let repository = try WorkspaceRepository(directory: folder)
        let initial = try await repository.transact { try $0.createProject(title: "Existing project", site: "") }
        let editor = try TaskEditor { title, responsible in
            do { _ = try await repository.transact { try $0.saveTask(projectID: UUID(), title: title, responsible: responsible) }; return .saved }
            catch { return .failed(error.localizedDescription) }
        }
        try editor.changeTitle("kept task input")
        try editor.submit(); await editor.waitForSave()
        #expect(editor.state.failure == FieldLogError.missingRecord.localizedDescription)
        #expect(editor.state.title == "kept task input" && editor.state.canSubmit && !editor.state.saved)
        #expect(await repository.snapshot() == initial)
        try editor.close(); await repository.close()
    }

    @Test(arguments: ["before_file_sync", "after_rename", "after_directory_sync"])
    func interruptedPersistenceIsNotReportedAsSuccessAndRetryCannotDuplicate(_ point: String) async throws {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent("fieldlog-review-fault-\(UUID())")
        defer { try? FileManager.default.removeItem(at: folder) }
        let faults = ReviewFault()
        let repository = try WorkspaceRepository(directory: folder, fault: faults.check)
        let initial = try await repository.transact { try $0.createProject(title: "Retained project", site: "Original site") }
        let project = try #require(initial.projects.first?.id)
        let editor = try TaskEditor { title, responsible in
            do { _ = try await repository.transact { try $0.saveTask(projectID: project, title: title, responsible: responsible) }; return .saved }
            catch { return .failed(error.localizedDescription) }
        }
        let title = "  Measured  日本語 opening  "
        try editor.changeTitle(title); try editor.changeResponsible("  Rae  ")
        faults.arm(point)
        try editor.submit(); await editor.waitForSave()
        #expect(editor.state.failure != nil && !editor.state.saved && editor.state.canSubmit)
        #expect(editor.state.title == title && editor.state.responsible == "  Rae  ")
        #expect(await repository.snapshot() == initial)
        // The uncertain repository refuses further commits until reopen. The
        // editor may retry, but cannot manufacture a duplicate saved record.
        try editor.submit(); await editor.waitForSave()
        #expect(!editor.state.saved && editor.state.failure != nil)
        try editor.close(); await repository.close()
        let reopened = try WorkspaceRepository(directory: folder)
        let disk = await reopened.snapshot()
        #expect(disk.projects == initial.projects)
        #expect(disk.tasks.count == (point == "before_file_sync" ? 0 : 1))
        #expect(disk.outbox.count == initial.outbox.count + disk.tasks.count)
        if let task = disk.tasks.first {
            #expect(task.title == "Measured  日本語 opening" && task.responsible == "  Rae  ")
        }
        await reopened.close()
    }

    @Test func closeBeforeEffectAdmissionDoesNotUndoAuthorizedSubmission() async throws {
        let saves = ReviewSaves()
        let editor = try TaskEditor { await saves.save($0, $1) }
        try editor.changeTitle("authorized before close")
        try editor.submit()
        // Main-actor effect task has not yet had a chance to run. Closing removes
        // result ownership; the current public API does not guarantee pre-I/O
        // cancellation of an operation that ignores cancellation.
        try editor.close()
        try await reviewWait { await saves.inputs.count == 1 }
        await saves.finish(0, .saved)
        for _ in 0..<10 { await Task.yield() }
        #expect(!editor.state.saved)
        #expect(await saves.inputs.count == 1)
    }

    @Test func closingAfterCommitPreservesSavedRecordWithoutDeliveringLateSuccess() async throws {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent("fieldlog-review-close-commit-\(UUID())")
        defer { try? FileManager.default.removeItem(at: folder) }
        let repository = try WorkspaceRepository(directory: folder)
        let original = try await repository.transact { try $0.createProject(title: "Meaningful existing project", site: "Local test site") }
        let project = try #require(original.projects.first?.id)
        let saves = ReviewSaves()
        let editor = try TaskEditor { title, responsible in
            do {
                _ = try await repository.transact { try $0.saveTask(projectID: project, title: title, responsible: responsible) }
                return await saves.save(title, responsible)
            } catch { return .failed(error.localizedDescription) }
        }
        try editor.changeTitle("Committed despite revoked result ownership")
        try editor.submit()
        try await reviewWait { await saves.inputs.count == 1 }
        let committed = await repository.snapshot()
        #expect(committed.tasks.count == 1 && committed.outbox.count == original.outbox.count + 1)
        let beforeClose = editor.state
        try editor.close()
        await saves.finish(0, .saved)
        for _ in 0..<10 { await Task.yield() }
        #expect(editor.state == beforeClose && !editor.state.saved)
        #expect(throws: (any Error).self) { try editor.submit() }
        await repository.close()
        let reopened = try WorkspaceRepository(directory: folder)
        #expect(await reopened.snapshot() == committed)
        await reopened.close()
    }
}
