@_extern(c, "fieldlog_storage_get")
func storageGet(_ bytes: UnsafeRawPointer, _ count: UInt32, _ token: UnsafeMutablePointer<UInt64>) -> UInt32
@_extern(c, "fieldlog_storage_put")
func storagePut(_ bytes: UnsafeRawPointer, _ count: UInt32, _ token: UnsafeMutablePointer<UInt64>) -> UInt32
@_extern(c, "fieldlog_poll")
func poll(_ token: UInt64, _ bytes: UnsafeMutableRawPointer, _ capacity: UInt32, _ length: UnsafeMutablePointer<UInt32>) -> UInt32

private let headerSize = 32
private let eventCapacity = 4096
private let documentOffset = 4128
private let bufferCapacity = 1024
private nonisolated(unsafe) var ui = InlineArray<6176, UInt8>(repeating: 0)
private nonisolated(unsafe) var capability = InlineArray<1024, UInt8>(repeating: 0)
private nonisolated(unsafe) var token: UInt64 = 0
private nonisolated(unsafe) var request: Request = .none
private nonisolated(unsafe) var revision: UInt64 = 1
private nonisolated(unsafe) var sequence: UInt64 = 1
private nonisolated(unsafe) var storedRevision: UInt64 = 0
private nonisolated(unsafe) var flags: UInt8 = 0
private nonisolated(unsafe) var available = false
private let actionID: StaticString = "draft.action"
private enum Request { case none, hydration, read, write }

