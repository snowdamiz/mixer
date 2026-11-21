private let headerSize = 32
private let eventCapacity = 4096
private let documentCapacity = 2048
private let documentStart = headerSize + eventCapacity
private nonisolated(unsafe) var memory = InlineArray<6176, UInt8>(repeating: 0)
private nonisolated(unsafe) var checklist = Checklist()

@_cdecl("mixer_guest_ui_start_v1")
public func guestStart() -> UInt32 {
    withUnsafeMutableBytes(of: &memory) { buffer in
        let base = UInt32(UInt(bitPattern: buffer.baseAddress!))
        write(827_672_909, at: 0, in: buffer)
        write(UInt32(headerSize), at: 4, in: buffer)
        write(base + UInt32(documentStart), at: 8, in: buffer)
        write(base + UInt32(headerSize), at: 16, in: buffer)
        write(UInt32(eventCapacity), at: 20, in: buffer)
        publish(in: buffer)
        return base
    }
}

@_cdecl("mixer_guest_ui_event_v1")
public func guestEvent(_ length: UInt32) -> UInt32 {
    guard length == 2 else { return 1 }
    return withUnsafeMutableBytes(of: &memory) { buffer in
        let input = UnsafeRawBufferPointer(start: buffer.baseAddress! + headerSize, count: 2)
        guard checklist.accept(input) else { return 1 }
        publish(in: buffer)
        return 0
    }
}

@_cdecl("mixer_guest_capability_ready_v1")
public func guestReady() {}

private func publish(in buffer: UnsafeMutableRawBufferPointer) {
    let output = UnsafeMutableRawBufferPointer(start: buffer.baseAddress! + documentStart, count: documentCapacity)
    write(UInt32(checklist.frame(into: output)), at: 12, in: buffer)
}

private func write(_ word: UInt32, at offset: Int, in buffer: UnsafeMutableRawBufferPointer) {
    buffer.storeBytes(of: word.littleEndian, toByteOffset: offset, as: UInt32.self)
}
