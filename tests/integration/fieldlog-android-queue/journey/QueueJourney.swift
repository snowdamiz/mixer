import AppKit
import Darwin
import Foundation
import QueueABI
import FieldLogModels
import FieldLogStorage
import MixerAndroid
import MixerUI

private struct Failed: Error, CustomStringConvertible { let description: String }
private func require(_ condition: Bool, _ message: String) throws {
    if !condition { throw Failed(description: message) }
}
private func unwrap<T>(_ value: T?, _ message: String) throws -> T {
    guard let value else { throw Failed(description: message) }
    return value
}

private let profile = AndroidUIProfile.measuredMultilineLongNotesV4

private struct Frame {
    let owner: Data
    let document: UIDocument
    let identities: [UINodeIdentity]

    init(owner: Data, packet: Data) throws {
        self.owner = owner
        let object = try unwrap(JSONSerialization.jsonObject(with: packet) as? [String: Any], "packet object")
        let documentData = try JSONSerialization.data(withJSONObject: unwrap(object["document"], "document"))
        document = try UIDocument.decode(documentData, validator: UIValidator(
            supportedTextFieldAxes: profile.capabilities.textFieldAxes, textValuePolicy: profile.textValuePolicy))
        identities = try JSONDecoder().decode([UINodeIdentity].self, from: JSONSerialization.data(
            withJSONObject: unwrap(object["identities"], "identities")))
    }

    func node(_ id: String) -> UINode? {
        var nodes = [document.root]
        while let node = nodes.popLast() {
            if node.id == id { return node }
            nodes.append(contentsOf: node.children)
        }
        return nil
    }

    func label(_ id: String) -> String? {
        node(id)?.properties["text"]?.string ?? node(id)?.properties["label"]?.string
    }

    func activation(_ id: String) throws -> Data {
        let button = try unwrap(node(id), "projected button missing: \(id)")
        try require(button.kind == .button && button.properties["disabled"]?.bool != true, "button disabled: \(id)")
        try require(button.actions.contains(where: { $0.id == id && $0.event == .activate }), "activation missing: \(id)")
        let identity = try unwrap(identities.first { $0.id == id }, "projected identity missing: \(id)")
        return try JSONEncoder().encode(UIEventEnvelope(
            revision: document.revision, identity: identity, event: .activate, value: .null))
    }
}

@MainActor private enum Capture {
    static var owner: Data?
    static var frame: Frame?
    static var installs = 0
    static var revoked = 0
    static var failure: String?

    static func receive(_ operation: Int32, _ owner: Data, _ packet: Data, _ appearance: Data) -> Int32 {
        do {
            let token = try unwrap(String(data: owner, encoding: .utf8), "owner UTF-8")
            try require(UUID(uuidString: token)?.uuidString == token, "canonical owner UUID")
            switch operation {
            case 0:
                try require(Self.owner == nil, "duplicate owner activation")
                Self.owner = owner
            case 1:
                try require(Self.owner == owner, "packet owner mismatch")
                let expectedAppearance = try UIAppearanceDescriptorCodecV2.canonicalData(
                    UIAppearanceDescriptorCodecV2.mixerDefaultV2())
                try require(appearance == expectedAppearance, "appearance descriptor mismatch")
                let next = try Frame(owner: owner, packet: packet)
                frame = next
                installs += 1
            case 2:
                try require(Self.owner == owner, "revoke owner mismatch")
                Self.owner = nil
                revoked += 1
            default: throw Failed(description: "unexpected surface operation \(operation)")
            }
            return 0
        } catch {
            failure = String(describing: error)
            return 1
        }
    }
}

private let context: Int64 = 3109
private let surface: @convention(c) @Sendable (
    Int64, Int32, UnsafePointer<UInt8>?, Int, UnsafePointer<UInt8>?, Int, UnsafePointer<UInt8>?, Int
) -> Int32 = { id, op, owner, ownerCount, packet, packetCount, appearance, appearanceCount in
    guard id == context, Thread.isMainThread else { return 1 }
    let ownerBytes = owner.map { Data(bytes: $0, count: ownerCount) } ?? Data()
    let packetBytes = packet.map { Data(bytes: $0, count: packetCount) } ?? Data()
    let appearanceBytes = appearance.map { Data(bytes: $0, count: appearanceCount) } ?? Data()
    return MainActor.assumeIsolated { Capture.receive(op, ownerBytes, packetBytes, appearanceBytes) }
}

