import Foundation

/// Optional DWARF32 v4 line data from the same module admitted by the VM. All
/// addresses in the line program are relative to the start of the code payload.
struct GuestDebugLines {
    private let lines: Data
    private let codeStart: Int
    private let importedFunctions: Int
    private let bodies: [Range<Int>]

    init?(module: Data) {
        do {
            guard let metadata = try module.withUnsafeBytes(Self.sections) else { return nil }
            lines = metadata.lines
            codeStart = metadata.codeStart
            importedFunctions = metadata.importedFunctions
            bodies = metadata.bodies
        } catch { return nil }
    }

    private static func sections(_ bytes: UnsafeRawBufferPointer) throws -> Self? {
        guard bytes.count >= 8 else { return nil }
        var module = DebugReader(bytes: bytes, range: 8..<bytes.count)
        var code: Range<Int>?
        var lineTable: Range<Int>?
        var importedFunctions = 0
        // Metadata work is independent of the VM's module and execution limits.
        for _ in 0..<4096 {
            if module.done { break }
            let id = try module.byte()
            var section = try module.region(count: module.uleb())
            if id == 10 {
                code = section.position..<section.end
            } else if id == 2 {
                // The admitted capability profile permits only function imports.
                importedFunctions = try section.uleb()
            } else if id == 0 {
                let name = try section.take(section.uleb())
                if name.elementsEqual("external_debug_info".utf8) { return nil }
                if name.elementsEqual(".debug_line".utf8) {
                    guard lineTable == nil else { return nil }
                    lineTable = section.position..<section.end
                }
            }
        }
        guard module.done, let code, let lineTable, (1...262_144).contains(lineTable.count) else { return nil }

        var reader = DebugReader(bytes: bytes, range: code)
        let count = try reader.uleb()
        guard count <= 2048 else { return nil }
        var bodies: [Range<Int>] = []
        bodies.reserveCapacity(count)
        for _ in 0..<count {
            let body = try reader.region(count: reader.uleb())
            bodies.append((body.position - code.lowerBound)..<(body.end - code.lowerBound))
        }
        guard reader.done else { return nil }
        return Self(lines: Data(bytes[lineTable]), codeStart: code.lowerBound,
                    importedFunctions: importedFunctions, bodies: bodies)
    }

    private init(lines: Data, codeStart: Int, importedFunctions: Int, bodies: [Range<Int>]) {
        self.lines = lines
        self.codeStart = codeStart
        self.importedFunctions = importedFunctions
        self.bodies = bodies
    }

    func sourceLocation(function: UInt32, at offset: UInt32) -> ExperimentalCapabilitySourceLocation? {
        guard let absolute = Int(exactly: offset), absolute >= codeStart,
              let index = Int(exactly: function), index >= importedFunctions else { return nil }
        let address = absolute - codeStart
        let defined = index - importedFunctions
        guard defined < bodies.count, let codeEnd = bodies.last?.upperBound else { return nil }
        let body = bodies[defined]
        guard body.contains(address) else { return nil }
        return lines.withUnsafeBytes { bytes in
            var table = DebugReader(bytes: bytes, range: 0..<bytes.count)
            var match: DebugLineRow?
            do {
                while !table.done {
                    let unit = try table.region(count: table.fixed(4))
                    try DebugLineProgram.read(unit, address: address, body: body, codeEnd: codeEnd, match: &match)
                }
                return match?.location
            } catch { return nil }
        }
    }
}

private enum DebugLineError: Error { case invalid }

private struct DebugReader {
    let bytes: UnsafeRawBufferPointer
    let end: Int
    private(set) var position: Int
    var done: Bool { position == end }

    init(bytes: UnsafeRawBufferPointer, range: Range<Int>) {
        self.bytes = bytes
        position = range.lowerBound
        end = range.upperBound
    }

    mutating func take(_ count: Int) throws -> Slice<UnsafeRawBufferPointer> {
        guard count >= 0, count <= end - position else { throw DebugLineError.invalid }
        let start = position
        position += count
        return bytes[start..<position]
    }

