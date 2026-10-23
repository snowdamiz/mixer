import Foundation
import ImageIO
import CryptoKit

struct Raster {
    let width: Int
    let height: Int
    let components: Int
    let pixels: Data
}
func decode(_ path: String) throws -> Raster {
    guard let source = CGImageSourceCreateWithURL(URL(fileURLWithPath:path) as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil),
          image.bitsPerComponent == 8, image.bitsPerPixel % 8 == 0,
          let bytes = image.dataProvider?.data else {
        throw NSError(domain:"native-png-decode",code:1)
    }
    let raw = bytes as Data
    let storageComponents = image.bitsPerPixel / 8
    precondition(image.alphaInfo == .noneSkipLast && storageComponents == 4)
    let components = 3
    var packed = Data()
    for row in 0..<image.height {
        let start = row * image.bytesPerRow
        for column in 0..<image.width {
            let pixel = start + column * storageComponents
            packed.append(raw[pixel..<(pixel+3)])
        }
    }
    return Raster(width:image.width, height:image.height,components:components,pixels:packed)
}
let root = URL(fileURLWithPath:CommandLine.arguments[1])
let measurement = root.appendingPathComponent("verification/apple-appearance-measurement")
let reference = root.appendingPathComponent("verification/apple-appearance-reference")
let analysis = try JSONSerialization.jsonObject(with:Data(contentsOf:measurement.appendingPathComponent("analysis.json"))) as! [String:Any]
let captures = analysis["captures"] as! [[String:Any]]
var records = [[String:Any]]()
var comparisons = [[String:Any]]()
for capture in captures {
    let name = capture["name"] as! String
    let path = measurement.appendingPathComponent("captures/\(name)/screenshot.png").path
    let raster = try decode(path)
    let digest = SHA256.hash(data:raster.pixels).map{String(format:"%02x",$0)}.joined()
    let expected = capture["png"] as! [String:Any]
    precondition(raster.width == expected["width"] as! Int)
    precondition(raster.height == expected["height"] as! Int)
    precondition(raster.components == expected["channels"] as! Int)
    precondition(digest == expected["decodedPixelsSHA256"] as! String)
    records.append(["capture":name,"width":raster.width,"height":raster.height,"components":raster.components,"decoded_sha256":digest])
    let profile = String(name.split(separator:"/",maxSplits:1)[1])
    var references = [String]()
    if capture["historicalUninstrumentedReferenceComparison"] != nil {
        references.append(reference.appendingPathComponent("captures/\(profile)/screenshot.png").path)
    }
    if name.hasPrefix("release/") {
        references.append(measurement.appendingPathComponent("captures/debug/\(profile)/screenshot.png").path)
    }
    for other in references {
        let original = try decode(other)
        precondition(original.width == raster.width && original.height == raster.height && original.components == raster.components)
        precondition(original.pixels == raster.pixels)
        comparisons.append(["capture":name,"reference":String(other.dropFirst(root.path.count+1)),"identical_pixels":true,"pixel_count":raster.width*raster.height])
    }
}
precondition(records.count == 24 && comparisons.count == 28)
let result:[String:Any] = ["decoder":"Apple ImageIO CGImageSourceCreateImageAtIndex/dataProvider; native RGBX decoded bytes, unused X and row padding removed; no color conversion","records":records,"comparisons":comparisons]
let data=try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys,.prettyPrinted])
try data.write(to:root.appendingPathComponent("verification/apple-appearance-measurement-root-review/native-decoder-result.json"))
print("PASS: ImageIO independently decoded 24 captures and matched all producer raw pixel digests; 16 historical and 12 Debug/Release comparisons exact.")
