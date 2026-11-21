@_extern(c, "editor_get")
private func storageGet(_ arguments: UnsafeRawPointer, _ length: UInt32,
                        _ token: UnsafeMutablePointer<UInt64>) -> Int32

@_extern(c, "editor_put")
private func storagePut(_ arguments: UnsafeRawPointer, _ length: UInt32,
                        _ token: UnsafeMutablePointer<UInt64>) -> Int32

@_extern(c, "editor_poll")
private func poll(_ token: UInt64, _ response: UnsafeMutableRawPointer, _ capacity: UInt32,
                  _ length: UnsafeMutablePointer<UInt32>) -> Int32

private let eventOffset = 32
private let eventCapacity = 4096
private let documentOffset = 4128
private nonisolated(unsafe) var memory = InlineArray<69_664, UInt8>(repeating: 0)
private nonisolated(unsafe) var projection = InlineArray<16_394, UInt8>(repeating: 0)
private nonisolated(unsafe) var reply = InlineArray<512, UInt8>(repeating: 0)
private nonisolated(unsafe) var editor = EditorBoundary(titleGeneration: 1, cancelGeneration: 2, saveGeneration: 3)
private nonisolated(unsafe) var publishedRevision: UInt64 = 1
private nonisolated(unsafe) var nextSequence: UInt64 = 1
private enum SaveRequest { case none, facts(UInt64), commit(UInt64) }
private nonisolated(unsafe) var request = SaveRequest.none

@_cdecl("mixer_guest_ui_start_v1")
public func start() -> UInt32 {
    publish()
    return withUnsafeMutableBytes(of: &memory) { buffer in
        let offset = address(buffer.baseAddress!)
        word(0x3155494d, at: 0, in: buffer)
        word(32, at: 4, in: buffer)
        word(offset + UInt32(eventOffset), at: 16, in: buffer)
        word(UInt32(eventCapacity), at: 20, in: buffer)
        return offset
    }
}

private struct Event {
    let node: EditorNode
    let bytes: [UInt8]

