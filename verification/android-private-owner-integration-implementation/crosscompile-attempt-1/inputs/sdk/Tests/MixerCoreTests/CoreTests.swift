import Foundation
import Testing
@testable import MixerCore

@Test func lifecycleRejectsInvalidTransitions() throws {
    #expect(throws: LifecycleError.invalidTransition(.initialized, .enterForeground)) {
        try FeatureLifecycle.initialized.applying(.enterForeground)
    }
    var state = try FeatureLifecycle.initialized.applying(.start)
    state = try state.applying(.enterBackground)
    state = try state.applying(.enterForeground)
    state = try state.applying(.stop)
    #expect(state == .stopped)
    #expect(throws: LifecycleError.invalidTransition(.stopped, .start)) { try state.applying(.start) }
}

private actor EffectGate {
    private var started: Set<Int> = []
    private var startWaiters: [Int: [CheckedContinuation<Void, Never>]] = [:]
    private var pending: [Int: CheckedContinuation<Int, Never>] = [:]

    func run(_ key: Int) async -> Int {
        // This intentionally ignores cancellation: the store must still prevent delivery.
        await withCheckedContinuation { continuation in
            pending[key] = continuation
            started.insert(key)
            for waiter in startWaiters.removeValue(forKey: key) ?? [] { waiter.resume() }
        }
    }

    func waitUntilStarted(_ key: Int) async {
        if started.contains(key) { return }
        await withCheckedContinuation { startWaiters[key, default: []].append($0) }
    }

    func release(_ key: Int, value: Int) { pending.removeValue(forKey: key)?.resume(returning: value) }
}

private enum StoreAction: Sendable { case load(Int), loaded(Int), increment, cancel }
private struct StoreState: Sendable { var value = 0; var received: [Int] = [] }

@MainActor
@Test func reducerEffectsReplaceAndCancelWithoutStaleDelivery() async throws {
    let gate = EffectGate()
    let store = FeatureStore<StoreState, StoreAction>(initialState: StoreState()) { state, action in
        switch action {
        case let .load(key): return [.run(id: "load") { .loaded(await gate.run(key)) }]
        case let .loaded(value): state.value = value; state.received.append(value)
        case .increment: state.value += 1
        case .cancel: return [.cancel(id: "load")]
        }
        return []
    }
    #expect(throws: LifecycleError.featureNotRunning) { try store.send(.increment) }
    try store.transition(.start)
    try store.send(.load(1))
    await gate.waitUntilStarted(1)
    try store.send(.load(2))
    await gate.waitUntilStarted(2)
    await gate.release(1, value: 100)
    await gate.release(2, value: 20)
    await store.awaitCurrentEffects()
    #expect(store.state.value == 20)
    #expect(store.state.received == [20])
    #expect(store.runningEffectCount == 0)

    try store.send(.load(3))
    await gate.waitUntilStarted(3)
    try store.send(.cancel)
    await gate.release(3, value: 300)
    try store.send(.increment)
    #expect(store.state.value == 21)
    #expect(store.runningEffectCount == 0)
    try store.send(.load(4))
    await gate.waitUntilStarted(4)
    try store.transition(.stop)
    await gate.release(4, value: 400)
    #expect(store.state.received == [20])
    #expect(store.runningEffectCount == 0)
    #expect(throws: LifecycleError.featureNotRunning) { try store.send(.increment) }
}

@MainActor
@Test func observersAreValueSnapshotsAndReentrantDispatchIsRejected() throws {
    let store = FeatureStore<Int, Int>(initialState: 0) { state, action in state += action; return [] }
    try store.transition(.start)
    var snapshots: [Int] = []
    var rejected = false
    let token = store.observe { value in
        snapshots.append(value)
        if value == 1 {
            do { try store.send(10) }
            catch { rejected = error as? LifecycleError == .reentrantDispatch }
        }
    }
    try store.send(1)
    store.removeObserver(token)
    try store.send(2)
    #expect(snapshots == [0, 1])
    #expect(rejected)
    #expect(store.state == 3)
}

@Test func resourcesRejectStaleForeignAndClosedHandles() async throws {
    let registry = try ResourceRegistry<String>(owner: "session.1.photos", capacity: 1)
    let old = try await registry.insert("photo-a")
    #expect(try await registry.value(for: old) == "photo-a")
    await #expect(throws: ResourceError.capacityExceeded) { try await registry.insert("overflow") }
    #expect(try await registry.remove(old) == "photo-a")
    let current = try await registry.insert("photo-b")
    #expect(current.slot == old.slot)
    #expect(current.generation > old.generation)
    await #expect(throws: ResourceError.staleHandle) { try await registry.value(for: old) }
    let foreign = ResourceHandle(owner: "another-session", slot: current.slot, generation: current.generation)
    await #expect(throws: ResourceError.invalidOwner) { try await registry.value(for: foreign) }
    await registry.close()
    await #expect(throws: ResourceError.registryClosed) { try await registry.value(for: current) }
}

@Test func navigationRoundTripsAndRejectsVersionOrIdentityLoss() throws {
    var state = try NavigationState(routes: [NavigationRoute(id: "project.42", name: "project", parameters: ["title": "Café 🏗️"])])
    try state.push(NavigationRoute(id: "entry.7", name: "editor", parameters: ["draft": "7"]))
    #expect(try NavigationState.restore(from: state.encoded()) == state)
    #expect(throws: NavigationError.duplicateIdentity("entry.7")) {
        try state.push(NavigationRoute(id: "entry.7", name: "other"))
    }
    #expect(state.routes.count == 2)
    #expect(state.pop()?.id == "entry.7")
    state.popToRoot()
    #expect(state.routes.isEmpty)
    let newer = Data(#"{"schemaVersion":2,"routes":[]}"#.utf8)
    #expect(throws: NavigationError.unsupportedSchema(2)) { try NavigationState.restore(from: newer) }
    #expect(throws: NavigationError.oversizedRepresentation) { try NavigationState.restore(from: newer, maximumBytes: 1) }
    #expect(throws: NavigationError.oversizedRepresentation) {
        try NavigationState(routes: (0...64).map { NavigationRoute(id: "r\($0)", name: "entry") })
    }
}
