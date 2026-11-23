// macOS host replay of the exported F03 iPhone 17 Pro XCTest attachments.
import CoreGraphics
import CryptoKit
import Foundation
import ImageIO

struct ExportCase: Decodable {
  let testIdentifier: String
  let testIdentifierURL: String
  let attachments: [Attachment]
}

struct Attachment: Decodable {
  let suggestedHumanReadableName: String
  let exportedFileName: String
  let deviceId: UUID
  let isAssociatedWithFailure: Bool
  let timestamp: Double
}

enum Phase: String, CaseIterable {
  case prior, exact, rollback, cold
}

enum Refusal: Error, Equatable {
  case identity(String), geometry(String), paint(Phase), projectPaint(Phase)
  case doneBytes(Phase), onlineProjectBytes(Phase)
  case coldAlpha(Int), coldRGB(Int), coldOutsideCorners(Int), coldHistogram
  case unexpectedControl(String)
}

let deep: UInt32 = 0x245747ff
let mint: UInt32 = 0x7ad1b0ff
let white: UInt32 = 0xffffffff

struct Raster {
  let rect: CGRect
  var bytes: [UInt8]

  var grid: CGSize { rect.size }
  var pixels: Int { bytes.count / 4 }

  func pixel(at offset: Int) -> UInt32 {
    UInt32(bytes[offset]) << 24 | UInt32(bytes[offset + 1]) << 16
      | UInt32(bytes[offset + 2]) << 8 | UInt32(bytes[offset + 3])
  }

  var histogram: [UInt32: Int] {
    var counts: [UInt32: Int] = [:]
    for offset in stride(from: 0, to: bytes.count, by: 4) {
      counts[pixel(at: offset), default: 0] += 1
    }
    return counts
  }

  var summary: [String: Any] {
    let counts = histogram
    return [
      "rect": [rect.minX, rect.minY, rect.width, rect.height].map { Int($0) },
      "pixels": pixels,
      "rgbaSHA256": SHA256.hash(data: Data(bytes)).map { String(format: "%02x", $0) }.joined(),
      "deep": counts[deep, default: 0], "mint": counts[mint, default: 0],
      "white": counts[white, default: 0],
    ]
  }
}

struct Frame {
  var done: Raster
  var project: Raster
}

func rasterize(_ image: CGImage, at rect: CGRect, grid: CGSize, label: String) throws -> Raster {
  let imageBounds = CGRect(x: 0, y: 0, width: image.width, height: image.height)
  guard rect.size == grid, imageBounds.contains(rect),
        let crop = image.cropping(to: rect),
        let srgb = CGColorSpace(name: CGColorSpace.sRGB)
  else { throw Refusal.geometry(label) }

  var bytes = [UInt8](repeating: 0, count: crop.width * crop.height * 4)
  try bytes.withUnsafeMutableBytes { pixels in
    guard let ctx = CGContext(
      data: pixels.baseAddress, width: crop.width, height: crop.height, bitsPerComponent: 8,
      bytesPerRow: crop.width * 4, space: srgb,
      bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue
    ) else { throw Refusal.geometry(label) }
    ctx.draw(crop, in: CGRect(origin: .zero, size: grid))
  }
  return Raster(rect: rect, bytes: bytes)
}

