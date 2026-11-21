import Foundation
import os
import Testing

// A scripted response is registered by URLProtocol before the test runs the newer writer.
final class StoreReconciliationRequestHold: Sendable {
    private enum State {
        case waiting
        case held(DispatchTime, @Sendable (URLError?) -> Void)
        case retired
    }

    private let state = OSAllocatedUnfairLock(initialState: State.waiting)
    private let changed = DispatchSemaphore(value: 0)

    func hold(_ respond: @escaping @Sendable (URLError?) -> Void) {
        let accepted = state.withLock { state in
            guard case .waiting = state else { return false }
            state = .held(.now() + 5, respond)
            return true
        }
        if accepted {
            changed.signal()
        } else {
            respond(URLError(.cancelled))
        }
    }

    private var isHeld: Bool {
        state.withLock { state in
            if case .held = state { return true }
            return false
        }
    }

    private func finish(deliver: Bool) -> Bool {
        let held = state.withLock { state -> (DispatchTime, @Sendable (URLError?) -> Void)? in
            defer { state = .retired }
            guard case let .held(deadline, respond) = state else { return nil }
            return (deadline, respond)
        }
        guard let (deadline, respond) = held else { return false }
        guard deliver else {
            respond(URLError(.cancelled))
            return false
        }
        guard DispatchTime.now() <= deadline else {
            respond(URLError(.timedOut))
            return false
        }
        respond(nil)
        return true
    }

    func run<Report: Sendable>(
        old: @escaping @Sendable () throws -> Report,
        retireScript: () -> Void,
        whileHeld: () throws -> Void
    ) throws -> Report {
        let worker = OSAllocatedUnfairLock(initialState: Worker<Report>.pending)
        let done = DispatchGroup()
        done.enter()
        // The synchronous query waits for URLSession. Give it a separate thread.
        Thread {
            defer { done.leave() }
            let admitted = worker.withLock { state in
                guard case .pending = state else { return false }
                state = .running
                return true
            }
            guard admitted else { return }
            let result = Result { try old() }
            worker.withLock { $0 = .finished(result) }
            self.changed.signal()
        }.start()

        var attemptedJoin = false
        defer {
            if !attemptedJoin {
                worker.withLock { state in
                    if case .pending = state { state = .cancelled }
                }
                _ = finish(deliver: false)
                if done.wait(timeout: .now() + 5) != .success {
                    retireScript()
                    Issue.record("Old reconciliation worker did not exit during fixture cleanup")
                }
            }
        }

        if changed.wait(timeout: .now() + 5) != .success {
            let stage = worker.withLock { state in
                if case .pending = state { return "worker never entered" }
                return "worker entered"
            }
            throw StoreRequestHoldFailure("Old reconciliation request did not reach URLProtocol within five seconds (\(stage))")
        }
        try #require(isHeld, "Old reconciliation worker returned before URLProtocol held its request")
        try whileHeld()
        try #require(finish(deliver: true), "Newer reconciliation work exceeded the held-response deadline")
        attemptedJoin = true
        if done.wait(timeout: .now() + 5) != .success {
            retireScript()
            throw StoreRequestHoldFailure("Old reconciliation worker did not finish after the held response was delivered")
        }
        let result = worker.withLock { state -> Result<Report, any Error>? in
            guard case let .finished(result) = state else { return nil }
            return result
        }
        return try #require(result).get()
    }

    private enum Worker<Report: Sendable> {
        case pending
        case running
        case finished(Result<Report, any Error>)
        case cancelled
    }
}

private struct StoreRequestHoldFailure: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}
