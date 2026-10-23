import Foundation
import MixerUI

func checkValue<T: Sendable & Equatable>(_ a: T, _ b: T) { precondition(a == b) }
let original = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
guard case let .shared(theme) = original.mode else { fatalError("default mode") }
checkValue(UIRoleMetricsV2(body: theme.typography.profiles.l.body, headline: theme.typography.profiles.l.headline, title: theme.typography.profiles.l.title, caption: theme.typography.profiles.l.caption, sectionHeader: theme.typography.profiles.l.sectionHeader, navigationExpanded: theme.typography.profiles.l.navigationExpanded), theme.typography.profiles.l)
checkValue(UIProfilesV2(xs: theme.typography.profiles.xs, s: theme.typography.profiles.s, m: theme.typography.profiles.m, l: theme.typography.profiles.l, xl: theme.typography.profiles.xl, xxl: theme.typography.profiles.xxl, xxxl: theme.typography.profiles.xxxl, a1: theme.typography.profiles.a1, a2: theme.typography.profiles.a2, a3: theme.typography.profiles.a3, a4: theme.typography.profiles.a4, a5: theme.typography.profiles.a5), theme.typography.profiles)
checkValue(UIProfileFloorsV2(xs: theme.groupedList.profileFloors64.xs, s: theme.groupedList.profileFloors64.s, m: theme.groupedList.profileFloors64.m, l: theme.groupedList.profileFloors64.l, xl: theme.groupedList.profileFloors64.xl, xxl: theme.groupedList.profileFloors64.xxl, xxxl: theme.groupedList.profileFloors64.xxxl, a1: theme.groupedList.profileFloors64.a1, a2: theme.groupedList.profileFloors64.a2, a3: theme.groupedList.profileFloors64.a3, a4: theme.groupedList.profileFloors64.a4, a5: theme.groupedList.profileFloors64.a5), theme.groupedList.profileFloors64)
checkValue(UITypographyV2(font: theme.typography.font, profiles: theme.typography.profiles, defaultProfile: theme.typography.defaultProfile, preferencePolicy: theme.typography.preferencePolicy), theme.typography)
checkValue(UIRolePaintsV2(body: theme.light.text.body, headline: theme.light.text.headline, title: theme.light.text.title, caption: theme.light.text.caption, sectionHeader: theme.light.text.sectionHeader, navigationExpanded: theme.light.text.navigationExpanded), theme.light.text)
checkValue(UIOutlineV2(color: theme.light.button.normal.focus.color, width64: theme.light.button.normal.focus.width64, radius64: theme.light.button.normal.focus.radius64), theme.light.button.normal.focus)
checkValue(UIButtonPaintV2(label: theme.light.button.normal.enabled.label, background: theme.light.button.normal.enabled.background), theme.light.button.normal.enabled)
checkValue(UIButtonStatesV2(enabled: theme.light.button.normal.enabled, pressed: theme.light.button.normal.pressed, disabled: theme.light.button.normal.disabled, focus: theme.light.button.normal.focus), theme.light.button.normal)
checkValue(UIButtonRolesV2(normal: theme.light.button.normal, destructive: theme.light.button.destructive, cancel: theme.light.button.cancel), theme.light.button)
checkValue(UIFieldPaintV2(text: theme.light.field.focused.text, placeholder: theme.light.field.focused.placeholder, background: theme.light.field.focused.background, caret: theme.light.field.focused.caret, selection: theme.light.field.focused.selection, outline: theme.light.field.focused.outline), theme.light.field.focused)
checkValue(UIFieldStatesV2(enabled: theme.light.field.enabled, focused: theme.light.field.focused, disabled: theme.light.field.disabled), theme.light.field)
checkValue(UITogglePaintV2(label: theme.light.toggle.on.enabled.label, track: theme.light.toggle.on.enabled.track, thumb: theme.light.toggle.on.enabled.thumb, overlay: theme.light.toggle.on.enabled.overlay), theme.light.toggle.on.enabled)
checkValue(UIToggleStatesV2(enabled: theme.light.toggle.on.enabled, pressed: theme.light.toggle.on.pressed, disabled: theme.light.toggle.on.disabled, focus: theme.light.toggle.on.focus), theme.light.toggle.on)
checkValue(UIToggleValuesV2(on: theme.light.toggle.on, off: theme.light.toggle.off), theme.light.toggle)
checkValue(UIPaintsV2(canvas: theme.light.canvas, surface: theme.light.surface, separator: theme.light.separator, text: theme.light.text, button: theme.light.button, field: theme.light.field, toggle: theme.light.toggle), theme.light)
checkValue(UIStackMetricsV2(defaultGap64: theme.stacks.defaultGap64, bodyCaptionGap64: theme.stacks.bodyCaptionGap64, missingVStackGap: theme.stacks.missingVStackGap, vStackAlignment: theme.stacks.vStackAlignment, hStackAlignment: theme.stacks.hStackAlignment, zStackAlignment: theme.stacks.zStackAlignment), theme.stacks)
checkValue(UIGroupedListMetricsV2(outerHorizontal64: theme.groupedList.outerHorizontal64, contentInsets64: theme.groupedList.contentInsets64, topPadding64: theme.groupedList.topPadding64, bottomPadding64: theme.groupedList.bottomPadding64, headerToGroup64: theme.groupedList.headerToGroup64, groupToNextHeader64: theme.groupedList.groupToNextHeader64, groupWithoutHeaderGap64: theme.groupedList.groupWithoutHeaderGap64, profileFloors64: theme.groupedList.profileFloors64, separatorInset64: theme.groupedList.separatorInset64, separatorThickness64: theme.groupedList.separatorThickness64, outline: theme.groupedList.outline, radius64: theme.groupedList.radius64, rowPolicy: theme.groupedList.rowPolicy, separatorPolicy: theme.groupedList.separatorPolicy), theme.groupedList)
checkValue(UIButtonMetricsV2(labelInsets64: theme.button.labelInsets64, minimumHitWidth64: theme.button.minimumHitWidth64, minimumHitHeight64: theme.button.minimumHitHeight64, overlayRadius64: theme.button.overlayRadius64), theme.button)
checkValue(UIFieldMetricsV2(insets64: theme.field.insets64, minimumContentHeight64: theme.field.minimumContentHeight64, minimumHitHeight64: theme.field.minimumHitHeight64), theme.field)
checkValue(UIToggleMetricsV2(track: theme.toggle.track, thumb: theme.toggle.thumb, trackWidth64: theme.toggle.trackWidth64, trackHeight64: theme.toggle.trackHeight64, thumbWidth64: theme.toggle.thumbWidth64, thumbHeight64: theme.toggle.thumbHeight64, trackAuthoringRadius64: theme.toggle.trackAuthoringRadius64, thumbAuthoringRadius64: theme.toggle.thumbAuthoringRadius64, thumbInset64: theme.toggle.thumbInset64, labelGap64: theme.toggle.labelGap64, minimumHitWidth64: theme.toggle.minimumHitWidth64, minimumHitHeight64: theme.toggle.minimumHitHeight64, checkedEnd: theme.toggle.checkedEnd), theme.toggle)
checkValue(UINavigationMetricsV2(expandedRole: theme.navigation.expandedRole, compactRole: theme.navigation.compactRole, expandedAlignment: theme.navigation.expandedAlignment, compactAlignment: theme.navigation.compactAlignment, expandedInsets64: theme.navigation.expandedInsets64, compactInsets64: theme.navigation.compactInsets64, minimumExpandedBar64: theme.navigation.minimumExpandedBar64, minimumCompactBar64: theme.navigation.minimumCompactBar64, collapse: theme.navigation.collapse, titleWrap: theme.navigation.titleWrap), theme.navigation)
checkValue(UIThemeV2(recipe: theme.recipe, typography: theme.typography, light: theme.light, dark: theme.dark, stacks: theme.stacks, groupedList: theme.groupedList, button: theme.button, field: theme.field, toggle: theme.toggle, navigation: theme.navigation), theme)
let copy = UIAppearanceConfigurationV2(id: original.id, mode: .shared(theme), resources: [])
checkValue(copy, original)
let roles = UIRoleMetricsV2(body: UISharedTextProfileV1.l.metrics(for: .body),
    headline: UISharedTextProfileV1.l.metrics(for: .headline), title: UISharedTextProfileV1.l.metrics(for: .title),
    caption: UISharedTextProfileV1.l.metrics(for: .caption), sectionHeader: UISharedTextProfileV1.l.metrics(for: .sectionHeader),
    navigationExpanded: UISharedTextProfileV1.l.metrics(for: .navigationExpanded))
