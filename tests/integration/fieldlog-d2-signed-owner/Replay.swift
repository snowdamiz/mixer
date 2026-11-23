import AppKit
import Crypto
import FieldLogFeatures
import FieldLogHostTest
import FieldLogInstalledGuest
import FieldLogModels
import FieldLogStorage
import Foundation
import MixerAndroid
import MixerCapabilities
import MixerUI
import Synchronization

struct TrialError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

enum Trial {
    static let channel = "beta"
    static let materials: [(String, Int)] = [("bridge.json", 0), ("storage.json", 0)]
    static func read(_ root: URL, _ file: String) throws -> Data {
        try Data(contentsOf: root.appendingPathComponent(file))
    }
}

private let ordinaryOwner = Mutex<UUID?>(nil)
private let staleInput = Mutex<UInt64>(0)

private func ordinarySurface(_ context: Int64, _ operation: Int32, _ owner: UnsafePointer<UInt8>?,
                             _ count: Int, _ packet: UnsafePointer<UInt8>?, _ packetCount: Int,
                             _ appearance: UnsafePointer<UInt8>?, _ appearanceCount: Int) -> Int32 {
    guard context == 1, let owner, count == 36,
          let id = UUID(uuidString: String(decoding: UnsafeBufferPointer(start: owner, count: count), as: UTF8.self))
    else { return 1 }
    return ordinaryOwner.withLock { current in
        switch operation {
        case 0: current = id
        case 1: if current != id || packet == nil || packetCount <= 0 { return 1 }
        case 2: if current != id { return 1 }; current = nil
        default: return 1
        }
        return 0
    }
}

@_cdecl("mxish_swift_scalar_entry")
func savedDraftWitness(_ facade: UInt64, _ kind: UInt32) -> Int32 {
    let attachment = mxish_last_id(facade, 1)
    let input = mxish_last_id(facade, 2)
    switch kind {
    case 20:
        return mxis_guest_ui_witness(facade, attachment, staleInput.withLock { $0 }, 2)
    case 21:
        return mxis_guest_ui_witness(facade, attachment + 1, input, 2)
    default: return -1
    }
}

@main @MainActor
enum Host {
    nonisolated static let variants = ["optional"]
    nonisolated static let fieldLogRevision = "74cdeca2ed0d4b0eb6b1bc1a6c5fa278b8ee498a"
    static let bundle = "dev.fieldlog.generatedr90"
    static let installation = "778e1d11-85fe-4423-aa28-59a8fa71feda"
    nonisolated static let project = UUID(uuidString: "68000000-0000-4000-8000-000000000001")!
    nonisolated static let primary = UUID(uuidString: "68000000-0000-4000-8000-000000000002")!
    nonisolated static let other = UUID(uuidString: "68000000-0000-4000-8000-000000000003")!
    nonisolated static let date = Date(timeIntervalSince1970: 1_700_000_000)
    nonisolated static let privateTitle = "Private fixture title Å"
    nonisolated static let privateNote = "Private fixture note 確"
    static let get = KVGetArguments(namespace: FieldLogDraftStorage.namespace, key: "selected-draft")

    static func check(_ truth: @autoclosure () throws -> Bool, _ message: String) throws {
        guard try truth() else { throw TrialError(message) }
    }

    static func wait(_ message: String, until predicate: () throws -> Bool) async throws {
        let deadline = ContinuousClock.now + .seconds(8)
        while try !predicate() {
            guard ContinuousClock.now < deadline else { throw TrialError(message) }
            try await Task.sleep(for: .milliseconds(10))
        }
    }

    static func fileIdentity(_ file: URL) throws -> [String] {
        let metadata = try FileManager.default.attributesOfItem(atPath: file.path)
        return [SHA256.hash(data: try Data(contentsOf: file)).map { String(format: "%02x", $0) }.joined(),
                String(describing: metadata[.systemFileNumber]), String(describing: metadata[.modificationDate])]
    }

    static func committedFile(_ root: URL) throws -> [String] {
        try fileIdentity(root.appendingPathComponent("FieldLog/workspace.json"))
    }