func readFrames(_ directory: String, device: UUID) throws -> [Frame] {
  let export = URL(fileURLWithPath: directory, isDirectory: true).resolvingSymlinksInPath()
  let cases = try JSONDecoder().decode([ExportCase].self, from: Data(
    contentsOf: export.appendingPathComponent("manifest.json")))
  let selector = "DarkAccentTests/testSignedDarkAccentReplacementAndColdReadback"
  guard cases.count == 1, cases[0].testIdentifier == selector + "()",
        cases[0].testIdentifierURL == "test://com.apple.xcode/FieldLog/FieldLogUITests/" + selector
  else { throw Refusal.identity("XCTest selector") }
  let attachments = cases[0].attachments
  guard attachments.count == 8, Set(attachments.map(\.exportedFileName)).count == 8,
        attachments.allSatisfy({ $0.deviceId == device && !$0.isAssociatedWithFailure })
  else { throw Refusal.identity("attachment set or device") }

  func attachment(_ name: String, ext: String) throws -> (URL, Double) {
    let matches = attachments.filter { $0.suggestedHumanReadableName.hasPrefix(name + "_") }
    guard matches.count == 1, matches[0].timestamp.isFinite else { throw Refusal.identity(name) }
    let file = export.appendingPathComponent(matches[0].exportedFileName)
    guard file.deletingLastPathComponent() == export, file.pathExtension == ext,
          file.resolvingSymlinksInPath() == file,
          UUID(uuidString: file.deletingPathExtension().lastPathComponent) != nil
    else { throw Refusal.identity(name) }
    return (file, matches[0].timestamp)
  }

  var previousImageTime = -Double.infinity
  return try Phase.allCases.map { phase in
    let title = "F03 " + phase.rawValue
    let (framesURL, framesTime) = try attachment(title + " frames", ext: "txt")
    let (imageURL, imageTime) = try attachment(title + " image", ext: "png")
    guard previousImageTime < framesTime, framesTime < imageTime else {
      throw Refusal.identity(title + " capture order")
    }
    previousImageTime = imageTime

    let area = try JSONDecoder().decode([String: [Double]].self, from: Data(contentsOf: framesURL))
    guard Set(area.keys) == ["app", "done", "firstProject"], area["app"] == [0, 0, 402, 874],
          let source = CGImageSourceCreateWithURL(imageURL as CFURL, nil),
          CGImageSourceGetType(source) as String? == "public.png", CGImageSourceGetCount(source) == 1,
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil),
          image.width == 1206, image.height == 2622
    else { throw Refusal.geometry(title) }

    func read(_ node: String, width: Int, height: Int) throws -> Raster {
      let label = title + " " + node
      guard let frame = area[node], frame.count == 4, frame.allSatisfy(\.isFinite),
            frame[0] >= 0, frame[1] >= 0, frame[2] > 0, frame[3] > 0,
            frame[0] + frame[2] <= 402, frame[1] + frame[3] <= 874
      else { throw Refusal.geometry(label) }
      // Use the original reader's integral bounds on the 3x screenshot.
      let rect = CGRect(x: frame[0] * 3, y: frame[1] * 3,
                        width: frame[2] * 3, height: frame[3] * 3).integral
      return try rasterize(image, at: rect, grid: CGSize(width: width, height: height), label: label)
    }

    return Frame(done: try read("done", width: 122, height: 62),
                 project: try read("firstProject", width: 614, height: 109))
  }
}

func compare(_ frames: [Frame]) throws -> [[Int]] {
  let baseline = frames[0]
  for (phase, frame) in zip(Phase.allCases, frames) {
    guard frame.done.grid == baseline.done.grid, frame.project.grid == baseline.project.grid else {
      throw Refusal.geometry(phase.rawValue + " pixel grid")
    }
    let exact = phase == .exact
    let done = frame.done.histogram
    guard done[exact ? mint : deep, default: 0] == (exact ? 979 : 991),
          done[exact ? deep : mint, default: 0] == 0
    else { throw Refusal.paint(phase) }
    let project = frame.project.histogram
    guard project[deep, default: 0] == 59_170, project[white, default: 0] == 3_878,
          project[mint, default: 0] == 0
    else { throw Refusal.projectPaint(phase) }
    if !exact && frame.done.bytes != baseline.done.bytes { throw Refusal.doneBytes(phase) }
    if phase != .cold && frame.project.bytes != baseline.project.bytes {
      throw Refusal.onlineProjectBytes(phase)
    }
  }

  let online = baseline.project
  let cold = frames[3].project
  var changes: [[Int]] = []
  let width = Int(online.grid.width)
  let height = Int(online.grid.height)
  // The retained captures have 100 one-unit differences, all within 30 columns
  // and 35 rows of a rounded corner. Keep the interior byte-identical and record
  // the actual differing coordinates and colors without rounding either capture.
  for offset in stride(from: 0, to: online.bytes.count, by: 4) {
    guard online.bytes[offset + 3] == cold.bytes[offset + 3] else { throw Refusal.coldAlpha(offset / 4) }
    guard (0..<3).allSatisfy({ abs(Int(online.bytes[offset + $0]) - Int(cold.bytes[offset + $0])) < 2 })
    else { throw Refusal.coldRGB(offset / 4) }
    let before = online.pixel(at: offset)
    let after = cold.pixel(at: offset)
    if before != after {
      let index = offset / 4
      let x = index % width
      let y = index / width
      guard min(x, width - 1 - x) < 30, min(y, height - 1 - y) < 35
      else { throw Refusal.coldOutsideCorners(index) }
      changes.append([index, Int(before), Int(after)])
    }
  }
  guard online.histogram == cold.histogram else { throw Refusal.coldHistogram }
  return changes
}

