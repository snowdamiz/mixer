import Testing
import MixerUI

private func environmentResolutionV2(scheme: UIColorSchemeV1 = .light, direction: UILayoutDirectionV1 = .leftToRight,
                                     profile: UISharedTextProfileV1 = .l, density: UInt16 = 1024,
                                     width: UInt32 = 25728, height: UInt32 = 55936,
                                     safe: UIInsets64V1 = UIInsets64V1(top: 0, leading: 0, bottom: 0, trailing: 0),
                                     locale: String = "en-US", bold: Bool = false, contrast: Bool = false,
                                     motion: Bool = false, generation: UInt64 = 1) -> UIAppearanceEnvironmentV2 {
    UIAppearanceEnvironmentV2(scheme: scheme, direction: direction, profile: profile, density1024: density,
        viewport: UIAppearanceViewportV2(width64: width, height64: height), safeArea64: safe,
        localeIdentifier: locale, accessibility: UIAppearanceAccessibilityV2(boldText: bold, increasedContrast: contrast,
            reduceMotion: motion), generation: generation)
}
private func snapshotResolutionV2(_ root: UINode, limits: UIValidationLimits = .standard) throws -> UIRenderSnapshot {
    var reconciler = UIReconciler(validator: UIValidator(limits: limits))
    try reconciler.apply(UIDocument(revision: 42, root: root))
    return try reconciler.currentSnapshot()
}
private func planResolutionV2(_ root: UINode, environment: UIAppearanceEnvironmentV2 = environmentResolutionV2(),
                              configuration: UIAppearanceConfigurationV2? = nil,
                              platform: UIAppearancePlatformV2 = .iOS) throws -> UIResolvedAppearancePlanV2 {
    try UIAppearanceResolverV2.prepare(snapshot: snapshotResolutionV2(root),
        configuration: configuration ?? UIAppearanceDescriptorCodecV2.mixerDefaultV2(), environment: environment, platform: platform)
}
private func textResolutionV2(_ id: String, _ style: String = "body") -> UINode {
    UINode(id: id, kind: .text, properties: ["text": .string(id), "style": .string(style)])
}
private func buttonResolutionV2(_ id: String, _ role: String = "normal", disabled: Bool = false) -> UINode {
    UINode(id: id, kind: .button, properties: ["label": .string(id), "role": .string(role), "disabled": .bool(disabled)],
        actions: [UIActionBinding(id: id + "Action", event: .activate)])
}
private func fieldResolutionV2(_ id: String, disabled: Bool = false) -> UINode {
    UINode(id: id, kind: .textField, properties: ["label": .string("Placeholder"), "value": .string("Input"), "disabled": .bool(disabled)],
        actions: [UIActionBinding(id: id + "Action", event: .textChange)])
}
private func toggleResolutionV2(_ id: String, _ checked: Bool, disabled: Bool = false) -> UINode {
    UINode(id: id, kind: .toggle, properties: ["label": .string(id), "value": .bool(checked), "disabled": .bool(disabled)],
        actions: [UIActionBinding(id: id + "Action", event: .valueChange)])
}
private func themeResolutionV2() throws -> UIThemeV2 {
    guard case let .shared(theme) = try UIAppearanceDescriptorCodecV2.mixerDefaultV2().mode else { throw UIAppearanceErrorV2.shape }
    return theme
}
private func rethemeResolutionV2(_ theme: UIThemeV2, typography: UITypographyV2? = nil,
                                 light: UIPaintsV2? = nil, stacks: UIStackMetricsV2? = nil,
                                 groupedList: UIGroupedListMetricsV2? = nil) -> UIThemeV2 {
    UIThemeV2(recipe: theme.recipe, typography: typography ?? theme.typography, light: light ?? theme.light, dark: theme.dark,
        stacks: stacks ?? theme.stacks, groupedList: groupedList ?? theme.groupedList, button: theme.button,
        field: theme.field, toggle: theme.toggle, navigation: theme.navigation)
}
private func colorResolutionV2(_ red: UInt8, _ green: UInt8, _ blue: UInt8, _ alpha: UInt8 = 255) -> UIRGBA8V1 {
    UIRGBA8V1(red: red, green: green, blue: blue, alpha: alpha)
}
private func listResolutionV2(_ plan: UIResolvedAppearancePlanV2, _ id: String = "list") throws -> UIResolvedListV2 {
    guard case let .list(value) = plan.node(for: id)?.recipe else { throw UIAppearanceErrorV2.shape }
    return value
}

