import CoreGraphics
import FieldLogModels
import FieldLogStorage
import Foundation
import ImageIO
import UniformTypeIdentifiers

private struct CheckFailed: Error {
  let description: String
}

private func check(_ condition: Bool, _ description: String) throws {
  guard condition else { throw CheckFailed(description: description) }
}

private func require<T>(_ value: T?, _ description: String) throws -> T {
  guard let value else { throw CheckFailed(description: description) }
  return value
}

@main @MainActor
struct AssignmentHost {
  static func main() async throws {
    let root = URL(filePath: CommandLine.arguments[1], directoryHint: .isDirectory)
    let directory = root.appending(path: "workspace")
    let repository = try WorkspaceRepository(directory: directory)
    let model = WorkspaceModel(repository: repository)
    await model.open()
    let targetProject = try require(await model.createProject(title: "Inspection", site: "North"), "target")
    let siblingProject = try require(await model.createProject(title: "Inspection", site: "South"), "sibling")
    try check(await model.addTask(projectID: targetProject, title: "Read gauge", responsible: "Rae"), "target task")
    try check(await model.addTask(projectID: siblingProject, title: "Read gauge", responsible: "Sam"), "sibling task")
    let initial = try await repository.readCommittedSnapshot()
    let target = try require(initial.tasks(for: targetProject).first, "target task identity")
    let sibling = try require(initial.tasks(for: siblingProject).first, "sibling task identity")
    model.toggleTask(sibling.id)
    model.restoreProject(siblingProject)
    await model.flush()
    model.showSiteMap(for: siblingProject)
    let map = try require(model.sitePinEdit(projectID: siblingProject), "map lease")
    let pin = try require(SiteCoordinate(latitude: 40, longitude: -73), "site coordinates")
    try check(await model.saveSitePin(map, to: pin), "site pin save")
    var draft = try require(await model.newDraft(projectID: siblingProject), "restored draft")
    draft.title = "Retain this draft"
    try check(await model.keepDraft(draft), "save draft title")
    model.selectDraftEditor(draft)
    let camera = try require(model.draftEditor, "draft photo selection")
    let jpeg = try makeJPEG()
    let photos = try await model.addPhoto(jpeg, to: camera)
    let photo = try require(photos.first, "photo identifier")
    let photoURL = try require(await model.photoURL(photo), "photo URL")

    var first = try require(model.savedTaskEdit(target.id, in: targetProject), "first saved editor")
    var second = try require(model.savedTaskEdit(target.id, in: targetProject), "second saved editor")
    first.text.title = "Read gauge now"
    second.text.title = "Read gauge after shutdown"
    try check(await model.saveTaskEdit(first), "first saved edit")
    try check(await model.saveTaskEdit(second), "persist competing edit")
    let review = try require(model.workspace?.taskConflict(for: target.id), "pending saved conflict")

    let settingsURL = root.appending(path: "settings.json")
    let settings = FieldLogSettings(fileURL: settingsURL)
    settings.update(FieldLogPreferences(appearance: .dark, regionalFormats: .frFR, largerText: true))
    let files = [directory.appending(path: "workspace.json"), photoURL, settingsURL]
    let before = try files.map { try Data(contentsOf: $0) }
    let snapshot = try await repository.readCommittedSnapshot()

    let optIn = ["FieldLog", "--fieldlog-local-assignment-fixture"]
    try check(LocalAssignmentNotificationFixture.allowsPosting(arguments: optIn, ordinaryWorkspace: true),
      "explicit fixture authorization was ignored")
    try check(!LocalAssignmentNotificationFixture.allowsPosting(arguments: ["FieldLog"], ordinaryWorkspace: true),
      "ordinary Debug launch enabled posting")
    try check(!LocalAssignmentNotificationFixture.allowsPosting(arguments: optIn, ordinaryWorkspace: false)
      && !LocalAssignmentNotificationFixture.allowsPosting(in: model), "isolated or injected store enabled posting")

    let router = AssignmentNotificationRouter()
    let notification = AssignmentNotification(workspaceID: snapshot.id, projectID: targetProject, taskID: target.id)
    let payload = notification.userInfo
    try check(AssignmentNotification(userInfo: payload) == notification, "historical payload compatibility")
    for key in payload.keys {
      var invalid = payload
      invalid[key] = "invalid"
      try check(AssignmentNotification(userInfo: invalid) == nil, "malformed field: \(key)")
      invalid[key] = nil
      try check(AssignmentNotification(userInfo: invalid) == nil, "missing field: \(key)")
    }

    router.receive(try require(AssignmentNotification(userInfo: payload), "decode tap"))
    try check(router.takeDestination(in: model, canPresent: true) == nil, "map and camera must defer")
    model.showSiteMap(for: nil)
    try check(router.takeDestination(in: model, canPresent: true) == nil, "camera alone must defer")
    try check(model.draftEditor?.id == camera.id, "tap replaced draft editor")
    try camera.admitPhoto()
    model.selectDraftEditor(nil)
    model.showSiteMap(for: siblingProject)
    let activeMap = try require(model.sitePinEdit(projectID: siblingProject), "map lease on return")
    try check(router.takeDestination(in: model, canPresent: true) == nil, "map alone must defer")
    try check(model.stillShowsSiteMap(for: activeMap), "tap changed map identity")
    try activeMap.session.lease.requireActive()
    model.showSiteMap(for: nil)

    let currentEditor = SavedTaskEditorOwner(edit: try require(
      model.savedTaskEdit(sibling.id, in: siblingProject), "open sibling editor"))
    currentEditor.edit.text.title = "Unsaved sibling text"
    try check(router.takeDestination(in: model, canPresent: false) == nil, "active sheet must defer")
    try check(router.pending == notification, "deferral lost pending tap")
    try check(currentEditor.edit.text.title == "Unsaved sibling text" && !currentEditor.saving,
      "tap modified or submitted the unsaved editor")

    let destination = router.takeDestination(in: model, canPresent: true)
    guard case .task(let edit) = destination else { throw CheckFailed(description: "exact task did not open") }
    let assignmentEditor = SavedTaskEditorOwner(edit: edit)
    let ordinaryEdit = try require(model.savedTaskEdit(target.id, in: targetProject), "ordinary edit")
    try check(assignmentEditor.edit.taskID == target.id && edit.workspaceID == snapshot.id
      && edit.projectID == targetProject && edit.base == ordinaryEdit.base, "tap selected a different saved-task owner")
    try check(model.workspace?.taskConflict(for: assignmentEditor.edit.taskID) == review, "conflict review changed")
    try check(router.takeDestination(in: model, canPresent: true) == nil, "tap consumed twice")

    for stale in [
      AssignmentNotification(workspaceID: UUID(), projectID: targetProject, taskID: target.id),
      AssignmentNotification(workspaceID: snapshot.id, projectID: UUID(), taskID: target.id),
      AssignmentNotification(workspaceID: snapshot.id, projectID: siblingProject, taskID: target.id),
      AssignmentNotification(workspaceID: snapshot.id, projectID: targetProject, taskID: UUID()),
    ] {
      router.receive(stale)
      try check(router.takeDestination(in: model, canPresent: true) == .unavailable, "stale identity matched")
      try check(router.pending == nil, "stale route consumed twice")
    }

    await model.flush()
    try check(try await repository.readCommittedSnapshot() == snapshot, "workspace state changed")
    try check(try files.map { try Data(contentsOf: $0) } == before, "workspace/outbox, JPEG or Settings bytes changed")
    try check(snapshot.restoration.selectedProjectID == siblingProject
      && snapshot.restoration.openDraftID == draft.id && snapshot.tasks(for: siblingProject).first?.completed == true,
      "fixture did not contain navigation, draft and checklist state")
    let reopened = WorkspaceModel(workspaceDirectory: directory)
    router.receive(notification)
    try check(router.takeDestination(in: reopened, canPresent: true) == nil, "cold tap resolved before open")
    await reopened.open()
    try check(!reopened.loading && reopened.workspace == nil
      && reopened.openError?.contains("open in another process") == true, "real workspace lock did not block open")
    let blocked = router.takeDestination(in: reopened, canPresent: true)
    try check(blocked == nil && router.pending == notification,
      "failed open consumed the exact cold assignment: unavailable=\(blocked == .unavailable)")
    await repository.close()
    await reopened.retryOpen()
    try check(!reopened.loading && reopened.openError == nil && reopened.workspace?.id == snapshot.id,
      "retry did not load the authoritative workspace")
    guard case .task(let cold) = router.takeDestination(in: reopened, canPresent: true) else {
      throw CheckFailed(description: "cold route did not reopen saved task")
    }
    try check(cold.taskID == target.id && reopened.workspace?.taskConflict(for: cold.taskID) == review,
      "cold saved route lost task or conflict identity")
    try check(try files.map { try Data(contentsOf: $0) } == before, "cold read changed persisted bytes")
    try check(router.takeDestination(in: reopened, canPresent: true) == nil, "retried assignment presented twice")
    router.receive(AssignmentNotification(workspaceID: snapshot.id, projectID: targetProject, taskID: UUID()))
    try check(router.takeDestination(in: reopened, canPresent: true) == .unavailable && router.pending == nil,
      "missing task stayed pending in an authoritative workspace")
    try await checkReportPresentation(in: reopened, notification: notification, sibling: sibling)
    try check(try files.map { try Data(contentsOf: $0) } == before, "report changed persisted workspace, photo or Settings")
    print("PASS overlapping real report export and assignment, dismissal guard, one-shot share, explicit export failure")
    print("PASS payload, exact and stale identities, one-shot warm/cold routing, saved conflict, editor/map deferral")
    print("PASS real repository lock, exact cold route after retry, stale route consumed after authoritative open")
    print("PASS workspace/outbox, checklist, restoration, draft JPEG and Settings byte preservation")
  }

