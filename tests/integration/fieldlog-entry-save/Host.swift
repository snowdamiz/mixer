import AppKit
import Crypto
import FieldLogFeatures
import FieldLogHostTest
import FieldLogInstalledGuest
import FieldLogModels
import FieldLogStorage
import Foundation
@_spi(AndroidGuestUIV1) import MixerCapabilityActivation
import MixerCapabilities
import MixerRuntimeIdentity
import MixerUI
import os

private let oldInputToken = OSAllocatedUnfairLock(initialState: UInt64(0))

@_cdecl("mxish_swift_scalar_entry")
func checkStaleInput(_ facade: UInt64, _ kind: UInt32) -> Int32 {
    guard kind == 20 else { return Int32(MXUIT_INVALID.rawValue) }
    return mxis_guest_ui_witness(facade, mxish_last_id(facade, 1), oldInputToken.withLock { $0 },
                                 UInt32(MXIS_WITNESS_TOGGLE_TAPPED.rawValue))
}

struct TrialError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

enum Trial {
    static let channel = "beta"
    static let materials: [(String, CapabilityMaterialFile.Role)] = [
        ("bridge.json", .bridgePolicy),
        ("http.json", .configuration(capabilityID: CapabilitySchemas.httpID)),
        ("storage.json", .configuration(capabilityID: CapabilitySchemas.storageID)),
        ("http-grant.json", .installedGrant(capabilityID: CapabilitySchemas.httpID)),
        ("storage-grant.json", .installedGrant(capabilityID: CapabilitySchemas.storageID)),
    ]

    static func read(_ directory: URL, _ name: String) throws -> Data {
        try Data(contentsOf: directory.appendingPathComponent(name))
    }

    static func open(directory: URL, assets: URL, storage: DecisionReads) async throws -> CapabilityGuestUIAndroidRuntime {
        let identity = try read(assets, "identity.json")
        let execution = try InstalledCapabilityExecution(identityJSON: identity, materials: materials.map { name, role in
            try .init(role: role, bytes: read(assets, name))
        }, trustRootsJSON: read(assets, "roots.json"), privateContainer: directory,
           applicationStorage: .init(runtimeFingerprint: CapabilityRuntimeIdentity(json: identity).fingerprint,
               namespace: FieldLogDraftStorage.namespace, service: storage, allowsDeferredGuestUIStartup: true))
        return try await CapabilityGuestUIAndroidRuntime.open(configuration: .init(
            directory: directory.appendingPathComponent("recovery"), channel: channel,
            installation: "fieldlog-entry-decision-local", observationSeconds: 1), execution: execution)
    }
}

actor DecisionReads: InstalledApplicationStorageServing {
    private let lease: any InstalledApplicationStorageServing
    private let malformedTurn: Bool
    private(set) var calls = [0, 0, 0]
    private(set) var packetSizes: [Int] = []

    init(_ lease: any InstalledApplicationStorageServing, malformedTurn: Bool) {
        self.lease = lease
        self.malformedTurn = malformedTurn
    }

    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        calls[0] += 1
        let call = calls[0]
        let response = try await lease.get(arguments)
        guard let bytes = Data(base64Encoded: response.valueBase64), bytes.count == 9, response.found else {
            throw TrialError("Selected draft exposed an invalid facts packet")
        }
        packetSizes.append(bytes.count)
        guard malformedTurn, call == 2 else { return response }
        var malformed = bytes
        malformed[8] |= 0x80
        return .init(found: true, valueBase64: malformed.base64EncodedString())
    }

    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        calls[1] += 1
        return try await lease.put(arguments, maximumTotalBytes: maximumTotalBytes, maximumEntries: maximumEntries)
    }

    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        calls[2] += 1
        return try await lease.delete(arguments)
    }
}

@MainActor private final class Effects {
    private(set) var count = 0
    func save(_ intent: EntrySaveIntent) -> EntrySaveResult {
        count += 1
        return .failed("Effect observed without writing")
    }
}

