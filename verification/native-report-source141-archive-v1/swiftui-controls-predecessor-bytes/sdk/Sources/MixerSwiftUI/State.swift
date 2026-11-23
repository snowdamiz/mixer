import Foundation

@propertyWrapper
public struct State<Value> {
    private let initial: Value
    let declaration = StateDeclarationIdentity()

    public init(wrappedValue: Value) {
        initial = wrappedValue
    }

    public var wrappedValue: Value {
        get {
            guard let turn = StateTurn.active, let address = turn.scope?.address(of: declaration) else {
                return initial
            }
            return turn.cells[address]?.read(as: Value.self) ?? initial
        }
        nonmutating set {
            guard let turn = StateTurn.active else {
                if !StateTurn.hasContext { declaration.noteUnboundWrite() }
                return
            }
            if let address = turn.scope?.address(of: declaration) {
                turn.write(newValue, at: address, in: turn.access)
            } else if turn.phase == .build {
                turn.refuseBuildWrite()
            }
        }
    }

    /// A projection reads the draft in its frame's active turn and the
    /// committed cell between turns while that frame is accepted. A stale
    /// projection reads the value from the moment it was captured.
    public var projectedValue: Binding<Value> {
        guard let turn = StateTurn.active, let address = turn.scope?.address(of: declaration) else {
            let initial = self.initial
            return Binding(get: { initial }, set: { _ in })
        }
        let captured = turn.cells[address]?.read(as: Value.self) ?? initial
        return Binding(
            get: { [weak access = turn.access] in access?.read(address, as: Value.self) ?? captured },
            set: { [weak access = turn.access] value in
                guard let access else { return }
                StateTurn.active?.write(value, at: address, in: access)
            }
        )
    }
}

@propertyWrapper
public struct Binding<Value> {
    private let get: () -> Value
    private let set: (Value) -> Void

    fileprivate init(get: @escaping () -> Value, set: @escaping (Value) -> Void) {
        self.get = get
        self.set = set
    }

    public var wrappedValue: Value {
        get { get() }
        nonmutating set { set(newValue) }
    }

    public var projectedValue: Self { self }
}

extension State: StateDeclaration {
    func register(_ address: StateAddress, in evaluation: ViewEvaluation) throws {
        try declaration.install {
            try evaluation.register(address, initial: initial)
        }
    }
}

protocol StateDeclaration {
    var declaration: StateDeclarationIdentity { get }
    func register(_ address: StateAddress, in evaluation: ViewEvaluation) throws
}

/// Copies share declaration identity. Addresses belong to a view's scope.
final class StateDeclarationIdentity: Hashable {
    private enum Setup { case fresh, unboundWrite, installed }

    private let lock = NSLock()
    private var setup = Setup.fresh

    static func == (lhs: StateDeclarationIdentity, rhs: StateDeclarationIdentity) -> Bool { lhs === rhs }
    func hash(into hasher: inout Hasher) { hasher.combine(ObjectIdentifier(self)) }

    func noteUnboundWrite() {
        lock.withLock {
            if setup == .fresh { setup = .unboundWrite }
        }
    }

    func install(_ register: () throws -> Void) throws {
        try lock.withLock {
            guard setup != .unboundWrite else { throw FeatureError.stateWriteDuringBuild }
            try register()
            setup = .installed
        }
    }
}

struct StateAddress: Hashable {
    let view: ViewPath
    let declaration: String
}

// Only the engine decides which types have value semantics.
enum StateValue {
    case integer(Int)
    case boolean(Bool)
    case string(String)

    init<Value>(_ value: Value) throws(FeatureError) {
        if Value.self == Int.self, let integer = value as? Int {
            self = .integer(integer)
        } else if Value.self == Bool.self, let boolean = value as? Bool {
            self = .boolean(boolean)
        } else if Value.self == String.self, let string = value as? String {
            guard fitsUTF8(string, limit: FeatureLimits.valueBytes) else {
                throw FeatureError.limitExceeded("state value bytes")
            }
            self = .string(string)
        } else {
            throw FeatureError.unsupportedState
        }
    }

