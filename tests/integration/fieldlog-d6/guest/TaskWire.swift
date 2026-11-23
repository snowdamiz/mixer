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

    mutating func stateValue() -> (revision: UInt64, completed: Bool)? {
        guard bytes.count - offset >= 12 else { return nil }
        var revision: UInt64 = 0
        var complete: UInt8 = 0
        for group in 0..<3 {
            var bits: UInt32 = 0
            for _ in 0..<4 {
                let byte = bytes[offset]
                guard let digit = (0..<64).first(where: { alphabet.utf8Start[$0] == byte }) else { return nil }
                bits = (bits << 6) | UInt32(digit)
                offset += 1
            }
            if group < 2 { revision = (revision << 24) | UInt64(bits) }
            else {
                revision = (revision << 16) | UInt64(bits >> 8)
                complete = UInt8(truncatingIfNeeded: bits)
            }
        }
        guard complete <= 1 else { return nil }
        return (revision, complete == 1)
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
        for index in 0..<text.utf8CodeUnitCount { append(text.utf8Start[index]) }
    }

    mutating func append(_ number: UInt64) {
        var divisor = decimalDivisor(number)
        while divisor > 0 {
            append(decimalDigit(number, divisor))
            divisor /= 10
        }
    }

    mutating func appendState(revision: UInt64, completed: Bool) {
        appendBase64Group(UInt32((revision >> 40) & 0xffffff))
        appendBase64Group(UInt32((revision >> 16) & 0xffffff))
        appendBase64Group((UInt32(revision & 0xffff) << 8) | (completed ? 1 : 0))
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
