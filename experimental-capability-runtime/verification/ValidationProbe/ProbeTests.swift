import Foundation
import Testing
@testable import MixerExperimentalCapabilityRuntime

@Suite(.serialized) struct ValidationOwnerProbeTests {
    @Test func malformedRealValidationReturnQuarantinesEvenAfterOperationDeinit() async throws {
        ValidationProbeHooks.mode.withLock{$0 = .malformed}
        for _ in 0..<2 {
            var operation:ExperimentalCapabilityValidation? = try ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot")
            do { try await operation!.validate();Issue.record("injected report fault accepted") }
            catch let error as ExperimentalCapabilityError {
                #expect(error.code == "invalid_native_report" && error.nativeStatus == nil)
                #expect(error.failure.kind == .unknown(.malformedNativeReport) && error.failure.operation == .validation)
            }
            operation = nil
            await withCheckedContinuation { continuation in ValidationQueue.serial.async { continuation.resume() } }
        }
        #expect(throws:ExperimentalCapabilityError("validation_busy")) {
            try ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot")
        }
    }
    @Test func cancellationAtRealCReturnHoldsCapacityUntilWorkerFrameReturns() async throws {
        let gate=ValidationProbeGate();ValidationProbeHooks.mode.withLock{$0 = .held(gate)}
        defer { gate.release();ValidationProbeHooks.mode.withLock{$0 = .ordinary} }
        let first=try ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot")
        let pending=Task { try await first.validate() }
        try await bridgeEventually { gate.entered }
        let second=try ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot")
        pending.cancel();first.cancel()
        #expect(throws:ExperimentalCapabilityError("validation_busy")) {
            try ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot")
        }
        gate.release();await #expect(throws:CancellationError.self) { try await pending.value }
        second.cancel();ValidationProbeHooks.mode.withLock{$0 = .ordinary}
        let a=try ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot")
        let b=try ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot")
        try await a.validate();try await b.validate()
    }
    @Test func rejectedCancelledSecondCallerCannotCancelFirstValidation() async throws {
        let gate=ValidationProbeGate();ValidationProbeHooks.mode.withLock{$0 = .held(gate)}
        defer { gate.release();ValidationProbeHooks.mode.withLock{$0 = .ordinary} }
        let operation=try ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot")
        let first=Task { try await operation.validate() }
        try await bridgeEventually { gate.entered }
        let second=Task { try await operation.validate() };second.cancel()
        await #expect(throws:ExperimentalCapabilityError("validation_consumed")) { try await second.value }
        gate.release();try await first.value
    }
}
