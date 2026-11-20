import CoreGraphics
import FieldLogModels
import FieldLogStorage
import Foundation
import ImageIO

private let project = UUID(uuidString: "4461A3CA-ACF4-43FA-90B7-958823CC6B19")!
private let first = UUID(uuidString: "F989403F-D7FA-4836-881C-B7F60C82E387")!
private let second = UUID(uuidString: "5F0897D2-1775-4DE5-AD1B-308F230022B3")!
private let offlineNote = "Updated in the ordinary editor’s save path"

private struct Failure: Error {
    let message: String
}

private func require(_ condition: Bool, _ message: String) throws {
    guard condition else { throw Failure(message: message) }
}

private func seedJPEG() throws -> Data {
    let output = NSMutableData()
    guard let context = CGContext(data: nil, width: 8, height: 8, bitsPerComponent: 8,
            bytesPerRow: 32, space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue),
          let destination = CGImageDestinationCreateWithData(output as CFMutableData, "public.jpeg" as CFString, 1, nil)
    else { throw Failure(message: "Could not create JPEG writer") }
    context.setFillColor(red: 0.5, green: 0.25, blue: 0.75, alpha: 1)
    context.fill(CGRect(x: 0, y: 0, width: 8, height: 8))
    guard let image = context.makeImage() else { throw Failure(message: "Could not create JPEG image") }
    CGImageDestinationAddImage(destination, image, nil)
    try require(CGImageDestinationFinalize(destination), "Could not encode JPEG")
    return output as Data
}

@main
struct RepositoryControl {
    static func main() async throws {
        try require(CommandLine.arguments.count == 3, "Expected a phase and an owned workspace directory")
        let directory = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
        let repository = try WorkspaceRepository(directory: directory)
        let workspaceURL = directory.appendingPathComponent("workspace.json")
        let originalJPEG = directory.deletingLastPathComponent().appendingPathComponent("original.jpg")
        let phase = CommandLine.arguments[1]
        #if OPTIONAL_SUCCESSOR
        switch phase {
        case "set-optional":
            try await repository.transact {
                try $0.createProject(id: project, title: "Public repository control", site: "")
                try $0.saveDraft(EntryDraft(id: first, projectID: project, title: "Pump A", note: "Original"))
                try $0.saveDraft(EntryDraft(id: second, projectID: project, title: "Pump B"))
            }
            let jpeg = try seedJPEG()
            try jpeg.write(to: originalJPEG)
            _ = try await repository.addPhoto(jpeg: jpeg, to: first)
            let before = try Data(contentsOf: workspaceURL)
            do {
                _ = try await repository.selectSavedDraft(projectID: project, draftID: UUID())
                throw Failure(message: "Unsaved draft was selectable")
            } catch FieldLogError.missingRecord {
                try require(try Data(contentsOf: workspaceURL) == before, "Unsaved selection changed disk")
            }
            let selection = try await repository.selectSavedDraft(projectID: project, draftID: first)
            let revision = try await repository.readSelectedDraft(selection).revision
            try await repository.updateSelectedDraftFollowUp(selection, expectedRevision: revision) { $0 = true }
            let bSelection = try await repository.selectSavedDraft(projectID: project, draftID: second)
            let b = try await repository.readSelectedDraft(bSelection).draft
            try require(b?.id == second && b?.followUpRequired == nil && b?.attachmentIDs == [], "Second draft inherited data")
        case "reopen":
            let state = try await repository.readCommittedSnapshot()
            let selection = try await repository.selectSavedDraft(projectID: project, draftID: first)
            let a = try await repository.readSelectedDraft(selection).draft
            let bSelection = try await repository.selectSavedDraft(projectID: project, draftID: second)
            let b = try await repository.readSelectedDraft(bSelection).draft
            try require(a?.id == first && a?.note == offlineNote && a?.followUpRequired == true
                && b?.id == second && b?.followUpRequired == nil && b?.attachmentIDs == [], "Cold read changed draft isolation")
            try require(state.outbox.map(\.kind) == [.projectCreated] && state.entries.isEmpty, "Draft edit changed the outbox or committed an entry")
            guard let photoID = a?.attachmentIDs.first else { throw Failure(message: "Draft lost JPEG") }
            let url = try await repository.photoURL(photoID)
            try require(try Data(contentsOf: url) == Data(contentsOf: originalJPEG), "Reopened JPEG bytes differ")
        default:
            throw Failure(message: "Wrong successor phase")
        }
        #else
        try require(phase == "rollback-edit", "Wrong rollback phase")
        let before = try Data(contentsOf: workspaceURL)
        let state = await repository.snapshot()
        guard var edited = state.drafts.first(where: { $0.id == first }) else {
            throw Failure(message: "Rollback could not read draft A")
        }
        try require(edited.followUpRequired == true && edited.note == "Original", "Rollback could not read the same stored record")
        try require(try Data(contentsOf: workspaceURL) == before, "Rollback read changed workspace bytes")
        edited.note = offlineNote
        edited.followUpRequired = nil
        let staleEdit = edited
        try await repository.transact { try $0.saveDraft(staleEdit) }
        #endif
        await repository.close()
        print("PASS \(phase)")
    }
}
