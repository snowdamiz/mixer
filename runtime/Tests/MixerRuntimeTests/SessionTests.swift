import Foundation
import Testing
import MixerRuntime

@Suite(.serialized)
struct SessionTests {
    // Independently authored small Wasm counter: mutable global plus one memory page.
    static let counter = Data([0,97,115,109,1,0,0,0,
        1,5,1,96,0,1,127,3,2,1,0,5,4,1,1,1,1,
        6,6,1,127,1,65,0,11,7,7,1,3,114,117,110,0,0,
        10,20,1,18,0,35,0,65,1,106,36,0,65,0,35,0,54,2,0,35,0,11])

    func expectFailure(_ code: String, _ body: () throws -> Void) {
        do { try body(); Issue.record("Expected \(code)") }
        catch let failure as VMFailure { #expect(failure.code == code) }
        catch { Issue.record("Unexpected error: \(error)") }
    }

    @Test func completeValidationHonorsProfileAndLimitsWithoutTakingSessionCapacity() throws {
        var sessions: [VMSession] = []
        defer { for session in sessions { try? session.close() } }
        for _ in 0..<16 { sessions.append(try VMSession(module: Self.counter, profile: .integerV1)) }
        for profile in VMProfile.allCases {
            try VMValidator.validate(Self.counter, profile: profile)
            expectFailure("invalid_limits") {
                try VMValidator.validate(Self.counter, profile: profile, limits: VMLimits(memoryPages: 65))
            }
            do { try VMValidator.validate(Self.counter, profile: profile, limits: VMLimits(memoryPages: 0)); Issue.record("Accepted memory beyond signed limit") }
            catch let failure as VMFailure { #expect(failure.status == 1) }
        }
        let float = Data([0,97,115,109,1,0,0,0,1,6,1,96,1,0x7d,1,0x7d,
            3,2,1,0,7,7,1,3,114,117,110,0,0,10,6,1,4,0,32,0,11])
        try VMValidator.validate(float, profile: .numericV2)
        do { try VMValidator.validate(float, profile: .integerV1); Issue.record("Accepted uninstalled numeric profile") }
        catch let failure as VMFailure { #expect(failure.status == 1) }
        var invalid = Self.counter; invalid[invalid.count-1] = 0xff
        do { try VMValidator.validate(invalid, profile: .integerV1); Issue.record("Accepted malformed final instruction") }
        catch let failure as VMFailure { #expect(failure.status == 1) }
    }

    @Test func stateAndMemoryPersistWithoutBorrowingSource() throws {
        var bytes = Self.counter
        let session = try VMSession(module: bytes, profile: .integerV1)
        bytes.resetBytes(in: 0..<bytes.count)
        for i in 1...3 {
            let result = try session.invoke("run")
            #expect(result.value == .i32(Int32(i)))
            #expect(result.fuelUsed == 9)
        }
        #expect(try session.readMemory(offset: 0, count: 4) == Data([3,0,0,0]))
        try session.writeMemory(offset: 7, bytes: Data([255,0,42]))
        #expect(try session.readMemory(offset: 7, count: 3) == Data([255,0,42]))
        try session.close()
        try session.close()
        expectFailure("invalid_session") { _ = try session.invoke("run") }
    }

    @Test func memoryBoundsAreAtomicAndDoNotTerminate() throws {
        let session = try VMSession(module: Self.counter, profile: .integerV1)
        try session.writeMemory(offset: 65534, bytes: Data([9,8]))
        expectFailure("memory_out_of_bounds") { try session.writeMemory(offset: 65534, bytes: Data([1,2,3])) }
        #expect(try session.readMemory(offset: 65534, count: 2) == Data([9,8]))
        #expect(try session.readMemory(offset: 65536, count: 0).isEmpty)
        expectFailure("memory_out_of_bounds") { _ = try session.readMemory(offset: 65537, count: 0) }
        expectFailure("invalid_arguments") { _ = try session.readMemory(offset: 0, count: -1) }
        expectFailure("invalid_arguments") { _ = try session.readMemory(offset: 0, count: Int.max) }
        expectFailure("invalid_arguments") { try session.writeMemory(offset: 0, bytes: Data(count: 1_048_577)) }
        #expect(try session.invoke("run").value == .i32(1))
    }

    @Test func cancellationAndTrapsCannotReuseMutatedState() throws {
        let cancelled = try VMSession(module: Self.counter, profile: .integerV1)
        try cancelled.cancel(); try cancelled.cancel()
        expectFailure("session_terminal") { _ = try cancelled.invoke("run") }
        let trapped = try VMSession(module: Self.counter, profile: .integerV1, limits: VMLimits(fuel: 8))
        do { _ = try trapped.invoke("run"); Issue.record("Expected fuel exhaustion") }
        catch let failure as VMFailure { #expect(failure.code == "fuel_exhausted"); #expect(failure.fuelUsed == 8) }
        expectFailure("session_terminal") { _ = try trapped.readMemory(offset: 0, count: 4) }
        try trapped.close()
    }

    @Test func profileAndFloatPayloadsStayExplicit() throws {
        for (profile, type, value) in [(VMProfile.numericV2, UInt8(0x7d), VMValue.f32Bits(0x7fa12345)),
                                      (.tableMemoryV3, 0x7c, .f64Bits(0xfff0123456789abc))] {
            let identity = Data([0,97,115,109,1,0,0,0,1,6,1,96,1,type,1,type,
                3,2,1,0,7,7,1,3,114,117,110,0,0,10,6,1,4,0,32,0,11])
            let session = try VMSession(module: identity, profile: profile)
            #expect(try session.invoke("run", arguments: [value]).value == value)
            do { _ = try VMSession(module: identity, profile: .integerV1); Issue.record("Integer profile accepted float") }
            catch let failure as VMFailure { #expect(failure.status == 1) }
        }
    }

    @Test func deinitializationReleasesCapacityAndInstancesAreIsolated() throws {
        func round() throws {
            let session = try VMSession(module: Self.counter, profile: .integerV1)
            #expect(try session.invoke("run").value == .i32(1))
        }
        for _ in 0..<40 { try round() }
        var sessions: [VMSession] = []
        for _ in 0..<16 { sessions.append(try VMSession(module: Self.counter, profile: .integerV1)) }
        expectFailure("session_limit") { _ = try VMSession(module: Self.counter, profile: .integerV1) }
        sessions.removeLast()
        let replacement = try VMSession(module: Self.counter, profile: .integerV1)
        #expect(try replacement.invoke("run").value == .i32(1))
        for session in sessions { try session.close() }
    }

    @Test func limitsAndMalformedArgumentsRejectWithoutCrashing() throws {
        expectFailure("invalid_limits") { _ = try VMSession(module: Self.counter, profile: .integerV1, limits: VMLimits(memoryPages: 65)) }
        let session = try VMSession(module: Self.counter, profile: .integerV1, limits: VMLimits(fuel: 9))
        expectFailure("invalid_arguments") { _ = try session.invoke(String(repeating: "x", count: 4097)) }
        expectFailure("invalid_arguments") { _ = try session.invoke("run", arguments: Array(repeating: .i32(0), count: 4097)) }
        #expect(try session.invoke("run").value == .i32(1))
        #expect(try session.invoke("run").value == .i32(2))
        expectFailure("invalid_arguments") { _ = try session.invoke("run", arguments: [.i32(0)]) }
        expectFailure("session_terminal") { _ = try session.invoke("run") }
    }

    @Test func concurrentReadInvokeCancelAndCloseHaveStructuredOutcomes() async throws {
        let session = try VMSession(module: Self.counter, profile: .integerV1)
        let codes = await withTaskGroup(of: String.self) { group in
            for i in 0..<200 {
                group.addTask {
                    do {
                        switch i % 5 {
                        case 0: _ = try session.invoke("run")
                        case 1: _ = try session.readMemory(offset: 0, count: 4)
                        case 2: try session.writeMemory(offset: 0, bytes: Data([1,2,3,4]))
                        case 3: try session.cancel()
                        default: try session.close()
                        }
                        return "success"
                    } catch let failure as VMFailure { return failure.code }
                    catch { return "unexpected:\(error)" }
                }
            }
            var result: [String] = []
            for await code in group { result.append(code) }
            return result
        }
        #expect(codes.count == 200)
        #expect(Set(codes).isSubset(of: ["success", "invalid_session", "session_terminal", "session_busy", "cancelled"]))
        expectFailure("invalid_session") { _ = try session.invoke("run") }
    }
}
