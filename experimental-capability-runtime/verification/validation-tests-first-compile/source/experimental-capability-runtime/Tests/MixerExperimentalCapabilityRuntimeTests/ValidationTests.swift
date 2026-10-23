import Foundation
import Dispatch
import Testing
import MixerCapabilities
@testable import MixerExperimentalCapabilityRuntime

private func validationFailure(_ module: Data, configuration: ExperimentalCapabilityConfiguration = .init(), startup: String = "boot") async throws -> ExperimentalCapabilityError {
    do { try await ExperimentalCapabilityValidator.prepare(module: module, startupExport: startup, configuration: configuration).validate() }
    catch let error as ExperimentalCapabilityError { return error }
    throw TestValidationFailure()
}
private struct TestValidationFailure: Error {}
private func validationSession(_ module: Data, configuration: ExperimentalCapabilityConfiguration = .init()) async throws -> ExperimentalCapabilitySession {
    try await ExperimentalCapabilitySession.prepare(module: module, startupExport: "boot", configuration: configuration,
        policy: CapabilityPolicy(installed: [],manifest: []), adapters: InstalledCapabilityAdapters()).create()
}
extension ExperimentalBridgeTests {
    @Test func validationChecksUncalledBodiesAndExactImportWakeStartupMemory() async throws {
        try await ExperimentalCapabilityValidator.prepare(module: ValidationGuest.build(boot: [0,0x0b]), startupExport: "boot").validate()
        let invalid = try await validationFailure(ValidationGuest.build(extraBodies: [[0x41,0,0x0b]]))
        #expect(invalid.failure.kind == .validation(.invalidBodyOrStructure))
        #expect(invalid.failure.location?.functionIndex == 3)
        let checkpoint = ValidationGuest.Import(module: "mixer",name: "checkpoint",parameters: [],result: nil)
        let cases = [ValidationGuest.build(omitWake: true), ValidationGuest.build(wakeResult: 0x7f,wake: [0x41,0,0x0b]),
            ValidationGuest.build(startupParameters: [0x7f]), ValidationGuest.build(imports: [checkpoint],importedStartup: true),
            ValidationGuest.build(imports: [checkpoint],importedWake: true), ValidationGuest.build(memoryCount: 0),
            ValidationGuest.build(memoryCount: 2), ValidationGuest.build(memoryFlags: 3), ValidationGuest.build(start: true)]
        for module in cases { #expect((try await validationFailure(module)).nativeStatus == 1) }
        let names = ["http_request","storage_get","storage_put","storage_delete","cancel","poll"]
        for (index,name) in names.enumerated() {
            let parameters: [UInt8] = index < 4 ? [0x7f,0x7f,0x7f] : index == 4 ? [0x7e] : [0x7e,0x7f,0x7f,0x7f]
            try await ExperimentalCapabilityValidator.prepare(module: ValidationGuest.build(imports: [.init(module:"mixer.capability.v1",name:name,parameters:parameters,result:0x7f)]),startupExport:"boot").validate()
            for bad in [ValidationGuest.Import(module:"foreign",name:name,parameters:parameters,result:0x7f), .init(module:"mixer.capability.v1",name:name+"_other",parameters:parameters,result:0x7f), .init(module:"mixer.capability.v1",name:name,parameters:[],result:nil)] {
                #expect((try await validationFailure(ValidationGuest.build(imports: [bad]))).failure.kind == .validation(.unsupported))
            }
        }
    }
    @Test func zeroPageValidationAndConstructionAgreeWithoutRoundingUp() async throws {
        for maximum in [Optional<UInt32>(0),nil] {
            let module = ValidationGuest.build(memoryMaximum: maximum)
            try await ExperimentalCapabilityValidator.prepare(module:module,startupExport:"boot",configuration:.init(memoryPages:0)).validate()
            let session = try await validationSession(module,configuration:.init(memoryPages:0))
            _ = try await session.startup(); try await session.writeMemory(offset:0,bytes:Data())
            #expect(try await session.readMemory(offset:0,count:0).isEmpty)
            do { _ = try await session.readMemory(offset:0,count:1); Issue.record("zero memory widened") }
            catch let error as ExperimentalCapabilityError { #expect(error.failure.kind == .callerAPI(.invalidNativeArguments)) }
            #expect(try await session.invoke("run").value == .i32(0))
            session.close(); try await bridgeEventually { session.status.drained }
        }
        for module in [ValidationGuest.build(memoryMaximum:1),ValidationGuest.build(memoryMinimum:1,memoryMaximum:1)] {
            #expect((try await validationFailure(module,configuration:.init(memoryPages:0))).failure.kind == .validation(.configuredLimit))
        }
        for bytes in [UInt64(1),65535,65536,65537] {
            let pages = UInt32(bytes/65536)
            let module = ValidationGuest.build(memoryMinimum:pages,memoryMaximum:pages)
            try await ExperimentalCapabilityValidator.prepare(module:module,startupExport:"boot",configuration:.init(memoryPages:pages)).validate()
        }
    }
    @Test func validationIsNotInstantiationOrStartupProofAndFailuresKeepContext() async throws {
        for (module,kind) in [(ValidationGuest.build(badData:true),ExperimentalCapabilityFailureKind.instantiation(.initialDataBounds)),(ValidationGuest.build(badElement:true),.instantiation(.initialElementBounds))] {
            try await ExperimentalCapabilityValidator.prepare(module:module,startupExport:"boot",configuration:.init(memoryPages:0)).validate()
            do { _ = try await validationSession(module,configuration:.init(memoryPages:0)); Issue.record("bad initial segment created") }
            catch let error as ExperimentalCapabilityError {
                #expect(error.failure.kind == kind && error.failure.operation == .construction)
                #expect(error == ExperimentalCapabilityError(error.code,status:2))
            }
        }
        let module = ValidationGuest.build(boot:[0,0x0b])
        try await ExperimentalCapabilityValidator.prepare(module:module,startupExport:"boot").validate()
        let session = try await validationSession(module)
        do { _ = try await session.startup(); Issue.record("startup trap missing") }
        catch let error as ExperimentalCapabilityError {
            #expect(error.failure.kind == .guestTrap(.unreachable) && error.failure.operation == .startup)
            #expect(session.status.failureDetail == error.failure)
        }
        session.close(); try await bridgeEventually { session.status.drained }
        #expect(session.status.failureDetail?.kind == .guestTrap(.unreachable))
    }
    @Test func realRuntimeResourceFailuresAreNotClassifiedAsGuestTraps() async throws {
        let spin: [UInt8] = [0x03,0x40,0x0c,0,0x0b,0,0x0b]
        let checkpoint = ValidationGuest.Import(module:"mixer",name:"checkpoint",parameters:[],result:nil)
        let cases: [(Data,ExperimentalCapabilityConfiguration,ExperimentalCapabilityFailureKind)] = [
            (ValidationGuest.build(run:spin),.init(fuel:50),.resource(.fuel)),
            (ValidationGuest.build(imports:[checkpoint],run:[0x10,0,0x41,0,0x0b]),.init(hostCalls:0),.resource(.hostCalls)),
            (ValidationGuest.build(run:[0x10,2,0x0b]),.init(callDepth:1),.resource(.callDepth)),
            (ValidationGuest.build(run:spin),.init(turnMilliseconds:1),.deadlineExceeded)]
        for (module,configuration,kind) in cases {
            let session = try await validationSession(module,configuration:configuration)
            _ = try await session.startup()
            do { _ = try await session.invoke("run"); Issue.record("expected runtime failure") }
            catch let error as ExperimentalCapabilityError { #expect(error.failure.kind == kind && error.failure.operation == .invocation) }
            session.close(); try await bridgeEventually { session.status.drained }
        }
    }
    @Test func validationBoundsAndTwoPermitsAreIndependentOfConstructionCapacity() async throws {
        let module = ValidationGuest.build(), one = try ExperimentalCapabilityValidator.prepare(module:module,startupExport:"boot")
        var two: ExperimentalCapabilityValidation? = try ExperimentalCapabilityValidator.prepare(module:module,startupExport:"boot")
        #expect(throws:ExperimentalCapabilityError("validation_busy")) { try ExperimentalCapabilityValidator.prepare(module:module,startupExport:"boot") }
        #expect(throws:ExperimentalCapabilityError("invalid_module_or_startup")) { try ExperimentalCapabilityValidator.prepare(module:Data(count:4_194_305),startupExport:"boot") }
        #expect(throws:ExperimentalCapabilityError("invalid_module_or_startup")) { try ExperimentalCapabilityValidator.prepare(module:module,startupExport:String(repeating:"a",count:4097)) }
        #expect(throws:ExperimentalCapabilityError("invalid_configuration")) { try ExperimentalCapabilityValidator.prepare(module:module,startupExport:"boot",configuration:.init(memoryPages:65)) }
        var sessions: [ExperimentalCapabilitySession] = []
        for _ in 0..<16 { sessions.append(try await validationSession(module,configuration:.init(memoryPages:0))) }
        try await one.validate()
        sessions.forEach{$0.close()}; try await bridgeEventually { sessions.allSatisfy{$0.status.drained} }
        two = nil; #expect(two == nil)
        await #expect(throws:ExperimentalCapabilityError("validation_consumed")) { try await one.validate() }
        let name = String(repeating:"a",count:4096)
        let padded = ValidationGuest.padded(ValidationGuest.build(startup:name),count:4_194_304)
        #expect(padded.count == 4_194_304)
        try await ExperimentalCapabilityValidator.prepare(module:padded,startupExport:name).validate()
    }
    @Test func validationOneShotConcurrentAndCancelledQueueRetainFiniteOwnership() async throws {
        let operation = try ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot")
        let results = await withTaskGroup(of:Bool.self) { group in
            for _ in 0..<2 { group.addTask { do { try await operation.validate(); return true } catch { return false } } }
            var results:[Bool]=[]; for await result in group { results.append(result) }; return results
        }
        #expect(results.filter{$0}.count == 1)
        operation.cancel() // A completed success stays complete.
        let unused = try ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot")
        unused.cancel(); await #expect(throws:ExperimentalCapabilityError("validation_consumed")) { try await unused.validate() }
        let gate = ValidationTestGate(); ValidationQueue.serial.async { gate.hold() }; defer { gate.release() }
        try await bridgeEventually { gate.entered }
        let first = try ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot")
        let second = try ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot")
        let pending = Task { try await first.validate() }
        try await Task.sleep(for:.milliseconds(15)); pending.cancel()
        #expect(throws:ExperimentalCapabilityError("validation_busy")) { try ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot") }
        gate.release(); await #expect(throws:CancellationError.self) { try await pending.value }
        second.cancel()
        try await ExperimentalCapabilityValidator.prepare(module:ValidationGuest.build(),startupExport:"boot").validate()
    }
}
private final class ValidationTestGate: @unchecked Sendable {
    private let condition=NSCondition(); private var released=false; private var started=false
    func hold() { condition.lock(); started=true; let end=Date().addingTimeInterval(5); while !released { if !condition.wait(until:end) { break } }; condition.unlock() }
    func release() { condition.lock();released=true;condition.broadcast();condition.unlock() }
    var entered:Bool { condition.lock();defer{condition.unlock()};return started }
}
