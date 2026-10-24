import Foundation
import Dispatch
import CMixerVMCapability
@_spi(GuestUIV1) import MixerGuest

private final class ValidationPermit: @unchecked Sendable {
    private static let count = Locked(0)
    private static let quarantined = Locked<[ValidationPermit]>([])
    private enum State { case active, released, quarantined }
    private let state = Locked(State.active)
    static func acquire() throws -> ValidationPermit {
        try count.withLock { count in
            guard count < 2 else { throw ExperimentalCapabilityError("validation_busy") }
            count += 1
        }
        return ValidationPermit()
    }
    func release() {
        let first = state.withLock { value in
            guard value == .active else { return false }
            value = .released; return true
        }
        if first { Self.count.withLock { $0 -= 1 } }
    }
    func quarantine() {
        let first = state.withLock { value in
            guard value == .active else { return false }
            value = .quarantined; return true
        }
        if first { Self.quarantined.withLock { $0.append(self) } }
    }
    deinit { release() }
}

enum ValidationQueue {
    static let serial = DispatchQueue(label: "mixer.experimental.capability.validate", qos: .utility)
}

/// Admission only. A successful return is not an execution or activation proof.
public enum ExperimentalCapabilityValidator {
    @_spi(GuestUIV1)
    public static func prepareGuestUIV1(module: Data, configuration: ExperimentalCapabilityConfiguration) throws -> ExperimentalCapabilityValidation {
        guard module.count <= 4_194_304 else { throw ExperimentalCapabilityError("invalid_module_or_startup") }
        try configuration.validate()
        let permit = try ValidationPermit.acquire()
        let snapshot = module.withUnsafeBytes { bytes in
            bytes.isEmpty ? Data() : Data(bytes: bytes.baseAddress!, count: bytes.count)
        }
        return ExperimentalCapabilityValidation(module: snapshot, startup: "mixer_guest_ui_start_v1", configuration: configuration, permit: permit, guestUI: true)
    }
    public static func prepare(module: Data, startupExport: String,
                               configuration: ExperimentalCapabilityConfiguration = .init()) throws -> ExperimentalCapabilityValidation {
        guard module.count <= 4_194_304, !startupExport.isEmpty, startupExport.utf8.prefix(4097).count <= 4096 else {
            throw ExperimentalCapabilityError("invalid_module_or_startup")
        }
        try configuration.validate()
        let permit = try ValidationPermit.acquire()
        let snapshot = module.withUnsafeBytes { bytes in
            bytes.isEmpty ? Data() : Data(bytes: bytes.baseAddress!, count: bytes.count)
        }
        let name = String(decoding: Array(startupExport.utf8), as: UTF8.self)
        return ExperimentalCapabilityValidation(module: snapshot, startup: name, configuration: configuration, permit: permit)
    }
}

/// Two process permits cover unused, queued, running and cancelled/draining
/// validations. Cancellation cannot interrupt the synchronous native validator.
public final class ExperimentalCapabilityValidation: @unchecked Sendable {
    private struct Input: Sendable {
        let module: Data
        let startup: String
        let configuration: ExperimentalCapabilityConfiguration
        let guestUI: Bool
    }
    private struct State {
        var input: Input?
        var started = false
        var cancelled = false
        var finished = false
    }
    private let state: Locked<State>
    private let permit: ValidationPermit
    fileprivate init(module: Data, startup: String, configuration: ExperimentalCapabilityConfiguration, permit: ValidationPermit, guestUI: Bool = false) {
        state = Locked(State(input: Input(module: module, startup: startup, configuration: configuration, guestUI: guestUI)))
        self.permit = permit
    }
    deinit {
        state.withLock { $0.input = nil }
        permit.release()
    }
    public func cancel() {
        let unused = state.withLock { state in
            guard !state.finished else { return false }
            state.cancelled = true
            if !state.started { state.input = nil; return true }
            return false
        }
        if unused { permit.release() }
    }
    public func validate() async throws {
        try state.withLock { state in
            guard !state.started, !state.finished, !state.cancelled, state.input != nil else {
                throw ExperimentalCapabilityError("validation_consumed")
            }
            state.started = true
        }
        try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, any Error>) in
                ValidationQueue.serial.async { [self] in
                    let outcome = perform()
                    let cancelled = state.withLock { state in state.finished = true; return state.cancelled }
                    let fault: Bool
                    if case .failure(let error) = outcome, let native = error as? ExperimentalCapabilityError {
                        fault = native.nativeStatus == nil || native.nativeStatus == 4
                    } else { fault = false }
                    // perform's input and C frame are gone before capacity is
                    // released. Only a tiny owner/continuation remains here.
                    if fault { permit.quarantine() } else { permit.release() }
                    if cancelled && !fault { continuation.resume(throwing: CancellationError()) }
                    else { continuation.resume(with: outcome) }
                }
            }
        } onCancel: { self.cancel() }
    }
    private func perform() -> Result<Void, any Error> {
        let input = state.withLock { state -> Input? in
            let input = state.input; state.input = nil
            return state.cancelled ? nil : input
        }
        guard let input else { return .failure(CancellationError()) }
        if input.guestUI {
            do { try NativeCapabilitySession.validateGuestUI(module: input.module, configuration: input.configuration); return .success(()) }
            catch { return .failure(error) }
        }
        var vm = input.configuration.vm, capability = input.configuration.capability, report = MixerVmReport()
        let name = Array(input.startup.utf8)
        let status = input.module.withUnsafeBytes { bytes in
            name.withUnsafeBufferPointer { name in
                mixer_vm_capability_validate_v1(bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count,
                    name.baseAddress, name.count, &vm, &capability, &report)
            }
        }
        do {
            try NativeDiagnostics.check(status, report, operation: .validation, moduleLength: input.module.count,
                configuration: input.configuration)
            return .success(())
        } catch { return .failure(error) }
    }
}
