import Foundation
import MixerUpdates

func read(_ directory: URL, _ name: String) throws -> Data {
    try Data(contentsOf: directory.appendingPathComponent(name))
}

func check(_ condition: Bool, _ message: String) throws {
    guard condition else { throw UpdateError("f11.witness", message) }
}

func need<Value>(_ value: Value?, _ message: String) throws -> Value {
    guard let value else { throw UpdateError("f11.witness", message) }
    return value
}

import FieldLogModels
import FieldLogStorage
@testable @_spi(PrivateFieldLogEditor) import MixerCapabilityActivation
@testable @_spi(GuestUIV1) import MixerGuest
import MixerCapabilities
@_spi(PrivateFieldLogEditor) import MixerRuntimeIdentity

@MainActor
struct WitnessInput {
    static let installation = "fieldlog-f11-ios-private"
    static let wasmHash = "b3def2b5d11c0a350d33a44ff0cd55f4a7e97f6979e547c49ab13bde696d4fe5"
    let root: URL
    let workspace: URL
    let packet: URL

    init(run: UUID) throws {
        packet = try need(Bundle.main.resourceURL, "App resources").appendingPathComponent("SealedInput")
        root = URL.applicationSupportDirectory.appendingPathComponent("f11-" + run.uuidString)
        workspace = root.appendingPathComponent("workspace")
    }

    func open() async throws -> (CapabilityGuestUIRuntime, WorkspaceRepository, NoteStorage) {
        let seed = try read(packet, "workspace.json")
        try check(ReleaseVerifier.sha256(seed) == NoteStorage.seedHash, "Seed bytes")
        try FileManager.default.createDirectory(at: .applicationSupportDirectory, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        try FileManager.default.createDirectory(at: workspace, withIntermediateDirectories: false)
        try seed.write(to: workspace.appendingPathComponent("workspace.json"), options: .withoutOverwriting)

        let identity = try read(packet, "identity.json")
        let descriptor = try CapabilityRuntimeIdentity(privateDevelopmentFieldLogNoteFixtureJSON: identity)
        try check(descriptor.capabilityExecution.turnMilliseconds == 50, "VM turn limit")
        try check((try? CapabilityRuntimeIdentity(json: identity)) == nil, "Stock identity selected F11")
        let repository = try WorkspaceRepository(directory: workspace)
        let storage = NoteStorage(repository)
        let files: [(String, CapabilityMaterialFile.Role)] = [
            ("bridge.json", .bridgePolicy),
            ("storage.json", .configuration(capabilityID: CapabilitySchemas.storageID)),
            ("storage-grant.json", .installedGrant(capabilityID: CapabilitySchemas.storageID)),
        ]
        let materials = try files.map { name, role in
            CapabilityMaterialFile(role: role, bytes: try read(packet, name))
        }
        let roots = try read(packet, "roots.json")
        try check((try? InstalledCapabilityExecution(identityJSON: identity, materials: materials,
            trustRootsJSON: roots, privateContainer: root)) == nil, "Stock execution selected F11")
        let execution = try InstalledCapabilityExecution(privateDevelopmentFieldLogNoteFixtureJSON: identity,
            materials: materials, trustRootsJSON: roots, privateContainer: root, repository: storage)
        let configuration = CapabilityColdStartConfiguration(directory: root.appendingPathComponent("recovery"),
            channel: "beta", installation: Self.installation, observationSeconds: 1)
        let owner = try await CapabilityGuestUIRuntime.open(privateDevelopmentFieldLogNoteFixture: execution,
                                                           configuration: configuration)
        do {
            let wasm = try read(packet, "payload.wasm")
            try check(ReleaseVerifier.sha256(wasm) == Self.wasmHash, "Wasm bytes")
            try await owner.beginDownload(signedManifest: read(packet, "signed-manifest.json"),
                                          signedAssignment: read(packet, "assignment.json"))
            try await owner.appendDownload(wasm, atOffset: 0)
            try await owner.finishDownload()
            let staged = await owner.recoverySnapshot()
            let started = try await owner.start()
            try check(started.launchID != nil && started.candidateID == staged.staged, "Signed candidate launch")
            return (owner, repository, storage)
        } catch {
            await owner.close()
            await repository.close()
            throw error
        }
    }

    func verify(_ live: Workspace, revision: UInt64) throws {
        let baseline = try JSONDecoder().decode(Workspace.self, from: read(packet, "workspace.json"))
        let note = Data(GuestUIFieldLogNoteFixture.edited.utf8)
        try check(live.id == NoteStorage.workspaceID && live.revision == revision
            && live.restoration.selectedProjectID == NoteStorage.projectID, "Workspace identity or revision")
        let target = NoteStorage.draftID
        try check(live.schema == baseline.schema && live.createdAt == baseline.createdAt
            && live.projects == baseline.projects && live.tasks == baseline.tasks
            && live.attachments == baseline.attachments
            && live.drafts.filter { $0.id != target } == baseline.drafts.filter { $0.id != target }
            && live.entries.filter { $0.id != target } == baseline.entries, "Unrelated workspace records changed")
        if revision == 2 {
            let draft = try need(live.drafts.first { $0.id == NoteStorage.draftID }, "Cold draft missing")
            try check(live.restoration.openDraftID == draft.id && draft.projectID == NoteStorage.projectID
                && Data(draft.note.utf8) == note && live.outbox == baseline.outbox, "Cold draft bytes and outbox")
            return
        }
        let entry = try need(live.entries.first { $0.id == NoteStorage.draftID }, "Cold committed entry missing")
        let event = try need(live.outbox.last, "Linked entrySaved missing")
        try check(live.restoration.openDraftID == nil && !live.drafts.contains { $0.id == entry.id }
            && entry.projectID == NoteStorage.projectID && Data(entry.note.utf8) == note
            && live.outbox.count == baseline.outbox.count + 1
            && Array(live.outbox.dropLast()) == baseline.outbox
            && event.recordID == entry.id && event.kind == .entrySaved && event.revision == 3,
            "Committed bytes or entrySaved linkage")
    }

    func coldCommit() async throws -> String {
        let receipt = try JSONDecoder().decode(CommitReceipt.self, from: read(root, "commit.json"))
        try check(receipt.pid != ProcessInfo.processInfo.processIdentifier, "Committed readback requires a new process")
        let repository = try WorkspaceRepository(directory: workspace)
        let snapshot = await repository.snapshot()
        await repository.close()
        try verify(snapshot, revision: 3)
        try check(ReleaseVerifier.sha256(read(workspace, "workspace.json")) == receipt.workspaceHash,
                  "Cold committed workspace bytes differed")
        return receipt.workspaceHash
    }
}

struct CommitReceipt: Codable {
    let pid: Int32
    let workspaceHash: String
}
