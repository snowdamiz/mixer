import Foundation

/// Checked fixed-point math. Inputs are logical units; this does not measure a native view.
public enum UIAppearanceMetricMathV1 {
    public static func scaled64(_ metric64: UInt32, textScale1024: UInt16) throws -> UInt32 {
        guard metric64 <= 65_536, (512...4096).contains(textScale1024) else {
            throw UIAppearanceErrorV1.number
        }
        return UInt32((UInt64(metric64) * UInt64(textScale1024) + 512) / 1024)
    }

    public static func pixels(_ metric64: UInt32, density1024: UInt16) throws -> UInt32 {
        guard metric64 <= 262_144, (128...16_384).contains(density1024) else {
            throw UIAppearanceErrorV1.number
        }
        return UInt32((UInt64(metric64) * UInt64(density1024) + 32_768) / 65_536)
    }

    public static func spacing64(_ value: Double) throws -> UInt32 {
        guard value.isFinite, (0...256).contains(value) else { throw UIAppearanceErrorV1.number }
        return UInt32(floor(value * 64 + 0.5))
    }

    public static func normalizeTextScale(_ value: Double) throws -> UInt16 {
        try normalize(value, range: 0.5...4)
    }

    public static func normalizeDensity(_ value: Double) throws -> UInt16 {
        try normalize(value, range: 0.125...16)
    }

    private static func normalize(_ value: Double, range: ClosedRange<Double>) throws -> UInt16 {
        guard value.isFinite, range.contains(value) else { throw UIAppearanceErrorV1.number }
        return UInt16(floor(value * 1024 + 0.5))
    }
}
