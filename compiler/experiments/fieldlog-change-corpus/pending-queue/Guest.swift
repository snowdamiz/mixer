@_extern(c, "fieldlog_get")
private func storageGet(_ arguments: UnsafeRawPointer, _ length: UInt32,
                        _ token: UnsafeMutablePointer<UInt64>) -> Int32
@_extern(c, "fieldlog_poll")
private func storagePoll(_ token: UInt64, _ response: UnsafeMutableRawPointer, _ capacity: UInt32,
                         _ length: UnsafeMutablePointer<UInt32>) -> Int32

private let eventOffset = 32
private let eventCapacity = 4_096
private let documentOffset = 4_128
private let documentCapacity = 32_768
private nonisolated(unsafe) var presentation = InlineArray<36_896, UInt8>(repeating: 0)
private nonisolated(unsafe) var reply = InlineArray<8_448, UInt8>(repeating: 0)
private nonisolated(unsafe) var pageBytes = InlineArray<5_562, UInt8>(repeating: 0)
private nonisolated(unsafe) var pageLength = 0
private nonisolated(unsafe) var displayedPage = 0
private nonisolated(unsafe) var token: UInt64 = 0
private nonisolated(unsafe) var revision: UInt64 = 1
private nonisolated(unsafe) var sequence: UInt64 = 1
private nonisolated(unsafe) var navigation = QueueNavigation()

@_cdecl("mixer_guest_ui_start_v1")
public func start() -> UInt32 {
    withUnsafeMutableBytes(of: &presentation) { buffer in
        let offset = address(buffer.baseAddress!)
        write(827_672_909, at: 0, in: buffer)
        write(32, at: 4, in: buffer)
        write(offset + UInt32(eventOffset), at: 16, in: buffer)
        write(UInt32(eventCapacity), at: 20, in: buffer)
        return offset
    }
}

@_cdecl("mixer_guest_ui_hydrate_v1")
public func hydrate() -> UInt32 { request(page: 0) ? 0 : 1 }

@_cdecl("mixer_guest_ui_event_v1")
public func event(_ length: UInt32) -> UInt32 {
    guard token == 0, (1...UInt32(eventCapacity)).contains(length) else { return 1 }
    let action: QueueAction? = withUnsafeBytes(of: &presentation) { buffer in
        let input = UnsafeRawBufferPointer(rebasing: buffer[eventOffset..<(eventOffset + Int(length))])
        for candidate in [QueueAction.open, .tasks, .entries, .previous, .next] {
            var event = QueueBytes(input)
            if event.expect(#"{"actionID":""#), event.expect(candidate.id),
               event.expect(#"","event":"activate","nodeID":""#), event.expect(candidate.id),
               event.expect(#"","revision":"#), event.expectDecimal(revision),
               event.expect(#","schemaVersion":1,"sequence":"#), event.expectDecimal(sequence),
               event.expect(#","value":null}"#), event.atEnd {
                return candidate
            }
        }
        return nil
    }
    guard let action, let current = pageHeader(), navigation.activate(action, current: current) else { return 1 }
    sequence += 1
    revision += 1
    if navigation.page != displayedPage && !request(page: navigation.page) { return 1 }
    return publish(loading: token != 0) ? 0 : 1
}

@_cdecl("mixer_guest_capability_ready_v1")
public func ready() {
    guard token != 0 else { return }
    var length: UInt32 = 0
    let status = withUnsafeMutableBytes(of: &reply) {
        storagePoll(token, $0.baseAddress!, UInt32($0.count), &length)
    }
    // A completion callback may only publish a page after the bound read succeeds.
    precondition(status == 0 && length <= 8_448)
    let decoded = withUnsafeBytes(of: &reply) { source in
        withUnsafeMutableBytes(of: &pageBytes) { target in
            decode(UnsafeRawBufferPointer(rebasing: source.prefix(Int(length))), into: target)
        }
    }
    precondition(decoded > 0)
    if pageLength > 0 { revision += 1 }
    pageLength = decoded
    displayedPage = navigation.page
    token = 0
    precondition(publish(loading: false))
}

private func request(page: Int) -> Bool {
    var bytes = InlineArray<128, UInt8>(repeating: 0)
    var next: UInt64 = 0
    let status = withUnsafeMutableBytes(of: &bytes) { buffer in
        var arguments = QueueOutput(buffer)
        arguments.write(#"{"key":"queue-"#)
        arguments.decimal(UInt64(page))
        arguments.write(#"","namespace":"material_test"}"#)
        return storageGet(buffer.baseAddress!, UInt32(arguments.result), &next)
    }
    guard status == 0, next != 0 else { return false }
    token = next
    return true
}

private func pageHeader() -> QueuePage? {
    guard pageLength >= 2 else { return nil }
    return withUnsafeBytes(of: &pageBytes) {
        QueuePage(index: displayedPage, total: Int($0[0]) + 256 * Int($0[1]))
    }
}

private func publish(loading: Bool) -> Bool {
    withUnsafeMutableBytes(of: &presentation) { buffer in
        let output = UnsafeMutableRawBufferPointer(rebasing: buffer[documentOffset..<(documentOffset + documentCapacity)])
        let count = withUnsafeBytes(of: &pageBytes) { bytes in
            let data = UnsafeRawBufferPointer(rebasing: bytes.prefix(pageLength))
            #if HISTORICAL_QUEUE_LAYOUT
            let historical = true
            #else
            let historical = false
            #endif
            return navigation.render(revision: revision, pageIndex: displayedPage, payload: data,
                                     into: output, loading: loading, historicalLayout: historical)
        }
        guard count > 0 else { return false }
        write(address(output.baseAddress!), at: 8, in: buffer)
        write(UInt32(count), at: 12, in: buffer)
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
