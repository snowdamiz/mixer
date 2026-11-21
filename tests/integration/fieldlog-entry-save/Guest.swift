@_extern(c, "fieldlog_storage_get")
func storageGet(_ bytes: UnsafeRawPointer, _ count: UInt32, _ token: UnsafeMutablePointer<UInt64>) -> UInt32
#if FIELDLOG_DURABLE_COMMIT_REPLAY
@_extern(c, "fieldlog_storage_put")
func storagePut(_ bytes: UnsafeRawPointer, _ count: UInt32, _ token: UnsafeMutablePointer<UInt64>) -> UInt32
#endif
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
#if FIELDLOG_DURABLE_COMMIT_REPLAY
private nonisolated(unsafe) var firstWrite: UInt64 = 0
#if FIELDLOG_COMMIT_MULTIPLE_PUTS
private nonisolated(unsafe) var replayWrite: UInt64 = 0
private nonisolated(unsafe) var otherWrite: UInt64 = 0
private nonisolated(unsafe) var committed = false
#endif
#endif

@_cdecl("mixer_guest_ui_start_v1")
public func guestStart() -> UInt32 {
    let offset = withUnsafeMutableBytes(of: &ui) { bytes in
        let base = UInt32(UInt(bitPattern: bytes.baseAddress!))
        bytes.storeBytes(of: UInt32(0x3155494d), as: UInt32.self)
        bytes.storeBytes(of: UInt32(headerSize), toByteOffset: 4, as: UInt32.self)
        bytes.storeBytes(of: base + UInt32(headerSize), toByteOffset: 16, as: UInt32.self)
        bytes.storeBytes(of: UInt32(eventCapacity), toByteOffset: 20, as: UInt32.self)
        return base
    }
    #if FIELDLOG_DURABLE_COMMIT_REPLAY
    available = true
    publish("Ready to commit")
    #endif
    return offset
}

#if !FIELDLOG_DURABLE_COMMIT_REPLAY
@_cdecl("mixer_guest_ui_hydrate_v1")
public func hydrate() -> UInt32 {
    guard !pending else { return 1 }
    return readFacts()
}
#endif

