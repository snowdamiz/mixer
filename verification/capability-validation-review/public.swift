import Foundation
import MixerCapabilities
import MixerExperimentalCapabilityRuntime

// Original public-consumer fixture: three defined functions and zero-page memory.
// No implementation fixture, @testable access, C calls or injected report is used.
func uleb(_ n: Int) -> [UInt8] {
    var n = n, result: [UInt8] = []
    repeat { let low = UInt8(n & 127); n >>= 7; result.append(low | (n == 0 ? 0 : 128)) } while n != 0
    return result
}
func name(_ value: String) -> [UInt8] { uleb(value.utf8.count) + Array(value.utf8) }
func module(unused: [UInt8] = [0x41, 42, 0x0b], memoryMaximum: UInt8 = 0,
            wake: String = "mixer_guest_capability_ready_v1", startup: [UInt8] = [0x0b]) -> Data {
    var data: [UInt8] = [0, 97, 115, 109, 1, 0, 0, 0]
    func section(_ id: UInt8, _ bytes: [UInt8]) { data.append(id); data += uleb(bytes.count); data += bytes }
    section(1, [2, 0x60, 0, 0, 0x60, 0, 1, 0x7f])
    section(3, [3, 0, 0, 1])
    section(5, [1, 1, 0, memoryMaximum])
    var exports: [UInt8] = [3]
    exports += name("entry"); exports += [0, 0]
    exports += name(wake); exports += [0, 1]
    exports += name("value"); exports += [0, 2]
    section(7, exports)
    var code: [UInt8] = [3]
    for body in [startup, [0x0b], unused] { code += uleb(body.count + 1); code += [0]; code += body }
    section(10, code)
    return Data(data)
}

@main struct PublicReview {
    @MainActor static var count = 0
    @MainActor static func expect(_ condition: Bool, _ label: String) {
        precondition(condition, label); count += 1
    }
    @MainActor static func rejected(_ data: Data, expected: ExperimentalCapabilityFailureKind) async throws {
        do {
            try await ExperimentalCapabilityValidator.prepare(module: data, startupExport: "entry", configuration: .init(memoryPages: 0)).validate()
            preconditionFailure("accepted invalid module")
        } catch let error as ExperimentalCapabilityError {
            expect(error.failure.kind == expected, "wrong validation category: \(error.failure)")
            expect(error.failure.operation == .validation, "wrong operation")
        }
    }
    @MainActor static func main() async throws {
        let good = module()
        let foreign = NSMutableData(data: good)
        let operation = try ExperimentalCapabilityValidator.prepare(module: Data(referencing: foreign), startupExport: "entry", configuration: .init(memoryPages: 0))
        foreign.resetBytes(in: NSRange(location: 0, length: foreign.length))
        try await operation.validate()
        expect(foreign as Data != good, "foreign backing did not mutate")
        do { try await operation.validate(); preconditionFailure("reused validation") }
        catch let error as ExperimentalCapabilityError { expect(error.failure.kind == .callerAPI(.consumedOperation), "one-shot failure") }
        try await rejected(module(unused: [0x0b]), expected: .validation(.invalidBodyOrStructure))
        try await rejected(module(unused: [0xfd, 0, 0x0b]), expected: .validation(.unsupported))
        try await rejected(module(memoryMaximum: 1), expected: .validation(.configuredLimit))
        try await rejected(module(wake: "other"), expected: .validation(.requiredDefinedExport))
        let held = try ExperimentalCapabilityValidator.prepare(module: good, startupExport: "entry")
        let second = try ExperimentalCapabilityValidator.prepare(module: good, startupExport: "entry")
        do { _ = try ExperimentalCapabilityValidator.prepare(module: good, startupExport: "entry"); preconditionFailure("third validation admitted") }
        catch let error as ExperimentalCapabilityError { expect(error.failure.kind == .resource(.validationCapacity), "capacity kind") }
        held.cancel()
        do { try await held.validate(); preconditionFailure("cancelled validation restarted") }
        catch let error as ExperimentalCapabilityError { expect(error.failure.kind == .callerAPI(.consumedOperation), "cancelled one-shot kind") }
        try await second.validate()
        for trapping in [false, true] {
            let bytes = module(startup: trapping ? [0, 0x0b] : [0x0b])
            try await ExperimentalCapabilityValidator.prepare(module: bytes, startupExport: "entry", configuration: .init(memoryPages: 0)).validate()
            let session = try await ExperimentalCapabilitySession.prepare(module: bytes, startupExport: "entry", configuration: .init(memoryPages: 0), policy: CapabilityPolicy(installed: [], manifest: []), adapters: InstalledCapabilityAdapters()).create()
            if trapping {
                do { _ = try await session.startup(); preconditionFailure("startup trap absent") }
                catch let error as ExperimentalCapabilityError {
                    expect(error.failure.kind == .guestTrap(.unreachable), "startup kind")
                    expect(error.failure.operation == .startup && error.failure.location?.functionIndex == 0, "startup location")
                    expect(session.status.failureDetail == error.failure, "first failure detail")
                }
            } else {
                _ = try await session.startup()
                expect(try await session.invoke("value").value == .i32(42), "zero-page execution")
                expect(try await session.readMemory(offset: 0, count: 0).isEmpty, "zero-page empty read")
                do { try await session.writeMemory(offset: 0, bytes: Data([1])); preconditionFailure("zero memory widened") }
                catch let error as ExperimentalCapabilityError { expect(error.failure.kind == .callerAPI(.invalidNativeArguments), "memory API classification") }
            }
            let failure = session.status.failureDetail
            session.close()
            let deadline = ContinuousClock.now.advanced(by: .seconds(5))
            while !session.status.drained && ContinuousClock.now < deadline { try await Task.sleep(for: .milliseconds(5)) }
            expect(session.status.drained, "drain deadline")
            expect(session.status.failureDetail == failure, "cleanup replaced first cause")
        }
        print("Root independent public validator review passed \(count) checks; no signed activation or device qualification")
    }
}