@MainActor private func request(_ op: Int32, path: String = "", owner: Data = Data(), event: Data = Data()) throws -> Int32 {
    try require(Thread.isMainThread, "ABI poll must run on the real main thread")
    let selected = Data((op == 0 ? profile.rawValue : "").utf8)
    let directory = Data(path.utf8)
    let admitted = selected.withUnsafeBytes { p in
        directory.withUnsafeBytes { d in
            owner.withUnsafeBytes { o in
                event.withUnsafeBytes { e in
                    mixer_public_android_submit(context, op, p.bindMemory(to: UInt8.self).baseAddress, p.count,
                        d.bindMemory(to: UInt8.self).baseAddress, d.count,
                        o.bindMemory(to: UInt8.self).baseAddress, o.count,
                        e.bindMemory(to: UInt8.self).baseAddress, e.count, surface)
                }
            }
        }
    }
    try require(admitted == 0, "op \(op): submit rejected \(admitted)")
    let deadline = ProcessInfo.processInfo.systemUptime + 8
    while ProcessInfo.processInfo.systemUptime < deadline {
        let result = mixer_public_android_poll(context)
        if let failure = Capture.failure { throw Failed(description: failure) }
        if result != 0 { return result }
    }
    throw Failed(description: "op \(op): poll timed out")
}

@MainActor private func activate(_ id: String) throws {
    let frame = try unwrap(Capture.frame, "no activation frame")
    let event = Data([0x5b]) + (try frame.activation(id)) + Data([0x5d])
    let status = try request(1, owner: frame.owner, event: event)
    try require(status == 1, "activation \(id) returned \(status), expected 1")
}

@MainActor private func waitFor<T>(_ message: String, seconds: Double = 8, _ inspect: () throws -> T?) throws -> T {
    let deadline = ProcessInfo.processInfo.systemUptime + seconds
    while ProcessInfo.processInfo.systemUptime < deadline {
        if let value = try inspect() { return value }
        _ = RunLoop.main.run(mode: .default, before: Date(timeIntervalSinceNow: 0.01))
    }
    throw Failed(description: "timeout: \(message)")
}

@MainActor private func awaitResult<T>(_ body: @escaping @MainActor () async throws -> T) throws -> T {
    var result: Result<T, any Error>?
    let task = Task { @MainActor in
        do { result = .success(try await body()) }
        catch { result = .failure(error) }
    }
    defer { task.cancel() }
    return try waitFor("repository operation") { result }.get()
}

private struct Fixture: Codable {
    let workspace: UUID
    let project: UUID
    let entry: UUID
    let photo: UUID
    let event: UUID
    let unrelated: UUID
    let bytes: Int
}

private func writeJSON<T: Encodable>(_ value: T, to url: URL) throws {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.sortedKeys, .prettyPrinted]
    try encoder.encode(value).write(to: url, options: .atomic)
}

private func jpegFixture() throws -> Data {
    let width = 640, height = 480
    let bitmap = try unwrap(NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height,
        bitsPerSample: 8, samplesPerPixel: 3, hasAlpha: false, isPlanar: false, colorSpaceName: .deviceRGB,
        bytesPerRow: width * 3, bitsPerPixel: 24), "AppKit bitmap")
    let pixels = try unwrap(bitmap.bitmapData, "bitmap bytes")
    var noise: UInt32 = 0x8a328fe1
    for index in 0..<(width * height * 3) {
        noise ^= noise << 13
        noise ^= noise >> 17
        noise ^= noise << 5
        pixels[index] = UInt8(truncatingIfNeeded: noise)
    }
    let data = try unwrap(bitmap.representation(using: .jpeg, properties: [.compressionFactor: 0.82]), "JPEG encoding")
    let decoded = try unwrap(NSBitmapImageRep(data: data), "JPEG decoding")
    try require(decoded.pixelsWide == width && decoded.pixelsHigh == height && data.count > 3 * 32768
        && data.count <= 6 * 1024 * 1024, "JPEG dimensions or length")
    return data
}

