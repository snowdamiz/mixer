import Foundation
import MixerCore

public enum CapabilityWireError: Error, Equatable, Sendable { case invalid(String) }
public enum CapabilityFailure: String, CaseIterable, Sendable {
    case permissionDenied, unavailable, cancelled, deadlineExceeded, invalidResponse, redirectDenied, quotaExceeded, ioFailure
}
public struct CapabilityRequestID: Hashable, Sendable {
    public let session: String
    public let slot: UInt16
    public let generation: UInt32
    public init(session: String, slot: UInt16, generation: UInt32) { self.session = session; self.slot = slot; self.generation = generation }
    var wire: [String: WireValue] { ["session": .string(session), "slot": .uint(UInt32(slot)), "generation": .uint(generation)] }
    init(wire: [String: WireValue]) throws {
        try WireRules.exact(wire, ["session", "slot", "generation"])
        session = try WireRules.string(wire, "session", rule: "uuid", maximum: 36)
        slot = UInt16(try WireRules.uint(wire, "slot", minimum: 0, maximum: 65535))
        generation = try WireRules.uint(wire, "generation", minimum: 1, maximum: .max)
    }
}
public struct CapabilityCall: Equatable, Sendable {
    public let identity: CapabilityRequestID
    public let operation: CapabilityOperation
    public init(identity: CapabilityRequestID, operation: CapabilityOperation) { self.identity = identity; self.operation = operation }
}
public struct CapabilityCancellation: Equatable, Sendable {
    public let identity: CapabilityRequestID
    public let capabilityID: String
    public let operationID: String
}
public enum CapabilityInbound: Equatable, Sendable { case call(CapabilityCall), cancel(CapabilityCancellation) }
public enum CapabilityOutcome: Equatable, Sendable { case success(CapabilityResult), failure(CapabilityFailure) }
public struct CapabilityCompletion: Equatable, Sendable {
    public let call: CapabilityCall
    public let outcome: CapabilityOutcome
    public init(call: CapabilityCall, outcome: CapabilityOutcome) { self.call = call; self.outcome = outcome }
}

// Value-only internal representation. Public models deliberately do not expose an
// unguarded Codable path for untrusted input.
indirect enum WireValue: Codable, Equatable, Sendable {
    case object([String: WireValue]), array([WireValue]), string(String), uint(UInt32), bool(Bool)
    init(from decoder: any Decoder) throws {
        let c = try decoder.singleValueContainer()
        if let value = try? c.decode([String: WireValue].self) { self = .object(value) }
        else if let value = try? c.decode([WireValue].self) { self = .array(value) }
        else if let value = try? c.decode(String.self) { self = .string(value) }
        else if let value = try? c.decode(Bool.self) { self = .bool(value) }
        else if let value = try? c.decode(UInt32.self) { self = .uint(value) }
        else { throw CapabilityWireError.invalid("wire type") }
    }
    func encode(to encoder: any Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self { case .object(let v): try c.encode(v); case .array(let v): try c.encode(v)
        case .string(let v): try c.encode(v); case .uint(let v): try c.encode(v); case .bool(let v): try c.encode(v) }
    }
}

