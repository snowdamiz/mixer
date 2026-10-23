import Foundation
import MixerCapabilities

/// A synchronous construction reservation. Pending and native-draining owners
/// share sixteen permits. No C work is scheduled until the one-shot create call.
public final class ExperimentalCapabilityConstruction: @unchecked Sendable {
    private struct Input: Sendable {
        let module: Data
        let startup: String
        let configuration: ExperimentalCapabilityConfiguration
        let policy: CapabilityPolicy
        let adapters: InstalledCapabilityAdapters
    }
    private struct State {
        var input: Input?
        var started = false
        var finished = false
        var cancelled = false
    }
    private let state: Locked<State>
    private let permit: ConstructionPermit
    fileprivate init(module: Data, startup: String, configuration: ExperimentalCapabilityConfiguration,
                     policy: CapabilityPolicy, adapters: InstalledCapabilityAdapters, permit: ConstructionPermit) {
        state = Locked(State(input: Input(module: module, startup: startup, configuration: configuration, policy: policy, adapters: adapters)))
        self.permit = permit
    }
    /// Cancels only unfinished construction; it never closes an already returned
    /// session or changes the permit after its ownership was transferred.
    public func cancel() {
        let unused = state.withLock { state in
            guard !state.finished else { return false }
            state.cancelled = true
            if !state.started { state.input = nil; return true }
            return false
        }
        if unused { permit.release() }
    }
    public func create() async throws -> ExperimentalCapabilitySession {
        let input = try state.withLock { state in
            guard !state.started, !state.finished, !state.cancelled, let input = state.input else {
                throw ExperimentalCapabilityError("construction_consumed")
            }
            state.started = true; state.input = nil; return input
        }
        return try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { continuation in
                ExperimentalQueues.construction.async { [self] in
                    do {
                        guard !state.withLock({ $0.cancelled }) else { throw CancellationError() }
                        let host = try CapabilityHost(policy: input.policy, maximumRequests: Int(input.configuration.maximumRequests),
                            timeoutMilliseconds: input.configuration.timeoutMilliseconds, installedAdapters: input.adapters)
                        let native = try NativeCapabilitySession(module: input.module, startup: input.startup, configuration: input.configuration)
                        let owner = NativeExitOwner(native: native, host: host, configuration: input.configuration, permit: permit)
                        owner.start()
                        let accepted = state.withLock { state in
                            state.finished = true; return !state.cancelled
                        }
                        if accepted { continuation.resume(returning: ExperimentalCapabilitySession(owner: owner)) }
                        else { owner.stop(); continuation.resume(throwing: CancellationError()) }
                    } catch {
                        state.withLock { $0.finished = true }
                        if let failure = error as? NativeConstructionFailure {
                            if failure.retainsPermit { permit.quarantine() } else { permit.release() }
                            continuation.resume(throwing: failure.reported)
                        } else {
                            permit.release()
                            continuation.resume(throwing: error)
                        }
                    }
                }
            }
        } onCancel: { self.cancel() }
    }
}

/// Opt-in experimental owner. It never exposes a native handle, mailbox token,
/// host request identity or a generic completion/exit-ack entry point.
public final class ExperimentalCapabilitySession: @unchecked Sendable {
    private let owner: NativeExitOwner
    fileprivate init(owner: NativeExitOwner) { self.owner = owner }
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
    deinit { owner.stop() }
    public var status: ExperimentalCapabilityStatus { owner.status }
    /// Latches admission closed synchronously; native and host cleanup run off UI.
    /// Already admitted effects may commit. Actual exit remains separately counted.
    public func close() { owner.stop() }
    public func startup() async throws -> ExperimentalCapabilityInvocation { try await owner.startup() }
    /// Development-only transition after startup, never verified activation.
    public func enableEffects() async throws { try await owner.enable() }
    public func invoke(_ export: String, arguments: [ExperimentalVMValue] = []) async throws -> ExperimentalCapabilityInvocation {
        guard !export.isEmpty, export.utf8.prefix(4097).count <= 4096, arguments.count <= 4096 else {
            throw ExperimentalCapabilityError("invalid_invoke_arguments")
        }
        return try await owner.command(turn: true) { [owner] in try owner.native.invoke(export, arguments: arguments) }
    }
    public func readMemory(offset: UInt32, count: Int) async throws -> Data {
        guard (0...1_048_576).contains(count) else { throw ExperimentalCapabilityError("invalid_read_length") }
        return try await owner.command { [owner] in try owner.native.read(offset: offset, count: count) }
    }
    public func writeMemory(offset: UInt32, bytes: Data) async throws {
        // One admitted command may retain the caller's Data backing allocation;
        // this public limit measures logical bytes rather than backing capacity.
        guard bytes.count <= 1_048_576 else { throw ExperimentalCapabilityError("invalid_write_length") }
        try await owner.command { [owner] in try owner.native.write(offset: offset, data: bytes) }
    }
}