@_cdecl("mixer_guest_ui_start_v1")
public func guestStart() -> UInt32 {
    return withUnsafeMutableBytes(of: &ui) { buffer in
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
    guard request == .none else { return 1 }
    request = .hydration
    return submitRead() ? 0 : 1
}

@_cdecl("mixer_guest_ui_event_v1")
public func guestEvent(_ length: UInt32) -> UInt32 {
    guard length > 0, length <= UInt32(eventCapacity), sequence < .max else { return 1 }
    let matches = withUnsafeBytes(of: &ui) { buffer in
        var parser = TaskWireReader(UnsafeRawBufferPointer(start: buffer.baseAddress! + headerSize, count: Int(length)))
        return parser.consume(#"{"actionID":""#) && parser.consume(actionID)
            && parser.consume(#"","event":"activate","nodeID":"toggle","revision":"#)
            && parser.consume(revision) && parser.consume(#","schemaVersion":1,"sequence":"#)
            && parser.consume(sequence) && parser.consume(#","value":null}"#) && parser.atEnd
    }
    guard matches else { return 1 }
    sequence += 1
    guard request == .none else { return 0 }
    #if OPTIONAL_FIELD
    if available {
        request = .write
        guard submitWrite() else { return 1 }
    } else {
        request = .read
        guard submitRead() else { return 1 }
    }
    #else
    request = .read
    guard submitRead() else { return 1 }
    #endif
    return 0
}

@_cdecl("mixer_guest_capability_ready_v1")
public func guestReady() {
    guard request != .none else { return }
    var length: UInt32 = 0
    let result = withUnsafeMutableBytes(of: &capability) { buffer in
        poll(token, buffer.baseAddress!, UInt32(buffer.count), &length)
    }
    if result == 1 { return } // Another completion can wake this guest.
    let finished = request
    request = .none
    if finished == .hydration {
        // A denied, missing, invalid or failed read must publish no task or action.
        precondition(result == 0 && length <= UInt32(bufferCapacity) && readResult(length))
        available = true
        withUnsafeMutableBytes(of: &ui) { publish(in: $0) }
        return
    }
    guard result == 0, length <= UInt32(bufferCapacity) else {
        update(false)
        return
    }
    if finished == .write {
        // Read the canonical state after accepted, stale or ambiguous writes.
        // Never issue another write from a completion callback.
        request = .read
        if !submitRead() { request = .none; update(false) }
        return
    }
    update(readResult(length))
}

private func readResult(_ length: UInt32) -> Bool {
    withUnsafeBytes(of: &capability) { buffer in
        var reader = TaskWireReader(UnsafeRawBufferPointer(start: buffer.baseAddress!, count: Int(length)))
        guard reader.consume(#"{"abi":1,"capability":"storage.keyValue.v1","operation":"get","outcome":{"#) else { return false }
        guard reader.consume(#""kind":"success","value":{"found":true,"valueBase64":""#),
              let value = reader.stateValue(),
              reader.consume(#""}},"schemaHash":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"}"#),
              reader.atEnd else { return false }
        storedRevision = value.revision
        flags = value.flags
        return true
    }
}

private func submitRead() -> Bool {
    let arguments: StaticString = #"{"key":"selected-draft","namespace":"fieldlog-task-v1"}"#
    return storageGet(arguments.utf8Start, UInt32(arguments.utf8CodeUnitCount), &token) == 0
}

private func submitWrite() -> Bool {
    withUnsafeMutableBytes(of: &capability) { buffer in
        var writer = TaskWireWriter(buffer)
        writer.append(#"{"key":"selected-draft","namespace":"fieldlog-task-v1","valueBase64":""#)
        writer.appendState(revision: storedRevision, flags: flags & 8 == 0 ? 1 : 2)
        writer.append(#""}"#)
        return storagePut(buffer.baseAddress!, UInt32(writer.count), &token) == 0
    }
}

private func update(_ ready: Bool) {
    precondition(revision < .max)
    available = ready
    revision += 1
    withUnsafeMutableBytes(of: &ui) { publish(in: $0) }
}

private func publish(in buffer: UnsafeMutableRawBufferPointer) {
    var output = TaskWireWriter(UnsafeMutableRawBufferPointer(start: buffer.baseAddress! + documentOffset, count: 2048))
    output.append(#"{"schemaVersion":1,"revision":"#)
    output.append(revision)
    output.append(#","root":{"id":"fieldlog-draft","kind":"vStack","properties":{},"actions":[],"children":["#)
    output.append(#"{"id":"validation","kind":"text","properties":{"text":""#)
    #if BASELINE
    let titlePresent = flags & 1 != 0
    #else
    let titlePresent = flags & 2 != 0
    #endif
    if !available {
        output.append("Saved draft unavailable")
    } else {
        #if !OPTIONAL_FIELD
        if revision == 1 { output.append("Saved draft loaded") }
        else { output.append(titlePresent ? "Ready to save entry" : "Entry title is required") }
        #else
        output.append(titlePresent ? "Ready to save entry" : "Entry title is required")
        #endif
    }
    output.append(#""},"children":[],"actions":[]},{"id":"photo","kind":"text","properties":{"text":""#)
    output.append(available && flags & 4 != 0 ? "JPEG linked" : "No photo shown")
    output.append(#""},"children":[],"actions":[]},"#)
    #if OPTIONAL_FIELD
    output.append(#"{"id":"follow-up","kind":"text","properties":{"text":""#)
    if flags & 8 != 0 { output.append("Follow-up required") }
    else if flags & 16 != 0 { output.append("Follow-up not required") }
    else { output.append("Follow-up unset") }
    output.append(#""},"children":[],"actions":[]},"#)
    #endif
    output.append(#"{"id":"toggle","kind":"button","properties":{"label":""#)
    #if OPTIONAL_FIELD
    if !available { output.append("Reload draft") }
    else { output.append(flags & 8 != 0 ? "Clear follow-up requirement" : "Mark follow-up required") }
    #else
    output.append("Check saved draft")
    #endif
    output.append(#""},"children":[],"actions":[{"id":""#)
    output.append(actionID)
    output.append(#"","event":"activate"}]}]}}"#)
    let base = UInt32(UInt(bitPattern: buffer.baseAddress!))
    buffer.storeBytes(of: base + UInt32(documentOffset), toByteOffset: 8, as: UInt32.self)
    buffer.storeBytes(of: UInt32(output.count), toByteOffset: 12, as: UInt32.self)
}
