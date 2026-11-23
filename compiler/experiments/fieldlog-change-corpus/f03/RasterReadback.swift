import CoreGraphics
import Foundation
import ImageIO

struct ExportCase: Decodable {
  let testIdentifier: String
  let attachments: [Attachment]
}

struct Attachment: Decodable {
  let suggestedHumanReadableName: String
  let exportedFileName: String
}

enum ReadbackError: Error {
  case wrongSelector, missingAttachment(String), pathOutsideExport, decodeImage, invalidGeometry, unableToRasterize
}

let export = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true).standardizedFileURL
let cases = try JSONDecoder().decode([ExportCase].self, from: Data(contentsOf: export.appendingPathComponent("manifest.json")))
let selector = "DarkAccentTests/testHistoricalDarkAccentIsRendered()"
guard cases.count == 1, cases[0].testIdentifier.hasSuffix(selector) else { throw ReadbackError.wrongSelector }

func attachment(_ name: String) throws -> URL {
  let matches = cases[0].attachments.filter { $0.suggestedHumanReadableName.hasPrefix(name + "_") }
  guard matches.count == 1 else { throw ReadbackError.missingAttachment(name) }
  let file = export.appendingPathComponent(matches[0].exportedFileName).standardizedFileURL
  guard file.deletingLastPathComponent() == export else { throw ReadbackError.pathOutsideExport }
  return file
}

func read(_ title: String) throws -> [String: Any] {
  let area = try JSONDecoder().decode([String: [Double]].self, from: Data(contentsOf: attachment(title + " frames")))
  let url = try attachment(title + " image")
  guard let input = CGImageSourceCreateWithURL(url as CFURL, nil),
    let screenshot = CGImageSourceCreateImageAtIndex(input, 0, nil)
  else { throw ReadbackError.decodeImage }
  guard let frame = area["app"], frame.count == 4, frame[2] > 0, frame[3] > 0 else {
    throw ReadbackError.invalidGeometry
  }
  let scaleX = Double(screenshot.width) / frame[2]
  let scaleY = Double(screenshot.height) / frame[3]
  guard abs(scaleX - scaleY) < 0.05 else { throw ReadbackError.invalidGeometry }
  var stats: [String: Any] = [:]
  for (name, rect) in area where name != "app" {
    guard rect.count == 4, rect.allSatisfy({ $0.isFinite }),
          rect[2] > 0, rect[3] > 0 else { throw ReadbackError.invalidGeometry }
    let pixelRect = CGRect(x: (rect[0] - frame[0]) * scaleX, y: (rect[1] - frame[1]) * scaleY,
                           width: rect[2] * scaleX, height: rect[3] * scaleY).integral
    guard CGRect(x: 0, y: 0, width: screenshot.width, height: screenshot.height).contains(pixelRect),
      let crop = screenshot.cropping(to: pixelRect), crop.width * crop.height < 2_000_000,
      let srgb = CGColorSpace(name: CGColorSpace.sRGB)
    else { throw ReadbackError.invalidGeometry }
    var colors = [UInt32: Int]()
    var lightGreen = 0
    var deepGreen = 0
    var nearWhite = 0
    var rgbBytes = [UInt8](repeating: 0, count: crop.width * crop.height * 4)
    try rgbBytes.withUnsafeMutableBufferPointer { pixels in
      guard let buffer = pixels.baseAddress,
        let ctx = CGContext(data: buffer, width: crop.width, height: crop.height, bitsPerComponent: 8,
                            bytesPerRow: crop.width * 4, space: srgb,
                            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue)
      else { throw ReadbackError.unableToRasterize }
      ctx.draw(crop, in: CGRect(x: 0, y: 0, width: crop.width, height: crop.height))
      for byte in stride(from: 0, to: pixels.count, by: 4) {
        let r = Int(pixels[byte]), g = Int(pixels[byte + 1]), b = Int(pixels[byte + 2])
        let packed = UInt32(r << 16 | g << 8 | b)
        colors[packed, default: 0] += 1
        if abs(r - 122) <= 18 && abs(g - 209) <= 18 && abs(b - 176) <= 18 { lightGreen += 1 }
        if abs(r - 36) <= 16 && abs(g - 87) <= 16 && abs(b - 71) <= 16 { deepGreen += 1 }
        if min(r, g, b) >= 235 { nearWhite += 1 }
      }
    }
    let modes = colors.sorted { $0.value == $1.value ? $0.key < $1.key : $0.value > $1.value }.prefix(7)
    stats[name] = [
      "pixels": crop.width * crop.height,
      "nearLightAccent": lightGreen, "nearDeepGreen": deepGreen, "nearWhite": nearWhite,
      "commonColors": modes.map { ["rgb": String(format: "%06x", $0.key), "count": $0.value] }
    ]
  }
  return stats
}

let evidence = ["empty": try read("F03 empty dark"), "draft": try read("F03 draft dark")]
let data = try JSONSerialization.data(withJSONObject: evidence, options: [.prettyPrinted, .sortedKeys])
print(String(decoding: data, as: UTF8.self))
