import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilities
import MixerVM

private let fixtureTitle = "فحص المضخة 07"
private let getPayload = #"{"key":"selected-task","namespace":"fieldlog-task-v1"}"#

private struct Failure: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

private func expect(_ condition: Bool, _ step: String) throws {
    guard condition else { throw Failure(step) }
}

private struct Node: Codable, Equatable {
    struct Action: Codable, Equatable {
        let id: String
        let event: String
    }
    let id: String
    let kind: String
    let properties: [String: String]
    var actions: [Action] = []
    var children: [Node] = []
}

private struct Frame: Codable, Equatable {
    let schemaVersion: Int
    let revision: Int
    let root: Node
}

private struct Session {
    private var report = MixerVmReport()
    private var handle: UInt64 = 0
    private var offset: UInt32 = 0

    init(_ wasm: [UInt8]) throws {
        var limits = MixerVmLimits(struct_size: UInt32(MemoryLayout<MixerVmLimits>.size),
            abi_version: 1, fuel: 1_000_000, memory_pages: 1, operand_stack: 4096, call_depth: 64, host_calls: 1024)
        var caps = MixerVmCapabilityLimitsV1(struct_size: UInt32(MemoryLayout<MixerVmCapabilityLimitsV1>.size),
            abi_version: 1, maximum_requests: 8, timeout_milliseconds: 30_000, turn_milliseconds: 50,
            reserved: 0, reservation_bytes: 8_388_608)
        let startup = Array("mixer_guest_ui_start_v1".utf8)
        try check(mixer_vm_capability_guest_ui_validate_deferred_v1(wasm, wasm.count, &limits, &caps, &report),
                  "deferred validation")
        try check(mixer_vm_capability_session_create_v1(wasm, wasm.count, startup, startup.count,
                                                       &limits, &caps, &handle, &report), "create")
        do {
            try check(mixer_vm_capability_session_startup_v1(handle, &report), "startup")
            try expect(report.value_type == 1 && report.value > 0 && report.host_calls_used == 0, "deferred startup")
            offset = UInt32(report.value)
            let words = try header()
            try expect(words[2] == 0 && words[3] == 0, "published before hydration")
            try noRequest()
            try check(mixer_vm_capability_session_enable_v1(handle, &report), "enable")
        } catch {
            try close()
            throw error
        }
    }

    mutating func close() throws {
        guard handle != 0 else { return }
        try check(mixer_vm_capability_session_close_v1(handle, &report), "close")
        handle = 0
    }

    private func check(_ status: UInt32, _ step: String) throws {
        guard status != 0 else { return }
        let bytes = withUnsafeBytes(of: report.message) { Array($0.prefix { $0 != 0 }) }
        throw Failure("\(step): VM status \(status), \(String(decoding: bytes, as: UTF8.self))")
    }

    private mutating func header() throws -> [UInt32] {
        var words = [UInt32](repeating: 0, count: 8)
        let status = words.withUnsafeMutableBytes {
            mixer_vm_capability_session_read_v1(handle, offset, $0.baseAddress!.assumingMemoryBound(to: UInt8.self),
                                                $0.count, &report)
        }
        try check(status, "read header")
        try expect(words[0] == 0x3155494d && words[1] == 32 && words[5] == 4096, "control header")
        return words
    }

    mutating func frame(_ revision: Int, _ text: String, _ label: String) throws -> Frame {
        let words = try header()
        try expect((1...2048).contains(words[3]), "bounded document")
        var bytes = [UInt8](repeating: 0, count: Int(words[3]))
        try check(mixer_vm_capability_session_read_v1(handle, words[2], &bytes, bytes.count, &report), "read document")
        let frame = try JSONDecoder().decode(Frame.self, from: Data(bytes))
        let children = [
            Node(id: "task", kind: "text", properties: ["text": fixtureTitle]),
            Node(id: "status", kind: "text", properties: ["text": text]),
            Node(id: "toggle", kind: "button", properties: ["label": label],
                 actions: [.init(id: "task.toggle", event: "activate")]),
        ]
        let expected = Frame(schemaVersion: 1, revision: revision,
            root: Node(id: "fieldlog-task", kind: "vStack", properties: [:], children: children))
        try expect(frame == expected, "unexpected Android renderer document at revision \(revision): \(frame)")
        return frame
    }

    mutating func invoke(_ name: String, _ args: [MixerVmValue] = [], returns value: Int64 = 0) throws {
        let exported = Array(name.utf8)
        try check(mixer_vm_capability_session_invoke_v1(handle, exported, exported.count, args, args.count, &report), name)
        try expect(report.value_type == 1 && report.value == value, "\(name) expected i32 \(value), got \(report.value)")
    }

