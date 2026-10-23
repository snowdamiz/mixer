import Foundation
import CMixerVMCapability

public enum ExperimentalCapabilityFailureOperation: Sendable, Equatable {
    case localAPI, validation, construction, startup, enableEffects, invocation, wake
    case readMemory, writeMemory, take, post, ackExit, limitDeadline, expire, close
}
public enum ExperimentalCapabilityAPIFailure: Sendable, Equatable {
    case invalidInput, consumedOperation, unknownExport, invalidInvocation
    case invalidNativeArguments, invalidLifecycleState, nativeBusy, invalidNativeSession
}
public enum ExperimentalCapabilityValidationFailure: Sendable, Equatable {
    case malformed, unsupported, invalidBodyOrStructure, configuredLimit, invalidLimits, requiredDefinedExport
}
public enum ExperimentalCapabilityInstantiationFailure: Sendable, Equatable {
    case initialDataBounds, initialElementBounds, admissionRejected
}
public enum ExperimentalCapabilityGuestTrap: Sendable, Equatable {
    case unreachable, integerDivideByZero, integerOverflow, invalidConversionToInteger
    case memoryOutOfBounds, tableOutOfBounds, indirectCallNull, indirectCallTypeMismatch, hostAbort
}
public enum ExperimentalCapabilityResourceFailure: Sendable, Equatable {
    case fuel, hostCalls, callDepth, operandStack, nativeInstantiationAllocation, capabilityPayloadAllocation
    case requestIdentityExhaustion, nativeSessionCapacity, validationCapacity, constructionCapacity, commandCapacity
}
public enum ExperimentalCapabilityInternalFailure: Sendable, Equatable {
    case poisoned, containedPanic, invariant, registryPoisoned
}
public enum ExperimentalCapabilityUnknownFailure: Sendable, Equatable {
    case malformedNativeReport, unexpectedStatusOrOperation, unrecognizedCode, terminalState
    case unsupportedEnvironment, nativeProtocol, bridgeInvariant, nonBridgeError
}
public enum ExperimentalCapabilityFailureKind: Sendable, Equatable {
    case callerAPI(ExperimentalCapabilityAPIFailure)
    case validation(ExperimentalCapabilityValidationFailure)
    case instantiation(ExperimentalCapabilityInstantiationFailure)
    case guestTrap(ExperimentalCapabilityGuestTrap)
    case cancelled, deadlineExceeded
    case resource(ExperimentalCapabilityResourceFailure)
    case panicOrQuarantine(ExperimentalCapabilityInternalFailure)
    case unknown(ExperimentalCapabilityUnknownFailure)
}
public struct ExperimentalCapabilityNativeLocation: Sendable, Equatable {
    public let functionIndex: UInt32?
    /// Exact native absolute offset; zero can also be an import/export boundary sentinel.
    public let byteOffset: UInt32
}
public struct ExperimentalCapabilityFailure: Sendable, Equatable {
    public let kind: ExperimentalCapabilityFailureKind
    public let operation: ExperimentalCapabilityFailureOperation
    public let code: String
    public let nativeStatus: UInt32?
    public let location: ExperimentalCapabilityNativeLocation?
}

extension ExperimentalCapabilityError {
    static func localKind(_ code: String) -> ExperimentalCapabilityFailureKind {
        switch code {
        case "invalid_configuration", "invalid_module_or_startup", "invalid_invoke_arguments", "invalid_read_length", "invalid_write_length": .callerAPI(.invalidInput)
        case "construction_consumed", "validation_consumed": .callerAPI(.consumedOperation)
        case "construction_busy": .resource(.constructionCapacity)
        case "validation_busy": .resource(.validationCapacity)
        case "command_busy": .resource(.commandCapacity)
        case "closed": .unknown(.terminalState)
        case "invalid_native_report", "invalid_native_handle", "invalid_native_create", "invalid_native_i32", "invalid_native_f32", "invalid_native_value", "invalid_native_wake", "invalid_native_message", "invalid_native_none", "invalid_native_call", "invalid_native_cancel", "invalid_native_take_kind", "invalid_native_remaining", "invalid_native_post", "invalid_native_ack", "invalid_native_result": .unknown(.malformedNativeReport)
        default: .unknown(.bridgeInvariant)
        }
    }
    static func detail(_ error: any Error) -> ExperimentalCapabilityFailure {
        if let error = error as? ExperimentalCapabilityError { return error.failure }
        return ExperimentalCapabilityFailure(kind: .unknown(.nonBridgeError), operation: .localAPI,
            code: "bridge_failure", nativeStatus: nil, location: nil)
    }
}

