import Foundation

public enum NodeKind: String, Codable, CaseIterable, Hashable, Sendable {
    case text, button, textField, toggle, vStack, hStack, zStack, list, section, navigation
}

/// UI properties are scalar values. Object graphs, pointers and executable callbacks
/// cannot enter the renderer through this representation.
public enum UIValue: Codable, Equatable, Sendable {
    case string(String), number(Double), bool(Bool), null

    public init(from decoder: any Decoder) throws {
        let value = try decoder.singleValueContainer()
        if value.decodeNil() { self = .null }
        else if let boolean = try? value.decode(Bool.self) { self = .bool(boolean) }
        else if let string = try? value.decode(String.self) { self = .string(string) }
        else { self = .number(try value.decode(Double.self)) }
    }

    public func encode(to encoder: any Encoder) throws {
        var value = encoder.singleValueContainer()
        switch self {
        case let .string(string): try value.encode(string)
        case let .number(number): try value.encode(number)
        case let .bool(boolean): try value.encode(boolean)
        case .null: try value.encodeNil()
        }
    }

    public var string: String? { if case let .string(value) = self { value } else { nil } }
    public var number: Double? { if case let .number(value) = self { value } else { nil } }
    public var bool: Bool? { if case let .bool(value) = self { value } else { nil } }
}

public enum UIEventKind: String, Codable, Hashable, Sendable {
    case activate, textChange, valueChange, submit
}

public struct UIActionBinding: Codable, Equatable, Sendable {
    public let id: String
    public let event: UIEventKind

    public init(id: String, event: UIEventKind) { self.id = id; self.event = event }

    public init(from decoder: any Decoder) throws {
        try rejectUnknownKeys(decoder, allowed: ["id", "event"])
        let values = try decoder.container(keyedBy: CodingKeys.self)
        id = try values.decode(String.self, forKey: .id)
        event = try values.decode(UIEventKind.self, forKey: .event)
    }
}

public struct UINode: Codable, Equatable, Sendable, Identifiable {
    public let id: String
    public let kind: NodeKind
    public var properties: [String: UIValue]
    public let children: [UINode]
    public let actions: [UIActionBinding]

    public init(id: String, kind: NodeKind, properties: [String: UIValue] = [:],
                children: [UINode] = [], actions: [UIActionBinding] = []) {
        self.id = id; self.kind = kind; self.properties = properties
        self.children = children; self.actions = actions
    }

    public init(from decoder: any Decoder) throws {
        var count = 0
        self = try Self.decode(from: decoder, limits: .standard, depth: 1, count: &count)
    }

    fileprivate static func decode(from decoder: any Decoder, limits: UIValidationLimits,
                                   depth: Int, count: inout Int) throws -> UINode {
        guard depth <= limits.maximumDepth else { throw UIValidationError.limitExceeded("depth") }
        count += 1
        guard count <= limits.maximumNodes else { throw UIValidationError.limitExceeded("nodes") }
        try rejectUnknownKeys(decoder, allowed: ["id", "kind", "properties", "children", "actions"])
        let values = try decoder.container(keyedBy: CodingKeys.self)
        let id = try values.decode(String.self, forKey: .id)
        let kind = try values.decode(NodeKind.self, forKey: .kind)
        let propertyDecoder = try values.superDecoder(forKey: .properties)
        let propertyValues = try propertyDecoder.container(keyedBy: WireKey.self)
        guard propertyValues.allKeys.count <= 16 else { throw UIValidationError.limitExceeded("properties") }
        var properties: [String: UIValue] = [:]
        for key in propertyValues.allKeys {
            properties[key.stringValue] = try propertyValues.decode(UIValue.self, forKey: key)
        }
        var childValues = try values.nestedUnkeyedContainer(forKey: .children)
        var children: [UINode] = []
        while !childValues.isAtEnd {
            guard children.count < limits.maximumChildrenPerNode else {
                throw UIValidationError.limitExceeded("children")
            }
            children.append(try Self.decode(from: childValues.superDecoder(), limits: limits,
                                            depth: depth + 1, count: &count))
        }
        var actionValues = try values.nestedUnkeyedContainer(forKey: .actions)
        var actions: [UIActionBinding] = []
        while !actionValues.isAtEnd {
            guard actions.count < 4 else { throw UIValidationError.limitExceeded("actions") }
            actions.append(try actionValues.decode(UIActionBinding.self))
        }
        return UINode(id: id, kind: kind, properties: properties, children: children, actions: actions)
    }
}

public struct UIDocument: Codable, Equatable, Sendable {
    public static let currentSchemaVersion = 1
    public let schemaVersion: Int
    public let revision: UInt64
    public let root: UINode

    public init(schemaVersion: Int = Self.currentSchemaVersion, revision: UInt64, root: UINode) {
        self.schemaVersion = schemaVersion; self.revision = revision; self.root = root
    }

    public init(from decoder: any Decoder) throws {
        try rejectUnknownKeys(decoder, allowed: ["schemaVersion", "revision", "root"])
        let values = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try values.decode(Int.self, forKey: .schemaVersion)
        guard schemaVersion == Self.currentSchemaVersion else {
            throw UIValidationError.unsupportedSchema(schemaVersion)
        }
        revision = try values.decode(UInt64.self, forKey: .revision)
        let limits = decoder.userInfo[.mixerUILimits] as? UIValidationLimits ?? .standard
        guard limits.isValid else { throw UIValidationError.invalidLimits }
        var count = 0
        root = try UINode.decode(from: values.superDecoder(forKey: .root), limits: limits, depth: 1, count: &count)
    }
}

private struct WireKey: CodingKey {
    var stringValue: String
    var intValue: Int? { nil }
    init(stringValue: String) { self.stringValue = stringValue }
    init?(intValue: Int) { return nil }
}

private func rejectUnknownKeys(_ decoder: any Decoder, allowed: Set<String>) throws {
    let keys = try decoder.container(keyedBy: WireKey.self).allKeys
    if let unknown = keys.first(where: { !allowed.contains($0.stringValue) }) {
        throw UIValidationError.unsupportedField(unknown.stringValue)
    }
}

extension CodingUserInfoKey {
    fileprivate static let mixerUILimits = CodingUserInfoKey(rawValue: "mixer.ui.validationLimits")!
}

extension UIValidator {
    /// The byte limit applies before JSON parsing. Node, depth, property, action and child
    /// limits apply during decoding as well as to in-memory authoring results.
    public func decode(_ data: Data) throws -> ValidatedUIDocument {
        guard limits.isValid else { throw UIValidationError.invalidLimits }
        guard data.count <= limits.maximumMessageBytes else { throw UIValidationError.limitExceeded("messageBytes") }
        let decoder = JSONDecoder()
        decoder.userInfo[.mixerUILimits] = limits
        return try validate(decoder.decode(UIDocument.self, from: data))
    }

    public func encode(_ document: UIDocument) throws -> Data {
        _ = try validate(document)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let data = try encoder.encode(document)
        guard data.count <= limits.maximumMessageBytes else { throw UIValidationError.limitExceeded("messageBytes") }
        return data
    }
}
