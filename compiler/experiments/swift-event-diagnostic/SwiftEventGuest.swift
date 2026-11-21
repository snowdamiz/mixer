private let accepted: StaticString = #"{"actionID":"validate","event":"activate","nodeID":"button","revision":1,"schemaVersion":1,"sequence":1,"value":null}"#
private let fault: StaticString = #"{"actionID":"validate","event":"activate","nodeID":"button","revision":1,"schemaVersion":1,"sequence":2,"value":null}"#
private let document: StaticString = #"{"schemaVersion":1,"revision":1,"root":{"id":"button","kind":"button","properties":{"label":"Validate"},"actions":[{"id":"validate","event":"activate"}],"children":[]}}"#
private let headerSize = 32
private let eventCapacity = 128
private let documentOffset = headerSize + eventCapacity
private nonisolated(unsafe) var memory = InlineArray<384, UInt8>(repeating: 0)

@_cdecl("mixer_guest_ui_start_v1")
public func start() -> UInt32 {
    withUnsafeMutableBytes(of: &memory) { bytes in
        let address = UInt32(UInt(bitPattern: bytes.baseAddress!))
        let words = (827_672_909 as UInt32, UInt32(headerSize), address + UInt32(documentOffset),
                     UInt32(document.utf8CodeUnitCount), address + UInt32(headerSize), UInt32(eventCapacity))
        bytes.storeBytes(of: words, as: type(of: words))
        for index in 0..<document.utf8CodeUnitCount {
            bytes[documentOffset + index] = document.utf8Start[index]
        }
        return address
    }
}

@_cdecl("mixer_guest_ui_event_v1")
public func event(_ length: UInt32) -> UInt32 {
    guard length <= eventCapacity else { return 1 }
    return withUnsafeBytes(of: &memory) { bytes in
        let input = UnsafeRawBufferPointer(rebasing: bytes[headerSize..<(headerSize + Int(length))])
        let rejected = matches(input, fault)
#if ALTERNATE_LINE
        precondition(!rejected) // alternate diagnostic
#else
        precondition(!rejected) // expected diagnostic
#endif
        return matches(input, accepted) ? 0 : 1
    }
}

@_cdecl("mixer_guest_capability_ready_v1")
public func ready() {}

private func matches(_ bytes: UnsafeRawBufferPointer, _ expected: StaticString) -> Bool {
    guard bytes.count == expected.utf8CodeUnitCount else { return false }
    for index in bytes.indices where bytes[index] != expected.utf8Start[index] { return false }
    return true
}
