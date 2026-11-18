import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilities

struct RowFailure: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

actor RowStorage: InstalledApplicationStorageServing {
    static let namespace = "fieldlog-task-v1"
    static let project = UUID(uuidString: "22F02008-0000-4000-8000-000000000001")!
    static let otherProject = UUID(uuidString: "22F02008-0000-4000-8000-000000000002")!
    static let draft = UUID(uuidString: "22F02008-0000-4000-8000-000000000003")!
    static let title = "Valve \"北\""
    let repository: WorkspaceRepository
    private(set) var reads = 0
    private(set) var moves: [UUID] = []

    init(_ repository: WorkspaceRepository) {
        self.repository = repository
    }

    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        guard arguments.namespace == Self.namespace, arguments.key == "rows" else {
            throw CapabilityFailure.unavailable
        }
        let state = await repository.snapshot()
        let tasks = state.tasks(for: Self.project)
        guard tasks.count == 3, tasks.allSatisfy({
            (1...96).contains($0.title.utf8.count) && !$0.title.utf8.contains { $0 < 32 || $0 == 127 }
        }) else { throw CapabilityFailure.unavailable }
        reads += 1
        let rows = tasks.map { "\($0.id.uuidString)\t\($0.title)\n" }.joined()
        return .init(found: true, valueBase64: Data("\(state.revision)\n\(rows)".utf8).base64EncodedString())
    }

    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        guard arguments.namespace == Self.namespace, arguments.key.hasPrefix("move-"),
              let id = UUID(uuidString: String(arguments.key.dropFirst(5))),
              arguments.key == "move-" + id.uuidString,
              let bytes = Data(base64Encoded: arguments.valueBase64), bytes.count <= 20,
              let digits = String(data: bytes, encoding: .ascii), let expected = UInt64(digits),
              digits == String(expected), maximumEntries >= 1, maximumTotalBytes >= bytes.count else {
            throw CapabilityFailure.unavailable
        }
        do {
            // Check the expected revision, task membership and boundary inside the
            // same durable transaction. A replay can never move the row twice.
            try await repository.transact(expectedRevision: expected) { workspace in
                var order = workspace.tasks(for: Self.project).map(\.id)
                guard let index = order.firstIndex(of: id), index > 0 else {
                    throw FieldLogError.validation("This task cannot move farther.")
                }
                order.swapAt(index, index - 1)
                try workspace.reorderTasks(projectID: Self.project, ids: order)
            }
            moves.append(id)
            return .init(committed: true)
        } catch FieldLogError.staleRevision {
            return .init(committed: false)
        } catch FieldLogError.validation {
            return .init(committed: false)
        }
    }

    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        throw CapabilityFailure.unavailable
    }

    static func seed(_ repository: WorkspaceRepository) async throws -> Workspace {
        let now = Date(timeIntervalSince1970: 1_700_000_000)
        _ = try await repository.transact(expectedRevision: 0) { workspace in
            try workspace.createProject(id: Self.project, title: "Filter inspection", site: "North unit", now: now)
        }
        for (title, responsible) in [("Photograph meter", "Lin"), (Self.title, "Zoë"), ("File report", "Amir")] {
            _ = try await repository.transact { workspace in
                try workspace.saveTask(projectID: Self.project, title: title, responsible: responsible, now: now)
            }
        }
        _ = try await repository.transact { workspace in
            guard let first = workspace.tasks(for: Self.project).first else { throw FieldLogError.missingRecord }
            try workspace.toggleTask(first.id, now: now)
        }
        _ = try await repository.transact { workspace in
            try workspace.createProject(id: Self.otherProject, title: "Other unit", site: "South", now: now)
        }
        _ = try await repository.transact { workspace in
            try workspace.saveTask(projectID: Self.otherProject, title: Self.title, responsible: "Different project", now: now)
        }
        return try await repository.transact { workspace in
            try workspace.saveDraft(.init(id: Self.draft, projectID: Self.project,
                title: "Unsubmitted check", note: "Keep this line\nand 北.", category: .issue,
                occurredAt: now, updatedAt: now))
            workspace.restoration = .init(selectedProjectID: Self.project, openDraftID: Self.draft)
        }
    }
}
