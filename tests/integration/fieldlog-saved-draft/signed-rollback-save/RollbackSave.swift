import AppKit
import FieldLogModels
import FieldLogStorage
import Foundation
@testable import MixerCapabilityActivation
import MixerRuntimeIdentity
@testable import MixerUI
import MixerUpdates
import os

@main @MainActor enum RollbackSave {
    nonisolated private static let projectID = UUID(uuidString: "6BC5E772-D2FF-4563-9D46-7BE1812BBAA0")!
    nonisolated private static let draftID = UUID(uuidString: "6BC5E772-D2FF-4563-9D46-7BE1812BBAA1")!
    nonisolated private static let otherID = UUID(uuidString: "6BC5E772-D2FF-4563-9D46-7BE1812BBAA2")!
    private static let bundleID = "dev.mixer.fieldlog"
    private static let newNote = "Seal replaced. Étanchéité vérifiée."

    private struct Failure: Error, CustomStringConvertible {
        let description: String
        init(_ description: String) { self.description = description }
    }

    private struct DiskFile: Codable, Equatable {
        let sha256: String
        let inode: UInt64
        let bytes: Int

        init(_ url: URL) throws {
            let data = try Data(contentsOf: url)
            let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
            guard let inode = attributes[.systemFileNumber] as? NSNumber else {
                throw Failure("Missing inode for \(url.lastPathComponent)")
            }
            self.inode = inode.uint64Value
            bytes = data.count
            sha256 = ReleaseVerifier.sha256(data)
        }
    }

    private struct Checkpoint: Codable {
        let pid: Int32
        let workspace: Workspace
        let snapshot: DiskFile
        let photo: DiskFile
    }

