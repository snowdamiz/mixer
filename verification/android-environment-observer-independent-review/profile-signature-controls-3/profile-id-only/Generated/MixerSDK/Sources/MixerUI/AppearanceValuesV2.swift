// Untrusted, immutable V2 data values. Codec validation supplies no installed
// resource, native rendering, signed presentation, or release authority.
import Foundation

public enum UIRecipeV2: String, Sendable, Equatable { case measuredShared2 }
public enum UIAppearanceModeV2: Sendable, Equatable {
    case shared(UIThemeV2)
    case platformSpecific(iOS: UIThemeV2, android: UIThemeV2, reason: String)
}
public enum UIProfilePreferencePolicyV2: String, Sendable, Equatable { case nearestBody64TiesUpRejectOutside }
public enum UIMissingVStackGapV2: String, Sendable, Equatable { case bodyThenCaptionPairOtherwiseDefault }
public enum UIRowPolicyV2: String, Sendable, Equatable { case maxProfileFloorSemanticContentPlusInsets }
public enum UISeparatorPolicyV2: String, Sendable, Equatable { case interiorRowsOnly }
public enum UICheckedEndV2: String, Sendable, Equatable { case logicalTrailing }
public enum UINavigationCollapseV2: String, Sendable, Equatable { case snapAtExpandedOverflow }
public enum UINavigationTitleWrapV2: String, Sendable, Equatable { case growExpandedEllipsizeCompactOneLine }

/// Data admission errors are distinct from later native/runtime failures.
public enum UIAppearanceErrorV2: Error, Sendable, Equatable {
    case byteLimit, invalidEncoding, syntax, duplicateKey, depthLimit, valueLimit, arrayLimit
    case noncanonical, shape, number, resourceCatalog, fontCatalog, unsupportedProfile, geometry
    case unsupportedNativeOperation, layout, nativeAttachment
}

public struct UIAppearanceConfigurationV2: Sendable, Equatable {
    public static let format = "mixer.native-appearance.2"
    public let id: String
    public let mode: UIAppearanceModeV2
    public let resources: [UIAppearanceResourceV1]
    public init(id: String, mode: UIAppearanceModeV2, resources: [UIAppearanceResourceV1] = []) {
        self.id = id
        self.mode = mode
        self.resources = resources
    }
}

public struct UIRoleMetricsV2: Sendable, Equatable {
    public let body: UISharedTextMetricsV1
    public let headline: UISharedTextMetricsV1
    public let title: UISharedTextMetricsV1
    public let caption: UISharedTextMetricsV1
    public let sectionHeader: UISharedTextMetricsV1
    public let navigationExpanded: UISharedTextMetricsV1
    public init(body: UISharedTextMetricsV1, headline: UISharedTextMetricsV1, title: UISharedTextMetricsV1, caption: UISharedTextMetricsV1, sectionHeader: UISharedTextMetricsV1, navigationExpanded: UISharedTextMetricsV1) {
        self.body = body
        self.headline = headline
        self.title = title
        self.caption = caption
        self.sectionHeader = sectionHeader
        self.navigationExpanded = navigationExpanded
    }
}

public struct UIProfilesV2: Sendable, Equatable {
    public let xs: UIRoleMetricsV2
    public let s: UIRoleMetricsV2
    public let m: UIRoleMetricsV2
    public let l: UIRoleMetricsV2
    public let xl: UIRoleMetricsV2
    public let xxl: UIRoleMetricsV2
    public let xxxl: UIRoleMetricsV2
    public let a1: UIRoleMetricsV2
    public let a2: UIRoleMetricsV2
    public let a3: UIRoleMetricsV2
    public let a4: UIRoleMetricsV2
    public let a5: UIRoleMetricsV2
    public init(xs: UIRoleMetricsV2, s: UIRoleMetricsV2, m: UIRoleMetricsV2, l: UIRoleMetricsV2, xl: UIRoleMetricsV2, xxl: UIRoleMetricsV2, xxxl: UIRoleMetricsV2, a1: UIRoleMetricsV2, a2: UIRoleMetricsV2, a3: UIRoleMetricsV2, a4: UIRoleMetricsV2, a5: UIRoleMetricsV2) {
        self.xs = xs
        self.s = s
        self.m = m
        self.l = l
        self.xl = xl
        self.xxl = xxl
        self.xxxl = xxxl
        self.a1 = a1
        self.a2 = a2
        self.a3 = a3
        self.a4 = a4
        self.a5 = a5
    }
}

