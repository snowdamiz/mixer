import MixerUI

enum FeatureLimits {
    static let visitedViews = 4_096
    static let pathComponents = 64
    static let fieldsPerView = 128
    static let declarationBytes = 128
    static let rowsPerLoop = 1_000
    static let keyBytes = 256
    static let stateCells = 1_024
    static let valueBytes = 1_024
    static let handlers = 1_024
}

func fitsUTF8(_ string: String, limit: Int) -> Bool {
    string.utf8.prefix(limit + 1).count <= limit
}

package enum ExplicitIdentityError: Error, Equatable, Sendable {
    case unsupportedKey
    case duplicateKey
}

enum ViewKey: Hashable {
    case integer(Int)
    case string(String)

    init?<Key>(_ key: Key) {
        if Key.self == Int.self, let integer = key as? Int {
            self = .integer(integer)
        } else if Key.self == String.self, let string = key as? String {
            self = .string(string)
        } else {
            return nil
        }
    }

    var fitsByteLimit: Bool {
        switch self {
        case .integer: true
        case let .string(string): fitsUTF8(string, limit: FeatureLimits.keyBytes)
        }
    }
}

struct ViewPath: Hashable {
    enum Component: Hashable {
        case type(ObjectIdentifier)
        case child(Int)
        case branch(Bool)
        case row(ViewKey)
        case explicit(ViewKey)
    }

    private var components: [Component] = []

    func appending(_ component: Component) throws -> Self {
        guard components.count < FeatureLimits.pathComponents else {
            throw FeatureError.limitExceeded("view path components")
        }
        var path = self
        path.components.append(component)
        return path
    }
}

struct NodeIdentities {
    var live: [ViewPath: String] = [:]
    var lastID: UInt64 = 0
}

final class ViewEvaluation {
    private let limits: UIValidationLimits
    private let previousCells: StateCells
    private let previousNodeIDs: [ViewPath: String]
    private var visitedViews = 0
    private var explicitPaths: Set<ViewPath> = []
    let turn: StateTurn
    private(set) var identities: NodeIdentities
    private(set) var handlers: [String: StateHandler] = [:]

    init(limits: UIValidationLimits, cells: StateCells, identities: NodeIdentities, turn: StateTurn) {
        self.limits = limits
        previousCells = cells
        previousNodeIDs = identities.live
        self.identities = NodeIdentities(lastID: identities.lastID)
        self.turn = turn
    }

    func document(from root: some View, revision: UInt64) throws -> UIDocument {
        var roots: [UINode] = []
        try lower(root, at: ViewPath(), into: &roots)
        guard roots.count == 1, let root = roots.first else { throw FeatureError.invalidRoot }
        return UIDocument(revision: revision, root: root)
    }

    func register<Value>(_ address: StateAddress, initial: Value) throws {
        guard turn.cells.count < FeatureLimits.stateCells else {
            throw FeatureError.limitExceeded("state cells")
        }
        guard turn.cells[address] == nil else { throw FeatureError.reusedState }
        let initialValue = try StateValue(initial)
        if let previous = previousCells[address] {
            guard previous.read(as: Value.self) != nil else { throw FeatureError.unsupportedState }
            turn.cells[address] = previous
        } else {
            turn.cells[address] = initialValue
        }
    }

    func lower(
        _ view: any View, at parent: ViewPath, childIndex: Int? = nil, into output: inout [UINode]
    ) throws {
        var content = view
        var disabled = false
        var accessibility: [String: UIValue] = [:]
        // These modifiers share their content's structural position, including an explicit key.
        while let modified = content as? any NodeModifyingView {
            try visit(content)
            switch modified.modifier {
            case let .disabled(value):
                disabled = disabled || value
            case let .accessibilityLabel(label):
                try setAccessibility(.string(label), key: "accessibilityLabel", in: &accessibility)
            case let .accessibilityHint(hint):
                try setAccessibility(.string(hint), key: "accessibilityHint", in: &accessibility)
            }
            content = modified.unmodifiedContent
        }
        try visit(content)
        let start = output.count
        try lowerView(content, at: parent, childIndex: childIndex, into: &output)
        if !accessibility.isEmpty {
            guard output.count - start == 1 else { throw FeatureError.unsupportedAccessibilityTarget }
            switch output[start].kind {
            case .text, .button, .textField, .toggle: break
            default: throw FeatureError.unsupportedAccessibilityTarget
            }
            for (key, value) in accessibility {
                try setAccessibility(value, key: key, in: &output[start].properties)
            }
        }
        if disabled {
            for index in start..<output.count {
                output[index].properties["disabled"] = .bool(true)
            }
        }
    }

