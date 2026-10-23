// DESIGN DECLARATIONS ONLY. No codec, resolver, installer, native implementation,
// runtime registration, signed authority, or product module is supplied here.
import Foundation
import MixerUI

public enum UIRecipeV2: String, Sendable { case measuredShared2 }
public enum UINativeShapeV2: String, Sendable {
    case fullGroupContinuousCubic2, track63x28Continuous2, thumb37x24Continuous2
}
public enum UIAppearanceModeV2: Sendable {
    case shared(UIThemeV2)
    case platformSpecific(iOS: UIThemeV2, android: UIThemeV2, reason: String)
}
public struct UIAppearanceConfigurationV2: Sendable {
    public let id: String
    public let mode: UIAppearanceModeV2
    public let resources: [UIAppearanceResourceV1]
}
// Six named fields, never an unchecked role dictionary; schema closes all rows.
public struct UIRoleMetricsV2: Sendable {
    public let body, headline, title, caption, sectionHeader, navigationExpanded: UISharedTextMetricsV1
}
public struct UIProfilesV2: Sendable {
    public let xs, s, m, l, xl, xxl, xxxl, a1, a2, a3, a4, a5: UIRoleMetricsV2
}
public struct UIProfileFloorsV2: Sendable {
    public let xs, s, m, l, xl, xxl, xxxl, a1, a2, a3, a4, a5: UInt32
}
public enum UIProfilePreferencePolicyV2: String, Sendable { case nearestBody64TiesUpRejectOutside }
public struct UITypographyV2: Sendable {
    public let font: UIFontSourceV1
    public let profiles: UIProfilesV2
    public let defaultProfile: UISharedTextProfileV1
    public let preferencePolicy: UIProfilePreferencePolicyV2
}
public struct UIRolePaintsV2: Sendable {
    public let body, headline, title, caption, sectionHeader, navigationExpanded: UIRGBA8V1
}
public struct UIOutlineV2: Sendable {
    public let color: UIRGBA8V1
    public let width64, radius64: UInt32
}
public struct UIButtonPaintV2: Sendable { public let label, background: UIRGBA8V1 }
public struct UIButtonStatesV2: Sendable {
    public let enabled, pressed, disabled: UIButtonPaintV2
    public let focus: UIOutlineV2
}
public struct UIButtonRolesV2: Sendable { public let normal, destructive, cancel: UIButtonStatesV2 }
public struct UIFieldPaintV2: Sendable {
    public let text, placeholder, background, caret, selection: UIRGBA8V1
    public let outline: UIOutlineV2
}
public struct UIFieldStatesV2: Sendable { public let enabled, focused, disabled: UIFieldPaintV2 }
public struct UITogglePaintV2: Sendable { public let label, track, thumb, overlay: UIRGBA8V1 }
public struct UIToggleStatesV2: Sendable {
    public let enabled, pressed, disabled: UITogglePaintV2
    public let focus: UIOutlineV2
}
public struct UIToggleValuesV2: Sendable { public let on, off: UIToggleStatesV2 }
public struct UIPaintsV2: Sendable {
    public let canvas, surface, separator: UIRGBA8V1
    public let text: UIRolePaintsV2
    public let button: UIButtonRolesV2
    public let field: UIFieldStatesV2
    public let toggle: UIToggleValuesV2
}
public enum UIMissingVStackGapV2: String, Sendable { case bodyThenCaptionPairOtherwiseDefault }
public struct UIStackMetricsV2: Sendable {
    public let defaultGap64, bodyCaptionGap64: UInt32
    public let missingVStackGap: UIMissingVStackGapV2
    public let vStackAlignment: UIHorizontalAlignmentV1
    public let hStackAlignment: UIVerticalAlignmentV1
    public let zStackAlignment: UIOverlayAlignmentV1
}
public enum UIRowPolicyV2: String, Sendable { case maxProfileFloorSemanticContentPlusInsets }
public enum UISeparatorPolicyV2: String, Sendable { case interiorRowsOnly }
public struct UIGroupedListMetricsV2: Sendable {
    public let outerHorizontal64: UInt32
    public let contentInsets64: UIInsets64V1
    public let topPadding64, bottomPadding64, headerToGroup64: UInt32
    public let groupToNextHeader64, groupWithoutHeaderGap64: UInt32
    public let profileFloors64: UIProfileFloorsV2
    public let separatorInset64, separatorThickness64: UInt32
    public let outline: UINativeShapeV2
    public let radius64: UInt32
    public let rowPolicy: UIRowPolicyV2
    public let separatorPolicy: UISeparatorPolicyV2
}
public struct UIButtonMetricsV2: Sendable {
    public let labelInsets64: UIInsets64V1
    public let minimumHitWidth64, minimumHitHeight64, overlayRadius64: UInt32
}
public struct UIFieldMetricsV2: Sendable {
    public let insets64: UIInsets64V1
    public let minimumContentHeight64, minimumHitHeight64: UInt32
}
public enum UICheckedEndV2: String, Sendable { case logicalTrailing }
public struct UIToggleMetricsV2: Sendable {
    public let track, thumb: UINativeShapeV2
    public let trackWidth64, trackHeight64, thumbWidth64, thumbHeight64: UInt32
    public let trackAuthoringRadius64, thumbAuthoringRadius64, thumbInset64: UInt32
    public let labelGap64, minimumHitWidth64, minimumHitHeight64: UInt32
    public let checkedEnd: UICheckedEndV2
}
public enum UINavigationCollapseV2: String, Sendable { case snapAtExpandedOverflow }
public enum UINavigationTitleWrapV2: String, Sendable { case growExpandedEllipsizeCompactOneLine }
public struct UINavigationMetricsV2: Sendable {
    public let expandedRole, compactRole: UISharedTextRoleV1
    public let expandedAlignment, compactAlignment: UIHorizontalAlignmentV1
    public let expandedInsets64, compactInsets64: UIInsets64V1
    public let minimumExpandedBar64, minimumCompactBar64: UInt32
    public let collapse: UINavigationCollapseV2
    public let titleWrap: UINavigationTitleWrapV2
}
public struct UIThemeV2: Sendable {
    public let recipe: UIRecipeV2
    public let typography: UITypographyV2
    public let light, dark: UIPaintsV2
    public let stacks: UIStackMetricsV2
    public let groupedList: UIGroupedListMetricsV2
    public let button: UIButtonMetricsV2
    public let field: UIFieldMetricsV2
    public let toggle: UIToggleMetricsV2
    public let navigation: UINavigationMetricsV2
}

