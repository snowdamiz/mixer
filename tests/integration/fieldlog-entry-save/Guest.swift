@_extern(c, "fieldlog_storage_get")
func storageGet(_ bytes: UnsafeRawPointer, _ count: UInt32, _ token: UnsafeMutablePointer<UInt64>) -> UInt32
@_extern(c, "fieldlog_poll")
func poll(_ token: UInt64, _ bytes: UnsafeMutableRawPointer, _ capacity: UInt32, _ length: UnsafeMutablePointer<UInt32>) -> UInt32

private let headerSize = 32
private let eventCapacity = 4096
private let documentOffset = 4128
private let documentCapacity = 1024
private nonisolated(unsafe) var ui = InlineArray<5152, UInt8>(repeating: 0)
private nonisolated(unsafe) var response = InlineArray<512, UInt8>(repeating: 0)
private nonisolated(unsafe) var token: UInt64 = 0
private nonisolated(unsafe) var pending = false
private nonisolated(unsafe) var available = false
private nonisolated(unsafe) var revision: UInt64 = 1
private nonisolated(unsafe) var sequence: UInt64 = 1

@_cdecl("mixer_guest_ui_start_v1")
public func guestStart() -> UInt32 {
    withUnsafeMutableBytes(of: &ui) { bytes in
        let base = UInt32(UInt(bitPattern: bytes.baseAddress!))
        bytes.storeBytes(of: UInt32(0x3155494d), as: UInt32.self)
        bytes.storeBytes(of: UInt32(headerSize), toByteOffset: 4, as: UInt32.self)
        bytes.storeBytes(of: base + UInt32(headerSize), toByteOffset: 16, as: UInt32.self)
        bytes.storeBytes(of: UInt32(eventCapacity), toByteOffset: 20, as: UInt32.self)
        return base
    }
}

@_cdecl("mixer_guest_ui_hydrate_v1")
public func hydrate() -> UInt32 {
    guard !pending else { return 1 }
    return readFacts()
}

@_cdecl("mixer_guest_ui_event_v1")
public func guestEvent(_ length: UInt32) -> UInt32 {
    guard available, !pending, length > 0, length <= UInt32(eventCapacity),
          sequence < .max, revision < .max else { return 1 }
    let matches = withUnsafeBytes(of: &ui) { bytes in
        var reader = TaskWireReader(UnsafeRawBufferPointer(start: bytes.baseAddress! + headerSize, count: Int(length)))
        return reader.consume(#"{"actionID":"entry.check","event":"activate","nodeID":"toggle","revision":"#)
            && reader.consume(revision) && reader.consume(#","schemaVersion":1,"sequence":"#)
            && reader.consume(sequence) && reader.consume(#","value":null}"#) && reader.atEnd
    }
    guard matches else { return 1 }
    sequence += 1
    return readFacts()
}

@_cdecl("mixer_guest_capability_ready_v1")
public func guestReady() {
    guard pending else { return }
    var length: UInt32 = 0
    let status = withUnsafeMutableBytes(of: &response) { bytes in
        poll(token, bytes.baseAddress!, UInt32(bytes.count), &length)
    }
    if status == 1 { return }
    pending = false
    let facts = status == 0 ? decodeFacts(length) : nil
    if sequence == 1 {
        precondition(facts != nil)
        available = true
        publish("Saved draft loaded")
    } else {
        revision += 1
        available = facts != nil
        publish(facts?.decision.message ?? "Selected draft unavailable.")
    }
}

private func readFacts() -> UInt32 {
    let request: StaticString = #"{"key":"entry-save-decision-v1","namespace":"fieldlog-task-v1"}"#
    let status = storageGet(request.utf8Start, UInt32(request.utf8CodeUnitCount), &token)
    pending = status == 0
    return pending ? 0 : 1
}

private func decodeFacts(_ length: UInt32) -> EntrySaveDecision.Facts? {
    withUnsafeBytes(of: &response) { bytes in
        guard length <= bytes.count else { return nil }
        var reader = TaskWireReader(UnsafeRawBufferPointer(rebasing: bytes.prefix(Int(length))))
        guard reader.consume(#"{"abi":1,"capability":"storage.keyValue.v1","operation":"get","outcome":{"kind":"success","value":{"found":true,"valueBase64":""#),
              let wire = reader.stateValue(),
              reader.consume(#""}},"schemaHash":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"}"#),
              reader.atEnd else { return nil }
        return .init(commitCounts: wire.revision, flags: wire.flags)
    }
}

private func publish(_ message: StaticString) {
    withUnsafeMutableBytes(of: &ui) { bytes in
        var output = TaskWireWriter(UnsafeMutableRawBufferPointer(start: bytes.baseAddress! + documentOffset, count: documentCapacity))
        output.append(#"{"schemaVersion":1,"revision":"#)
        output.append(revision)
        output.append(#","root":{"id":"fieldlog-entry-save","kind":"vStack","properties":{},"actions":[],"children":["#)
        output.append(#"{"id":"decision","kind":"text","properties":{"text":""#)
        output.append(message)
        output.append(#""},"children":[],"actions":[]}"#)
        if available {
            output.append(#",{"id":"toggle","kind":"button","properties":{"label":"Check entry"},"children":[],"actions":[{"id":"entry.check","event":"activate"}]}"#)
        }
        output.append("]}}")
        let base = UInt32(UInt(bitPattern: bytes.baseAddress!))
        bytes.storeBytes(of: base + UInt32(documentOffset), toByteOffset: 8, as: UInt32.self)
        bytes.storeBytes(of: UInt32(output.count), toByteOffset: 12, as: UInt32.self)
    }
}
