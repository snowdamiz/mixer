import Foundation

@main struct Probe {
    static func main() throws {
        switch CommandLine.arguments[1] {
        case "descriptor": try descriptors()
        case "geometry": try geometry()
        default: fatalError("unknown probe")
        }
    }
    static func descriptors() throws {
        let lines = try String(contentsOfFile: CommandLine.arguments[2], encoding: .ascii).split(separator: "\n")
        var accepted = 0
        for line in lines {
            let f = line.split(separator: "\t", omittingEmptySubsequences: false)
            let bytes = Data(base64Encoded: String(f[2]))!
            var encoded: Data?
            do {
                let value = try UIAppearanceDescriptorCodecV2.decode(bytes)
                let output = try UIAppearanceDescriptorCodecV2.canonicalData(value)
                guard output == bytes else { fatalError("Swift typed roundtrip: \(f[0])") }
                encoded = output
            } catch is UIAppearanceErrorV2 {} catch { fatalError("unexpected Swift failure: \(error)") }
            let success = encoded != nil
            guard success == (f[1] == "1") else { fatalError("Swift admission mismatch: \(f[0])") }
            if success { accepted += 1 }
            print("\(f[0])\t\(success ? "1" : "0")\t\(encoded?.base64EncodedString() ?? "-")")
        }
        let v1 = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[3]))
        guard v1.count == 1906, try UIAppearanceDescriptorCodecV1.canonicalData(UIAppearanceDescriptorCodecV1.decode(v1)) == v1 else { fatalError("V1 golden changed") }
        let expected = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[4]))
        guard try UIAppearanceDescriptorCodecV2.canonicalData(UIAppearanceConfigurationV2.mixerDefaultV2()) == expected else { fatalError("actual Swift default differs") }
        FileHandle.standardError.write(Data("PASS Swift descriptor cases=\(lines.count) accepted=\(accepted) rejected=\(lines.count-accepted); actual default and V1 golden preserved\n".utf8))
    }
    static func path(_ path: UIAppearanceGeometryV2.Path) -> String {
        var result = "\(path.shape.rawValue)|\(path.width64),\(path.height64)"
        func point(_ p: UIAppearanceGeometryV2.Point) -> String {
            guard p.x64 <= path.width64, p.y64 <= path.height64 else { fatalError("Swift point outside path") }
            return ":\(p.x64),\(p.y64)"
        }
        for command in path.commands {
            switch command {
            case let .move(p): result += "|move" + point(p)
            case let .line(p): result += "|line" + point(p)
            case let .cubic(c1,c2,p): result += "|cubic" + point(c1) + point(c2) + point(p)
            case .close: result += "|close"
            }
        }
        return result
    }
    static func number(_ text: Substring) -> Double { Double(bitPattern: UInt64(text,radix:16)!) }
    static func evaluate(_ f: [Substring]) throws -> String {
        switch f[1] {
        case "group": return path(try UIAppearanceGeometryV2.group(width64: UInt32(f[2])!,height64: UInt32(f[3])!,radius64: UInt32(f[4])!))
        case "track": return path(UIAppearanceGeometryV2.track())
        case "thumb": return path(UIAppearanceGeometryV2.thumb())
        case "origin":
            let p = UIAppearanceGeometryV2.thumbOrigin(checked: f[2] == "1",direction: UILayoutDirectionV1(rawValue:String(f[3]))!)
            return "\(p.x64),\(p.y64)"
        case "measure": return String(try UIAppearanceGeometryV2.measuredExtent64(number(f[2])))
        case "spacing": return String(try UIAppearanceGeometryV2.spacing64(number(f[2])))
        case "density": return String(try UIAppearanceGeometryV2.normalizeDensity(number(f[2])))
        case "edge": return String(try UIAppearanceGeometryV2.pixelEdge(UInt32(f[2])!,density1024:UInt16(f[3])!))
        case "coordinate":
            let value = try UIAppearanceGeometryV2.pixelCoordinate(UInt32(f[2])!,density1024:UInt16(f[3])!)
            let hex = String(value.bitPattern,radix:16)
            return String(repeating:"0",count:16-hex.count) + hex
        default: fatalError("unknown geometry operation")
        }
    }
    static func geometry() throws {
        let lines = try String(contentsOfFile: CommandLine.arguments[2],encoding:.ascii).split(separator:"\n")
        var rejected = 0
        for line in lines {
            let f = line.split(separator:"\t",omittingEmptySubsequences:false)
            let result: String
            do { result = try evaluate(f) }
            catch let error as UIAppearanceGeometryErrorV2 { result = "error:\(error)"; rejected += 1 }
            catch { fatalError("unexpected geometry failure: \(error)") }
            print("\(f[0])\t\(result)")
        }
        FileHandle.standardError.write(Data("PASS Swift geometry cases=\(lines.count) rejected=\(rejected)\n".utf8))
    }
}
