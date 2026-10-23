import Foundation

/// Executes the original and edited builders with the same hand-selected input
/// domain. The runner compares entire byte arrays, not only module lengths.
@main
struct FixtureParity {
    static func main() throws {
        let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        func write(_ name: String, _ bytes: Data) throws {
            try bytes.write(to: directory.appendingPathComponent(name + ".wasm"))
            print("\(name) \(bytes.count)")
        }
        let modes: [(String, GuestUIProgram.Mode)] = [
            ("normal", .normal), ("invalidStartupHeader", .invalidStartupHeader),
            ("overlappingRanges", .overlappingRanges), ("outsideMemory", .outsideMemory),
            ("invalidEventDocument", .invalidEventDocument), ("nonzeroEvent", .nonzeroEvent),
            ("invalidWakeDocument", .invalidWakeDocument), ("changedWakeBuffer", .changedWakeBuffer),
            ("regressedWake", .regressedWake), ("sameRevisionWake", .sameRevisionWake),
            ("unconsumed", .unconsumed), ("confirmationWindow", .confirmationWindow),
        ]
        let revisions: [UInt64] = [
            0, 1, 2, 63, 64, 127, 128, 16_383, 16_384,
            UInt64(UInt32.max), UInt64(UInt32.max) + 1, UInt64(Int64.max), UInt64.max - 1,
        ]
        for (name, mode) in modes {
            for revision in revisions {
                try write("runtime-\(name)-\(revision)", GuestUIProgram.build(mode, initialRevision: revision))
            }
            // Other modes compute initialRevision + 1 and therefore cannot be
            // called with UInt64.max in either the original or edited source.
            if mode == .regressedWake || mode == .sameRevisionWake {
                try write("runtime-\(name)-\(UInt64.max)", GuestUIProgram.build(mode, initialRevision: .max))
            }
        }
        try write("runtime-default", GuestUIProgram.build())
        let signedModes: [(String, GuestUISignedProgram.Mode)] = [
            ("valid", .valid), ("invalidHeader", .invalidHeader),
            ("invalidEventDocument", .invalidEventDocument),
            ("invalidWakeDocument", .invalidWakeDocument), ("missingEvent", .missingEvent),
        ]
        for (name, mode) in signedModes {
            try write("signed-\(name)", GuestUISignedProgram.build(mode))
        }
        try write("signed-default", GuestUISignedProgram.build())
    }
}
