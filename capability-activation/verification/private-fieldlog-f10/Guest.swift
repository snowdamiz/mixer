@_extern(c, "fieldlog_get")
private func storageGet(_ arguments: UnsafeRawPointer, _ length: UInt32,
                        _ token: UnsafeMutablePointer<UInt64>) -> Int32
@_extern(c, "fieldlog_poll")
private func storagePoll(_ token: UInt64, _ response: UnsafeMutableRawPointer, _ capacity: UInt32,
                         _ length: UnsafeMutablePointer<UInt32>) -> Int32

private let eventOffset = 32
private let eventCapacity = 1_048_576
private let documentOffset = 1_048_608
private nonisolated(unsafe) var presentation = InlineArray<1_081_376, UInt8>(repeating: 0)
private nonisolated(unsafe) var reply = InlineArray<8_448, UInt8>(repeating: 0)
private nonisolated(unsafe) var pageBytes = InlineArray<5_562, UInt8>(repeating: 0)
private nonisolated(unsafe) var pageLength = 0
private nonisolated(unsafe) var token: UInt64 = 0
private nonisolated(unsafe) var revision: UInt64 = 1
private nonisolated(unsafe) var kicked = false
private nonisolated(unsafe) var navigation = QueueNavigation()

@_cdecl("mixer_guest_ui_start_v3")
public func start() -> UInt32 {
    withUnsafeMutableBytes(of: &presentation) { buffer in
        let offset = address(buffer.baseAddress!)
        write(0x3349554d, at: 0, in: buffer)
        write(32, at: 4, in: buffer)
        write(offset + UInt32(eventOffset), at: 16, in: buffer)
        write(UInt32(eventCapacity), at: 20, in: buffer)
        let output = UnsafeMutableRawBufferPointer(rebasing: buffer[documentOffset...])
        var document = QueueOutput(output)
        #if !F10_WRONG_DOCUMENT
        document.write(#"{"featureSchemaVersion":3,"document":"#)
        #endif
        document.write(#"{"schemaVersion":1,"revision":1,"root":{"id":"f10.loading","kind":"text","properties":{"text":"Loading pending changes…"},"actions":[],"children":[]}}"#)
        #if !F10_WRONG_DOCUMENT
        document.write("}")
        #endif
        write(address(output.baseAddress!), at: 8, in: buffer)
        write(UInt32(document.result), at: 12, in: buffer)
        return offset
    }
}

@_cdecl("mixer_guest_ui_event_v3")
public func event(_ length: UInt32) -> UInt32 {
    guard token == 0, revision == 2, pageLength >= 2, (1...UInt32(eventCapacity)).contains(length) else { return 1 }
    let isQueue = withUnsafeBytes(of: &presentation) { buffer in
        var event = QueueBytes(UnsafeRawBufferPointer(rebasing: buffer[eventOffset..<(eventOffset + Int(length))]))
        return event.expect(#"{"actionID":"workspace.queue","event":"activate","nodeID":"workspace.queue","revision":"#)
            && event.expectDecimal(revision)
            && event.expect(#","schemaVersion":3,"sequence":1,"value":null}"#)
            && event.atEnd
    }
    let total = withUnsafeBytes(of: &pageBytes) { Int($0[0]) + 256 * Int($0[1]) }
    guard isQueue, let page = QueuePage(index: 0, total: total), navigation.activate(.open, current: page) else { return 1 }
    revision += 1
    return publish() ? 0 : 1
}

@_cdecl("mixer_guest_ui_ready_v3")
public func ready() {
    if !kicked {
        kicked = true
        #if F10_WRONG_REQUEST
        let arguments: StaticString = #"{"key":"queue-1","namespace":"material_test"}"#
        #else
        let arguments: StaticString = #"{"key":"queue-0","namespace":"material_test"}"#
        #endif
        var next: UInt64 = 0
        let status = storageGet(arguments.utf8Start, UInt32(arguments.utf8CodeUnitCount), &next)
        precondition(status == 0 && next != 0)
        token = next
        return
    }
    precondition(token != 0 && revision == 1)
    var length: UInt32 = 0
    let status = withUnsafeMutableBytes(of: &reply) {
        storagePoll(token, $0.baseAddress!, UInt32($0.count), &length)
    }
    precondition(status == 0 && length <= 8_448)
    let decoded = withUnsafeBytes(of: &reply) { source in
        withUnsafeMutableBytes(of: &pageBytes) { target in
            decode(UnsafeRawBufferPointer(rebasing: source.prefix(Int(length))), into: target)
        }
    }
    precondition(decoded > 0)
    revision += 1
    pageLength = decoded
    token = 0
    precondition(publish())
}

private func publish() -> Bool {
    withUnsafeMutableBytes(of: &presentation) { buffer in
        let output = UnsafeMutableRawBufferPointer(rebasing: buffer[documentOffset...])
        var prefix = QueueOutput(output)
        prefix.write(#"{"featureSchemaVersion":3,"document":"#)
        let target = UnsafeMutableRawBufferPointer(rebasing: output[prefix.result..<(output.count - 1)])
        let count = withUnsafeBytes(of: &pageBytes) { bytes in
            let data = UnsafeRawBufferPointer(rebasing: bytes.prefix(pageLength))
            return navigation.render(revision: revision, pageIndex: 0, payload: data,
                                     into: target, historicalLayout: true)
        }
        guard count > 0 else { return false }
        output[prefix.result + count] = 125
        write(address(output.baseAddress!), at: 8, in: buffer)
        write(UInt32(prefix.result + count + 1), at: 12, in: buffer)
        return true
    }
}

private func address(_ pointer: UnsafeRawPointer) -> UInt32 { UInt32(UInt(bitPattern: pointer)) }

private func write(_ value: UInt32, at offset: Int, in buffer: UnsafeMutableRawBufferPointer) {
    buffer.storeBytes(of: value.littleEndian, toByteOffset: offset, as: UInt32.self)
}

extension QueueBytes {
    fileprivate mutating func expectDecimal(_ value: UInt64) -> Bool {
        var divisor: UInt64 = 1
        while value / divisor >= 10 { divisor &*= 10 }
        while divisor > 0 {
            guard byte() == 48 + UInt8(value / divisor % 10) else { return false }
            divisor /= 10
        }
        return true
    }
}

// Only the canonical successful result for the imported get may become a page.
private func decode(_ bytes: UnsafeRawBufferPointer, into target: UnsafeMutableRawBufferPointer) -> Int {
    var input = QueueBytes(bytes)
    guard input.expect(#"{"abi":1,"capability":"storage.keyValue.v1","operation":"get","outcome":{"kind":"success","value":{"found":true,"valueBase64":""#) else { return 0 }
    var output = QueueOutput(target)
    while let a = input.byte(), a != 34 {
        guard let first = digit(a), let b = input.byte(), let second = digit(b),
              let c = input.byte(), let d = input.byte() else { return 0 }
        output.append((first << 2) | (second >> 4))
        if c == 61 {
            guard d == 61, second & 15 == 0, input.byte() == 34 else { return 0 }
            break
        }
        guard let third = digit(c) else { return 0 }
        output.append((second << 4) | (third >> 2))
        if d == 61 {
            guard third & 3 == 0, input.byte() == 34 else { return 0 }
            break
        }
        guard let fourth = digit(d) else { return 0 }
        output.append((third << 6) | fourth)
    }
    guard input.expect(#"}},"schemaHash":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"}"#),
          input.atEnd else { return 0 }
    return output.result
}

private func digit(_ byte: UInt8) -> UInt8? {
    switch byte {
    case 65...90: byte - 65
    case 97...122: byte - 71
    case 48...57: byte + 4
    case 43: 62
    case 47: 63
    default: nil
    }
}