    static func seed(_ root: URL) async throws {
        let repository = try WorkspaceRepository(directory: root.appendingPathComponent("FieldLog"))
        _ = try await repository.transact(expectedRevision: 0) {
            try $0.createProject(id: project, title: "Replay workspace", site: "Local", now: date)
            try $0.saveDraft(.init(id: primary, projectID: project, title: privateTitle,
                                   note: privateNote, category: .observation, occurredAt: date, updatedAt: date))
            try $0.saveDraft(.init(id: other, projectID: project, title: "Other saved draft",
                                   category: .observation, occurredAt: date, updatedAt: date))
            $0.restoration.openDraftID = primary
        }
        guard let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 4, pixelsHigh: 4,
            bitsPerSample: 8, samplesPerPixel: 3, hasAlpha: false, isPlanar: false, colorSpaceName: .deviceRGB,
            bytesPerRow: 0, bitsPerPixel: 0) else { throw TrialError("Create fixture JPEG") }
        for y in 0..<4 { for x in 0..<4 { bitmap.setColor(NSColor(srgbRed: 0.1, green: 0.2, blue: 0.8, alpha: 1), atX: x, y: y) } }
        guard let jpeg = bitmap.representation(using: .jpeg, properties: [:]) else { throw TrialError("Encode fixture JPEG") }
        _ = try await repository.addPhoto(jpeg: jpeg, to: primary, now: date)
        await repository.close()
    }

    static func ordinary(_ op: Int32, root: URL? = nil, owner: UUID? = nil, event: Data = Data()) async throws -> Int32 {
        let profile = op == 0 ? Data(AndroidUIProfile.measuredMultilineLongNotesV4.rawValue.utf8) : Data()
        let path = root.map { Data($0.path.utf8) } ?? Data()
        let token = owner.map { Data($0.uuidString.utf8) } ?? Data()
        let submit = profile.withUnsafeBytes { p in path.withUnsafeBytes { d in token.withUnsafeBytes { o in event.withUnsafeBytes { e in
            publicAndroidSubmit(1, op, p.bindMemory(to: UInt8.self).baseAddress, p.count,
                d.bindMemory(to: UInt8.self).baseAddress, d.count, o.bindMemory(to: UInt8.self).baseAddress,
                o.count, e.bindMemory(to: UInt8.self).baseAddress, e.count, ordinarySurface)
        }}}}
        try check(submit == 0, "Ordinary command submit failed")
        var result: Int32 = 0
        try await wait("Ordinary reply timed out") { result = publicAndroidPoll(1); return result != 0 }
        return result
    }

    static func event(_ node: String, from presentation: ProjectPresentation) throws -> Data {
        let snapshot = presentation.snapshot
        guard let identity = snapshot.identity(for: node) else { throw TrialError("Missing ordinary action " + node) }
        return try JSONEncoder().encode(UIEventEnvelope(revision: snapshot.document.revision, identity: identity,
                                                        event: .activate, value: .null))
    }

    static func checklist(_ action: Int32, root: URL, material: URL, bundleID: String = bundle) throws {
        let code = root.path.withCString { r in material.path.withCString { m in installation.withCString { i in
            bundleID.withCString { b in checklistSubmit(action, 1, r, m, i, b) }
        }}}
        try check(code == 1, "Checklist command submit failed")
    }

    static func status() -> String {
        var text = [CChar](repeating: 0, count: 256)
        checklistStatus(&text, text.count)
        return String(decoding: text.prefix(while: { $0 != 0 }).map { UInt8(bitPattern: $0) }, as: UTF8.self)
    }

    static func awaitStatus(_ expected: String) async throws {
        var observed = ""
        try await wait("Checklist status timed out") {
            observed = status()
            if observed == "Opening checklist" { return false }
            try check(observed == expected, "Checklist status: \(observed), expected \(expected)")
            return true
        }
    }

    static func frame(_ facade: UInt64) throws -> (UInt64, [String]) {
        var bytes = [UInt8](repeating: 0, count: 8192)
        let count = mxfield_host_packet(facade, mxfield_recorded_probe(facade), &bytes, UInt32(bytes.count))
        let data = Data(bytes.prefix(Int(count)))
        guard count > 0, let object = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let revision = object["revision"] as? UInt64, let root = object["root"] as? [String: Any],
              let children = root["children"] as? [[String: Any]], children.count == 4
        else { throw TrialError("Missing applied guest frame") }
        try check(data.range(of: Data(privateTitle.utf8)) == nil && data.range(of: Data(privateNote.utf8)) == nil,
                  "Guest frame disclosed draft text")
        return (revision, try children.map {
            guard let props = $0["properties"] as? [String: Any],
                  let value = (props["text"] ?? props["label"]) as? String else { throw TrialError("Missing guest label") }
            return value
        })
    }

    static func storageRead(_ presentation: ProjectPresentation, revision: UInt64, flags: UInt8) async throws {
        let lease = try await presentation.attachSignedDraft()
        let response = try await lease.get(get)
        guard response.found, let bytes = Data(base64Encoded: response.valueBase64), bytes.count == 9
        else { throw TrialError("Storage did not return 9-byte revision/flags ABI") }
        let observedRevision = bytes.prefix(8).reduce(UInt64(0)) { ($0 << 8) | UInt64($1) }
        try check(observedRevision == revision && bytes.last == flags, "ABI revision or flags changed")
        print("ABI revision=\(revision) flags=\(flags) length=\(bytes.count)")
        presentation.detachSignedDraft()
    }

    static func replay(_ root: URL, material: URL, rejectedGrant: URL, cold: Bool) async throws {
        if !cold { try await seed(root) }
        try check(mxish_start() == 0, "Host renderer transport setup failed")
        let opened = try await ordinary(0, root: root)
        try check(opened == 1, "Ordinary app open refused")
        guard let app = checklistPresentation(1), let owner = ordinaryOwner.withLock({ $0 })
        else { throw TrialError("Ordinary app owner missing") }
        let before = try await app.repository.readCommittedSnapshot()
        let diskBefore = try committedFile(root)
        var expectedDisk = diskBefore
        guard let photoID = before.drafts.first(where: { $0.id == primary })?.attachmentIDs.first
        else { throw TrialError("Selected draft has no saved photo") }
        let photo = try await app.repository.photoURL(photoID)
        let photoBefore = try fileIdentity(photo)
        let selection = app.entryState?.draft.id
        try check(selection == primary && before.revision == (cold ? 3 : 2), "Expected restored saved draft")
        try await storageRead(app, revision: before.revision, flags: cold ? 15 : 7)

        if !cold {
            let save = try event("entry.saveDraft", from: app)
            let wrong = try await ordinary(1, owner: UUID(), event: save)
            try check(wrong == 2 && committedFile(root) == diskBefore, "Wrong ordinary owner wrote")
            let openedNew = try await ordinary(1, owner: owner, event: event("entry.new", from: app))
            try check(openedNew == 1, "Could not select unsaved draft")
            let stale = try await ordinary(1, owner: owner, event: save)
            try check(stale == 2 && committedFile(root) == diskBefore, "Stale ordinary frame wrote")
            try checklist(1, root: root, material: material)
            try await awaitStatus("Could not open the signed release for this draft")
            try check(committedFile(root) == diskBefore && replay_find_facade() == 0, "Unsaved selection reached mount or wrote")
            let restored = try await ordinary(1, owner: owner, event: event(ProjectDetailControl.draftID(primary), from: app))
            try check(restored == 1 && app.entryState?.draft.id == primary, "Could not return to saved draft")
            try checklist(1, root: root, material: material, bundleID: bundle + ".wrong")
            try await awaitStatus("Could not open the signed release for this draft")
            try check(committedFile(root) == diskBefore && replay_find_facade() == 0, "Wrong identity reached mount or wrote")
            try checklist(1, root: root, material: rejectedGrant)
            try await awaitStatus("Could not open the signed release for this draft")
            try check(committedFile(root) == diskBefore && replay_find_facade() == 0, "Wrong grant reached mount or wrote")
            print("REFUSED unsaved selection, wrong bundle, wrong installed grant, wrong ordinary owner, stale ordinary frame")
        }

        try checklist(1, root: root, material: material)
        try await wait("No signed frame applied") {
            let reply = status()
            try check(reply == "Opening checklist", "Mount stopped before frame: " + reply)
            return replay_find_facade() != 0
        }
        let facade = replay_find_facade()
        let initial = try frame(facade)
        try check(initial.1 == ["Ready to save entry", "JPEG linked", cold ? "Follow-up required" : "Follow-up unset",
                               cold ? "Clear follow-up requirement" : "Mark follow-up required"], "Wrong hydrated frame")
        try check(committedFile(root) == diskBefore, "Mount wrote the workspace")
        try check(mxish_call_entry(facade, 10) == 0, "Current draw witness refused")
        try await awaitStatus(cold ? "Using saved checklist release | Sequence 1" : "Signed checklist | Sequence 1")
        print("MOUNT sequence=1 frame=\(initial.0) cold=\(cold)")

        if !cold {
            staleInput.withLock { $0 = mxish_last_id(facade, 2) }
            let probe = mxfield_recorded_probe(facade)
            try check(mxish_call_entry(facade, 21) != 0, "Wrong attachment accepted")
            try check(committedFile(root) == diskBefore, "Wrong guest attachment wrote")
            try await wait("Current guest tap refused") { mxish_call_entry(facade, 11) == 0 }
            try await wait("No successor guest frame") { mxfield_recorded_probe(facade) > probe }
            let applied = try frame(facade)
            try check(applied.0 > initial.0 && applied.1.contains("Follow-up required"), "Wrong guest readback")
            try check(mxish_call_entry(facade, 10) == 0, "Successor draw refused")
            let after = try await app.repository.readCommittedSnapshot()
            var expected = before
            expected.revision += 1
            expected.drafts[expected.drafts.firstIndex { $0.id == primary }!].followUpRequired = true
            try check(after == expected, "Guest write changed fields outside the selected follow-up")
            let diskAfter = try committedFile(root)
            try check(diskAfter != diskBefore, "Guest write never reached disk")
            expectedDisk = diskAfter
            try check(mxish_call_entry(facade, 20) != 0, "Stale guest input token accepted")
            try check(committedFile(root) == diskAfter, "Stale guest input wrote")
            let selectedOther = try await ordinary(1, owner: owner,
                event: event(ProjectDetailControl.draftID(other), from: app))
            try check(selectedOther == 1 && app.entryState?.draft.id == other, "The editor did not reselect")
            try check(committedFile(root) == diskAfter, "Reselection itself wrote")
            let prior = mxfield_recorded_probe(facade)
            try await wait("Current post-reselection tap was not dispatched") { mxish_call_entry(facade, 11) == 0 }
            try await wait("No denial frame after reselection") { mxfield_recorded_probe(facade) > prior }
            try check(frame(facade).1.contains("Saved draft unavailable"), "Old lease did not refuse storage after reselection")
            try check(committedFile(root) == diskAfter, "Revoked selection wrote")
            print("MUTATION revision=3 onlySelectedFollowUp=true outbox=\(after.outbox.count)")
            print("REFUSED wrong guest attachment, stale guest token, revoked saved selection")
        }

        try checklist(2, root: root, material: material)
        try await awaitStatus("Closed")
        try check(mxish_live_allocations() == 0 && mxish_destructors() == 1, "Signed ownership leaked")
        print("RETIRED signed facade and display allocations")

        let closed = try await ordinary(2)
        try check(closed == 1, "Ordinary owner failed to retire")
        let final = try committedFile(root)
        try check(final == expectedDisk, "Retirement rewrote the workspace")
        try check(fileIdentity(photo) == photoBefore, "Guest or retirement changed the saved JPEG")
        print("CLOSED workspaceSHA256=\(final[0])")
    }

    static func main() async throws {
        let args = CommandLine.arguments
        switch args[1] {
        case "sign":
            try signReleases(fixtures: URL(fileURLWithPath: args[2]), guests: URL(fileURLWithPath: args[3]),
                output: URL(fileURLWithPath: args[4]), archive: args[5], binary: args[6], storageOnly: true,
                sourceCommit: args[7])
        case "online", "cold":
            try await replay(URL(fileURLWithPath: args[2]), material: URL(fileURLWithPath: args[3]),
                             rejectedGrant: URL(fileURLWithPath: args[4]), cold: args[1] == "cold")
        default: throw TrialError("Usage: sign | online | cold")
        }
    }
}
