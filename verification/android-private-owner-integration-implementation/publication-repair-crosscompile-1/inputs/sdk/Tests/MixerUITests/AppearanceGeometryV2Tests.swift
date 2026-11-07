import XCTest
import MixerUI

final class AppearanceGeometryV2Tests: XCTestCase {
    private typealias Geometry = UIAppearanceGeometryV2

    private func coordinates(_ command: Geometry.Command) -> [[UInt32]] {
        switch command {
        case let .move(p), let .line(p): return [[p.x64, p.y64]]
        case let .cubic(a, b, c): return [[a.x64, a.y64], [b.x64, b.y64], [c.x64, c.y64]]
        case .close: return []
        }
    }

    func testGroupMatchesFrozen370By208AuthoredPath() throws {
        // Frozen integer contract output; no native raster equality is inferred.
        let expected: [[[UInt32]]] = [
            [[23680,6656]], [[23680,10768]],
            [[23680,11501],[23680,11867],[23555,12261]],
            [[23399,12692],[23060,13031],[22629,13187]],
            [[22235,13312],[21869,13312],[21136,13312]], [[2544,13312]],
            [[1811,13312],[1445,13312],[1051,13187]],
            [[620,13031],[281,12692],[125,12261]],
            [[0,11867],[0,11501],[0,10768]], [[0,2544]],
            [[0,1811],[0,1445],[125,1051]], [[281,620],[620,281],[1051,125]],
            [[1445,0],[1811,0],[2544,0]], [[21136,0]],
            [[21869,0],[22235,0],[22629,125]], [[23060,281],[23399,620],[23555,1051]],
            [[23680,1445],[23680,1811],[23680,2544]], [],
        ]
        let path = try Geometry.group(width64: 370 * 64, height64: 208 * 64, radius64: 26 * 64)
        XCTAssertEqual(path.shape, .fullGroupContinuousCubic2)
        XCTAssertEqual(path.commands.map(coordinates), expected)
        XCTAssertEqual(path.commands.last, .close)
    }

    func testClosedGroupBoundsAndReflectionsIncludingDegenerateBoxes() throws {
        let extents: [UInt32] = [0,1,2,3,5,63,64,127,128,1792,3328,23680,65536,2_147_483_647]
        for w in extents {
            for h in extents {
                for radius: UInt32 in [0,1,16,1664,65536] {
                    let path = try Geometry.group(width64: w, height64: h, radius64: radius)
                    XCTAssertEqual(path.width64, w)
                    XCTAssertEqual(path.height64, h)
                    if w == 0 || h == 0 {
                        XCTAssertEqual(path.commands, [])
                        continue
                    }
                    XCTAssertEqual(path.commands.count, 18)
                    XCTAssertEqual(path.commands.filter { $0 == .close }.count, 1)
                    XCTAssertEqual(path.commands.last, .close)
                    let points = path.commands.dropFirst().flatMap(coordinates)
                    let set = Set(points.map { "\($0[0]),\($0[1])" })
                    for point in points {
                        XCTAssertLessThanOrEqual(point[0], w)
                        XCTAssertLessThanOrEqual(point[1], h)
                        XCTAssertTrue(set.contains("\(w - point[0]),\(point[1])"))
                        XCTAssertTrue(set.contains("\(point[0]),\(h - point[1])"))
                    }
                    // The top-left tangent cannot overlap its opposite corner.
                    let tangent = coordinates(path.commands[9])[0][1]
                    XCTAssertLessThanOrEqual(UInt64(tangent) * 2, UInt64(min(w, h)))
                }
            }
        }
    }

    func testFixedSwitchGeometryAndCheckedEndMirror() {
        let track = Geometry.track(), thumb = Geometry.thumb()
        XCTAssertEqual(track.shape, .track63x28Continuous2)
        XCTAssertEqual(thumb.shape, .thumb37x24Continuous2)
        XCTAssertEqual([track.width64,track.height64,thumb.width64,thumb.height64], [4032,1792,2368,1536])
        XCTAssertEqual(coordinates(track.commands[3]), [[3881,1458],[3698,1641],[3466,1725]])
        XCTAssertEqual(coordinates(thumb.commands[3]), [[2238,1250],[2082,1406],[1883,1478]])
        for path in [track, thumb] {
            XCTAssertEqual(path.commands.count, 18)
            XCTAssertEqual(path.commands.filter { $0 == .close }.count, 1)
            XCTAssertEqual(path.commands.last, .close)
            for point in path.commands.flatMap(coordinates) {
                XCTAssertLessThanOrEqual(point[0], path.width64)
                XCTAssertLessThanOrEqual(point[1], path.height64)
            }
        }
        for checked in [false, true] {
            let ltr = Geometry.thumbOrigin(checked: checked, direction: .leftToRight)
            let rtl = Geometry.thumbOrigin(checked: checked, direction: .rightToLeft)
            XCTAssertEqual(ltr.y64, 128)
            XCTAssertEqual(rtl.y64, 128)
            XCTAssertEqual(ltr.x64 + rtl.x64 + thumb.width64, track.width64)
            XCTAssertEqual(ltr.x64, checked ? 1536 : 128)
            XCTAssertEqual(ltr.y64 + thumb.height64 + 128, track.height64)
        }
    }