@Test func resolutionV2TenKindsPreorderContentAndSnapshotIdentity() throws {
    let root = UINode(id: "nav", kind: .navigation, properties: ["title": .string("Original Case")], children: [
        UINode(id: "list", kind: .list, children: [UINode(id: "section", kind: .section,
            properties: ["title": .string("Header")], children: [UINode(id: "v", kind: .vStack, children: [
                textResolutionV2("text"), buttonResolutionV2("button"), fieldResolutionV2("field"),
                toggleResolutionV2("toggle", true), UINode(id: "h", kind: .hStack), UINode(id: "z", kind: .zStack)])])])])
    let snapshot = try snapshotResolutionV2(root)
    let plan = try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: UIAppearanceDescriptorCodecV2.mixerDefaultV2(),
        environment: environmentResolutionV2(), platform: .iOS)
    #expect(plan.nodes.map(\.identity.id) == ["nav", "list", "section", "v", "text", "button", "field", "toggle", "h", "z"])
    #expect(Set(plan.nodes.map(\.kind)) == Set(NodeKind.allCases))
    #expect(plan.revision == 42 && plan.nodes.count == snapshot.nodeCount)
    #expect(plan.configurationID == "mixer.measured-candidate.v2" && plan.recipe == .measuredShared2)
    for node in plan.nodes { #expect(node.identity == snapshot.identity(for: node.identity.id)) }
    #expect(plan.node(for: "v")?.childIDs == ["text", "button", "field", "toggle", "h", "z"])
    guard case let .textField(label, value, text, metrics) = plan.node(for: "field")?.recipe else { throw UIAppearanceErrorV2.shape }
    #expect(label == "Placeholder" && value == "Input" && text.value == "Input" && text.role == .body)
    #expect(metrics.minimumHitHeight64 == 2816)
    guard case let .navigation(nav) = plan.node(for: "nav")?.recipe else { throw UIAppearanceErrorV2.shape }
    #expect(nav.expandedTitle?.value == "Original Case" && nav.expandedTitle?.role == .navigationExpanded)
    #expect(nav.compactTitle?.value == "Original Case" && nav.compactTitle?.role == .headline && nav.compactTitle?.maximumLines == 1)
    #expect(nav.metrics.minimumExpandedBar64 == 6784 && nav.metrics.minimumCompactBar64 == 2816)
    #expect(snapshot.document.root == root)
    #expect(plan.node(for: "missing") == nil && plan.style(nodeID: "missing") == nil)
}

@Test func resolutionV2SixRoleMetricsAcrossAllTwelveProfilesWithoutScalar() throws {
    let expected: [(UISharedTextProfileV1, UInt32, UInt32, UInt32, UInt32, UInt32)] = [
        (.xs,14,25,11,31,49), (.s,15,26,11,32,50), (.m,16,27,11,33,51), (.l,17,28,12,34,52),
        (.xl,19,30,14,36,54), (.xxl,21,32,16,38,56), (.xxxl,23,34,18,40,59),
        (.a1,28,38,22,44,59), (.a2,33,43,26,48,59), (.a3,40,48,32,52,59), (.a4,47,53,37,56,59), (.a5,53,58,43,60,59)]
    let root = UINode(id: "nav", kind: .navigation, properties: ["title": .string("Title")], children: [
        UINode(id: "list", kind: .list, children: [UINode(id: "s", kind: .section, properties: ["title": .string("Header")], children: [
            textResolutionV2("body"), textResolutionV2("headline", "headline"), textResolutionV2("title", "title"),
            textResolutionV2("caption", "caption")])])])
    for (profile, body, title, caption, expanded, floor) in expected {
        for density: UInt16 in [128, 1024, 16384] {
            let plan = try planResolutionV2(root, environment: environmentResolutionV2(profile: profile, density: density))
            for (id, role, size, weight) in [("body", UISharedTextRoleV1.body, body, UIFontWeightV1.w400),
                ("headline", .headline, body, .w600), ("title", .title, title, .w400), ("caption", .caption, caption, .w400)] {
                guard case let .text(text) = plan.node(for: id)?.recipe else { throw UIAppearanceErrorV2.shape }
                #expect(text.role == role && text.metrics.size64 == size * 64 && text.metrics.weight == weight)
            }
            guard case let .section(section) = plan.node(for: "s")?.recipe,
                  case let .navigation(nav) = plan.node(for: "nav")?.recipe else { throw UIAppearanceErrorV2.shape }
            #expect(section.header?.metrics.size64 == body * 64 && section.header?.metrics.weight == .w600)
            #expect(nav.expandedTitle?.metrics.size64 == expanded * 64 && nav.expandedTitle?.metrics.weight == .w700)
            #expect(nav.compactTitle?.metrics.size64 == body * 64 && nav.compactTitle?.metrics.weight == .w600)
            #expect(try listResolutionV2(plan).rowHeightFloor64 == floor * 64)
        }
    }
}

@Test func resolutionV2MixedAdjacentGapsDefaultsExplicitZeroAndRounding() throws {
    let children = [textResolutionV2("body"), textResolutionV2("caption", "caption"), textResolutionV2("headline", "headline"),
        UINode(id: "nested", kind: .vStack, children: [textResolutionV2("nestedBody"), textResolutionV2("nestedCaption", "caption")]),
        textResolutionV2("last", "caption")]
    for (spacing, expected) in [(nil as Double?, [128,512,512,512] as [UInt32]), (0, [0,0,0,0]),
                               (1.0078125, [65,65,65,65]), (256, [16384,16384,16384,16384])] {
        let root = UINode(id: "v", kind: .vStack, properties: spacing.map { ["spacing": .number($0)] } ?? [:], children: children)
        let plan = try planResolutionV2(root)
        #expect(plan.node(for: "v")?.recipe == .vStack(gaps64: expected, alignment: .center))
        #expect(plan.node(for: "nested")?.recipe == .vStack(gaps64: [128], alignment: .center))
    }
    for count in 0...1 {
        let root = UINode(id: "v", kind: .vStack, children: Array(children.prefix(count)))
        #expect(try planResolutionV2(root).node(for: "v")?.recipe == .vStack(gaps64: [], alignment: .center))
    }
}

