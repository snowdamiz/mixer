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
private let pageSize = 20
private let target: StaticString = "F0900000-0000-4000-8000-000000000120"
private let move: StaticString = "task.f0900000-0000-4000-8000-000000000120.up"
private let moveKey: StaticString = "move-up-F0900000-0000-4000-8000-000000000120"
private enum Phase { case startup, hydration, displayed, write, refresh, unavailable }

private nonisolated(unsafe) var ui = InlineArray<10272, UInt8>(repeating: 0)
private nonisolated(unsafe) var capability = InlineArray<4096, UInt8>(repeating: 0)
private nonisolated(unsafe) var payload = InlineArray<2048, UInt8>(repeating: 0)
private nonisolated(unsafe) var rows = InlineArray<23, TaskRow>(repeating: TaskRow())
private nonisolated(unsafe) var token: UInt64 = 0
private nonisolated(unsafe) var phase: Phase = .startup
private nonisolated(unsafe) var revision: UInt64 = 1
private nonisolated(unsafe) var sequence: UInt64 = 1
private nonisolated(unsafe) var workspaceRevision: UInt64 = 0
private nonisolated(unsafe) var page = 0

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
    guard phase == .startup, submitRead() else { return 1 }
    phase = .hydration
    return 0
}

@_cdecl("mixer_guest_ui_event_v1")
public func guestEvent(_ length: UInt32) -> UInt32 {
    #if FIELDLOG_UPDATED
    guard phase == .displayed, length > 0, length <= UInt32(eventCapacity), sequence < .max, revision < .max else { return 1 }
    let action = withUnsafeBytes(of: &ui) { interface in
        let event = UnsafeRawBufferPointer(start: interface.baseAddress! + headerSize, count: Int(length))
        if page == 0, matches(event, "tasks.next") { return 1 }
        if page == 1, matches(event, "tasks.previous") { return 0 }
        if canMove(), matches(event, move) { return 2 }
        return -1
    }
    guard action >= 0 else { return 1 }
    sequence += 1
    if action == 2 {
        guard submitMove() else { return 1 }
        phase = .write
    } else {
        page = action
        revision += 1
        publish()
    }
    return 0
    #else
    return 1
    #endif
}

