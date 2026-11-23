import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilities
import MixerUpdates

actor TaskStorage: InstalledApplicationStorageServing {
    static let namespace = "fieldlog-f08-v1"
    static let workspaceID = UUID(uuidString: "F0800000-0000-4000-8000-000000000001")!
    static let project = UUID(uuidString: "F0800000-0000-4000-8000-000000000002")!
    static let roof = UUID(uuidString: "F0800000-0000-4000-8000-000000000004")!
    static let delivery = UUID(uuidString: "F0800000-0000-4000-8000-000000000005")!
    static let seedSHA256 = "fc96e23f6ae6cfdad5d14aca37c9890fc358c4268a3464eaf65e2909a546f239"
    static let initialOrder = [roof, delivery]
    static let completion = "complete-" + roof.uuidString
    static let reorder = "move-up-" + delivery.uuidString
    let repository: WorkspaceRepository
    private(set) var writes: [String] = []

    init(_ repository: WorkspaceRepository) { self.repository = repository }

    func get(_ request: KVGetArguments) async throws -> KVGetResponse {
        guard request.namespace == Self.namespace, request.key == "rows" else {
            throw CapabilityFailure.unavailable
        }
        let state = await repository.snapshot()
        let rows = state.tasks(for: Self.project)
        let eventKinds: [PendingChange.Kind] = [.projectCreated, .taskSaved, .entrySaved, .taskSaved, .taskOrderChanged]
        guard rows.count == 2, Set(rows.map(\.id)) == Set(Self.initialOrder),
              (3...5).contains(state.outbox.count),
              state.outbox.map(\.kind).elementsEqual(eventKinds.prefix(state.outbox.count)) else {
            throw CapabilityFailure.unavailable
        }
        let wire = "\(state.revision)\n\(state.outbox.count)\n"
            + rows.map { "\($0.id.uuidString)\t\($0.completed ? 1 : 0)|\($0.title)\n" }.joined()
        return .init(found: true, valueBase64: Data(wire.utf8).base64EncodedString())
    }

    func put(_ request: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        let completing = request.key == Self.completion
        guard completing || request.key == Self.reorder, request.namespace == Self.namespace,
              maximumEntries >= 1, let bytes = Data(base64Encoded: request.valueBase64),
              bytes.count <= min(maximumTotalBytes, 20), let text = String(data: bytes, encoding: .ascii),
              let expected = UInt64(text), text == String(expected) else { throw CapabilityFailure.unavailable }
        do {
            try await repository.transact(expectedRevision: expected) { state in
                let tasks = state.tasks(for: Self.project)
                guard tasks.map(\.id) == Self.initialOrder else {
                    throw FieldLogError.validation("F08 actions require the original task order.")
                }
                if completing {
                    guard !tasks[0].completed else { throw FieldLogError.validation("Task already completed.") }
                    try state.toggleTask(Self.roof)
                } else {
                    try state.reorderTasks(projectID: Self.project, ids: [Self.delivery, Self.roof])
                }
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

    static func seed(_ source: URL, into folder: URL) throws {
        let bytes = try Data(contentsOf: source)
        try check(ReleaseVerifier.sha256(bytes) == seedSHA256, "Installed F08 seed digest")
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false)
        try bytes.write(to: folder.appendingPathComponent("workspace.json"), options: .withoutOverwriting)
    }
}
