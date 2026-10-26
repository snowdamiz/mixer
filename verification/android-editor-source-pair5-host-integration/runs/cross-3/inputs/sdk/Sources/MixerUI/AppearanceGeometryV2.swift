/// Closed, authored geometry for the opt-in measuredShared2 recipe. These are
/// app shapes, not a claim to reproduce a platform's private control paths.
public enum UINativeShapeV2: String, Sendable, Equatable {
    case fullGroupContinuousCubic2, track63x28Continuous2, thumb37x24Continuous2
}

public enum UIAppearanceGeometryErrorV2: Error, Sendable, Equatable {
    case extent, radius, density, spacing
}

/// Logical coordinates use 1/64 point/dp. Native adapters own drawing, text
/// measurement and density application; obtaining a path grants no native support.
public enum UIAppearanceGeometryV2 {
    public struct Point: Sendable, Equatable {
        public let x64: UInt32
        public let y64: UInt32
    }

    public enum Command: Sendable, Equatable {
        case move(Point)
        case line(Point)
        case cubic(control1: Point, control2: Point, end: Point)
        case close
    }

    /// Construction is private to the closed recipes. Consumers can inspect the
    /// immutable commands, but no descriptor can supply arbitrary path commands.
    public struct Path: Sendable, Equatable {
        public let shape: UINativeShapeV2
        public let width64: UInt32
        public let height64: UInt32
        public let commands: [Command]

        fileprivate init(_ shape: UINativeShapeV2, _ width64: UInt32,
                         _ height64: UInt32, _ commands: [Command]) {
            self.shape = shape
            self.width64 = width64
            self.height64 = height64
            self.commands = commands
        }
    }

    public static let maximumExtent64: UInt32 = 2_147_483_647

    /// One full group outline. The tangent extent is 1.528665 times the authored
    /// radius, so clamping by half the box alone would allow corners to overlap.
    /// All arithmetic is within UInt64 for the admitted inputs. Reflect rounded
    /// offsets by subtraction to preserve exact opposite-edge symmetry.
    public static func group(width64 w: UInt32, height64 h: UInt32,
                             radius64: UInt32) throws -> Path {
        guard w <= maximumExtent64, h <= maximumExtent64 else {
            throw UIAppearanceGeometryErrorV2.extent
        }
        guard radius64 <= 65_536 else { throw UIAppearanceGeometryErrorV2.radius }
        guard w != 0, h != 0 else {
            return Path(.fullGroupContinuousCubic2, w, h, [])
        }
        let radius = min(UInt64(radius64), UInt64(min(w, h)) * 1_000_000 / 3_057_330)
        func offset(_ coefficient: UInt64) -> UInt32 {
            UInt32((radius * coefficient + 500_000) / 1_000_000)
        }
        let a = offset(1_528_665), b = offset(1_088_490), c = offset(868_407)
        let d = offset(631_494), e = offset(74_911), f = offset(169_060), g = offset(372_824)
        return Path(.fullGroupContinuousCubic2, w, h, [
            .move(p(w, h / 2 + h % 2)), .line(p(w, h - a)),
            .cubic(control1: p(w, h - b), control2: p(w, h - c), end: p(w - e, h - d)),
            .cubic(control1: p(w - f, h - g), control2: p(w - g, h - f), end: p(w - d, h - e)),
            .cubic(control1: p(w - c, h), control2: p(w - b, h), end: p(w - a, h)),
            .line(p(a, h)),
            .cubic(control1: p(b, h), control2: p(c, h), end: p(d, h - e)),
            .cubic(control1: p(g, h - f), control2: p(f, h - g), end: p(e, h - d)),
            .cubic(control1: p(0, h - c), control2: p(0, h - b), end: p(0, h - a)),
            .line(p(0, a)),
            .cubic(control1: p(0, b), control2: p(0, c), end: p(e, d)),
            .cubic(control1: p(f, g), control2: p(g, f), end: p(d, e)),
            .cubic(control1: p(c, 0), control2: p(b, 0), end: p(a, 0)),
            .line(p(w - a, 0)),
            .cubic(control1: p(w - b, 0), control2: p(w - c, 0), end: p(w - d, e)),
            .cubic(control1: p(w - g, f), control2: p(w - f, g), end: p(w - e, d)),
            .cubic(control1: p(w, c), control2: p(w, b), end: p(w, a)), .close,
        ])
    }

