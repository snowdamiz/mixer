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

enum RowKey: Hashable {
    case integer(Int)
    case string(String)

    init<Key>(_ key: Key) throws {
        if Key.self == Int.self, let integer = key as? Int {
            self = .integer(integer)
        } else if Key.self == String.self, let string = key as? String {
            guard fitsUTF8(string, limit: FeatureLimits.keyBytes) else {
                throw FeatureError.limitExceeded("row key bytes")
            }
            self = .string(string)
        } else {
            throw FeatureError.unsupportedRowKey
        }
    }
}

struct ViewPath: Hashable {
    enum Component: Hashable {
        case type(ObjectIdentifier)
        case child(Int)
        case branch(Bool)
        case row(RowKey)
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

    func lower<V: View>(_ view: V, at parent: ViewPath, into output: inout [UINode]) throws {
        guard visitedViews < FeatureLimits.visitedViews else {
            throw FeatureError.limitExceeded("visited views")
        }
        visitedViews += 1
        let path = try parent.appending(.type(ObjectIdentifier(V.self)))
        guard !(view is any CustomReflectable) else { throw FeatureError.customMirror }
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
        for field in mirror.children {
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
        if !declarations.isEmpty { turn.scope = StateScope(parent: parentScope, addresses: declarations) }
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

    func bindButton(_ action: @escaping () -> Void, nodeID: String) throws -> UIActionBinding {
        guard handlers.count < FeatureLimits.handlers else {
            throw FeatureError.limitExceeded("handlers")
        }
        let actionID = "a\(nodeID)"
        handlers[actionID] = StateHandler(scope: turn.scope, action: action)
        return UIActionBinding(id: actionID, event: .activate)
    }
}

private protocol PrimitiveView: View {
    func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws
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
        let binding = try evaluation.bindButton(action, nodeID: id)
        let node = UINode(id: id, kind: .button, properties: ["label": .string(title)], actions: [binding])
        try evaluation.append(node, into: &output)
    }
}

extension VStack: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        let id = try evaluation.nodeID(at: path)
        var children: [UINode] = []
        try evaluation.lower(content, at: path, into: &children)
        try evaluation.append(UINode(id: id, kind: .vStack, children: children), into: &output)
    }
}

extension ViewBuilder.ViewGroup: PrimitiveView {
    fileprivate func lower(in evaluation: ViewEvaluation, at path: ViewPath, into output: inout [UINode]) throws {
        for (index, child) in children.enumerated() {
            try evaluation.lower(child, at: path.appending(.child(index)), into: &output)
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
        var seen: Set<RowKey> = []
        var keys: [RowKey] = []
        for element in data {
            let key = try RowKey(element[keyPath: id])
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