enum WireRules {
    static func exact(_ value: [String: WireValue], _ keys: Set<String>) throws {
        guard Set(value.keys) == keys else { throw CapabilityWireError.invalid("fields") }
    }
    static func object(_ value: WireValue?) throws -> [String: WireValue] {
        guard case .object(let object) = value else { throw CapabilityWireError.invalid("object") }; return object
    }
    static func uint(_ object: [String: WireValue], _ key: String, minimum: UInt32, maximum: UInt32) throws -> UInt32 {
        guard case .uint(let n) = object[key], n >= minimum, n <= maximum else { throw CapabilityWireError.invalid(key) }; return n
    }
    static func bool(_ object: [String: WireValue], _ key: String) throws -> Bool {
        guard case .bool(let b) = object[key] else { throw CapabilityWireError.invalid(key) }; return b
    }
    static func string(_ object: [String: WireValue], _ key: String, rule: String, maximum: Int) throws -> String {
        guard case .string(let value) = object[key] else { throw CapabilityWireError.invalid(key) }
        let bytes = Array(value.utf8)
        if rule == "base64" {
            guard value.count <= ((maximum + 2) / 3) * 4, let data = Data(base64Encoded: value), data.count <= maximum,
                  data.base64EncodedString() == value else { throw CapabilityWireError.invalid(key) }; return value
        }
        guard bytes.count <= maximum, bytes.allSatisfy({ (32...126).contains($0) }) else { throw CapabilityWireError.invalid(key) }
        let identifier = !bytes.isEmpty && bytes.allSatisfy { (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || $0 == 45 || $0 == 95 }
        switch rule {
        case "identifier": guard identifier else { throw CapabilityWireError.invalid(key) }
        case "uuid": guard UUID(uuidString: value)?.uuidString.lowercased() == value else { throw CapabilityWireError.invalid(key) }
        case "method": guard ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"].contains(value) else { throw CapabilityWireError.invalid(key) }
        case "headerName": guard !bytes.isEmpty, bytes.allSatisfy({ (97...122).contains($0) || (48...57).contains($0) || $0 == 45 }),
            !["host", "connection", "content-length", "transfer-encoding", "proxy-authorization", "proxy-authenticate", "cookie", "set-cookie"].contains(value) else { throw CapabilityWireError.invalid(key) }
        case "httpsURL": _ = try origin(value)
        case "ascii": break
        default: throw CapabilityWireError.invalid("rule")
        }
        return value
    }
    static func headers(_ object: [String: WireValue], _ key: String, maximum: Int) throws -> [Header] {
        guard case .array(let values) = object[key], values.count <= maximum else { throw CapabilityWireError.invalid(key) }
        let headers = try values.map { try Header(wire: self.object($0)) }
        guard Set(headers.map(\.name)).count == headers.count else { throw CapabilityWireError.invalid("duplicate header") }; return headers
    }
    static func origin(_ url: String) throws -> String {
        guard url.hasPrefix("https://"), url.utf8.allSatisfy({ (33...126).contains($0) && ![35, 92].contains($0) }), url.utf8.count <= 4096 else { throw CapabilityWireError.invalid("https URL") }
        let rest = url.dropFirst(8); let authority = String(rest.prefix { $0 != "/" && $0 != "?" })
        let parts = authority.split(separator: ":", omittingEmptySubsequences: false)
        guard (1...2).contains(parts.count), !parts[0].isEmpty, parts[0].utf8.count <= 253 else { throw CapabilityWireError.invalid("origin") }
        let labels = parts[0].split(separator: ".", omittingEmptySubsequences: false)
        guard labels.allSatisfy({ !$0.isEmpty && $0.utf8.count <= 63 && $0.first != "-" && $0.last != "-" && $0.utf8.allSatisfy({ (97...122).contains($0) || (48...57).contains($0) || $0 == 45 }) }) else { throw CapabilityWireError.invalid("host") }
        if parts.count == 2 {
            guard let port = UInt16(parts[1]), port > 0, String(port) == parts[1], port != 443 else { throw CapabilityWireError.invalid("port") }
        }
        let bytes = Array(url.utf8); var i = 0
        while i < bytes.count {
            if bytes[i] == 37 {
                guard i + 2 < bytes.count, [bytes[i+1], bytes[i+2]].allSatisfy({ (48...57).contains($0) || (65...70).contains($0) }) else { throw CapabilityWireError.invalid("percent escape") }; i += 2
            }
            i += 1
        }
        return "https://" + authority
    }
}

public enum CapabilityCodec {
    static func decodeObject(_ data: Data) throws -> [String: WireValue] {
        guard data.count <= 524288 else { throw CapabilityWireError.invalid("bytes") }
        let bytes = Array(data)
        let snapshot = Data(bytes)
        try JSONInputGuard.validate(snapshot, limits: JSONInputLimits(maximumBytes: 524288, maximumDepth: 8, maximumValues: 8192, maximumStringBytes: 350000, maximumKeyBytes: 64))
        // Foundation accepts 1.0/1e0 as integers. The wire requires the same exact
        // unsigned-decimal number grammar on Swift and Java.
        var index = 0; var quoted = false; var escaped = false
        while index < bytes.count {
            let b = bytes[index]
            if quoted { if escaped { escaped = false } else if b == 92 { escaped = true } else if b == 34 { quoted = false }; index += 1; continue }
            if b == 34 { quoted = true; index += 1; continue }
            if b == 45 || (48...57).contains(b) {
                let start = index
                while index < bytes.count, ![32,9,10,13,44,93,125].contains(bytes[index]) { index += 1 }
                let token = bytes[start..<index]
                guard token.allSatisfy({ (48...57).contains($0) }), token.count <= 10,
                      UInt32(String(decoding: token, as: UTF8.self)) != nil else { throw CapabilityWireError.invalid("integer") }
                continue
            }
            index += 1
        }
        return try WireRules.object(JSONDecoder().decode(WireValue.self, from: snapshot))
    }
    static func encodeObject(_ object: [String: WireValue]) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let data = try encoder.encode(WireValue.object(object)); _ = try decodeObject(data); return data
    }
    static func envelope(_ call: CapabilityCall, kind: String) throws -> [String: WireValue] {
        _ = try CapabilityRequestID(wire: call.identity.wire)
        _ = try CapabilityOperation.decode(capability: call.operation.capabilityID, operation: call.operation.operationID, wire: call.operation.wire)
        return ["schema": .uint(1), "kind": .string(kind), "identity": .object(call.identity.wire), "capability": .string(call.operation.capabilityID),
                "schemaHash": .string(call.operation.schemaSHA256), "operation": .string(call.operation.operationID)]
    }
    public static func encodeCall(_ call: CapabilityCall) throws -> Data {
        var object = try envelope(call, kind: "call"); object["arguments"] = .object(call.operation.wire); return try encodeObject(object)
    }
    public static func encodeCancel(_ call: CapabilityCall) throws -> Data { try encodeObject(envelope(call, kind: "cancel")) }
    public static func encodeCancellation(_ cancellation: CapabilityCancellation) throws -> Data {
        _ = try CapabilityRequestID(wire: cancellation.identity.wire)
        let object: [String: WireValue] = ["schema": .uint(1), "kind": .string("cancel"), "identity": .object(cancellation.identity.wire),
            "capability": .string(cancellation.capabilityID), "schemaHash": .string(cancellation.capabilityID == CapabilitySchemas.httpID ? CapabilitySchemas.httpSHA256 : CapabilitySchemas.storageSHA256), "operation": .string(cancellation.operationID)]
        _ = try metadata(object); return try encodeObject(object)
    }
    public static func decodeInbound(_ data: Data) throws -> CapabilityInbound {
        let object = try decodeObject(data)
        let kind = try WireRules.string(object, "kind", rule: "ascii", maximum: 16)
        try WireRules.exact(object, kind == "call" ? ["schema","kind","identity","capability","schemaHash","operation","arguments"] : ["schema","kind","identity","capability","schemaHash","operation"])
        guard kind == "call" || kind == "cancel" else { throw CapabilityWireError.invalid("kind") }
        let identity = try CapabilityRequestID(wire: WireRules.object(object["identity"]))
        let (capability, operation) = try metadata(object)
        if kind == "cancel" { return .cancel(CapabilityCancellation(identity: identity, capabilityID: capability, operationID: operation)) }
        let arguments = try WireRules.object(object["arguments"])
        let call = try CapabilityCall(identity: identity, operation: CapabilityOperation.decode(capability: capability, operation: operation, wire: arguments))
        return .call(call)
    }
    static func metadata(_ object: [String: WireValue]) throws -> (String, String) {
        _ = try WireRules.uint(object, "schema", minimum: 1, maximum: 1)
        let cap = try WireRules.string(object, "capability", rule: "ascii", maximum: 64)
        let op = try WireRules.string(object, "operation", rule: "ascii", maximum: 16)
        let hash = try WireRules.string(object, "schemaHash", rule: "ascii", maximum: 64)
        let expected = cap == CapabilitySchemas.httpID ? CapabilitySchemas.httpSHA256 : cap == CapabilitySchemas.storageID ? CapabilitySchemas.storageSHA256 : ""
        guard !expected.isEmpty, hash == expected,
              cap == CapabilitySchemas.httpID ? op == "request" : ["get", "put", "delete"].contains(op) else { throw CapabilityWireError.invalid("schema hash/operation") }
        return (cap, op)
    }
    public static func encodeCompletion(_ completion: CapabilityCompletion) throws -> Data {
        var object = try envelope(completion.call, kind: "completion")
        switch completion.outcome {
        case .failure(let code): object["outcome"] = .object(["kind": .string("failure"), "code": .string(code.rawValue)])
        case .success(let result):
            guard result.capabilityID == completion.call.operation.capabilityID, result.operationID == completion.call.operation.operationID else { throw CapabilityWireError.invalid("result binding") }
            _ = try CapabilityResult.decode(capability: result.capabilityID, operation: result.operationID, wire: result.wire)
            object["outcome"] = .object(["kind": .string("success"), "value": .object(result.wire)])
        }
        return try encodeObject(object)
    }
    public static func decodeCompletion(_ data: Data, expected: CapabilityCall) throws -> CapabilityCompletion {
        let object = try decodeObject(data)
        try WireRules.exact(object, ["schema","kind","identity","capability","schemaHash","operation","outcome"])
        let (cap, op) = try metadata(object)
        guard object["kind"] == .string("completion"), try CapabilityRequestID(wire: WireRules.object(object["identity"])) == expected.identity,
              cap == expected.operation.capabilityID, op == expected.operation.operationID else { throw CapabilityWireError.invalid("completion owner") }
        let outcome = try WireRules.object(object["outcome"])
        switch outcome["kind"] {
        case .string("success"):
            try WireRules.exact(outcome, ["kind", "value"])
            return try CapabilityCompletion(call: expected, outcome: .success(CapabilityResult.decode(capability: cap, operation: op, wire: WireRules.object(outcome["value"]))))
        case .string("failure"):
            try WireRules.exact(outcome, ["kind", "code"])
            guard let code = try CapabilityFailure(rawValue: WireRules.string(outcome, "code", rule: "ascii", maximum: 32)) else { throw CapabilityWireError.invalid("failure") }
            return CapabilityCompletion(call: expected, outcome: .failure(code))
        default: throw CapabilityWireError.invalid("outcome")
        }
    }
}