@Test func resolutionV2AlignmentsHStackGapCountsRTLOrderAndZStackIntrinsicRecipe() throws {
    for raw in ["top", "center", "bottom", "firstTextBaseline", "lastTextBaseline"] {
        let root = UINode(id: "h", kind: .hStack, properties: ["alignment": .string(raw)],
            children: [textResolutionV2("one"), textResolutionV2("two"), textResolutionV2("three")])
        let left = try planResolutionV2(root), right = try planResolutionV2(root, environment: environmentResolutionV2(direction: .rightToLeft))
        #expect(left.nodes == right.nodes && right.node(for: "h")?.childIDs == ["one", "two", "three"])
        #expect(right.node(for: "h")?.recipe == .hStack(gaps64: [512,512], alignment: UIVerticalAlignmentV1(rawValue: raw)!))
    }
    for raw in ["leading", "center", "trailing"] {
        #expect(try planResolutionV2(UINode(id: "v", kind: .vStack, properties: ["alignment": .string(raw)])).node(for: "v")?.recipe ==
            .vStack(gaps64: [], alignment: UIHorizontalAlignmentV1(rawValue: raw)!))
    }
    for raw in ["center", "leading", "trailing", "top", "bottom", "topLeading", "topTrailing", "bottomLeading", "bottomTrailing"] {
        #expect(try planResolutionV2(UINode(id: "z", kind: .zStack, properties: ["alignment": .string(raw)])).node(for: "z")?.recipe ==
            .zStack(alignment: UIOverlayAlignmentV1(rawValue: raw)!))
    }
}

@Test func resolutionV2GroupedRunsSectionsEmptyHeadersAndInteriorSeparators() throws {
    let root = UINode(id: "list", kind: .list, children: [
        UINode(id: "hidden", kind: .section, properties: ["title": .string("")]),
        textResolutionV2("a"), textResolutionV2("b"),
        UINode(id: "headed", kind: .section, properties: ["title": .string("Original header")], children: [textResolutionV2("c"), textResolutionV2("d")]),
        UINode(id: "emptyTitle", kind: .section, properties: ["title": .string("Only header")]),
        UINode(id: "hidden2", kind: .section), textResolutionV2("e"),
        UINode(id: "unheaded", kind: .section, children: [textResolutionV2("f")])])
    let plan = try planResolutionV2(root), list = try listResolutionV2(plan)
    #expect(plan.nodes.map(\.identity.id) == ["list","hidden","a","b","headed","c","d","emptyTitle","hidden2","e","unheaded","f"])
    #expect(list.groups.count == 7)
    #expect(list.groups.map { $0.rowIdentities.map(\.id) } == [[],["a","b"],["c","d"],[],[],["e"],["f"]])
    #expect(list.groups.map(\.visible) == [false,true,true,true,false,true,true])
    #expect(list.groups.map(\.drawsOutline) == [false,true,true,false,false,true,true])
    #expect(list.groups.map(\.leadingGap64) == [0,640,1771,1771,0,1771,1771])
    #expect(list.groups.map(\.headerToRowsGap64) == [0,0,640,0,0,0,0])
    #expect(list.trailingPadding64 == 640 && list.metrics.separatorThickness64 == 43 && list.metrics.separatorInset64 == 1024)
    #expect(list.groups[1].source == .directRun(firstRow: plan.node(for: "a")!.identity))
    #expect(list.groups[2].source == .section(plan.node(for: "headed")!.identity))
    #expect(list.groups[2].header?.value == "Original header" && list.groups[2].header?.role == .sectionHeader)
    for (groupIndex, group) in list.groups.enumerated() {
        for (rowIndex, identity) in group.rowIdentities.enumerated() {
            let row = try #require(plan.node(for: identity.id))
            #expect(row.identity == identity)
            #expect(row.rowPlacement?.listIdentity == plan.node(for: "list")?.identity)
            #expect(row.rowPlacement?.groupIndex == groupIndex && row.rowPlacement?.rowIndex == rowIndex)
            #expect(row.rowPlacement?.separatorAfter == (rowIndex + 1 < group.rowIdentities.count))
        }
    }
    guard case let .section(section) = plan.node(for: "headed")?.recipe else { throw UIAppearanceErrorV2.shape }
    #expect(section.context == .listGroup(listIdentity: plan.node(for: "list")!.identity, groupIndex: 2))
    #expect(section.contentGaps64.isEmpty && section.headerToContentGap64 == 0)
    #expect(plan.node(for: "headed")?.rowPlacement == nil)
}

@Test func resolutionV2OnlyHeaderAndEntirelyEmptyListPadding() throws {
    let only = try listResolutionV2(planResolutionV2(UINode(id: "list", kind: .list, children: [
        UINode(id: "s", kind: .section, properties: ["title": .string("Header")])])) )
    #expect(only.groups.count == 1 && only.groups[0].leadingGap64 == 640 && only.trailingPadding64 == 640)
    #expect(!only.groups[0].drawsOutline && only.groups[0].headerToRowsGap64 == 0)
    for children in [[], [UINode(id: "s", kind: .section)], [UINode(id: "s", kind: .section, properties: ["title": .string("")])]] {
        let list = try listResolutionV2(planResolutionV2(UINode(id: "list", kind: .list, children: children)))
        #expect(list.trailingPadding64 == 0 && !list.groups.contains(where: \.visible))
    }
}

