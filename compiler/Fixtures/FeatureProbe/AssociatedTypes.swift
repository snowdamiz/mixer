private protocol ReadingFormat {
    associatedtype Reading

    func extract(_ bits: UInt16) -> Reading
    func change(from baseline: Reading, to current: Reading) -> Int32
}

private struct SignedReading: ReadingFormat {
    func extract(_ bits: UInt16) -> Int16 { Int16(bitPattern: bits) }

    func change(from baseline: Int16, to current: Int16) -> Int32 {
        Int32(current) - Int32(baseline)
    }
}

private struct WrappingCounter: ReadingFormat {
    func extract(_ bits: UInt16) -> UInt16 { bits }

    func change(from baseline: UInt16, to current: UInt16) -> Int32 {
        Int32(current &- baseline)
    }
}

private func readingChange<Format: ReadingFormat>(
    _ format: Format, baseline: UInt16, current: UInt16
) -> Int32 {
    let first: Format.Reading = format.extract(baseline)
    let second: Format.Reading = format.extract(current)
    return format.change(from: first, to: second)
}

enum AssociatedTypesPreview {
    static let inputSize = 5
    static let outputSize = 4

    static func render(_ input: UnsafeRawBufferPointer, into output: UnsafeMutableRawBufferPointer) -> Bool {
        guard input.count == inputSize else { return false }
        let baseline = UInt16(littleEndian: input.loadUnaligned(fromByteOffset: 1, as: UInt16.self))
        let current = UInt16(littleEndian: input.loadUnaligned(fromByteOffset: 3, as: UInt16.self))

        let change: Int32
        switch input[0] {
        case 0:
            change = readingChange(SignedReading(), baseline: baseline, current: current)
        case 1:
            change = readingChange(WrappingCounter(), baseline: baseline, current: current)
        default:
            return false
        }
        output.storeBytes(of: change.littleEndian, as: Int32.self)
        return true
    }
}