@main @MainActor enum Host {
    nonisolated static let fieldLogRevision = "552559d2d3278abb9b1aa7dcf0288102c09a202b"
    nonisolated static let variants = ["decision"]
    nonisolated private static let project = UUID()
    nonisolated private static let draftID = UUID()
    nonisolated private static let otherDraft = UUID()
    nonisolated private static let originalTitle = " \t "
    nonisolated private static let originalNote = "e\u{301}\r\nKeep these bytes. 🛠"
    private static let required = "Entry title can't be empty."
    private static let titleTooLong = "Entry title is too long (maximum 160 UTF-8 bytes)."
    private static let titleNUL = "Entry title contains an unsupported character."
    private static let noteTooLong = "Note is too long (maximum 100000 UTF-8 bytes)."
    private static let noteNUL = "Note contains an unsupported character."
    private static let invalidDate = "Choose a valid entry date."
    private static let eligible = "Entry is eligible to save."
    private static let unavailable = "Selected draft unavailable."
    private static let key = KVGetArguments(namespace: FieldLogDraftStorage.namespace, key: SelectedDraftBinding.entrySaveDecisionKey)

    static func main() async {
        do {
            let args = CommandLine.arguments
            if args.count == 7, args[1] == "sign" {
                try signReleases(fixtures: url(args[2]), guests: url(args[3]), output: url(args[4]),
                                 archive: args[5], binary: args[6])
            } else if args.count == 4, args[1] == "run" {
                try await replay(assets: url(args[2]), directory: url(args[3]))
            } else {
                throw TrialError("Expected sign <fixtures> <guest> <output> <VM hash> <host hash> or run <assets> <directory>")
            }
        } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(EXIT_FAILURE)
        }
    }

    private static func url(_ path: String) -> URL { URL(fileURLWithPath: path, isDirectory: true) }

    private static func check(_ condition: Bool, _ message: String) throws {
        guard condition else { throw TrialError(message) }
    }

    private static func denied<T>(_ run: () async throws -> T) async throws {
        do {
            _ = try await run()
            throw TrialError("Read-only or stale authority was accepted")
        } catch CapabilityFailure.permissionDenied {}
    }

    private static func eventually(_ message: String, _ condition: () -> Bool) async throws {
        let deadline = ContinuousClock.now + .seconds(5)
        while !condition() {
            try check(ContinuousClock.now < deadline, message)
            try await Task.sleep(for: .milliseconds(10))
        }
    }

    private static func nativeControls() async throws {
        let oversizeNote = String(repeating: "é", count: 50_000) + "\0"
        let nonfinite = Date(timeIntervalSinceReferenceDate: .infinity)
        let tests: [(String, String, String, Date, UUID, EntrySaveIntent.Kind, FieldLogError?)] = [
            ("scope first", "\0", oversizeNote, nonfinite, UUID(), .commit, .missingRecord),
            ("raw bytes before trim and later failures", String(repeating: " ", count: 161), oversizeNote,
             nonfinite, project, .commit, .validation(titleTooLong)),
            ("commit required before note size", " ", oversizeNote, nonfinite, project, .commit, .validation(required)),
            ("title NUL before note size", "\0", oversizeNote, nonfinite, project, .commit, .validation(titleNUL)),
            ("note size before NUL and date", "x", oversizeNote, nonfinite, project, .commit, .validation(noteTooLong)),
            ("note NUL before date", "x", "\0", nonfinite, project, .commit, .validation(noteNUL)),
            ("finite date", "x", "", nonfinite, project, .commit, .validation(invalidDate)),
            ("draft blank allowed", "", "", Date(), project, .draft, nil),
        ]
        for (label, title, note, date, scope, kind, expected) in tests {
            let draft = EntryDraft(projectID: project, title: title, note: note, occurredAt: date)
            var actual: FieldLogError?
            do { try EntrySaveIntent(projectID: scope, draft: draft, kind: kind).validate() }
            catch let error as FieldLogError { actual = error }
            try check(actual == expected, "Wrong native error for \(label): \(String(describing: actual))")
        }

        let effects = Effects()
        let editor = try EntryEditor(projectID: project, draft: EntryDraft(projectID: project, title: originalTitle)) {
            await effects.save($0)
        }
        try editor.commitDraft()
        await editor.waitForSave()
        try check(editor.state.failure == required && !editor.state.saving && effects.count == 0, "Blank commit launched an effect")
        try editor.changeTitle("Eligible")
        try editor.commitDraft()
        await editor.waitForSave()
        try check(effects.count == 1 && !editor.state.saving, "Positive native editor did not run exactly one effect")
        try editor.close()
        print("native=scope,title-size,commit-required,title-NUL,note-size,note-NUL,date,draft-blank blankEffects=0 eligibleEffects=1")
    }

    private static func replay(assets: URL, directory: URL) async throws {
        try await nativeControls()
        try check(mxish_start() == 0, "Host witness transport failed")
        let workspaceDir = directory.appendingPathComponent("workspace", isDirectory: true)
        let workspaceFile = workspaceDir.appendingPathComponent("workspace.json")
        let seed = try WorkspaceRepository(directory: workspaceDir)
        let jpeg = try makeJPEG()
        _ = try await seed.transact(expectedRevision: 0) { workspace in
            try workspace.createProject(id: project, title: "North plant", site: "Pump 4")
            try workspace.saveDraft(EntryDraft(id: draftID, projectID: project, title: originalTitle, note: originalNote))
            try workspace.saveDraft(EntryDraft(id: otherDraft, projectID: project, title: "Different draft"))
            workspace.restoration.selectedProjectID = project
            workspace.restoration.openDraftID = draftID
        }
        let original = try await seed.addPhoto(jpeg: jpeg, to: draftID)
        await seed.close()
        let raw = try Data(contentsOf: workspaceFile)
        let identity = try fileIdentity(workspaceFile)
        try check(original.outbox.count == 1 && original.entries.isEmpty, "Missing outbox or unexpected seed entry")

        let cases: [(String, String, String, String?)] = [
            ("blank", originalTitle, originalNote, required),
            ("161 UTF-8 bytes", String(repeating: "é", count: 80) + "x", originalNote, titleTooLong),
            ("mixed blank and oversize", String(repeating: " ", count: 161), originalNote, titleTooLong),
            ("mixed blank and note NUL", originalTitle, "a\0b", required),
            ("note NUL", "Inspection", "a\0b", noteNUL),
            ("U+200B", "\u{200B}", originalNote, required),
            ("U+FEFF", "\u{FEFF}", originalNote, nil),
            ("eligible at byte limits", String(repeating: "é", count: 80), String(repeating: "é", count: 50_000), nil),
        ]
        for chapter in ["decision", "malformed", "stale"] {
            let repository = try WorkspaceRepository(directory: workspaceDir)
            let editor = try await ProjectPresentation(repository: repository)
            let restored = editor.entryState?.draft
            try check(restored?.id == draftID && restored?.title.utf8.elementsEqual(originalTitle.utf8) == true
                      && restored?.note.utf8.elementsEqual(originalNote.utf8) == true, "Cold editor did not restore the exact draft")
            let photo = try await repository.photoURL(original.attachments[0].id)
            let lease = try await editor.attachEntrySaveDecision()
            try await denied { try await lease.get(.init(namespace: key.namespace, key: "selected-draft")) }
            try await denied { try await lease.put(.init(namespace: key.namespace, key: key.key, valueBase64: "AQ=="),
                                                   maximumTotalBytes: 9, maximumEntries: 1) }
            try await denied { try await lease.delete(.init(namespace: key.namespace, key: key.key)) }
            let reads = DecisionReads(lease, malformedTurn: chapter == "malformed")
            let privateDir = directory.appendingPathComponent(chapter, isDirectory: true)
            try FileManager.default.createDirectory(at: privateDir, withIntermediateDirectories: false)
            let owner = try await Trial.open(directory: privateDir, assets: assets, storage: reads)
            let facade = owner.facade
            do {
                try await owner.stage(manifest: Trial.read(assets, "decision.manifest.json"),
                                      assignment: Trial.read(assets, "sequence-1.assignment.json"),
                                      bytes: Trial.read(assets, "decision.wasm"))
                let start = try await owner.start()
                try check(start.phase == .provisionalGuest && start.candidateID != nil, "Owner did not start provisionally")
                try await eventually("No hydrated frame") { mxfield_recorded_probe(facade) > 0 }
                try check(try frame(facade) == ["Saved draft loaded", "Check entry"], "Wrong hydrated frame")
                try await witness(facade, command: 10)
                try await eventually("Guest did not reach healthy installed state") {
                    owner.recoverySnapshot().activation.phase == .healthyGuest
                }
                try check(owner.recoverySnapshot().healthy == start.candidateID && owner.recoverySnapshot().acceptedSequence == 1,
                          "Installed assignment did not settle")

                if chapter == "decision" {
                    for (label, title, note, expected) in cases {
                        try send(editor, field("title"), .textChange, .string(title))
                        try send(editor, field("note"), .textChange, .string(note))
                        guard let liveDraft = editor.entryState?.draft else { throw TrialError("Live draft missing") }
                        try check(liveDraft.title.utf8.elementsEqual(title.utf8) && liveDraft.note.utf8.elementsEqual(note.utf8),
                                  "Editor changed input for \(label)")
                        let intent = EntrySaveIntent(projectID: project, draft: liveDraft, kind: .commit)
                        let commit = try envelope(editor.snapshot, "entry.commit", .activate, .null)
                        if let expected {
                            do {
                                try editor.send(commit)
                                throw TrialError("Invalid Commit was routed for \(label)")
                            } catch UIRoutingError.disabledNode {}
                            do {
                                try intent.validate()
                                throw TrialError("Invalid intent passed for \(label)")
                            } catch FieldLogError.validation(let actual) {
                                try check(actual == expected, "Wrong validation error for \(label): \(actual)")
                            }
                        } else {
                            try intent.validate()
                            try check(try editor.snapshot.route(commit).actionID == "entry.commit",
                                      "Eligible native Commit was disabled for \(label)")
                        }
                        try await tap(facade, expected: [expected ?? eligible, "Check entry"])
                        print("liveCase=\(label) decision=\(expected ?? eligible)")
                    }
                    try await checkDateCorrection(editor, facade: facade)
                } else {
                    if chapter == "stale" {
                        try send(editor, "draft." + otherDraft.uuidString.lowercased())
                        try check(editor.entryState?.draft.id == otherDraft, "Selection did not change")
                        try await denied { try await lease.get(key) }
                    }
                    try await tap(facade, expected: [unavailable])
                }
                let calls = await reads.calls
                let sizes = await reads.packetSizes
                let expectedSizes = chapter == "stale" ? 1 : calls[0]
                try check(calls == [chapter == "decision" ? 1 + cases.count + 3 : 2, 0, 0]
                          && sizes == Array(repeating: 9, count: expectedSizes), "Bad capability accounting: \(calls), \(sizes)")
                try check(try await repository.readCommittedSnapshot() == original, "Repository state changed")
                try check(try Data(contentsOf: workspaceFile) == raw && fileIdentity(workspaceFile) == identity
                          && Data(contentsOf: photo) == jpeg, "Decision changed workspace or photo on disk")
                print("chapter=\(chapter) getPutDelete=\(calls) factsBytes=\(sizes) diskUntouched=true")
            } catch {
                let terminal = owner.recoverySnapshot().activation
                let retired = await owner.close()
                await editor.close()
                throw TrialError("\(chapter) retired=\(retired) activation=\(terminal): \(error)")
            }
            let retired = await owner.close()
            try check(retired && mxish_live_allocations() == 0, "Owner or transport leaked")
            editor.detachSignedDraft()
            try await denied { try await lease.get(key) }
            await editor.close()
        }

        let reopened = try WorkspaceRepository(directory: workspaceDir)
        let readback = try await reopened.readCommittedSnapshot()
        await reopened.close()
        try check(readback == original && mxish_destructors() == 3, "Reopen or owner destruction count differed")
        try check(try Data(contentsOf: workspaceFile) == raw, "Cold reopen bytes differed")
        let hash = SHA256.hash(data: raw).map { String(format: "%02x", $0) }.joined()
        print("reopen=exact workspaceSHA256=\(hash) outbox=\(readback.outbox.count) entries=\(readback.entries.count) ownersRetired=3 liveAllocations=0")
    }

    private static func checkDateCorrection(_ editor: ProjectPresentation, facade: UInt64) async throws {
        let title = "Inspection"
        let malformedDate = "2025-02-29T14:30:00+05:30"
        let correctedDate = "2024-02-29T14:30:00+05:30"
        let dateStatus = "Enter a complete valid date and time with Z or a known ±HH:MM offset, and at most 3 fractional digits. Save is blocked; your input is retained."
        try send(editor, field("title"), .textChange, .string(title))
        try send(editor, field("date"), .textChange, .string(malformedDate))
        let invalid = editor.snapshot
        let fields = invalid.document.root.children.flatMap(\.children).flatMap(\.children)
        try check(fields.first { $0.id == "entry.date.error" }?.properties["text"] == .string(dateStatus)
                  && fields.first { $0.id == field("date") }?.properties["value"] == .string(malformedDate),
                  "Native editor lost the date error or the malformed input")
        do {
            _ = try invalid.route(envelope(invalid, "entry.commit", .activate, .null))
            throw TrialError("Native Commit was enabled with malformed date text")
        } catch UIRoutingError.disabledNode {}
        try await tap(facade, expected: [invalidDate, "Check entry"])
        print("liveCase=malformed date decision=\(invalidDate)")

        try send(editor, field("title"), .textChange, .string(originalTitle))
        try await tap(facade, expected: [required, "Check entry"])
        print("liveCase=malformed date and blank title decision=\(required)")

        try send(editor, field("title"), .textChange, .string(title))
        try send(editor, field("date"), .textChange, .string(correctedDate))
        let corrected = editor.snapshot
        try check(corrected.identity(for: "entry.date.error") == nil
                  && corrected.route(envelope(corrected, "entry.commit", .activate, .null)).actionID == "entry.commit",
                  "Native editor did not clear the date error and enable Commit")
        try await tap(facade, expected: [eligible, "Check entry"])
        print("liveCase=corrected date decision=\(eligible) sameOwnerAndLease=true")
    }

    private static func makeJPEG() throws -> Data {
        guard let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 2, pixelsHigh: 2,
            bitsPerSample: 8, samplesPerPixel: 3, hasAlpha: false, isPlanar: false,
            colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0) else {
            throw TrialError("Could not allocate fixture image")
        }
        for y in 0..<2 {
            for x in 0..<2 { bitmap.setColor(NSColor(deviceRed: 1, green: 0.5, blue: 0, alpha: 1), atX: x, y: y) }
        }
        guard let jpeg = bitmap.representation(using: .jpeg, properties: [:]) else {
            throw TrialError("Could not encode fixture JPEG")
        }
        return jpeg
    }

    private static func fileIdentity(_ file: URL) throws -> [String] {
        let info = try FileManager.default.attributesOfItem(atPath: file.path)
        return [FileAttributeKey.systemFileNumber, .modificationDate, .size].map { String(describing: info[$0]) }
    }

    private static func field(_ name: String) -> String { "entry." + draftID.uuidString.lowercased() + "." + name }

    private static func send(_ editor: ProjectPresentation, _ id: String,
                             _ event: UIEventKind = .activate, _ value: UIValue = .null) throws {
        try editor.send(envelope(editor.snapshot, id, event, value))
    }

    private static func envelope(_ snapshot: UIRenderSnapshot, _ id: String,
                                 _ event: UIEventKind, _ value: UIValue) throws -> UIEventEnvelope {
        guard let identity = snapshot.identity(for: id) else { throw TrialError("Missing identity for \(id)") }
        return .init(revision: snapshot.document.revision, identity: identity, event: event, value: value)
    }

    private static func frame(_ facade: UInt64) throws -> [String] {
        var bytes = [UInt8](repeating: 0, count: 4096)
        let count = mxfield_host_packet(facade, mxfield_recorded_probe(facade), &bytes, UInt32(bytes.count))
        guard count > 0, count <= bytes.count,
              let json = try JSONSerialization.jsonObject(with: Data(bytes.prefix(Int(count)))) as? [String: Any],
              let root = json["root"] as? [String: Any],
              let nodes = root["children"] as? [[String: Any]] else { throw TrialError("Missing captured frame") }
        return try nodes.map { node in
            guard let properties = node["properties"] as? [String: String],
                  let text = properties["text"] ?? properties["label"] else { throw TrialError("Missing frame text") }
            return text
        }
    }

    private static func witness(_ facade: UInt64, command: UInt32) async throws {
        try await eventually("Witness \(command) was refused") { mxish_call_entry(facade, command) == 0 }
    }

    private static func tap(_ facade: UInt64, expected: [String]) async throws {
        let previous = mxfield_recorded_probe(facade)
        let oldInput = mxish_last_id(facade, 2)
        try await witness(facade, command: 11)
        try await eventually("No action successor") { mxfield_recorded_probe(facade) > previous }
        let actual = try frame(facade)
        try check(actual == expected, "Wrong action frame \(actual), expected \(expected)")
        try await witness(facade, command: 10)
        oldInputToken.withLock { $0 = oldInput }
        try check(mxish_call_entry(facade, 20) == Int32(MXUIT_STALE.rawValue), "Stale input was accepted")
    }
}
