/// The measured iOS size hierarchy used by the next shared appearance recipe.
/// These values are data only: they do not select a font, change a renderer,
/// install resources, or modify the existing appearance-v1 wire/default recipe.
public enum UISharedTextProfileV1: String, CaseIterable, Sendable {
    case xs, s, m, l, xl, xxl, xxxl, a1, a2, a3, a4, a5

    public func metrics(for role: UISharedTextRoleV1) -> UISharedTextMetricsV1 {
        let row: (body: UInt32, title: UInt32, caption: UInt32, expanded: UInt32)
        switch self {
        case .xs: row = (14, 25, 11, 31)
        case .s: row = (15, 26, 11, 32)
        case .m: row = (16, 27, 11, 33)
        case .l: row = (17, 28, 12, 34)
        case .xl: row = (19, 30, 14, 36)
        case .xxl: row = (21, 32, 16, 38)
        case .xxxl: row = (23, 34, 18, 40)
        case .a1: row = (28, 38, 22, 44)
        case .a2: row = (33, 43, 26, 48)
        case .a3: row = (40, 48, 32, 52)
        case .a4: row = (47, 53, 37, 56)
        case .a5: row = (53, 58, 43, 60)
        }
        switch role {
        case .body: return UISharedTextMetricsV1(size64: row.body * 64, weight: .w400)
        case .headline, .sectionHeader:
            return UISharedTextMetricsV1(size64: row.body * 64, weight: .w600)
        case .title: return UISharedTextMetricsV1(size64: row.title * 64, weight: .w400)
        case .caption: return UISharedTextMetricsV1(size64: row.caption * 64, weight: .w400)
        case .navigationExpanded:
            return UISharedTextMetricsV1(size64: row.expanded * 64, weight: .w700)
        }
    }
}

public enum UISharedTextRoleV1: String, CaseIterable, Sendable {
    case body, headline, title, caption, sectionHeader, navigationExpanded
}

public struct UISharedTextMetricsV1: Sendable, Equatable {
    /// Logical 1/64 point/dp size, already selected for the requested profile.
    /// Native consumers must not apply a second semantic/sp scale multiplier.
    public let size64: UInt32
    public let weight: UIFontWeightV1
    // Deliberately no fixed text height or clipping box. Native shaping, script
    // fallback, wrapping and accessibility may need a larger layout rectangle.
}

public enum UISharedTextProfileErrorV1: Error, Sendable, Equatable {
    case unsupportedBodySize
}

public enum UISharedTextProfileSelectionV1 {
    /// App policy for a previously converted native body-size preference, in
    /// logical 64ths. Select the nearest measured body anchor; ties select the
    /// larger profile. Outside the supported range is an explicit error, never
    /// a silent accessibility cap or extrapolation. Conversion from a native
    /// preference remains the adapter's responsibility and needs native evidence.
    public static func nearest(preferredBodySize64: UInt32) throws -> UISharedTextProfileV1 {
        let profiles = UISharedTextProfileV1.allCases
        guard preferredBodySize64 >= profiles[0].metrics(for: .body).size64,
              preferredBodySize64 <= profiles[profiles.count - 1].metrics(for: .body).size64 else {
            throw UISharedTextProfileErrorV1.unsupportedBodySize
        }
        for index in 1..<profiles.count {
            let lower = profiles[index - 1].metrics(for: .body).size64
            let upper = profiles[index].metrics(for: .body).size64
            // The checked domain is 896...3392. UInt64 makes the comparison
            // exact without division, floating point or midpoint truncation.
            if UInt64(preferredBodySize64) * 2 < UInt64(lower) + UInt64(upper) {
                return profiles[index - 1]
            }
        }
        return .a5
    }
}
