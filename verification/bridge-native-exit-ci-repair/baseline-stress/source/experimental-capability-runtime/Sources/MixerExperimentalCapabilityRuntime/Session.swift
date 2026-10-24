import Foundation
import MixerCapabilities
@_spi(GuestUIV1) import MixerGuest

/// A synchronous construction reservation. Pending and native-draining owners
/// share sixteen permits. No C work is scheduled until the one-shot create call.
public final class ExperimentalCapabilityConstruction: @unchecked Sendable {
    private struct Input: Sendable {
        let module: Data
        let startup: String
        let configuration: ExperimentalCapabilityConfiguration
        let policy: CapabilityPolicy
        let adapters: InstalledCapabilityAdapters
        let exchange: GuestUIExchangeV1?
    }
    private struct State {
        var input: Input?
        var started = false
        var finished = false
        var cancelled = false
    }
    private let state: Locked<State>
    private let permit: ConstructionPermit
    private let lifecycle: AdapterCloseCore?
    private let guestUIExchange: GuestUIExchangeV1?
    fileprivate init(module: Data, startup: String, configuration: ExperimentalCapabilityConfiguration,
                     policy: CapabilityPolicy, adapters: InstalledCapabilityAdapters, permit: ConstructionPermit, lifecycle: AdapterCloseCore? = nil,
                     exchange: GuestUIExchangeV1? = nil) {
        state = Locked(State(input: Input(module: module, startup: startup, configuration: configuration, policy: policy, adapters: adapters, exchange: exchange)))
        self.permit = permit; self.lifecycle = lifecycle
        guestUIExchange = exchange
    }
    deinit {
        let unused = state.withLock { state in
            guard !state.started, !state.finished else { return false }
            state.input = nil; state.finished = true; return true
        }
        if unused { closeUnused() }
    }
    private func closeUnused() {
        guestUIExchange?.stop(.closed)
        if let lifecycle {
            lifecycle.failedBeforeNative(host: nil, error: CancellationError(), quarantined: false)
            lifecycle.constructorReturned()
        } else { permit.release() }
    }
    /// Cancels only unfinished construction; it never closes an already returned
    /// session or changes the permit after its ownership was transferred.
    public func cancel() {
        let result = state.withLock { state -> (Bool, Bool) in
            guard !state.finished else { return (false, false) }
            state.cancelled = true
            if !state.started { state.input = nil; state.finished = true; return (true, true) }
            return (true, false)
        }
        if result.0 { guestUIExchange?.stop(.cancelled) }
        if result.1 { closeUnused() }
    }
    public func create() async throws -> ExperimentalCapabilitySession {
        try state.withLock { state in
            guard !state.started, !state.finished, !state.cancelled, state.input != nil else {
                throw ExperimentalCapabilityError("construction_consumed")
            }
            state.started = true
        }
        return try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { continuation in
                ExperimentalQueues.construction.async { [self] in
                    let outcome = performCreate()
                    let accepted = state.withLock { state in state.finished = true; return !state.cancelled }
                    switch outcome {
                    case .success(let owner):
                        owner.start()
                        if accepted { continuation.resume(returning: ExperimentalCapabilitySession(owner: owner)) }
                        else {
                            guestUIExchange?.stop(.cancelled)
                            owner.stop(); continuation.resume(throwing: CancellationError())
                        }
                    case .failure(let error, let host, let quarantined):
                        if error is CancellationError { guestUIExchange?.stop(.cancelled) }
                        if let lifecycle {
                            if error is GuestUIProtocolFailureV1 || error is GuestUIControlRejectionV1 {
                                lifecycle.close(host: host, nativeOwner: nil)
                            } else { lifecycle.failedBeforeNative(host: host, error: error, quarantined: quarantined) }
                        }
                        else if quarantined { permit.quarantine() }
                        else { permit.release() }
                        continuation.resume(throwing: error)
                    }
                    // performCreate's payload/C frame is gone. Both successful
                    // handoff and failure wait for this tiny logical worker tail.
                    lifecycle?.constructorReturned()
                }
            }
        } onCancel: { self.cancel() }
    }
    private enum Outcome {
        case success(NativeExitOwner)
        case failure(any Error, CapabilityHost?, Bool)
    }
    private func performCreate() -> Outcome {
        let input = state.withLock { state -> Input? in
            let input = state.input; state.input = nil
            return state.cancelled ? nil : input
        }
        guard let input else { return .failure(CancellationError(),nil,false) }
        var host: CapabilityHost?
        do {
            if let exchange = input.exchange {
                try GuestUITurns.requireLive(exchange)
                try NativeCapabilitySession.validateGuestUI(module: input.module, configuration: input.configuration)
                try GuestUITurns.requireLive(exchange)
            }
            let createdHost = try CapabilityHost(policy: input.policy, maximumRequests: Int(input.configuration.maximumRequests),
                timeoutMilliseconds: input.configuration.timeoutMilliseconds, installedAdapters: input.adapters)
            host = createdHost
            let native = try NativeCapabilitySession(module: input.module, startup: input.startup, configuration: input.configuration)
            lifecycle?.expectsNative()
            return .success(NativeExitOwner(native: native, host: createdHost, configuration: input.configuration, permit: permit, lifecycle: lifecycle, exchange: input.exchange))
        } catch let failure as GuestUIProtocolFailureV1 {
            input.exchange?.recordProtocolFailure(failure)
            return .failure(failure,host,false)
        } catch let failure as NativeConstructionFailure {
            input.exchange?.stop(failure.reported.failure.kind == .deadlineExceeded ? .deadline : failure.reported.failure.kind == .cancelled ? .cancelled : .bridge)
            return .failure(failure.reported,host,failure.retainsPermit)
        } catch {
            if !(error is GuestUIControlRejectionV1) { input.exchange?.stop(.bridge) }
            return .failure(error,host,false)
        }
    }

}

