import MixerUI

// This consumer intentionally imports public API without @testable. It is
// typechecked against each separately compiled host/iOS/Android module.
func consumeAppearanceData(_ snapshot: UIRenderSnapshot, _ configuration: UIAppearanceConfigurationV1,
                           _ environment: UIAppearanceEnvironmentV1,
                           _ platform: UIAppearancePlatformV1) throws -> UInt64 {
    let plan: UIResolvedAppearancePlanV1 = try UIAppearanceResolverV1.prepare(snapshot: snapshot,
        configuration: configuration, environment: environment, platform: platform)
    let _: String = plan.configurationID
    let _: UIRecipeV1 = plan.recipe
    let _: UIAppearanceEnvironmentV1 = plan.environment
    let _: UIAppearancePlatformV1 = plan.platform
    let _: String? = plan.platformSpecificReason
    let _: UIFontSourceV1 = plan.font
    let _: [UIAppearanceResourceV1] = plan.resources
    for node in plan.nodes {
        let _: UINodeIdentity = node.identity
        let _: NodeKind = node.kind
        let _: Bool = node.disabled
        let _: [String] = node.childIDs
        let _: UIResolvedAppearanceNodeV1? = plan.node(for: node.identity.id)
        switch node.recipe {
        case let .text(text): _ = text.size64; _ = text.weight; _ = text.minimumLineBox64; _ = text.role
            _ = text.selectable; _ = text.maximumLines
        case let .button(role, text, metrics, floor): _ = role; _ = text; _ = metrics; _ = floor
        case let .textField(text, metrics, floor): _ = text; _ = metrics; _ = floor
        case let .toggle(text, checked, metrics, floor): _ = text; _ = checked; _ = metrics; _ = floor
        case let .vStack(gap, alignment): _ = gap; _ = alignment
        case let .hStack(gap, alignment): _ = gap; _ = alignment
        case let .zStack(alignment): _ = alignment
        case let .list(metrics, floor): _ = metrics; _ = floor
        case let .section(header, insets): _ = header; _ = insets
        case let .navigation(title, metrics, floor): _ = title; _ = metrics; _ = floor
        }
        if let style = plan.style(nodeID: node.identity.id, pressed: true, focused: true) {
            let _: UIAppearancePaintV1 = style.foreground
            _ = style.foreground.color.alpha; _ = style.foreground.opacityPermille
            _ = style.background; _ = style.rowBackground; _ = style.separator
            _ = style.disabled; _ = style.pressed; _ = style.focused
            _ = style.placeholder; _ = style.caret; _ = style.selection; _ = style.border
            _ = style.toggleTrack; _ = style.toggleThumb; _ = style.pressedOverlay
            _ = style.focusOutline?.paint; _ = style.focusOutline?.width64; _ = style.focusOutline?.radius64
        }
    }
    return plan.revision
}
