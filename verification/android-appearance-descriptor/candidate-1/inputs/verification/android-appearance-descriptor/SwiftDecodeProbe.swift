import Foundation
@main struct Probe {
    static func main() throws {
        let lines = try String(contentsOfFile: CommandLine.arguments[1], encoding: .utf8).split(separator: "\n")
        var accepted = 0
        for line in lines {
            let fields = line.split(separator: "\t", omittingEmptySubsequences: false)
            let bytes = Data(base64Encoded: String(fields[2]))!
            var success = false
            do {
                let value = try UIAppearanceDescriptorCodecV1.decode(bytes)
                guard try UIAppearanceDescriptorCodecV1.canonicalData(value) == bytes else { fatalError("roundtrip") }
                success = true
            } catch is UIAppearanceErrorV1 {} catch { fatalError("unexpected: \(error)") }
            guard success == (fields[1] == "1") else { fatalError("case mismatch: \(fields[0])") }
            if success { accepted += 1 }
        }
        print("PASS descriptor cases=\(lines.count) accepted=\(accepted) rejected=\(lines.count-accepted)")
    }
}
