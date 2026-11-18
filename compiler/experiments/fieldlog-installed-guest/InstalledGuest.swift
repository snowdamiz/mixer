private let headerSize = 32
private let eventCapacity = 4096
private let documentCapacity = 2048
private let documentStart = headerSize + eventCapacity
#if REQUIRE_REVIEW
private let requireReview = true
#else
private let requireReview = false
#endif

private nonisolated(unsafe) var memory = InlineArray<6176, UInt8>(repeating: 0)
private nonisolated(unsafe) var task = TaskCompletion()

@_cdecl("mixer_guest_ui_start_v1")
public func guestStart() -> UInt32 {
    withUnsafeMutableBytes(of: &memory) { buffer in
        let base = buffer.baseAddress!
        let offset = UInt32(UInt(bitPattern: base))
        write(827_672_909, at: 0, in: buffer)
        write(UInt32(headerSize), at: 4, in: buffer)
        write(offset + UInt32(documentStart), at: 8, in: buffer)
        write(offset + UInt32(headerSize), at: 16, in: buffer)
        write(UInt32(eventCapacity), at: 20, in: buffer)
        publish(in: buffer)
        return offset
    }
}

@_cdecl("mixer_guest_ui_event_v1")
public func guestEvent(_ length: UInt32) -> UInt32 {
    guard length > 0 && length <= UInt32(eventCapacity) else { return 1 }
    return withUnsafeMutableBytes(of: &memory) { buffer in
        let event = UnsafeRawBufferPointer(start: buffer.baseAddress! + headerSize, count: Int(length))
        guard task.accepts(event), task.activate(requireReview: requireReview) else { return 1 }
        publish(in: buffer)
        return 0
    }
}

@_cdecl("mixer_guest_capability_ready_v1")
public func guestReady() {}

private func publish(in buffer: UnsafeMutableRawBufferPointer) {
    let output = UnsafeMutableRawBufferPointer(start: buffer.baseAddress! + documentStart, count: documentCapacity)
    write(UInt32(task.render(into: output)), at: 12, in: buffer)
}

private func write(_ word: UInt32, at offset: Int, in buffer: UnsafeMutableRawBufferPointer) {
    buffer.storeBytes(of: word.littleEndian, toByteOffset: offset, as: UInt32.self)
}
