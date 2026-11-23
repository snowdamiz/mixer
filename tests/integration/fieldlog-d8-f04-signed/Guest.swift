@_extern(c, "fieldlog_storage_get")
func storageGet(_ bytes: UnsafeRawPointer, _ count: UInt32, _ token: UnsafeMutablePointer<UInt64>) -> UInt32
@_extern(c, "fieldlog_storage_put")
func storagePut(_ bytes: UnsafeRawPointer, _ count: UInt32, _ token: UnsafeMutablePointer<UInt64>) -> UInt32
@_extern(c, "fieldlog_poll")
func poll(_ token: UInt64, _ bytes: UnsafeMutableRawPointer, _ capacity: UInt32, _ length: UnsafeMutablePointer<UInt32>) -> UInt32

private enum Phase { case initial, hydrating, editing, saving, retry, saved, unavailable }
private enum Field {
    case title, responsible
    var key: StaticString { self == .title ? "title" : "responsible" }
}
private let alphabet: StaticString = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
private let schemaSuffix: StaticString = #"},"schemaHash":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"}"#
private let headerSize = 32
private let eventCapacity = 4096
private let documentOffset = 4128
private let documentCapacity = 4096
private nonisolated(unsafe) var ui = InlineArray<8224, UInt8>(repeating: 0)
private nonisolated(unsafe) var wire = InlineArray<2048, UInt8>(repeating: 0)
private nonisolated(unsafe) var document = InlineArray<1024, UInt8>(repeating: 0)
private nonisolated(unsafe) var title = InlineArray<256, UInt8>(repeating: 0)
private nonisolated(unsafe) var responsible = InlineArray<256, UInt8>(repeating: 0)
private nonisolated(unsafe) var titleCount = 0
private nonisolated(unsafe) var responsibleCount = 0
private nonisolated(unsafe) var token: UInt64 = 0
private nonisolated(unsafe) var revision: UInt64 = 1
private nonisolated(unsafe) var sequence: UInt64 = 1
private nonisolated(unsafe) var phase: Phase = .initial

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
    let request: StaticString = #"{"key":"task","namespace":"fieldlog-d8-f04-task"}"#
    guard phase == .initial, storageGet(request.utf8Start, UInt32(request.utf8CodeUnitCount), &token) == 0
    else { return 1 }
    phase = .hydrating
    return 0
}

