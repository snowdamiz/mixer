@resultBuilder
private enum FixedSlotMenuBuilder {
    static func buildBlock(_ child: UInt8) -> UInt8 { child }

    static func buildBlock(_ marker: UInt8, _ first: UInt8, _ second: UInt8, _ third: UInt8) -> UInt32 {
        UInt32(marker) | (UInt32(first) << 8) | (UInt32(second) << 16) | (UInt32(third) << 24)
    }

    static func buildEither(first: UInt8) -> UInt8 { first }
    static func buildEither(second: UInt8) -> UInt8 { second }
    static func buildOptional(_ child: UInt8?) -> UInt8 { child ?? 0 }
}

struct FixedSlotResultBuilderPreview {
    static let inputSize = 3
    static let outputSize = 4

    @FixedSlotMenuBuilder
    private static func menu(priority: Bool, first: UInt8, count: UInt8) -> UInt32 {
        if priority {
            UInt8(0x21) // !
        } else {
            UInt8(0x2e) // .
        }
        if count > 0 {
            0x30 + first
        }
        if count > 1 {
            0x31 + first
        }
        if count > 2 {
            0x32 + first
        }
    }

    static func render(_ input: UnsafeRawBufferPointer, into output: UnsafeMutableRawBufferPointer) -> Bool {
        guard input.count == inputSize else { return false }
        let priority = input[0]
        let first = input[1]
        let count = input[2]
        guard priority <= 1, count <= 3, first <= 9, first + count <= 10 else { return false }

        let frame = menu(priority: priority == 1, first: first, count: count)
        output.storeBytes(of: frame.littleEndian, as: UInt32.self)
        return true
    }
}
