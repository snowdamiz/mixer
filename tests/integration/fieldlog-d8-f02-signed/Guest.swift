@_extern(c, "fieldlog_storage_get")
func storageGet(_ bytes: UnsafeRawPointer, _ count: UInt32, _ token: UnsafeMutablePointer<UInt64>) -> UInt32
@_extern(c, "fieldlog_storage_put")
func storagePut(_ bytes: UnsafeRawPointer, _ count: UInt32, _ token: UnsafeMutablePointer<UInt64>) -> UInt32
@_extern(c, "fieldlog_poll")
func poll(_ token: UInt64, _ bytes: UnsafeMutableRawPointer, _ capacity: UInt32, _ length: UnsafeMutablePointer<UInt32>) -> UInt32

private let headerSize = 32
private let eventCapacity = 4096
private let documentOffset = 4128
private let documentCapacity = 6144
private nonisolated(unsafe) var ui = InlineArray<10272, UInt8>(repeating: 0)
private nonisolated(unsafe) var capability = InlineArray<2048, UInt8>(repeating: 0)
private nonisolated(unsafe) var payload = InlineArray<609, UInt8>(repeating: 0)
private nonisolated(unsafe) var rows = InlineArray<2, TaskRow>(repeating: TaskRow())
private nonisolated(unsafe) var token: UInt64 = 0
private nonisolated(unsafe) var phase: Phase = .beforeHydration
private nonisolated(unsafe) var revision: UInt64 = 1
private nonisolated(unsafe) var sequence: UInt64 = 1
private nonisolated(unsafe) var workspaceRevision: UInt64 = 0

private enum Move {
    case up, down

    var key: StaticString { self == .up ? "move-up-" : "move-down-" }
    var label: StaticString { self == .up ? "Move up" : "Move down" }

    func permitted(at index: Int) -> Bool {
        self == .up ? index > 0 : index < rowCount - 1
    }
}

private enum Phase { case beforeHydration, hydration, displayed, write, refresh, unavailable }

@_cdecl("mixer_guest_ui_start_v1")
public func guestStart() -> UInt32 {
    withUnsafeMutableBytes(of: &ui) { buffer in
        let base = UInt32(UInt(bitPattern: buffer.baseAddress!))
        buffer.storeBytes(of: UInt32(0x3155494d), as: UInt32.self)
        buffer.storeBytes(of: UInt32(headerSize), toByteOffset: 4, as: UInt32.self)
        buffer.storeBytes(of: base + UInt32(headerSize), toByteOffset: 16, as: UInt32.self)
        buffer.storeBytes(of: UInt32(eventCapacity), toByteOffset: 20, as: UInt32.self)
        return base
    }
}

@_cdecl("mixer_guest_ui_hydrate_v1")
public func hydrate() -> UInt32 {
    guard phase == .beforeHydration, submitRead() else { return 1 }
    phase = .hydration
    return 0
}

