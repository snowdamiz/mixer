import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilities

actor TaskStorage: InstalledApplicationStorageServing {
    static let namespace = "fieldlog-task-v1"
    static let workspaceID = UUID(uuidString: "302B5A08-D339-4D3F-9F7C-52448F69B4F6")!
    static let project = UUID(uuidString: "5B7B803C-4740-4DC4-BBF9-2DA4F940285E")!
    static let target = UUID(uuidString: "36D8162B-B3D1-409B-8C25-55EC275017A5")!
    static let other = UUID(uuidString: "D2C7DB17-7CB4-4DFE-B261-C3EE38247273")!
    static let initialOrder = [target, other]
    static let swappedOrder = [other, target]
    let repository: WorkspaceRepository
    private(set) var writes: [String] = []

    init(_ repository: WorkspaceRepository) { self.repository = repository }

    func get(_ request: KVGetArguments) async throws -> KVGetResponse {
        guard request.namespace == Self.namespace, request.key == "rows" else {
            throw CapabilityFailure.unavailable
        }
        let state = await repository.snapshot()
        let rows = state.tasks(for: Self.project)
        guard rows.count == 2, Set(rows.map(\.id)) == Set(Self.initialOrder) else {
            throw CapabilityFailure.unavailable
        }
        let wire = "\(state.revision)\n" + rows.map { "\($0.id.uuidString)\t\($0.title)\n" }.joined()
        return .init(found: true, valueBase64: Data(wire.utf8).base64EncodedString())
    }

    func put(_ request: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        let offset = request.key.hasPrefix("move-down-") ? 1 : -1
        let prefix = offset == 1 ? "move-down-" : "move-up-"
        guard request.key.hasPrefix(prefix),
              let task = UUID(uuidString: String(request.key.dropFirst(prefix.count))),
              request.key == prefix + task.uuidString, Self.initialOrder.contains(task) else {
            throw CapabilityFailure.unavailable
        }
        guard request.namespace == Self.namespace, maximumEntries >= 1,
              let bytes = Data(base64Encoded: request.valueBase64), bytes.count <= min(maximumTotalBytes, 20),
              let text = String(data: bytes, encoding: .ascii), let expected = UInt64(text),
              text == String(expected) else { throw CapabilityFailure.unavailable }
        do {
            try await repository.transact(expectedRevision: expected) { state in
                var ids = state.tasks(for: Self.project).map(\.id)
                guard let index = ids.firstIndex(of: task), ids.indices.contains(index + offset) else {
                    throw FieldLogError.validation("This task cannot move farther.")
                }
                ids.swapAt(index, index + offset)
                try state.reorderTasks(projectID: Self.project, ids: ids)
            }
            writes.append(request.key)
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

    static func seed(_ folder: URL) throws {
        let date = Date(timeIntervalSince1970: 1_700_000_000)
        var state = Workspace(id: workspaceID, createdAt: date)
        try state.createProject(id: project, title: "Historical task ordering", site: "", now: date)
        state.revision = 1
        for (title, id) in [("Measure opening", target), ("Take field notes", other)] {
            try state.saveTask(projectID: project, title: title, responsible: "", now: date)
            state.tasks[state.tasks.count - 1].id = id
            state.outbox[state.outbox.count - 1].recordID = id
            state.revision += 1
        }
        try state.validate()
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false)
        try encode(state).write(to: folder.appendingPathComponent("workspace.json"), options: .withoutOverwriting)
    }
}
