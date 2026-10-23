public struct UIValidationLimits: Equatable, Sendable {
    public static let standard = UIValidationLimits()
    public let maximumMessageBytes: Int
    public let maximumNodes: Int
    public let maximumDepth: Int
    public let maximumChildrenPerNode: Int
    public let maximumStringBytes: Int

    public init(maximumMessageBytes: Int = 1_048_576, maximumNodes: Int = 4096,
                maximumDepth: Int = 64, maximumChildrenPerNode: Int = 1000,
                maximumStringBytes: Int = 16_384) {
        self.maximumMessageBytes = maximumMessageBytes
        self.maximumNodes = maximumNodes
        self.maximumDepth = maximumDepth
        self.maximumChildrenPerNode = maximumChildrenPerNode
        self.maximumStringBytes = maximumStringBytes
    }

    var isValid: Bool {
        (1...16_777_216).contains(maximumMessageBytes) && (1...65_536).contains(maximumNodes)
            && (1...128).contains(maximumDepth) && (1...10_000).contains(maximumChildrenPerNode)
            && (1...262_144).contains(maximumStringBytes)
    }
}

public enum UIValidationError: Error, Equatable, Sendable {
    case unguardedDecoder
    case invalidLimits
    case unsupportedSchema(Int)
    case limitExceeded(String)
    case invalidIdentifier(String)
    case duplicateIdentity(String)
    case unsupportedNode(NodeKind)
    case unsupportedField(String)
    case invalidProperty(node: String, key: String)
    case invalidChildren(String)
    case invalidAction(node: String, event: UIEventKind)
}

public struct ValidatedUIDocument: Sendable {
    public let document: UIDocument
    public let nodeCount: Int
    // Only a validator can establish this type's invariant.
    init(document: UIDocument, nodeCount: Int) { self.document = document; self.nodeCount = nodeCount }
}

public struct UIValidator: Sendable {
    public let limits: UIValidationLimits
    public let supportedKinds: Set<NodeKind>

    public init(limits: UIValidationLimits = .standard, supportedKinds: Set<NodeKind> = Set(NodeKind.allCases)) {
        self.limits = limits; self.supportedKinds = supportedKinds
    }

    public func validate(_ document: UIDocument) throws -> ValidatedUIDocument {
        guard limits.isValid else { throw UIValidationError.invalidLimits }
        guard document.schemaVersion == UIDocument.currentSchemaVersion else {
            throw UIValidationError.unsupportedSchema(document.schemaVersion)
        }
        var pending = [(document.root, 1)]
        var identities: Set<String> = []
        var bytes = 0
        while let (node, depth) = pending.popLast() {
            guard depth <= limits.maximumDepth else { throw UIValidationError.limitExceeded("depth") }
            guard identities.count < limits.maximumNodes else { throw UIValidationError.limitExceeded("nodes") }
            guard validIdentifier(node.id) else { throw UIValidationError.invalidIdentifier(node.id) }
            guard identities.insert(node.id).inserted else { throw UIValidationError.duplicateIdentity(node.id) }
            guard supportedKinds.contains(node.kind) else { throw UIValidationError.unsupportedNode(node.kind) }
            guard node.children.count <= limits.maximumChildrenPerNode else { throw UIValidationError.limitExceeded("children") }
            guard node.properties.count <= 16 else { throw UIValidationError.limitExceeded("properties") }
            guard node.actions.count <= 4 else { throw UIValidationError.limitExceeded("actions") }
            bytes += node.id.utf8.count + node.kind.rawValue.utf8.count
            for (key, value) in node.properties {
                bytes += key.utf8.count
                switch value {
                case let .string(string):
                    guard string.utf8.count <= limits.maximumStringBytes else { throw UIValidationError.limitExceeded("stringBytes") }
                    bytes += string.utf8.count
                case let .number(number):
                    guard number.isFinite else { throw UIValidationError.invalidProperty(node: node.id, key: key) }
                    bytes += 8
                case .bool: bytes += 1
                case .null: break
                }
            }
            try validateProperties(of: node)
            try validateStructure(of: node)
            var events: Set<UIEventKind> = []
            for action in node.actions {
                guard validIdentifier(action.id) else { throw UIValidationError.invalidIdentifier(action.id) }
                guard events.insert(action.event).inserted, permittedEvents(for: node.kind).contains(action.event) else {
                    throw UIValidationError.invalidAction(node: node.id, event: action.event)
                }
                bytes += action.id.utf8.count + action.event.rawValue.utf8.count
            }
            for required in requiredEvents(for: node.kind) where !events.contains(required) {
                throw UIValidationError.invalidAction(node: node.id, event: required)
            }
            // This aggregate bound also protects in-memory trees before encoding. The exact
            // serialized byte bound is checked by encode/decode on the wire.
            guard bytes <= limits.maximumMessageBytes else { throw UIValidationError.limitExceeded("contentBytes") }
            // Admit the entire next frontier before retaining any child. Counting
            // only visited identities lets a wide/deep tree grow pending storage
            // beyond the node limit before it reaches the eventual rejection.
            guard node.children.isEmpty || depth < limits.maximumDepth else {
                throw UIValidationError.limitExceeded("depth")
            }
            let availableNodes = limits.maximumNodes - identities.count - pending.count
            guard node.children.count <= availableNodes else {
                throw UIValidationError.limitExceeded("nodes")
            }
            for child in node.children.reversed() { pending.append((child, depth + 1)) }
        }
        return ValidatedUIDocument(document: document, nodeCount: identities.count)
    }

