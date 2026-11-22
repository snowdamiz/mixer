import FieldLogModels
import FieldLogStorage
import Foundation

enum CheckFailure: Error { case interrupted, lockWasNotHeld }

@main
struct AccountWorkspaceSeed {
    static func main() async throws {
        let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
        let scoped = root.appendingPathComponent("account")
        let snapshot = scoped.appendingPathComponent("workspace.json")
        let project = Project(id: UUID(), title: "FieldLog", site: "Local workspace")
        var seed = Workspace()
        seed.projects = [project]
        seed.restoration.selectedProjectID = project.id

        do {
            _ = try WorkspaceRepository(directory: scoped, initialWorkspace: seed, fault: {
                if $0 == "before_rename" { throw CheckFailure.interrupted }
            })
            throw CheckFailure.lockWasNotHeld
        } catch CheckFailure.interrupted {}
        precondition(!FileManager.default.fileExists(atPath: snapshot.path))

        let open = try WorkspaceRepository(directory: scoped, initialWorkspace: seed)
        let retained = try await open.readCommittedSnapshot()
        precondition(retained == seed)
        let bytes = try Data(contentsOf: snapshot)
        do {
            _ = try WorkspaceRepository(directory: scoped, initialWorkspace: Workspace())
            throw CheckFailure.lockWasNotHeld
        } catch FieldLogError.storage {}
        await open.close()

        let reopened = try WorkspaceRepository(directory: scoped, initialWorkspace: Workspace())
        let restored = try await reopened.readCommittedSnapshot()
        precondition(restored == seed)
        let reopenedBytes = try Data(contentsOf: snapshot)
        precondition(reopenedBytes == bytes)
        await reopened.close()

        let ordinary = try WorkspaceRepository(directory: root.appendingPathComponent("ordinary"))
        let ordinarySnapshot = await ordinary.snapshot()
        precondition(ordinarySnapshot.id != seed.id && ordinarySnapshot.projects.isEmpty)
        await ordinary.close()
        print("Account seed recovery, competing owner, cold preservation, and ordinary workspace passed.")
    }
}