@Test func resolutionV2SectionsOutsideAndWithinRowsAreSemanticLeadingContent() throws {
    let semantic = UINode(id: "semantic", kind: .section, properties: ["title": .string("Semantic")],
        children: [textResolutionV2("one"), textResolutionV2("two")])
    let outside = try planResolutionV2(semantic)
    guard case let .section(section) = outside.node(for: "semantic")?.recipe else { throw UIAppearanceErrorV2.shape }
    #expect(section.context == .outsideList && section.contentGaps64 == [512] && section.headerToContentGap64 == 640 && section.alignment == .leading)
    let root = UINode(id: "list", kind: .list, children: [UINode(id: "s", kind: .section, children: [semantic])])
    let inside = try planResolutionV2(root)
    guard case let .section(row) = inside.node(for: "semantic")?.recipe else { throw UIAppearanceErrorV2.shape }
    #expect(row.context == .withinListRow(listIdentity: inside.node(for: "list")!.identity))
    #expect(row.contentGaps64 == [512] && row.headerToContentGap64 == 640 && inside.node(for: "semantic")?.rowPlacement?.rowIndex == 0)
    #expect(try listResolutionV2(inside).groups[0].rowIdentities.map(\.id) == ["semantic"])
}

@Test func resolutionV2AbsentAndEmptyNavigationTitlesMakeNoLabels() throws {
    for properties: [String: UIValue] in [[:], ["title": .string("")]] {
        let plan = try planResolutionV2(UINode(id: "nav", kind: .navigation, properties: properties, children: [textResolutionV2("child")]))
        guard case let .navigation(nav) = plan.node(for: "nav")?.recipe else { throw UIAppearanceErrorV2.shape }
        #expect(nav.expandedTitle == nil && nav.compactTitle == nil)
        #expect(plan.style(nodeID: "nav")?.paints == .navigation(expanded: nil, compact: nil, background: colorResolutionV2(242,242,247)))
    }
}

@Test func resolutionV2DisabledInheritancePreservesExactRoleTextAndClearsControlState() throws {
    let root = UINode(id: "v", kind: .vStack, properties: ["disabled": .bool(true)], children: [
        textResolutionV2("text"), UINode(id: "section", kind: .section, properties: ["title": .string("Header")]),
        buttonResolutionV2("button"), fieldResolutionV2("field"), toggleResolutionV2("toggle", true),
        UINode(id: "nested", kind: .hStack, properties: ["disabled": .bool(false)], children: [buttonResolutionV2("cannotEnable")])])
    for (scheme, primary, header, disabled, onTrack, thumb) in [
        (UIColorSchemeV1.light, colorResolutionV2(0,0,0), colorResolutionV2(133,133,139), colorResolutionV2(191,191,191), colorResolutionV2(153,227,172), colorResolutionV2(255,255,255)),
        (.dark, colorResolutionV2(255,255,255), colorResolutionV2(141,141,147), colorResolutionV2(85,85,86), colorResolutionV2(38,119,59), colorResolutionV2(142,142,143))] {
        let plan = try planResolutionV2(root, environment: environmentResolutionV2(scheme: scheme))
        for node in plan.nodes {
            let style = try #require(plan.style(nodeID: node.identity.id, pressed: true, focused: true))
            #expect(node.disabled && style.disabled && !style.pressed && !style.focused)
        }
        #expect(plan.style(nodeID: "text")?.paints == .text(foreground: primary, background: colorResolutionV2(0,0,0,0)))
        #expect(plan.style(nodeID: "section")?.paints == .section(header: header, background: colorResolutionV2(0,0,0,0)))
        #expect(plan.style(nodeID: "button")?.paints == .button(UIButtonPaintV2(label: disabled, background: colorResolutionV2(0,0,0,0)), focus: nil))
        guard case let .field(field) = plan.style(nodeID: "field")?.paints,
              case let .toggle(toggle, focus) = plan.style(nodeID: "toggle")?.paints else { throw UIAppearanceErrorV2.shape }
        #expect(field.text == disabled && field.placeholder == disabled && field.caret.alpha == 0 && field.selection.alpha == 0 && field.outline.width64 == 0)
        #expect(toggle.label == disabled && toggle.track == onTrack && toggle.thumb == thumb && toggle.overlay.alpha == 0 && focus == nil)
    }
}

