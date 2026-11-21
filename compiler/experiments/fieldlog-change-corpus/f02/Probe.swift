import FieldLogModels
import FieldLogStorage
import Foundation
import SwiftUI

private enum ProbeError: Error {
  case failed(String)
}

private func require(_ condition: Bool, _ message: String) throws {
  guard condition else { throw ProbeError.failed(message) }
}

@main struct Probe {
  @MainActor static func main() async throws {
    let arguments = ProcessInfo.processInfo.arguments
    try require(arguments.count == 3, "Expected an operation and the isolated home path")
    let support = try FileManager.default.url(
      for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: false)
    let expectedSupport = URL(fileURLWithPath: arguments[2]).appendingPathComponent(
      "Library/Application Support", isDirectory: true)
    try require(
      support.resolvingSymlinksInPath().path == expectedSupport.resolvingSymlinksInPath().path,
      "Foundation did not resolve to the isolated Application Support")
    let directory = support.appendingPathComponent("FieldLog", isDirectory: true)
    let operation = arguments[1]
    if operation == "seed" {
      let repository = try WorkspaceRepository(directory: directory)
      let workspace = try await repository.transact { state in
        let date = Date(timeIntervalSince1970: 1_700_000_000)
        let other = try state.createProject(title: "Other project", site: "South", now: date)
        try state.saveTask(projectID: other, title: "Leave alone", responsible: "Sam", now: date)
        let project = try state.createProject(title: "Checklist", site: "North", now: date)
        try state.saveTask(projectID: project, title: "Inspect", responsible: "Ari", now: date)
        try state.saveTask(projectID: project, title: "Measure", responsible: "Bo", now: date)
        try state.saveTask(projectID: project, title: "Record", responsible: "Cam", now: date)
        let middle = state.tasks(for: project)[1]
        try state.toggleTask(middle.id, now: date)
        let entry = EntryDraft(projectID: project, title: "Saved entry", note: "Retain this entry",
                               occurredAt: date, updatedAt: date)
        try state.saveDraft(entry)
        try state.commitDraft(entry.id, now: date)
        let draft = EntryDraft(projectID: project, title: "Open draft", note: "Retain this draft",
                               occurredAt: date, updatedAt: date)
        try state.saveDraft(draft)
        state.restoration.openDraftID = draft.id
      }
      await repository.close()
      try emit(workspace)
      return
    }

    let model = WorkspaceModel()
    await model.open()
    guard let workspace = model.workspace, let projectID = workspace.restoration.selectedProjectID
    else { throw ProbeError.failed("Original WorkspaceModel.open failed: \(model.openError ?? "")") }
    if operation == "reopen" {
      try emit(workspace)
      return
    }

    #if !F02_BEFORE
      let rows = workspace.tasks(for: projectID)
    #endif
    switch operation {
      #if F02_BEFORE
      case "legacy-drag":
        let source = IndexSet(integer: 1)
        let destination = 3
        // Pinned ProjectDetail.swift .onMove body.
        var tasks = workspace.tasks(for: projectID)
        tasks.move(fromOffsets: source, toOffset: destination)
        model.reorder(projectID: projectID, ids: tasks.map(\.id))
      #else
      case "down":
        let task = rows[1]
        // Pinned ProjectDetail.swift Move down button body.
        model.moveTask(task.id, offset: 1)
      case "up", "reject-top-up":
        let task = operation == "up" ? rows[2] : rows[0]
        // Pinned ProjectDetail.swift Move up button body.
        model.moveTask(task.id, offset: -1)
      #endif
      default:
        throw ProbeError.failed("Unexpected operation: \(operation)")
    }
    await model.flush()
    let expectedError = operation == "reject-top-up" ? "This task cannot move farther." : nil
    try require(model.saveError == expectedError, "Unexpected save result: \(model.saveError ?? "")")
    try require(model.pendingSaves == 0 && model.unsavedDrafts.isEmpty, "Model has pending changes")
    guard let saved = model.workspace else { throw ProbeError.failed("Workspace was lost") }
    try emit(saved)
  }

  private static func emit(_ workspace: Workspace) throws {
    let data = try JSONEncoder().encode(workspace)
    FileHandle.standardOutput.write(data)
  }
}