@_cdecl("mixer_guest_ui_event_v1")
public func guestEvent(_ length: UInt32) -> UInt32 {
    guard available, !pending, length > 0, length <= UInt32(eventCapacity),
          sequence < .max, revision < .max else { return 1 }
    let matches = withUnsafeBytes(of: &ui) { bytes in
        var reader = TaskWireReader(UnsafeRawBufferPointer(start: bytes.baseAddress! + headerSize, count: Int(length)))
        #if FIELDLOG_DURABLE_COMMIT_REPLAY
        let prefix: StaticString = #"{"actionID":"entry.commit","event":"activate","nodeID":"toggle","revision":"#
        #else
        let prefix: StaticString = #"{"actionID":"entry.check","event":"activate","nodeID":"toggle","revision":"#
        #endif
        return reader.consume(prefix)
            && reader.consume(revision) && reader.consume(#","schemaVersion":1,"sequence":"#)
            && reader.consume(sequence) && reader.consume(#","value":null}"#) && reader.atEnd
    }
    guard matches else { return 1 }
    sequence += 1
    return readFacts()
}

@_cdecl("mixer_guest_capability_ready_v1")
public func guestReady() {
    #if FIELDLOG_DURABLE_COMMIT_REPLAY
    advanceCommit()
    #else
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
    #endif
}

#if FIELDLOG_DURABLE_COMMIT_REPLAY
private func advanceCommit() {
    if pending {
        #if FIELDLOG_COMMIT_WITHOUT_POLL
        // Attempt puts in the first ready turn without consuming facts.
        if firstWrite == 0 { enqueueCommit(); return }
        #endif
        var length: UInt32 = 0
        let status = withUnsafeMutableBytes(of: &response) { bytes in
            poll(token, bytes.baseAddress!, UInt32(bytes.count), &length)
        }
        if status == 1 { return }
        pending = false
        #if !FIELDLOG_COMMIT_WITHOUT_POLL
        let decision = status == 0 ? decodeFacts(length)?.decision : nil
        if decision == .eligible { enqueueCommit() }
        else { finishCommit(decision?.message ?? "Selected draft unavailable.") }
        return
        #endif
    }
    if firstWrite != 0 {
        guard let result = putResult(firstWrite) else { return }
        firstWrite = 0
        #if FIELDLOG_COMMIT_MULTIPLE_PUTS
        committed = result == .committed
        #else
        finishCommit(result == .committed ? "Committed once" : "Commit refused")
        #endif
    }
    #if FIELDLOG_COMMIT_MULTIPLE_PUTS
    if replayWrite != 0 {
        guard let result = putResult(replayWrite) else { return }
        precondition(result == .permissionDenied)
        replayWrite = 0
    }
    if otherWrite != 0 {
        guard let result = putResult(otherWrite) else { return }
        precondition(result == .permissionDenied)
        otherWrite = 0
        finishCommit(committed ? "Committed once" : "Commit refused")
    }
    #endif
}

private func enqueueCommit() {
    let request: StaticString = #"{"key":"entry-commit-v1","namespace":"fieldlog-task-v1","valueBase64":"AQ=="}"#
    precondition(storagePut(request.utf8Start, UInt32(request.utf8CodeUnitCount), &firstWrite) == 0)
    #if FIELDLOG_COMMIT_MULTIPLE_PUTS
    precondition(storagePut(request.utf8Start, UInt32(request.utf8CodeUnitCount), &replayWrite) == 0)
    let other: StaticString = #"{"key":"entry-commit-v1","namespace":"fieldlog-task-v1","valueBase64":"Ag=="}"#
    precondition(storagePut(other.utf8Start, UInt32(other.utf8CodeUnitCount), &otherWrite) == 0)
    #endif
}

private enum PutResult: Equatable {
    case committed, refused, permissionDenied
}

private func putResult(_ token: UInt64) -> PutResult? {
    var length: UInt32 = 0
    let status = withUnsafeMutableBytes(of: &response) { bytes in
        poll(token, bytes.baseAddress!, UInt32(bytes.count), &length)
    }
    if status == 1 { return nil }
    precondition(status == 0 && length <= 512)
    return withUnsafeBytes(of: &response) { bytes in
        let response = UnsafeRawBufferPointer(rebasing: bytes.prefix(Int(length)))
        var reader = TaskWireReader(response)
        let prefix: StaticString = #"{"abi":1,"capability":"storage.keyValue.v1","operation":"put","outcome":"#
        let suffix: StaticString = #","schemaHash":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"}"#
        precondition(reader.consume(prefix))
        let result: PutResult
        if reader.consume(#"{"kind":"success","value":{"committed":true}}"#) {
            result = .committed
        } else if reader.consume(#"{"kind":"success","value":{"committed":false}}"#) {
            result = .refused
        } else {
            precondition(reader.consume(#"{"code":""#))
            if reader.consume("permissionDenied") {
                result = .permissionDenied
            } else {
                precondition(reader.consume("ioFailure") || reader.consume("unavailable")
                    || reader.consume("cancelled") || reader.consume("deadlineExceeded")
                    || reader.consume("quotaExceeded"))
                result = .refused
            }
            precondition(reader.consume(#"","kind":"failure"}"#))
        }
        precondition(reader.consume(suffix) && reader.atEnd)
        return result
    }
}

private func finishCommit(_ message: StaticString) {
    revision += 1
    available = false
    publish(message)
}
#endif

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
            #if FIELDLOG_DURABLE_COMMIT_REPLAY
            output.append(#",{"id":"toggle","kind":"button","properties":{"label":"Commit"},"children":[],"actions":[{"id":"entry.commit","event":"activate"}]}"#)
            #else
            output.append(#",{"id":"toggle","kind":"button","properties":{"label":"Check entry"},"children":[],"actions":[{"id":"entry.check","event":"activate"}]}"#)
            #endif
        }
        output.append("]}}")
        let base = UInt32(UInt(bitPattern: bytes.baseAddress!))
        bytes.storeBytes(of: base + UInt32(documentOffset), toByteOffset: 8, as: UInt32.self)
        bytes.storeBytes(of: UInt32(output.count), toByteOffset: 12, as: UInt32.self)
    }
}
