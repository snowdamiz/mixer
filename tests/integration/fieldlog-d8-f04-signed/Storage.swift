import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilities
import MixerUpdates
import os

private struct PrePublicationRefusal: Error {}

final class SaveBoundary: Sendable {
    struct Observation: Sendable {
        var attempts = 0
        var publications = 0
        var staged = false
    }

    private let counts = OSAllocatedUnfairLock(initialState: Observation())
    private let resume = DispatchSemaphore(value: 0)
    var observation: Observation { counts.withLock { $0 } }

    func release() { resume.signal() }

    func writePhase(_ phase: String) throws {
        if phase == "after_rename" { counts.withLock { $0.publications += 1 } }
        guard phase == "before_rename" else { return }
        let count = counts.withLock {
            $0.attempts += 1
            $0.staged = true
            return $0.attempts
        }
        if count == 1 {
            guard resume.wait(timeout: .now() + 3) == .success else {
                throw CapabilityFailure.deadlineExceeded
            }
            throw PrePublicationRefusal()
        }
    }
}

actor TaskStorage: InstalledApplicationStorageServing {
    static let namespace = "fieldlog-d8-f04-task"
    static let project = UUID(uuidString: "5B7B803C-4740-4DC4-BBF9-2DA4F940285E")!
    static let other = UUID(uuidString: "D2C7DB17-7CB4-4DFE-B261-C3EE38247273")!
    static let title = "  Measure  日本語\nopening 🧪  "
    static let responsible = "  Rae  "
    static let baseRevision: UInt64 = 4
    static let date = Date(timeIntervalSince1970: 1_700_000_000)

    let repository: WorkspaceRepository
    let workspace: URL
    let initial: Data
    let boundary: SaveBoundary?
    private(set) var puts: [String] = []
    private(set) var confirmedRefusals = 0

    init(_ repository: WorkspaceRepository, workspace: URL, initial: Data, boundary: SaveBoundary?) {
        self.repository = repository
        self.workspace = workspace
        self.initial = initial
        self.boundary = boundary
    }

    func get(_ request: KVGetArguments) async throws -> KVGetResponse {
        try authorize(request.namespace, request.key)
        let state = await repository.snapshot()
        guard [Self.baseRevision, Self.baseRevision + 1].contains(state.revision) else {
            throw CapabilityFailure.unavailable
        }
        let slotFilled: UInt8 = state.revision == Self.baseRevision ? 0 : 1
        return .init(found: true, valueBase64: Data([slotFilled]).base64EncodedString())
    }

    func put(_ request: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        try authorize(request.namespace, request.key)
        guard let boundary else { throw CapabilityFailure.permissionDenied }
        guard let bytes = Data(base64Encoded: request.valueBase64), bytes.count <= 520,
              maximumEntries >= 1, bytes.count <= maximumTotalBytes else {
            throw CapabilityFailure.quotaExceeded
        }
        let fields = try JSONDecoder().decode([String].self, from: bytes)
        guard fields.count == 2 else { throw CapabilityFailure.permissionDenied }
        try Task.checkCancellation()
        puts.append(ReleaseVerifier.sha256(bytes))
        do {
            try await repository.transact(expectedRevision: Self.baseRevision) { state in
                try Task.checkCancellation()
                try state.saveTask(projectID: Self.project, title: fields[0], responsible: fields[1], now: Self.date)
            }
            return .init(committed: true)
        } catch is PrePublicationRefusal {
            let disk = try read(workspace, "workspace.json")
            let names = try FileManager.default.contentsOfDirectory(atPath: workspace.path)
            guard boundary.observation.publications == 0, disk == initial,
                  !names.contains(where: { $0.hasPrefix(".saving-") }) else {
                throw CapabilityFailure.ioFailure
            }
            confirmedRefusals += 1
            return .init(committed: false)
        }
    }

    func delete(_ request: KVDeleteArguments) async throws -> KVMutationResponse {
        throw CapabilityFailure.permissionDenied
    }

    private func authorize(_ namespace: String, _ key: String) throws {
        guard namespace == Self.namespace, key == "task" else { throw CapabilityFailure.permissionDenied }
    }

    static func seed(_ folder: URL) async throws {
        let repository = try WorkspaceRepository(directory: folder)
        try await repository.transact { try $0.createProject(id: project, title: "Selected project", site: "", now: date) }
        try await repository.transact { try $0.createProject(id: other, title: "Unrelated project", site: "", now: date) }
        try await repository.transact {
            try $0.saveTask(projectID: other, title: "Unrelated task", responsible: "Other owner", now: date)
        }
        try await repository.transact {
            try $0.saveTask(projectID: project, title: "Existing task", responsible: "Existing owner", now: date)
        }
        await repository.close()
    }
}
