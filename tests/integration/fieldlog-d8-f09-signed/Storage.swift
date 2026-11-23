import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilities
import MixerUpdates

struct ArchivedPage: Decodable {
    struct Row: Decodable {
        let id: UUID
        let text: String
    }

    let position: String
    let rows: [Row]
}

struct ArchivedPages: Decodable {
    let projectID: UUID
    let before: [ArchivedPage]
    let after: [ArchivedPage]

    static func load(_ bytes: Data) throws -> Self {
        try check(ReleaseVerifier.sha256(bytes) == "f1a3b77a0ad0880fdd8da04748af4e0ebfc176bda87c4498b63d3393b50857d9",
                  "Archived F09 pages digest")
        return try JSONDecoder().decode(Self.self, from: bytes)
    }
}

actor TaskStorage: InstalledApplicationStorageServing {
    static let namespace = "fieldlog-f09-v1"
    static let workspaceID = UUID(uuidString: "F0900000-0000-4000-8000-000000000003")!
    static let project = UUID(uuidString: "F0900000-0000-4000-8000-000000000001")!
    static let target = UUID(uuidString: "F0900000-0000-4000-8000-000000000120")!
    static let neighbor = UUID(uuidString: "F0900000-0000-4000-8000-000000000119")!
    static let reorder = "task." + target.uuidString.lowercased() + ".up"
    private static let reorderKey = "move-up-" + target.uuidString
    static let seedSHA256 = "9f60598bdeed93f8e9ddf5d0a1b89e5f6b44d52d9f650108923e8fc1f0c21242"
    static let archivedMoveSHA256 = "98198e1cb6e6825cd8c9edeb3f71d2c6185f54c0a310d4a6b4640c8f89e979eb"

    let repository: WorkspaceRepository
    private let initialOrder: [UUID]
    private(set) var writes: [String] = []

    init(_ repository: WorkspaceRepository, pages: ArchivedPages) {
        self.repository = repository
        initialOrder = pages.before.flatMap(\.rows).map(\.id)
    }

    func get(_ request: KVGetArguments) async throws -> KVGetResponse {
        guard request.namespace == Self.namespace, request.key == "rows" else {
            throw CapabilityFailure.unavailable
        }
        let state = await repository.snapshot()
        let rows = state.tasks(for: Self.project)
        guard state.id == Self.workspaceID, rows.count == 23, Set(rows.map(\.id)) == Set(initialOrder),
              (1...2).contains(state.revision), state.outbox.count == 26 + Int(state.revision) else {
            throw CapabilityFailure.unavailable
        }
        let wire = "\(state.revision)\n" + rows.map {
            "\($0.id.uuidString)\t\($0.completed ? 1 : 0)|\($0.title)\n"
        }.joined()
        return .init(found: true, valueBase64: Data(wire.utf8).base64EncodedString())
    }

    func put(_ request: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        guard request.namespace == Self.namespace, request.key == Self.reorderKey,
              maximumEntries >= 1, let bytes = Data(base64Encoded: request.valueBase64),
              bytes.count <= min(maximumTotalBytes, 20), let text = String(data: bytes, encoding: .ascii),
              let expected = UInt64(text), text == String(expected) else { throw CapabilityFailure.unavailable }
        let initial = initialOrder
        do {
            try await repository.transact(expectedRevision: expected) { state in
                var order = state.tasks(for: Self.project).map(\.id)
                guard order == initial, order.count == 23,
                      order[19] == Self.neighbor, order[20] == Self.target else {
                    throw FieldLogError.validation("F09 move requires the archived boundary order.")
                }
                order.swapAt(19, 20)
                try state.reorderTasks(projectID: Self.project, ids: order)
            }
            writes.append(Self.reorder)
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
        try check(ReleaseVerifier.sha256(bytes) == seedSHA256, "Installed F09 seed digest")
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false)
        try bytes.write(to: folder.appendingPathComponent("workspace.json"), options: .withoutOverwriting)
    }
}
