public struct UINodeIdentity: Codable, Hashable, Sendable {
    public let id: String
    public let generation: UInt64

    public init(id: String, generation: UInt64) { self.id = id; self.generation = generation }
}

public struct UIEventEnvelope: Codable, Equatable, Sendable {
    public let revision: UInt64
    public let identity: UINodeIdentity
    public let event: UIEventKind
    public let value: UIValue

    public init(revision: UInt64, identity: UINodeIdentity, event: UIEventKind, value: UIValue = .null) {
        self.revision = revision; self.identity = identity; self.event = event; self.value = value
    }
}

public struct RoutedUIAction: Codable, Equatable, Sendable {
    public let revision: UInt64
    public let nodeID: String
    public let actionID: String
    public let event: UIEventKind
    public let value: UIValue
}

public enum UIRoutingError: Error, Equatable, Sendable {
    case staleRevision
    case staleIdentity
    case disabledNode
    case unboundEvent
    case invalidValue
}

public enum UIReconciliationError: Error, Equatable, Sendable {
    case noDocument
    case revisionNotIncreasing
    case identitySpaceExhausted
}

public struct UINodeMove: Equatable, Sendable {
    public let id: String
    public let fromParent: String?
    public let toParent: String?
    public let fromIndex: Int
    public let toIndex: Int
}

/// Property/action changes are separate from structural insert/remove/reorder changes.
/// An ID whose kind changes is replaced and receives a new native identity.
public struct UIChangeSet: Equatable, Sendable {
    public let inserted: [String]
    public let removed: [String]
    public let replaced: [String]
    public let updated: [String]
    public let moved: [UINodeMove]
}

struct ReconciledNode: Sendable {
    let node: UINode
    let identity: UINodeIdentity
    let parent: String?
    let index: Int
    let disabled: Bool
}

/// An immutable render receipt. Its constructor is internal so a renderer can only
/// receive a validated, fully indexed tree.
public struct UIRenderSnapshot: Sendable {
    public let document: UIDocument
    public var nodeCount: Int { nodes.count }
    let nodes: [String: ReconciledNode]
    let maximumStringBytes: Int

    public func identity(for nodeID: String) -> UINodeIdentity? { nodes[nodeID]?.identity }

    /// Bindings come from the current node, never from a caller-supplied action ID.
    public func route(_ envelope: UIEventEnvelope) throws -> RoutedUIAction {
        guard envelope.revision == document.revision else { throw UIRoutingError.staleRevision }
        guard let record = nodes[envelope.identity.id], record.identity == envelope.identity else {
            throw UIRoutingError.staleIdentity
        }
        guard !record.disabled else { throw UIRoutingError.disabledNode }
        guard let action = record.node.actions.first(where: { $0.event == envelope.event }) else {
            throw UIRoutingError.unboundEvent
        }
        switch (envelope.event, envelope.value) {
        case (.activate, .null), (.submit, .null), (.valueChange, .bool): break
        case let (.textChange, .string(text)):
            guard text.utf8.count <= maximumStringBytes else { throw UIRoutingError.invalidValue }
        default: throw UIRoutingError.invalidValue
        }
        return RoutedUIAction(revision: document.revision, nodeID: record.node.id,
                              actionID: action.id, event: action.event, value: envelope.value)
    }
}

/// Owns identity and reconciles a whole validated batch atomically. Failed validation,
/// replayed revisions and identity exhaustion leave the last snapshot intact.
public struct UIReconciler: Sendable {
    public let validator: UIValidator
    public private(set) var snapshot: UIRenderSnapshot?
    private var nextGeneration: UInt64 = 0

    public init(validator: UIValidator = UIValidator()) { self.validator = validator }

    public func currentSnapshot() throws -> UIRenderSnapshot {
        guard let snapshot else { throw UIReconciliationError.noDocument }
        return snapshot
    }

    @discardableResult
    public mutating func apply(_ document: UIDocument) throws -> UIChangeSet {
        _ = try validator.validate(document)
        if let snapshot, document.revision <= snapshot.document.revision {
            throw UIReconciliationError.revisionNotIncreasing
        }
        let previous = snapshot?.nodes ?? [:]
        var records: [String: ReconciledNode] = [:]
        var generation = nextGeneration
        var inserted: [String] = [], replaced: [String] = [], updated: [String] = []
        var moved: [UINodeMove] = []
        var pending: [(UINode, String?, Int, Bool)] = [(document.root, nil, 0, false)]
        while let (node, parent, index, ancestorDisabled) = pending.popLast() {
            let identity: UINodeIdentity
            if let old = previous[node.id], old.node.kind == node.kind {
                identity = old.identity
                if old.node.properties != node.properties || old.node.actions != node.actions {
                    updated.append(node.id)
                }
                if old.parent != parent || old.index != index {
                    moved.append(UINodeMove(id: node.id, fromParent: old.parent, toParent: parent,
                                            fromIndex: old.index, toIndex: index))
                }
            } else {
                guard generation < UInt64.max else { throw UIReconciliationError.identitySpaceExhausted }
                generation += 1
                identity = UINodeIdentity(id: node.id, generation: generation)
                if previous[node.id] == nil { inserted.append(node.id) } else { replaced.append(node.id) }
            }
            let disabled = ancestorDisabled || node.properties["disabled"]?.bool == true
            records[node.id] = ReconciledNode(node: node, identity: identity, parent: parent, index: index, disabled: disabled)
            for (childIndex, child) in node.children.enumerated().reversed() {
                pending.append((child, node.id, childIndex, disabled))
            }
        }
        let removed = previous.keys.filter { records[$0] == nil }.sorted()
        nextGeneration = generation
        snapshot = UIRenderSnapshot(document: document, nodes: records,
                                    maximumStringBytes: validator.limits.maximumStringBytes)
        return UIChangeSet(inserted: inserted, removed: removed, replaced: replaced, updated: updated, moved: moved)
    }
}