    func read<Value>(as type: Value.Type) -> Value? {
        switch self {
        case let .integer(value): value as? Value
        case let .boolean(value): value as? Value
        case let .string(value): value as? Value
        }
    }
}

typealias StateCells = [StateAddress: StateValue]

struct StateHandler {
    let scope: StateScope?
    let action: () -> Void
}

final class StateScope {
    private let parent: StateScope?
    private let addresses: [StateDeclarationIdentity: StateAddress]

    init(parent: StateScope?, addresses: [StateDeclarationIdentity: StateAddress]) {
        self.parent = parent
        self.addresses = addresses
    }

    func address(of declaration: StateDeclarationIdentity) -> StateAddress? {
        addresses[declaration] ?? parent?.address(of: declaration)
    }
}

/// The unique publisher for one frame on one mount.
final class StateAccess {
    private let lock = NSLock()
    private var published: StateCells?

    var acceptedCells: StateCells {
        lock.withLock { published ?? [:] }
    }

    func publish(_ cells: StateCells) {
        lock.withLock { published = cells }
    }

    func retire() {
        lock.withLock { published = nil }
    }

    func read<Value>(_ address: StateAddress, as type: Value.Type) -> Value? {
        if let turn = StateTurn.active, turn.access === self {
            return turn.cells[address]?.read(as: type)
        }
        return lock.withLock { published?[address]?.read(as: type) }
    }
}

/// Build and event drafts live only in the synchronous turn that opened them.
final class StateTurn {
    enum Phase { case build, event }

    // A child task can inherit the lease. The unsafe task reference stays valid
    // until revocation, which precedes return from withUnsafeCurrentTask.
    private final class Lease: @unchecked Sendable {
        private struct Authorization {
            let task: UnsafeCurrentTask?
            let turn: StateTurn
        }

        private let lock = NSLock()
        private var authorization: Authorization?

        init(task: UnsafeCurrentTask?, turn: StateTurn) {
            authorization = Authorization(task: task, turn: turn)
        }

        var activeTurn: StateTurn? {
            let turn = lock.withLock { () -> StateTurn? in
                guard let authorization else { return nil }
                return withUnsafeCurrentTask { task in
                    task == authorization.task ? authorization.turn : nil
                }
            }
            // A synchronous handoff can keep the same task or have no task at all.
            guard let turn, turn.executor.isCurrent() else { return nil }
            return turn
        }

        func revoke() {
            lock.withLock { authorization = nil }
        }
    }

    private static let context = TaskLocal<Lease?>(wrappedValue: nil)
    static var hasContext: Bool { context.get() != nil }
    static var active: StateTurn? { context.get()?.activeTurn }

    let access: StateAccess
    let phase: Phase
    private let executor: FeatureExecutor
    var cells: StateCells
    var scope: StateScope?
    private var writeError: FeatureError?

    private init(
        _ access: StateAccess, executor: FeatureExecutor, phase: Phase, cells: StateCells, scope: StateScope?
    ) {
        self.access = access
        self.executor = executor
        self.phase = phase
        self.cells = cells
        self.scope = scope
    }

    static func run<Result>(
        _ access: StateAccess, executor: FeatureExecutor, phase: Phase,
        cells: StateCells = [:], scope: StateScope? = nil,
        _ operation: (StateTurn) throws -> Result
    ) rethrows -> Result {
        try withUnsafeCurrentTask { task in
            let turn = StateTurn(access, executor: executor, phase: phase, cells: cells, scope: scope)
            let lease = Lease(task: task, turn: turn)
            defer { lease.revoke() }
            return try context.withValue(lease) { try operation(turn) }
        }
    }

    func refuseBuildWrite() {
        writeError = .stateWriteDuringBuild
    }

    func write<Value>(_ value: Value, at address: StateAddress, in publisher: StateAccess) {
        switch phase {
        case .build:
            refuseBuildWrite()
        case .event:
            guard access === publisher, writeError == nil else { return }
            do throws(FeatureError) {
                guard cells[address]?.read(as: Value.self) != nil else { throw FeatureError.unsupportedState }
                cells[address] = try StateValue(value)
            } catch {
                writeError = error
            }
        }
    }

    func checkWrites() throws(FeatureError) {
        if let writeError { throw writeError }
    }
}
