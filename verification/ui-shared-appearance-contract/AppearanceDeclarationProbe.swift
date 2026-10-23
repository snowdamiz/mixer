// DESIGN ONLY. Compiler probe, never linked into Mixer or executed.
// fatalError bodies intentionally provide no resolver or validation semantics.
// This checks the immutable declaration shape and representative app call sites.
public struct UIAppearanceConfigurationV1: Sendable {
    public let id: String
    public let mode: UIAppearanceModeV1
    public init(id: String, mode: UIAppearanceModeV1) throws {
        fatalError("declaration-only")
    }
    public static var mixerDefaultV1: Self { fatalError("declaration-only") }
}
public enum UIAppearanceModeV1: Sendable {
    case shared(UIThemeV1)
    case platformSpecific(iOS: UIThemeV1, android: UIThemeV1, reason: String)
}
public struct UIThemeV1: Sendable {
    public let light: UIPaletteV1
    public let dark: UIPaletteV1
    public let typography: UITypographyV1
    public let metrics: UIMetricsV1
    public let controls: UIControlsV1
    public let assets: [UIAssetV1]
}
public enum UIFontSourceV1: Sendable {
    case systemSans
    case bundled(faces: [UIFontFaceV1], fallback: UIFontFallbackV1)
}
public enum UIFontFallbackV1: Sendable { case none, systemSans }
public struct UIFontFaceV1: Sendable {
    public let id: String
    public let bundleRelativePath: String
    public let sha256: String
    public let provenance: String
    public let postScriptIdentity: String
    public let weight: UInt16
    public let italic: Bool
}
public struct UIRGBA8V1: Sendable {
    public let red: UInt8, green: UInt8, blue: UInt8, alpha: UInt8
}
public struct UIPaletteV1: Sendable {
    public let canvas, surface, primaryText, secondaryText: UIRGBA8V1
    public let accent, destructive, disabledText, separator, focus: UIRGBA8V1
    public let toggleOff, toggleThumb, pressedOverlay: UIRGBA8V1
    public let pressedOverlayAlpha: Double
}
public struct UITextMetricV1: Sendable {
    public let size, minimumLineBox: Double
    public let weight: UInt16
}
public struct UITypographyV1: Sendable {
    public let font: UIFontSourceV1
    public let body, headline, title, caption: UITextMetricV1
}
public struct UILogicalInsetsV1: Sendable {
    public let top, leading, bottom, trailing: Double
}
public struct UIMetricsV1: Sendable {
    public let stackGap, listMinimumRow, listRowGap, listGroupGap: Double
    public let listSeparator, navigationMinimumBarHeight: Double
    public let listInsets, sectionHeaderInsets, navigationTitleInsets: UILogicalInsetsV1
}
public struct UIControlsV1: Sendable {
    public let buttonLabelInsets, fieldInsets: UILogicalInsetsV1
    public let minimumHitWidth, minimumRowHeight, buttonRadius: Double
    public let fieldNormalBorder, focusWidth, focusRadius: Double
    public let toggleTrackWidth, toggleTrackHeight, toggleThumbSize: Double
    public let toggleInset, toggleLabelGap: Double
}
public enum UIAssetKindV1: Sendable { case raster, vector }
public struct UIAssetV1: Sendable {
    public let id, bundleRelativePath, sha256, provenance: String
    public let kind: UIAssetKindV1
    public let scale: UInt8
    public let locale: String
    public let direction: UIAssetDirectionV1
}
public enum UIAssetDirectionV1: Sendable { case neutral, leftToRight, rightToLeft }

// No native enum or toolkit style is needed at these app declaration sites.
func appDeclaration(sharedTheme: UIThemeV1, iOS: UIThemeV1, android: UIThemeV1)
    throws -> [UIAppearanceConfigurationV1] {
    [try UIAppearanceConfigurationV1(id: "app.shared", mode: .shared(sharedTheme)),
     try UIAppearanceConfigurationV1(id: "app.explicit", mode:
         .platformSpecific(iOS: iOS, android: android, reason: "App-declared variant")),
     .mixerDefaultV1]
}
func declaredFont(faces: [UIFontFaceV1]) -> (UIFontSourceV1, UIFontSourceV1) {
    (.systemSans, .bundled(faces: faces, fallback: .none))
}