@_cdecl("mixer_guest_ui_event_v1")
public func guestEvent(_ length: UInt32) -> UInt32 {
    #if FIELDLOG_UPDATED
    guard phase == .editing || phase == .retry, length > 0, length <= UInt32(eventCapacity),
          sequence < .max, revision < .max else { return 1 }
    let accepted = withUnsafeBytes(of: &ui) { buffer in
        let event = UnsafeRawBufferPointer(start: buffer.baseAddress! + headerSize, count: Int(length))
        if let value = fieldValue(event, .title) {
            titleCount = value.count
            withUnsafeMutableBytes(of: &title) { $0.copyBytes(from: value) }
            phase = .editing
        } else if let value = fieldValue(event, .responsible) {
            responsibleCount = value.count
            withUnsafeMutableBytes(of: &responsible) { $0.copyBytes(from: value) }
            phase = .editing
        } else {
            var reader = TaskWireReader(event)
            guard reader.consume(#"{"actionID":"save","event":"activate","nodeID":"save","revision":"#),
                  consumeHeader(&reader), reader.consume("null}"), reader.atEnd, titleCount > 0
            else { return false }
            phase = submit() ? .saving : .unavailable
        }
        return true
    }
    guard accepted else { return 1 }
    sequence += 1
    revision += 1
    publish()
    return 0
    #else
    return 1
    #endif
}

private func consumeHeader(_ reader: inout TaskWireReader) -> Bool {
    reader.consume(revision) && reader.consume(#","schemaVersion":1,"sequence":"#)
        && reader.consume(sequence) && reader.consume(#","value":"#)
}

private func fieldValue(_ event: UnsafeRawBufferPointer, _ field: Field) -> UnsafeRawBufferPointer? {
    let key = field.key
    var reader = TaskWireReader(event)
    guard reader.consume(#"{"actionID":""#), reader.consume(key),
          reader.consume(#"","event":"textChange","nodeID":""#), reader.consume(key),
          reader.consume(#"","revision":"#), consumeHeader(&reader), reader.consume("\"")
    else { return nil }
    let contentStart = reader.index
    var end = contentStart
    while end < event.count {
        let byte = event[end]
        if byte == 34 { break }
        guard byte >= 32 else { return nil }
        if byte == 92 { end += 1 }
        end += 1
    }
    guard end + 2 == event.count, event[end + 1] == 125, end - contentStart <= 256
    else { return nil }
    return UnsafeRawBufferPointer(rebasing: event[contentStart..<end])
}

private func submit() -> Bool {
    let length = withUnsafeMutableBytes(of: &document) { bytes in
        var payload = TaskWireWriter(bytes)
        payload.append("[\"")
        withUnsafeBytes(of: &title) { payload.append(UnsafeRawBufferPointer(rebasing: $0[..<titleCount])) }
        payload.append("\",\"")
        withUnsafeBytes(of: &responsible) {
            payload.append(UnsafeRawBufferPointer(rebasing: $0[..<responsibleCount]))
        }
        payload.append("\"]")
        return payload.count
    }
    return withUnsafeMutableBytes(of: &wire) { buffer in
        var output = TaskWireWriter(buffer)
        output.append(#"{"key":"task","namespace":"fieldlog-d8-f04-task","valueBase64":""#)
        withUnsafeBytes(of: &document) {
            appendBase64(UnsafeRawBufferPointer(rebasing: $0[..<length]), to: &output)
        }
        output.append(#""}"#)
        return storagePut(buffer.baseAddress!, UInt32(output.count), &token) == 0
    }
}

private func appendBase64(_ bytes: UnsafeRawBufferPointer, to output: inout TaskWireWriter) {
    withUnsafeTemporaryAllocation(of: UInt8.self, capacity: 4) { quartet in
        for offset in stride(from: 0, to: bytes.count, by: 3) {
            let remaining = bytes.count - offset
            let a = Int(bytes[offset])
            let b = remaining > 1 ? Int(bytes[offset + 1]) : 0
            let c = remaining > 2 ? Int(bytes[offset + 2]) : 0
            quartet[0] = alphabet.utf8Start[a >> 2]
            quartet[1] = alphabet.utf8Start[((a & 3) << 4) | (b >> 4)]
            quartet[2] = remaining > 1 ? alphabet.utf8Start[((b & 15) << 2) | (c >> 6)] : 61
            quartet[3] = remaining > 2 ? alphabet.utf8Start[c & 63] : 61
            output.append(UnsafeRawBufferPointer(quartet))
        }
    }
}

@_cdecl("mixer_guest_capability_ready_v1")
public func guestReady() {
    guard phase == .hydrating || phase == .saving else { return }
    let hydrating = phase == .hydrating
    var length: UInt32 = 0
    let status = withUnsafeMutableBytes(of: &wire) {
        poll(token, $0.baseAddress!, UInt32($0.count), &length)
    }
    if status == 1 { return }
    phase = .unavailable
    if status == 0 && length <= 2048 {
        withUnsafeBytes(of: &wire) { bytes in
            let response = UnsafeRawBufferPointer(rebasing: bytes[..<Int(length)])
            var reader = TaskWireReader(response)
            if hydrating {
                guard reader.consume(#"{"abi":1,"capability":"storage.keyValue.v1","operation":"get","outcome":{"kind":"success","value":{"found":true,"valueBase64":"#)
                else { return }
                // A one-byte slot state, encoded as padded Base64.
                let empty = reader.consume(#""AA=="}"#)
                let saved = !empty && reader.consume(#""AQ=="}"#)
                guard (empty || saved), reader.consume(schemaSuffix), reader.atEnd else { return }
                phase = saved ? .saved : .editing
            } else {
                guard reader.consume(#"{"abi":1,"capability":"storage.keyValue.v1","operation":"put","outcome":{"kind":"success","value":{"committed":"#)
                else { return }
                let committed = reader.consume("true}")
                let refused = !committed && reader.consume("false}")
                guard (committed || refused), reader.consume(schemaSuffix), reader.atEnd else { return }
                phase = committed ? .saved : .retry
            }
        }
    }
    if !hydrating { revision += 1 }
    publish()
}

private func publish() {
    withUnsafeMutableBytes(of: &ui) { buffer in
        let doc = UnsafeMutableRawBufferPointer(start: buffer.baseAddress! + documentOffset, count: documentCapacity)
        var output = TaskWireWriter(doc)
        output.append(#"{"schemaVersion":1,"revision":"#)
        output.append(revision)
        output.append(#","root":{"id":"task-editor","kind":"vStack","properties":{},"actions":[],"children":["#)
        #if FIELDLOG_UPDATED
        if phase != .saved && phase != .unavailable {
            let editable = phase == .editing || phase == .retry
            field(.title, label: "Task", editable: editable, to: &output)
            output.append(",")
            field(.responsible, label: "Responsible person", editable: editable, to: &output)
            output.append(#",{"id":"save","kind":"button","properties":{"label":"Add","disabled":"#)
            output.append(editable && titleCount > 0 ? "false" : "true")
            output.append(#"},"children":[],"actions":[{"id":"save","event":"activate"}]},"#)
        }
        #endif
        output.append(#"{"id":"status","kind":"text","properties":{"text":""#)
        switch phase {
        case .saving: output.append("Saving")
        case .retry: output.append("Save refused before publication")
        case .saved: output.append("Task saved")
        case .unavailable: output.append("Workspace unavailable")
        default: output.append("New task")
        }
        output.append(#""},"actions":[],"children":[]}]}}"#)
        let base = UInt32(UInt(bitPattern: buffer.baseAddress!))
        buffer.storeBytes(of: base + UInt32(documentOffset), toByteOffset: 8, as: UInt32.self)
        buffer.storeBytes(of: UInt32(output.count), toByteOffset: 12, as: UInt32.self)
    }
}

private func field(_ field: Field, label: StaticString, editable: Bool, to output: inout TaskWireWriter) {
    output.append(#"{"id":""#)
    output.append(field.key)
    output.append(#"","kind":"textField","properties":{"label":""#)
    output.append(label)
    output.append(#"","value":""#)
    if field == .title {
        withUnsafeBytes(of: &title) { output.append(UnsafeRawBufferPointer(rebasing: $0[..<titleCount])) }
    } else {
        withUnsafeBytes(of: &responsible) {
            output.append(UnsafeRawBufferPointer(rebasing: $0[..<responsibleCount]))
        }
    }
    output.append(#"","disabled":"#)
    output.append(editable ? "false" : "true")
    output.append(#"},"children":[],"actions":[{"id":""#)
    output.append(field.key)
    output.append(#"","event":"textChange"}]}"#)
}
