import FieldLogModels
import FieldLogStorage
import Foundation
import MixerUI

private actor TaskSaveOwner {
    private let repository: WorkspaceRepository
    private let projectID: UUID
    private let now: Date
    private(set) var invocationCount = 0

    init(repository: WorkspaceRepository, projectID: UUID, now: Date) {
        self.repository = repository
        self.projectID = projectID
        self.now = now
    }

    func save(_ title: String, _ responsible: String) async -> TaskSaveResult {
        invocationCount += 1
        do {
            try await repository.transact {
                try $0.saveTask(projectID: projectID, title: title, responsible: responsible, now: now)
            }
            return .saved
        } catch {
            return .failed(error.localizedDescription)
        }
    }
}

@MainActor func replaySave(_ guest: Data, in folder: URL) async throws {
    let projectID = UUID(uuidString: "4c589bde-5f6c-41f4-8acb-e6099d0a1877")!
    let now = Date(timeIntervalSince1970: 1_800_000_000)
    let title = "Inspect pump P-17"
    let nativeFolder = folder.appendingPathComponent("native")
    let guestFolder = folder.appendingPathComponent("guest")
    let nativeRepo = try WorkspaceRepository(directory: nativeFolder)
    let guestRepo = try WorkspaceRepository(directory: guestFolder)
    let nativeSeed = try await nativeRepo.transact {
        try $0.createProject(id: projectID, title: "Pump station", site: "", now: now)
    }
    let guestSeed = try await guestRepo.transact {
        try $0.createProject(id: projectID, title: "Pump station", site: "", now: now)
    }
    try require(nativeSeed.restoration.selectedProjectID == projectID &&
                guestSeed.restoration.selectedProjectID == projectID, "seed lacks selected project restoration")
    let nativeOwner = TaskSaveOwner(repository: nativeRepo, projectID: projectID, now: now)
    let guestOwner = TaskSaveOwner(repository: guestRepo, projectID: projectID, now: now)
    let native = try TaskEditorPresentation(save: nativeOwner.save)
    let render = native.snapshot.render
    guard let titleID = render.identity(for: "task.title"), let cancelID = render.identity(for: "task.cancel"),
          let saveID = render.identity(for: "task.save") else {
        throw ReplayFailure(description: "historical Save controls absent")
    }

    let session = try Session(guest)
    let address = try session.invoke("fieldlog_editor_open", [
        i64(titleID.generation), i64(cancelID.generation), i64(saveID.generation),
    ])
    try require(address > 0, "null Save guest buffer")
    try require(try session.snapshot(at: address) == originalBytes(native.snapshot), "initial Save fixture differs")
    let edit = Turn(name: "short-title-edit", revision: 1, node: .title, generation: titleID.generation,
                    event: .textChange, value: .string(title), expected: .accepted)
    let save = Turn(name: "submit-save", revision: 2, node: .save, generation: saveID.generation,
                    event: .activate, value: .null, expected: .accepted)
    for turn in [edit, save] {
        try require(try deliver(turn, to: native) == turn.expected, "\(turn.name): historical reply")
        try require(try guestSend(turn, session, at: address, input: turn.input) == turn.expected.rawValue,
                    "\(turn.name): guest reply")
        let sendFuel = session.fuel
        let expected = try originalBytes(native.snapshot, includeSave: true)
        let phase: UInt8 = turn.node == .save ? 2 : 0
        let actual = try session.snapshot(at: address)
        try require(expected[8] == phase && expected[9] == 1 && actual == expected, "\(turn.name): published state differs")
        print("saveTurn=\(turn.name) revision=\(native.snapshot.render.document.revision) phase=\(phase) routes=1 sendFuel=\(sendFuel) snapshotFuel=\(session.fuel)")
    }
    try require(try session.invoke("fieldlog_editor_complete_save") == EditorReply.closed.rawValue,
                "guest accepted an outcome before effect delivery")
    let beforeOwner = await guestRepo.snapshot()
    try require(beforeOwner == guestSeed, "guest dispatch changed repository before owner commit")
    try require(await guestOwner.invocationCount == 0, "guest owner started before effect delivery")
    let count = Int(try session.invoke("fieldlog_editor_take_save"))
    let takeFuel = session.fuel
    try require(count == title.utf8.count, "unexpected Save effect size")
    let bytes = try session.read(at: address, count: count)
    guard let effectTitle = String(validating: bytes, as: UTF8.self), bytes.elementsEqual(title.utf8) else {
        throw ReplayFailure(description: "Save effect title differs")
    }
    try require(try session.invoke("fieldlog_editor_take_save") == 0, "Save effect was delivered more than once")
    switch await guestOwner.save(effectTitle, "") {
    case .saved: break
    case .failed(let message): throw ReplayFailure(description: "guest owner could not commit: \(message)")
    }
    try require(try session.invoke("fieldlog_editor_complete_save") == EditorReply.accepted.rawValue,
                "guest did not accept the owner's success")
    let completeFuel = session.fuel
    await native.waitForSave()
    let saved = try originalBytes(native.snapshot, includeSave: true)
    try require(saved[8] == 3 && saved[9] == 0, "historical Save did not finish navigation")
    try require(try session.snapshot(at: address) == saved, "guest Save outcome differs")
    print("saveTurn=owner-completed revision=\(native.snapshot.render.document.revision) phase=saved routes=0 takeFuel=\(takeFuel) completeFuel=\(completeFuel) snapshotFuel=\(session.fuel)")
    try require(try session.invoke("fieldlog_editor_complete_save") == EditorReply.closed.rawValue,
                "guest accepted duplicate completion")
    try session.close()
    try native.close()

    let nativeCalls = await nativeOwner.invocationCount
    let guestCalls = await guestOwner.invocationCount
    try require(nativeCalls == 1 && guestCalls == 1,
                "expected one owner invocation per leg, observed native=\(nativeCalls) guest=\(guestCalls)")
    let nativeCold = try await coldReadback(nativeRepo, at: nativeFolder)
    let guestCold = try await coldReadback(guestRepo, at: guestFolder)
    try require(matchesSave(nativeCold, after: nativeSeed, title: title, projectID: projectID, now: now),
                "native cold workspace differs from its seed plus the expected Save")
    try require(matchesSave(guestCold, after: guestSeed, title: title, projectID: projectID, now: now),
                "guest cold workspace differs from its seed plus the expected Save")
    print("saveReadback=matched title=\"\(title)\" revision=\(guestSeed.revision)->\(guestCold.revision) tasksAdded=1 outboxAdded=1 outboxKind=taskSaved linkedRecord=true fullSeededWorkspaceMatched=true selectedProjectPreserved=true nativeOwnerCalls=\(nativeCalls) guestOwnerCalls=\(guestCalls) closedAndReopened=true retiredHandle=refused peakFuel=\(session.peakFuel)")

    var clearedRestoration = guestCold
    clearedRestoration.restoration.selectedProjectID = nil
    try require(!matchesSave(clearedRestoration, after: guestSeed, title: title, projectID: projectID, now: now),
                "full workspace comparison missed cleared restoration")
    let controlOwner = TaskSaveOwner(repository: guestRepo, projectID: projectID, now: now)
    guard case .failed = await controlOwner.save(title, ""), case .failed = await controlOwner.save(title, "") else {
        throw ReplayFailure(description: "closed repository accepted a control Save")
    }
    let failedCalls = await controlOwner.invocationCount
    try require(failedCalls == 2, "owner count missed a failed invocation")
    print("saveControls=clearedRestorationDetected failedOwnerCalls=\(failedCalls) expectedOwnerCalls=1")
}

private func coldReadback(_ repository: WorkspaceRepository, at folder: URL) async throws -> Workspace {
    let committed = await repository.snapshot()
    await repository.close()
    let reopened = try WorkspaceRepository(directory: folder)
    let cold = await reopened.snapshot()
    await reopened.close()
    try require(cold == committed, "cold repository differs from committed state")
    return cold
}

private func matchesSave(_ cold: Workspace, after seed: Workspace, title: String, projectID: UUID, now: Date) -> Bool {
    let revision = seed.revision + 1
    // Each repository creates its own IDs. Validate their linkage and every
    // other field before accepting the new records as the expected append.
    guard let task = cold.tasks.last, task.projectID == projectID, task.title.utf8.elementsEqual(title.utf8),
          task.responsible.isEmpty, !task.completed, task.position == seed.tasks(for: projectID).count,
          task.updatedAt == now,
          let change = cold.outbox.last, change.kind == .taskSaved, change.recordID == task.id,
          change.revision == revision, change.createdAt == now, change.idempotencyKey == change.id.uuidString.lowercased() else {
        return false
    }
    var expected = seed
    expected.revision = revision
    expected.tasks.append(task)
    expected.outbox.append(change)
    return cold == expected
}