@Test func resolutionV2CompleteButtonRoleSchemeStateMatrixAndFocusCoexistence() throws {
    let root = UINode(id: "v", kind: .vStack, children: [buttonResolutionV2("normal"), buttonResolutionV2("cancel", "cancel"),
        buttonResolutionV2("destructive", "destructive"), buttonResolutionV2("disabled", disabled: true)])
    for (scheme, normal, destructive, disabled) in [
        (UIColorSchemeV1.light, colorResolutionV2(0,136,255), colorResolutionV2(255,56,60), colorResolutionV2(191,191,191)),
        (.dark, colorResolutionV2(0,145,255), colorResolutionV2(255,66,69), colorResolutionV2(85,85,86))] {
        let plan = try planResolutionV2(root, environment: environmentResolutionV2(scheme: scheme))
        for id in ["normal", "cancel", "destructive", "disabled"] {
            let color = id == "disabled" ? disabled : (id == "destructive" ? destructive : normal)
            for press in [false,true] { for focus in [false,true] {
                let style = try #require(plan.style(nodeID: id, pressed: press, focused: focus))
                guard case let .button(paint, outline) = style.paints else { throw UIAppearanceErrorV2.shape }
                #expect(paint.label == color)
                #expect(paint.background == (press && id != "disabled" ? UIRGBA8V1(red: color.red, green: color.green, blue: color.blue, alpha: 31) : colorResolutionV2(0,0,0,0)))
                #expect(style.pressed == (press && id != "disabled") && style.focused == (focus && id != "disabled"))
                if focus && id != "disabled" { #expect(outline == UIOutlineV2(color: color, width64: 128, radius64: 512)) }
                else { #expect(outline == nil) }
            } }
        }
    }
}

@Test func resolutionV2CompleteFieldStatesPressIgnoredAndToggleValueStateMatrix() throws {
    let root = UINode(id: "v", kind: .vStack, children: [fieldResolutionV2("field"), fieldResolutionV2("disabledField", disabled: true),
        toggleResolutionV2("on", true), toggleResolutionV2("off", false), toggleResolutionV2("disabledOn", true, disabled: true),
        toggleResolutionV2("disabledOff", false, disabled: true), textResolutionV2("ordinary")])
    for (scheme, accent, off, on, disabledOff, disabledOn, thumb, placeholder) in [
        (UIColorSchemeV1.light, colorResolutionV2(0,136,255), colorResolutionV2(197,197,199), colorResolutionV2(52,199,89),
         colorResolutionV2(229,229,231), colorResolutionV2(153,227,172), colorResolutionV2(255,255,255), colorResolutionV2(179,179,181)),
        (.dark, colorResolutionV2(0,145,255), colorResolutionV2(90,90,94), colorResolutionV2(48,209,88),
         colorResolutionV2(56,56,59), colorResolutionV2(38,119,59), colorResolutionV2(142,142,143), colorResolutionV2(90,90,94))] {
        let plan = try planResolutionV2(root, environment: environmentResolutionV2(scheme: scheme))
        for focus in [false,true] {
            let style = try #require(plan.style(nodeID: "field", pressed: true, focused: focus))
            guard case let .field(field) = style.paints else { throw UIAppearanceErrorV2.shape }
            #expect(!style.pressed && style.focused == focus && field.placeholder == placeholder && field.caret == accent)
            #expect(field.selection == UIRGBA8V1(red: accent.red, green: accent.green, blue: accent.blue, alpha: 61))
            #expect(field.outline.width64 == (focus ? 128 : 0) && field.background.alpha == 0)
        }
        for (id, track) in [("on",on),("off",off),("disabledOn",disabledOn),("disabledOff",disabledOff)] {
            let disabled = id.hasPrefix("disabled")
            for press in [false,true] { for focus in [false,true] {
                let style = try #require(plan.style(nodeID: id, pressed: press, focused: focus))
                guard case let .toggle(toggle, outline) = style.paints else { throw UIAppearanceErrorV2.shape }
                #expect(toggle.track == track && toggle.thumb == (disabled ? thumb : colorResolutionV2(255,255,255)))
                #expect(toggle.overlay == (press && !disabled ? UIRGBA8V1(red: accent.red, green: accent.green, blue: accent.blue, alpha: 31) : colorResolutionV2(0,0,0,0)))
                #expect((outline != nil) == (focus && !disabled))
            } }
        }
        #expect(plan.style(nodeID: "ordinary", pressed: true, focused: true)?.pressed == false)
        #expect(plan.style(nodeID: "ordinary", pressed: true, focused: true)?.focused == false)
    }
}

@Test func resolutionV2ExplicitAppPaintAlphaCustomGeometryAndPlatformTheme() throws {
    let theme = try themeResolutionV2(), p = theme.light
    let canvas = colorResolutionV2(1,2,3,128), ink = colorResolutionV2(4,5,6,99)
    let paints = UIPaintsV2(canvas: canvas, surface: p.surface, separator: p.separator,
        text: UIRolePaintsV2(body: ink, headline: p.text.headline, title: p.text.title, caption: p.text.caption,
            sectionHeader: p.text.sectionHeader, navigationExpanded: p.text.navigationExpanded),
        button: p.button, field: p.field, toggle: p.toggle)
    let stacks = UIStackMetricsV2(defaultGap64: 123, bodyCaptionGap64: 42, missingVStackGap: .bodyThenCaptionPairOtherwiseDefault,
        vStackAlignment: .trailing, hStackAlignment: .lastTextBaseline, zStackAlignment: .bottomLeading)
    let custom = rethemeResolutionV2(theme, light: paints, stacks: stacks)
    let configuration = UIAppearanceConfigurationV2(id: "explicit.app", mode: .platformSpecific(iOS: theme, android: custom, reason: "Reviewed app distinction"))
    let root = UINode(id: "v", kind: .vStack, children: [textResolutionV2("body"),textResolutionV2("caption","caption"),UINode(id: "h", kind: .hStack)])
    let first = try planResolutionV2(root, configuration: configuration), second = try planResolutionV2(root, configuration: configuration, platform: .android)
    #expect(first.canvas == colorResolutionV2(242,242,247) && second.canvas == canvas)
    #expect(second.platformSpecificReason == "Reviewed app distinction")
    #expect(second.style(nodeID: "body")?.paints == .text(foreground: ink, background: colorResolutionV2(0,0,0,0)))
    #expect(second.node(for: "v")?.recipe == .vStack(gaps64: [42,123], alignment: .trailing))
    #expect(second.node(for: "h")?.recipe == .hStack(gaps64: [], alignment: .lastTextBaseline))
}

@Test func resolutionV2RejectsNormalizedEnvironmentBoundsWithoutClamping() throws {
    let root = textResolutionV2("text")
    for density: UInt16 in [0,127,16385,.max] {
        #expect(throws: UIAppearanceGeometryErrorV2.density) { _ = try planResolutionV2(root, environment: environmentResolutionV2(density: density)) }
    }
    let badGeometry = [environmentResolutionV2(width: 0), environmentResolutionV2(height: 0),
        environmentResolutionV2(width: .max), environmentResolutionV2(height: .max),
        environmentResolutionV2(safe: UIInsets64V1(top: .max, leading: 0, bottom: .max, trailing: 0)),
        environmentResolutionV2(safe: UIInsets64V1(top: 0, leading: 25728, bottom: 0, trailing: 1))]
    for environment in badGeometry {
        #expect(throws: UIAppearanceErrorV2.geometry) { _ = try planResolutionV2(root, environment: environment) }
    }
    for locale in ["",String(repeating: "x", count: 129),"en\nUS","en\u{0000}US"] {
        #expect(throws: UIAppearanceErrorV2.shape) { _ = try planResolutionV2(root, environment: environmentResolutionV2(locale: locale)) }
    }
    for environment in [environmentResolutionV2(bold: true),environmentResolutionV2(contrast: true)] {
        #expect(throws: UIAppearanceErrorV2.unsupportedNativeOperation) { _ = try planResolutionV2(root, environment: environment) }
    }
    let maximum = UIAppearanceGeometryV2.maximumExtent64
    for environment in [environmentResolutionV2(density: 128, width: maximum, height: maximum, locale: String(repeating: "x", count: 128), generation: 0),
        environmentResolutionV2(density: 16384, safe: UIInsets64V1(top: 55936, leading: 25728, bottom: 0, trailing: 0), motion: true, generation: .max)] {
        #expect(try planResolutionV2(root, environment: environment).environment == environment)
    }
}

@Test func resolutionV2RejectsNestedListsAndEveryNonrootNavigationBeforeOutput() throws {
    let nested = UINode(id: "list", kind: .list, children: [UINode(id: "v", kind: .vStack, children: [
        UINode(id: "s", kind: .section, children: [UINode(id: "nested", kind: .list)])])])
    let nonroot = UINode(id: "v", kind: .vStack, children: [UINode(id: "nav", kind: .navigation, children: [textResolutionV2("child")])])
    let multiple = UINode(id: "nav", kind: .navigation, children: [UINode(id: "v", kind: .vStack, children: [
        UINode(id: "second", kind: .navigation, children: [textResolutionV2("child")])])])
    for root in [nested,nonroot,multiple] {
        #expect(throws: UIAppearanceErrorV2.unsupportedNativeOperation) { _ = try planResolutionV2(root) }
    }
    let siblings = UINode(id: "v", kind: .vStack, children: [UINode(id: "first", kind: .list),UINode(id: "second", kind: .list)])
    #expect(try planResolutionV2(siblings).nodes.count == 3)
}

@Test func resolutionV2WholeConfigurationRevalidatesUnselectedThemeAndCatalog() throws {
    let theme = try themeResolutionV2()
    let invalidStacks = UIStackMetricsV2(defaultGap64: 65537, bodyCaptionGap64: 128, missingVStackGap: .bodyThenCaptionPairOtherwiseDefault,
        vStackAlignment: .center, hStackAlignment: .center, zStackAlignment: .center)
    let invalid = rethemeResolutionV2(theme, stacks: invalidStacks)
    for configuration in [UIAppearanceConfigurationV2(id: "", mode: .shared(theme)),
        UIAppearanceConfigurationV2(id: "bad", mode: .platformSpecific(iOS: theme, android: invalid, reason: "Invalid unselected theme")),
        UIAppearanceConfigurationV2(id: "bad", mode: .platformSpecific(iOS: invalid, android: theme, reason: "Invalid selected theme")),
        UIAppearanceConfigurationV2(id: "bad", mode: .platformSpecific(iOS: theme, android: theme, reason: " "))] {
        #expect(throws: UIAppearanceErrorV2.self) { _ = try planResolutionV2(textResolutionV2("t"), configuration: configuration) }
    }
    let resources = (0..<65).map { UIAppearanceResourceV1(id: "r\($0)", kind: .iconPNG, path: "missing/\($0).png",
        sha256: String(repeating: "a", count: 64), bytes: 1, provenance: "Raw metadata only", scale: 1, locale: "und", direction: .neutral) }
    #expect(try planResolutionV2(textResolutionV2("t"), configuration: UIAppearanceConfigurationV2(id: "resources", mode: .shared(theme),
        resources: Array(resources.prefix(64)))).resources.count == 64)
    #expect(throws: UIAppearanceErrorV2.self) { _ = try planResolutionV2(textResolutionV2("t"), configuration:
        UIAppearanceConfigurationV2(id: "resources", mode: .shared(theme), resources: resources)) }
}

