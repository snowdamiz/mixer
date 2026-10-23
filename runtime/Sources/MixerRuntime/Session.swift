import Foundation
import CMixerVM

public enum VMProfile: UInt32, Sendable, CaseIterable {
    case integerV1 = 1, numericV2 = 2, tableMemoryV3 = 3
}

/// Native hosts may narrow the published ceilings. Profiles are explicit and immutable.
public struct VMLimits: Sendable, Equatable {
    public let fuel: UInt64
    public let memoryPages: UInt32
    public let operandStack: UInt32
    public let callDepth: UInt32
    public let hostCalls: UInt32
    public init(fuel: UInt64 = 1_000_000, memoryPages: UInt32 = 64,
                operandStack: UInt32 = 4096, callDepth: UInt32 = 64, hostCalls: UInt32 = 1024) {
        self.fuel = fuel; self.memoryPages = memoryPages; self.operandStack = operandStack
        self.callDepth = callDepth; self.hostCalls = hostCalls
    }
    var cValue: MixerVmLimits {
        MixerVmLimits(struct_size: UInt32(MemoryLayout<MixerVmLimits>.size), abi_version: 1,
            fuel: fuel, memory_pages: memoryPages, operand_stack: operandStack,
            call_depth: callDepth, host_calls: hostCalls)
    }
}

/// Float transport is bit-exact, including signed zero and NaN payloads.
public enum VMValue: Sendable, Equatable {
    case i32(Int32), i64(Int64), f32Bits(UInt32), f64Bits(UInt64)
    var cValue: MixerVmValue {
        switch self {
        case .i32(let value): MixerVmValue(value_type: 1, reserved: 0, value: Int64(value))
        case .i64(let value): MixerVmValue(value_type: 2, reserved: 0, value: value)
        case .f32Bits(let bits): MixerVmValue(value_type: 3, reserved: 0, value: Int64(bits))
        case .f64Bits(let bits): MixerVmValue(value_type: 4, reserved: 0, value: Int64(bitPattern: bits))
        }
    }
}

public struct VMInvocation: Sendable, Equatable {
    public let value: VMValue?
    public let fuelUsed: UInt64
    public let hostCallsUsed: UInt64
}

public struct VMFailure: Error, Sendable, Equatable, CustomStringConvertible {
    public let status: UInt32
    public let code: String
    public let message: String
    public let function: UInt32?
    public let offset: UInt32
    public let fuelUsed: UInt64
    public let hostCallsUsed: UInt64
    public var description: String { "\(code): \(message)" }
    fileprivate init(_ code: String, _ message: String, status: UInt32 = 3) {
        self.status = status; self.code = code; self.message = message
        function = nil; offset = 0; fuelUsed = 0; hostCallsUsed = 0
    }
    fileprivate init(_ report: MixerVmReport) {
        status = report.status
        var report = report
        code = withUnsafeBytes(of: &report.code) { String(decoding: $0.prefix(while: { $0 != 0 }), as: UTF8.self) }
        message = withUnsafeBytes(of: &report.message) { String(decoding: $0.prefix(while: { $0 != 0 }), as: UTF8.self) }
        function = report.function == UInt32.max ? nil : report.function
        offset = report.offset; fuelUsed = report.fuel_used; hostCallsUsed = report.host_calls_used
    }
}

/// Validates the complete module against the explicitly installed profile and
/// limits. It does not instantiate memory, reserve a session or execute an export.
public enum VMValidator {
    public static func validate(_ module: Data, profile: VMProfile, limits: VMLimits = VMLimits()) throws {
        var nativeLimits = limits.cValue
        var report = MixerVmReport()
        let status = module.withUnsafeBytes { input in
            let bytes = input.bindMemory(to: UInt8.self).baseAddress
            switch profile {
            case .integerV1: return mixer_vm_validate(bytes, input.count, &nativeLimits, &report)
            case .numericV2: return mixer_vm_validate_numeric_v2(bytes, input.count, &nativeLimits, &report)
            case .tableMemoryV3: return mixer_vm_validate_table_memory_v3(bytes, input.count, &nativeLimits, &report)
            }
        }
        try VMSession.check(status, report)
    }
}

/// A process-local owned VM instance. Invoke/read/write are synchronous: run guest
/// work on a feature executor, never an unbounded loop on the UI executor. Concurrent
/// operations fail with session_busy; cancel/close are safe from another thread.
///
/// Sendability relies on the native generation registry, retained in-flight storage,
/// per-instance mutex and atomic cancellation. This lock protects only Swift handle
/// lifetime; it is never held while executing guest code or calling the native ABI.
public final class VMSession: @unchecked Sendable {
    public let profile: VMProfile
    public let limits: VMLimits
    private let lifecycle = NSLock()
    private var handle: UInt64