@MainActor private func seed(_ root: URL, _ storage: URL) throws {
    let jpeg = try jpegFixture()
    try jpeg.write(to: root.appendingPathComponent("fixture.jpg"))
    let final = try awaitResult {
        let repository = try WorkspaceRepository(directory: storage)
        let initial = try await repository.transact { workspace in
            try workspace.createProject(title: "Synthetic FieldLog project", site: "Loopback fixture")
        }
        let project = try unwrap(initial.projects.first, "fixture project").id
        let draft = EntryDraft(projectID: project, title: "Synthetic entry", note: "JPEG replay · 雨")
        _ = try await repository.transact { workspace in
            try workspace.saveDraft(draft)
            try workspace.saveTask(projectID: project, title: "Unrelated queued task", responsible: "Test")
        }
        _ = try await repository.addPhoto(jpeg: jpeg, to: draft.id)
        let ready = try await repository.transact { workspace in try workspace.commitDraft(draft.id) }
        await repository.close()
        return ready
    }
    let entry = try unwrap(final.entries.first, "fixture entry")
    let event = try unwrap(final.outbox.first { $0.kind == .entrySaved }, "fixture outbox")
    let unrelated = try unwrap(final.outbox.first { $0.kind == .taskSaved }, "fixture unrelated outbox")
    let photo = try unwrap(entry.attachmentIDs.first, "fixture photo")
    try writeJSON(final, to: root.appendingPathComponent("baseline.json"))
    try writeJSON(Fixture(workspace: final.id, project: entry.projectID, entry: entry.id, photo: photo,
                          event: event.id, unrelated: unrelated.id, bytes: jpeg.count),
                  to: root.appendingPathComponent("fixture.json"))
}

@MainActor private func verifyRepository(_ storage: URL, _ baseline: Workspace, _ fixture: Fixture,
                                        _ jpeg: Data, acknowledged: Bool) throws -> UInt64 {
    try awaitResult {
        let repository = try WorkspaceRepository(directory: storage)
        let current = await repository.snapshot()
        let file = try await repository.photoURL(fixture.photo)
        let actual = try Data(contentsOf: file)
        await repository.close()
        var expected = baseline
        if acknowledged {
            expected.outbox.removeAll { $0.id == fixture.event }
            expected.revision += 1
        }
        try require(current == expected, "cold repository did not match baseline with expected acknowledgment=\(acknowledged)")
        try require(actual == jpeg, "cold repository JPEG differs byte-for-byte")
        return current.revision
    }
}

