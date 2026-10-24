import CoreGraphics
import MixerUI

/// Converts the closed shared geometry into a fresh, immutable native path.
/// Coordinates are local physical pixels with a top-left origin. The eventual
/// native consumer owns placement/clipping and must use nonzero winding fill;
/// it must not apply another display-density transform to these coordinates.
/// A path alone supplies no native appearance or resource-support authority.
enum AppearanceNativePathsV2 {
    enum Failure: Error { case pathCopy }

    static func make(_ geometry: UIAppearanceGeometryV2.Path,
                     density1024: UInt16) throws -> CGPath {
        // Empty geometry must reject an unsupported density as well.
        _ = try UIAppearanceGeometryV2.pixelCoordinate(0, density1024: density1024)
        func point(_ value: UIAppearanceGeometryV2.Point) throws -> CGPoint {
            CGPoint(x: try UIAppearanceGeometryV2.pixelCoordinate(value.x64, density1024: density1024),
                    y: try UIAppearanceGeometryV2.pixelCoordinate(value.y64, density1024: density1024))
        }
        let path = CGMutablePath()
        for command in geometry.commands {
            switch command {
            case let .move(value): path.move(to: try point(value))
            case let .line(value): path.addLine(to: try point(value))
            case let .cubic(first, second, end):
                path.addCurve(to: try point(end), control1: try point(first), control2: try point(second))
            case .close: path.closeSubpath()
            }
        }
        guard let result = path.copy() else { throw Failure.pathCopy }
        return result
    }
}