    func testMeasurementAndPixelConversionPreserveBoundsAndFractions() throws {
        XCTAssertEqual(try Geometry.measuredExtent64(0), 0)
        XCTAssertEqual(try Geometry.measuredExtent64(1.0 / 128), 1)
        XCTAssertEqual(try Geometry.measuredExtent64(1.0 / 64), 1)
        XCTAssertEqual(try Geometry.measuredExtent64((1.0 / 64).nextUp), 2)
        XCTAssertEqual(try Geometry.measuredExtent64(Double(Geometry.maximumExtent64) / 64), Geometry.maximumExtent64)
        XCTAssertEqual(try Geometry.spacing64(1.0 / 128), 1)
        XCTAssertEqual(try Geometry.spacing64((1.0 / 128).nextDown), 0)
        XCTAssertEqual(try Geometry.spacing64(256), 16384)
        XCTAssertEqual(try Geometry.normalizeDensity(0.125), 128)
        XCTAssertEqual(try Geometry.normalizeDensity(16), 16384)
        XCTAssertEqual(try Geometry.normalizeDensity(1024.5 / 1024), 1025)
        XCTAssertEqual(try Geometry.normalizeDensity((1024.5 / 1024).nextDown), 1024)
        XCTAssertEqual(try Geometry.pixelEdge(32, density1024: 1024), 1)
        XCTAssertEqual(try Geometry.pixelEdge(31, density1024: 1024), 0)
        XCTAssertEqual(try Geometry.pixelCoordinate(31, density1024: 1024), 31.0 / 64)
        for density: UInt16 in [128,512,1024,1536,3072,16384] {
            var last: UInt32 = 0
            for coordinate in UInt32(0)...1024 {
                let edge = try Geometry.pixelEdge(coordinate, density1024: density)
                XCTAssertGreaterThanOrEqual(edge, last)
                let native = try Geometry.pixelCoordinate(coordinate, density1024: density)
                XCTAssertLessThanOrEqual(abs(Double(edge) - native), 0.5)
                last = edge
            }
            let maximum = try Geometry.pixelEdge(Geometry.maximumExtent64, density1024: density)
            XCTAssertLessThanOrEqual(maximum, 536_870_912)
        }
    }

    func testUnsupportedInputsRejectInsteadOfClampingOrTrapping() {
        for value in [-1.0, Double.nan, .infinity, -.infinity,
                      (Double(Geometry.maximumExtent64) / 64).nextUp] {
            XCTAssertThrowsError(try Geometry.measuredExtent64(value)) {
                XCTAssertEqual($0 as? UIAppearanceGeometryErrorV2, .extent)
            }
        }
        for value in [-1.0, Double.nan, .infinity, 256.0.nextUp] {
            XCTAssertThrowsError(try Geometry.spacing64(value))
        }
        for value in [(0.125).nextDown, (16.0).nextUp, 0, -1, Double.nan, .infinity, -.infinity] {
            XCTAssertThrowsError(try Geometry.normalizeDensity(value)) {
                XCTAssertEqual($0 as? UIAppearanceGeometryErrorV2, .density)
            }
        }
        XCTAssertThrowsError(try Geometry.group(width64: .max, height64: 0, radius64: 0))
        XCTAssertThrowsError(try Geometry.group(width64: 0, height64: .max, radius64: 0))
        XCTAssertThrowsError(try Geometry.group(width64: 0, height64: 0, radius64: 65537))
        for density: UInt16 in [0,127,16385,.max] {
            XCTAssertThrowsError(try Geometry.pixelEdge(0, density1024: density))
            XCTAssertThrowsError(try Geometry.pixelCoordinate(0, density1024: density))
        }
        XCTAssertThrowsError(try Geometry.pixelEdge(.max, density1024: 1024))
        XCTAssertThrowsError(try Geometry.pixelCoordinate(.max, density1024: 1024))
    }
}