public struct UIProfileFloorsV2: Sendable, Equatable {
    public let xs: UInt32
    public let s: UInt32
    public let m: UInt32
    public let l: UInt32
    public let xl: UInt32
    public let xxl: UInt32
    public let xxxl: UInt32
    public let a1: UInt32
    public let a2: UInt32
    public let a3: UInt32
    public let a4: UInt32
    public let a5: UInt32
    public init(xs: UInt32, s: UInt32, m: UInt32, l: UInt32, xl: UInt32, xxl: UInt32, xxxl: UInt32, a1: UInt32, a2: UInt32, a3: UInt32, a4: UInt32, a5: UInt32) {
        self.xs = xs
        self.s = s
        self.m = m
        self.l = l
        self.xl = xl
        self.xxl = xxl
        self.xxxl = xxxl
        self.a1 = a1
        self.a2 = a2
        self.a3 = a3
        self.a4 = a4
        self.a5 = a5
    }
}

public struct UITypographyV2: Sendable, Equatable {
    public let font: UIFontSourceV1
    public let profiles: UIProfilesV2
    public let defaultProfile: UISharedTextProfileV1
    public let preferencePolicy: UIProfilePreferencePolicyV2
    public init(font: UIFontSourceV1, profiles: UIProfilesV2, defaultProfile: UISharedTextProfileV1, preferencePolicy: UIProfilePreferencePolicyV2) {
        self.font = font
        self.profiles = profiles
        self.defaultProfile = defaultProfile
        self.preferencePolicy = preferencePolicy
    }
}

public struct UIRolePaintsV2: Sendable, Equatable {
    public let body: UIRGBA8V1
    public let headline: UIRGBA8V1
    public let title: UIRGBA8V1
    public let caption: UIRGBA8V1
    public let sectionHeader: UIRGBA8V1
    public let navigationExpanded: UIRGBA8V1
    public init(body: UIRGBA8V1, headline: UIRGBA8V1, title: UIRGBA8V1, caption: UIRGBA8V1, sectionHeader: UIRGBA8V1, navigationExpanded: UIRGBA8V1) {
        self.body = body
        self.headline = headline
        self.title = title
        self.caption = caption
        self.sectionHeader = sectionHeader
        self.navigationExpanded = navigationExpanded
    }
}

public struct UIOutlineV2: Sendable, Equatable {
    public let color: UIRGBA8V1
    public let width64: UInt32
    public let radius64: UInt32
    public init(color: UIRGBA8V1, width64: UInt32, radius64: UInt32) {
        self.color = color
        self.width64 = width64
        self.radius64 = radius64
    }
}

public struct UIButtonPaintV2: Sendable, Equatable {
    public let label: UIRGBA8V1
    public let background: UIRGBA8V1
    public init(label: UIRGBA8V1, background: UIRGBA8V1) {
        self.label = label
        self.background = background
    }
}

public struct UIButtonStatesV2: Sendable, Equatable {
    public let enabled: UIButtonPaintV2
    public let pressed: UIButtonPaintV2
    public let disabled: UIButtonPaintV2
    public let focus: UIOutlineV2
    public init(enabled: UIButtonPaintV2, pressed: UIButtonPaintV2, disabled: UIButtonPaintV2, focus: UIOutlineV2) {
        self.enabled = enabled
        self.pressed = pressed
        self.disabled = disabled
        self.focus = focus
    }
}

