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
