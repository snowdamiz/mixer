import Foundation
import MixerCapabilities

/// Trusted implementation sink: O(1), nonblocking, nonreentrant latch/update only.
/// It supplies no execution, release or health authority.
@_spi(CapabilityLifecycle)
public protocol CapabilityBridgeTerminalObserver: Sendable {
    func recordTerminalFailure(_ failure: ExperimentalCapabilityFailure)
}
@_spi(CapabilityLifecycle)
public protocol CapabilityBridgeRetirementObserver: Sendable {
    func recordRetired()
}

/// A single concrete group. Its private caller must reserve a counted whole
/// attempt before constructing these adapters, including partially opened setup.
@_spi(CapabilityLifecycle)
public final class OwnedCapabilityAdapterGroup: @unchecked Sendable {
    let core: AdapterCloseCore
    public init(http: URLSessionHTTPTransport? = nil, storage: AppPrivateKeyValueStore? = nil,
                terminal: any CapabilityBridgeTerminalObserver,
                retirement: any CapabilityBridgeRetirementObserver) {
        core = AdapterCloseCore(http: http, storage: storage, terminal: terminal, retirement: retirement)
    }
    /// Prepare failure leaves ownership here. After transfer this is a no-op;
    /// construction/session cancellation owns cleanup instead.
    public func closeIfUntransferred() { core.closeIfUntransferred() }
    deinit { core.closeIfUntransferred() } // The separate core is captured, never self.
}

final class AdapterCloseCore: @unchecked Sendable {
    private static let quarantinedOwners = Locked<[AdapterCloseCore]>([])
    private struct State {
        var http: URLSessionHTTPTransport?
        var storage: AppPrivateKeyValueStore?
        var terminal: (any CapabilityBridgeTerminalObserver)?
        var retirement: (any CapabilityBridgeRetirementObserver)?
        var permit: ConstructionPermit?
        var consumed = false
        var workerTail = false
        var nativeExpected = false
        var nativeDrained = false
        var closeStarted = false
        var adaptersClosed = false
        var quarantined = false
        var retired = false
        var firstFailure: ExperimentalCapabilityFailure?
        var cleanupJobs = 0
    }
    private let state: Locked<State>
    init(http: URLSessionHTTPTransport?, storage: AppPrivateKeyValueStore?,
         terminal: any CapabilityBridgeTerminalObserver, retirement: any CapabilityBridgeRetirementObserver) {
        state = Locked(State(http: http, storage: storage, terminal: terminal, retirement: retirement))
    }
    func consume(_ permit: ConstructionPermit) throws -> InstalledCapabilityAdapters {
        try state.withLock { state in
            guard !state.consumed, !state.closeStarted else { throw ExperimentalCapabilityError("adapter_group_consumed") }
            state.consumed = true; state.permit = permit
            return InstalledCapabilityAdapters(http: state.http, storage: state.storage)
        }
    }
    func closeIfUntransferred() {
        let begin = state.withLock { state in
            guard !state.consumed, !state.closeStarted else { return false }
            state.consumed = true; state.workerTail = true; return true
        }
        if begin { close(host: nil, nativeOwner: nil) }
    }
    func expectsNative() { state.withLock { $0.nativeExpected = true } }
    func constructorReturned() { state.withLock { $0.workerTail = true }; retireIfReady() }
    func nativeDidDrain() { state.withLock { $0.nativeDrained = true }; retireIfReady() }
    func terminal(_ failure: ExperimentalCapabilityFailure) {
        let observer = state.withLock { state -> (any CapabilityBridgeTerminalObserver)? in
            guard state.firstFailure == nil, !state.retired else { return nil }
            state.firstFailure = failure; return state.terminal
        }
        observer?.recordTerminalFailure(failure)
    }
    func quarantine() {
        let permit = state.withLock { state -> ConstructionPermit? in
            guard !state.quarantined else { return nil }
            state.quarantined = true; return state.permit
        }
        if let permit {
            Self.quarantinedOwners.withLock { $0.append(self) }
            permit.quarantine()
        }
    }
    func failedBeforeNative(host: CapabilityHost?, error: any Error, quarantined: Bool) {
        if !(error is CancellationError) { terminal(ExperimentalCapabilityError.detail(error)) }
        if quarantined { quarantine() }
        close(host: host, nativeOwner: nil)
    }
    func close(host: CapabilityHost?, nativeOwner: NativeExitOwner?) {
        let begin = state.withLock { state in
            guard !state.closeStarted else { return false }
            state.closeStarted = true; state.cleanupJobs += 1; return true
        }
        guard begin else { return }
        Task.detached { [self, host, nativeOwner] in
            if let host { await host.close() }
            let storage = state.withLock { $0.storage }
            if let storage { await storage.close() }
            state.withLock { $0.adaptersClosed = true; $0.http = nil; $0.storage = nil }
            if let nativeOwner { nativeOwner.concreteAdaptersClosed() }
            retireIfReady()
        }
    }
    private func retireIfReady() {
        let retirement = state.withLock { state -> ((any CapabilityBridgeRetirementObserver)?, ConstructionPermit?) in
            guard !state.retired, !state.quarantined, state.workerTail, state.adaptersClosed,
                  !state.nativeExpected || state.nativeDrained else { return (nil,nil) }
            state.retired = true
            let result = (state.retirement, state.permit)
            state.retirement = nil; state.terminal = nil; state.permit = nil
            return result
        }
        retirement.1?.release()
        retirement.0?.recordRetired()
    }
    // Logical lifecycle observations, not Task object/allocator destruction.
    var cleanupJobCount: Int { state.withLock { $0.cleanupJobs } }
    var constructorTailObserved: Bool { state.withLock { $0.workerTail } }
}
