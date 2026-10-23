import Foundation
import MixerUpdates

/// Original bounded parser for installed material. The tighter material limits
/// are independent of the update document scanner's larger resource ceilings.
enum MaterialJSON {
    static func decode(_ bytes: Data) throws -> CanonicalValue {
        guard bytes.count <= 65_536 else { throw materialError("size") }
        var parser = Parser(bytes: Array(bytes))
        let value = try parser.value(containers: 0)
        parser.whitespace()
        guard parser.index == parser.bytes.count, value.object != nil else { throw materialError("json") }
        return value
    }

    static func canonical(_ value: CanonicalValue) -> Data {
        var bytes: [UInt8] = []
        encode(value, into: &bytes)
        bytes.append(10)
        return Data(bytes)
    }

    private static func encode(_ value: CanonicalValue, into bytes: inout [UInt8]) {
        switch value {
        case let .uint(number): bytes += String(number).utf8
        case let .boolean(flag): bytes += (flag ? "true" : "false").utf8
        case let .text(text): string(text, into: &bytes)
        case let .array(values):
            bytes.append(91)
            for (index, value) in values.enumerated() {
                if index != 0 { bytes.append(44) }; encode(value, into: &bytes)
            }
            bytes.append(93)
        case let .object(fields):
            bytes.append(123)
            for (index, key) in fields.keys.sorted(by: { $0.utf8.lexicographicallyPrecedes($1.utf8) }).enumerated() {
                if index != 0 { bytes.append(44) }
                string(key, into: &bytes); bytes.append(58); encode(fields[key]!, into: &bytes)
            }
            bytes.append(125)
        }
    }

    private static func string(_ text: String, into bytes: inout [UInt8]) {
        let hex = Array("0123456789abcdef".utf8)
        func escaped(_ unit: UInt16, into bytes: inout [UInt8]) {
            bytes += [92, 117]
            for shift in stride(from: 12, through: 0, by: -4) { bytes.append(hex[Int((unit >> shift) & 15)]) }
        }
        bytes.append(34)
        for scalar in text.unicodeScalars {
            switch scalar.value {
            case 34, 92: bytes += [92, UInt8(scalar.value)]
            case 8: bytes += [92, 98]
            case 9: bytes += [92, 116]
            case 10: bytes += [92, 110]
            case 12: bytes += [92, 102]
            case 13: bytes += [92, 114]
            case 32...126: bytes.append(UInt8(scalar.value))
            case 0...0xffff: escaped(UInt16(scalar.value), into: &bytes)
            default:
                let adjusted = scalar.value - 0x10000
                escaped(UInt16(0xd800 + (adjusted >> 10)), into: &bytes)
                escaped(UInt16(0xdc00 + (adjusted & 1023)), into: &bytes)
            }
        }
        bytes.append(34)
    }

    private struct Parser {
        let bytes: [UInt8]
        var index = 0
        var values = 0
        mutating func whitespace() { while index < bytes.count, [9, 10, 13, 32].contains(bytes[index]) { index += 1 } }
        mutating func expect(_ byte: UInt8) throws {
            whitespace()
            guard index < bytes.count, bytes[index] == byte else { throw materialError("json") }
            index += 1
        }
        mutating func text() throws -> String {
            whitespace(); let start = index; try expect(34)
            while index < bytes.count {
                let byte = bytes[index]; index += 1
                if byte == 34 {
                    do { return try JSONDecoder().decode(String.self, from: Data(bytes[start..<index])) }
                    catch { throw materialError("json") }
                }
                if byte == 92 {
                    guard index < bytes.count else { throw materialError("json") }; index += 1
                } else if byte < 32 { throw materialError("json") }
            }
            throw materialError("json")
        }
        mutating func value(containers: Int) throws -> CanonicalValue {
            values += 1
            guard values <= 8192 else { throw materialError("json.limit") }
            whitespace()
            guard index < bytes.count else { throw materialError("json") }
            switch bytes[index] {
            case 123:
                guard containers < 8 else { throw materialError("json.limit") }
                index += 1; whitespace(); var fields: [String: CanonicalValue] = [:]
                if index < bytes.count, bytes[index] == 125 { index += 1; return .object(fields) }
                while true {
                    let key = try text()
                    guard fields[key] == nil else { throw materialError("json.duplicate") }
                    try expect(58); fields[key] = try value(containers: containers + 1); whitespace()
                    if index < bytes.count, bytes[index] == 125 { index += 1; return .object(fields) }
                    try expect(44)
                }
            case 91:
                guard containers < 8 else { throw materialError("json.limit") }
                index += 1; whitespace(); var elements: [CanonicalValue] = []
                if index < bytes.count, bytes[index] == 93 { index += 1; return .array(elements) }
                while true {
                    elements.append(try value(containers: containers + 1)); whitespace()
                    if index < bytes.count, bytes[index] == 93 { index += 1; return .array(elements) }
                    try expect(44)
                }
            case 34: return .text(try text())
            default:
                let start = index
                while index < bytes.count, ![9, 10, 13, 32, 44, 93, 125].contains(bytes[index]) { index += 1 }
                let token = bytes[start..<index]
                if token.elementsEqual("true".utf8) { return .boolean(true) }
                if token.elementsEqual("false".utf8) { return .boolean(false) }
                guard !token.isEmpty, token.count <= 20, token.allSatisfy({ (48...57).contains($0) }),
                      token.count == 1 || token.first != 48,
                      let number = UInt64(String(decoding: token, as: UTF8.self)) else { throw materialError("json") }
                return .uint(number)
            }
        }
    }
}

func materialError(_ code: String) -> UpdateError {
    UpdateError("installed.capability." + code, "Invalid installed capability material: " + code)
}
