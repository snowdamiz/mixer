// A task measurement preview computes the total, change, scaled value, and
// normalized value. Preserve the result bits so signed zero stays observable.
enum FloatingPointPreview {
    static let inputSize = 24
    static let outputSize = 56

    static func render(_ input: UnsafeRawBufferPointer, into output: UnsafeMutableRawBufferPointer) -> Bool {
        guard input.count == inputSize else { return false }

        let measured = Float(bitPattern: UInt32(littleEndian: input.loadUnaligned(as: UInt32.self)))
        let reference = Float(bitPattern: UInt32(littleEndian: input.loadUnaligned(fromByteOffset: 4, as: UInt32.self)))
        let precise = Double(bitPattern: UInt64(littleEndian: input.loadUnaligned(fromByteOffset: 8, as: UInt64.self)))
        let preciseReference = Double(bitPattern: UInt64(littleEndian: input.loadUnaligned(fromByteOffset: 16, as: UInt64.self)))

        // Keep the operations shared between the native and Embedded Swift builds.
        func write<T: BinaryFloatingPoint, Word: FixedWidthInteger>(
            _ value: T, _ reference: T, at offset: Int, flagsAt flagsOffset: Int, bits: (T) -> Word
        ) {
            let width = MemoryLayout<Word>.size
            output.storeBytes(of: bits(value + reference).littleEndian, toByteOffset: offset, as: Word.self)
            output.storeBytes(of: bits(value - reference).littleEndian, toByteOffset: offset + width, as: Word.self)
            output.storeBytes(of: bits(value * reference).littleEndian, toByteOffset: offset + 2 * width, as: Word.self)
            output.storeBytes(of: bits(value / reference).littleEndian, toByteOffset: offset + 3 * width, as: Word.self)
            let flags: UInt32 = (value < reference ? 1 : 0) | (value == 0 ? 2 : 0)
            output.storeBytes(of: flags.littleEndian, toByteOffset: flagsOffset, as: UInt32.self)
        }

        write(measured, reference, at: 0, flagsAt: 48) { $0.bitPattern }
        write(precise, preciseReference, at: 16, flagsAt: 52) { $0.bitPattern }
        return true
    }
}

#if FLOATING_POINT_GUEST
// Same fixed header and memory bounds as the installed TaskCompletion adapter.
// This probe exchanges binary measurements and result bits through the ABI.
private let eventStart = 32
private let eventCapacity = 4096
private let documentStart = eventStart + eventCapacity
private nonisolated(unsafe) var memory = InlineArray<6176, UInt8>(repeating: 0)

@_cdecl("mixer_guest_ui_start_v1")
public func guestStart() -> UInt32 {
    withUnsafeMutableBytes(of: &memory) { buffer in
        let base = UInt32(UInt(bitPattern: buffer.baseAddress!))
        buffer.storeBytes(of: UInt32(827_672_909), as: UInt32.self)
        buffer.storeBytes(of: UInt32(eventStart), toByteOffset: 4, as: UInt32.self)
        buffer.storeBytes(of: base + UInt32(documentStart), toByteOffset: 8, as: UInt32.self)
        buffer.storeBytes(of: UInt32(FloatingPointPreview.outputSize), toByteOffset: 12, as: UInt32.self)
        buffer.storeBytes(of: base + UInt32(eventStart), toByteOffset: 16, as: UInt32.self)
        buffer.storeBytes(of: UInt32(eventCapacity), toByteOffset: 20, as: UInt32.self)
        return base
    }
}

@_cdecl("mixer_guest_ui_event_v1")
public func guestEvent(_ length: UInt32) -> UInt32 {
    guard length == UInt32(FloatingPointPreview.inputSize) else { return 1 }
    return withUnsafeMutableBytes(of: &memory) { buffer in
        let input = UnsafeRawBufferPointer(rebasing: buffer[eventStart ..< eventStart + Int(length)])
        let output = UnsafeMutableRawBufferPointer(
            rebasing: buffer[documentStart ..< documentStart + FloatingPointPreview.outputSize])
        return FloatingPointPreview.render(input, into: output) ? 0 : 1
    }
}

@_cdecl("mixer_guest_capability_ready_v1")
public func guestReady() {}
#endif