@_cdecl("mixer_guest_ui_event_v1")
public func guestEvent(_ length: UInt32) -> UInt32 {
    #if FIELDLOG_UPDATED
    guard phase == .displayed || phase == .write || phase == .refresh,
          length > 0, length <= UInt32(eventCapacity), sequence < .max else { return 1 }
    let command = withUnsafeBytes(of: &ui) { interface in
        withUnsafeBytes(of: &payload) { data -> (Int, Move)? in
            let event = UnsafeRawBufferPointer(start: interface.baseAddress! + headerSize, count: Int(length))
            for index in 0..<rowCount {
                let id = UnsafeRawBufferPointer(rebasing: data[rows[index].id])
                let move: Move = index == 0 ? .down : .up
                var reader = TaskWireReader(event)
                if reader.consume(#"{"actionID":""#), reader.consume(move.key), reader.consume(id),
                   reader.consume(#"","event":"activate","nodeID":""#), reader.consume(move.key), reader.consume(id),
                   reader.consume(#"","revision":"#), reader.consume(revision),
                   reader.consume(#","schemaVersion":1,"sequence":"#), reader.consume(sequence),
                   reader.consume(#","value":null}"#), reader.atEnd { return (index, move) }
            }
            return nil
        }
    }
    guard let (selectedRow, move) = command else { return 1 }
    sequence += 1
    guard phase == .displayed else { return 0 }
    if submitMove(selectedRow, move: move) {
        phase = .write
    } else {
        refresh()
    }
    return 0
    #else
    return 1
    #endif
}

@_cdecl("mixer_guest_capability_ready_v1")
public func guestReady() {
    guard phase == .hydration || phase == .write || phase == .refresh else { return }
    var length: UInt32 = 0
    let status = withUnsafeMutableBytes(of: &capability) { buffer in
        poll(token, buffer.baseAddress!, UInt32(buffer.count), &length)
    }
    if status == 1 { return }
    if phase == .write {
        refresh()
        return
    }
    let read = status == 0 && readResult(length)
    if phase == .hydration {
        precondition(read)
        phase = .displayed
        publish()
    } else {
        finishRefresh(success: read)
    }
}

private func submitRead() -> Bool {
    let arguments: StaticString = #"{"key":"rows","namespace":"fieldlog-task-v1"}"#
    return storageGet(arguments.utf8Start, UInt32(arguments.utf8CodeUnitCount), &token) == 0
}

#if FIELDLOG_UPDATED
private func submitMove(_ row: Int, move: Move) -> Bool {
    withUnsafeBytes(of: &payload) { data in
        let id = UnsafeRawBufferPointer(rebasing: data[rows[row].id])
        return withUnsafeMutableBytes(of: &capability) { buffer in
            var writer = TaskWireWriter(buffer)
            writer.append(#"{"key":""#)
            writer.append(move.key)
            writer.append(id)
            writer.append(#"","namespace":"fieldlog-task-v1","valueBase64":""#)
            writer.appendBase64Decimal(workspaceRevision)
            writer.append(#""}"#)
            return storagePut(buffer.baseAddress!, UInt32(writer.count), &token) == 0
        }
    }
}
#endif

private func refresh() {
    if submitRead() {
        phase = .refresh
    } else {
        finishRefresh(success: false)
    }
}

private func finishRefresh(success: Bool) {
    precondition(revision < .max)
    revision += 1
    phase = success ? .displayed : .unavailable
    publish()
}

private func readResult(_ length: UInt32) -> Bool {
    withUnsafeBytes(of: &capability) { input in
        guard length <= UInt32(input.count) else { return false }
        var response = TaskWireReader(UnsafeRawBufferPointer(rebasing: input[..<Int(length)]))
        guard response.consume(#"{"abi":1,"capability":"storage.keyValue.v1","operation":"get","outcome":{"kind":"success","value":{"found":true,"valueBase64":""#)
        else { return false }

        return withUnsafeMutableBytes(of: &payload) { decoded in
            precondition(decoded.count == payloadCapacity)
            guard let count = response.decodeBase64(into: decoded),
                  response.consume(#""}},"schemaHash":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"}"#),
                  response.atEnd else { return false }
            let data = UnsafeRawBufferPointer(rebasing: decoded[..<count])
            var reader = TaskWireReader(data)
            guard let incomingRevision = reader.revisionLine(),
                  phase == .hydration || incomingRevision >= workspaceRevision else { return false }
            for index in 0..<rowCount {
                guard let row = reader.row() else { return false }
                for earlier in 0..<index where data[row.id].elementsEqual(data[rows[earlier].id]) {
                    return false
                }
                rows[index] = row
            }
            guard reader.atEnd else { return false }
            workspaceRevision = incomingRevision
            return true
        }
    }
}

private func publish() {
    withUnsafeMutableBytes(of: &ui) { buffer in
        let doc = UnsafeMutableRawBufferPointer(start: buffer.baseAddress! + documentOffset, count: documentCapacity)
        var output = TaskWireWriter(doc)
        output.append(#"{"schemaVersion":1,"revision":"#)
        output.append(revision)
        output.append(#","root":{"id":"fieldlog-rows","kind":"vStack","properties":{},"actions":[],"children":["#)
        if phase == .unavailable {
            output.append(#"{"id":"status","kind":"text","properties":{"text":"Saved tasks unavailable"},"children":[],"actions":[]}"#)
        } else {
            #if FIELDLOG_UPDATED
            output.append(#"{"id":"heading","kind":"text","properties":{"text":"Reorder tasks"},"children":[],"actions":[]},"#)
            #endif
            withUnsafeBytes(of: &payload) { data in
                for index in 0..<rowCount {
                    if index > 0 { output.append(",") }
                    appendRow(index, data: data, to: &output)
                }
            }
        }
        output.append("]}}")
        let base = UInt32(UInt(bitPattern: buffer.baseAddress!))
        buffer.storeBytes(of: base + UInt32(documentOffset), toByteOffset: 8, as: UInt32.self)
        buffer.storeBytes(of: UInt32(output.count), toByteOffset: 12, as: UInt32.self)
    }
}

private func appendRow(_ index: Int, data: UnsafeRawBufferPointer, to output: inout TaskWireWriter) {
    let id = UnsafeRawBufferPointer(rebasing: data[rows[index].id])
    let title = UnsafeRawBufferPointer(rebasing: data[rows[index].title])
    output.append(#"{"id":"row-"#)
    output.append(id)
    #if FIELDLOG_HSTACK
    output.append(#"","kind":"hStack""#)
    #else
    output.append(#"","kind":"vStack""#)
    #endif
    output.append(#","properties":{},"actions":[],"children":[{"id":"title-"#)
    output.append(id)
    output.append(#"","kind":"text","properties":{"accessibilityIdentifier":"title-"#)
    output.append(id)
    output.append(#"","text":""#)
    output.appendEscapedTitle(title)
    output.append(#""},"children":[],"actions":[]}"#)
    #if FIELDLOG_UPDATED
    let move: Move = index == 0 ? .down : .up
    precondition(move.permitted(at: index))
    output.append(#",{"id":""#)
    output.append(move.key)
    output.append(id)
    output.append(#"","kind":"button","properties":{"label":""#)
    output.append(move.label)
    output.append(#""},"children":[],"actions":[{"id":""#)
    output.append(move.key)
    output.append(id)
    output.append(#"","event":"activate"}]}"#)
    #endif
    output.append("]}")
}
