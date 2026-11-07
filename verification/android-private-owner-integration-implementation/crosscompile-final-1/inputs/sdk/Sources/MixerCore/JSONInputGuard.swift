import Foundation

/// Resource bounds for one UTF-8 JSON value. This guard does not rewrite, normalize,
/// canonicalize, or authorize the value; the original bytes remain the decoder input.
public struct JSONInputLimits: Equatable, Sendable {
    public let maximumBytes: Int
    public let maximumDepth: Int
    public let maximumValues: Int
    public let maximumStringBytes: Int
    public let maximumKeyBytes: Int

    public init(maximumBytes: Int = 1_048_576, maximumDepth: Int = 256,
                maximumValues: Int = 200_000, maximumStringBytes: Int = 262_144,
                maximumKeyBytes: Int = 4096) {
        self.maximumBytes = maximumBytes; self.maximumDepth = maximumDepth
        self.maximumValues = maximumValues; self.maximumStringBytes = maximumStringBytes
        self.maximumKeyBytes = maximumKeyBytes
    }

    var isValid: Bool {
        (1...16_777_216).contains(maximumBytes) && (1...384).contains(maximumDepth)
            && (1...3_000_000).contains(maximumValues) && (1...1_048_576).contains(maximumStringBytes)
            && (1...65_536).contains(maximumKeyBytes)
    }
}

public struct JSONInputError: Error, Equatable, Sendable {
    public enum Reason: String, Sendable {
        case invalidLimits, byteLimit, depthLimit, valueLimit, stringLimit, numberLimit
        case invalidUTF8, syntax, duplicateKey
    }
    public let reason: Reason
    public let offset: Int
    public let key: String?
}

public enum JSONInputGuard {
    /// Reject ambiguous object members, malformed JSON/Unicode, and excessive resources
    /// before Foundation can collapse duplicate keys. Key equality compares decoded UTF-8
    /// bytes, including surrogate pairs and escapes, with no Unicode normalization.
    public static func validate(_ data: Data, limits: JSONInputLimits = JSONInputLimits()) throws {
        guard limits.isValid else { throw JSONInputError(reason: .invalidLimits, offset: 0, key: nil) }
        guard data.count <= limits.maximumBytes else { throw JSONInputError(reason: .byteLimit, offset: 0, key: nil) }
        guard String(data: data, encoding: .utf8) != nil else { throw JSONInputError(reason: .invalidUTF8, offset: 0, key: nil) }
        var scanner = JSONScanner(bytes: Array(data), limits: limits)
        try scanner.value(depth: 0)
        scanner.whitespace()
        guard scanner.index == scanner.bytes.count else { throw scanner.error(.syntax) }
    }
}

private struct JSONScanner {
    let bytes: [UInt8]
    let limits: JSONInputLimits
    var index = 0
    var values = 0

    func error(_ reason: JSONInputError.Reason, at offset: Int? = nil, key: String? = nil) -> JSONInputError {
        JSONInputError(reason: reason, offset: offset ?? index, key: key)
    }

    mutating func whitespace() {
        while index < bytes.count {
            switch bytes[index] {
            case 0x20, 0x09, 0x0a, 0x0d: index += 1
            default: return
            }
        }
    }

    mutating func consume(_ byte: UInt8) -> Bool {
        guard index < bytes.count, bytes[index] == byte else { return false }
        index += 1
        return true
    }

    mutating func expect(_ byte: UInt8) throws {
        guard consume(byte) else { throw error(.syntax) }
    }

    mutating func value(depth: Int) throws {
        values += 1
        guard values <= limits.maximumValues else { throw error(.valueLimit) }
        whitespace()
        guard index < bytes.count else { throw error(.syntax) }
        switch bytes[index] {
        case 0x7b:
            guard depth < limits.maximumDepth else { throw error(.depthLimit) }
            index += 1
            whitespace()
            if consume(0x7d) { return }
            var keys: Set<[UInt8]> = []
            while true {
                whitespace()
                let start = index
                let key = try string(isKey: true)
                guard keys.insert(key).inserted else {
                    throw error(.duplicateKey, at: start, key: String(decoding: key, as: UTF8.self))
                }
                whitespace(); try expect(0x3a)
                try value(depth: depth + 1)
                whitespace()
                if consume(0x7d) { return }
                try expect(0x2c)
            }
        case 0x5b:
            guard depth < limits.maximumDepth else { throw error(.depthLimit) }
            index += 1
            whitespace()
            if consume(0x5d) { return }
            while true {
                try value(depth: depth + 1)
                whitespace()
                if consume(0x5d) { return }
                try expect(0x2c)
            }
        case 0x22: _ = try string(isKey: false)
        case 0x74: try literal([0x74, 0x72, 0x75, 0x65])
        case 0x66: try literal([0x66, 0x61, 0x6c, 0x73, 0x65])
        case 0x6e: try literal([0x6e, 0x75, 0x6c, 0x6c])
        case 0x2d, 0x30...0x39: try number()
        default: throw error(.syntax)
        }
    }