    private func setAccessibility(_ value: UIValue, key: String, in properties: inout [String: UIValue]) throws {
        guard properties[key] == nil else { throw FeatureError.duplicateAccessibilityProperty(key) }
        properties[key] = value
    }

    private func visit(_ view: any View) throws {
        guard visitedViews < FeatureLimits.visitedViews else {
            throw FeatureError.limitExceeded("visited views")
        }
        visitedViews += 1
        guard !(view is any CustomReflectable) else { throw FeatureError.customMirror }
    }

    private func lowerView<V: View>(
        _ view: V, at parent: ViewPath, childIndex: Int?, into output: inout [UINode]
    ) throws {
        if let identified = view as? any ExplicitIdentityView {
            let path = try parent.appending(.explicit(identified.identityKey))
            guard explicitPaths.insert(path).inserted else { throw ExplicitIdentityError.duplicateKey }
            try identified.lower(in: self, at: path, into: &output)
            return
        }
        let slot = try childIndex.map { try parent.appending(.child($0)) } ?? parent
        let path = try slot.appending(.type(ObjectIdentifier(V.self)))
        if let primitive = view as? any PrimitiveView {
            try primitive.lower(in: self, at: path, into: &output)
            return
        }
        guard V.Body.self != Never.self, !(V.self is AnyClass) else { throw FeatureError.unsupportedView }
        let mirror = Mirror(reflecting: view)
        guard mirror.displayStyle == .struct, mirror.subjectType == V.self else {
            throw FeatureError.unsupportedView
        }
        guard mirror.children.count <= FeatureLimits.fieldsPerView else {
            throw FeatureError.limitExceeded("view fields")
        }
        let parentScope = turn.scope
        var declarations: [StateDeclarationIdentity: StateAddress] = [:]
        var environmentDeclarations: Set<EnvironmentDeclarationIdentity> = []
        for field in mirror.children {
            if let property = field.value as? any EnvironmentDeclaration {
                guard property.isSupported else { throw FeatureError.unsupportedEnvironment }
                environmentDeclarations.insert(property.identity)
                continue
            }
            guard let property = field.value as? any StateDeclaration else { continue }
            guard let label = field.label, !label.isEmpty, fitsUTF8(label, limit: FeatureLimits.declarationBytes) else {
                throw FeatureError.unsupportedState
            }
            let address = StateAddress(view: path, declaration: label)
            guard parentScope?.address(of: property.declaration) == nil,
                  declarations.updateValue(address, forKey: property.declaration) == nil else {
                throw FeatureError.reusedState
            }
            try property.register(address, in: self)
        }
        if !declarations.isEmpty || !environmentDeclarations.isEmpty {
            turn.scope = ViewScope(
                parent: parentScope, addresses: declarations, environmentDeclarations: environmentDeclarations
            )
        }
        defer { turn.scope = parentScope }
        let body = view.body
        try turn.checkWrites()
        try lower(body, at: path, into: &output)
    }

    func nodeID(at path: ViewPath) throws -> String {
        guard identities.live.count < limits.maximumNodes else {
            throw FeatureError.limitExceeded("rendered nodes")
        }
        let id: String
        if let previous = previousNodeIDs[path] {
            id = previous
        } else {
            guard identities.lastID < .max else { throw FeatureError.exhaustedNodeIDs }
            identities.lastID += 1
            id = "n\(identities.lastID)"
        }
        identities.live[path] = id
        return id
    }

    func append(_ node: UINode, into output: inout [UINode]) throws {
        guard output.count < limits.maximumChildrenPerNode else {
            throw FeatureError.limitExceeded("rendered siblings")
        }
        output.append(node)
    }

    func bind(_ action: StateAction, nodeID: String) throws -> UIActionBinding {
        guard handlers.count < FeatureLimits.handlers else {
            throw FeatureError.limitExceeded("handlers")
        }
        let actionID = "a\(nodeID)"
        handlers[actionID] = StateHandler(scope: turn.scope, action: action)
        return UIActionBinding(id: actionID, event: action.event)
    }

    func controlValue<Value>(_ binding: Binding<Value>) throws -> Value {
        guard binding.belongs(to: turn.access) else { throw FeatureError.unboundControl }
        return binding.wrappedValue
    }

