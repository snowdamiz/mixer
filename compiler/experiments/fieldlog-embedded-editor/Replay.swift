import Foundation
import MixerCore
import MixerUI
import OwnedVM

struct Turn {
    var name: String
    var revision: UInt64
    var node: EditorNode
    var generation: UInt64
    var event: EditorEvent
    var value: UIValue
    var expected: EditorReply

    var input: [UInt8] { Array((value.string ?? "").utf8) }
    var kind: EditorValue {
        switch value {
        case .string: .text
        case .bool: .boolean
        case .null: .null
        default: preconditionFailure("unsupported replay value")
        }
    }
}

struct ReplayFailure: Error, CustomStringConvertible {
    var description: String
}

struct VMFailure: Error, CustomStringConvertible {
    var operation: String
    var status: UInt32
    var code: String
    var message: String
    var offset: UInt32
    var fuel: UInt64

    var description: String { "\(operation): status=\(status) \(code) \(message) offset=\(offset) fuel=\(fuel)" }
}

func require(_ condition: Bool, _ message: String) throws {
    guard condition else { throw ReplayFailure(description: message) }
}

func vmCode(_ report: MixerVmReport) -> String {
    withUnsafeBytes(of: report.code) { String(decoding: $0.prefix { $0 != 0 }, as: UTF8.self) }
}

func vmCheck(_ status: UInt32, _ report: MixerVmReport, _ operation: String) throws {
    guard status != 0 else { return }
    let message = withUnsafeBytes(of: report.message) { String(decoding: $0.prefix { $0 != 0 }, as: UTF8.self) }
    throw VMFailure(operation: operation, status: status, code: vmCode(report),
                    message: message, offset: report.offset, fuel: report.fuel_used)
}

final class Session {
    private var handle: UInt64 = 0
    private(set) var peakFuel: UInt64 = 0
    private(set) var fuel: UInt64 = 0

    init(_ guest: Data) throws {
        var report = MixerVmReport()
        let status = guest.withUnsafeBytes {
            mixer_vm_session_create_v1(3, $0.bindMemory(to: UInt8.self).baseAddress,
                                       guest.count, nil, &handle, &report)
        }
        try vmCheck(status, report, "create")
    }

    deinit {
        if handle != 0 {
            var report = MixerVmReport()
            _ = mixer_vm_session_close_v1(handle, &report)
        }
    }

    func close() throws {
        var report = MixerVmReport()
        try vmCheck(mixer_vm_session_close_v1(handle, &report), report, "close")
        let retired = handle
        handle = 0
        var byte: UInt8 = 0
        let status = mixer_vm_session_read_v1(retired, 0, &byte, 1, &report)
        try require(status == 3 && vmCode(report) == "invalid_session", "retired session was not refused")
    }

    func invoke(_ name: String, _ args: [MixerVmValue] = []) throws -> UInt32 {
        let export = Array(name.utf8)
        var report = MixerVmReport()
        let status = export.withUnsafeBufferPointer { name in
            args.withUnsafeBufferPointer {
                mixer_vm_session_invoke_v1(handle, name.baseAddress, name.count,
                                           $0.baseAddress, $0.count, &report)
            }
        }
        try vmCheck(status, report, name)
        try require(report.value_type == 1, "\(name): expected i32")
        try require(report.host_calls_used == 0, "\(name): host import called")
        fuel = report.fuel_used
        peakFuel = max(peakFuel, fuel)
        return UInt32(bitPattern: Int32(report.value))
    }

    func write(_ bytes: [UInt8], at offset: UInt32) throws {
        var report = MixerVmReport()
        let status = bytes.withUnsafeBufferPointer {
            mixer_vm_session_write_v1(handle, offset, $0.baseAddress, $0.count, &report)
        }
        try vmCheck(status, report, "write")
    }

    func snapshot(at address: UInt32) throws -> [UInt8] {
        let count = Int(try invoke("fieldlog_editor_snapshot"))
        try require((EditorBoundary.headerBytes...EditorBoundary.bufferBytes).contains(count), "snapshot bounds")
        return try read(at: address, count: count)
    }

    func read(at address: UInt32, count: Int) throws -> [UInt8] {
        var bytes = [UInt8](repeating: 0, count: count)
        var report = MixerVmReport()
        let status = bytes.withUnsafeMutableBufferPointer {
            mixer_vm_session_read_v1(handle, address, $0.baseAddress, $0.count, &report)
        }
        try vmCheck(status, report, "read")
        return bytes
    }
}

func i32(_ value: Int32) -> MixerVmValue {
    MixerVmValue(value_type: 1, reserved: 0, value: Int64(value))
}