/// Closed mapping owned by the checked native call site. No human message is read.
enum NativeDiagnostics {
    typealias Operation = ExperimentalCapabilityFailureOperation
    static func turn(_ operation: Operation) -> Bool { operation == .startup || operation == .invocation || operation == .wake }
    static func session(_ operation: Operation) -> Bool { operation != .localAPI && operation != .validation && operation != .construction }
    static func check(_ status: UInt32, _ report: MixerVmReport, operation: Operation,
                      moduleLength: Int, configuration: ExperimentalCapabilityConfiguration) throws {
        func malformed(_ code: String = "invalid_native_report") -> ExperimentalCapabilityError {
            ExperimentalCapabilityError(code, operation: operation)
        }
        guard status <= 4, report.abi_version == 1, report.status == status, report.reserved == 0,
              report.fuel_used <= configuration.fuel, report.host_calls_used <= UInt64(configuration.hostCalls) else { throw malformed() }
        var rawCode = report.code
        let code: String = try withUnsafeBytes(of: &rawCode) { bytes in
            guard let end = bytes.firstIndex(of: 0), bytes[..<end].allSatisfy({ $0 < 128 }) else { throw malformed() }
            return String(decoding: bytes[..<end], as: UTF8.self)
        }
        let function: UInt32? = report.function == .max ? nil : report.function
        guard function.map({ $0 < 2048 }) ?? true, UInt64(report.offset) <= UInt64(moduleLength) else { throw malformed() }
        if session(operation), function != nil, UInt64(report.offset) >= UInt64(moduleLength) { throw malformed() }
        if !turn(operation) && (report.fuel_used != 0 || report.host_calls_used != 0) { throw malformed() }
        if status == 0 {
            guard code.isEmpty, function == nil, report.offset == 0 else { throw malformed() }
            if operation == .startup || operation == .invocation { _ = try value(report, operation: operation) }
            else if report.value_type != 0 || report.value != 0 { throw malformed("invalid_native_value") }
            return
        }
        guard !code.isEmpty, report.value_type == 0, report.value == 0 else { throw malformed() }
        let kind = classify(status, code, operation: operation)
        if case .guestTrap = kind {
            guard function != nil, UInt64(report.offset) < UInt64(moduleLength) else { throw malformed() }
        }
        // Direct API/registry/panic reports contain no instruction position.
        let initialSegment = kind == .instantiation(.initialDataBounds) || kind == .instantiation(.initialElementBounds)
        let initialAllocation = kind == .resource(.nativeInstantiationAllocation)
        let internalFailure: Bool
        if case .panicOrQuarantine = kind { internalFailure = true } else { internalFailure = false }
        let direct = status == 3 || status == 4 || initialSegment || initialAllocation || internalFailure || code == "capability_terminal" || code == "capability_closed" || code == "unsupported_float_environment" || code == "unknown_export"
        if direct && (function != nil || report.offset != 0) { throw malformed() }
        throw ExperimentalCapabilityError(code, status: status, operation: operation, kind: kind,
            location: ExperimentalCapabilityNativeLocation(functionIndex: function, byteOffset: report.offset))
    }
    static func value(_ report: MixerVmReport, operation: Operation) throws -> ExperimentalVMValue? {
        switch report.value_type {
        case 0:
            guard report.value == 0 else { throw ExperimentalCapabilityError("invalid_native_value", operation: operation) }
            return nil
        case 1:
            guard let value = Int32(exactly: report.value) else { throw ExperimentalCapabilityError("invalid_native_i32", operation: operation) }
            return .i32(value)
        case 2: return .i64(report.value)
        case 3:
            guard let value = UInt32(exactly: report.value) else { throw ExperimentalCapabilityError("invalid_native_f32", operation: operation) }
            return .f32Bits(value)
        case 4: return .f64Bits(UInt64(bitPattern: report.value))
        default: throw ExperimentalCapabilityError("invalid_native_value", operation: operation)
        }
    }
    static func classify(_ status: UInt32, _ code: String, operation: Operation) -> ExperimentalCapabilityFailureKind {
        let validation: ExperimentalCapabilityValidationFailure?
        switch code {
        case "malformed": validation = .malformed
        case "unsupported": validation = .unsupported
        case "validation": validation = .invalidBodyOrStructure
        case "limit": validation = .configuredLimit
        case "invalid_limits": validation = .invalidLimits
        case "capability_export": validation = .requiredDefinedExport
        default: validation = nil
        }
        if let validation, status == 1 && (operation == .validation || operation == .construction) { return .validation(validation) }
        if status == 2 && operation == .construction {
            if code == "memory_out_of_bounds" { return .instantiation(.initialDataBounds) }
            if code == "table_out_of_bounds" { return .instantiation(.initialElementBounds) }
            if validation != nil { return .instantiation(.admissionRejected) }
            if code == "allocation" { return .resource(.nativeInstantiationAllocation) }
        }
        if status == 2 && turn(operation) {
            switch code {
            case "unreachable": return .guestTrap(.unreachable)
            case "integer_divide_by_zero": return .guestTrap(.integerDivideByZero)
            case "integer_overflow": return .guestTrap(.integerOverflow)
            case "invalid_conversion_to_integer": return .guestTrap(.invalidConversionToInteger)
            case "memory_out_of_bounds": return .guestTrap(.memoryOutOfBounds)
            case "table_out_of_bounds": return .guestTrap(.tableOutOfBounds)
            case "indirect_call_null": return .guestTrap(.indirectCallNull)
            case "indirect_call_type_mismatch": return .guestTrap(.indirectCallTypeMismatch)
            case "host_abort": return .guestTrap(.hostAbort)
            case "cancelled": return .cancelled
            case "capability_turn_timeout": return .deadlineExceeded
            case "fuel_exhausted": return .resource(.fuel)
            case "host_call_limit": return .resource(.hostCalls)
            case "call_depth_exceeded": return .resource(.callDepth)
            case "operand_stack_exceeded": return .resource(.operandStack)
            case "capability_identifier_exhausted": return .resource(.requestIdentityExhaustion)
            case "unsupported_float_environment": return .unknown(.unsupportedEnvironment)
            default: break
            }
        }
        if status == 2 {
            if code == "capability_allocation" && (turn(operation) || operation == .post) { return .resource(.capabilityPayloadAllocation) }
            if operation == .invocation && code == "unknown_export" { return .callerAPI(.unknownExport) }
            if operation == .invocation && code == "invalid_arguments" { return .callerAPI(.invalidInvocation) }
            if session(operation) && (code == "capability_closed" || code == "capability_terminal") { return .unknown(.terminalState) }
            if (turn(operation) || operation == .enableEffects) && ["capability_protocol", "unsupported", "invalid_limits"].contains(code) { return .unknown(.nativeProtocol) }
        }
        if code == "capability_poisoned" && ((status == 2 && (turn(operation) || operation == .enableEffects)) || (status == 4 && session(operation))) { return .panicOrQuarantine(.poisoned) }
        if status == 3 {
            switch code {
            case "invalid_arguments": return .callerAPI(.invalidNativeArguments)
            case "capability_state" where turn(operation) || operation == .enableEffects: return .callerAPI(.invalidLifecycleState)
            case "session_busy" where turn(operation) || operation == .enableEffects || operation == .readMemory || operation == .writeMemory: return .callerAPI(.nativeBusy)
            case "session_limit" where operation == .construction: return .resource(.nativeSessionCapacity)
            case "invalid_session" where operation == .close: return .callerAPI(.invalidNativeSession)
            default: break
            }
        }
        if status == 4 {
            if code == "internal_panic" { return .panicOrQuarantine(.containedPanic) }
            if code == "capability_invariant" && session(operation) { return .panicOrQuarantine(.invariant) }
            if code == "registry_poisoned" && (session(operation) || operation == .construction) { return .panicOrQuarantine(.registryPoisoned) }
        }
        let known: Set<String> = ["malformed", "unsupported", "validation", "limit", "invalid_limits", "capability_export", "memory_out_of_bounds", "table_out_of_bounds", "allocation", "unreachable", "integer_divide_by_zero", "integer_overflow", "invalid_conversion_to_integer", "indirect_call_null", "indirect_call_type_mismatch", "host_abort", "cancelled", "capability_turn_timeout", "fuel_exhausted", "host_call_limit", "call_depth_exceeded", "operand_stack_exceeded", "capability_identifier_exhausted", "unsupported_float_environment", "capability_allocation", "unknown_export", "invalid_arguments", "capability_closed", "capability_terminal", "capability_protocol", "capability_poisoned", "capability_state", "session_busy", "session_limit", "invalid_session", "internal_panic", "capability_invariant", "registry_poisoned"]
        return .unknown(known.contains(code) ? .unexpectedStatusOrOperation : .unrecognizedCode)
    }
}
