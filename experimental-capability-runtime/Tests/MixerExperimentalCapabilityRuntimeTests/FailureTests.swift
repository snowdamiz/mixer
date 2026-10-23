import Foundation
import Testing
import CMixerVMCapability
import MixerCapabilities
@testable import MixerExperimentalCapabilityRuntime

private func nativeReport(_ status: UInt32, _ code: String, function: UInt32 = .max, offset: UInt32 = 0) -> MixerVmReport {
    var report = MixerVmReport(); report.abi_version = 1; report.status = status; report.function = function; report.offset = offset
    withUnsafeMutableBytes(of:&report.code) { bytes in
        for (index,value) in code.utf8.prefix(47).enumerated() { bytes[index] = value }
    }
    withUnsafeMutableBytes(of:&report.message) { bytes in
        for (index,value) in "unreachable integer division by zero cancelled allocation".utf8.enumerated() { bytes[index] = value }
    }
    return report
}
private func reportFailure(_ report: MixerVmReport, returned: UInt32? = nil, operation: ExperimentalCapabilityFailureOperation = .invocation) throws -> ExperimentalCapabilityError {
    do { try NativeDiagnostics.check(returned ?? report.status,report,operation:operation,moduleLength:128,configuration:.init()) }
    catch let error as ExperimentalCapabilityError { return error }
    throw ReportUnexpectedSuccess()
}
private struct ReportUnexpectedSuccess: Error {}

