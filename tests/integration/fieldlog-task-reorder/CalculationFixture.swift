#if DEBUG && FIELDLOG_CALCULATION_FIXTURE
import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilities
import MixerUpdates

public enum CalculationFixture {
    public static let bundleID = "dev.fieldlog.generatedr90.calculation"
    public static let projectID = UUID(uuidString: "22F02008-0000-4000-8000-000000000001")!
    public static let taskID = UUID(uuidString: "91094B1F-51E9-42AD-9CF1-64055970E7CB")!
    public static let predecessor = UUID(uuidString: "D8FD094D-6A4E-4B03-930E-1C4BEE0FB8A7")!
    public static let actionNode = "toggle"
    public static let actionID = "draft.action"
    private static let key = "move-" + taskID.uuidString

    public static func readSeed(_ file: URL) throws -> Data {
        let source = try FileHandle(forReadingFrom: file)
        defer { try? source.close() }
        let bytes = try source.read(upToCount: 3531) ?? Data()
        guard bytes.count == 3530,
              ReleaseVerifier.sha256(bytes) == "f202de8c0101f04e7d6624f90a7f521ce416eb36ae3994d7b1f0692380043260" else {
            throw UpdateError("fieldlog.rowSeed", "The row fixture requires the exact saved workspace")
        }
        return bytes
    }

    public static func storage(repository: WorkspaceRepository,
                               task: WorkTask) throws -> any InstalledApplicationStorageServing {
        guard task.projectID == projectID, task.id == taskID else {
            throw UpdateError("fieldlog.rowFixture", "Incorrect reorder project or task")
        }
        return RowStorage(repository: repository)
    }

    static func admits(_ payload: Data) -> Bool {
        switch (payload.count, ReleaseVerifier.sha256(payload)) {
        case (6_485, "c76c22bfa086ce6b19775f282cf36f8690464c63374085046fbc337226c49b42"),
             (9_908, "de422cba560554bc8642a4c3205c320a7ce870a8a05ff61be3231bbe5a9da9ab"):
            return true
        default:
            return false
        }
    }

    private struct RowStorage: InstalledApplicationStorageServing {
        let repository: WorkspaceRepository

        func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
            guard arguments.namespace == FieldLogDraftStorage.namespace, arguments.key == "rows" else {
                throw CapabilityFailure.permissionDenied
            }
            let state = try await repository.readCommittedSnapshot()
            let rows = state.tasks(for: projectID)
            guard rows.count == 3, rows.allSatisfy({
                (1...96).contains($0.title.utf8.count) && !$0.title.utf8.contains { $0 < 32 || $0 == 127 }
            }) else { throw CapabilityFailure.unavailable }
            let body = rows.map { "\($0.id.uuidString)\t\($0.title)\n" }.joined()
            return .init(found: true, valueBase64: Data("\(state.revision)\n\(body)".utf8).base64EncodedString())
        }

        func put(_ arguments: KVPutArguments, maximumTotalBytes: Int,
                 maximumEntries: Int) async throws -> KVMutationResponse {
            guard arguments.namespace == FieldLogDraftStorage.namespace, arguments.key == key,
                  let bytes = Data(base64Encoded: arguments.valueBase64), bytes.count <= min(20, maximumTotalBytes),
                  maximumEntries >= 1, let text = String(data: bytes, encoding: .ascii),
                  let expected = UInt64(text), text == String(expected) else {
                throw CapabilityFailure.permissionDenied
            }
            do {
                try await repository.transact(expectedRevision: expected) { workspace in
                    var order = workspace.tasks(for: projectID).map(\.id)
                    guard order.count == 3, order[1] == predecessor, order[2] == taskID else {
                        throw FieldLogError.validation("The reviewed adjacent rows are no longer in their original order.")
                    }
                    order.swapAt(1, 2)
                    try workspace.reorderTasks(projectID: projectID, ids: order)
                }
                return .init(committed: true)
            } catch FieldLogError.staleRevision {
                return .init(committed: false)
            } catch FieldLogError.validation {
                return .init(committed: false)
            }
        }

        func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
            throw CapabilityFailure.permissionDenied
        }
    }
}
#endif
