import CoreGraphics
import Testing
import MixerUI
@testable import MixerApple

private struct NativeElement: Equatable {
    let type: CGPathElementType
    let points: [CGPoint]
}

private func elements(_ path: CGPath) -> [NativeElement] {
    var result: [NativeElement] = []
    path.applyWithBlock { pointer in
        let element = pointer.pointee
        let count: Int
        switch element.type {
        case .moveToPoint, .addLineToPoint: count = 1
        case .addQuadCurveToPoint: count = 2
        case .addCurveToPoint: count = 3
        case .closeSubpath: count = 0
        @unknown default: count = 0
        }
        result.append(NativeElement(type: element.type,
            points: Array(UnsafeBufferPointer(start: element.points, count: count))))
    }
    return result
}

@Test func nativeSharedPathsPreserveClosedCommandsAndFractionalCoordinates() throws {
    let densities: [UInt16] = [128, 1024, 1537, 3072, 16384]
    let paths = [UIAppearanceGeometryV2.track(), UIAppearanceGeometryV2.thumb(),
        try UIAppearanceGeometryV2.group(width64: 1, height64: 1, radius64: 1664),
        try UIAppearanceGeometryV2.group(width64: 24749, height64: 3329, radius64: 1664),
        try UIAppearanceGeometryV2.group(width64: 2147483647, height64: 2147483647, radius64: 65536)]
    for density in densities {
        for path in paths {
            let native = try AppearanceNativePathsV2.make(path, density1024: density)
            let actual = elements(native)
            #expect(actual.count == path.commands.count)
            func point(_ p: UIAppearanceGeometryV2.Point) -> CGPoint {
                CGPoint(x: Double(UInt64(p.x64) * UInt64(density)) / 65536,
                        y: Double(UInt64(p.y64) * UInt64(density)) / 65536)
            }
            let expected = path.commands.map { command -> NativeElement in
                switch command {
                case let .move(p): NativeElement(type: .moveToPoint, points: [point(p)])
                case let .line(p): NativeElement(type: .addLineToPoint, points: [point(p)])
                case let .cubic(a, b, c): NativeElement(type: .addCurveToPoint, points: [point(a), point(b), point(c)])
                case .close: NativeElement(type: .closeSubpath, points: [])
                }
            }
            #expect(actual == expected)
            #expect(actual.last?.type == .closeSubpath)
        }
    }
}

@Test func nativeSharedPathsEmptyGeometryStillValidatesDensity() throws {
    for extent: (UInt32, UInt32) in [(0, 0), (0, 100), (100, 0)] {
        let empty = try UIAppearanceGeometryV2.group(width64: extent.0, height64: extent.1, radius64: 1664)
        #expect(try AppearanceNativePathsV2.make(empty, density1024: 1024).isEmpty)
        for density: UInt16 in [0, 127, 16385, 65535] {
            #expect(throws: UIAppearanceGeometryErrorV2.density) {
                try AppearanceNativePathsV2.make(empty, density1024: density)
            }
        }
    }
}

@Test func nativeSharedPathsOwnIndependentImmutableCopies() throws {
    let geometry = UIAppearanceGeometryV2.track()
    let first = try AppearanceNativePathsV2.make(geometry, density1024: 1024)
    let second = try AppearanceNativePathsV2.make(geometry, density1024: 1024)
    let before = elements(first)
    let mutable = try #require(first.mutableCopy())
    mutable.addRect(CGRect(x: 200, y: 200, width: 10, height: 10))
    #expect(elements(first) == before)
    #expect(elements(second) == before)
    #expect(elements(mutable) != before)
}

@Test func nativeSharedPathsFillAndClipInPixelCoordinates() throws {
    let path = try AppearanceNativePathsV2.make(UIAppearanceGeometryV2.track(), density1024: 2048)
    #expect(path.boundingBoxOfPath == CGRect(x: 0, y: 0, width: 126, height: 56))
    #expect(path.contains(CGPoint(x: 63, y: 28), using: .winding))
    #expect(!path.contains(CGPoint(x: 1, y: 1), using: .winding))
    let width = 140, height = 70
    var pixels = [UInt8](repeating: 0, count: width * height * 4)
    try pixels.withUnsafeMutableBytes { bytes in
        let context = try #require(CGContext(data: bytes.baseAddress, width: width, height: height,
            bitsPerComponent: 8, bytesPerRow: width * 4, space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue))
        context.setShouldAntialias(false)
        context.addPath(path)
        context.clip(using: .winding)
        context.setFillColor(red: 1, green: 0, blue: 0, alpha: 1)
        context.fill(CGRect(x: 0, y: 0, width: width, height: height))
    }
    func pixel(_ x: Int, _ y: Int) -> [UInt8] {
        Array(pixels[((y * width + x) * 4)..<((y * width + x) * 4 + 4)])
    }
    #expect(pixel(63, 28) == [255, 0, 0, 255])
    #expect(pixel(1, 1) == [0, 0, 0, 0])
    #expect(pixel(130, 28) == [0, 0, 0, 0])
    #expect(pixel(63, 60) == [0, 0, 0, 0])
}