    mutating func literal(_ token: [UInt8]) throws {
        for byte in token { try expect(byte) }
    }

    mutating func number() throws {
        let start = index
        _ = consume(0x2d)
        if !consume(0x30) {
            guard index < bytes.count, (0x31...0x39).contains(bytes[index]) else { throw error(.syntax) }
            index += 1
            while index < bytes.count, (0x30...0x39).contains(bytes[index]) { index += 1 }
        }
        if consume(0x2e) {
            let first = index
            while index < bytes.count, (0x30...0x39).contains(bytes[index]) { index += 1 }
            guard index > first else { throw error(.syntax) }
        }
        if consume(0x65) || consume(0x45) {
            if !consume(0x2b) { _ = consume(0x2d) }
            let first = index
            while index < bytes.count, (0x30...0x39).contains(bytes[index]) { index += 1 }
            guard index > first else { throw error(.syntax) }
        }
        guard index - start <= 256 else { throw error(.numberLimit, at: start) }
    }

    mutating func hexQuad() throws -> UInt32 {
        var value: UInt32 = 0
        for _ in 0..<4 {
            guard index < bytes.count else { throw error(.syntax) }
            let digit: UInt32
            switch bytes[index] {
            case 0x30...0x39: digit = UInt32(bytes[index] - 0x30)
            case 0x41...0x46: digit = UInt32(bytes[index] - 0x41 + 10)
            case 0x61...0x66: digit = UInt32(bytes[index] - 0x61 + 10)
            default: throw error(.syntax)
            }
            index += 1
            value = value * 16 + digit
        }
        return value
    }

    mutating func string(isKey: Bool) throws -> [UInt8] {
        try expect(0x22)
        var decoded: [UInt8] = []
        var decodedBytes = 0
        let maximum = isKey ? limits.maximumKeyBytes : limits.maximumStringBytes
        while index < bytes.count {
            let byte = bytes[index]
            index += 1
            if byte == 0x22 { return decoded }
            guard byte >= 0x20 else { throw error(.syntax, at: index - 1) }
            if byte != 0x5c {
                decodedBytes += 1
                guard decodedBytes <= maximum else { throw error(.stringLimit) }
                if isKey { decoded.append(byte) }
                continue
            }
            guard index < bytes.count else { throw error(.syntax) }
            let escaped = bytes[index]
            index += 1
            let scalar: UInt32
            switch escaped {
            case 0x22, 0x5c, 0x2f: scalar = UInt32(escaped)
            case 0x62: scalar = 0x08
            case 0x66: scalar = 0x0c
            case 0x6e: scalar = 0x0a
            case 0x72: scalar = 0x0d
            case 0x74: scalar = 0x09
            case 0x75:
                let first = try hexQuad()
                if (0xd800...0xdbff).contains(first) {
                    try expect(0x5c); try expect(0x75)
                    let second = try hexQuad()
                    guard (0xdc00...0xdfff).contains(second) else { throw error(.syntax) }
                    scalar = 0x10000 + (first - 0xd800) * 0x400 + second - 0xdc00
                } else {
                    guard !(0xdc00...0xdfff).contains(first) else { throw error(.syntax) }
                    scalar = first
                }
            default: throw error(.syntax, at: index - 1)
            }
            // All branches above produce valid Unicode scalar values.
            let encoded = String(Unicode.Scalar(scalar)!).utf8
            decodedBytes += encoded.count
            guard decodedBytes <= maximum else { throw error(.stringLimit) }
            if isKey { decoded.append(contentsOf: encoded) }
        }
        throw error(.syntax)
    }
}