    mutating func region(count: Int) throws -> Self {
        let slice = try take(count)
        return Self(bytes: bytes, range: slice.startIndex..<slice.endIndex)
    }

    mutating func byte() throws -> UInt8 {
        guard position < end else { throw DebugLineError.invalid }
        defer { position += 1 }
        return bytes[position]
    }

    mutating func fixed(_ count: Int) throws -> Int {
        var value: UInt32 = 0
        for (index, byte) in try take(count).enumerated() { value |= UInt32(byte) << (8 * index) }
        guard let result = Int(exactly: value) else { throw DebugLineError.invalid }
        return result
    }

    mutating func uleb() throws -> Int {
        let value = try leb(signed: false)
        guard UInt32(exactly: value) != nil, let result = Int(exactly: value) else { throw DebugLineError.invalid }
        return result
    }

    mutating func sleb() throws -> Int {
        let value = try leb(signed: true)
        guard Int32(exactly: value) != nil else { throw DebugLineError.invalid }
        return Int(value)
    }

    private mutating func leb(signed: Bool) throws -> Int64 {
        var value: Int64 = 0
        for shift in stride(from: 0, to: 35, by: 7) {
            let next = try byte()
            value |= Int64(next & 0x7f) << shift
            if next < 0x80 {
                return signed && next & 0x40 != 0 ? value - (1 << (shift + 7)) : value
            }
        }
        throw DebugLineError.invalid
    }

    mutating func cString() throws -> Slice<UnsafeRawBufferPointer> {
        let start = position
        while try byte() != 0 {}
        return bytes[start..<(position - 1)]
    }
}

private struct DebugLineRow {
    let address: Int64
    var location: ExperimentalCapabilitySourceLocation?
    private var sourceFile: Int?
    private var ambiguous = false
    private var hasLineZero = false

    init(address: Int64) { self.address = address }

    mutating func merge(file: Int, line: Int64, location next: ExperimentalCapabilitySourceLocation?) {
        if line == 0 {
            hasLineZero = true
        } else if next == nil || (location != nil && (location != next || sourceFile != file)) {
            ambiguous = true
        } else {
            location = next
            sourceFile = file
        }
    }

    func source(at target: Int64) -> ExperimentalCapabilitySourceLocation? {
        guard !ambiguous, !hasLineZero || target == address else { return nil }
        return location
    }
}

private enum DebugLineProgram {
    private struct State {
        var address: Int64 = 0
        var file = 1
        var line: Int64 = 1
        var column = 0
        var discarded = false
    }