    static func main() async {
        do {
            try await dispatch()
        } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(1)
        }
    }

    private static func dispatch() async throws {
        let args = Array(CommandLine.arguments.dropFirst())
        func url(_ index: Int) -> URL { URL(fileURLWithPath: args[index]) }
        switch args.first {
        case "sign" where args.count == 9:
            try AppleCommitMaterial.sign(fixtures: url(1), guest: url(2), output: url(3),
                engineHash: args[4], sourceHash: args[5], linkHash: args[6], revision: args[7],
                metadata: url(8), draftTools: true)
        case "save" where args.count == 4:
            try await save(material: url(1), root: url(2), checkpoint: url(3))
        case "cold" where args.count == 4:
            try await cold(material: url(1), root: url(2), checkpoint: url(3))
        default:
            throw Failure("Expected sign FIXTURES GUESTS MATERIAL ENGINE SOURCE LINK REVISION METADATA or {save|cold} MATERIAL WORKSPACE CHECKPOINT")
        }
    }

    private static func save(material: URL, root: URL, checkpoint: URL) async throws {
        let writes = OSAllocatedUnfairLock(initialState: 0)
        let repository = try WorkspaceRepository(directory: root) { point in
            if point == "before_write" { writes.withLock { $0 += 1 } }
        }
        let date = Date(timeIntervalSince1970: 1_700_000_061)
        try await repository.transact(expectedRevision: 0) { state in
            try state.createProject(id: projectID, title: "Pump station", site: "North plant", now: date)
            try state.saveDraft(EntryDraft(id: draftID, projectID: projectID, title: "Inspect valve",
                note: "Seal inspection at pump 4.", occurredAt: date, updatedAt: date))
            try state.saveDraft(EntryDraft(id: otherID, projectID: projectID, title: "Other draft",
                note: "Leave intact.", occurredAt: date, updatedAt: date))
            state.restoration = Restoration(selectedProjectID: projectID, openDraftID: draftID)
        }
        let jpeg = try makePhoto()
        let seeded = try await repository.addPhoto(jpeg: jpeg, to: draftID, now: date)
        let editorDraft = try selected(seeded)
        let photoURL = try await repository.photoURL(try attachmentID(editorDraft))
        let photo = try DiskFile(photoURL)
        let snapshotURL = root.appendingPathComponent("workspace.json")
        let seedFile = try DiskFile(snapshotURL)
        try require(seeded.revision == 2 && seeded.outbox.count == 1 && editorDraft.followUpRequired == nil
            && photo.sha256 == ReleaseVerifier.sha256(jpeg), "Unexpected seed")
        print("phase=seed pid=\(ProcessInfo.processInfo.processIdentifier) workspace=\(seeded.id) "
            + "draft=\(draftID) other=\(otherID) photo=\(photoURL.lastPathComponent) photoSHA256=\(photo.sha256) "
            + "photoBytes=\(photo.bytes) outbox=\(seeded.outbox[0].id) revision=2 fileSHA256=\(seedFile.sha256)")
        writes.withLock { $0 = 0 }

        let model = WorkspaceModel(repository: repository)
        await model.open()
        model.selectDraftEditor(editorDraft)
        try await withGuest(model, material, root, stages: [1, 2]) { owner, _ in
            _ = try await active(owner, material, sequence: 2, phase: "prior")
            try await frame(owner, node: "toggle", property: "label", expected: "Check saved draft")
        }
        try require(try DiskFile(snapshotURL) == seedFile && writes.withLock { $0 } == 0,
                    "Prior release changed the workspace")
        try await withGuest(model, material, root, stages: [3]) { owner, attachment in
            _ = try await active(owner, material, sequence: 3, phase: "optional-writer")
            try await frame(owner, node: "follow-up", property: "text", expected: "Follow-up unset")
            try await setFollowUp(owner, attachment: attachment)
        }
        var expected = seeded
        let index = try draftIndex(expected)
        expected.revision = 3
        expected.drafts[index].followUpRequired = true
        let optionalFile = try DiskFile(snapshotURL)
        let optional = try await repository.readCommittedSnapshot()
        try require(optional == expected && model.workspace == expected && writes.withLock { $0 } == 1
            && optionalFile != seedFile, "Signed optional writer changed more than follow-up")
        print("phase=optional-write revision=3 followUp=true writes=1 fileSHA256=\(optionalFile.sha256)")

        try await withGuest(model, material, root, stages: [4]) { owner, _ in
            let launch = try await active(owner, material, sequence: 4, phase: "rollback-before-save")
            try await frame(owner, node: "toggle", property: "label", expected: "Check saved draft")
            try await frame(owner, node: "validation", property: "text", expected: "Saved draft loaded")
            try require(try DiskFile(snapshotURL) == optionalFile && writes.withLock { $0 } == 1,
                        "Rollback activation changed the workspace")
            var edited = editorDraft
            edited.note = newNote
            let before = Date()
            // The ordinary EntryEditor onChange callback passes its existing draft copy.
            model.scheduleDraft(edited)
            await model.flush()
            let after = Date()
            let saved = try await repository.readCommittedSnapshot()
            let draft = try selected(saved)
            try require(edited.followUpRequired == nil && draft.followUpRequired == true,
                        "Ordinary save under rollback overwrote follow-up")
            try require((before...after).contains(draft.updatedAt), "Editor did not advance updatedAt")
            expected.revision = 4
            expected.drafts[index].note = newNote
            expected.drafts[index].updatedAt = draft.updatedAt
            try require(model.pendingSaves == 0 && model.saveError == nil && model.unsavedCount == 0
                && saved == expected && model.workspace == expected && writes.withLock { $0 } == 2,
                "Ordinary save changed unexpected records or wrote more than once")
            try require(try DiskFile(photoURL) == photo, "Ordinary save changed the attachment file")
            let activeAfterSave = try await active(owner, material, sequence: 4, phase: "rollback-after-save")
            try require(activeAfterSave == launch, "Rollback launch changed during the ordinary save")
            print("phase=ordinary-save revision=4 followUp=true editorInputFollowUp=nil writes=1 outboxDelta=0 sameRollbackLaunch=true")
        }

        let snapshot = try DiskFile(snapshotURL)
        try require(snapshot != optionalFile && writes.withLock { $0 } == 2,
                    "Retirement changed the write count")
        let savedCheckpoint = Checkpoint(pid: ProcessInfo.processInfo.processIdentifier, workspace: expected,
                                         snapshot: snapshot, photo: photo)
        try JSONEncoder().encode(savedCheckpoint).write(to: checkpoint, options: .withoutOverwriting)
        await repository.close()
        print("phase=save-process-closed revision=4 fileSHA256=\(snapshot.sha256)")
    }

    private static func cold(material: URL, root: URL, checkpoint: URL) async throws {
        let expected = try JSONDecoder().decode(Checkpoint.self, from: Data(contentsOf: checkpoint))
        let pid = ProcessInfo.processInfo.processIdentifier
        try require(pid != expected.pid, "Cold readback ran in the save process")
        let writes = OSAllocatedUnfairLock(initialState: 0)
        let repository = try WorkspaceRepository(directory: root) { point in
            if point == "before_write" { writes.withLock { $0 += 1 } }
        }
        let reopened = try await repository.readCommittedSnapshot()
        let draft = try selected(reopened)
        let snapshotURL = root.appendingPathComponent("workspace.json")
        let photoURL = try await repository.photoURL(try attachmentID(draft))
        try require(reopened.revision == 4 && reopened == expected.workspace && draft.followUpRequired == true
            && draft.note == newNote && reopened.outbox.count == 1 && reopened.entries.isEmpty,
            "Cold repository did not recover the complete saved workspace")
        try require(try DiskFile(snapshotURL) == expected.snapshot && DiskFile(photoURL) == expected.photo
            && NSBitmapImageRep(data: Data(contentsOf: photoURL))?.pixelsWide == 24,
            "Cold repository did not recover the exact workspace and JPEG files")
        print("phase=cold-read pid=\(pid) revision=4 followUp=true outbox=1 fileSHA256=\(expected.snapshot.sha256)")

        let model = WorkspaceModel(repository: repository)
        await model.open()
        model.selectDraftEditor(draft)
        try await withGuest(model, material, root, stages: []) { owner, _ in
            _ = try await active(owner, material, sequence: 4, phase: "cold-rollback-without-staging")
            try await frame(owner, node: "toggle", property: "label", expected: "Check saved draft")
        }
        try await withGuest(model, material, root, stages: [5]) { owner, _ in
            _ = try await active(owner, material, sequence: 5, phase: "re-upgrade")
            try await frame(owner, node: "follow-up", property: "text", expected: "Follow-up required")
        }
        let after = try await repository.readCommittedSnapshot()
        try require(try after == expected.workspace && DiskFile(snapshotURL) == expected.snapshot
            && DiskFile(photoURL) == expected.photo && writes.withLock { $0 } == 0,
            "Cold activation or re-upgrade wrote to the workspace")
        await repository.close()
        print("phase=re-upgrade-read revision=4 followUp=true writes=0 outboxDelta=0 unrelatedDraftAndJPEGUnchanged=true")
    }

    private static func withGuest(
        _ model: WorkspaceModel, _ material: URL, _ root: URL, stages: [Int],
        run: (CapabilityGuestUIRuntime, CapabilityGuestUIAttachmentIdentity) async throws -> Void
    ) async throws {
        let access = try await model.attachDraftGuest(projectID: projectID, draftID: draftID)
        var owner: CapabilityGuestUIRuntime?
        do {
            let opened = try await InstalledDraftGuest.open(materials: material, workspaceDirectory: root,
                storage: access, bundleID: bundleID)
            owner = opened
            for sequence in stages { try await InstalledDraftGuest.stage(sequence, in: material, on: opened) }
            let presentation = opened.presentation
            guard let attachment = presentation.claimNativeAttachment() else {
                throw Failure("Could not attach headless presentation witness")
            }
            defer { presentation.detachNativeAttachment(attachment) }
            _ = try await opened.start()
            try await eventually("Missing presentation ticket for headless display witness") {
                presentation.nativeDisplayTicket(attachment: attachment) != nil
            }
            guard let ticket = presentation.nativeDisplayTicket(attachment: attachment),
                  presentation.observeNativeDisplay(ticket) else {
                throw Failure("Headless display witness was rejected")
            }
            try await run(opened, attachment)
        } catch {
            let result = await model.finishDraftGuest(access, owner: owner)
            try require(result == .closed, "Guest retirement after failure returned \(result): \(error)")
            throw error
        }
        let result = await model.finishDraftGuest(access, owner: owner)
        try require(result == .closed, "Guest close returned \(result)")
        print("phase=owner-retired staged=\(stages)")
    }

    private static func active(
        _ owner: CapabilityGuestUIRuntime, _ material: URL, sequence: Int, phase: String
    ) async throws -> String {
        let variant = InstalledDraftGuest.variants[sequence - 1]
        let manifest = try Data(contentsOf: material.appendingPathComponent("\(variant).manifest.json"))
        let assignment = try Data(contentsOf: material.appendingPathComponent("sequence-\(sequence).assignment.json"))
        let payload = try Data(contentsOf: material.appendingPathComponent("\(variant).wasm"))
        let manifestValue = try StrictJSON.decode(CanonicalValue.self, from: manifest).object?["manifest"]
        guard let value = manifestValue, let release = value.object?["release_id"]?.text else {
            throw Failure("Missing \(variant) signed manifest")
        }
        let payloadHash = ReleaseVerifier.sha256(payload)
        let artifact = ReleaseVerifier.sha256(try value.canonicalCBOR())
        let expectedID = try CapabilityRecoveryCandidate.id(artifact: artifact, sequence: UInt64(sequence),
            manifest: manifest, assignment: assignment)
        try require(value.object?["payload_sha256"]?.text == payloadHash, "Payload differs from signed manifest")
        let deadline = ContinuousClock.now + .seconds(8)
        var state = await owner.recoverySnapshot()
        repeat {
            if !state.closed && state.activation.phase == .healthyGuest && state.activation.terminalCause == nil,
               state.acceptedSequence == UInt64(sequence), state.healthy == expectedID,
               state.activation.candidateID == expectedID, let launch = state.activation.launchID {
                print("phase=\(phase) sequence=\(sequence) release=\(release) artifactSHA256=\(artifact) "
                    + "payloadSHA256=\(payloadHash) candidate=\(expectedID) launch=\(launch)")
                return launch
            }
            if let cause = state.activation.terminalCause { throw Failure("\(phase) stopped: \(cause)") }
            try await Task.sleep(for: .milliseconds(10))
            state = await owner.recoverySnapshot()
        } while ContinuousClock.now < deadline
        throw Failure("\(phase) expected candidate \(expectedID) at sequence \(sequence), "
            + "observed sequence \(state.acceptedSequence), phase \(state.activation.phase), "
            + "active \(state.activation.candidateID ?? "nil"), healthy \(state.healthy ?? "nil")")
    }

    private static func frame(
        _ owner: CapabilityGuestUIRuntime, node: String, property: String, expected: String
    ) async throws {
        let presentation = owner.presentation
        try await eventually("Missing frame text: \(expected)") {
            presentation.renderHost?.snapshot.document.root.children.contains {
                $0.id == node && $0.properties[property] == .string(expected)
            } == true
        }
        print("frame=\(expected)")
    }

    private static func setFollowUp(
        _ owner: CapabilityGuestUIRuntime, attachment: CapabilityGuestUIAttachmentIdentity
    ) async throws {
        let presentation = owner.presentation
        try await eventually("Signed optional writer did not accept input") { presentation.inputEnabled }
        guard let host = presentation.renderHost, let identity = host.snapshot.identity(for: "toggle")
        else { throw Failure("Missing signed follow-up action") }
        let event = try host.route(UIEventEnvelope(revision: 1, identity: identity, event: .activate))
        presentation.actionHandler(host: host, attachment: attachment)(event)
        try await frame(owner, node: "follow-up", property: "text", expected: "Follow-up required")
    }

    private static func eventually(_ message: String, _ condition: () -> Bool) async throws {
        let deadline = ContinuousClock.now + .seconds(8)
        while !condition() {
            try require(ContinuousClock.now < deadline, message)
            try await Task.sleep(for: .milliseconds(10))
        }
    }

    private static func draftIndex(_ workspace: Workspace) throws -> Int {
        guard let index = workspace.drafts.firstIndex(where: { $0.id == draftID && $0.projectID == projectID })
        else { throw Failure("Selected draft is missing") }
        return index
    }

    private static func selected(_ workspace: Workspace) throws -> EntryDraft {
        workspace.drafts[try draftIndex(workspace)]
    }

    private static func attachmentID(_ draft: EntryDraft) throws -> UUID {
        guard draft.attachmentIDs.count == 1, let id = draft.attachmentIDs.first else {
            throw Failure("Expected one linked photo")
        }
        return id
    }

    private static func require(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
        guard try condition() else { throw Failure(message) }
    }

    private static func makePhoto() throws -> Data {
        guard let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 24, pixelsHigh: 16,
            bitsPerSample: 8, samplesPerPixel: 3, hasAlpha: false, isPlanar: false,
            colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)
        else { throw Failure("JPEG bitmap unavailable") }
        let blue = NSColor(deviceRed: 0, green: 0.25, blue: 1, alpha: 1)
        for y in 0..<16 {
            for x in 0..<24 { bitmap.setColor(blue, atX: x, y: y) }
        }
        guard let jpeg = bitmap.representation(using: .jpeg, properties: [:]) else {
            throw Failure("JPEG encoding failed")
        }
        return jpeg
    }
}
