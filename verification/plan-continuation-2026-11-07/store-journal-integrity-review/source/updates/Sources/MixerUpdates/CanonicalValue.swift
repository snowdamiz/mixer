import Foundation

public struct UpdateError: Error, CustomStringConvertible, Sendable, Equatable {
    public let code: String
    public let description: String
    public init(_ code: String, _ description: String) { self.code = code; self.description = description }
}

/// Restricted RFC 8949 data model shared with release-v1. Floating point,
/// signed integers, tags, null and indefinite lengths are not in this profile.
public indirect enum CanonicalValue: Codable, Equatable, Sendable {
    case uint(UInt64), text(String), boolean(Bool), array([CanonicalValue]), object([String: CanonicalValue])

    public init(from decoder: any Decoder) throws {
        let value = try decoder.singleValueContainer()
        if let boolean = try? value.decode(Bool.self) { self = .boolean(boolean) }
        else if let number = try? value.decode(UInt64.self) { self = .uint(number) }
        else if let string = try? value.decode(String.self) { self = .text(string) }
        else if let array = try? value.decode([CanonicalValue].self) { self = .array(array) }
        else { self = .object(try value.decode([String: CanonicalValue].self)) }
    }
    public func encode(to encoder: any Encoder) throws {
        var value = encoder.singleValueContainer()
        switch self {
        case let .uint(n): try value.encode(n)
        case let .text(s): try value.encode(s)
        case let .boolean(b): try value.encode(b)
        case let .array(a): try value.encode(a)
        case let .object(o): try value.encode(o)
        }
    }
    public var object: [String: CanonicalValue]? { if case let .object(value) = self { value } else { nil } }
    public var text: String? { if case let .text(value) = self { value } else { nil } }
    public var uint: UInt64? { if case let .uint(value) = self { value } else { nil } }

    public func canonicalCBOR() throws -> Data {
        var result = Data()
        try encodeCBOR(into: &result, depth: 0)
        guard result.count <= 1_048_576 else { throw UpdateError("manifest.size", "Canonical metadata exceeds 1 MiB") }
        return result
    }
    private func encodeCBOR(into result: inout Data, depth: Int) throws {
        guard depth <= 32 else { throw UpdateError("manifest.depth", "Canonical metadata nesting exceeds 32") }
        switch self {
        case let .uint(value): Self.head(0, value, into: &result)
        case let .text(value):
            let bytes = Data(value.utf8)
            guard bytes.count <= 65_536 else { throw UpdateError("manifest.string", "Metadata string exceeds 64 KiB") }
            Self.head(3, UInt64(bytes.count), into: &result); result.append(bytes)
        case let .boolean(value): result.append(value ? 0xf5 : 0xf4)
        case let .array(values):
            guard values.count <= 4096 else { throw UpdateError("manifest.array", "Metadata collection exceeds limit") }
            Self.head(4, UInt64(values.count), into: &result)
            for value in values { try value.encodeCBOR(into: &result, depth: depth + 1) }
        case let .object(values):
            guard values.count <= 4096 else { throw UpdateError("manifest.map", "Metadata collection exceeds limit") }
            var sorted: [(Data, CanonicalValue)] = []
            for (key, value) in values { sorted.append((try CanonicalValue.text(key).canonicalCBOR(), value)) }
            sorted.sort { $0.0.lexicographicallyPrecedes($1.0) }
            Self.head(5, UInt64(sorted.count), into: &result)
            for (key, value) in sorted { result.append(key); try value.encodeCBOR(into: &result, depth: depth + 1) }
        }
        guard result.count <= 1_048_576 else { throw UpdateError("manifest.size", "Canonical metadata exceeds 1 MiB") }
    }
    private static func head(_ major: UInt8, _ value: UInt64, into bytes: inout Data) {
        let prefix = major << 5
        if value < 24 { bytes.append(prefix | UInt8(value)) }
        else if value <= 0xff { bytes.append(prefix | 24); bytes.append(UInt8(value)) }
        else if value <= 0xffff { bytes.append(prefix | 25); appendBigEndian(value, count: 2, into: &bytes) }
        else if value <= 0xffff_ffff { bytes.append(prefix | 26); appendBigEndian(value, count: 4, into: &bytes) }
        else { bytes.append(prefix | 27); appendBigEndian(value, count: 8, into: &bytes) }
    }
    private static func appendBigEndian(_ value: UInt64, count: Int, into bytes: inout Data) {
        for shift in stride(from: (count - 1) * 8, through: 0, by: -8) { bytes.append(UInt8(truncatingIfNeeded: value >> shift)) }
    }
}

extension Dictionary where Key == String, Value == CanonicalValue {
    func required(_ key: String) throws -> CanonicalValue {
        guard let value = self[key] else { throw UpdateError("manifest.missing", "Missing \(key)") }; return value
    }
    func text(_ key: String) throws -> String {
        guard let value = try required(key).text else { throw UpdateError("manifest.type", "\(key) must be text") }; return value
    }
    func uint(_ key: String) throws -> UInt64 {
        guard let value = try required(key).uint else { throw UpdateError("manifest.type", "\(key) must be an unsigned integer") }; return value
    }
    func object(_ key: String) throws -> [String: CanonicalValue] {
        guard let value = try required(key).object else { throw UpdateError("manifest.type", "\(key) must be an object") }; return value
    }
    func exactKeys(_ keys: Set<String>) throws {
        guard Set(self.keys) == keys else { throw UpdateError("manifest.fields", "Missing or unknown fields: \(Set(self.keys).symmetricDifference(keys).sorted().joined(separator: ", "))") }
    }
}

private struct ConfigurationField: CodingKey {
    let stringValue: String
    var intValue: Int? { nil }
    init(stringValue: String) { self.stringValue = stringValue }
    init?(intValue: Int) { return nil }
}

func requireConfigurationFields(_ decoder: any Decoder, _ fields: Set<String>) throws {
    let keys = Set(try decoder.container(keyedBy: ConfigurationField.self).allKeys.map(\.stringValue))
    guard keys == fields else { throw UpdateError("manifest.fields", "Missing or unknown installed configuration fields") }
}
