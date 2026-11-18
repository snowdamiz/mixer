import AppKit
import Crypto
import FieldLogModels
import FieldLogStorage
import FieldLogDraftIntegration
import Foundation
import FieldLogHostTest
@_spi(AndroidGuestUIV1) import MixerCapabilityActivation

@_cdecl("mxish_swift_scalar_entry")
func hostEntry(_ facade: UInt64, _ kind: UInt32) -> Int32 {
    let display = kind == 10
    return mxfield_witness(facade, mxish_last_id(facade, 1), mxish_last_id(facade, display ? 3 : 2), display ? 1 : 0)
}

@main
enum Host {
    static let fieldLogRevision = "552559d2d3278abb9b1aa7dcf0288102c09a202b"
    static let draftID = UUID(uuidString: "552559D2-D327-48AB-9B1A-A7DCF0288102")!
    static let projectID = UUID(uuidString: "552559D2-D327-48AB-9B1A-A7DCF0288103")!
    static let date = Date(timeIntervalSince1970: 1_700_000_000)
    static let variants = ["baseline", "corrected", "optional", "corrected", "optional"]

    static func check(_ value: Bool, _ message: String) throws {
        guard value else { throw TrialError(message) }
    }

    static func eventually(_ message: String, _ predicate: () -> Bool) async throws {
        let clock = ContinuousClock()
        let deadline = clock.now + .seconds(8)
        while !predicate() {
            guard clock.now < deadline else { throw TrialError(message) }
            try await Task.sleep(for: .milliseconds(10))
        }
    }

    static func frame(_ facade: UInt64, probe: UInt64) throws -> [String] {
        var bytes = [UInt8](repeating: 0, count: 8192)
        let count = mxfield_host_packet(facade, probe, &bytes, UInt32(bytes.count))
        guard count > 0, count <= bytes.count,
              let json = try JSONSerialization.jsonObject(with: Data(bytes.prefix(Int(count)))) as? [String: Any],
              let root = json["root"] as? [String: Any],
              let nodes = root["children"] as? [[String: Any]], (3...4).contains(nodes.count)
        else { throw TrialError("Missing FieldLog bridge frame") }
        return try nodes.map { node in
            guard let properties = node["properties"] as? [String: String],
                  let text = properties["text"] ?? properties["label"] else { throw TrialError("Missing node text") }
            return text
        }
    }

    static func selected(_ workspace: Workspace) throws -> EntryDraft {
        guard let draft = workspace.drafts.first(where: { $0.id == draftID && $0.projectID == projectID }) else {
            throw TrialError("Saved draft missing")
        }
        return draft
    }

    @MainActor
    static func appCheck(_ model: WorkspaceModel, projectID: UUID) async throws -> String {
        do {
            try await model.checkSavedDraft(projectID: projectID, draftID: draftID)
            return "Ready to save entry"
        } catch FieldLogError.validation(let message) {
            try check(message == "Entry title can't be empty.", "Unexpected app validation")
            return "Entry title is required"
        }
    }

    static func fileIdentity(_ url: URL) throws -> [String] {
        let info = try FileManager.default.attributesOfItem(atPath: url.path)
        return [FileAttributeKey.systemFileNumber, .modificationDate, .size].map {
            String(describing: info[$0])
        }
    }

