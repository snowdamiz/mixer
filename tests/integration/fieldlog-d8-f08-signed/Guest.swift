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
private nonisolated(unsafe) var outboxCount: UInt64 = 0
private nonisolated(unsafe) var queueVisible = false

private let roof: StaticString = "F0800000-0000-4000-8000-000000000004"
private let delivery: StaticString = "F0800000-0000-4000-8000-000000000005"
private let complete: StaticString = "complete-F0800000-0000-4000-8000-000000000004"
private let reorder: StaticString = "move-up-F0800000-0000-4000-8000-000000000005"

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
    guard phase == .displayed || phase == .write || phase == .refresh,
          length > 0, length <= UInt32(eventCapacity), sequence < .max else { return 1 }
    let previousRevision = revision
    let result: UInt32 = withUnsafeBytes(of: &ui) { interface in
        let event = UnsafeRawBufferPointer(start: interface.baseAddress! + headerSize, count: Int(length))
        if matches(event, queueVisible ? "back" : "queue") {
            guard phase == .displayed else { return 1 }
            sequence += 1
            queueVisible.toggle()
            revision += 1
            return 0
        }
        return mutation(event)
    }
    if revision != previousRevision { publish() }
    if phase == .refresh && result == 2 { refresh(); return 0 }
    return result
}

private func matches(_ event: UnsafeRawBufferPointer, _ id: StaticString) -> Bool {
    var reader = TaskWireReader(event)
    return reader.consume(#"{"actionID":""#) && reader.consume(id)
        && reader.consume(#"","event":"activate","nodeID":""#) && reader.consume(id)
        && reader.consume(#"","revision":"#) && reader.consume(revision)
        && reader.consume(#","schemaVersion":1,"sequence":"#) && reader.consume(sequence)
        && reader.consume(#","value":null}"#) && reader.atEnd
}

private func mutation(_ event: UnsafeRawBufferPointer) -> UInt32 {
    #if FIELDLOG_UPDATED
    guard !queueVisible else { return 1 }
    let command: StaticString
    if !isCompleted(0), isRow(0, roof), matches(event, complete) { command = complete }
    else if isRow(1, delivery), matches(event, reorder) { command = reorder }
    else { return 1 }
    sequence += 1
    guard phase == .displayed else { return 0 }
    if submitWrite(command) { phase = .write }
    else { phase = .refresh; return 2 }
    return 0
    #else
    return 1
    #endif
}

private func isRow(_ index: Int, _ id: StaticString) -> Bool {
    withUnsafeBytes(of: &payload) { data in
        var reader = TaskWireReader(UnsafeRawBufferPointer(rebasing: data[rows[index].id]))
        return reader.consume(id) && reader.atEnd
    }
}

private func isCompleted(_ index: Int) -> Bool {
    withUnsafeBytes(of: &payload) { $0[rows[index].title.lowerBound] == 49 }
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
    let arguments: StaticString = #"{"key":"rows","namespace":"fieldlog-f08-v1"}"#
    return storageGet(arguments.utf8Start, UInt32(arguments.utf8CodeUnitCount), &token) == 0
}

#if FIELDLOG_UPDATED
private func submitWrite(_ command: StaticString) -> Bool {
    withUnsafeMutableBytes(of: &capability) { buffer in
        var writer = TaskWireWriter(buffer)
        writer.append(#"{"key":""#)
        writer.append(command)
        writer.append(#"","namespace":"fieldlog-f08-v1","valueBase64":""#)
        writer.appendBase64Decimal(workspaceRevision)
        writer.append(#""}"#)
        return storagePut(buffer.baseAddress!, UInt32(writer.count), &token) == 0
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
                  phase == .hydration || incomingRevision >= workspaceRevision,
                  let incomingCount = reader.revisionLine(), (3...5).contains(incomingCount) else { return false }
            for index in 0..<rowCount {
                guard let row = reader.row(), row.title.count > 2,
                      data[row.title.lowerBound] == 48 || data[row.title.lowerBound] == 49,
                      data[row.title.lowerBound + 1] == 124 else { return false }
                for earlier in 0..<index where data[row.id].elementsEqual(data[rows[earlier].id]) {
                    return false
                }
                rows[index] = row
            }
            guard reader.atEnd else { return false }
            workspaceRevision = incomingRevision
            outboxCount = incomingCount
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
        } else if queueVisible {
            appendQueue(to: &output)
        } else {
            output.append(#"{"id":"progress","kind":"text","properties":{"text":""#)
            output.append(UInt64((isCompleted(0) ? 1 : 0) + (isCompleted(1) ? 1 : 0)))
            output.append(#" of 2 tasks completed"},"children":[],"actions":[]}"#)
            withUnsafeBytes(of: &payload) { data in
                for index in 0..<rowCount {
                    output.append(",")
                    appendRow(index, data: data, to: &output)
                }
            }
            button("queue", "Pending changes", to: &output)
        }
        output.append("]}}")
        let base = UInt32(UInt(bitPattern: buffer.baseAddress!))
        buffer.storeBytes(of: base + UInt32(documentOffset), toByteOffset: 8, as: UInt32.self)
        buffer.storeBytes(of: UInt32(output.count), toByteOffset: 12, as: UInt32.self)
    }
}

private func appendRow(_ index: Int, data: UnsafeRawBufferPointer, to output: inout TaskWireWriter) {
    let row = rows[index]
    let id = UnsafeRawBufferPointer(rebasing: data[row.id])
    let title = UnsafeRawBufferPointer(rebasing: data[(row.title.lowerBound + 2)..<row.title.upperBound])
    let done = data[row.title.lowerBound] == 49
    output.append(#"{"id":"row-"#)
    output.append(id)
    output.append(#"","kind":"vStack","properties":{},"actions":[],"children":[{"id":"title-"#)
    output.append(id)
    output.append(#"","kind":"text","properties":{"text":""#)
    output.appendEscapedTitle(title)
    output.append(done ? " · Completed" : " · Not completed")
    output.append(#""},"children":[],"actions":[]}"#)
    #if FIELDLOG_UPDATED
    if index == 0, !done, isRow(0, roof) { button(complete, "Complete: Inspect roof", to: &output) }
    if index == 1, isRow(1, delivery) { button(reorder, "Move up: Record delivery", to: &output) }
    #endif
    output.append("]}")
}

private func appendQueue(to output: inout TaskWireWriter) {
    output.append(#"{"id":"queue-info","kind":"text","properties":{"text":"Records are saved on this device. Sending is unavailable for this project."},"children":[],"actions":[]}"#)
    if outboxCount == 5 { queueRow("5", "Checklist reordered", to: &output) }
    if outboxCount >= 4 { queueRow("4", "Task updated: Inspect roof", to: &output) }
    queueRow("3", "Entry saved", to: &output)
    queueRow("2", "Task updated: Record delivery", to: &output)
    queueRow("1", "Project created", to: &output)
    button("back", "Back to checklist", to: &output)
}

private func queueRow(_ id: StaticString, _ label: StaticString, to output: inout TaskWireWriter) {
    output.append(#",{"id":"change-"#)
    output.append(id)
    output.append(#"","kind":"text","properties":{"text":""#)
    output.append(label)
    output.append(#" — Saved on device"},"children":[],"actions":[]}"#)
}

private func button(_ id: StaticString, _ label: StaticString, to output: inout TaskWireWriter) {
    output.append(#",{"id":""#)
    output.append(id)
    output.append(#"","kind":"button","properties":{"label":""#)
    output.append(label)
    output.append(#""},"children":[],"actions":[{"id":""#)
    output.append(id)
    output.append(#"","event":"activate"}]}"#)
}
