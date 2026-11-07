import Foundation
import MixerCore

@_spi(GuestUIV1) public enum GuestUIEventCodecErrorV1: Error, Sendable, Equatable {
    case messageTooLarge, malformed, fields, integer, identifier
}
/// Pure values only; no Codable conformance bypasses raw preflight.
@_spi(GuestUIV1) public struct GuestUIEventV1: Sendable, Equatable {
    public let sequence: UInt64
    public let revision: UInt64
    public let nodeID: String
    public let actionID: String
    public init(sequence: UInt64, revision: UInt64, nodeID: String, actionID: String) throws {
        guard sequence > 0, revision > 0 else { throw GuestUIEventCodecErrorV1.integer }
        guard guestUIIdentifierV1(nodeID), guestUIIdentifierV1(actionID) else { throw GuestUIEventCodecErrorV1.identifier }
        self.sequence = sequence; self.revision = revision; self.nodeID = nodeID; self.actionID = actionID
    }
}
@_spi(GuestUIV1) public enum GuestUIEventCodecV1 {
    public static func encode(_ value: GuestUIEventV1) throws -> Data {
        // Fixed sorted keys; only strings use Foundation's scalar JSON encoder.
        let encoder = JSONEncoder(); encoder.outputFormatting = [.withoutEscapingSlashes]
        let action = try encoder.encode(value.actionID), node = try encoder.encode(value.nodeID)
        var data = Data(#"{"actionID":"#.utf8); data.append(action)
        data.append(44)
        data.append(Data(#""event":"activate","nodeID":"#.utf8)); data.append(node)
        data.append(Data(",\"revision\":\(value.revision),\"schemaVersion\":1,\"sequence\":\(value.sequence),\"value\":null}".utf8))
        guard data.count <= 4096 else { throw GuestUIEventCodecErrorV1.messageTooLarge }
        return data
    }
    public static func decode(_ data: Data) throws -> GuestUIEventV1 {
        guard data.count <= 4096 else { throw GuestUIEventCodecErrorV1.messageTooLarge }
        do {
            try JSONInputGuard.validate(data, limits: JSONInputLimits(maximumBytes: 4096,
                maximumDepth: 1, maximumValues: 8, maximumStringBytes: 128, maximumKeyBytes: 32))
            var parser = GuestUIFlatEventV1(bytes: Array(data))
            let fields = try parser.object()
            guard Set(fields.keys) == ["schemaVersion", "sequence", "revision", "nodeID", "actionID", "event", "value"],
                  fields["schemaVersion"] == .literal("1"), fields["event"] == .string("activate"),
                  fields["value"] == .literal("null"),
                  case let .string(node)? = fields["nodeID"], case let .string(action)? = fields["actionID"] else {
                throw GuestUIEventCodecErrorV1.fields
            }
            func positive(_ key: String) throws -> UInt64 {
                guard case let .literal(raw)? = fields[key], let first = raw.utf8.first,
                      (49...57).contains(first), raw.utf8.allSatisfy({ (48...57).contains($0) }),
                      raw.utf8.count <= 20, let value = UInt64(raw), value > 0 else {
                    throw GuestUIEventCodecErrorV1.integer
                }
                return value
            }
            return try GuestUIEventV1(sequence: positive("sequence"), revision: positive("revision"),
                                      nodeID: node, actionID: action)
        } catch let error as GuestUIEventCodecErrorV1 { throw error }
        catch { throw GuestUIEventCodecErrorV1.malformed }
    }
}

private enum GuestUIFlatValueV1: Equatable { case string(String), literal(String) }
/// Preflight has already checked complete syntax/Unicode/duplicates. This small
/// flat extractor preserves numeric lexemes instead of accepting Codable coercion.
private struct GuestUIFlatEventV1 {
    let bytes: [UInt8]
    var index = 0
    mutating func whitespace() { while index < bytes.count && [9, 10, 13, 32].contains(bytes[index]) { index += 1 } }
    mutating func expect(_ byte: UInt8) throws {
        whitespace()
        guard index < bytes.count, bytes[index] == byte else { throw GuestUIEventCodecErrorV1.malformed }
        index += 1
    }
    mutating func string() throws -> String {
        whitespace(); let start = index; try expect(34)
        while index < bytes.count {
            let byte = bytes[index]; index += 1
            if byte == 34 { return try JSONDecoder().decode(String.self, from: Data(bytes[start..<index])) }
            if byte == 92 { index += 1 }
        }
        throw GuestUIEventCodecErrorV1.malformed
    }
    mutating func object() throws -> [String: GuestUIFlatValueV1] {
        try expect(123)
        var fields: [String: GuestUIFlatValueV1] = [:]
        while true {
            whitespace()
            if index < bytes.count, bytes[index] == 125 { index += 1; break }
            let key = try string(); try expect(58); whitespace()
            let value: GuestUIFlatValueV1
            if index < bytes.count, bytes[index] == 34 { value = .string(try string()) }
            else {
                let start = index
                while index < bytes.count && ![9, 10, 13, 32, 44, 125].contains(bytes[index]) { index += 1 }
                value = .literal(String(decoding: bytes[start..<index], as: UTF8.self))
            }
            guard fields.updateValue(value, forKey: key) == nil else { throw GuestUIEventCodecErrorV1.fields }
            whitespace()
            if index < bytes.count, bytes[index] == 125 { index += 1; break }
            try expect(44)
        }
        whitespace()
        guard index == bytes.count else { throw GuestUIEventCodecErrorV1.malformed }
        return fields
    }
}