  private static func checkReportPresentation(
    in model: WorkspaceModel, notification: AssignmentNotification, sibling: WorkTask
  ) async throws {
    let owner = WorkspacePresentationOwner()
    let assignments = AssignmentNotificationRouter()
    let (started, signalStarted) = AsyncStream<Void>.makeStream()
    let (released, release) = AsyncStream<Void>.makeStream()
    defer { signalStarted.finish(); release.finish() }
    let export = try require(owner.requestReport {
      signalStarted.yield()
      for await _ in released { break }
      return try await model.exportReport(projectID: notification.projectID)
    }, "report request")
    for await _ in started { break }
    try check(owner.requestReport { throw CheckFailed(description: "duplicate report ran") } == nil,
      "a second export was admitted")

    assignments.receive(notification)
    owner.presentPending(in: model, assignments: assignments, canPresent: true)
    guard let assignment = owner.sheet, case .assignment(.task(let edit)) = assignment.content else {
      throw CheckFailed(description: "assignment did not open while export was in flight")
    }
    try check(edit.taskID == notification.taskID && assignments.pending == nil, "assignment identity or consumption")
    let next = AssignmentNotification(
      workspaceID: notification.workspaceID, projectID: sibling.projectID, taskID: sibling.id)
    assignments.receive(next)
    release.yield()
    await export.value
    owner.presentPending(in: model, assignments: assignments, canPresent: true)
    try check(owner.sheet?.id == assignment.id && assignments.pending == next, "finished report changed the active editor")

    owner.sheet = nil // SwiftUI clears the item before calling onDismiss.
    owner.presentPending(in: model, assignments: assignments, canPresent: true)
    try check(owner.sheet == nil, "report presented during dismissal animation")
    owner.didDismissSheet()
    owner.presentPending(in: model, assignments: assignments, canPresent: false)
    try check(owner.sheet == nil, "report presented while the workspace was ineligible")
    owner.presentPending(in: model, assignments: assignments, canPresent: true)
    guard let share = owner.sheet, case .share(let url) = share.content else {
      throw CheckFailed(description: "completed report disappeared while the assignment occupied the sheet")
    }
    let workspace = try require(model.workspace, "loaded workspace")
    try check(try String(contentsOf: url, encoding: .utf8) == workspace.report(projectID: notification.projectID),
      "share was for a different project")
    try check(assignments.pending == next, "queued assignment lost priority behind completed share")
    owner.presentPending(in: model, assignments: assignments, canPresent: true)
    try check(owner.sheet?.id == share.id, "share presented twice")
    owner.didDismissSheet()
    owner.presentPending(in: model, assignments: assignments, canPresent: true)
    guard case .assignment(.task(let nextEdit)) = owner.sheet?.content else {
      throw CheckFailed(description: "next assignment did not open after share dismissal")
    }
    try check(nextEdit.taskID == sibling.id && assignments.pending == nil, "next assignment identity or consumption")
    owner.didDismissSheet()
    owner.presentPending(in: model, assignments: assignments, canPresent: true)
    try check(owner.sheet == nil, "a consumed share or assignment reappeared")

    let failedExport = try require(owner.requestReport {
      try await model.exportReport(projectID: UUID())
    }, "failing report request")
    owner.present(.newTask(notification.projectID))
    await failedExport.value
    owner.presentPending(in: model, assignments: assignments, canPresent: true)
    guard case .newTask = owner.sheet?.content else {
      throw CheckFailed(description: "export failure replaced the current sheet")
    }
    owner.didDismissSheet()
    owner.presentPending(in: model, assignments: assignments, canPresent: true)
    guard case .reportFailure(let reason) = owner.sheet?.content, !reason.isEmpty else {
      throw CheckFailed(description: "report failure never surfaced")
    }
    owner.didDismissSheet()
    owner.presentPending(in: model, assignments: assignments, canPresent: true)
    try check(owner.sheet == nil, "report failure presented twice")
  }

  private static func makeJPEG() throws -> Data {
    let context = try require(CGContext(data: nil, width: 4, height: 4, bitsPerComponent: 8, bytesPerRow: 0,
      space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue), "raster")
    context.fill(CGRect(x: 0, y: 0, width: 4, height: 4))
    let image = try require(context.makeImage(), "image")
    let data = NSMutableData()
    let output = try require(CGImageDestinationCreateWithData(data, UTType.jpeg.identifier as CFString, 1, nil), "JPEG")
    CGImageDestinationAddImage(output, image, nil)
    try check(CGImageDestinationFinalize(output), "encode photo")
    return data as Data
  }
}
