#if canImport(Crypto)
import Foundation
import MixerUI

@_spi(FeatureUIV3) public enum SwiftFeatureFrontendRequest: Sendable, Equatable { case closeOwnedWindowAndStop, closeOwnedWindowAndHold }
@_spi(FeatureUIV3) public struct SwiftFeatureScopeResult: Sendable {
    public let primaryError: (any Error)?
    public let close: SwiftFeatureCloseOutcome
    public var frontendRequest: SwiftFeatureFrontendRequest {
        if case .retained = close { return .closeOwnedWindowAndHold }
        return .closeOwnedWindowAndStop
    }
}
@_spi(FeatureUIV3) public enum SwiftFeatureRetirementReason: Sendable { case ownerRequested, cancelled }
@_spi(FeatureUIV3) public enum SwiftFeatureActionRejection: Sendable, Equatable { case notActive, retiring, retired, overloaded, invalidOrStale }
@_spi(FeatureUIV3) public enum SwiftFeatureActionOutcome: Sendable {
    case acknowledged(UIRenderSnapshot), rejected(SwiftFeatureActionRejection), cancelledBeforeDispatch
    case retiring(SwiftFeatureRetirementTicket), terminal(SwiftFeatureScopeResult)
}
@_spi(FeatureUIV3) public enum SwiftFeatureActionCancellation: Sendable, Equatable { case removedBeforeDispatch, retirementRequested, alreadySettled }
@_spi(FeatureUIV3) public enum SwiftFeatureSubmission { case accepted(SwiftFeatureActionTicket), rejected(SwiftFeatureActionRejection) }
@_spi(FeatureUIV3) public enum SwiftFeatureRetirementState: Sendable {
    /// Runtime closure is an independent fact. Nil means it has not been consumed.
    case pending(runtimeClose: SwiftFeatureCloseOutcome?), terminal(SwiftFeatureScopeResult)
}

@MainActor private final class FeatureObservation<Value: Sendable> {
    private var result: Value?
    private var waiters: [UUID: CheckedContinuation<Value, any Error>] = [:]
    func settle(_ value: Value) {
        guard result == nil else { return }
        result = value
        let pending = Array(waiters.values); waiters.removeAll()
        for waiter in pending { waiter.resume(returning: value) }
    }
    func value() async throws -> Value {
        let id = UUID()
        return try await withTaskCancellationHandler {
            try Task.checkCancellation()
            if let result { return result }
            return try await withCheckedThrowingContinuation { continuation in
                if Task.isCancelled { continuation.resume(throwing: CancellationError()) }
                else { waiters[id] = continuation }
            }
        } onCancel: {
            Task { @MainActor in self.waiters.removeValue(forKey: id)?.resume(throwing: CancellationError()) }
        }
    }
}
@_spi(FeatureUIV3) @MainActor public final class SwiftFeatureActionTicket {
    fileprivate let id = UUID()
    private let observation = FeatureObservation<SwiftFeatureActionOutcome>()
    fileprivate var cancellation: (() -> SwiftFeatureActionCancellation)?
    fileprivate init() {}
    public func outcome() async throws -> SwiftFeatureActionOutcome { try await observation.value() }
    public func cancel() -> SwiftFeatureActionCancellation { cancellation?() ?? .alreadySettled }
    fileprivate func settle(_ outcome: SwiftFeatureActionOutcome) { cancellation = nil; observation.settle(outcome) }
}
@_spi(FeatureUIV3) @MainActor public final class SwiftFeatureRetirementTicket {
    public private(set) var state: SwiftFeatureRetirementState = .pending(runtimeClose: nil)
    private let observation = FeatureObservation<SwiftFeatureScopeResult>()
    fileprivate var custodian: SwiftFeatureOwnershipScope?
    fileprivate init() {}
    public func outcome() async throws -> SwiftFeatureScopeResult { try await observation.value() }
    fileprivate func settle(_ result: SwiftFeatureScopeResult) {
        state = .terminal(result); observation.settle(result); custodian = nil
    }
}

/// Root retains this scope before mounting. No destructor consumes a backend.
@_spi(FeatureUIV3) @MainActor public final class SwiftFeatureOwnershipScope {
    private enum State { case idle, mounting, active, retiring, terminal }
    private struct Entry { let action: IssuedUIAction; let ticket: SwiftFeatureActionTicket }
    private var state = State.idle
    private var session: SwiftFeatureSession?
    private var operationActive = false
    private var queue: [Entry] = [] // bounded to 64 waiting; never a settled-ticket history.
    private var active: Entry?
    private var drain: Task<Void, Never>?
    private var retirement: SwiftFeatureRetirementTicket?
    private var primaryError: (any Error)?
    private var teardown: (@MainActor (SwiftFeatureFrontendRequest) -> Void)?
    private var tornDown = false
    public private(set) var result: SwiftFeatureScopeResult?
    public init() {}