private func matches(_ event: UnsafeRawBufferPointer, _ id: StaticString) -> Bool {
    var reader = TaskWireReader(event)
    return reader.consume(#"{"actionID":""#) && reader.consume(id)
        && reader.consume(#"","event":"activate","nodeID":""#) && reader.consume(id)
        && reader.consume(#"","revision":"#) && reader.consume(revision)
        && reader.consume(#","schemaVersion":1,"sequence":"#) && reader.consume(sequence)
        && reader.consume(#","value":null}"#) && reader.atEnd
}

private func canMove() -> Bool {
    guard page == 1, workspaceRevision == 1 else { return false }
    return withUnsafeBytes(of: &payload) { data in
        var reader = TaskWireReader(UnsafeRawBufferPointer(rebasing: data[rows[pageSize].id]))
        return reader.consume(target) && reader.atEnd
    }
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
        if status == 0 && submitRead() { phase = .refresh }
        else { phase = .unavailable; revision += 1; publish() }
        return
    }
    let hydrated = phase == .hydration
    let read = status == 0 && readResult(length)
    if !hydrated {
        revision += 1
        if read && workspaceRevision == 2 { page = 0 }
    }
    phase = read ? .displayed : .unavailable
    publish()
}

private func submitRead() -> Bool {
    let arguments: StaticString = #"{"key":"rows","namespace":"fieldlog-f09-v1"}"#
    return storageGet(arguments.utf8Start, UInt32(arguments.utf8CodeUnitCount), &token) == 0
}

private func submitMove() -> Bool {
    withUnsafeMutableBytes(of: &capability) { buffer in
        var writer = TaskWireWriter(buffer)
        writer.append(#"{"key":""#)
        writer.append(moveKey)
        writer.append(#"","namespace":"fieldlog-f09-v1","valueBase64":""#)
        writer.appendBase64Decimal(workspaceRevision)
        writer.append(#""}"#)
        return storagePut(buffer.baseAddress!, UInt32(writer.count), &token) == 0
    }
}

private func readResult(_ length: UInt32) -> Bool {
    withUnsafeBytes(of: &capability) { input in
        guard length <= UInt32(input.count) else { return false }
        var response = TaskWireReader(UnsafeRawBufferPointer(rebasing: input[..<Int(length)]))
        guard response.consume(#"{"abi":1,"capability":"storage.keyValue.v1","operation":"get","outcome":{"kind":"success","value":{"found":true,"valueBase64":""#)
        else { return false }
        return withUnsafeMutableBytes(of: &payload) { decoded in
            guard let count = response.decodeBase64(into: decoded),
                  response.consume(#""}},"schemaHash":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"}"#),
                  response.atEnd else { return false }
            let data = UnsafeRawBufferPointer(rebasing: decoded[..<count])
            var reader = TaskWireReader(data)
            guard let incoming = reader.revisionLine(), (1...2).contains(incoming), incoming >= workspaceRevision else { return false }
            for index in 0..<rowCount {
                guard let row = reader.row(), row.title.count > 2,
                      data[row.id.lowerBound] == 70,
                      data[(row.id.lowerBound + 1)..<row.id.upperBound].allSatisfy({ $0 < 65 }),
                      data[row.title.lowerBound] == 48 || data[row.title.lowerBound] == 49,
                      data[row.title.lowerBound + 1] == 124 else { return false }
                rows[index] = row
            }
            guard reader.atEnd else { return false }
            workspaceRevision = incoming
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
        output.append(#"{"id":"tasks.position","kind":"text","properties":{"text":""#)
        if phase == .unavailable {
            output.append("Saved tasks unavailable")
        } else {
            #if FIELDLOG_UPDATED
            output.append(page == 0 ? "Page 1 of 2 · Tasks 1–20 of 23" : "Page 2 of 2 · Tasks 21–23 of 23")
            #else
            output.append("Checklist")
            #endif
        }
        output.append(#""},"children":[],"actions":[]}"#)
        if phase == .displayed {
            #if FIELDLOG_UPDATED
            let start = page * pageSize
            let end = min(start + pageSize, rowCount)
            button("tasks.previous", "Previous", disabled: page == 0, to: &output)
            button("tasks.next", "Next", disabled: page == 1, to: &output)
            #else
            let start = 0
            let end = rowCount
            #endif
            withUnsafeBytes(of: &payload) { data in
                for index in start..<end { appendRow(index, data: data, to: &output) }
            }
            #if FIELDLOG_UPDATED
            if canMove() { button(move, "Move up: Verify café drain", disabled: false, to: &output) }
            #endif
        }
        output.append("]}}")
        let base = UInt32(UInt(bitPattern: buffer.baseAddress!))
        buffer.storeBytes(of: base + UInt32(documentOffset), toByteOffset: 8, as: UInt32.self)
        buffer.storeBytes(of: UInt32(output.count), toByteOffset: 12, as: UInt32.self)
    }
}

private func appendRow(_ index: Int, data: UnsafeRawBufferPointer, to output: inout TaskWireWriter) {
    let row = rows[index]
    let idSuffix = UnsafeRawBufferPointer(rebasing: data[(row.id.lowerBound + 1)..<row.id.upperBound])
    let title = UnsafeRawBufferPointer(rebasing: data[(row.title.lowerBound + 2)..<row.title.upperBound])
    output.append(#",{"id":"task.f"#)
    output.append(idSuffix)
    output.append(#".title","kind":"text","properties":{"text":""#)
    output.append(UInt64(index + 1))
    output.append(". ")
    output.appendEscapedTitle(title)
    output.append(data[row.title.lowerBound] == 49 ? " · Completed" : " · Not completed")
    output.append(#""},"children":[],"actions":[]}"#)
}

private func button(_ id: StaticString, _ label: StaticString, disabled: Bool, to output: inout TaskWireWriter) {
    output.append(#",{"id":""#)
    output.append(id)
    output.append(#"","kind":"button","properties":{"label":""#)
    output.append(label)
    output.append(disabled ? #"","disabled":true"# : #"","disabled":false"#)
    output.append(#"},"children":[],"actions":[{"id":""#)
    output.append(id)
    output.append(#"","event":"activate"}]}"#)
}
