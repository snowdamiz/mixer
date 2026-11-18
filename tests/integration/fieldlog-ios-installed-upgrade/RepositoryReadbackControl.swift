import FieldLogModels
import FieldLogStorage
import Foundation

@main
struct RepositoryReadbackControl {
  static func main() async throws {
    let args = CommandLine.arguments
    let directory = URL(fileURLWithPath: args[2], isDirectory: true)
    let repo = try WorkspaceRepository(directory: directory)
    switch args[1] {
    case "create":
      let project = UUID()
      let draft = EntryDraft(
        projectID: project, title: "Migration photo draft", note: "Keep  two spaces.")
      try await repo.transact {
        try $0.createProject(id: project, title: "Migration pump station", site: "")
      }
      try await repo.transact {
        try $0.saveTask(projectID: project, title: "Inspect pump", responsible: "")
      }
      try await repo.transact {
        try $0.saveDraft(draft)
        $0.restoration.openDraftID = draft.id
      }
      let jpeg = try Data(contentsOf: URL(fileURLWithPath: args[3]))
      _ = try await repo.addPhoto(jpeg: jpeg, to: draft.id)
    case "read":
      let snapshot = await repo.snapshot()
      guard let attachment = snapshot.attachments.first else { throw FieldLogError.missingRecord }
      let photo = try await repo.photoURL(attachment.id)
      guard try Data(contentsOf: photo).starts(with: [0xff, 0xd8, 0xff]) else {
        throw FieldLogError.validation("Expected repository JPEG")
      }
    case "edit":
      let snapshot = await repo.snapshot()
      guard var draft = snapshot.drafts.first, snapshot.restoration.openDraftID == draft.id else {
        throw FieldLogError.missingRecord
      }
      draft.note += " Checked on site."
      let updated = draft
      try await repo.transact {
        try $0.saveDraft(updated)
        try $0.commitDraft(updated.id)
      }
    default:
      throw FieldLogError.validation("Unknown control step")
    }
    await repo.close()
  }
}
