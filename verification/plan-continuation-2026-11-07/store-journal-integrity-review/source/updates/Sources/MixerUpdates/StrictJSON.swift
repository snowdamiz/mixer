import Foundation

/// Preflight duplicate keys and resource bounds before Foundation decoding.
/// Foundation's JSONDecoder otherwise accepts repeated object keys.
public enum StrictJSON {
    public static func decode<T: Decodable>(_ type: T.Type, from data: Data, maximumBytes: Int = 1_048_576) throws -> T {
        guard data.count <= maximumBytes else { throw UpdateError("json.size", "JSON exceeds byte limit") }
        var scanner = Scanner(bytes: Array(data))
        try scanner.value(depth: 0)
        scanner.whitespace()
        guard scanner.index == scanner.bytes.count else { throw UpdateError("json.trailing", "Trailing JSON data") }
        return try JSONDecoder().decode(type, from: data)
    }
    private struct Scanner {
        let bytes: [UInt8]
        var index = 0
        var nodes = 0
        mutating func whitespace() { while index < bytes.count && [9, 10, 13, 32].contains(bytes[index]) { index += 1 } }
        mutating func expect(_ value: UInt8) throws {
            whitespace(); guard index < bytes.count, bytes[index] == value else { throw UpdateError("json.syntax", "Malformed JSON at byte \(index)") }; index += 1
        }
        mutating func string() throws -> String {
            whitespace(); let start = index; try expect(34)
            while index < bytes.count {
                let byte = bytes[index]; index += 1
                if byte == 34 {
                    guard index - start <= 131_072 else { throw UpdateError("json.string", "JSON string exceeds limit") }
                    return try JSONDecoder().decode(String.self, from: Data(bytes[start..<index]))
                }
                if byte == 92 { guard index < bytes.count else { break }; index += 1 }
                else if byte < 32 { throw UpdateError("json.syntax", "Unescaped control character") }
            }
            throw UpdateError("json.syntax", "Unterminated JSON string")
        }
        mutating func value(depth: Int) throws {
            nodes += 1
            guard depth <= 32, nodes <= 20_000 else { throw UpdateError("json.limit", "JSON nesting/node limit exceeded") }
            whitespace()
            guard index < bytes.count else { throw UpdateError("json.syntax", "Truncated JSON") }
            switch bytes[index] {
            case 123:
                index += 1; whitespace(); var keys = Set<String>()
                if index < bytes.count, bytes[index] == 125 { index += 1; return }
                while true {
                    let key = try string()
                    guard keys.insert(key).inserted else { throw UpdateError("json.duplicate", "Duplicate JSON key: \(key)") }
                    try expect(58); try value(depth: depth + 1); whitespace()
                    if index < bytes.count, bytes[index] == 125 { index += 1; break }
                    try expect(44)
                }
            case 91:
                index += 1; whitespace()
                if index < bytes.count, bytes[index] == 93 { index += 1; return }
                while true {
                    try value(depth: depth + 1); whitespace()
                    if index < bytes.count, bytes[index] == 93 { index += 1; break }
                    try expect(44)
                }
            case 34: _ = try string()
            default:
                let start = index
                while index < bytes.count, ![9, 10, 13, 32, 44, 93, 125].contains(bytes[index]) { index += 1 }
                guard index > start, index - start <= 32 else { throw UpdateError("json.syntax", "Invalid primitive") }
                let token = String(decoding: bytes[start..<index], as: UTF8.self)
                guard token == "true" || token == "false" || token == "null" || token.range(of: "^(0|[1-9][0-9]*)$", options: .regularExpression) != nil else { throw UpdateError("json.primitive", "Only unsigned integers, booleans and strings are permitted") }
            }
        }
    }
}
