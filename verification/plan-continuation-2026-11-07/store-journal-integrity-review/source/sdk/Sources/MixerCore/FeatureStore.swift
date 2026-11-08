import Foundation

/// Effects return actions, including error actions. Throwing work must translate its error
/// into the feature's action model; the store never silently discards an error.
public enum Effect<Action: Sendable>: Sendable {
    case run(id: String, operation: @Sendable () async -> Action?)
    case cancel(id: String)
    case cancelAll
}

/// A serialized, value-state feature runtime. Reducers run on the main actor. Effect
/// results from canceled/replaced work and stopped instances cannot enter the reducer.
@MainActor
public final class FeatureStore<State: Sendable, Action: Sendable> {
    public typealias Reducer = @MainActor @Sendable (inout State, Action) -> [Effect<Action>]
    public typealias Observer = @MainActor @Sendable (State) -> Void

    public private(set) var state: State
    public private(set) var lifecycle: FeatureLifecycle = .initialized
    public var runningEffectCount: Int { effects.count }

    private let reducer: Reducer
    private var effects: [String: RunningEffect] = [:]
    private var observers: [UUID: Observer] = [:]
    private var isDispatching = false

    private struct RunningEffect {
        let generation: UUID
        let task: Task<Void, Never>
    }

    public init(initialState: State, reducer: @escaping Reducer) {
        state = initialState
        self.reducer = reducer
    }

    deinit {
        for effect in effects.values { effect.task.cancel() }
    }

    public func transition(_ event: LifecycleEvent) throws {
        lifecycle = try lifecycle.applying(event)
        if lifecycle == .stopped { cancelAllEffects() }
    }

    public func send(_ action: Action) throws {
        guard lifecycle == .active || lifecycle == .background else {
            throw LifecycleError.featureNotRunning
        }
        guard !isDispatching else { throw LifecycleError.reentrantDispatch }
        isDispatching = true
        defer { isDispatching = false }
        let commands = reducer(&state, action)
        // A snapshot prevents observer registration/removal from invalidating iteration.
        let listeners = Array(observers.values)
        for listener in listeners { listener(state) }
        for command in commands { execute(command) }
    }

    /// Registering an observer delivers the current value immediately.
    @discardableResult
    public func observe(_ observer: @escaping Observer) -> UUID {
        let token = UUID()
        observers[token] = observer
        observer(state)
        return token
    }

    public func removeObserver(_ token: UUID) { observers.removeValue(forKey: token) }

    public func cancelEffect(id: String) {
        // Remove first: even an operation that ignores cancellation loses ownership.
        effects.removeValue(forKey: id)?.task.cancel()
    }

    public func cancelAllEffects() {
        let pending = effects.values
        effects.removeAll()
        for effect in pending { effect.task.cancel() }
    }

    /// Waits for the effects currently owned by this instance. Effects launched by their
    /// resulting actions are a later batch and are not included in this wait.
    public func awaitCurrentEffects() async {
        let pending = effects.values.map(\.task)
        for task in pending { await task.value }
    }

    private func execute(_ command: Effect<Action>) {
        switch command {
        case let .cancel(id): cancelEffect(id: id)
        case .cancelAll: cancelAllEffects()
        case let .run(id, operation):
            guard lifecycle == .active || lifecycle == .background else { return }
            cancelEffect(id: id)
            let generation = UUID()
            let task = Task { [weak self] in
                let result = await operation()
                guard !Task.isCancelled else { return }
                self?.complete(id: id, generation: generation, result: result)
            }
            effects[id] = RunningEffect(generation: generation, task: task)
        }
    }

    private func complete(id: String, generation: UUID, result: Action?) {
        guard effects[id]?.generation == generation else { return }
        effects.removeValue(forKey: id)
        guard let result, lifecycle == .active || lifecycle == .background else { return }
        // The lifecycle guard establishes the precondition of send.
        try? send(result)
    }
}
