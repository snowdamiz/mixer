import Foundation
import Testing
import MixerRuntime

@Suite(.serialized) struct ReviewTests {
    static let counter = Data([0,97,115,109,1,0,0,0,
        1,5,1,96,0,1,127,3,2,1,0,5,4,1,1,1,1,
        6,6,1,127,1,65,0,11,7,7,1,3,114,117,110,0,0,
        10,20,1,18,0,35,0,65,1,106,36,0,65,0,35,0,54,2,0,35,0,11])
    func leb(_ number: Int) -> [UInt8] {
        var n = number; var result: [UInt8] = []
        repeat { var byte = UInt8(n & 127); n >>= 7; if n != 0 { byte |= 128 }; result.append(byte) } while n != 0
        return result
    }
    func identity(_ type: UInt8, name: String = "run") -> Data {
        var b: [UInt8] = [0,97,115,109,1,0,0,0]
        func section(_ id: UInt8, _ data: [UInt8]) { b += [id] + leb(data.count) + data }
        section(1, [1,96,1,type,1,type]); section(3, [1,0])
        section(7, [1] + leb(name.utf8.count) + name.utf8 + [0,0])
        section(10, [1,4,0,32,0,11]); return Data(b)
    }
    @Test func rawBitAndSignedBoundaryTransport() throws {
        var f32: [UInt32] = [0,1,0x7f800000,0xff800000,0x80000000,0x7fc00000,0x7fa00001,UInt32.max]
        var f64: [UInt64] = [0,1,0x7ff0000000000000,0xfff0000000000000,0x8000000000000000,0x7ff8000000000000,0x7ff0000000000001,UInt64.max]
        var random: UInt64 = 0x123456789abcdef
        for _ in 0..<256 { random = random &* 6364136223846793005 &+ 1442695040888963407; f32.append(UInt32(truncatingIfNeeded: random)); f64.append(random) }
        for profile in [VMProfile.numericV2, .tableMemoryV3] {
            for (type, values) in [(UInt8(0x7d), f32.map(VMValue.f32Bits)), (0x7c, f64.map(VMValue.f64Bits)),
                (0x7f, [Int32.min,-1,0,1,Int32.max].map(VMValue.i32)), (0x7e, [Int64.min,-1,0,1,Int64.max].map(VMValue.i64))] {
                let session = try VMSession(module: identity(type), profile: profile)
                for value in values { #expect(try session.invoke("run", arguments: [value]).value == value) }
                try session.close()
            }
        }
    }
    @Test func copiedMemoryAndExactExportBytes() throws {
        let session = try VMSession(module: Self.counter, profile: .integerV1)
        var source = Data([0,255,17,0,255]); try session.writeMemory(offset: 64, bytes: source)
        source.resetBytes(in: 0..<source.count)
        let read = try session.readMemory(offset: 64, count: 5)
        #expect(read == Data([0,255,17,0,255]))
        try session.writeMemory(offset: 64, bytes: Data(repeating: 77, count: 5))
        #expect(read == Data([0,255,17,0,255]))
        for name in ["nul\0tail", "cafe\u{0301}", "☃"] {
            let identity = try VMSession(module: identity(0x7e, name: name), profile: .integerV1)
            #expect(try identity.invoke(name, arguments: [.i64(Int64.min)]).value == .i64(Int64.min))
            try identity.close()
        }
    }
    @Test func malformedAndHugeInputsHaveBoundedStructuredErrors() throws {
        for bytes in [Data(), Data([0]), Data(repeating: 0, count: 4_194_305), Data([0,97,115,109,2,0,0,0])] {
            do { _ = try VMSession(module: bytes, profile: .integerV1); Issue.record("Accepted bad module") }
            catch let failure as VMFailure { #expect(!failure.code.isEmpty); #expect([1,3].contains(failure.status)) }
        }
        let session = try VMSession(module: Self.counter, profile: .integerV1)
        for offset in [UInt32.max, UInt32.max-1, 65537] {
            do { _ = try session.readMemory(offset: offset, count: 1); Issue.record("Accepted bad offset") }
            catch let failure as VMFailure { #expect(failure.code == "memory_out_of_bounds"); #expect(failure.status == 3) }
        }
        #expect(try session.invoke("run").value == .i32(1)); try session.close()
    }
    @Test func repeatedCloseCancelRecreateNeverMutatesNewOwner() async throws {
        for _ in 0..<100 {
            let session = try VMSession(module: Self.counter, profile: .integerV1)
            let results = await withTaskGroup(of: String.self) { group in
                for i in 0..<128 { group.addTask {
                    do {
                        switch i % 5 {
                        case 0: _ = try session.invoke("run")
                        case 1: _ = try session.readMemory(offset: 0, count: 4)
                        case 2: try session.writeMemory(offset: 0, bytes: Data([9,8,7,6]))
                        case 3: try session.cancel()
                        default: try session.close()
                        }
                        return "ok"
                    } catch let f as VMFailure { return f.code } catch { return "unexpected" }
                } }
                var values: [String] = []; for await value in group { values.append(value) }; return values
            }
            #expect(Set(results).isSubset(of: ["ok","invalid_session","session_busy","session_terminal","cancelled"]))
            try session.close()
            let next = try VMSession(module: Self.counter, profile: .integerV1)
            do { try session.cancel(); Issue.record("Closed handle cancelled replacement") } catch let f as VMFailure { #expect(f.code == "invalid_session") }
            #expect(try next.invoke("run").value == .i32(1)); try next.close()
        }
    }
}
