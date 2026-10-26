// Raw values do not establish validation, native resource provenance, or release authority.
// Every descriptor codec entry validates the entire graph.
import Foundation
public struct UIRGBA8V1: Sendable, Equatable {
    public let red, green, blue, alpha: UInt8
    public init(red: UInt8, green: UInt8, blue: UInt8, alpha: UInt8) {
        self.red = red; self.green = green; self.blue = blue; self.alpha = alpha
    }
}
public enum UIRecipeV1: String, Sendable, Equatable {
    case sharedCandidate1 = "sharedCandidate1"
}

public enum UIFontWeightV1: UInt16, Sendable, Equatable {
    case w400 = 400
    case w500 = 500
    case w600 = 600
    case w700 = 700
}

public enum UIFontStyleV1: String, Sendable, Equatable {
    case normal = "normal"
    case italic = "italic"
}

public enum UIFontFallbackV1: String, Sendable, Equatable {
    case none = "none"
    case systemSans = "systemSans"
}

public enum UIResourceKindV1: String, Sendable, Equatable {
    case fontSFNT = "fontSFNT"
    case iconPNG = "iconPNG"
}

public enum UIResourceDirectionV1: String, Sendable, Equatable {
    case neutral = "neutral"
    case leftToRight = "leftToRight"
    case rightToLeft = "rightToLeft"
}

public enum UIHorizontalAlignmentV1: String, Sendable, Equatable {
    case leading = "leading"
    case center = "center"
    case trailing = "trailing"
}

public enum UIVerticalAlignmentV1: String, Sendable, Equatable {
    case top = "top"
    case center = "center"
    case bottom = "bottom"
    case firstTextBaseline = "firstTextBaseline"
    case lastTextBaseline = "lastTextBaseline"
}

public enum UIOverlayAlignmentV1: String, Sendable, Equatable {
    case center = "center"
    case leading = "leading"
    case trailing = "trailing"
    case top = "top"
    case bottom = "bottom"
    case topLeading = "topLeading"
    case topTrailing = "topTrailing"
    case bottomLeading = "bottomLeading"
    case bottomTrailing = "bottomTrailing"
}

public enum UIColorSchemeV1: String, Sendable, Equatable {
    case light = "light"
    case dark = "dark"
}

public enum UILayoutDirectionV1: String, Sendable, Equatable {
    case leftToRight = "leftToRight"
    case rightToLeft = "rightToLeft"
}

public struct UIInsets64V1: Sendable, Equatable {
    public let top: UInt32
    public let leading: UInt32
    public let bottom: UInt32
    public let trailing: UInt32
    public init(top: UInt32, leading: UInt32, bottom: UInt32, trailing: UInt32) {
        self.top = top
        self.leading = leading
        self.bottom = bottom
        self.trailing = trailing
    }
}

public struct UIPaletteV1: Sendable, Equatable {
    public let canvas: UIRGBA8V1
    public let surface: UIRGBA8V1
    public let primaryText: UIRGBA8V1
    public let secondaryText: UIRGBA8V1
    public let accent: UIRGBA8V1
    public let destructive: UIRGBA8V1
    public let disabledText: UIRGBA8V1
    public let separator: UIRGBA8V1
    public let focus: UIRGBA8V1
    public let toggleOff: UIRGBA8V1
    public let toggleThumb: UIRGBA8V1
    public init(canvas: UIRGBA8V1, surface: UIRGBA8V1, primaryText: UIRGBA8V1, secondaryText: UIRGBA8V1, accent: UIRGBA8V1, destructive: UIRGBA8V1, disabledText: UIRGBA8V1, separator: UIRGBA8V1, focus: UIRGBA8V1, toggleOff: UIRGBA8V1, toggleThumb: UIRGBA8V1) {
        self.canvas = canvas
        self.surface = surface
        self.primaryText = primaryText
        self.secondaryText = secondaryText
        self.accent = accent
        self.destructive = destructive
        self.disabledText = disabledText
        self.separator = separator
        self.focus = focus
        self.toggleOff = toggleOff
        self.toggleThumb = toggleThumb
    }
}

public struct UITextMetricV1: Sendable, Equatable {
    public let size64: UInt32
    public let weight: UIFontWeightV1
    public let minimumLineBox64: UInt32
    public init(size64: UInt32, weight: UIFontWeightV1, minimumLineBox64: UInt32) {
        self.size64 = size64
        self.weight = weight
        self.minimumLineBox64 = minimumLineBox64
    }
}