func i64(_ value: UInt64) -> MixerVmValue {
    MixerVmValue(value_type: 2, reserved: 0, value: Int64(bitPattern: value))
}

func originalBytes(_ snapshot: TaskEditorPresentationSnapshot, includeSave: Bool = false) throws -> [UInt8] {
    try require(snapshot.renderingFailure == nil, "original document invalid")
    try require(snapshot.state.responsible.isEmpty && snapshot.state.failure == nil, "unexpected reducer fields")
    let phase: UInt8
    switch (snapshot.outcome, snapshot.state.saving, snapshot.state.saved) {
    case (.editing, false, false): phase = 0
    case (.cancelled, false, false): phase = 1
    case (.editing, true, false) where includeSave: phase = 2
    case (.saved, false, true) where includeSave: phase = 3
    default: throw ReplayFailure(description: "unexpected original outcome")
    }
    let routes = snapshot.navigation.routes
    try require(phase == 1 || phase == 3 ? routes.isEmpty :
                routes.count == 1 && routes[0].id == "task.editor" && routes[0].name == "newTask",
                "unexpected original route")
    let fields = snapshot.render.document.root.children[0].children[0].children
    try require(fields[0].id == "task.title", "unexpected original field")
    try require(fields[0].properties["value"]?.string?.utf8.elementsEqual(snapshot.state.title.utf8) == true,
                "original document and reducer title diverged")
    var revision = snapshot.render.document.revision.littleEndian
    return withUnsafeBytes(of: &revision) { Array($0) }
        + [phase, UInt8(routes.count)] + Array(snapshot.state.title.utf8)
}

@MainActor func deliver(_ turn: Turn, to original: TaskEditorPresentation) throws -> EditorReply {
    let nodeID: String
    switch turn.node {
    case .title: nodeID = "task.title"
    case .cancel: nodeID = "task.cancel"
    case .save: nodeID = "task.save"
    }
    let envelope = UIEventEnvelope(revision: turn.revision,
        identity: UINodeIdentity(id: nodeID, generation: turn.generation),
        event: turn.event == .textChange ? .textChange : .activate, value: turn.value)
    do { try original.send(envelope) }
    catch TaskEditorPresentationError.closed { return .closed }
    catch UIRoutingError.staleRevision { return .staleRevision }
    catch UIRoutingError.staleIdentity { return .staleIdentity }
    catch UIRoutingError.disabledNode { return .disabled }
    catch UIRoutingError.unboundEvent { return .unboundEvent }
    catch UIRoutingError.invalidValue { return .invalidValue }
    return .accepted
}

func guestSend(_ turn: Turn, _ session: Session, at address: UInt32, input: [UInt8]) throws -> UInt32 {
    try session.write(input, at: address)
    return try session.invoke("fieldlog_editor_send", [
        i64(turn.revision), i32(turn.node.rawValue), i64(turn.generation),
        i32(turn.event.rawValue), i32(turn.kind.rawValue), i32(Int32(input.count)),
    ])
}