    public static func track() -> Path {
        Path(.track63x28Continuous2, 4032, 1792, [
            .move(p(4032, 896)), .line(p(4032, 896)),
            .cubic(control1: p(4032, 932), control2: p(4032, 1057), end: p(3965, 1226)),
            .cubic(control1: p(3881, 1458), control2: p(3698, 1641), end: p(3466, 1725)),
            .cubic(control1: p(3254, 1792), control2: p(3057, 1792), end: p(2662, 1792)),
            .line(p(1370, 1792)),
            .cubic(control1: p(975, 1792), control2: p(778, 1792), end: p(566, 1725)),
            .cubic(control1: p(334, 1641), control2: p(151, 1458), end: p(67, 1226)),
            .cubic(control1: p(0, 1057), control2: p(0, 932), end: p(0, 896)),
            .line(p(0, 896)),
            .cubic(control1: p(0, 860), control2: p(0, 735), end: p(67, 566)),
            .cubic(control1: p(151, 334), control2: p(334, 151), end: p(566, 67)),
            .cubic(control1: p(778, 0), control2: p(975, 0), end: p(1370, 0)),
            .line(p(2662, 0)),
            .cubic(control1: p(3057, 0), control2: p(3254, 0), end: p(3466, 67)),
            .cubic(control1: p(3698, 151), control2: p(3881, 334), end: p(3965, 566)),
            .cubic(control1: p(4032, 735), control2: p(4032, 860), end: p(4032, 896)), .close,
        ])
    }

    public static func thumb() -> Path {
        Path(.thumb37x24Continuous2, 2368, 1536, [
            .move(p(2368, 768)), .line(p(2368, 768)),
            .cubic(control1: p(2368, 799), control2: p(2368, 906), end: p(2310, 1051)),
            .cubic(control1: p(2238, 1250), control2: p(2082, 1406), end: p(1883, 1478)),
            .cubic(control1: p(1701, 1536), control2: p(1532, 1536), end: p(1194, 1536)),
            .line(p(1174, 1536)),
            .cubic(control1: p(836, 1536), control2: p(667, 1536), end: p(485, 1478)),
            .cubic(control1: p(286, 1406), control2: p(130, 1250), end: p(58, 1051)),
            .cubic(control1: p(0, 906), control2: p(0, 799), end: p(0, 768)),
            .line(p(0, 768)),
            .cubic(control1: p(0, 737), control2: p(0, 630), end: p(58, 485)),
            .cubic(control1: p(130, 286), control2: p(286, 130), end: p(485, 58)),
            .cubic(control1: p(667, 0), control2: p(836, 0), end: p(1174, 0)),
            .line(p(1194, 0)),
            .cubic(control1: p(1532, 0), control2: p(1701, 0), end: p(1883, 58)),
            .cubic(control1: p(2082, 130), control2: p(2238, 286), end: p(2310, 485)),
            .cubic(control1: p(2368, 630), control2: p(2368, 737), end: p(2368, 768)), .close,
        ])
    }

    public static func thumbOrigin(checked: Bool, direction: UILayoutDirectionV1) -> Point {
        p(checked != (direction == .rightToLeft) ? 1536 : 128, 128)
    }

    /// Convert a measured nonnegative logical extent without rounding it smaller.
    public static func measuredExtent64(_ value: Double) throws -> UInt32 {
        guard value.isFinite, value >= 0, value <= Double(maximumExtent64) / 64 else {
            throw UIAppearanceGeometryErrorV2.extent
        }
        return UInt32((value * 64).rounded(.up))
    }

    public static func spacing64(_ value: Double) throws -> UInt32 {
        guard value.isFinite, (0...256).contains(value) else {
            throw UIAppearanceGeometryErrorV2.spacing
        }
        return UInt32((value * 64).rounded(.toNearestOrAwayFromZero))
    }

    /// Reject unsupported raw density before quantization; a value just outside
    /// the interval cannot round back into support.
    public static func normalizeDensity(_ value: Double) throws -> UInt16 {
        guard value.isFinite, (0.125...16).contains(value) else {
            throw UIAppearanceGeometryErrorV2.density
        }
        return UInt16((value * 1024).rounded(.toNearestOrAwayFromZero))
    }

    /// Edges use nearest/ties-up rounding. Round absolute rectangle edges, then
    /// subtract them for dimensions; do not independently round a row's width.
    public static func pixelEdge(_ coordinate64: UInt32, density1024: UInt16) throws -> UInt32 {
        try admitCoordinate(coordinate64, density1024)
        return UInt32((UInt64(coordinate64) * UInt64(density1024) + 32768) / 65536)
    }

    /// Cubic control points retain their fraction. Do not integer-round each
    /// control point or apply a second native density transform to these pixels.
    public static func pixelCoordinate(_ coordinate64: UInt32, density1024: UInt16) throws -> Double {
        try admitCoordinate(coordinate64, density1024)
        return Double(UInt64(coordinate64) * UInt64(density1024)) / 65536
    }

    private static func admitCoordinate(_ coordinate64: UInt32, _ density1024: UInt16) throws {
        guard coordinate64 <= maximumExtent64 else { throw UIAppearanceGeometryErrorV2.extent }
        guard (128...16384).contains(density1024) else { throw UIAppearanceGeometryErrorV2.density }
    }

    private static func p(_ x: UInt32, _ y: UInt32) -> Point { Point(x64: x, y64: y) }
}