// Internal native-consumer seam. These declarations deliberately supply no public
// initializer or support-provider protocol: a caller cannot mint installed capture
// or advertise native support by conformance. Raw configuration remains untrusted.
struct UICapturedInstalledAppearanceV2: Sendable {
    let configuration: UIAppearanceConfigurationV2
    let canonicalDescriptor: Data
    let descriptorSHA256: String
    let resources: [UICapturedResourceV2]
}
struct UICapturedResourceV2: Sendable { let entry: UIAppearanceResourceV1; let immutableBytes: Data }
enum UINativePlatformV2: String, Sendable { case iOS, android }
enum UINavigationPresentationV2: String, Sendable { case expanded, compact }
struct UIAppearanceEnvironmentV2: Sendable {
    let scheme: UIColorSchemeV1
    let direction: UILayoutDirectionV1
    let profile: UISharedTextProfileV1
    let density1024: UInt16
    let viewportWidth64, viewportHeight64: UInt32
    let safeArea64: UIInsets64V1
    let localeID: String
    let boldTextRequested, increasedContrastRequested, reduceMotionRequested: Bool
    let generation: UInt64
}
struct UIAppearanceBuildSupportV2: Sendable {
    let platform: UINativePlatformV2
    let implementedKinds: Set<NodeKind>
    let supportsAllTextOperations, supportsBaselineAlignment: Bool
    let supportsClosedShapes, supportsNativeControls, supportsCapturedFontPolicy: Bool
    let supportsRequestedAccessibilityVisualContext: Bool
}
struct UIResolvedTextV2: Sendable {
    let role: UISharedTextRoleV1
    let metrics: UISharedTextMetricsV1
    let selectable: Bool
    let maximumLines: UInt32?
    // No first-line height, repeat advance, fontScale, or universal clip box.
}
struct UINodeKeyV2: Sendable { let identity: UINodeIdentity; let kind: NodeKind }
struct UIResolvedRowPlacementV2: Sendable {
    let rowNode: UINodeKeyV2
    let groupIndex, rowIndex: UInt32
    let rowCount: UInt32
    let profileFloor64: UInt32
    let contentInsets64: UIInsets64V1
    let drawsSeparator: Bool
}
struct UIResolvedGroupV2: Sendable {
    let sectionNode: UINodeKeyV2? // nil for a contiguous direct-row run
    let rowIDs: [String]
    let header: UIResolvedTextV2?
    let gapBefore64, gapAfterHeader64: UInt32
    let outline: UINativeShapeV2
    let requestedRadius64: UInt32
}
enum UIResolvedRecipeV2: Sendable {
    case text(UIResolvedTextV2)
    case button(role: UIResolvedButtonRoleV1, text: UIResolvedTextV2, metrics: UIButtonMetricsV2)
    case textField(text: UIResolvedTextV2, metrics: UIFieldMetricsV2)
    case toggle(text: UIResolvedTextV2, checked: Bool, metrics: UIToggleMetricsV2)
    case vStack(gaps64: [UInt32], alignment: UIHorizontalAlignmentV1)
    case hStack(gaps64: [UInt32], alignment: UIVerticalAlignmentV1)
    case zStack(alignment: UIOverlayAlignmentV1)
    case list(metrics: UIGroupedListMetricsV2, groups: [UIResolvedGroupV2], rows: [UIResolvedRowPlacementV2])
    case section(header: UIResolvedTextV2?)
    case navigation(expanded: UIResolvedTextV2?, compact: UIResolvedTextV2?, metrics: UINavigationMetricsV2)
}
struct UIResolvedNodeV2: Sendable {
    let key: UINodeKeyV2
    let childIDs: [String] // Original order under RTL.
    let disabled: Bool
    let recipe: UIResolvedRecipeV2
}
struct UIPreparedAppearanceV2: Sendable {
    let snapshot: UIRenderSnapshot
    let descriptorSHA256: String
    let configurationID: String
    let environment: UIAppearanceEnvironmentV2
    let platform: UINativePlatformV2
    let platformSpecificReason: String?
    let nodes: [UIResolvedNodeV2] // Same preorder; exactly one record per snapshot node.
    let paints: UIPaintsV2
    let captured: UICapturedInstalledAppearanceV2
}
// Proposed internal function, implementation intentionally absent:
// prepareAppearanceV2(snapshot:captured:environment:buildSupport:) throws
//   -> UIPreparedAppearanceV2
// prepare revalidates snapshot + identities, descriptor, resources + support before
// returning. Native text shaping/layout and transactional attachment remain later
// steps and can still fail. This value grants no display, event or health proof.