checkValue(roles, theme.typography.profiles.l)
let platform = UIAppearanceConfigurationV2(id: "public.platform", mode: .platformSpecific(iOS: theme,
    android: theme, reason: "Explicit \"choice\" \\ pair"))
try UIAppearanceDescriptorCodecV2.validate(platform)
checkValue(try UIAppearanceDescriptorCodecV2.decode(UIAppearanceDescriptorCodecV2.canonicalData(platform)), platform)
let resources = [400,600,700].enumerated().map { index, weight in
    UIAppearanceResourceV1(id: "font\(weight)", kind: .fontSFNT, path: "font/f\(index).ttf",
        sha256: String(repeating: "a", count: 64), bytes: 1, provenance: "Public caller synthetic metadata",
        scale: 1, locale: "und", direction: .neutral)
}
let faces = [UIFontWeightV1.w400,.w600,.w700].map { weight in
    UIFontFaceV1(resourceID: "font\(weight.rawValue)", postScriptName: "Owned\(weight.rawValue)", weight: weight, style: .normal)
}
let typography = UITypographyV2(font: .bundled(faces: faces, fallback: .none), profiles: theme.typography.profiles,
    defaultProfile: .a5, preferencePolicy: .nearestBody64TiesUpRejectOutside)
let custom = UIThemeV2(recipe: .measuredShared2, typography: typography, light: theme.light, dark: theme.dark,
    stacks: theme.stacks, groupedList: theme.groupedList, button: theme.button, field: theme.field,
    toggle: theme.toggle, navigation: theme.navigation)
let bundled = UIAppearanceConfigurationV2(id: "public.font", mode: .shared(custom), resources: resources)
try UIAppearanceDescriptorCodecV2.validate(bundled)
checkValue(try UIAppearanceDescriptorCodecV2.decode(UIAppearanceDescriptorCodecV2.canonicalData(bundled)), bundled)
let bytes = try UIAppearanceDescriptorCodecV2.canonicalData(original)
precondition(bytes.count == 9587)
print("PASS public V2 initializers/value equality/shared/platformSpecific/synthetic font reference roundtrips; default9587bytes")
