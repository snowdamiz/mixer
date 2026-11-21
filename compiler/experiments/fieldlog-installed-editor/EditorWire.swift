struct EditorWireInput {
    private let bytes: UnsafeRawBufferPointer
    private var cursor = 0

    init(_ bytes: UnsafeRawBufferPointer) { self.bytes = bytes }
    var atEnd: Bool { cursor == bytes.count }

    private mutating func next() -> UInt8? {
        guard cursor < bytes.count else { return nil }
        defer { cursor += 1 }
        return bytes[cursor]
    }

    mutating func expect(_ text: StaticString) -> Bool {
        for byte in UnsafeBufferPointer(start: text.utf8Start, count: text.utf8CodeUnitCount) {
            guard next() == byte else { return false }
        }
        return true
    }

    mutating func expectDecimal(_ value: UInt64) -> Bool {
        var place: UInt64 = 1
        while value / place >= 10 { place &*= 10 }
        while place != 0 {
            guard next() == 48 + UInt8(value / place % 10) else { return false }
            place /= 10
        }
        return true
    }

    mutating func title() -> [UInt8]? {
        guard next() == 34 else { return nil }
        var result: [UInt8] = []
        while let byte = next() {
            switch byte {
            case 34: return result
            case 92:
                switch next() {
                case 34: result.append(34)
                case 47: result.append(47)
                case 92: result.append(92)
                case 98: result.append(8)
                case 102: result.append(12)
                case 110: result.append(10)
                case 116: result.append(9)
                case 117:
                    // JSONEncoder emits non-ASCII UTF-8 directly. It uses the
                    // short escapes or four hex digits for C0 controls.
                    guard next() == 48, next() == 48, let high = hex(), let low = hex() else { return nil }
                    let control = high * 16 + low
                    guard (1..<32).contains(control), control != 13 else { return nil }
                    result.append(control)
                default: return nil
                }
            case 0..<32: return nil
            default: result.append(byte)
            }
        }
        return nil
    }

    private mutating func hex() -> UInt8? {
        guard let value = next() else { return nil }
        switch value {
        case 48...57: return value - 48
        case 65...70: return value - 55
        case 97...102: return value - 87
        default: return nil
        }
    }
}

struct EditorWireOutput {
    private let bytes: UnsafeMutableRawBufferPointer
    private(set) var count = 0

    init(_ bytes: UnsafeMutableRawBufferPointer) { self.bytes = bytes }

    private mutating func append(_ byte: UInt8) {
        precondition(count < bytes.count)
        bytes[count] = byte
        count += 1
    }

    mutating func write(_ text: StaticString) {
        for byte in UnsafeBufferPointer(start: text.utf8Start, count: text.utf8CodeUnitCount) { append(byte) }
    }

    mutating func decimal(_ value: UInt64) {
        var place: UInt64 = 1
        while value / place >= 10 { place &*= 10 }
        while place != 0 {
            append(48 + UInt8(value / place % 10))
            place /= 10
        }
    }

    mutating func boolean(_ value: Bool) { write(value ? "true" : "false") }

    mutating func title(_ title: UnsafeBufferPointer<UInt8>) {
        let hex: StaticString = "0123456789abcdef"
        append(34)
        for byte in title {
            switch byte {
            case 34, 92:
                append(92)
                append(byte)
            case 0..<32:
                write(#"\u00"#)
                append(hex.utf8Start[Int(byte >> 4)])
                append(hex.utf8Start[Int(byte & 15)])
            default: append(byte)
            }
        }
        append(34)
    }
}