public struct UIFontFaceV1: Sendable, Equatable {
    public let resourceID: String
    public let postScriptName: String
    public let weight: UIFontWeightV1
    public let style: UIFontStyleV1
    public init(resourceID: String, postScriptName: String, weight: UIFontWeightV1, style: UIFontStyleV1) {
        self.resourceID = resourceID
        self.postScriptName = postScriptName
        self.weight = weight
        self.style = style
    }
}

public enum UIFontSourceV1: Sendable, Equatable {
    case systemSans
    case bundled(faces: [UIFontFaceV1], fallback: UIFontFallbackV1)
}

public struct UITypographyV1: Sendable, Equatable {
    public let font: UIFontSourceV1
    public let body: UITextMetricV1
    public let headline: UITextMetricV1
    public let title: UITextMetricV1
    public let caption: UITextMetricV1
    public init(font: UIFontSourceV1, body: UITextMetricV1, headline: UITextMetricV1, title: UITextMetricV1, caption: UITextMetricV1) {
        self.font = font
        self.body = body
        self.headline = headline
        self.title = title
        self.caption = caption
    }
}

public struct UIListMetricsV1: Sendable, Equatable {
    public let insets64: UIInsets64V1
    public let minimumRow64: UInt32
    public let rowGap64: UInt32
    public let groupGap64: UInt32
    public let separator64: UInt32
    public init(insets64: UIInsets64V1, minimumRow64: UInt32, rowGap64: UInt32, groupGap64: UInt32, separator64: UInt32) {
        self.insets64 = insets64
        self.minimumRow64 = minimumRow64
        self.rowGap64 = rowGap64
        self.groupGap64 = groupGap64
        self.separator64 = separator64
    }
}

public struct UINavigationMetricsV1: Sendable, Equatable {
    public let titleInsets64: UIInsets64V1
    public let minimumBarHeight64: UInt32
    public let titleAlignment: UIHorizontalAlignmentV1
    public init(titleInsets64: UIInsets64V1, minimumBarHeight64: UInt32, titleAlignment: UIHorizontalAlignmentV1) {
        self.titleInsets64 = titleInsets64
        self.minimumBarHeight64 = minimumBarHeight64
        self.titleAlignment = titleAlignment
    }
}

public struct UILayoutMetricsV1: Sendable, Equatable {
    public let stackGap64: UInt32
    public let vStackAlignment: UIHorizontalAlignmentV1
    public let hStackAlignment: UIVerticalAlignmentV1
    public let zStackAlignment: UIOverlayAlignmentV1
    public let list: UIListMetricsV1
    public let sectionHeaderInsets64: UIInsets64V1
    public let navigation: UINavigationMetricsV1
    public init(stackGap64: UInt32, vStackAlignment: UIHorizontalAlignmentV1, hStackAlignment: UIVerticalAlignmentV1, zStackAlignment: UIOverlayAlignmentV1, list: UIListMetricsV1, sectionHeaderInsets64: UIInsets64V1, navigation: UINavigationMetricsV1) {
        self.stackGap64 = stackGap64
        self.vStackAlignment = vStackAlignment
        self.hStackAlignment = hStackAlignment
        self.zStackAlignment = zStackAlignment
        self.list = list
        self.sectionHeaderInsets64 = sectionHeaderInsets64
        self.navigation = navigation
    }
}

public struct UIButtonMetricsV1: Sendable, Equatable {
    public let labelInsets64: UIInsets64V1
    public let minimumWidth64: UInt32
    public let minimumHeight64: UInt32
    public let radius64: UInt32
    public init(labelInsets64: UIInsets64V1, minimumWidth64: UInt32, minimumHeight64: UInt32, radius64: UInt32) {
        self.labelInsets64 = labelInsets64
        self.minimumWidth64 = minimumWidth64
        self.minimumHeight64 = minimumHeight64
        self.radius64 = radius64
    }
}

public struct UIFieldMetricsV1: Sendable, Equatable {
    public let insets64: UIInsets64V1
    public let minimumHeight64: UInt32
    public let border64: UInt32
    public init(insets64: UIInsets64V1, minimumHeight64: UInt32, border64: UInt32) {
        self.insets64 = insets64
        self.minimumHeight64 = minimumHeight64
        self.border64 = border64
    }
}