extension ExperimentalBridgeTests {
    @Test func checkedNativeMappingKeepsValidationInstantiationRuntimeAndInterruptionsDistinct() throws {
        typealias Kind = ExperimentalCapabilityFailureKind
        typealias Operation = ExperimentalCapabilityFailureOperation
        let validation: [(String,ExperimentalCapabilityValidationFailure)] = [("malformed",.malformed),("unsupported",.unsupported),("validation",.invalidBodyOrStructure),("limit",.configuredLimit),("invalid_limits",.invalidLimits),("capability_export",.requiredDefinedExport)]
        for (code,kind) in validation {
            for operation in [Operation.validation,.construction] {
                #expect(try reportFailure(nativeReport(1,code,offset:128),operation:operation).failure.kind == .validation(kind))
            }
            #expect(try reportFailure(nativeReport(2,code),operation:.construction).failure.kind == .instantiation(.admissionRejected))
        }
        let traps: [(String,ExperimentalCapabilityGuestTrap)] = [("unreachable",.unreachable),("integer_divide_by_zero",.integerDivideByZero),("integer_overflow",.integerOverflow),("invalid_conversion_to_integer",.invalidConversionToInteger),("memory_out_of_bounds",.memoryOutOfBounds),("table_out_of_bounds",.tableOutOfBounds),("indirect_call_null",.indirectCallNull),("indirect_call_type_mismatch",.indirectCallTypeMismatch),("host_abort",.hostAbort)]
        for (code,kind) in traps {
            for operation in [Operation.startup,.invocation,.wake] {
                let error = try reportFailure(nativeReport(2,code,function:1,offset:20),operation:operation)
                #expect(error.failure.kind == .guestTrap(kind) && error.failure.operation == operation)
                #expect(error.failure.location?.functionIndex == 1 && error.failure.location?.byteOffset == 20)
            }
        }
        let rows: [(UInt32,String,Operation,Kind)] = [
            (2,"memory_out_of_bounds",.construction,.instantiation(.initialDataBounds)),(2,"table_out_of_bounds",.construction,.instantiation(.initialElementBounds)),
            (2,"cancelled",.wake,.cancelled),(2,"capability_turn_timeout",.startup,.deadlineExceeded),
            (2,"fuel_exhausted",.invocation,.resource(.fuel)),(2,"host_call_limit",.invocation,.resource(.hostCalls)),
            (2,"call_depth_exceeded",.invocation,.resource(.callDepth)),(2,"operand_stack_exceeded",.invocation,.resource(.operandStack)),
            (2,"allocation",.construction,.resource(.nativeInstantiationAllocation)),(2,"capability_allocation",.post,.resource(.capabilityPayloadAllocation)),
            (2,"capability_identifier_exhausted",.wake,.resource(.requestIdentityExhaustion)),(2,"unknown_export",.invocation,.callerAPI(.unknownExport)),
            (2,"invalid_arguments",.invocation,.callerAPI(.invalidInvocation)),(2,"capability_closed",.startup,.unknown(.terminalState)),
            (2,"capability_terminal",.take,.unknown(.terminalState)),(2,"unsupported_float_environment",.startup,.unknown(.unsupportedEnvironment)),
            (2,"capability_protocol",.enableEffects,.unknown(.nativeProtocol)),(2,"capability_poisoned",.wake,.panicOrQuarantine(.poisoned)),
            (4,"capability_poisoned",.ackExit,.panicOrQuarantine(.poisoned)),(3,"invalid_arguments",.validation,.callerAPI(.invalidNativeArguments)),
            (3,"capability_state",.startup,.callerAPI(.invalidLifecycleState)),(3,"session_busy",.readMemory,.callerAPI(.nativeBusy)),
            (3,"session_limit",.construction,.resource(.nativeSessionCapacity)),(3,"invalid_session",.close,.callerAPI(.invalidNativeSession)),
            (4,"internal_panic",.validation,.panicOrQuarantine(.containedPanic)),(4,"capability_invariant",.take,.panicOrQuarantine(.invariant)),
            (4,"registry_poisoned",.construction,.panicOrQuarantine(.registryPoisoned))]
        for (status,code,operation,kind) in rows { #expect(try reportFailure(nativeReport(status,code),operation:operation).failure.kind == kind) }
    }
    @Test func negativeReportCombinationsAndMisleadingMessagesNeverManufactureGuestTrap() throws {
        for status in [UInt32(1),3,4] {
            let error = try reportFailure(nativeReport(status,"unreachable"))
            #expect(error.failure.kind == .unknown(.unexpectedStatusOrOperation))
        }
        #expect(try reportFailure(nativeReport(2,"unreachable",function:1,offset:20),operation:.validation).failure.kind == .unknown(.unexpectedStatusOrOperation))
        #expect(try reportFailure(nativeReport(2,"future_native_error")).failure.kind == .unknown(.unrecognizedCode))
        #expect(try reportFailure(nativeReport(2,"session_terminal")).failure.kind == .unknown(.unrecognizedCode))
        #expect(try reportFailure(nativeReport(4,"session_poisoned")).failure.kind == .unknown(.unrecognizedCode))
        #expect(try reportFailure(nativeReport(2,"future_native_error")).failure.kind == .unknown(.unrecognizedCode))
        var corrupt: [MixerVmReport] = [nativeReport(0,"unreachable"),nativeReport(5,"unreachable")]
        var report = nativeReport(2,"unreachable",function:1,offset:20)
        report.abi_version = 2; corrupt.append(report)
        report = nativeReport(2,"unreachable",function:1,offset:20); report.reserved=1;corrupt.append(report)
        report = nativeReport(2,"unreachable",function:2048,offset:20);corrupt.append(report)
        report = nativeReport(2,"unreachable",function:1,offset:129);corrupt.append(report)
        report = nativeReport(2,"unreachable");corrupt.append(report) // No reported function.
        report = nativeReport(2,"unreachable",function:1,offset:20);report.value_type=1;corrupt.append(report)
        report = nativeReport(2,"unreachable",function:1,offset:20);report.fuel_used=1_000_001;corrupt.append(report)
        report = nativeReport(2,"unreachable",function:1,offset:20);report.host_calls_used=1025;corrupt.append(report)
        report = nativeReport(2,"unreachable",function:1,offset:20);_ = withUnsafeMutableBytes(of:&report.code){$0.initializeMemory(as:UInt8.self,repeating:65)};corrupt.append(report)
        report = nativeReport(2,"unreachable",function:1,offset:20);withUnsafeMutableBytes(of:&report.code){$0[0]=255};corrupt.append(report)
        for report in corrupt {
            let error = try reportFailure(report)
            #expect(error.code == "invalid_native_report" && error.nativeStatus == nil)
            #expect(error.failure.kind == .unknown(.malformedNativeReport) && error.failure.operation == .invocation)
        }
        #expect(try reportFailure(nativeReport(2,"cancelled"),returned:3).failure.kind == .unknown(.malformedNativeReport))
        for code in ["memory_out_of_bounds","table_out_of_bounds","allocation"] {
            #expect(try reportFailure(nativeReport(2,code,function:1,offset:20),operation:.construction).failure.kind == .unknown(.malformedNativeReport))
        }
        #expect(try reportFailure(nativeReport(2,"fuel_exhausted",function:1,offset:128)).failure.kind == .unknown(.malformedNativeReport))
        for (type,value,code) in [(UInt32(1),Int64(Int32.max)+1,"invalid_native_i32"),(UInt32(3),Int64(-1),"invalid_native_f32"),(UInt32(9),Int64(0),"invalid_native_value")] {
            var report=nativeReport(0,"");report.value_type=type;report.value=value
            #expect(try reportFailure(report).code == code)
        }
        let known = try reportFailure(nativeReport(2,"cancelled"))
        #expect(known.description == "cancelled" && known == ExperimentalCapabilityError("cancelled",status:2))
        #expect(known.failure.kind == .cancelled)
        #expect(known.failure.location?.functionIndex == nil && known.failure.location?.byteOffset == 0)
    }
    @Test func autonomousWakeFailurePublishesFirstTypedDetailThroughRealConcreteStorage() async throws {
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-validation-wake-"+UUID().uuidString)
        defer { try? FileManager.default.removeItem(at:directory) }
        let store=try AppPrivateKeyValueStore(directory:directory,namespaces:["entries"])
        let imported=ValidationGuest.Import(module:"mixer.capability.v1",name:"storage_put",parameters:[0x7f,0x7f,0x7f],result:0x7f)
        var run=GuestProgram.i(1024)
        run += GuestProgram.i(Int32(GuestProgram.put.count));run += GuestProgram.i(16);run += [0x10,0,0x0b]
        let module=ValidationGuest.build(memoryMinimum:1,memoryMaximum:1,imports:[imported],wake:[0,0x0b],run:run,arguments:GuestProgram.put)
        try await ExperimentalCapabilityValidator.prepare(module:module,startupExport:"boot").validate()
        let session=try await bridgeSession(module,store:store)
        _ = try await session.startup();try await session.enableEffects();_ = try await session.invoke("run")
        try await bridgeEventually { session.status.drained }
        let first=session.status.failureDetail
        #expect(first?.kind == .guestTrap(.unreachable) && first?.operation == .wake)
        #expect(session.status.failure == "unreachable" && session.status.acknowledgements == 1)
        session.close();#expect(session.status.failureDetail == first)
        await store.close()
    }
}