    static func read(_ unit: DebugReader, address target: Int, body: Range<Int>, codeEnd: Int,
                     match: inout DebugLineRow?) throws {
        var program = unit
        guard try program.fixed(2) == 4 else { throw DebugLineError.invalid }
        var header = try program.region(count: program.fixed(4))
        let instructionLength = Int64(try header.byte())
        guard instructionLength > 0, try header.byte() == 1, try header.byte() <= 1 else { throw DebugLineError.invalid }
        let lineBase = Int(Int8(bitPattern: try header.byte()))
        let lineRange = Int(try header.byte())
        let opcodeBase = Int(try header.byte())
        let operandCounts: [UInt8] = [0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1]
        guard lineRange > 0, opcodeBase == 13, try header.take(12).elementsEqual(operandCounts) else {
            throw DebugLineError.invalid
        }

        var directories = 0
        while try !header.cString().isEmpty { directories += 1 }
        var files: [String?] = []
        while try appendFile(from: &header, directories: directories, files: &files) {}
        guard header.done else { throw DebugLineError.invalid }

        var state = State()
        var row: DebugLineRow?
        var ended = true
        let target = Int64(target)
        while !program.done {
            ended = false
            let opcode = Int(try program.byte())
            var emit = false
            var endSequence = false
            switch opcode {
            case 0:
                var extended = try program.region(count: program.uleb())
                switch try extended.byte() {
                case 1: endSequence = true
                case 2:
                    let address = try extended.fixed(4)
                    // wasm-ld marks sequences for eliminated functions with
                    // an all-ones address. Advance within them without mapping.
                    if address == UInt32.max {
                        guard row == nil else { throw DebugLineError.invalid }
                        state.discarded = true
                        state.address = 0
                    } else {
                        guard !state.discarded else { throw DebugLineError.invalid }
                        state.address = Int64(address)
                    }
                case 3:
                    guard try appendFile(from: &extended, directories: directories, files: &files) else {
                        throw DebugLineError.invalid
                    }
                case 4: _ = try extended.uleb() // discriminator
                default: throw DebugLineError.invalid
                }
                guard extended.done else { throw DebugLineError.invalid }
            case 1: emit = true
            case 2: state.address += Int64(try program.uleb()) * instructionLength
            case 3: state.line += Int64(try program.sleb())
            case 4: state.file = try program.uleb()
            case 5: state.column = try program.uleb()
            case 6, 7, 10, 11: break // flags with no effect on source coordinates
            case 8: state.address += Int64((255 - opcodeBase) / lineRange) * instructionLength
            case 9: state.address += Int64(try program.fixed(2))
            case 12: _ = try program.uleb() // ISA
            default:
                let adjusted = opcode - opcodeBase
                state.address += Int64(adjusted / lineRange) * instructionLength
                state.line += Int64(lineBase + adjusted % lineRange)
                emit = true
            }
            guard state.address <= (state.discarded ? Int64(UInt32.max) : Int64(codeEnd)),
                  state.line >= 0, state.line <= UInt32.max else { throw DebugLineError.invalid }
            if emit || endSequence {
                if let previous = row {
                    guard previous.address <= state.address else { throw DebugLineError.invalid }
                    if !state.discarded, previous.address <= target, target < state.address {
                        guard match == nil else { throw DebugLineError.invalid }
                        match = previous
                        if previous.address < Int64(body.lowerBound) || state.address > Int64(body.upperBound) {
                            match?.location = nil
                        } else {
                            match?.location = previous.source(at: target)
                        }
                    }
                }
                if endSequence {
                    state = State()
                    row = nil
                    ended = true
                } else {
                    guard state.file > 0, state.file <= files.count else { throw DebugLineError.invalid }
                    let location = state.line > 0 ? files[state.file - 1].map {
                        ExperimentalCapabilitySourceLocation(file: $0, line: UInt32(state.line),
                            column: state.column > 0 ? UInt32(state.column) : nil)
                    } : nil
                    // Swift can emit both a source row and line zero at the
                    // trap address. Only recover that label at the exact row.
                    if row?.address != state.address { row = DebugLineRow(address: state.address) }
                    row?.merge(file: state.file, line: state.line, location: location)
                }
            }
        }
        guard ended else { throw DebugLineError.invalid }
    }

    private static func appendFile(from reader: inout DebugReader, directories: Int, files: inout [String?]) throws -> Bool {
        let path = try reader.cString()
        if path.isEmpty { return false }
        guard files.count < 4096, try reader.uleb() <= directories else { throw DebugLineError.invalid }
        _ = try reader.uleb() // modification time
        _ = try reader.uleb() // size
        // Paths come from guest metadata. Expose a bounded, single-line file
        // name without disclosing the compiler's checkout or home directory.
        let start = path.lastIndex(where: { $0 == 47 || $0 == 92 }).map { $0 + 1 } ?? path.startIndex
        let name = path[start...]
        if name.count <= 255, let file = String(bytes: name, encoding: .utf8), file.hasSuffix(".swift"),
           file.unicodeScalars.allSatisfy({ ![.control, .format, .lineSeparator, .paragraphSeparator].contains($0.properties.generalCategory) }) {
            files.append(file)
        } else {
            files.append(nil)
        }
        return true
    }
}