    public func mount(_ packet: Data, grant: ReviewedDevelopmentGrant,
        backend: any SwiftFeatureRuntimeFactory, presenter: any SwiftFeatureNativePresenter) async throws -> UIRenderSnapshot {
        guard state == .idle else { throw SwiftFeatureError.closed }
        state = .mounting; operationActive = true
        return try await withTaskCancellationHandler {
            do {
                let (exchange, startup) = try SwiftFeatureSession.prepare(packet, grant: grant)
                try Task.checkCancellation()
                switch backend.acquire(SwiftFeatureRuntimeRequest(packet: packet, profile: grant.executionProfile)) {
                case .refused(let error): throw error
                case .ready(let owner):
                    session = SwiftFeatureSession(exchange: exchange, startup: startup, lease: SwiftFeatureLease(owner), presenter: presenter)
                case .failedOwned(let owner, let cause):
                    session = SwiftFeatureSession(exchange: exchange, startup: startup, lease: SwiftFeatureLease(owner), presenter: presenter)
                    throw cause
                }
                try Task.checkCancellation()
                guard state == .mounting, let session else { throw CancellationError() }
                let snapshot = try await session.start()
                try Task.checkCancellation()
                guard state == .mounting else { throw CancellationError() }
                operationActive = false; state = .active; scheduleDrain()
                return snapshot
            } catch {
                let acquired = session != nil
                _ = beginRetirement(error)
                operationActive = false; completeRetirementIfQuiescent()
                if acquired, let result { throw SwiftFeatureFailure(cause: result.primaryError ?? error, close: result.close) }
                throw error
            }
        } onCancel: { Task { @MainActor in _ = self.beginRetirement(CancellationError()) } }
    }

    /// Admission is synchronous, including callbacks reentered during startup/display.
    public func submit(_ action: IssuedUIAction) -> SwiftFeatureSubmission {
        switch state {
        case .idle: return .rejected(.notActive)
        case .retiring: return .rejected(.retiring)
        case .terminal: return .rejected(.retired)
        case .mounting, .active: break
        }
        guard queue.count < 64 else { _ = beginRetirement(SwiftFeatureError.overloaded); return .rejected(.overloaded) }
        let ticket = SwiftFeatureActionTicket()
        ticket.cancellation = { [weak self, weak ticket] in
            guard let self, let ticket else { return .alreadySettled }
            return self.cancel(ticket)
        }
        queue.append(Entry(action: action, ticket: ticket)); scheduleDrain()
        return .accepted(ticket)
    }

    public func finish(_ reason: SwiftFeatureRetirementReason,
        teardown: @escaping @MainActor (SwiftFeatureFrontendRequest) -> Void) -> SwiftFeatureRetirementTicket {
        if self.teardown == nil { self.teardown = teardown }
        let ticket = beginRetirement(reason == .cancelled ? CancellationError() : nil)
        performTeardownIfTerminal()
        return ticket
    }

    private func cancel(_ ticket: SwiftFeatureActionTicket) -> SwiftFeatureActionCancellation {
        if let index = queue.firstIndex(where: { $0.ticket === ticket }) {
            queue.remove(at: index).ticket.settle(.cancelledBeforeDispatch)
            return .removedBeforeDispatch
        }
        if active?.ticket === ticket { _ = beginRetirement(CancellationError()); return .retirementRequested }
        return .alreadySettled
    }
    private func scheduleDrain() {
        guard state == .active, !operationActive, drain == nil, !queue.isEmpty else { return }
        drain = Task { @MainActor in await self.drainQueue() }
    }
    private func drainQueue() async {
        while state == .active, !queue.isEmpty {
            await Task.yield() // Cancellation/retirement gets a scheduling opportunity per turn.
            guard state == .active, !queue.isEmpty, let session else { break }
            let entry = queue.removeFirst(); active = entry; operationActive = true
            do {
                let snapshot = try await session.send(entry.action)
                if state == .active { entry.ticket.settle(.acknowledged(snapshot)) }
            } catch SwiftFeatureInputRefusal.invalidOrStale {
                if state == .active { entry.ticket.settle(.rejected(.invalidOrStale)) }
            } catch { _ = beginRetirement(error) }
            operationActive = false
            if state == .retiring {
                completeRetirementIfQuiescent()
                if let result { entry.ticket.settle(.terminal(result)) }
            }
            active = nil
        }
        drain = nil
        completeRetirementIfQuiescent()
    }
    @discardableResult private func beginRetirement(_ error: (any Error)?) -> SwiftFeatureRetirementTicket {
        if let retirement {
            if state != .terminal, primaryError == nil, let error, !(error is CancellationError) { primaryError = error }
            return retirement
        }
        if primaryError == nil { primaryError = error }
        let ticket = SwiftFeatureRetirementTicket(); retirement = ticket; ticket.custodian = self
        state = .retiring
        let pending = queue; queue.removeAll(keepingCapacity: true)
        for entry in pending { entry.ticket.settle(.retiring(ticket)) }
        session?.cancelPresentation()
        completeRetirementIfQuiescent()
        return ticket
    }
    private func completeRetirementIfQuiescent() {
        guard state == .retiring, !operationActive, let retirement else { return }
        let close = session?.consume() ?? .notAcquired
        session = nil
        let completed = SwiftFeatureScopeResult(primaryError: primaryError, close: close)
        result = completed; state = .terminal
        retirement.settle(completed)
        performTeardownIfTerminal()
    }
    private func performTeardownIfTerminal() {
        guard !tornDown, let result, let teardown else { return }
        tornDown = true; self.teardown = nil; teardown(result.frontendRequest)
    }
}
#endif