public struct UIButtonRolesV2: Sendable, Equatable {
    public let normal: UIButtonStatesV2
    public let destructive: UIButtonStatesV2
    public let cancel: UIButtonStatesV2
    public init(normal: UIButtonStatesV2, destructive: UIButtonStatesV2, cancel: UIButtonStatesV2) {
        self.normal = normal
        self.destructive = destructive
        self.cancel = cancel
    }
}

public struct UIFieldPaintV2: Sendable, Equatable {
    public let text: UIRGBA8V1
    public let placeholder: UIRGBA8V1
    public let background: UIRGBA8V1
    public let caret: UIRGBA8V1
    public let selection: UIRGBA8V1
    public let outline: UIOutlineV2
    public init(text: UIRGBA8V1, placeholder: UIRGBA8V1, background: UIRGBA8V1, caret: UIRGBA8V1, selection: UIRGBA8V1, outline: UIOutlineV2) {
        self.text = text
        self.placeholder = placeholder
        self.background = background
        self.caret = caret
        self.selection = selection
        self.outline = outline
    }
}

public struct UIFieldStatesV2: Sendable, Equatable {
    public let enabled: UIFieldPaintV2
    public let focused: UIFieldPaintV2
    public let disabled: UIFieldPaintV2
    public init(enabled: UIFieldPaintV2, focused: UIFieldPaintV2, disabled: UIFieldPaintV2) {
        self.enabled = enabled
        self.focused = focused
        self.disabled = disabled
    }
}

public struct UITogglePaintV2: Sendable, Equatable {
    public let label: UIRGBA8V1
    public let track: UIRGBA8V1
    public let thumb: UIRGBA8V1
    public let overlay: UIRGBA8V1
    public init(label: UIRGBA8V1, track: UIRGBA8V1, thumb: UIRGBA8V1, overlay: UIRGBA8V1) {
        self.label = label
        self.track = track
        self.thumb = thumb
        self.overlay = overlay
    }
}

public struct UIToggleStatesV2: Sendable, Equatable {
    public let enabled: UITogglePaintV2
    public let pressed: UITogglePaintV2
    public let disabled: UITogglePaintV2
    public let focus: UIOutlineV2
    public init(enabled: UITogglePaintV2, pressed: UITogglePaintV2, disabled: UITogglePaintV2, focus: UIOutlineV2) {
        self.enabled = enabled
        self.pressed = pressed
        self.disabled = disabled
        self.focus = focus
    }
}

public struct UIToggleValuesV2: Sendable, Equatable {
    public let on: UIToggleStatesV2
    public let off: UIToggleStatesV2
    public init(on: UIToggleStatesV2, off: UIToggleStatesV2) {
        self.on = on
        self.off = off
    }
}

public struct UIPaintsV2: Sendable, Equatable {
    public let canvas: UIRGBA8V1
    public let surface: UIRGBA8V1
    public let separator: UIRGBA8V1
    public let text: UIRolePaintsV2
    public let button: UIButtonRolesV2
    public let field: UIFieldStatesV2
    public let toggle: UIToggleValuesV2
    public init(canvas: UIRGBA8V1, surface: UIRGBA8V1, separator: UIRGBA8V1, text: UIRolePaintsV2, button: UIButtonRolesV2, field: UIFieldStatesV2, toggle: UIToggleValuesV2) {
        self.canvas = canvas
        self.surface = surface
        self.separator = separator
        self.text = text
        self.button = button
        self.field = field
        self.toggle = toggle
    }
}

