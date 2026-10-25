import Foundation

/// Encoding a snapshot is a data operation. It creates no native presentation,
/// lifecycle, event or release authority.
public enum UINativePacketEncodingError: Error, Equatable, Sendable {
    case missingIdentity
    case outputLimit
}

public extension UIRenderSnapshot {
    /// The existing native packet shape with identities from this exact snapshot.
    /// Custom reconciler limits cannot widen the standard native packet bounds.
    /// The UI document, revision and generations are never changed or regenerated.
    func encodeNativePacketV1() throws -> Data {
        _ = try UIValidator().validate(document)
        var measurement = NativePacketWriterV1()
        try measurement.packet(self)
        var output = NativePacketWriterV1(capacity: measurement.count)
        try output.packet(self)
        return output.data!
    }
}

/// A first bounded pass measures every escaped byte before allocating the sole
/// output buffer. Both passes walk a tree narrowed to depth64/nodes4096. Property
/// sorting is limited to16 keys; no full JSONEncoder/String intermediate exists.
private struct NativePacketWriterV1 {
    private static let maximumBytes = 1_048_576
    private static let hex = Array("0123456789abcdef".utf8)
    private(set) var count = 0
    private(set) var data: Data?

    init(capacity: Int? = nil) {
        if let capacity { data = Data(capacity: capacity) }
    }

    private mutating func byte(_ value: UInt8) throws {
        guard count < Self.maximumBytes else { throw UINativePacketEncodingError.outputLimit }
        count += 1
        data?.append(value)
    }

    private mutating func raw(_ value: String) throws {
        let bytes = value.utf8
        guard bytes.count <= Self.maximumBytes - count else { throw UINativePacketEncodingError.outputLimit }
        count += bytes.count
        data?.append(contentsOf: bytes)
    }

    private mutating func quoted(_ value: String) throws {
        try byte(34)
        for value in value.utf8 {
            switch value {
            case 34, 92: try byte(92); try byte(value)
            case 0..<32:
                try raw("\\u00")
                try byte(Self.hex[Int(value >> 4)])
                try byte(Self.hex[Int(value & 15)])
            default: try byte(value)
            }
        }
        try byte(34)
    }

    mutating func packet(_ snapshot: UIRenderSnapshot) throws {
        try raw("{\"document\":{\"revision\":")
        try raw(String(snapshot.document.revision))
        try raw(",\"root\":")
        try node(snapshot.document.root)
        try raw(",\"schemaVersion\":1},\"identities\":[")
        var first = true
        try identities(snapshot.document.root, snapshot: snapshot, first: &first)
        try raw("],\"schemaVersion\":1}")
    }

    private mutating func identities(_ node: UINode, snapshot: UIRenderSnapshot,
                                     first: inout Bool) throws {
        guard let identity = snapshot.identity(for: node.id), identity.generation != 0,
              identity.id.utf8.elementsEqual(node.id.utf8) else {
            throw UINativePacketEncodingError.missingIdentity
        }
        if !first { try byte(44) }
        first = false
        try raw("{\"generation\":")
        try raw(String(identity.generation))
        try raw(",\"id\":")
        try quoted(identity.id)
        try byte(125)
        for child in node.children { try identities(child, snapshot: snapshot, first: &first) }
    }

    private mutating func node(_ node: UINode) throws {
        try raw("{\"actions\":[")
        for (index, action) in node.actions.enumerated() {
            if index != 0 { try byte(44) }
            try raw("{\"event\":")
            try quoted(action.event.rawValue)
            try raw(",\"id\":")
            try quoted(action.id)
            try byte(125)
        }
        try raw("],\"children\":[")
        for (index, child) in node.children.enumerated() {
            if index != 0 { try byte(44) }
            try self.node(child)
        }
        try raw("],\"id\":")
        try quoted(node.id)
        try raw(",\"kind\":")
        try quoted(node.kind.rawValue)
        try raw(",\"properties\":{")
        for (index, key) in node.properties.keys.sorted().enumerated() {
            if index != 0 { try byte(44) }
            try quoted(key)
            try byte(58)
            switch node.properties[key]! {
            case let .string(value): try quoted(value)
            case let .number(value): try raw(String(value))
            case let .bool(value): try raw(value ? "true" : "false")
            case .null: try raw("null")
            }
        }
        try raw("}}")
    }
}
