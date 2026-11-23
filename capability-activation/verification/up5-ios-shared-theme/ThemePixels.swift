import CoreGraphics
import UIKit
import XCTest

struct ThemePixels {
    let width: Int
    let height: Int
    private let rgba: [UInt8]

    @MainActor
    init(_ screenshot: XCUIScreenshot) throws {
        let image = try XCTUnwrap(screenshot.image.cgImage)
        let width = image.width
        let height = image.height
        let colorSpace = try XCTUnwrap(CGColorSpace(name: CGColorSpace.sRGB))
        var rgba = [UInt8](repeating: 0, count: width * height * 4)
        try rgba.withUnsafeMutableBytes { bytes in
            let context = try XCTUnwrap(CGContext(
                data: bytes.baseAddress, width: width, height: height, bitsPerComponent: 8,
                bytesPerRow: width * 4, space: colorSpace,
                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue
            ))
            context.setBlendMode(.copy)
            context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        }
        self.width = width
        self.height = height
        self.rgba = rgba
    }

    struct RGB {
        let red: Int
        let green: Int
        let blue: Int

        init(_ red: Int, _ green: Int, _ blue: Int) {
            self.red = red
            self.green = green
            self.blue = blue
        }
    }

    func fraction(of color: RGB, x: Range<Double> = 0..<1, y: Range<Double> = 0..<1) -> Double {
        let columns = Int(x.lowerBound * Double(width))..<Int(x.upperBound * Double(width))
        let rows = Int(y.lowerBound * Double(height))..<Int(y.upperBound * Double(height))
        var matches = 0
        for row in rows {
            for column in columns {
                let offset = (row * width + column) * 4
                if rgba[offset + 3] >= 248,
                   abs(Int(rgba[offset]) - color.red) <= 8,
                   abs(Int(rgba[offset + 1]) - color.green) <= 8,
                   abs(Int(rgba[offset + 2]) - color.blue) <= 8 {
                    matches += 1
                }
            }
        }
        return Double(matches) / Double(rows.count * columns.count)
    }
}
