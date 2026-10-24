import Foundation

func path(_ value: UIAppearanceGeometryV2.Path) -> String {
    var result = "\(value.shape.rawValue);\(value.width64);\(value.height64)"
    func points(_ values: [UIAppearanceGeometryV2.Point]) -> String {
        values.map { ":\($0.x64),\($0.y64)" }.joined()
    }
    for command in value.commands {
        switch command {
        case let .move(p): result += ";move" + points([p])
        case let .line(p): result += ";line" + points([p])
        case let .cubic(a,b,p): result += ";cubic" + points([a,b,p])
        case .close: result += ";close"
        }
    }
    return result
}

@main struct ReviewProbe {
    static func main() {
        while let line=readLine() {
            if CommandLine.arguments[1] == "descriptor" {
                let bytes=Data(base64Encoded:line)!
                do {
                    let d=try UIAppearanceDescriptorCodecV2.decode(bytes)
                    try UIAppearanceDescriptorCodecV2.validate(d)
                    print(try UIAppearanceDescriptorCodecV2.canonicalData(d)==bytes ? "accept" : "typedMismatch")
                } catch { print("reject") }
                continue
            }
            let f=line.split(separator:"\t").map(String.init)
            do {
                let result: String
                switch f[0] {
                case "group": result=path(try UIAppearanceGeometryV2.group(width64:UInt32(f[1])!,height64:UInt32(f[2])!,radius64:UInt32(f[3])!))
                case "track": result=path(UIAppearanceGeometryV2.track())
                case "thumb": result=path(UIAppearanceGeometryV2.thumb())
                case "origin":
                    let p=UIAppearanceGeometryV2.thumbOrigin(checked:f[1]=="1",direction:f[2]=="rightToLeft" ? .rightToLeft : .leftToRight)
                    result="\(p.x64),\(p.y64)"
                case "extent": result=String(try UIAppearanceGeometryV2.measuredExtent64(Double(bitPattern:UInt64(f[1],radix:16)!)))
                case "spacing": result=String(try UIAppearanceGeometryV2.spacing64(Double(bitPattern:UInt64(f[1],radix:16)!)))
                case "density": result=String(try UIAppearanceGeometryV2.normalizeDensity(Double(bitPattern:UInt64(f[1],radix:16)!)))
                case "edge": result=String(try UIAppearanceGeometryV2.pixelEdge(UInt32(f[1])!,density1024:UInt16(f[2])!))
                case "coordinate": result=String(try UIAppearanceGeometryV2.pixelCoordinate(UInt32(f[1])!,density1024:UInt16(f[2])!).bitPattern,radix:16)
                default: fatalError("unknown probe")
                }
                print("ok\t"+result)
            } catch { print("reject\t\(error)") }
        }
    }
}
