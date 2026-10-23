import Foundation
@main struct IndependentSwiftProbe {
    static func main() throws {
        let lines = try String(contentsOfFile: CommandLine.arguments[1], encoding: .ascii).split(separator: "\n")
        var accepted = 0
        for line in lines {
            let fields = line.split(separator: "\t", omittingEmptySubsequences: false)
            guard let bytes = Data(base64Encoded: String(fields[2])) else { fatalError("bad corpus") }
            var success = false
            do {
                let parsed = try UIAppearanceDescriptorCodecV1.decode(bytes)
                guard try UIAppearanceDescriptorCodecV1.canonicalData(parsed) == bytes else { fatalError("retained value mismatch") }
                success = true
            } catch is UIAppearanceErrorV1 {} catch { fatalError("unexpected error: \(error)") }
            guard success == (fields[1] == "1") else { fatalError("case mismatch: \(fields[0])") }
            if success { accepted += 1 }
        }
        print("PASS independent descriptor cases=\(lines.count) accepted=\(accepted) rejected=\(lines.count - accepted)")
    }
}
