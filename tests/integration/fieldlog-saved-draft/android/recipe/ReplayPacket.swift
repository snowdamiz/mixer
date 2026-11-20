import AppKit
import CryptoKit
import FieldLogHostTest
import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilities
@_spi(AndroidGuestUIV1) import MixerCapabilityActivation
import MixerRuntimeIdentity
import MixerUI

@_cdecl("mxish_swift_scalar_entry")
func rejectUnexpectedHostEntry(_: UInt64, _: UInt32) -> Int32 {
    Int32(MXUIT_INVALID.rawValue)
}

private struct ReplayError: Error, CustomStringConvertible { let description: String }

private actor StorageReads: InstalledApplicationStorageServing {
    let lease: any InstalledApplicationStorageServing
    private(set) var counts = [0, 0, 0]

    init(_ lease: any InstalledApplicationStorageServing) { self.lease = lease }

    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        counts[0] += 1
        return try await lease.get(arguments)
    }

    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        counts[1] += 1
        return try await lease.put(arguments, maximumTotalBytes: maximumTotalBytes, maximumEntries: maximumEntries)
    }

    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        counts[2] += 1
        return try await lease.delete(arguments)
    }
}

@main @MainActor struct ReplayPacket {
    static func main() async {
        do {
            try await replay()
        } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(EXIT_FAILURE)
        }
    }

    private static func replay() async throws {
        let delivery = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
        let directory = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
        let installation = CommandLine.arguments[3]
        let repository = try WorkspaceRepository(directory: directory.appendingPathComponent("workspace"))
        let editor = try await ProjectPresentation(repository: repository)
        let project = try value(editor.workspace.projects.first?.id, "project")
        let selected = UUID()
        let other = UUID()
        let photoBytes = try makeJPEG()
        _ = try await repository.transact { workspace in
            try workspace.saveDraft(EntryDraft(id: other, projectID: project, title: "Unselected draft"))
            try workspace.saveDraft(EntryDraft(id: selected, projectID: project, title: "Selected draft", note: "Original note"))
        }
        let seeded = try await repository.addPhoto(jpeg: photoBytes, to: selected)
        let draft = try value(seeded.drafts.first { $0.id == selected }, "selected draft")
        let photo = try await repository.photoURL(try value(draft.attachmentIDs.first, "attachment"))
        let workspaceFile = directory.appendingPathComponent("workspace/workspace.json")
        try await editor.reloadChecklist()
        try send(editor, "workspace.entries")
        try send(editor, "draft." + selected.uuidString.lowercased())
        try check(mxish_start() == 0, "Host presentation transport failed")

        let chapters: [(UInt64, String, Bool, Bool?)] = [
            (1, "baseline", true, nil), (2, "optional", true, true),
            (3, "baseline", true, true), (3, "baseline", false, true),
            (4, "optional", true, false),
        ]
        var previousCandidate: String?
        var candidates: Set<String> = []
        let selectedKey = KVGetArguments(namespace: "fieldlog-task-v1", key: "selected-draft")
        let otherDraftKey = KVGetArguments(namespace: "fieldlog-task-v1", key: other.uuidString.lowercased())
        var coldRollbackReadback = false
        for (sequence, variant, stage, expectedFlag) in chapters {
            let before = try await repository.readCommittedSnapshot()
            let beforeBytes = try Data(contentsOf: workspaceFile)
            let beforeDraftIndex = try value(before.drafts.firstIndex { $0.id == selected }, "selected draft index")
            let beforeFlag = before.drafts[beforeDraftIndex].followUpRequired
            let selectedLease = try await editor.attachSignedDraft()
            try await requireDenied { _ = try await selectedLease.get(otherDraftKey) }
            let lease = StorageReads(selectedLease)
            let owner = try await startOwner(delivery: delivery, directory: directory, installation: installation, storage: lease)
            do {
                let payload = try read(delivery, "\(variant).wasm")
                if stage {
                    try await owner.stage(manifest: read(delivery, "\(variant).manifest.json"),
                                          assignment: read(delivery, "sequence-\(sequence).assignment.json"), bytes: payload)
                }
                let start = try await owner.start()
                let candidate = try value(start.candidateID, "provisional candidate")
                try check(start.phase == .provisionalGuest, "Sequence \(sequence) did not start provisionally")
                let facade = owner.facade
                try await eventually("No hydrated frame for sequence \(sequence)") {
                    mxfield_recorded_probe(facade) > 0 || owner.recoverySnapshot().activation.terminalCause != nil
                }
                let first = try frame(facade)
                try check(first == expectedFrame(variant, started: false, flag: beforeFlag), "Wrong first frame \(first)")
                try check(try Data(contentsOf: workspaceFile) == beforeBytes && owner.recoverySnapshot().activation.phase == .provisionalGuest,
                          "First frame rewrote the draft or committed health before the witness")
                try check(await lease.counts == [1, 0, 0], "Hydration must issue one selected-draft read")
                try check(mxish_call_entry(facade, 10) == 0, "First-frame witness refused")
                try await eventually("Sequence \(sequence) did not commit health") {
                    owner.recoverySnapshot().activation.phase == .healthyGuest
                }
                let state = owner.recoverySnapshot()
                try check(state.healthy == candidate && state.acceptedSequence == sequence, "Durable candidate or sequence mismatch")
                if stage {
                    try check(candidates.insert(candidate).inserted && state.previousHealthy == previousCandidate,
                              "Assignment did not create the expected durable successor")
                } else {
                    try check(candidate == previousCandidate, "Offline startup did not reuse the cached rollback")
                }
                previousCandidate = candidate

                let previousProbe = mxfield_recorded_probe(facade)
                try await eventually("Sequence \(sequence) refused input") { mxish_call_entry(facade, 11) == 0 }
                try await eventually("Sequence \(sequence) did not render a successor") {
                    mxfield_recorded_probe(facade) > previousProbe || owner.recoverySnapshot().activation.terminalCause != nil
                }
                try check(mxfield_recorded_probe(facade) > previousProbe, "Sequence \(sequence) stopped before rendering a successor")
                let afterFrame = try frame(facade)
                try check(afterFrame == expectedFrame(variant, started: true, flag: expectedFlag), "Wrong action frame \(afterFrame)")
                try check(mxish_call_entry(facade, 10) == 0, "Successor witness refused")
                let calls = await lease.counts
                try check(calls == (variant == "optional" ? [2, 1, 0] : [2, 0, 0]), "Wrong read/write counts \(calls)")
                var expected = before
                if variant == "optional" {
                    expected.drafts[beforeDraftIndex].followUpRequired = expectedFlag
                    expected.revision += 1
                }
                let after = try await repository.readCommittedSnapshot()
                try check(after == expected, "Signed action changed the wrong FieldLog data")
                if variant == "baseline" {
                    try check(try Data(contentsOf: workspaceFile) == beforeBytes, "Read-only check rewrote the workspace")
                }
                try check(try Data(contentsOf: photo) == photoBytes, "Signed action modified JPEG data")
                try printJSON([
                    "sequence": sequence, "variant": variant, "staged": stage, "installation": installation,
                    "candidate": candidate, "beforeRevision": before.revision, "afterRevision": after.revision,
                    "payloadSHA256": hash(payload), "workspaceSHA256": hash(try Data(contentsOf: workspaceFile)),
                    "storedFollowUp": expectedFlag as Any? ?? NSNull(), "getPutDelete": calls,
                    "firstFrame": first, "actionFrame": afterFrame,
                ])
            } catch {
                let terminal = owner.recoverySnapshot().activation
                let retired = await owner.close()
                throw ReplayError(description: "Sequence \(sequence), staged=\(stage), retired=\(retired), activation=\(terminal): \(error)")
            }
            let retired = await owner.close()
            try check(retired && mxish_live_allocations() == 0, "Guest owner did not retire")
            editor.detachSignedDraft()
            try await requireDenied { _ = try await selectedLease.get(selectedKey) }
            try await editor.reloadChecklist()
            if sequence == 3 && stage {
                let before = try await repository.readCommittedSnapshot()
                try send(editor, "entry.\(selected.uuidString.lowercased()).note", .textChange, .string("Offline revised note"))
                try send(editor, "entry.saveDraft")
                try await editor.waitForSave()
                let after = try await repository.readCommittedSnapshot()
                try check(after.revision == before.revision + 1 && after.outbox == before.outbox &&
                          after.drafts.first { $0.id == selected }?.note == "Offline revised note" &&
                          after.drafts.first { $0.id == selected }?.followUpRequired == true &&
                          after.drafts.first { $0.id == other } == before.drafts.first { $0.id == other },
                          "Ordinary offline save changed another draft or lost the optional field")
            }
            if sequence == 3 && !stage {
                // Read the persisted snapshot without opening a second writer.
                let disk = try JSONDecoder().decode(Workspace.self, from: Data(contentsOf: workspaceFile))
                try disk.validate()
                let savedDraft = try value(disk.drafts.first { $0.id == selected }, "cold rollback draft")
                try check(try await repository.readCommittedSnapshot() == disk &&
                          savedDraft.note == "Offline revised note" && savedDraft.followUpRequired == true,
                          "Cold rollback readback lost the saved note or optional flag")
                coldRollbackReadback = true
            }
        }
        let final = try await repository.readCommittedSnapshot()
        await editor.close()
        let reopened = try WorkspaceRepository(directory: directory.appendingPathComponent("workspace"))
        let cold = try await reopened.readCommittedSnapshot()
        await reopened.close()
        let coldDraft = try value(cold.drafts.first { $0.id == selected }, "cold re-upgrade draft")
        try check(cold == final && coldDraft.note == "Offline revised note" && coldDraft.followUpRequired == false,
                  "Cold reopen lost the saved note or re-upgraded flag")
        try check(mxish_destructors() == UInt64(chapters.count), "Wrong guest destruction count")
        try printJSON(["status": "passed", "installation": installation, "nativeWriterCount": 1,
                       "ownersRetired": mxish_destructors(), "liveAllocations": mxish_live_allocations(),
                       "draftID": selected.uuidString, "otherDraftID": other.uuidString,
                       "jpegSHA256": hash(photoBytes), "outboxCount": final.outbox.count,
                       "ordinaryOfflineSave": true, "cachedRollback": true, "coldRollbackReadback": coldRollbackReadback,
                       "coldRepositoryReadback": true, "wrongDraftKeyRejected": true, "detachedLeaseRejected": true])
    }

    private static func startOwner(delivery: URL, directory: URL, installation: String, storage: StorageReads) async throws
        -> CapabilityGuestUIAndroidRuntime {
        let assets = delivery.appendingPathComponent("Installed")
        let identity = try read(assets, "identity.json")
        let runtime = try CapabilityRuntimeIdentity(json: identity).fingerprint
        let execution = try InstalledCapabilityExecution(identityJSON: identity, materials: [
            .init(role: .bridgePolicy, bytes: read(assets, "bridge.json")),
            .init(role: .configuration(capabilityID: CapabilitySchemas.storageID), bytes: read(assets, "storage.json")),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.storageID), bytes: read(assets, "storage-grant.json")),
        ], trustRootsJSON: read(assets, "roots.json"), privateContainer: directory,
           applicationStorage: .init(runtimeFingerprint: runtime, namespace: "fieldlog-task-v1", service: storage,
                                     allowsDeferredGuestUIStartup: true))
        return try await CapabilityGuestUIAndroidRuntime.open(configuration: .init(
            directory: directory.appendingPathComponent("recovery"), channel: "beta",
            installation: installation, observationSeconds: 5), execution: execution)
    }

    private static func send(_ editor: ProjectPresentation, _ id: String, _ event: UIEventKind = .activate, _ payload: UIValue = .null) throws {
        let snapshot = editor.snapshot
        let identity = try value(snapshot.identity(for: id), id)
        try editor.send(.init(revision: snapshot.document.revision, identity: identity, event: event, value: payload))
    }

    private static func frame(_ facade: UInt64) throws -> [String] {
        var data = [UInt8](repeating: 0, count: 8192)
        let count = mxfield_host_packet(facade, mxfield_recorded_probe(facade), &data, UInt32(data.count))
        try check(count > 0 && count <= data.count, "Missing frame")
        let document = try JSONSerialization.jsonObject(with: Data(data.prefix(Int(count)))) as? [String: Any]
        let root = document?["root"] as? [String: Any]
        let nodes = try value(root?["children"] as? [[String: Any]], "frame nodes")
        return try nodes.map {
            let properties = $0["properties"] as? [String: String]
            return try value(properties?["text"] ?? properties?["label"], "node label")
        }
    }

    private static func expectedFrame(_ variant: String, started: Bool, flag: Bool?) -> [String] {
        if variant == "baseline" {
            return [started ? "Ready to save entry" : "Saved draft loaded", "JPEG linked", "Check saved draft"]
        }
        let status = flag.map { $0 ? "Follow-up required" : "Follow-up not required" } ?? "Follow-up unset"
        return ["Ready to save entry", "JPEG linked", status, flag == true ? "Clear follow-up requirement" : "Mark follow-up required"]
    }

    private static func eventually(_ failure: String, _ predicate: () -> Bool) async throws {
        let deadline = ContinuousClock.now + .seconds(12)
        while !predicate() {
            try check(ContinuousClock.now < deadline, failure)
            try await Task.sleep(for: .milliseconds(10))
        }
    }

    private static func makeJPEG() throws -> Data {
        let image = try value(NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 24, pixelsHigh: 16,
            bitsPerSample: 8, samplesPerPixel: 3, hasAlpha: false, isPlanar: false, colorSpaceName: .deviceRGB,
            bytesPerRow: 0, bitsPerPixel: 0), "JPEG bitmap")
        for y in 0..<16 {
            for x in 0..<24 {
                var pixel = x < 12 ? [255, 0, 0] : [0, 255, 0]
                image.setPixel(&pixel, atX: x, y: y)
            }
        }
        return try value(image.representation(using: .jpeg, properties: [:]), "JPEG bytes")
    }

    private static func check(_ condition: Bool, _ message: String) throws {
        guard condition else { throw ReplayError(description: message) }
    }

    private static func requireDenied(_ operation: () async throws -> Void) async throws {
        do {
            try await operation()
            throw ReplayError(description: "Signed storage lease accepted an unauthorized read")
        } catch CapabilityFailure.permissionDenied {}
    }

    private static func value<T>(_ candidate: T?, _ label: String) throws -> T {
        guard let candidate else { throw ReplayError(description: "Missing \(label)") }
        return candidate
    }

    private static func read(_ directory: URL, _ name: String) throws -> Data {
        try Data(contentsOf: directory.appendingPathComponent(name))
    }

    private static func hash(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    private static func printJSON(_ value: [String: Any]) throws {
        var line = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        line.append(0x0a)
        try FileHandle.standardOutput.write(contentsOf: line)
    }
}
