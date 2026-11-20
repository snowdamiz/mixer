import Foundation

@MainActor
private final class EffectGate {
    private var pending: [Int: CheckedContinuation<Void, Never>] = [:]
    private var started: [Int: CheckedContinuation<Void, Never>] = [:]
    private(set) var returned: [Int: Bool] = [:]

    func result(_ value: Int) async -> Int {
        // The operation returns an action even when the task has been cancelled.
        await withCheckedContinuation { continuation in
            pending[value] = continuation
            started.removeValue(forKey: value)?.resume()
        }
        returned[value] = Task.isCancelled
        return value
    }

    func waitUntilPending(_ value: Int) async {
        if pending[value] != nil { return }
        await withCheckedContinuation { started[value] = $0 }
    }

    func release(_ value: Int) {
        guard let continuation = pending.removeValue(forKey: value) else {
            preconditionFailure("effect \(value) was not pending")
        }
        continuation.resume()
    }
}

private enum Action: Sendable {
    case start(Int)
    case finished(Int)
    case cancel
}

private struct Observation: Encodable {
    let joined: [Int]
    let returnedAfterCancellation: [Int]
    let reducerDeliveries: [Int]
}

@main
private enum EffectCompletion {
    @MainActor
    static func main() async throws {
        let gate = EffectGate()
        let store = FeatureStore<[Int], Action>(initialState: []) { state, action in
            switch action {
            case let .start(value):
                return [.run(id: "load") { .finished(await gate.result(value)) }]
            case let .finished(value):
                state.append(value)
                return []
            case .cancel:
                return [.cancel(id: "load")]
            }
        }

        func startAndCapture(_ value: Int) async throws -> Task<Void, Never> {
            try store.send(.start(value))
            await gate.waitUntilPending(value)
            precondition(store.runningEffectCount == 1)
            // Both calls run on MainActor. The waiter captures the pending store task
            // before yielding at its join, while the gate still holds the operation.
            return Task.immediate { @MainActor in
                await store.awaitCurrentEffects()
            }
        }

        func releaseAndJoin(_ value: Int, _ waiter: Task<Void, Never>, cancelled: Bool) async {
            gate.release(value)
            await waiter.value
            precondition(gate.returned[value] == cancelled)
        }

        try store.transition(.start)
        let replaced = try await startAndCapture(1)
        let replacement = try await startAndCapture(2)
        await releaseAndJoin(1, replaced, cancelled: true)
        precondition(store.state.isEmpty && store.runningEffectCount == 1)
        await releaseAndJoin(2, replacement, cancelled: false)
        precondition(store.state == [2] && store.runningEffectCount == 0)

        let cancelled = try await startAndCapture(3)
        try store.send(.cancel)
        precondition(store.runningEffectCount == 0)
        await releaseAndJoin(3, cancelled, cancelled: true)
        precondition(store.state == [2])

        let stopped = try await startAndCapture(4)
        try store.transition(.stop)
        precondition(store.lifecycle == .stopped && store.runningEffectCount == 0)
        await releaseAndJoin(4, stopped, cancelled: true)
        precondition(store.state == [2])

        let observation = Observation(joined: gate.returned.keys.sorted(),
                                      returnedAfterCancellation: gate.returned.keys.filter {
                                          gate.returned[$0] == true
                                      }.sorted(),
                                      reducerDeliveries: store.state)
        print(String(decoding: try JSONEncoder().encode(observation), as: UTF8.self))
    }
}