public struct UIStackMetricsV2: Sendable, Equatable {
    public let defaultGap64: UInt32
    public let bodyCaptionGap64: UInt32
    public let missingVStackGap: UIMissingVStackGapV2
    public let vStackAlignment: UIHorizontalAlignmentV1
    public let hStackAlignment: UIVerticalAlignmentV1
    public let zStackAlignment: UIOverlayAlignmentV1
    public init(defaultGap64: UInt32, bodyCaptionGap64: UInt32, missingVStackGap: UIMissingVStackGapV2, vStackAlignment: UIHorizontalAlignmentV1, hStackAlignment: UIVerticalAlignmentV1, zStackAlignment: UIOverlayAlignmentV1) {
        self.defaultGap64 = defaultGap64
        self.bodyCaptionGap64 = bodyCaptionGap64
        self.missingVStackGap = missingVStackGap
        self.vStackAlignment = vStackAlignment
        self.hStackAlignment = hStackAlignment
        self.zStackAlignment = zStackAlignment
    }
}

public struct UIGroupedListMetricsV2: Sendable, Equatable {
    public let outerHorizontal64: UInt32
    public let contentInsets64: UIInsets64V1
    public let topPadding64: UInt32
    public let bottomPadding64: UInt32
    public let headerToGroup64: UInt32
    public let groupToNextHeader64: UInt32
    public let groupWithoutHeaderGap64: UInt32
    public let profileFloors64: UIProfileFloorsV2
    public let separatorInset64: UInt32
    public let separatorThickness64: UInt32
    public let outline: UINativeShapeV2
    public let radius64: UInt32
    public let rowPolicy: UIRowPolicyV2
    public let separatorPolicy: UISeparatorPolicyV2
    public init(outerHorizontal64: UInt32, contentInsets64: UIInsets64V1, topPadding64: UInt32, bottomPadding64: UInt32, headerToGroup64: UInt32, groupToNextHeader64: UInt32, groupWithoutHeaderGap64: UInt32, profileFloors64: UIProfileFloorsV2, separatorInset64: UInt32, separatorThickness64: UInt32, outline: UINativeShapeV2, radius64: UInt32, rowPolicy: UIRowPolicyV2, separatorPolicy: UISeparatorPolicyV2) {
        self.outerHorizontal64 = outerHorizontal64
        self.contentInsets64 = contentInsets64
        self.topPadding64 = topPadding64
        self.bottomPadding64 = bottomPadding64
        self.headerToGroup64 = headerToGroup64
        self.groupToNextHeader64 = groupToNextHeader64
        self.groupWithoutHeaderGap64 = groupWithoutHeaderGap64
        self.profileFloors64 = profileFloors64
        self.separatorInset64 = separatorInset64
        self.separatorThickness64 = separatorThickness64
        self.outline = outline
        self.radius64 = radius64
        self.rowPolicy = rowPolicy
        self.separatorPolicy = separatorPolicy
    }
}

public struct UIButtonMetricsV2: Sendable, Equatable {
    public let labelInsets64: UIInsets64V1
    public let minimumHitWidth64: UInt32
    public let minimumHitHeight64: UInt32
    public let overlayRadius64: UInt32
    public init(labelInsets64: UIInsets64V1, minimumHitWidth64: UInt32, minimumHitHeight64: UInt32, overlayRadius64: UInt32) {
        self.labelInsets64 = labelInsets64
        self.minimumHitWidth64 = minimumHitWidth64
        self.minimumHitHeight64 = minimumHitHeight64
        self.overlayRadius64 = overlayRadius64
    }
}

public struct UIFieldMetricsV2: Sendable, Equatable {
    public let insets64: UIInsets64V1
    public let minimumContentHeight64: UInt32
    public let minimumHitHeight64: UInt32
    public init(insets64: UIInsets64V1, minimumContentHeight64: UInt32, minimumHitHeight64: UInt32) {
        self.insets64 = insets64
        self.minimumContentHeight64 = minimumContentHeight64
        self.minimumHitHeight64 = minimumHitHeight64
    }
}

