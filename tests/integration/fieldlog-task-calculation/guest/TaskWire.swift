private let alphabet: StaticString = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
let uuidLength = 36
let titleLimit = 256
let rowCount = 3
let payloadCapacity = 21 + rowCount * (uuidLength + 1 + titleLimit + 1)

struct TaskRow {
    var id = 0..<0
    var title = 0..<0
}

struct TaskWireReader {
    private let bytes: UnsafeRawBufferPointer
    private var offset = 0
    var atEnd: Bool { offset == bytes.count }

    init(_ bytes: UnsafeRawBufferPointer) { self.bytes = bytes }

    mutating func consume(_ text: StaticString) -> Bool {
        consume(UnsafeRawBufferPointer(start: text.utf8Start, count: text.utf8CodeUnitCount))
    }

    mutating func consume(_ value: UnsafeRawBufferPointer) -> Bool {
        guard value.count <= bytes.count - offset else { return false }
        for index in 0..<value.count where bytes[offset + index] != value[index] {
            return false
        }
        offset += value.count
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

    mutating func decodeBase64(into output: UnsafeMutableRawBufferPointer) -> Int? {
        var count = 0
        while !atEnd && bytes[offset] != 34 {
            guard bytes.count - offset >= 4,
                  let a = base64Digit(bytes[offset]), let b = base64Digit(bytes[offset + 1]) else { return nil }
            let c = bytes[offset + 2]
            let d = bytes[offset + 3]
            offset += 4
            guard count < output.count else { return nil }
            output[count] = (a << 2) | (b >> 4)
            count += 1
            if c == 61 {
                guard d == 61, b & 15 == 0, !atEnd, bytes[offset] == 34 else { return nil }
                return count
            }
            guard let c = base64Digit(c), count < output.count else { return nil }
            output[count] = (b << 4) | (c >> 2)
            count += 1
            if d == 61 {
                guard c & 3 == 0, !atEnd, bytes[offset] == 34 else { return nil }
                return count
            }
            guard let d = base64Digit(d), count < output.count else { return nil }
            output[count] = (c << 6) | d
            count += 1
        }
        return count
    }

    mutating func revisionLine() -> UInt64? {
        guard !atEnd else { return nil }
        let start = offset
        var number: UInt64 = 0
        while !atEnd, (48...57).contains(bytes[offset]) {
            let digit = UInt64(bytes[offset] - 48)
            guard number <= (UInt64.max - digit) / 10 else { return nil }
            number = (number &* 10) &+ digit
            offset += 1
        }
        guard offset > start, offset - start == 1 || bytes[start] != 48, consume("\n") else {
            return nil
        }
        return number
    }

    mutating func row() -> TaskRow? {
        guard bytes.count - offset >= uuidLength else { return nil }
        let id = offset..<(offset + uuidLength)
        for index in 0..<uuidLength {
            let byte = bytes[offset + index]
            if index == 8 || index == 13 || index == 18 || index == 23 {
                guard byte == 45 else { return nil }
            } else {
                guard (48...57).contains(byte) || (65...70).contains(byte) else { return nil }
            }
        }
        offset = id.upperBound
        guard consume("\t") else { return nil }
        let start = offset
        while !atEnd && bytes[offset] != 10 {
            guard consumeTitleScalar(), offset - start <= titleLimit else { return nil }
        }
        let title = start..<offset
        guard consume("\n") else { return nil }
        return TaskRow(id: id, title: title)
    }

    private mutating func consumeTitleScalar() -> Bool {
        let lead = bytes[offset]
        if (32...126).contains(lead) {
            offset += 1
            return true
        }
        // C2 80–9F are controls. The first continuation bounds also reject
        // overlong sequences, UTF-16 surrogates, and values above U+10FFFF.
        let length: Int
        var low: UInt8 = 0x80
        var high: UInt8 = 0xbf
        switch lead {
        case 0xc2...0xdf:
            length = 2
            if lead == 0xc2 { low = 0xa0 }
        case 0xe0...0xef:
            length = 3
            if lead == 0xe0 { low = 0xa0 }
            if lead == 0xed { high = 0x9f }
        case 0xf0...0xf4:
            length = 4
            if lead == 0xf0 { low = 0x90 }
            if lead == 0xf4 { high = 0x8f }
        default: return false
        }
        guard bytes.count - offset >= length, (low...high).contains(bytes[offset + 1]) else { return false }
        for index in 2..<length where !(0x80...0xbf).contains(bytes[offset + index]) {
            return false
        }
        offset += length
        return true
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
        append(UnsafeRawBufferPointer(start: text.utf8Start, count: text.utf8CodeUnitCount))
    }

    mutating func append(_ value: UnsafeRawBufferPointer) {
        for byte in value { append(byte) }
    }

    mutating func appendEscapedTitle(_ value: UnsafeRawBufferPointer) {
        for byte in value {
            if byte == 34 || byte == 92 { append(UInt8(92)) }
            append(byte)
        }
    }

    mutating func append(_ number: UInt64) {
        var divisor = decimalDivisor(number)
        while divisor > 0 {
            append(decimalDigit(number, divisor))
            divisor /= 10
        }
    }

    mutating func appendBase64Decimal(_ number: UInt64) {
        var divisor = decimalDivisor(number)
        while divisor > 0 {
            let a = decimalDigit(number, divisor)
            divisor /= 10
            let b: UInt8 = divisor > 0 ? decimalDigit(number, divisor) : 0
            divisor /= 10
            let c: UInt8 = divisor > 0 ? decimalDigit(number, divisor) : 0
            divisor /= 10
            append(alphabet.utf8Start[Int(a >> 2)])
            append(alphabet.utf8Start[Int(((a & 3) << 4) | (b >> 4))])
            append(b == 0 ? 61 : alphabet.utf8Start[Int(((b & 15) << 2) | (c >> 6))])
            append(c == 0 ? 61 : alphabet.utf8Start[Int(c & 63)])
        }
    }
}

private func base64Digit(_ byte: UInt8) -> UInt8? {
    switch byte {
    case 65...90: return byte - 65
    case 97...122: return byte - 97 + 26
    case 48...57: return byte - 48 + 52
    case 43: return 62
    case 47: return 63
    default: return nil
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
