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
private nonisolated(unsafe) var screen: Screen = .unavailable
private nonisolated(unsafe) var revision: UInt64 = 1
private nonisolated(unsafe) var sequence: UInt64 = 1
private nonisolated(unsafe) var storedRevision: UInt64 = 0
private nonisolated(unsafe) var completed = false
private enum Screen { case task, review, unavailable }
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
    #if NO_HYDRATION_READ
    return 0
    #else
    guard request == .none else { return 1 }
    request = .hydration
    return submitRead() ? 0 : 1
    #endif
}

@_cdecl("mixer_guest_ui_event_v1")
public func guestEvent(_ length: UInt32) -> UInt32 {
    guard length > 0, length <= UInt32(eventCapacity), sequence < .max else { return 1 }
    let matches = withUnsafeBytes(of: &ui) { buffer in
        var parser = TaskWireReader(UnsafeRawBufferPointer(start: buffer.baseAddress! + headerSize, count: Int(length)))
        return parser.consume(#"{"actionID":"task.action","event":"activate","nodeID":"toggle","revision":"#)
            && parser.consume(revision) && parser.consume(#","schemaVersion":1,"sequence":"#)
            && parser.consume(sequence) && parser.consume(#","value":null}"#) && parser.atEnd
    }
    guard matches else { return 1 }
    sequence += 1
    guard request == .none else { return 0 }
    switch screen {
    case .unavailable:
        request = .read
        guard submitRead() else { return 1 }
    case .task:
        #if REQUIRE_REVIEW
        if !completed {
            update(.review)
            return 0
        }
        #endif
        fallthrough
    case .review:
        request = .write
        guard submitWrite() else { return 1 }
    }
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
        screen = .task
        withUnsafeMutableBytes(of: &ui) { publish(in: $0) }
        return
    }
    guard result == 0, length <= UInt32(bufferCapacity) else {
        update(.unavailable)
        return
    }
    if finished == .write {
        // Read the canonical state after accepted, stale or ambiguous writes.
        // Never issue another write from a completion callback.
        request = .read
        if !submitRead() { request = .none; update(.unavailable) }
        return
    }
    update(readResult(length) ? .task : .unavailable)
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
        completed = value.completed
        return true
    }
}

private func submitRead() -> Bool {
    let arguments: StaticString = #"{"key":"selected-task","namespace":"fieldlog-task-v1"}"#
    return storageGet(arguments.utf8Start, UInt32(arguments.utf8CodeUnitCount), &token) == 0
}

private func submitWrite() -> Bool {
    withUnsafeMutableBytes(of: &capability) { buffer in
        var writer = TaskWireWriter(buffer)
        writer.append(#"{"key":"selected-task","namespace":"fieldlog-task-v1","valueBase64":""#)
        writer.appendState(revision: storedRevision, completed: !completed)
        writer.append(#""}"#)
        return storagePut(buffer.baseAddress!, UInt32(writer.count), &token) == 0
    }
}

private func update(_ next: Screen) {
    precondition(revision < .max)
    screen = next
    revision += 1
    withUnsafeMutableBytes(of: &ui) { publish(in: $0) }
}

private func publish(in buffer: UnsafeMutableRawBufferPointer) {
    var output = TaskWireWriter(UnsafeMutableRawBufferPointer(start: buffer.baseAddress! + documentOffset, count: 2048))
    output.append(#"{"schemaVersion":1,"revision":"#)
    output.append(revision)
    output.append(#","root":{"id":"fieldlog-task","kind":"vStack","properties":{},"actions":[],"children":[{"id":"status","kind":"text","properties":{"text":""#)
    switch screen {
    case .task: output.append(completed ? "Completed" : "Open")
    case .review: output.append("Review required")
    case .unavailable: output.append("Saved task unavailable")
    }
    output.append(#""},"children":[],"actions":[]},{"id":"toggle","kind":"button","properties":{"label":""#)
    switch screen {
    case .unavailable: output.append("Retry saved task")
    case .task: output.append(completed ? "Reopen task" : "Complete task")
    case .review: output.append("Confirm completion")
    }
    output.append(#""},"children":[],"actions":[{"id":"task.action","event":"activate"}]}]}}"#)
    let base = UInt32(UInt(bitPattern: buffer.baseAddress!))
    buffer.storeBytes(of: base + UInt32(documentOffset), toByteOffset: 8, as: UInt32.self)
    buffer.storeBytes(of: UInt32(output.count), toByteOffset: 12, as: UInt32.self)
}