public struct UIToggleMetricsV1: Sendable, Equatable {
    public let trackWidth64: UInt32
    public let trackHeight64: UInt32
    public let thumb64: UInt32
    public let inset64: UInt32
    public let labelGap64: UInt32
    public let minimumRow64: UInt32
    public init(trackWidth64: UInt32, trackHeight64: UInt32, thumb64: UInt32, inset64: UInt32, labelGap64: UInt32, minimumRow64: UInt32) {
        self.trackWidth64 = trackWidth64
        self.trackHeight64 = trackHeight64
        self.thumb64 = thumb64
        self.inset64 = inset64
        self.labelGap64 = labelGap64
        self.minimumRow64 = minimumRow64
    }
}

public struct UIControlMetricsV1: Sendable, Equatable {
    public let button: UIButtonMetricsV1
    public let field: UIFieldMetricsV1
    public let toggle: UIToggleMetricsV1
    public let focusWidth64: UInt32
    public let focusRadius64: UInt32
    public let pressedOpacityPermille: UInt16
    public let selectionOpacityPermille: UInt16
    public init(button: UIButtonMetricsV1, field: UIFieldMetricsV1, toggle: UIToggleMetricsV1, focusWidth64: UInt32, focusRadius64: UInt32, pressedOpacityPermille: UInt16, selectionOpacityPermille: UInt16) {
        self.button = button
        self.field = field
        self.toggle = toggle
        self.focusWidth64 = focusWidth64
        self.focusRadius64 = focusRadius64
        self.pressedOpacityPermille = pressedOpacityPermille
        self.selectionOpacityPermille = selectionOpacityPermille
    }
}

public struct UIThemeV1: Sendable, Equatable {
    public let recipe: UIRecipeV1
    public let light: UIPaletteV1
    public let dark: UIPaletteV1
    public let typography: UITypographyV1
    public let layout: UILayoutMetricsV1
    public let controls: UIControlMetricsV1
    public init(recipe: UIRecipeV1, light: UIPaletteV1, dark: UIPaletteV1, typography: UITypographyV1, layout: UILayoutMetricsV1, controls: UIControlMetricsV1) {
        self.recipe = recipe
        self.light = light
        self.dark = dark
        self.typography = typography
        self.layout = layout
        self.controls = controls
    }
}

public struct UIAppearanceResourceV1: Sendable, Equatable {
    public let id: String
    public let kind: UIResourceKindV1
    public let path: String
    public let sha256: String
    public let bytes: UInt32
    public let provenance: String
    public let scale: UInt8
    public let locale: String
    public let direction: UIResourceDirectionV1
    public init(id: String, kind: UIResourceKindV1, path: String, sha256: String, bytes: UInt32, provenance: String, scale: UInt8, locale: String, direction: UIResourceDirectionV1) {
        self.id = id
        self.kind = kind
        self.path = path
        self.sha256 = sha256
        self.bytes = bytes
        self.provenance = provenance
        self.scale = scale
        self.locale = locale
        self.direction = direction
    }
}

public enum UIAppearanceModeV1: Sendable, Equatable {
    case shared(UIThemeV1)
    case platformSpecific(iOS: UIThemeV1, android: UIThemeV1, reason: String)
}
public struct UIAppearanceConfigurationV1: Sendable, Equatable {
    public static let format = "mixer.native-appearance.1"
    public let id: String
    public let mode: UIAppearanceModeV1
    public let resources: [UIAppearanceResourceV1]
    public init(id: String, mode: UIAppearanceModeV1, resources: [UIAppearanceResourceV1] = []) {
        self.id = id; self.mode = mode; self.resources = resources
    }
}
public struct UIAppearanceEnvironmentV1: Sendable, Equatable {
    public let scheme: UIColorSchemeV1
    public let direction: UILayoutDirectionV1
    public let textScale1024, density1024: UInt16
    public init(scheme: UIColorSchemeV1, direction: UILayoutDirectionV1,
                textScale1024: UInt16, density1024: UInt16) {
        self.scheme = scheme; self.direction = direction
        self.textScale1024 = textScale1024; self.density1024 = density1024
    }
}
public enum UIAppearanceErrorV1: Error, Sendable, Equatable {
    case byteLimit, invalidEncoding, syntax, duplicateKey, depthLimit, valueLimit
    case noncanonical, shape, number, resourceCatalog, fontCatalog, geometry
}
