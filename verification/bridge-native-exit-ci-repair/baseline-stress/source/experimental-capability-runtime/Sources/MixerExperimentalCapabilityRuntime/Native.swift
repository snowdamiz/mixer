import Foundation
import CMixerVMCapability
import MixerCapabilities
@_spi(GuestUIV1) import MixerGuest

enum NativeMessage {
    case none
    case call(UInt64, GuestCapabilityOperationV1, Data)
    case cancel(UInt64, GuestCapabilityOperationV1)
}

/// A create failure can have no trustworthy handle with which to prove that C
/// reclaimed its registry slot. Preserve capacity separately from module bytes.
struct NativeConstructionFailure: Error {
    let reported: ExperimentalCapabilityError
    let retainsPermit: Bool
}

/// Immutable retained handle. Only the pump uses scratch or ordinary operations;
/// the separate close path may race, using the C registry's reviewed contract.
final class NativeCapabilitySession: @unchecked Sendable {
    static func validateGuestUI(module: Data, configuration: ExperimentalCapabilityConfiguration) throws {
        var vm = configuration.vm, capability = configuration.capability, report = MixerVmReport()
        let status = module.withUnsafeBytes { bytes in
            mixer_vm_capability_guest_ui_validate_v1(bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count,
                &vm, &capability, &report)
        }
        do {
            try NativeDiagnostics.check(status, report, operation: .validation, moduleLength: module.count, configuration: configuration)
        } catch let error as ExperimentalCapabilityError {
            // Consume only the checked typed tuple from this fixed validator.
            // Never infer a UI protocol reason from a diagnostic string.
            if error.nativeStatus == 1, error.failure.operation == .validation,
               error.failure.kind == .validation(.requiredDefinedExport),
               let location = error.failure.location, location.functionIndex == nil, location.byteOffset == 0 {
                throw GuestUIProtocolFailureV1(phase: .validation, code: .requiredExport)
            }
            throw error
        }
    }
    let handle: UInt64
    private let moduleLength: Int
    private let configuration: ExperimentalCapabilityConfiguration
    private var scratch = Data(count: 524288)
    init(module: Data, startup: String, configuration: ExperimentalCapabilityConfiguration) throws {
        self.moduleLength = module.count; self.configuration = configuration
        var vm = configuration.vm, cap = configuration.capability
        var output: UInt64 = 0, report = MixerVmReport()
        let name = Array(startup.utf8)
        let status = module.withUnsafeBytes { bytes in
            name.withUnsafeBufferPointer { name in
                mixer_vm_capability_session_create_v1(bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count,
                    name.baseAddress, name.count, &vm, &cap, &output, &report)
            }
        }
        do {
            try Self.check(status, report, operation: .construction, moduleLength: module.count, configuration: configuration)
            guard output != 0 else { throw ExperimentalCapabilityError("invalid_native_handle", operation: .construction) }
        }
        catch {
            let reported = error as? ExperimentalCapabilityError ?? ExperimentalCapabilityError("invalid_native_create", operation: .construction)
            // Valid ordinary failure reports initialize the handle to zero. A
            // malformed report may conceal a quarantined reservation even if a
            // subsequent cleanup reports0, so never infer reclamation from it.
            var retain = reported.nativeStatus == nil || reported.nativeStatus == 4 || output != 0
            if output != 0 {
                var cleanup = MixerVmReport()
                let cleanupStatus = mixer_vm_capability_session_close_v1(output, &cleanup)
                do { try Self.check(cleanupStatus, cleanup, operation: .close, moduleLength: module.count, configuration: configuration) } catch { retain = true }
            }
            throw NativeConstructionFailure(reported: reported, retainsPermit: retain)
        }
        handle = output
    }
    static func check(_ status: UInt32, _ report: MixerVmReport, operation: NativeDiagnostics.Operation,
                      moduleLength: Int, configuration: ExperimentalCapabilityConfiguration) throws {
        try NativeDiagnostics.check(status, report, operation: operation, moduleLength: moduleLength, configuration: configuration)
    }
    private func check(_ status: UInt32, _ report: MixerVmReport, operation: NativeDiagnostics.Operation) throws {
        try Self.check(status, report, operation: operation, moduleLength: moduleLength, configuration: configuration)
    }
    static func invocation(_ report: MixerVmReport, operation: NativeDiagnostics.Operation) throws -> ExperimentalCapabilityInvocation {
        ExperimentalCapabilityInvocation(value: try NativeDiagnostics.value(report, operation: operation),
            fuelUsed: report.fuel_used, hostCallsUsed: report.host_calls_used)
    }
    func startup() throws -> ExperimentalCapabilityInvocation {
        var report = MixerVmReport(); let status = mixer_vm_capability_session_startup_v1(handle, &report)
        try check(status, report, operation: .startup); return try Self.invocation(report, operation: .startup)
    }
    func enable() throws {
        var report = MixerVmReport(); try check(mixer_vm_capability_session_enable_v1(handle, &report), report, operation: .enableEffects)
    }
    func invoke(_ export: String, arguments: [ExperimentalVMValue]) throws -> ExperimentalCapabilityInvocation {
        let name = Array(export.utf8), values = arguments.map(\.native)
        var report = MixerVmReport()
        let status = name.withUnsafeBufferPointer { name in
            values.withUnsafeBufferPointer { args in
                mixer_vm_capability_session_invoke_v1(handle, name.baseAddress, name.count, args.baseAddress, args.count, &report)
            }
        }
        try check(status, report, operation: .invocation); return try Self.invocation(report, operation: .invocation)
    }
    func wake() throws -> Bool {
        var flag: UInt32 = 0, report = MixerVmReport()
        let status = mixer_vm_capability_session_wake_v1(handle, &flag, &report)
        try check(status, report, operation: .wake)
        guard flag <= 1 else { throw ExperimentalCapabilityError("invalid_native_wake", operation: .wake) }
        return flag == 1
    }
    func read(offset: UInt32, count: Int) throws -> Data {
        var data = Data(count: count), report = MixerVmReport()
        let status = data.withUnsafeMutableBytes { bytes in
            mixer_vm_capability_session_read_v1(handle, offset, bytes.bindMemory(to: UInt8.self).baseAddress, count, &report)
        }
        try check(status, report, operation: .readMemory); return data
    }
    func write(offset: UInt32, data: Data) throws {
        var report = MixerVmReport()
        let status = data.withUnsafeBytes { bytes in
            mixer_vm_capability_session_write_v1(handle, offset, bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count, &report)
        }
        try check(status, report, operation: .writeMemory)
    }
    func take() throws -> NativeMessage {
        var message = MixerVmCapabilityMessageV1(), report = MixerVmReport()
        let status = scratch.withUnsafeMutableBytes { bytes in
            mixer_vm_capability_take_v1(handle, &message, bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count, &report)
        }
        try check(status, report, operation: .take)
        guard message.struct_size == 40, message.abi_version == 1, message.reserved == 0 else {
            throw ExperimentalCapabilityError("invalid_native_message", operation: .take)
        }
        switch message.kind {
        case 0:
            guard message.operation == 0, message.token == 0, message.remaining_milliseconds == 0, message.payload_length == 0 else { throw ExperimentalCapabilityError("invalid_native_none", operation: .take) }
            return .none
        case 1, 2:
            guard let op = GuestCapabilityOperationV1(rawValue: message.operation), message.token >> 32 != 0,
                  (1...8).contains(UInt32(truncatingIfNeeded: message.token)), message.remaining_milliseconds <= 30000,
                  message.payload_length <= 524288 else { throw ExperimentalCapabilityError("invalid_native_call", operation: .take) }
            if message.kind == 2 {
                guard message.remaining_milliseconds == 0, message.payload_length == 0 else { throw ExperimentalCapabilityError("invalid_native_cancel", operation: .take) }
                return .cancel(message.token, op)
            }
            let payload = scratch.withUnsafeBytes { bytes in
                Data(bytes: bytes.baseAddress!, count: Int(message.payload_length))
            }
            return .call(message.token, op, payload)
        default: throw ExperimentalCapabilityError("invalid_native_take_kind", operation: .take)
        }
    }
    func remaining(token: UInt64, operation: GuestCapabilityOperationV1, timeout: UInt32) throws -> UInt32 {
        var result = MixerVmCapabilityResultV1(), report = MixerVmReport()
        let status = mixer_vm_capability_limit_deadline_v1(handle, token, operation.rawValue, timeout, &result, &report)
        try check(status, report, operation: .limitDeadline); try Self.result(result, kinds: [0, 1], operation: .limitDeadline)
        guard result.remaining_milliseconds <= 30000, result.kind != 1 || result.remaining_milliseconds == 0 else { throw ExperimentalCapabilityError("invalid_native_remaining", operation: .limitDeadline) }
        return result.kind == 1 ? 0 : result.remaining_milliseconds
    }
    func post(token: UInt64, operation: GuestCapabilityOperationV1, data: Data) throws {
        var result = MixerVmCapabilityResultV1(), report = MixerVmReport()
        let status = data.withUnsafeBytes { bytes in
            mixer_vm_capability_post_v1(handle, token, operation.rawValue, bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count, &result, &report)
        }
        try check(status, report, operation: .post); try Self.result(result, kinds: [0, 1], operation: .post)
        guard result.remaining_milliseconds == 0 else { throw ExperimentalCapabilityError("invalid_native_post", operation: .post) }
    }
    func ack(token: UInt64, operation: GuestCapabilityOperationV1) throws {
        var result = MixerVmCapabilityResultV1(), report = MixerVmReport()
        try check(mixer_vm_capability_ack_exit_v1(handle, token, operation.rawValue, &result, &report), report, operation: .ackExit)
        try Self.result(result, kinds: [0, 2], operation: .ackExit)
        guard result.remaining_milliseconds == 0 else { throw ExperimentalCapabilityError("invalid_native_ack", operation: .ackExit) }
    }
    private static func result(_ result: MixerVmCapabilityResultV1, kinds: Set<UInt32>, operation: NativeDiagnostics.Operation) throws {
        guard result.struct_size == 24, result.abi_version == 1, result.reserved == 0, kinds.contains(result.kind) else { throw ExperimentalCapabilityError("invalid_native_result", operation: operation) }
    }
    func expire() throws {
        var report = MixerVmReport(); try check(mixer_vm_capability_expire_v1(handle, &report), report, operation: .expire)
    }
    func close() throws {
        var report = MixerVmReport(); try check(mixer_vm_capability_session_close_v1(handle, &report), report, operation: .close)
    }
    func discardScratchAfterDrain() { scratch = Data() }
}
