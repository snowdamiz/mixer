import Foundation
import CMixerVMCapability
import MixerCapabilities

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
    let handle: UInt64
    private var scratch = Data(count: 524288)
    init(module: Data, startup: String, configuration: ExperimentalCapabilityConfiguration) throws {
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
            try Self.check(status, report)
            guard output != 0 else { throw ExperimentalCapabilityError("invalid_native_handle") }
        }
        catch {
            let reported = error as? ExperimentalCapabilityError ?? ExperimentalCapabilityError("invalid_native_create")
            // Valid ordinary failure reports initialize the handle to zero. A
            // malformed report may conceal a quarantined reservation even if a
            // subsequent cleanup reports0, so never infer reclamation from it.
            var retain = reported.nativeStatus == nil || reported.nativeStatus == 4 || output != 0
            if output != 0 {
                var cleanup = MixerVmReport()
                let cleanupStatus = mixer_vm_capability_session_close_v1(output, &cleanup)
                do { try Self.check(cleanupStatus, cleanup) } catch { retain = true }
            }
            throw NativeConstructionFailure(reported: reported, retainsPermit: retain)
        }
        handle = output
    }
    static func check(_ status: UInt32, _ report: MixerVmReport) throws {
        guard status <= 4, report.abi_version == 1, report.status == status, report.reserved == 0 else {
            throw ExperimentalCapabilityError("invalid_native_report")
        }
        if status != 0 {
            var copy = report.code
            let code = withUnsafeBytes(of: &copy) { bytes in String(decoding: bytes.prefix(while: { $0 != 0 }), as: UTF8.self) }
            throw ExperimentalCapabilityError(code, status: status)
        }
    }
    static func invocation(_ report: MixerVmReport) throws -> ExperimentalCapabilityInvocation {
        let value: ExperimentalVMValue?
        switch report.value_type {
        case 0: value = nil
        case 1:
            guard let n = Int32(exactly: report.value) else { throw ExperimentalCapabilityError("invalid_native_i32") }
            value = .i32(n)
        case 2: value = .i64(report.value)
        case 3:
            guard let n = UInt32(exactly: report.value) else { throw ExperimentalCapabilityError("invalid_native_f32") }
            value = .f32Bits(n)
        case 4: value = .f64Bits(UInt64(bitPattern: report.value))
        default: throw ExperimentalCapabilityError("invalid_native_value")
        }
        return ExperimentalCapabilityInvocation(value: value, fuelUsed: report.fuel_used, hostCallsUsed: report.host_calls_used)
    }
    func startup() throws -> ExperimentalCapabilityInvocation {
        var report = MixerVmReport(); let status = mixer_vm_capability_session_startup_v1(handle, &report)
        try Self.check(status, report); return try Self.invocation(report)
    }
    func enable() throws {
        var report = MixerVmReport(); try Self.check(mixer_vm_capability_session_enable_v1(handle, &report), report)
    }
    func invoke(_ export: String, arguments: [ExperimentalVMValue]) throws -> ExperimentalCapabilityInvocation {
        let name = Array(export.utf8), values = arguments.map(\.native)
        var report = MixerVmReport()
        let status = name.withUnsafeBufferPointer { name in
            values.withUnsafeBufferPointer { args in
                mixer_vm_capability_session_invoke_v1(handle, name.baseAddress, name.count, args.baseAddress, args.count, &report)
            }
        }
        try Self.check(status, report); return try Self.invocation(report)
    }
    func wake() throws -> Bool {
        var flag: UInt32 = 0, report = MixerVmReport()
        let status = mixer_vm_capability_session_wake_v1(handle, &flag, &report)
        try Self.check(status, report)
        guard flag <= 1 else { throw ExperimentalCapabilityError("invalid_native_wake") }
        return flag == 1
    }
    func read(offset: UInt32, count: Int) throws -> Data {
        var data = Data(count: count), report = MixerVmReport()
        let status = data.withUnsafeMutableBytes { bytes in
            mixer_vm_capability_session_read_v1(handle, offset, bytes.bindMemory(to: UInt8.self).baseAddress, count, &report)
        }
        try Self.check(status, report); return data
    }
    func write(offset: UInt32, data: Data) throws {
        var report = MixerVmReport()
        let status = data.withUnsafeBytes { bytes in
            mixer_vm_capability_session_write_v1(handle, offset, bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count, &report)
        }
        try Self.check(status, report)
    }
    func take() throws -> NativeMessage {
        var message = MixerVmCapabilityMessageV1(), report = MixerVmReport()
        let status = scratch.withUnsafeMutableBytes { bytes in
            mixer_vm_capability_take_v1(handle, &message, bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count, &report)
        }
        try Self.check(status, report)
        guard message.struct_size == 40, message.abi_version == 1, message.reserved == 0 else {
            throw ExperimentalCapabilityError("invalid_native_message")
        }
        switch message.kind {
        case 0:
            guard message.operation == 0, message.token == 0, message.remaining_milliseconds == 0, message.payload_length == 0 else { throw ExperimentalCapabilityError("invalid_native_none") }
            return .none
        case 1, 2:
            guard let op = GuestCapabilityOperationV1(rawValue: message.operation), message.token >> 32 != 0,
                  (1...8).contains(UInt32(truncatingIfNeeded: message.token)), message.remaining_milliseconds <= 30000,
                  message.payload_length <= 524288 else { throw ExperimentalCapabilityError("invalid_native_call") }
            if message.kind == 2 {
                guard message.remaining_milliseconds == 0, message.payload_length == 0 else { throw ExperimentalCapabilityError("invalid_native_cancel") }
                return .cancel(message.token, op)
            }
            let payload = scratch.withUnsafeBytes { bytes in
                Data(bytes: bytes.baseAddress!, count: Int(message.payload_length))
            }
            return .call(message.token, op, payload)
        default: throw ExperimentalCapabilityError("invalid_native_take_kind")
        }
    }
    func remaining(token: UInt64, operation: GuestCapabilityOperationV1, timeout: UInt32) throws -> UInt32 {
        var result = MixerVmCapabilityResultV1(), report = MixerVmReport()
        let status = mixer_vm_capability_limit_deadline_v1(handle, token, operation.rawValue, timeout, &result, &report)
        try Self.check(status, report); try Self.result(result, kinds: [0, 1])
        guard result.remaining_milliseconds <= 30000, result.kind != 1 || result.remaining_milliseconds == 0 else { throw ExperimentalCapabilityError("invalid_native_remaining") }
        return result.kind == 1 ? 0 : result.remaining_milliseconds
    }
    func post(token: UInt64, operation: GuestCapabilityOperationV1, data: Data) throws {
        var result = MixerVmCapabilityResultV1(), report = MixerVmReport()
        let status = data.withUnsafeBytes { bytes in
            mixer_vm_capability_post_v1(handle, token, operation.rawValue, bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count, &result, &report)
        }
        try Self.check(status, report); try Self.result(result, kinds: [0, 1])
        guard result.remaining_milliseconds == 0 else { throw ExperimentalCapabilityError("invalid_native_post") }
    }
    func ack(token: UInt64, operation: GuestCapabilityOperationV1) throws {
        var result = MixerVmCapabilityResultV1(), report = MixerVmReport()
        try Self.check(mixer_vm_capability_ack_exit_v1(handle, token, operation.rawValue, &result, &report), report)
        try Self.result(result, kinds: [0, 2])
        guard result.remaining_milliseconds == 0 else { throw ExperimentalCapabilityError("invalid_native_ack") }
    }
    private static func result(_ result: MixerVmCapabilityResultV1, kinds: Set<UInt32>) throws {
        guard result.struct_size == 24, result.abi_version == 1, result.reserved == 0, kinds.contains(result.kind) else { throw ExperimentalCapabilityError("invalid_native_result") }
    }
    func expire() throws {
        var report = MixerVmReport(); try Self.check(mixer_vm_capability_expire_v1(handle, &report), report)
    }
    func close() throws {
        var report = MixerVmReport(); try Self.check(mixer_vm_capability_session_close_v1(handle, &report), report)
    }
    func discardScratchAfterDrain() { scratch = Data() }
}