    public init(module: Data, profile: VMProfile, limits: VMLimits = VMLimits()) throws {
        self.profile = profile; self.limits = limits
        var nativeLimits = limits.cValue
        var output: UInt64 = 0
        var report = MixerVmReport()
        let status = module.withUnsafeBytes { input in
            mixer_vm_session_create_v1(profile.rawValue, input.bindMemory(to: UInt8.self).baseAddress,
                input.count, &nativeLimits, &output, &report)
        }
        try Self.check(status, report)
        guard output != 0 else { throw VMFailure("invalid_vm_report", "VM returned an empty session handle", status: 4) }
        handle = output
    }

    deinit { if let handle = takeHandle() { var report = MixerVmReport(); _ = mixer_vm_session_close_v1(handle, &report) } }

    /// Close is idempotent at this Swift ownership boundary. In-flight operations may
    /// finish before cancellation; no rollback is promised. New operations reject.
    public func close() throws {
        guard let handle = takeHandle() else { return }
        var report = MixerVmReport()
        try Self.check(mixer_vm_session_close_v1(handle, &report), report)
    }

    public func cancel() throws {
        let handle = try currentHandle()
        var report = MixerVmReport()
        try Self.check(mixer_vm_session_cancel_v1(handle, &report), report)
    }

    public func invoke(_ export: String, arguments: [VMValue] = []) throws -> VMInvocation {
        let handle = try currentHandle()
        let name = Array(export.utf8.prefix(4097))
        guard name.count <= 4096, arguments.count <= 4096 else {
            throw VMFailure("invalid_arguments", "Export name or argument count exceeds profile")
        }
        let values = arguments.map(\.cValue)
        var report = MixerVmReport()
        let status = name.withUnsafeBufferPointer { name in
            values.withUnsafeBufferPointer { values in
                mixer_vm_session_invoke_v1(handle, name.baseAddress, name.count, values.baseAddress, values.count, &report)
            }
        }
        try Self.check(status, report)
        let value: VMValue?
        switch report.value_type {
        case 0: value = nil
        case 1:
            guard let number = Int32(exactly: report.value) else { throw VMFailure("invalid_vm_report", "Invalid i32 result", status: 4) }
            value = .i32(number)
        case 2: value = .i64(report.value)
        case 3:
            guard let bits = UInt32(exactly: report.value) else { throw VMFailure("invalid_vm_report", "Invalid f32 bits", status: 4) }
            value = .f32Bits(bits)
        case 4: value = .f64Bits(UInt64(bitPattern: report.value))
        default: throw VMFailure("invalid_vm_report", "Unknown result value type", status: 4)
        }
        return VMInvocation(value: value, fuelUsed: report.fuel_used, hostCallsUsed: report.host_calls_used)
    }

    public func readMemory(offset: UInt32, count: Int) throws -> Data {
        let handle = try currentHandle()
        guard (0...1_048_576).contains(count) else { throw VMFailure("invalid_arguments", "Memory copy exceeds 1MiB transfer ceiling") }
        var output = Data(count: count)
        var report = MixerVmReport()
        let status = output.withUnsafeMutableBytes { bytes in
            mixer_vm_session_read_v1(handle, offset, bytes.bindMemory(to: UInt8.self).baseAddress, count, &report)
        }
        try Self.check(status, report)
        return output
    }

    public func writeMemory(offset: UInt32, bytes: Data) throws {
        let handle = try currentHandle()
        guard bytes.count <= 1_048_576 else { throw VMFailure("invalid_arguments", "Memory copy exceeds 1MiB transfer ceiling") }
        var report = MixerVmReport()
        let status = bytes.withUnsafeBytes { bytes in
            mixer_vm_session_write_v1(handle, offset, bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count, &report)
        }
        try Self.check(status, report)
    }

    private func currentHandle() throws -> UInt64 {
        lifecycle.lock(); defer { lifecycle.unlock() }
        guard handle != 0 else { throw VMFailure("invalid_session", "Session is closed") }
        return handle
    }
    private func takeHandle() -> UInt64? {
        lifecycle.lock(); defer { lifecycle.unlock() }
        guard handle != 0 else { return nil }
        let result = handle; handle = 0; return result
    }
    fileprivate static func check(_ status: UInt32, _ report: MixerVmReport) throws {
        guard report.abi_version == 1, report.status == status, report.reserved == 0 else {
            throw VMFailure("invalid_vm_report", "Installed VM ABI/report mismatch", status: 4)
        }
        if status != 0 { throw VMFailure(report) }
    }
}
