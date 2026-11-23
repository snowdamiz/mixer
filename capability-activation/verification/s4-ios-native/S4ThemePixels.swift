import CoreGraphics
import UIKit
import XCTest

struct S4ThemePixels {
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

struct S4ThemeSample {
    let readyPixels: S4ThemePixels
    let savePixels: S4ThemePixels

    // Independent screenshot expectations for the installed S4 light fixture.
    private static let body = S4ThemePixels.RGB(8, 123, 103)
    private static let fill = S4ThemePixels.RGB(82, 36, 138)
    private static let label = S4ThemePixels.RGB(218, 255, 171)

    var readback: [String: Double] {
        [
            "readyInk": readyPixels.fraction(of: Self.body),
            "saveFillLeft": savePixels.fraction(of: Self.fill, x: 0.08..<0.14, y: 0.27..<0.73),
            "saveFillRight": savePixels.fraction(of: Self.fill, x: 0.86..<0.92, y: 0.27..<0.73),
            "saveLabelInk": savePixels.fraction(of: Self.label, x: 0.15..<0.85, y: 0.20..<0.80)
        ]
    }

    var evidence: String {
        let regions = readback.sorted { $0.key < $1.key }.map { "\($0.key)=\($0.value)" }
        return (["ready=\(readyPixels.width)x\(readyPixels.height)", "save=\(savePixels.width)x\(savePixels.height)"] +
                regions).joined(separator: "\n")
    }

    func assertDefault() {
        for (region, fraction) in readback {
            XCTAssertLessThan(fraction, 0.002, "Shared paint unexpectedly appeared in the default \(region) region")
        }
    }

    func assertTheme() {
        let regions = readback
        XCTAssertGreaterThan(regions["readyInk"]!, 0.008, "Ready must use the shared body paint")
        XCTAssertGreaterThan(regions["saveFillLeft"]!, 0.95, "Save must use the shared fill across its hit surface")
        XCTAssertGreaterThan(regions["saveFillRight"]!, 0.95, "Save must use the shared fill across its hit surface")
        XCTAssertGreaterThan(regions["saveLabelInk"]!, 0.01, "Save must use the shared label paint")
    }

    func assertMatches(_ bundled: Self) {
        // A fractional-pixel origin can change the capture edge and antialiasing.
        for (ours, theirs) in [(readyPixels, bundled.readyPixels), (savePixels, bundled.savePixels)] {
            XCTAssertLessThanOrEqual(abs(ours.width - theirs.width), 2)
            XCTAssertLessThanOrEqual(abs(ours.height - theirs.height), 2)
        }
        let reference = bundled.readback
        for (region, fraction) in readback {
            XCTAssertEqual(fraction, reference[region]!, accuracy: 0.03, "Bundled and guest differ in \(region)")
        }
    }
}
