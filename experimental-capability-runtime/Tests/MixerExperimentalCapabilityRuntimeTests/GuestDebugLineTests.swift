import Foundation
import Testing
@testable import MixerExperimentalCapabilityRuntime

struct GuestDebugLineTests {
    @Test func bindsNativeFunctionAndOffset() throws {
        let (module, codeStart) = fixture(rows: [5, 7, 1], files: ["src/Original.swift"])
        let lines = try #require(GuestDebugLines(module: module))
        let offset = codeStart + 3
        let source = try #require(lines.sourceLocation(function: 1, at: offset))
        #expect(source.file == "Original.swift" && source.line == 1 && source.column == 7)
        #expect(lines.sourceLocation(function: 1, at: offset + 1) == source)
        #expect(lines.sourceLocation(function: 0, at: offset) == nil)
        #expect(lines.sourceLocation(function: 2, at: offset) == nil)
        #expect(lines.sourceLocation(function: 1, at: codeStart + 9) == nil)
    }

    @Test func exactSourceRowTakesPrecedenceOverSameAddressLineZero() throws {
        // Emit line 1, then line 0 at the same address before ending the sequence.
        let (module, codeStart) = fixture(rows: [1, 3, 0x7f, 1], files: ["Original.swift"])
        let lines = try #require(GuestDebugLines(module: module))
        #expect(lines.sourceLocation(function: 1, at: codeStart + 3)?.line == 1)
        #expect(lines.sourceLocation(function: 1, at: codeStart + 4) == nil)
    }

    @Test(arguments: [["src/Original.swift", "lib/Original.swift"], ["Original.swift", "Inline.c"]])
    func conflictingFileRowsFallBackAfterDisplayPathReduction(files: [String]) throws {
        let (module, codeStart) = fixture(rows: [1, 4, 2, 1], files: files)
        let lines = try #require(GuestDebugLines(module: module))
        #expect(lines.sourceLocation(function: 1, at: codeStart + 3) == nil)
    }

    @Test func intervalsAreHalfOpenAndStayInTheReportedFunction() throws {
        let (module, codeStart) = fixture(rows: [1], files: ["Original.swift"])
        let lines = try #require(GuestDebugLines(module: module))
        #expect(lines.sourceLocation(function: 1, at: codeStart + 5)?.line == 1)
        #expect(lines.sourceLocation(function: 1, at: codeStart + 6) == nil)

        let (crossesBody, _) = fixture(rows: [1], files: ["Original.swift"], addressAdvance: 7)
        let crossing = try #require(GuestDebugLines(module: crossesBody))
        #expect(crossing.sourceLocation(function: 1, at: codeStart + 3) == nil)
    }

    @Test func overlappingSequencesDoNotPickAnArbitraryLocation() throws {
        let (module, codeStart) = fixture(rows: [1], files: ["Original.swift"], repeatSequence: true)
        let lines = try #require(GuestDebugLines(module: module))
        #expect(lines.sourceLocation(function: 1, at: codeStart + 3) == nil)
    }

    private func fixture(rows: [UInt8], files: [String], addressAdvance: UInt8 = 3,
                         repeatSequence: Bool = false) -> (Data, UInt32) {
        let section = GuestProgram.section
        var module: [UInt8] = [0, 97, 115, 109, 1, 0, 0, 0]
        module += section(1, [1] + GuestProgram.sig([0x7f, 0x7f, 0x7f], 0x7f))
        module += section(2, [1] + GuestProgram.text("mixer.capability.v1") + GuestProgram.text("storage_put") + [0, 0])
        module += section(3, [2, 0, 0])
        // Two bodies with the relevant positions in the first body.
        let code: [UInt8] = [2, 5, 0, 1, 0x20, 0, 0x0b, 4, 0, 0x20, 0, 0x0b]
        let codeStart = UInt32(module.count + 2)
        module += section(10, code)

        var header: [UInt8] = [1, 1, 1, 251, 14, 13, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0]
        for file in files { header += Array(file.utf8) + [0, 0, 0, 0] }
        header.append(0)
        var unit: [UInt8] = [4, 0]
        unit += littleEndian(UInt32(header.count)) + header
        let sequence: [UInt8] = [0, 5, 2] + littleEndian(3) + rows + [2, addressAdvance, 0, 1, 1]
        unit += sequence
        if repeatSequence { unit += sequence }
        module += section(0, GuestProgram.text(".debug_line") + littleEndian(UInt32(unit.count)) + unit)
        return (Data(module), codeStart)
    }

    private func littleEndian(_ value: UInt32) -> [UInt8] {
        (0..<4).map { UInt8(truncatingIfNeeded: value >> (8 * $0)) }
    }
}