    static func makePhoto() throws -> Data {
        guard let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 24, pixelsHigh: 16,
            bitsPerSample: 8, samplesPerPixel: 3, hasAlpha: false, isPlanar: false, colorSpaceName: .deviceRGB,
            bytesPerRow: 0, bitsPerPixel: 0) else { throw TrialError("JPEG bitmap unavailable") }
        let orange = NSColor(deviceRed: 1, green: 0.5, blue: 0, alpha: 1)
        let blue = NSColor(deviceRed: 0, green: 0.25, blue: 1, alpha: 1)
        for y in 0..<16 {
            for x in 0..<24 {
                bitmap.setColor(x < 12 ? orange : blue, atX: x, y: y)
            }
        }
        guard let jpeg = bitmap.representation(using: .jpeg, properties: [:]) else {
            throw TrialError("JPEG encoding failed")
        }
        return jpeg
    }

    static func seed(_ directory: URL, jpeg: Data) async throws -> Workspace {
        let repository = try WorkspaceRepository(directory: directory)
        do {
            _ = try await repository.transact(expectedRevision: 0) { state in
                try state.createProject(id: projectID, title: "Pump station", site: "North plant", now: date)
                try state.saveDraft(EntryDraft(id: draftID, projectID: projectID, title: " \t ", note: "Seal inspection at pump 4.",
                    category: .observation, occurredAt: date, updatedAt: date))
                state.restoration.openDraftID = draftID
            }
            let result = try await repository.addPhoto(jpeg: jpeg, to: draftID, now: date)
            await repository.close()
            return result
        } catch {
            await repository.close()
            throw error
        }
    }

    static func disk(_ url: URL) throws -> Data { try Data(contentsOf: url) }
    static func hash(_ bytes: Data) -> String { SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined() }

    static func action(_ facade: UInt64) async throws -> [String] {
        let previous = mxfield_recorded_probe(facade)
        try await eventually("Draft input refused") { mxish_call_entry(facade, 11) == 0 }
        try await eventually("Draft successor frame timed out") { mxfield_recorded_probe(facade) > previous }
        let applied = try frame(facade, probe: mxfield_recorded_probe(facade))
        try check(mxish_call_entry(facade, 10) == 0, "Successor witness refused")
        return applied
    }

    static func expectedFrame(_ validation: String, optional: Bool, followUp: Bool?) -> [String] {
        let common = [validation, "JPEG linked"]
        if !optional { return common + ["Check saved draft"] }
        if let followUp {
            return common + (followUp
                ? ["Follow-up required", "Clear follow-up requirement"]
                : ["Follow-up not required", "Mark follow-up required"])
        }
        return common + ["Follow-up unset", "Mark follow-up required"]
    }

    static func run(assets: URL, directory: URL, offline: Bool) async throws {
        let jpegFile = directory.appendingPathComponent("fixture.jpg")
        let jpeg = offline ? try disk(jpegFile) : try makePhoto()
        if !offline { try jpeg.write(to: jpegFile, options: .withoutOverwriting) }
        try check(mxish_start() == 0, "Transport setup failed")
        let workspaceDir = directory.appendingPathComponent("workspace")
        let workspaceFile = workspaceDir.appendingPathComponent("workspace.json")
        if !offline {
            let seeded = try await seed(workspaceDir, jpeg: jpeg)
            let draft = try selected(seeded)
            try check(seeded.revision == 2 && seeded.outbox.count == 1 && draft.attachmentIDs.count == 1 &&
                draft.followUpRequired == nil && seeded.restoration.openDraftID == draftID, "Wrong seed")
            try disk(workspaceFile).write(to: directory.appendingPathComponent("seed.json"), options: .withoutOverwriting)
        }
        let cycles = offline ? [6] : Array(1...5)
        let followUpBefore: [Bool?] = [nil, nil, nil, true, true, false]
        let followUpAfter: [Bool?] = [nil, nil, true, true, false, false]
        var lastHealthy: String?
        var healthyIDs: Set<String> = []
        for sequence in cycles {
            let repo = try WorkspaceRepository(directory: workspaceDir)
            let adapter = ObservedStorage(FieldLogDraftStorage(repository: repo, projectID: projectID, draftID: draftID))
            let owner = try await Trial.open(privateDirectory: directory, assets: assets, workspace: adapter)
            do {
                let before = try await repo.readCommittedSnapshot()
                let draft = try selected(before)
                let photo = try await repo.photoURL(draft.attachmentIDs[0])
                let raw = try disk(workspaceFile)
                let checkpoint = sequence == 1 ? "seed.json" : "sequence-\(sequence - 1)-workspace.json"
                try check(try disk(directory.appendingPathComponent(checkpoint)) == raw,
                    "Reopened workspace differs from the preceding committed snapshot")
                try check(draft.followUpRequired == followUpBefore[sequence - 1], "Reopen lost or changed the optional field")
                let workspaceIdentity = try fileIdentity(workspaceFile)
                let photoIdentity = try fileIdentity(photo)
                let model = await WorkspaceModel(repository: repo)
                await model.open()
                let validation = try await appCheck(model, projectID: projectID)
                try check(validation == "Entry title is required", "App check accepted whitespace title")
                do {
                    _ = try await appCheck(model, projectID: UUID())
                    throw TrialError("App check accepted a draft from another project")
                } catch FieldLogError.missingRecord {}
                try check(try disk(workspaceFile) == raw && fileIdentity(workspaceFile) == workspaceIdentity,
                    "App check wrote the workspace")
                try check(try disk(photo) == jpeg && fileIdentity(photo) == photoIdentity, "App check wrote the JPEG")
                try check(try disk(photo) == jpeg, "Original JPEG differs before release")
                let variant = variants[min(sequence, 5) - 1]
                if !offline {
                    try await owner.stage(manifest: Trial.read(assets, variant + ".manifest.json"),
                        assignment: Trial.read(assets, "sequence-\(sequence).assignment.json"),
                        bytes: Trial.read(assets, variant + ".wasm"))
                }
                let start = try await owner.start()
                guard start.phase == .provisionalGuest, let candidate = start.candidateID else {
                    throw TrialError("Draft guest did not start: \(start)")
                }
                let facade = owner.facade
                try await eventually("No hydrated draft frame") {
                    mxfield_recorded_probe(facade) > 0 || owner.recoverySnapshot().activation.terminalCause != nil
                }
                let first = try frame(facade, probe: mxfield_recorded_probe(facade))
                let expectedValidation = sequence == 1 ? "Ready to save entry" : validation
                try check(first == expectedFrame(variant == "optional" ? validation : "Saved draft loaded", optional: variant == "optional",
                    followUp: draft.followUpRequired), "Wrong hydrated frame: \(first)")
                try check(try disk(workspaceFile) == raw, "First frame changed persisted draft")
                try check(owner.recoverySnapshot().activation.phase == .provisionalGuest, "Health before witness")
                try check(mxish_call_entry(facade, 10) == 0, "First witness refused")
                try await eventually("Health did not commit") { owner.recoverySnapshot().activation.phase == .healthyGuest }
                let installed = owner.recoverySnapshot()
                try check(installed.healthy == candidate && installed.acceptedSequence == UInt64(min(sequence, 5)),
                    "Unexpected installed candidate or high-water")
                if !offline {
                    try check(healthyIDs.insert(candidate).inserted && installed.previousHealthy == lastHealthy,
                        "Unexpected durable candidate succession")
                }
                lastHealthy = candidate

                let hydrationCalls = await adapter.calls
                try check(hydrationCalls == [1, 0, 0], "Expected one installed read for hydration")
                var expected = before
                var successor: [String]?
                if !offline {
                    successor = try await action(facade)
                    if variant == "optional" {
                        let enabled = sequence == 3
                        expected.drafts[0].followUpRequired = enabled
                        expected.revision += 1
                        try check(successor == expectedFrame(validation, optional: true, followUp: enabled),
                            "Optional edit not rendered")
                    } else {
                        try check(successor == expectedFrame(expectedValidation, optional: false, followUp: nil),
                            "Draft check did not render its result")
                    }
                }
                let calls = await adapter.calls
                let expectedCalls = offline ? [1, 0, 0] : (variant == "optional" ? [2, 1, 0] : [2, 0, 0])
                try check(calls == expectedCalls, "Unexpected installed storage calls: \(calls)")
                let after = try await repo.readCommittedSnapshot()
                let committed = try disk(workspaceFile)
                try check(after == expected, "Unexpected FieldLog mutation")
                if expected == before {
                    try check(committed == raw && fileIdentity(workspaceFile) == workspaceIdentity,
                        "Read-only check rewrote the workspace")
                }
                try check(try disk(photo) == jpeg && fileIdentity(photo) == photoIdentity, "Original linked JPEG changed")
                try committed.write(to: directory.appendingPathComponent("sequence-\(sequence)-workspace.json"), options: .withoutOverwriting)
                let saved = try selected(after)
                try check(saved.followUpRequired == followUpAfter[sequence - 1], "Unexpected observed follow-up value")
                let observation: [String: Any] = [
                    "launch": sequence, "acceptedSequence": installed.acceptedSequence, "release": variant,
                    "candidate": candidate, "payloadSHA256": hash(try Trial.read(assets, variant + ".wasm")),
                    "workspaceSHA256": hash(committed), "workspaceRevision": after.revision,
                    "draftID": saved.id.uuidString, "projectID": saved.projectID.uuidString, "title": saved.title,
                    "note": saved.note, "category": saved.category.rawValue, "photoID": saved.attachmentIDs[0].uuidString,
                    "photoFilename": photo.lastPathComponent, "photoSHA256": hash(jpeg), "photoBytes": jpeg.count,
                    "outboxIDs": after.outbox.map { $0.id.uuidString }, "followUpRequired": saved.followUpRequired as Any? ?? NSNull(),
                    "firstFrame": first, "appValidation": validation, "successorFrame": successor as Any? ?? NSNull(),
                    "installedGetPutDelete": calls, "workspaceFileUntouched": expected == before,
                    "reopenedFromExactCheckpoint": true, "jpegFileUntouched": true
                ]
                let encoded = try JSONSerialization.data(withJSONObject: observation, options: [.sortedKeys])
                print(String(decoding: encoded, as: UTF8.self))
            } catch {
                let state = owner.recoverySnapshot().activation
                let retired = await owner.close()
                if retired { await repo.close() }
                throw TrialError("Sequence \(sequence) retired=\(retired) terminal=\(String(describing: state.terminalCause)) bridge=\(String(describing: state.firstBridgeFailure)) UI=\(String(describing: state.firstUIProtocolFailure)) error=\(error)")
            }
            let retired = await owner.close()
            try check(retired && mxish_live_allocations() == 0, "Owner or transport leaked")
            await repo.close()
        }
        try check(mxish_destructors() == UInt64(cycles.count), "Wrong consuming destruction count")
        print("owners_retired=\(cycles.count) live_allocations=0")
        if offline {
            try await checkValidSavedDraft(in: directory.appendingPathComponent("valid-title-control"))
        }
    }

    @MainActor
    static func checkValidSavedDraft(in directory: URL) async throws {
        let repo = try WorkspaceRepository(directory: directory)
        do {
            _ = try await repo.transact { workspace in
                try workspace.createProject(id: projectID, title: "Pump station", site: "North plant", now: date)
                try workspace.saveDraft(EntryDraft(id: draftID, projectID: projectID, title: " Inspection "))
            }
            let model = WorkspaceModel(repository: repo)
            await model.open()
            let file = directory.appendingPathComponent("workspace.json")
            let before = try disk(file)
            let identity = try fileIdentity(file)
            try await model.checkSavedDraft(projectID: projectID, draftID: draftID)
            try check(try disk(file) == before && fileIdentity(file) == identity, "Valid title check wrote workspace")
            print("valid_saved_title=accepted workspace_untouched=true")
        } catch {
            await repo.close()
            throw error
        }
        await repo.close()
    }

    static func main() async {
        do {
            let args = CommandLine.arguments
            if args.count == 7, args[1] == "sign" {
                try signReleases(fixtures: URL(fileURLWithPath: args[2]), guests: URL(fileURLWithPath: args[3]),
                    output: URL(fileURLWithPath: args[4]), archive: args[5], binary: args[6])
            } else if args.count == 4, ["run", "offline"].contains(args[1]) {
                try await run(assets: URL(fileURLWithPath: args[2]), directory: URL(fileURLWithPath: args[3]),
                    offline: args[1] == "offline")
            } else {
                throw TrialError("Pass sign, run, or offline with the scenario paths")
            }
        } catch {
            FileHandle.standardError.write(Data("FAIL: \(error)\n".utf8))
            Foundation.exit(1)
        }
    }
}