    mutating func event(_ revision: Int, _ sequence: Int, action: String = "task.toggle",
                        returns value: Int64 = 0) throws {
        let words = try header()
        let bytes = Array(#"{"actionID":"\#(action)","event":"activate","nodeID":"toggle","revision":\#(revision),"schemaVersion":1,"sequence":\#(sequence),"value":null}"#.utf8)
        try check(mixer_vm_capability_session_write_v1(handle, words[4], bytes, bytes.count, &report), "write event")
        try invoke("mixer_guest_ui_event_v1", [.init(value_type: 1, reserved: 0, value: Int64(bytes.count))], returns: value)
    }

    mutating func noRequest() throws {
        var message = MixerVmCapabilityMessageV1()
        var bytes = [UInt8](repeating: 0, count: 192)
        try check(mixer_vm_capability_take_v1(handle, &message, &bytes, bytes.count, &report), "empty mailbox")
        try expect(message.kind == 0, "unexpected capability request")
    }

    private mutating func take(_ operation: UInt32, _ arguments: String) throws -> UInt64 {
        var message = MixerVmCapabilityMessageV1()
        var bytes = [UInt8](repeating: 0, count: 192)
        try check(mixer_vm_capability_take_v1(handle, &message, &bytes, bytes.count, &report), "take capability")
        try expect(message.kind == 1 && message.operation == operation &&
                   bytes.prefix(Int(message.payload_length)).elementsEqual(arguments.utf8),
                   "unexpected capability request for operation \(operation)")
        return message.token
    }

    private mutating func answer(_ token: UInt64, _ operation: UInt32, _ verb: String,
                                 _ value: [String: Any]) throws {
        let reply = try JSONSerialization.data(withJSONObject: [
            "abi": 1, "capability": CapabilitySchemas.storageID, "operation": verb,
            "outcome": ["kind": "success", "value": value], "schemaHash": CapabilitySchemas.storageSHA256,
        ], options: [.sortedKeys, .withoutEscapingSlashes])
        var result = MixerVmCapabilityResultV1()
        try check(mixer_vm_capability_post_v1(handle, token, operation, Array(reply), reply.count, &result, &report), "post")
        try expect(result.kind == 0, "completion not accepted")
        try check(mixer_vm_capability_ack_exit_v1(handle, token, operation, &result, &report), "acknowledge exit")
        try expect(result.kind == 0, "exit not acknowledged")
        var woke: UInt32 = 0
        try check(mixer_vm_capability_session_wake_v1(handle, &woke, &report), "wake")
        try expect(woke == 1, "guest did not consume completion")
    }

    mutating func read(_ storage: FieldLogTaskStorage) async throws {
        let token = try take(2, getPayload)
        let response = try await storage.get(.init(namespace: FieldLogTaskStorage.namespace, key: "selected-task"))
        try expect(response.found, "selected fixture missing from repository")
        try answer(token, 2, "get", ["found": response.found, "valueBase64": response.valueBase64])
        try noRequest()
    }

    mutating func write(_ storage: FieldLogTaskStorage, revision: UInt64, completed: Bool) async throws {
        var value = withUnsafeBytes(of: revision.bigEndian) { Data($0) }
        value.append(completed ? 1 : 0)
        let base64 = value.base64EncodedString()
        let token = try take(3, #"{"key":"selected-task","namespace":"fieldlog-task-v1","valueBase64":"\#(base64)"}"#)
        let response = try await storage.put(.init(namespace: FieldLogTaskStorage.namespace, key: "selected-task",
                                                   valueBase64: base64), maximumTotalBytes: 4_194_304, maximumEntries: 1024)
        try expect(response.committed, "fixture write declined")
        try answer(token, 3, "put", ["committed": response.committed])
        // The next capability must be a freshly queued read of committed state.
        try await read(storage)
    }
}

private func verifyChange(_ before: Workspace, _ after: Workspace, task: WorkTask, completed: Bool) throws {
    try expect(after.revision == before.revision + 1, "workspace must advance exactly one revision")
    try expect(after.outbox.count == before.outbox.count + 1 && Array(after.outbox.dropLast()) == before.outbox,
               "workspace must append exactly one outbox record")
    let change = after.outbox.last
    try expect(change?.kind == .taskSaved && change?.recordID == task.id && change?.revision == after.revision,
               "outbox targets the selected task and its committed revision")
    var expected = before
    var updated = task
    updated.completed = completed
    updated.updatedAt = after.tasks[0].updatedAt
    expected.tasks = [updated]
    expected.outbox = after.outbox
    expected.revision = after.revision
    try expect(after == expected, "unrelated saved data changed")
}

@main
struct ChecklistProbe {
    static func main() async throws {
        let args = CommandLine.arguments
        try expect(args.count == 4 && ["baseline", "reviewed"].contains(args[1]), "expected variant, Wasm, fresh workspace")
        let reviewed = args[1] == "reviewed"
        let wasm = try Array(Data(contentsOf: URL(fileURLWithPath: args[2])))
        try expect((1...8192).contains(wasm.count), "Wasm fixture exceeded its size bound")
        let directory = URL(fileURLWithPath: args[3], isDirectory: true)
        try expect(!FileManager.default.fileExists(atPath: directory.path), "workspace must be fresh")

        let projectID = UUID()
        let repository = try WorkspaceRepository(directory: directory)
        _ = try await repository.transact { _ = try $0.createProject(id: projectID, title: "Pump inspection", site: "") }
        _ = try await repository.transact { try $0.saveTask(projectID: projectID, title: fixtureTitle, responsible: "") }
        let seed = try await repository.readCommittedSnapshot()
        try expect(seed.revision == 2 && seed.outbox.count == 2 && seed.tasks.count == 1, "expected ordinary saved fixture")
        let task = seed.tasks[0]
        let storage = FieldLogTaskStorage(repository: repository, projectID: projectID, taskID: task.id)
        let openText = reviewed ? "الفحص قيد التنفيذ" : "مفتوحة"
        let openLabel = reviewed ? "وضع علامة مكتملة" : "إكمال المهمة"
        let completedText = reviewed ? "اكتمل الفحص" : "مكتملة"
        let reopenLabel = reviewed ? "إعادة فتح الفحص" : "إعادة فتح المهمة"

        var guest = try Session(wasm)
        defer { try? guest.close() }
        try guest.invoke("mixer_guest_ui_hydrate_v1")
        try await guest.read(storage)
        var frames = [try guest.frame(1, openText, openLabel)]
        try guest.event(1, 1, action: "task.action", returns: 1)
        try guest.noRequest()
        try guest.event(1, 1)
        if reviewed {
            try guest.noRequest()
            try expect(try await repository.readCommittedSnapshot() == seed, "review wrote before confirmation")
            frames.append(try guest.frame(2, "الفحص بانتظار التأكيد", "تأكيد إكمال الفحص"))
            try guest.event(1, 1, returns: 1)
            try guest.noRequest()
            try guest.event(2, 2)
        }
        try guest.event(reviewed ? 2 : 1, reviewed ? 2 : 1, returns: 1)
        try await guest.write(storage, revision: seed.revision, completed: true)
        frames.append(try guest.frame(reviewed ? 3 : 2, completedText, reopenLabel))
        let completed = try await repository.readCommittedSnapshot()
        try verifyChange(seed, completed, task: task, completed: true)
        try guest.close()
        await repository.close()

        let reopenedRepository = try WorkspaceRepository(directory: directory)
        try expect(try await reopenedRepository.readCommittedSnapshot() == completed, "completion did not survive reopen")
        let reopenedStorage = FieldLogTaskStorage(repository: reopenedRepository, projectID: projectID, taskID: task.id)
        var reopened = try Session(wasm)
        defer { try? reopened.close() }
        try reopened.invoke("mixer_guest_ui_hydrate_v1")
        try await reopened.read(reopenedStorage)
        frames.append(try reopened.frame(1, completedText, reopenLabel))
        try reopened.event(1, 1)
        try await reopened.write(reopenedStorage, revision: completed.revision, completed: false)
        frames.append(try reopened.frame(2, openText, openLabel))
        let restored = try await reopenedRepository.readCommittedSnapshot()
        try verifyChange(completed, restored, task: completed.tasks[0], completed: false)
        try reopened.close()
        await reopenedRepository.close()

        let finalRepository = try WorkspaceRepository(directory: directory)
        try expect(try await finalRepository.readCommittedSnapshot() == restored, "reopen action did not survive repository restart")
        await finalRepository.close()

        let evidence: [String: Any] = [
            "frames": try JSONSerialization.jsonObject(with: JSONEncoder().encode(frames)),
            "workspaceID": seed.id.uuidString, "projectID": projectID.uuidString, "taskID": task.id.uuidString,
            "workspaceRevisions": [seed.revision, completed.revision, restored.revision],
            "outboxCounts": [seed.outbox.count, completed.outbox.count, restored.outbox.count],
            "completed": [false, true, false], "reviewWithoutWrite": reviewed, "durableAfterReopen": true,
        ]
        let json = try JSONSerialization.data(withJSONObject: evidence, options: [.sortedKeys, .withoutEscapingSlashes])
        print(String(decoding: json, as: UTF8.self))
    }
}