/// Opt-in experimental owner. It never exposes a native handle, mailbox token,
/// host request identity or a generic completion/exit-ack entry point.
public final class ExperimentalCapabilitySession: @unchecked Sendable {
    private let owner: NativeExitOwner
    fileprivate init(owner: NativeExitOwner) { self.owner = owner }
    @_spi(GuestUIV1)
    public static func prepareOwnedGuestUIV1(module: Data, configuration: ExperimentalCapabilityConfiguration,
                                           policy: CapabilityPolicy, adapterGroup: OwnedCapabilityAdapterGroup,
                                           exchange: GuestUIExchangeV1) throws -> ExperimentalCapabilityConstruction {
        guard module.count <= 4_194_304 else { throw ExperimentalCapabilityError("invalid_module_or_startup") }
        try configuration.validate()
        try GuestUITurns.requireLive(exchange)
        let permit = try ConstructionPermit.acquire()
        do {
            let adapters = try adapterGroup.core.consume(permit)
            let snapshot = module.withUnsafeBytes { bytes in
                bytes.isEmpty ? Data() : Data(bytes: bytes.baseAddress!, count: bytes.count)
            }
            return ExperimentalCapabilityConstruction(module: snapshot, startup: "mixer_guest_ui_start_v1", configuration: configuration,
                policy: policy, adapters: adapters, permit: permit, lifecycle: adapterGroup.core, exchange: exchange)
        } catch { permit.release(); throw error }
    }
    public static func prepare(module: Data, startupExport: String,
                               configuration: ExperimentalCapabilityConfiguration = .init(),
                               policy: CapabilityPolicy, adapters: InstalledCapabilityAdapters) throws -> ExperimentalCapabilityConstruction {
        // Counts are logical input bounds. Caller Data/String backing storage,
        // policies and installed adapters are not an allocator/RSS reservation.
        guard module.count <= 4_194_304, !startupExport.isEmpty,
              startupExport.utf8.prefix(4097).count <= 4096 else { throw ExperimentalCapabilityError("invalid_module_or_startup") }
        try configuration.validate()
        let permit = try ConstructionPermit.acquire()
        return ExperimentalCapabilityConstruction(module: module, startup: startupExport, configuration: configuration,
                                                 policy: policy, adapters: adapters, permit: permit)
    }
    @_spi(CapabilityLifecycle)
    public static func prepareOwned(module: Data, startupExport: String,
                                    configuration: ExperimentalCapabilityConfiguration = .init(),
                                    policy: CapabilityPolicy, adapterGroup: OwnedCapabilityAdapterGroup) throws -> ExperimentalCapabilityConstruction {
        guard module.count <= 4_194_304, !startupExport.isEmpty,
              startupExport.utf8.prefix(4097).count <= 4096 else { throw ExperimentalCapabilityError("invalid_module_or_startup") }
        try configuration.validate()
        let permit = try ConstructionPermit.acquire()
        do {
            let adapters = try adapterGroup.core.consume(permit)
            return ExperimentalCapabilityConstruction(module: module, startup: startupExport, configuration: configuration,
                policy: policy, adapters: adapters, permit: permit, lifecycle: adapterGroup.core)
        } catch { permit.release(); throw error }
    }
    deinit { owner.stop() }
    public var status: ExperimentalCapabilityStatus { owner.status }
    /// Latches admission closed synchronously; native and host cleanup run off UI.
    /// Already admitted effects may commit. Actual exit remains separately counted.
    public func close() { owner.stop() }
    public func startup() async throws -> ExperimentalCapabilityInvocation { try await owner.startup() }
    @_spi(GuestUIV1)
    public func startupGuestUIV1() async throws { try await owner.startupGuestUI() }
    /// Development-only transition after startup, never verified activation.
    public func enableEffects() async throws { try owner.requireGeneric(); try await owner.enable() }
    /// Trusted coordinator seam: carries its exact DispatchTime uptime startup
    /// cutoff to the guest worker. This is a sampled cooperative pre-C check,
    /// not a hard real-time guarantee or signed execution authority.
    @_spi(CapabilityLifecycle)
    public func enableOwnedEffects(noLaterThanUptimeNanoseconds cutoff: UInt64) async throws {
        try await owner.enableOwned(noLaterThanUptimeNanoseconds: cutoff)
    }
    public func invoke(_ export: String, arguments: [ExperimentalVMValue] = []) async throws -> ExperimentalCapabilityInvocation {
        try owner.requireGeneric()
        guard !export.isEmpty, export.utf8.prefix(4097).count <= 4096, arguments.count <= 4096 else {
            throw ExperimentalCapabilityError("invalid_invoke_arguments")
        }
        return try await owner.command(turn: true) { [owner] in try owner.native.invoke(export, arguments: arguments) }
    }
    public func readMemory(offset: UInt32, count: Int) async throws -> Data {
        try owner.requireGeneric()
        guard (0...1_048_576).contains(count) else { throw ExperimentalCapabilityError("invalid_read_length") }
        return try await owner.command { [owner] in try owner.native.read(offset: offset, count: count) }
    }
    public func writeMemory(offset: UInt32, bytes: Data) async throws {
        try owner.requireGeneric()
        // One admitted command may retain the caller's Data backing allocation;
        // this public limit measures logical bytes rather than backing capacity.
        guard bytes.count <= 1_048_576 else { throw ExperimentalCapabilityError("invalid_write_length") }
        try await owner.command { [owner] in try owner.native.write(offset: offset, data: bytes) }
    }
}