    func lowerContainer<Content: View>(
        _ kind: NodeKind, properties: [String: UIValue] = [:], content: Content,
        at path: ViewPath, into output: inout [UINode]
    ) throws {
        let id = try nodeID(at: path)
        var children: [UINode] = []
        try lower(content, at: path, into: &children)
        try append(UINode(id: id, kind: kind, properties: properties, children: children), into: &output)
    }
}

private protocol NodeModifyingView: View {
    var modifier: NodeModifier { get }
    var unmodifiedContent: any View { get }
}

extension NodeModifiedView: NodeModifyingView {
    fileprivate var unmodifiedContent: any View { content }
}

private protocol PrimitiveView: View {
    func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws
}

private protocol ExplicitIdentityView: PrimitiveView {
    var identityKey: ViewKey { get throws }
}

extension IdentifiedView: ExplicitIdentityView {
    fileprivate var identityKey: ViewKey {
        get throws {
            guard let key = ViewKey(id) else { throw ExplicitIdentityError.unsupportedKey }
            guard key.fitsByteLimit else { throw FeatureError.limitExceeded("explicit key bytes") }
            return key
        }
    }

    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        try evaluation.lower(content, at: path, into: &output)
    }
}

extension Text: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        let id = try evaluation.nodeID(at: path)
        try evaluation.append(UINode(id: id, kind: .text, properties: ["text": .string(title)]), into: &output)
    }
}

extension Button: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        let id = try evaluation.nodeID(at: path)
        let binding = try evaluation.bind(.activate(action), nodeID: id)
        let node = UINode(id: id, kind: .button, properties: ["label": .string(title)], actions: [binding])
        try evaluation.append(node, into: &output)
    }
}

extension VStack: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        try evaluation.lowerContainer(.vStack, content: content, at: path, into: &output)
    }
}

extension HStack: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        var properties: [String: UIValue] = ["alignment": .string(alignment.wireValue)]
        if let spacing { properties["spacing"] = .number(Double(spacing)) }
        try evaluation.lowerContainer(.hStack, properties: properties, content: content, at: path, into: &output)
    }
}

extension List: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        try evaluation.lowerContainer(.list, content: content, at: path, into: &output)
    }
}

extension Section: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        let properties: [String: UIValue] = title.map { ["title": .string($0)] } ?? [:]
        try evaluation.lowerContainer(.section, properties: properties, content: content, at: path, into: &output)
    }
}

extension TextField: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        let value = try evaluation.controlValue(text)
        let id = try evaluation.nodeID(at: path)
        let action = try evaluation.bind(.textChange(text), nodeID: id)
        let node = UINode(id: id, kind: .textField, properties: ["label": .string(title), "value": .string(value)],
                          actions: [action])
        try evaluation.append(node, into: &output)
    }
}

extension Toggle: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        let value = try evaluation.controlValue(isOn)
        let id = try evaluation.nodeID(at: path)
        let action = try evaluation.bind(.valueChange(isOn), nodeID: id)
        let node = UINode(id: id, kind: .toggle, properties: ["label": .string(title), "value": .bool(value)],
                          actions: [action])
        try evaluation.append(node, into: &output)
    }
}

extension ViewBuilder.ViewGroup: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        for (index, child) in children.enumerated() {
            try evaluation.lower(child, at: path, childIndex: index, into: &output)
        }
    }
}

extension ViewBuilder.OptionalContent: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        if let content {
            try evaluation.lower(content, at: path.appending(.branch(true)), into: &output)
        }
    }
}

extension ViewBuilder.ConditionalContent: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        switch self {
        case let .first(content):
            try evaluation.lower(content, at: path.appending(.branch(true)), into: &output)
        case let .second(content):
            try evaluation.lower(content, at: path.appending(.branch(false)), into: &output)
        }
    }
}

extension ForEach: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        guard ID.self == Int.self || ID.self == String.self else { throw FeatureError.unsupportedRowKey }
        guard data.count <= FeatureLimits.rowsPerLoop else { throw FeatureError.limitExceeded("rows per loop") }
        var seen: Set<ViewKey> = []
        var keys: [ViewKey] = []
        for element in data {
            guard let key = ViewKey(element[keyPath: id]) else { throw FeatureError.unsupportedRowKey }
            guard key.fitsByteLimit else { throw FeatureError.limitExceeded("row key bytes") }
            try evaluation.turn.checkWrites()
            guard seen.insert(key).inserted else { throw FeatureError.duplicateRowKey }
            keys.append(key)
        }
        for (element, key) in zip(data, keys) {
            let content = content(element)
            try evaluation.turn.checkWrites()
            try evaluation.lower(content, at: path.appending(.row(key)), into: &output)
        }
    }
}
