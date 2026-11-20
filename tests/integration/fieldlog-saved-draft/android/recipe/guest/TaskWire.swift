private let alphabet: StaticString = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

struct TaskWireReader {
    private let bytes: UnsafeRawBufferPointer
    private var offset = 0
    var atEnd: Bool { offset == bytes.count }

    init(_ bytes: UnsafeRawBufferPointer) { self.bytes = bytes }

    mutating func consume(_ text: StaticString) -> Bool {
        guard text.utf8CodeUnitCount <= bytes.count - offset else { return false }
        for index in 0..<text.utf8CodeUnitCount where bytes[offset + index] != text.utf8Start[index] {
            return false
        }
        offset += text.utf8CodeUnitCount
        return true
    }

    mutating func consume(_ number: UInt64) -> Bool {
        var divisor = decimalDivisor(number)
        while divisor > 0 {
            guard !atEnd, bytes[offset] == decimalDigit(number, divisor) else { return false }
            offset += 1
            divisor /= 10
        }
        return true
    }

    mutating func stateValue() -> (revision: UInt64, flags: UInt8)? {
        guard bytes.count - offset >= 12 else { return nil }
        var revision: UInt64 = 0
        var flags: UInt8 = 0
        for group in 0..<3 {
            var bits: UInt32 = 0
            for _ in 0..<4 {
                let byte = bytes[offset]
                guard let digit = base64Digit(byte) else { return nil }
                bits = (bits << 6) | digit
                offset += 1
            }
            if group < 2 { revision = (revision << 24) | UInt64(bits) }
            else {
                revision = (revision << 16) | UInt64(bits >> 8)
                flags = UInt8(truncatingIfNeeded: bits)
            }
        }
        return (revision, flags)
    }
}

struct TaskWireWriter {
    private let bytes: UnsafeMutableRawBufferPointer
    private(set) var count = 0

    init(_ bytes: UnsafeMutableRawBufferPointer) { self.bytes = bytes }

    private mutating func append(_ byte: UInt8) {
        precondition(count < bytes.count)
        bytes[count] = byte
        count += 1
    }

    mutating func append(_ text: StaticString) {
        let length = text.utf8CodeUnitCount
        precondition(length <= bytes.count - count)
        bytes.baseAddress!.advanced(by: count).copyMemory(from: text.utf8Start, byteCount: length)
        count += length
    }

    mutating func append(_ number: UInt64) {
        var divisor = decimalDivisor(number)
        while divisor > 0 {
            append(decimalDigit(number, divisor))
            divisor /= 10
        }
    }

    mutating func appendState(revision: UInt64, flags: UInt8) {
        appendBase64Group(UInt32((revision >> 40) & 0xffffff))
        appendBase64Group(UInt32((revision >> 16) & 0xffffff))
        appendBase64Group((UInt32(revision & 0xffff) << 8) | UInt32(flags))
    }

    private mutating func appendBase64Group(_ bits: UInt32) {
        for shift in [18, 12, 6, 0] { append(alphabet.utf8Start[Int((bits >> shift) & 63)]) }
    }
}

private func decimalDivisor(_ number: UInt64) -> UInt64 {
    var divisor: UInt64 = 1
    while number / divisor >= 10 { divisor &*= 10 }
    return divisor
}

private func decimalDigit(_ number: UInt64, _ divisor: UInt64) -> UInt8 {
    UInt8((number / divisor) % 10) + 48
}

private func base64Digit(_ byte: UInt8) -> UInt32? {
    switch byte {
    case 65...90: UInt32(byte - 65)
    case 97...122: UInt32(byte - 97) + 26
    case 48...57: UInt32(byte - 48) + 52
    case 43: 62
    case 47: 63
    default: nil
    }
}