    static func decode(_ input: UnsafeRawBufferPointer) -> Event? {
        for (node, id, route) in [(EditorNode.title, "task.title", "task.title.change"),
                                  (EditorNode.cancel, "task.cancel", "task.cancel"),
                                  (EditorNode.save, "task.save", "task.save")] as [(EditorNode, StaticString, StaticString)] {
            var wire = EditorWireInput(input)
            let event: StaticString = node == .title ? "textChange" : "activate"
            guard wire.expect(#"{"actionID":""#), wire.expect(route), wire.expect(#"","event":""#),
                  wire.expect(event), wire.expect(#"","nodeID":""#), wire.expect(id),
                  wire.expect(#"","revision":"#), wire.expectDecimal(publishedRevision),
                  wire.expect(#","schemaVersion":1,"sequence":"#), wire.expectDecimal(nextSequence),
                  wire.expect(#","value":"#) else { continue }
            if node == .title {
                guard let title = wire.title(), wire.expect("}"), wire.atEnd else { return nil }
                return Event(node: node, bytes: title)
            }
            return wire.expect("null}") && wire.atEnd ? Event(node: node, bytes: []) : nil
        }
        return nil
    }
}

@_cdecl("mixer_guest_ui_event_v1")
public func event(_ count: UInt32) -> UInt32 {
    guard case .none = request, (1...UInt32(eventCapacity)).contains(count), nextSequence < .max else { return 1 }
    let action = withUnsafeBytes(of: &memory) { buffer in
        Event.decode(UnsafeRawBufferPointer(rebasing: buffer[eventOffset..<(eventOffset + Int(count))]))
    }
    guard let action else { return 1 }
    let editing = action.node == .title
    let status = action.bytes.withUnsafeBufferPointer { bytes in
        editor.send(revision: publishedRevision, node: action.node.rawValue, generation: UInt64(action.node.rawValue),
            event: (editing ? EditorEvent.textChange : .activate).rawValue,
            kind: (editing ? EditorValue.text : .null).rawValue, input: bytes)
    }
    guard status == .accepted else { return 1 }
    nextSequence += 1
#if FIELDLOG_EDITOR_TEST_ABSENT_SAVING
    if action.node != .save { publish() }
#else
    publish()
#endif
    if action.node == .save {
        let taken = withUnsafeMutableBytes(of: &reply) { buffer in
            editor.takeSave(into: buffer.baseAddress!.assumingMemoryBound(to: UInt8.self))
        }
        guard taken > 0, let token = send(#"{"key":"task-save-facts","namespace":"fieldlog_editor"}"#, put: false) else { return 1 }
        request = .facts(token)
    }
    return 0
}

@_cdecl("mixer_guest_capability_ready_v1")
public func ready() {
    let token: UInt64
    let expected: StaticString
    switch request {
    case .none: return
    case .facts(let origin):
        token = origin
        expected = #"{"abi":1,"capability":"storage.keyValue.v1","operation":"get","outcome":{"kind":"success","value":{"found":true,"valueBase64":"AQ=="}},"schemaHash":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"}"#
    case .commit(let origin):
        token = origin
        expected = #"{"abi":1,"capability":"storage.keyValue.v1","operation":"put","outcome":{"kind":"success","value":{"committed":true}},"schemaHash":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"}"#
    }
    var size: UInt32 = 0
    let status = withUnsafeMutableBytes(of: &reply) { buffer in
        poll(token, buffer.baseAddress!, UInt32(buffer.count), &size)
    }
    precondition(status == 0 && size <= 512)
    let matched = withUnsafeBytes(of: &reply) { buffer in
        var input = EditorWireInput(UnsafeRawBufferPointer(rebasing: buffer.prefix(Int(size))))
        return input.expect(expected) && input.atEnd
    }
    // A denial, failed write or uncertain completion stops this guest. It has
    // no retry path and publishes Saved only for the originating success.
    precondition(matched)
    switch request {
    case .none: preconditionFailure()
    case .facts:
        guard let next = send(#"{"key":"task-save-commit","namespace":"fieldlog_editor","valueBase64":"AQ=="}"#,
                              put: true) else { preconditionFailure() }
        request = .commit(next)
    case .commit:
        request = .none
        precondition(editor.completeSave() == .accepted)
        publish()
    }
}

private func send(_ argument: StaticString, put: Bool) -> UInt64? {
    var token: UInt64 = 0
    let size = UInt32(argument.utf8CodeUnitCount)
    let status = put ? storagePut(argument.utf8Start, size, &token) : storageGet(argument.utf8Start, size, &token)
    return status == 0 && token != 0 ? token : nil
}

private func publish() {
    let count = withUnsafeMutableBytes(of: &projection) { bytes in
        editor.snapshot(into: bytes.baseAddress!.assumingMemoryBound(to: UInt8.self))
    }
    withUnsafeBytes(of: &projection) { snapshot in
        var revision: UInt64 = 0
        for index in 0..<8 { revision |= UInt64(snapshot[index]) << (8 * index) }
        publishedRevision = revision
#if FIELDLOG_EDITOR_TEST_REJECTED_SAVING
        let phase = snapshot[8] == 2 ? 0 : snapshot[8]
#else
        let phase = snapshot[8]
#endif
        let title = UnsafeBufferPointer(start: snapshot.baseAddress!.assumingMemoryBound(to: UInt8.self) + 10,
                                        count: count - 10)
        withUnsafeMutableBytes(of: &memory) { buffer in
            let document = UnsafeMutableRawBufferPointer(rebasing: buffer[documentOffset...])
            var output = EditorWireOutput(document)
            render(&output, revision: revision, phase: phase, title: title)
            word(address(document.baseAddress!), at: 8, in: buffer)
            word(UInt32(output.count), at: 12, in: buffer)
        }
    }
}

private func address(_ pointer: UnsafeRawPointer) -> UInt32 { UInt32(UInt(bitPattern: pointer)) }

private func word(_ value: UInt32, at offset: Int, in buffer: UnsafeMutableRawBufferPointer) {
    buffer.storeBytes(of: value.littleEndian, toByteOffset: offset, as: UInt32.self)
}