    private func validateProperties(of node: UINode) throws {
        let strings = ["accessibilityLabel", "accessibilityHint", "accessibilityValue", "accessibilityIdentifier"]
        var allowed = Set(strings + ["disabled"])
        for (key, value) in node.properties {
            if strings.contains(key), value.string == nil { throw UIValidationError.invalidProperty(node: node.id, key: key) }
            if key == "disabled", value.bool == nil { throw UIValidationError.invalidProperty(node: node.id, key: key) }
        }
        func requireString(_ key: String) throws {
            guard node.properties[key]?.string != nil else { throw UIValidationError.invalidProperty(node: node.id, key: key) }
        }
        func optionalString(_ key: String, values: Set<String>? = nil) throws {
            if let value = node.properties[key] {
                guard let string = value.string, values == nil || values!.contains(string) else {
                    throw UIValidationError.invalidProperty(node: node.id, key: key)
                }
            }
        }
        switch node.kind {
        case .text:
            allowed.formUnion(["text", "style", "selectable", "maxLines"])
            try requireString("text")
            try optionalString("style", values: ["body", "headline", "title", "caption"])
            if let value = node.properties["selectable"], value.bool == nil {
                throw UIValidationError.invalidProperty(node: node.id, key: "selectable")
            }
            if let value = node.properties["maxLines"] {
                guard let number = value.number, number.rounded() == number, (1...100).contains(number) else {
                    throw UIValidationError.invalidProperty(node: node.id, key: "maxLines")
                }
            }
        case .button:
            allowed.formUnion(["label", "role"])
            try requireString("label")
            try optionalString("role", values: ["normal", "destructive", "cancel"])
        case .textField:
            allowed.formUnion(["label", "value"])
            try requireString("label"); try requireString("value")
        case .toggle:
            allowed.formUnion(["label", "value"])
            try requireString("label")
            guard node.properties["value"]?.bool != nil else { throw UIValidationError.invalidProperty(node: node.id, key: "value") }
        case .vStack, .hStack, .zStack:
            allowed.formUnion(["spacing", "alignment"])
            if let value = node.properties["spacing"] {
                guard node.kind != .zStack, let number = value.number, (0...256).contains(number) else {
                    throw UIValidationError.invalidProperty(node: node.id, key: "spacing")
                }
            }
            let alignments: Set<String> = switch node.kind {
            case .vStack: ["leading", "center", "trailing"]
            case .hStack: ["top", "center", "bottom", "firstTextBaseline", "lastTextBaseline"]
            default: ["center", "leading", "trailing", "top", "bottom", "topLeading", "topTrailing", "bottomLeading", "bottomTrailing"]
            }
            try optionalString("alignment", values: alignments)
        case .section, .navigation:
            allowed.insert("title"); try optionalString("title")
        case .list: break
        }
        if let key = node.properties.keys.first(where: { !allowed.contains($0) }) {
            throw UIValidationError.invalidProperty(node: node.id, key: key)
        }
    }

    private func validateStructure(of node: UINode) throws {
        switch node.kind {
        case .text, .button, .textField, .toggle:
            guard node.children.isEmpty else { throw UIValidationError.invalidChildren(node.id) }
        case .navigation:
            guard node.children.count == 1 else { throw UIValidationError.invalidChildren(node.id) }
        default: break
        }
    }

    private func permittedEvents(for kind: NodeKind) -> Set<UIEventKind> {
        switch kind {
        case .button: [.activate]
        case .textField: [.textChange, .submit]
        case .toggle: [.valueChange]
        default: []
        }
    }

    private func requiredEvents(for kind: NodeKind) -> Set<UIEventKind> {
        switch kind {
        case .button: [.activate]
        case .textField: [.textChange]
        case .toggle: [.valueChange]
        default: []
        }
    }
}

func validIdentifier(_ value: String) -> Bool {
    !value.isEmpty && value.utf8.count <= 128
        && !value.unicodeScalars.contains { $0.value < 0x20 || $0.value == 0x7f }
}