@Test func resolutionV2MetadataFontsRemainReferencesWithoutNativeResourceAuthority() throws {
    let theme = try themeResolutionV2()
    let resource = UIAppearanceResourceV1(id: "font", kind: .fontSFNT, path: "missing/fixture.ttf", sha256: String(repeating: "a", count: 64),
        bytes: 1, provenance: "Synthetic descriptor metadata", scale: 1, locale: "und", direction: .neutral)
    let font = UIFontSourceV1.bundled(faces: [UIFontWeightV1.w400,.w600,.w700].map {
        UIFontFaceV1(resourceID: "font", postScriptName: "Fixture\($0.rawValue)", weight: $0, style: .normal) }, fallback: .none)
    let typography = UITypographyV2(font: font, profiles: theme.typography.profiles, defaultProfile: .a5, preferencePolicy: theme.typography.preferencePolicy)
    let config = UIAppearanceConfigurationV2(id: "references", mode: .shared(rethemeResolutionV2(theme, typography: typography)), resources: [resource])
    let plan = try planResolutionV2(textResolutionV2("body"), configuration: config)
    #expect(plan.font == font && plan.resources == [resource] && plan.environment.profile == .l)
    guard case let .text(text) = plan.node(for: "body")?.recipe else { throw UIAppearanceErrorV2.shape }
    #expect(text.metrics.size64 == 1088) // selected environment wins over declared build/reference default
}