@main struct Replay {
    @MainActor static func main() async throws {
        do {
            try await run()
        } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            Foundation.exit(1)
        }
    }

    @MainActor static func run() async throws {
        let args = CommandLine.arguments
        let guest = try Data(contentsOf: URL(fileURLWithPath: args[1]))
        let original = try TaskEditorPresentation { _, _ in
            fatalError("the edit and cancel replay invoked persistence")
        }
        let initial = original.snapshot.render
        guard let title = initial.identity(for: "task.title"), let cancel = initial.identity(for: "task.cancel") else {
            throw ReplayFailure(description: "original controls absent")
        }
        let field = initial.document.root.children[0].children[0].children[0]
        let axis = field.properties["axis"]?.string ?? "horizontal"
        try require(axis == args[2], "historical title axis mismatch")
        var projected = EditorBoundary(titleGeneration: title.generation, cancelGeneration: cancel.generation)
        var buffer = [UInt8](repeating: 0, count: EditorBoundary.bufferBytes)
        let session = try Session(guest)
        let address = try session.invoke("fieldlog_editor_open", [i64(title.generation), i64(cancel.generation), i64(0)])
        try require(address > 0, "null guest buffer")
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let originalInitial = try originalBytes(original.snapshot)
        try require(try session.snapshot(at: address) == originalInitial, "initial state differs")
        let accent = "Line one\ne\u{301} 🧑🏽‍🔧"
        let composed = "Line one\n\u{e9} 🧑🏽‍🔧"
        let turns: [Turn] = [
            Turn(name: "actual-title-edit", revision: 1, node: .title, generation: title.generation,
                 event: .textChange, value: .string("Inspect pump P-17"), expected: .accepted),
            Turn(name: "stale-title-edit", revision: 1, node: .title, generation: title.generation,
                 event: .textChange, value: .string("discard stale text"), expected: .staleRevision),
            Turn(name: "foreign-generation", revision: 2, node: .title, generation: cancel.generation,
                 event: .textChange, value: .string("discard foreign text"), expected: .staleIdentity),
            Turn(name: "wrong-title-event", revision: 2, node: .title, generation: title.generation,
                 event: .activate, value: .null, expected: .unboundEvent),
            Turn(name: "wrong-title-value", revision: 2, node: .title, generation: title.generation,
                 event: .textChange, value: .bool(true), expected: .invalidValue),
            Turn(name: "unicode-newline-title", revision: 2, node: .title, generation: title.generation,
                 event: .textChange, value: .string(accent), expected: .accepted),
            Turn(name: "canonically-equivalent-title", revision: 3, node: .title, generation: title.generation,
                 event: .textChange, value: .string(composed), expected: .accepted),
            Turn(name: "oversize-title", revision: 3, node: .title, generation: title.generation,
                 event: .textChange, value: .string(String(repeating: "a", count: 16_385)), expected: .invalidValue),
            Turn(name: "wrong-cancel-value", revision: 3, node: .cancel, generation: cancel.generation,
                 event: .activate, value: .bool(true), expected: .invalidValue),
            Turn(name: "stale-cancel", revision: 2, node: .cancel, generation: cancel.generation,
                 event: .activate, value: .null, expected: .staleRevision),
            Turn(name: "cancel", revision: 3, node: .cancel, generation: cancel.generation,
                 event: .activate, value: .null, expected: .accepted),
            Turn(name: "edit-after-cancel", revision: 4, node: .title, generation: title.generation,
                 event: .textChange, value: .string("discard closed text"), expected: .closed),
        ]
        var trace = Data()
        for (index, turn) in turns.enumerated() {
            let before = try encoder.encode(original.snapshot.render.document)
            let beforeSnapshot = try originalBytes(original.snapshot)
            let reply = try deliver(turn, to: original)
            try require(reply == turn.expected, "\(turn.name): original response changed")
            if reply != .accepted || turn.name == "canonically-equivalent-title" {
                try require(try encoder.encode(original.snapshot.render.document) == before,
                            "\(turn.name): original document changed")
                try require(try originalBytes(original.snapshot) == beforeSnapshot,
                            "\(turn.name): original state changed")
            }
            let input = turn.input
            let projectionReply = input.withUnsafeBufferPointer {
                projected.send(revision: turn.revision, node: turn.node.rawValue, generation: turn.generation,
                               event: turn.event.rawValue, kind: turn.kind.rawValue, input: $0)
            }
            try require(projectionReply == reply, "\(turn.name): host projection response differs")
            let guestReply = try guestSend(turn, session, at: address, input: input)
            let sendFuel = session.fuel
            try require(guestReply == reply.rawValue, "\(turn.name): guest reply differs")
            let actual = try session.snapshot(at: address)
            let expected = try originalBytes(original.snapshot)
            let nativeCount = buffer.withUnsafeMutableBufferPointer { projected.snapshot(into: $0.baseAddress!) }
            try require(actual == expected,
                        "\(turn.name): guest bytes \(actual.prefix(10)) expected \(expected.prefix(10)) (lengths \(actual.count), \(expected.count))")
            try require(buffer.prefix(nativeCount).elementsEqual(expected),
                        "\(turn.name): host projection bytes \(buffer.prefix(10)) expected \(expected.prefix(10))")
            trace.append(contentsOf: [UInt8(index), UInt8(reply.rawValue), UInt8(actual.count)])
            trace.append(contentsOf: actual)
            print("turn=\(turn.name) reply=\(reply) revision=\(original.snapshot.render.document.revision) bytes=\(actual.count) sendFuel=\(sendFuel) snapshotFuel=\(session.fuel)")
        }
        let final = original.snapshot
        try require(final.outcome == .cancelled && final.state.title.utf8.elementsEqual(composed.utf8),
                    "cancel did not publish the reducer's latest title and clear navigation")
        try trace.write(to: URL(fileURLWithPath: args[3]))
        try session.close()
        try original.close()
        print("axis=\(axis) peakFuel=\(session.peakFuel) retiredHandle=refused")
        try await replaySave(guest, in: URL(fileURLWithPath: args[4]))
    }
}