@MainActor private func exercise(_ phase: String, _ root: URL, _ app: URL, _ storage: URL) throws {
    let fixture = try JSONDecoder().decode(Fixture.self, from: Data(contentsOf: root.appendingPathComponent("fixture.json")))
    let baseline = try JSONDecoder().decode(Workspace.self, from: Data(contentsOf: root.appendingPathComponent("baseline.json")))
    let jpeg = try Data(contentsOf: root.appendingPathComponent("fixture.jpg"))
    let before = try verifyRepository(storage, baseline, fixture, jpeg, acknowledged: false)
    let startup = try request(0, path: app.path)
    try require(startup == 1, "startup reply \(startup)")
    let initialRefresh = try request(3)
    try require(initialRefresh == 1, "startup refresh reply \(initialRefresh)")
    try activate("workspace.queue")
    let event = fixture.event.uuidString.lowercased()
    let pending = "pending." + event
    let unrelated = "pending." + fixture.unrelated.uuidString.lowercased()
    let send = "queue.send." + event
    let cancel = "queue.cancel." + event
    try require(Capture.frame?.node(unrelated) != nil, "unrelated event not projected")
    try require(Capture.frame?.node("queue.send." + fixture.unrelated.uuidString.lowercased()) == nil,
                "unrelated queued task rendered a send action")
    if phase == "offline" {
        try require(Capture.frame?.node(pending) != nil && Capture.frame?.node(send) == nil,
                    "unconfigured queue did not stay offline")
        let pendingLabel = try unwrap(Capture.frame?.label(pending), "pending row missing")
        let explanation = try unwrap(Capture.frame?.label("queue.explanation"), "queue explanation missing")
        try require(pendingLabel.contains("Saved on device") && explanation.contains("Sending is unavailable") &&
                    !pendingLabel.contains("Not sent") && !explanation.contains("has been sent"),
                    "unconfigured queue misstates remote delivery")
        let closed = try request(2)
        try require(closed == 1 && Capture.revoked == 1, "offline context did not close")
        _ = try verifyRepository(storage, baseline, fixture, jpeg, acknowledged: false)
        return
    }
    try activate(send)

    func hold(_ name: String, bytes: Int) throws -> String {
        let marker = root.appendingPathComponent(name + ".held").path
        return try waitFor("held \(name), \(bytes) confirmed; last: \(Capture.frame?.label(pending) ?? "-")") {
            let status = try request(3)
            try require(status == 3, "expected active refresh while waiting for \(name), got \(status)")
            guard FileManager.default.fileExists(atPath: marker),
                  let label = Capture.frame?.label(pending),
                  label.hasSuffix("— \(bytes) of \(fixture.bytes) bytes confirmed") else { return nil }
            return label
        }
    }

    func release(_ name: String) throws {
        try Data().write(to: root.appendingPathComponent(name + ".release"), options: .atomic)
    }

    var progress: [String] = []
    if phase == "close" {
        progress.append(try hold("second-chunk", bytes: 32768))
        let closed = try request(2)
        try require(closed == 1 && Capture.revoked == 1 && Capture.owner == nil,
                    "close during active HTTP request did not revoke the owner")
        let rejected = try request(3)
        try require(rejected == 2, "closed context still accepted refresh")
        let after = try verifyRepository(storage, baseline, fixture, jpeg, acknowledged: false)
        try writeJSON(["confirmedProgress": progress[0], "closedRefresh": String(rejected),
                       "coldReopenRevision": String(after)], to: root.appendingPathComponent("close.json"))
        try release("second-chunk")
        return
    }
    if phase == "cancel" {
        progress.append(try hold("second-chunk", bytes: 32768))
        try activate(cancel)
        // The server cannot finish the original request until this release, so an
        // idle response here is evidence of cancellation rather than an HTTP error.
        let result = try waitFor("cancel before releasing held HTTP reply") { () -> Int32? in
            let status = try request(3)
            return status == 3 ? nil : status
        }
        try require(result == 1, "cancel idle reply \(result)")
        try release("second-chunk")
    } else if phase == "lost" {
        progress.append(try hold("resume-chunk", bytes: 65536))
        try release("resume-chunk")
        progress.append(try hold("final-receipt", bytes: fixture.bytes))
        try release("final-receipt")
    }

    let idle = try waitFor("idle \(phase)") { () -> Int32? in
        let status = try request(3)
        return status == 3 ? nil : status
    }
    try require(idle == 1, "final refresh reply \(idle)")
    let status = try unwrap(Capture.frame?.label("queue.sync.status"), "queue status projection missing")
    let acknowledged = phase == "reconcile"
    let lower = status.lowercased()
    if phase == "cancel" {
        try require(lower.contains("cancel"), "cancel status: \(status)")
    } else if phase == "lost" {
        try require(lower.contains("not confirmed") && lower.contains("resume"), "lost-ack status: \(status)")
    } else {
        try require(lower.contains("sent") || lower.contains("reconcil") || lower.contains("confirm"), "retry status: \(status)")
    }
    try require((Capture.frame?.node(pending) == nil) == acknowledged, "unexpected target pending projection")
    try require(Capture.frame?.node(unrelated) != nil, "unrelated event missing after \(phase)")
    if phase == "lost" {
        try activate("workspace.back")
        let label = try unwrap(Capture.frame?.label("workspace.queue"), "Tasks queue navigation missing")
        try require(label.contains("pending changes") && !label.contains("Not sent"),
                    "Tasks queue navigation misstates remote delivery")
    }
    let close = try request(2)
    try require(close == 1 && Capture.revoked == 1 && Capture.owner == nil, "owner revoke/close failed")
    let rejected = try request(3)
    try require(rejected == 2, "closed-context refresh replied \(rejected)")
    let after = try verifyRepository(storage, baseline, fixture, jpeg, acknowledged: acknowledged)
    struct Result: Codable {
        let activeProgress: [String]
        let status: String
        let beforeRevision: UInt64
        let coldReopenRevision: UInt64
        let installs: Int
        let idle: Int32
        let closedRefresh: Int32
    }
    try writeJSON(Result(activeProgress: progress, status: status, beforeRevision: before,
                         coldReopenRevision: after, installs: Capture.installs,
                         idle: idle, closedRefresh: rejected),
                  to: root.appendingPathComponent(phase + ".json"))
}

@main private enum QueueJourney {
    @MainActor static func main() {
        do {
            let phase = CommandLine.arguments[1]
            let root = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
            let app = root.appendingPathComponent("app-storage", isDirectory: true)
            let storage = app.appendingPathComponent("FieldLog", isDirectory: true)
            if phase == "seed" { try seed(root, storage) }
            else { try exercise(phase, root, app, storage) }
        } catch {
            FileHandle.standardError.write(Data("FAIL \(CommandLine.arguments[1]): \(error)\n".utf8))
            exit(1)
        }
    }
}