@Test func resolutionV2StandardNodeDepthChildrenStringAndAggregateBounds() throws {
    func tree(_ count: Int) -> UINode {
        var remaining = count - 1, groups: [UINode] = [], next = 0
        while remaining > 0 {
            let count = min(999, remaining - 1)
            groups.append(UINode(id: "g\(next)", kind: .vStack, children: (0..<count).map { textResolutionV2("t\(next)-\($0)") }))
            remaining -= count + 1; next += 1
        }
        return UINode(id: "v", kind: .vStack, children: groups)
    }
    #expect(try planResolutionV2(tree(4096)).nodes.count == 4096)
    var deep = textResolutionV2("leaf")
    for index in 0..<64 { deep = UINode(id: "deep\(index)", kind: .vStack, children: [deep]) }
    let wide = UINode(id: "wide", kind: .vStack, children: (0..<1001).map { textResolutionV2("t\($0)") })
    let long = UINode(id: "long", kind: .text, properties: ["text": .string(String(repeating: "x", count: 16385))])
    let aggregate = UINode(id: "aggregate", kind: .vStack, children: (0..<65).map {
        UINode(id: "t\($0)", kind: .text, properties: ["text": .string(String(repeating: "x", count: 16384))]) })
    let limits = UIValidationLimits(maximumMessageBytes: 2097152, maximumNodes: 8192, maximumDepth: 128,
        maximumChildrenPerNode: 2000, maximumStringBytes: 32768)
    for (root, bound) in [(tree(4097),"nodes"),(deep,"depth"),(wide,"children"),(long,"stringBytes"),(aggregate,"contentBytes")] {
        let snapshot = try snapshotResolutionV2(root, limits: limits)
        #expect(throws: UIValidationError.limitExceeded(bound)) {
            _ = try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: UIAppearanceDescriptorCodecV2.mixerDefaultV2(),
                environment: environmentResolutionV2(), platform: .iOS)
        }
    }
}

@Test func resolutionV2DerivedRowGroupCountsAtStandardBoundary() throws {
    let groups = (0..<4).map { group in UINode(id: "s\(group)", kind: .section, properties: ["title": .string("Header")],
        children: (0..<1000).map { textResolutionV2("t\(group)-\($0)") }) }
    let plan = try planResolutionV2(UINode(id: "list", kind: .list, children: groups)), list = try listResolutionV2(plan)
    #expect(plan.nodes.count == 4005 && list.groups.count == 4 && list.groups.flatMap(\.rowIdentities).count == 4000)
    #expect(plan.nodes.filter { $0.rowPlacement != nil }.count == 4000)
    #expect(plan.nodes.filter { $0.rowPlacement?.separatorAfter == true }.count == 3996)
}

@Test func resolutionV2FailedOrEnvironmentOnlyPreparationPreservesReconcilerRevisionRoutingAndIdentity() throws {
    var reconciler = UIReconciler()
    try reconciler.apply(UIDocument(revision: 9, root: buttonResolutionV2("button")))
    let snapshot = try reconciler.currentSnapshot(), identity = try #require(snapshot.identity(for: "button"))
    #expect(throws: UIAppearanceErrorV2.unsupportedNativeOperation) {
        _ = try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: UIAppearanceDescriptorCodecV2.mixerDefaultV2(),
            environment: environmentResolutionV2(bold: true), platform: .android)
    }
    let first = try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: UIAppearanceDescriptorCodecV2.mixerDefaultV2(),
        environment: environmentResolutionV2(), platform: .iOS)
    let changed = try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: UIAppearanceDescriptorCodecV2.mixerDefaultV2(),
        environment: environmentResolutionV2(scheme: .dark, direction: .rightToLeft, profile: .a5, density: 16384, motion: true, generation: 2), platform: .iOS)
    for plan in [first,changed] {
        #expect(plan.revision == 9 && plan.node(for: "button")?.identity == identity)
        for _ in 0..<3 { _ = plan.style(nodeID: "button", pressed: true, focused: true) }
        #expect(plan.node(for: "button")?.identity == identity)
    }
    #expect(reconciler.snapshot?.identity(for: "button") == identity && reconciler.snapshot?.document.revision == 9)
    #expect(try snapshot.route(UIEventEnvelope(revision: 9, identity: identity, event: .activate)).actionID == "buttonAction")
    try reconciler.apply(UIDocument(revision: 10, root: buttonResolutionV2("button", "destructive")))
    #expect(reconciler.snapshot?.identity(for: "button") == identity)
    try reconciler.apply(UIDocument(revision: 11, root: textResolutionV2("button")))
    #expect(reconciler.snapshot?.identity(for: "button") != identity)
}