public struct UIToggleMetricsV2: Sendable, Equatable {
    public let track: UINativeShapeV2
    public let thumb: UINativeShapeV2
    public let trackWidth64: UInt32
    public let trackHeight64: UInt32
    public let thumbWidth64: UInt32
    public let thumbHeight64: UInt32
    public let trackAuthoringRadius64: UInt32
    public let thumbAuthoringRadius64: UInt32
    public let thumbInset64: UInt32
    public let labelGap64: UInt32
    public let minimumHitWidth64: UInt32
    public let minimumHitHeight64: UInt32
    public let checkedEnd: UICheckedEndV2
    public init(track: UINativeShapeV2, thumb: UINativeShapeV2, trackWidth64: UInt32, trackHeight64: UInt32, thumbWidth64: UInt32, thumbHeight64: UInt32, trackAuthoringRadius64: UInt32, thumbAuthoringRadius64: UInt32, thumbInset64: UInt32, labelGap64: UInt32, minimumHitWidth64: UInt32, minimumHitHeight64: UInt32, checkedEnd: UICheckedEndV2) {
        self.track = track
        self.thumb = thumb
        self.trackWidth64 = trackWidth64
        self.trackHeight64 = trackHeight64
        self.thumbWidth64 = thumbWidth64
        self.thumbHeight64 = thumbHeight64
        self.trackAuthoringRadius64 = trackAuthoringRadius64
        self.thumbAuthoringRadius64 = thumbAuthoringRadius64
        self.thumbInset64 = thumbInset64
        self.labelGap64 = labelGap64
        self.minimumHitWidth64 = minimumHitWidth64
        self.minimumHitHeight64 = minimumHitHeight64
        self.checkedEnd = checkedEnd
    }
}

public struct UINavigationMetricsV2: Sendable, Equatable {
    public let expandedRole: UISharedTextRoleV1
    public let compactRole: UISharedTextRoleV1
    public let expandedAlignment: UIHorizontalAlignmentV1
    public let compactAlignment: UIHorizontalAlignmentV1
    public let expandedInsets64: UIInsets64V1
    public let compactInsets64: UIInsets64V1
    public let minimumExpandedBar64: UInt32
    public let minimumCompactBar64: UInt32
    public let collapse: UINavigationCollapseV2
    public let titleWrap: UINavigationTitleWrapV2
    public init(expandedRole: UISharedTextRoleV1, compactRole: UISharedTextRoleV1, expandedAlignment: UIHorizontalAlignmentV1, compactAlignment: UIHorizontalAlignmentV1, expandedInsets64: UIInsets64V1, compactInsets64: UIInsets64V1, minimumExpandedBar64: UInt32, minimumCompactBar64: UInt32, collapse: UINavigationCollapseV2, titleWrap: UINavigationTitleWrapV2) {
        self.expandedRole = expandedRole
        self.compactRole = compactRole
        self.expandedAlignment = expandedAlignment
        self.compactAlignment = compactAlignment
        self.expandedInsets64 = expandedInsets64
        self.compactInsets64 = compactInsets64
        self.minimumExpandedBar64 = minimumExpandedBar64
        self.minimumCompactBar64 = minimumCompactBar64
        self.collapse = collapse
        self.titleWrap = titleWrap
    }
}

public struct UIThemeV2: Sendable, Equatable {
    public let recipe: UIRecipeV2
    public let typography: UITypographyV2
    public let light: UIPaintsV2
    public let dark: UIPaintsV2
    public let stacks: UIStackMetricsV2
    public let groupedList: UIGroupedListMetricsV2
    public let button: UIButtonMetricsV2
    public let field: UIFieldMetricsV2
    public let toggle: UIToggleMetricsV2
    public let navigation: UINavigationMetricsV2
    public init(recipe: UIRecipeV2, typography: UITypographyV2, light: UIPaintsV2, dark: UIPaintsV2, stacks: UIStackMetricsV2, groupedList: UIGroupedListMetricsV2, button: UIButtonMetricsV2, field: UIFieldMetricsV2, toggle: UIToggleMetricsV2, navigation: UINavigationMetricsV2) {
        self.recipe = recipe
        self.typography = typography
        self.light = light
        self.dark = dark
        self.stacks = stacks
        self.groupedList = groupedList
        self.button = button
        self.field = field
        self.toggle = toggle
        self.navigation = navigation
    }
}