func refusalControls(_ frames: [Frame]) throws -> [String: String] {
  func refuses(_ label: String, _ changed: [Frame], _ expected: Refusal) throws -> String {
    do { _ = try compare(changed) }
    catch let error as Refusal where error == expected { return String(describing: error) }
    throw Refusal.unexpectedControl(label)
  }

  var changed = frames
  changed[1].done = frames[0].done
  let wrongPalette = try refuses("wrong palette", changed, .paint(.exact))

  changed = frames
  changed.swapAt(0, 1)
  let swapped = try refuses("swapped phase", changed, .paint(.prior))

  changed = frames
  guard let paintOffset = stride(from: 0, to: changed[1].done.bytes.count, by: 4).first(where: {
    changed[1].done.pixel(at: $0) == 0x000000ff
  }) else { throw Refusal.unexpectedControl("changed paint fixture") }
  changed[1].done.bytes.replaceSubrange(paintOffset..<(paintOffset + 4), with: [0x24, 0x57, 0x47, 0xff])
  let paint = try refuses("changed paint", changed, .paint(.exact))

  changed = frames
  guard let editOffset = stride(from: 0, to: changed[3].project.bytes.count, by: 4).first(where: {
    changed[3].project.pixel(at: $0) == 0x000000ff && frames[0].project.pixel(at: $0) == 0x000000ff
  }) else { throw Refusal.unexpectedControl("single pixel edit fixture") }
  changed[3].project.bytes[editOffset] = 32
  let edit = try refuses("one substantial pixel edit", changed, .coldRGB(editOffset / 4))
  return ["wrongPalette": wrongPalette, "swappedPhase": swapped, "changedPaint": paint, "singlePixelEdit": edit]
}

do {
  let args = Array(CommandLine.arguments.dropFirst())
  guard args.count == 2 || (args.count == 3 && args[2] == "--controls"),
        let device = UUID(uuidString: args[1])
  else { throw Refusal.identity("usage: f03-raster-readback ATTACHMENTS DEVICE-UUID [--controls]") }
  let frames = try readFrames(args[0], device: device)
  let diff = try compare(frames)
  var result: [String: Any] = [
    "status": "passed",
    "frames": Dictionary(uniqueKeysWithValues: zip(Phase.allCases, frames).map { phase, frame in
      (phase.rawValue, ["done": frame.done.summary, "firstProject": frame.project.summary])
    }),
    "coldFirstProject": [
      "count": diff.count, "maxSRGBChannelDelta": diff.isEmpty ? 0 : 1,
      "pixelDeltas": diff, // row-major pixel index, prior RGBA32, cold RGBA32
    ],
  ]
  if args.count == 3 { result["refusalControls"] = try refusalControls(frames) }
  let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
  print(String(decoding: data, as: UTF8.self))
} catch {
  FileHandle.standardError.write(Data("F03 raster refused: \(error)\n".utf8))
  exit(1)
}