@Test func resolutionV2SelectableMaximumLinesAndSharedPlatformPlans() throws {
    let root = UINode(id: "text", kind: .text, properties: ["text": .string("Original العربية e\u{0301} 👩🏽‍🚀"),
        "style": .string("caption"), "selectable": .bool(true), "maxLines": .number(100)])
    let first = try planResolutionV2(root), second = try planResolutionV2(root, platform: .android)
    guard case let .text(text) = first.node(for: "text")?.recipe else { throw UIAppearanceErrorV2.shape }
    #expect(text.value == "Original العربية e\u{0301} 👩🏽‍🚀" && text.selectable && text.maximumLines == 100 && text.role == .caption)
    #expect(first.nodes == second.nodes && first.canvas == second.canvas && first.platformSpecificReason == nil)
    #expect(first.style(nodeID: "text") == second.style(nodeID: "text"))
}

@Test func resolutionV2CustomCompleteMatricesAreSelectedWholeWithoutOpacityOrFallbacks() throws {
    let theme = try themeResolutionV2(), original = theme.light
    let clear = colorResolutionV2(0,0,0,0)
    func color(_ seed: UInt8) -> UIRGBA8V1 { colorResolutionV2(seed,seed + 1,seed + 2,seed + 3) }
    func button(_ seed: UInt8) -> UIButtonStatesV2 {
        UIButtonStatesV2(enabled: UIButtonPaintV2(label: color(seed), background: color(seed + 4)),
            pressed: UIButtonPaintV2(label: color(seed + 8), background: color(seed + 12)),
            disabled: UIButtonPaintV2(label: color(seed + 16), background: clear),
            focus: UIOutlineV2(color: color(seed + 20), width64: UInt32(seed), radius64: UInt32(seed + 1)))
    }
    func field(_ seed: UInt8, width: UInt32, disabled: Bool = false) -> UIFieldPaintV2 {
        UIFieldPaintV2(text: color(seed), placeholder: color(seed + 4), background: color(seed + 8),
            caret: disabled ? clear : color(seed + 12), selection: disabled ? clear : color(seed + 16),
            outline: UIOutlineV2(color: color(seed + 20), width64: width, radius64: 123))
    }
    func toggle(_ seed: UInt8) -> UIToggleStatesV2 {
        func paint(_ seed: UInt8, disabled: Bool = false) -> UITogglePaintV2 {
            UITogglePaintV2(label: color(seed), track: color(seed + 4), thumb: color(seed + 8), overlay: disabled ? clear : color(seed + 12))
        }
        return UIToggleStatesV2(enabled: paint(seed), pressed: paint(seed + 16), disabled: paint(seed + 32, disabled: true),
            focus: UIOutlineV2(color: color(seed + 48), width64: 17, radius64: 19))
    }
    let buttons = UIButtonRolesV2(normal: button(1), destructive: button(31), cancel: button(61))
    let fields = UIFieldStatesV2(enabled: field(91,width: 0), focused: field(121,width: 7), disabled: field(151,width: 0,disabled: true))
    let toggles = UIToggleValuesV2(on: toggle(1), off: toggle(81))
    let paints = UIPaintsV2(canvas: color(191), surface: color(195), separator: color(199), text: original.text,
        button: buttons, field: fields, toggle: toggles)
    let config = UIAppearanceConfigurationV2(id: "authored.matrices", mode: .shared(rethemeResolutionV2(theme, light: paints)))
    for disabled in [false,true] {
        let root = UINode(id: "v", kind: .vStack, properties: ["disabled": .bool(disabled)], children: [
            buttonResolutionV2("normal"), buttonResolutionV2("destructive","destructive"), buttonResolutionV2("cancel","cancel"),
            fieldResolutionV2("field"), toggleResolutionV2("on",true), toggleResolutionV2("off",false)])
        let plan = try planResolutionV2(root, configuration: config), before = plan.nodes
        #expect(plan.canvas == color(191))
        for press in [false,true] { for focus in [false,true] {
            for (id, states) in [("normal",buttons.normal),("destructive",buttons.destructive),("cancel",buttons.cancel)] {
                #expect(plan.style(nodeID: id, pressed: press, focused: focus)?.paints ==
                    .button(disabled ? states.disabled : (press ? states.pressed : states.enabled), focus: !disabled && focus ? states.focus : nil))
            }
            #expect(plan.style(nodeID: "field", pressed: press, focused: focus)?.paints == .field(disabled ? fields.disabled : (focus ? fields.focused : fields.enabled)))
            for (id, states) in [("on",toggles.on),("off",toggles.off)] {
                #expect(plan.style(nodeID: id, pressed: press, focused: focus)?.paints ==
                    .toggle(disabled ? states.disabled : (press ? states.pressed : states.enabled), focus: !disabled && focus ? states.focus : nil))
            }
        } }
        #expect(plan.nodes == before)
    }
}
