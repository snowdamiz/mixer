import Foundation
import ImageIO

// Independent platform PNG decoder. Expected colors are fixed swatches, not
// values copied from the producer's analysis output. No color conversion.
let directory = URL(fileURLWithPath: CommandLine.arguments[1])
let records = try JSONSerialization.jsonObject(with: Data(contentsOf:
    directory.appendingPathComponent("observations.json"))) as! [[String: Any]]
let byStage = Dictionary(uniqueKeysWithValues: records.map { ($0["stage"] as! String, $0) })
let selected = (byStage["native-selection"]!["after"] as! [String: Any])["selectionRectsInWindow"] as! [[Double]]
let cases: [(String, [Int], Bool)] = [
    ("install-selection", [204,204,255], true),
    ("reactivate-selection", [204,204,255], true),
    ("selection-alpha61", [194,255,194], true),
    ("selection-alpha128", [127,255,127], true),
    ("selection-clear", [255,255,255], true),
    ("selection-caret-green", [255,194,194], true),
    ("authored-caret", [255,0,0], false),
    ("caret-alpha61", [255,194,194], false),
    ("caret-alpha128", [255,127,127], false),
    ("caret-green", [0,255,0], false),
    ("caret-clear", [255,255,255], false)
]
var result = [[String: Any]]()
for (stage, expected, selection) in cases {
    let source = CGImageSourceCreateWithURL(directory.appendingPathComponent(stage + ".png") as CFURL, nil)!
    let image = CGImageSourceCreateImageAtIndex(source, 0, nil)!
    precondition(image.bitsPerComponent == 8 && image.bitsPerPixel == 32 && image.alphaInfo == .noneSkipLast)
    let bytes = image.dataProvider!.data! as Data
    let after = byStage[stage]!["after"] as! [String: Any]
    let scale = after["scale"] as! Double
    let rect = selection ? selected[0] : after["cursorRectInWindow"] as! [Double]
    let x = Int(((rect[0] + rect[2] / 2) * scale).rounded())
    let y = Int(((rect[1] + rect[3] / 2) * scale).rounded())
    let radius = selection ? 5 : 0
    var count = 0
    for row in (y-radius)...(y+radius) {
        for column in (x-radius)...(x+radius) {
            precondition(row >= 0 && row < image.height && column >= 0 && column < image.width)
            let offset = row * image.bytesPerRow + column * 4
            let actual = bytes[offset..<(offset+3)].map(Int.init)
            precondition(actual == expected, "Unexpected native pixel in \(stage): \(actual)")
            count += 1
        }
    }
    result.append(["stage":stage, "rgb":expected, "pixelsChecked":count, "center":[x,y]])
}
let output: [String: Any] = ["decoder":"Apple ImageIO raw RGBX, no color conversion", "cases":result,
                           "passed":true, "scope":"Retained compositor PNG samples only; no new simulator run"]
print(String(data:try JSONSerialization.data(withJSONObject:output, options:[.prettyPrinted,.sortedKeys]),encoding:.utf8)!)
