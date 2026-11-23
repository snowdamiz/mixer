import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilities
import MixerUpdates

actor PagerStorage: InstalledApplicationStorageServing {
    static let namespace = "fieldlog-f20-v1"
    static let workspaceID = UUID(uuidString: "F2000000-0000-4000-8000-000000000003")!
    static let projectID = UUID(uuidString: "F2000000-0000-4000-8000-000000000001")!
    static let seedSHA256 = "ea178afd68bd143837e0ef09405ac99a6efe59563d238adad41dc8d6a9aa9a8c"
    private let repository: WorkspaceRepository
    private(set) var reads: [String] = []
    private(set) var refusedWrites = 0

    init(_ repository: WorkspaceRepository) { self.repository = repository }

    func get(_ request: KVGetArguments) async throws -> KVGetResponse {
        guard request.namespace == Self.namespace else { throw CapabilityFailure.unavailable }
        let state = await repository.snapshot()
        let drafts = state.drafts.filter { $0.projectID == Self.projectID }
        let records: [(UUID, String)]
        let total: Int
        if request.key == "workspace" {
            guard state.id == Self.workspaceID && state.revision == 1 else {
                throw CapabilityFailure.unavailable
            }
            records = []
            total = state.outbox.count
        } else if request.key.hasPrefix("draft-"),
           let id = UUID(uuidString: String(request.key.dropFirst(6))),
           let draft = drafts.first(where: { $0.id == id }) {
            records = [(id, draft.title), (id, draft.note)]
            total = 2
        } else {
            let parts = request.key.split(separator: "-")
            guard parts.count == 2, let page = Int(parts[1]), (0...2).contains(page) else {
                throw CapabilityFailure.unavailable
            }
            let all: [(UUID, String)]
            switch parts[0] {
            case "drafts":
                all = drafts.map { ($0.id, $0.title.isEmpty ? "Untitled draft" : $0.title) }
            case "entries":
                all = state.entries(for: Self.projectID).map {
                    ($0.id, $0.title + " · " + $0.category.rawValue + " · " + $0.occurredAt.formatted(.iso8601))
                }
            default: throw CapabilityFailure.unavailable
            }
            guard page * 20 < all.count else { throw CapabilityFailure.unavailable }
            records = Array(all.dropFirst(page * 20).prefix(20))
            total = all.count
        }
        guard records.allSatisfy({ $0.1.utf8.count <= 96 && !$0.1.contains("\n") }) else {
            throw CapabilityFailure.unavailable
        }
        reads.append(request.key)
        let wire = "\(total)\n\(records.count)\n" + records.map { "\($0.0.uuidString)\t\($0.1)\n" }.joined()
        return .init(found: true, valueBase64: Data(wire.utf8).base64EncodedString())
    }

    func put(_ request: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        refusedWrites += 1
        throw CapabilityFailure.unavailable
    }

    func delete(_ request: KVDeleteArguments) async throws -> KVMutationResponse {
        refusedWrites += 1
        throw CapabilityFailure.unavailable
    }

    static func seed(_ source: URL, into folder: URL) throws {
        let bytes = try Data(contentsOf: source)
        try check(ReleaseVerifier.sha256(bytes) == seedSHA256, "Installed F20 seed digest")
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false)
        try bytes.write(to: folder.appendingPathComponent("workspace.json"), options: .withoutOverwriting)
    }
}
