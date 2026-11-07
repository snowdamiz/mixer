import Testing
import MixerUI

private let resolutionEnvironmentV1 = UIAppearanceEnvironmentV1(scheme: .light, direction: .leftToRight,
    textScale1024: 1024, density1024: 1024)

private func resolutionSnapshotV1(_ root: UINode, revision: UInt64 = 71,
                                  limits: UIValidationLimits = .standard) throws -> UIRenderSnapshot {
    var reconciler = UIReconciler(validator: UIValidator(limits: limits))
    try reconciler.apply(UIDocument(revision: revision, root: root))
    return try reconciler.currentSnapshot()
}

private func resolutionPlanV1(_ root: UINode, configuration: UIAppearanceConfigurationV1? = nil,
                              environment: UIAppearanceEnvironmentV1 = resolutionEnvironmentV1,
                              platform: UIAppearancePlatformV1 = .iOS) throws -> UIResolvedAppearancePlanV1 {
    try UIAppearanceResolverV1.prepare(snapshot: resolutionSnapshotV1(root),
        configuration: configuration ?? UIAppearanceDescriptorCodecV1.mixerDefaultV1(),
        environment: environment, platform: platform)
}

private func resolutionThemeV1() throws -> UIThemeV1 {
    guard case let .shared(theme) = try UIAppearanceDescriptorCodecV1.mixerDefaultV1().mode else {
        throw UIAppearanceErrorV1.shape
    }
    return theme
}

private func resolutionRethemeV1(_ theme: UIThemeV1, light: UIPaletteV1? = nil,
                                 typography: UITypographyV1? = nil, layout: UILayoutMetricsV1? = nil,
                                 controls: UIControlMetricsV1? = nil) -> UIThemeV1 {
    UIThemeV1(recipe: theme.recipe, light: light ?? theme.light, dark: theme.dark,
        typography: typography ?? theme.typography, layout: layout ?? theme.layout, controls: controls ?? theme.controls)
}

private func resolutionPaletteV1(_ palette: UIPaletteV1, accent: UIRGBA8V1,
                                 destructive: UIRGBA8V1? = nil, canvas: UIRGBA8V1? = nil) -> UIPaletteV1 {
    UIPaletteV1(canvas: canvas ?? palette.canvas, surface: palette.surface, primaryText: palette.primaryText,
        secondaryText: palette.secondaryText, accent: accent, destructive: destructive ?? palette.destructive,
        disabledText: palette.disabledText, separator: palette.separator, focus: accent,
        toggleOff: palette.toggleOff, toggleThumb: palette.toggleThumb)
}

private func resolutionButtonV1(_ id: String, role: String = "normal", disabled: Bool = false) -> UINode {
    UINode(id: id, kind: .button, properties: ["label": .string(id), "role": .string(role), "disabled": .bool(disabled)],
        actions: [UIActionBinding(id: id + "Action", event: .activate)])
}

private func resolutionToggleV1(_ id: String, checked: Bool) -> UINode {
    UINode(id: id, kind: .toggle, properties: ["label": .string(id), "value": .bool(checked)],
        actions: [UIActionBinding(id: id + "Action", event: .valueChange)])
}

private func resolutionTextV1(_ id: String, style: String = "body") -> UINode {
    UINode(id: id, kind: .text, properties: ["text": .string(id), "style": .string(style)])
}

@Test func resolutionV1EveryCurrentKindAndStableSnapshotIdentities() throws {
    let root = UINode(id: "navigation", kind: .navigation, properties: ["title": .string("Heading")], children: [
        UINode(id: "list", kind: .list, children: [
            UINode(id: "section", kind: .section, properties: ["title": .string("Group")], children: [
                UINode(id: "vertical", kind: .vStack, children: [
                    resolutionTextV1("text"), resolutionButtonV1("button"),
                    UINode(id: "field", kind: .textField, properties: ["label": .string("Name"), "value": .string("V")],
                        actions: [UIActionBinding(id: "change", event: .textChange)]),
                    resolutionToggleV1("toggle", checked: true), UINode(id: "horizontal", kind: .hStack),
                    UINode(id: "overlay", kind: .zStack)
                ])
            ])
        ])
    ])
    let snapshot = try resolutionSnapshotV1(root, revision: UInt64.max)
    let configuration = try UIAppearanceDescriptorCodecV1.mixerDefaultV1()
    let plan = try UIAppearanceResolverV1.prepare(snapshot: snapshot, configuration: configuration,
        environment: resolutionEnvironmentV1, platform: .iOS)
    #expect(plan.revision == UInt64.max)
    #expect(plan.configurationID == configuration.id)
    #expect(plan.recipe == .sharedCandidate1)
    #expect(plan.nodes.map(\.identity.id) == ["navigation", "list", "section", "vertical", "text", "button", "field", "toggle", "horizontal", "overlay"])
    #expect(Set(plan.nodes.map(\.kind)) == Set(NodeKind.allCases))
    #expect(plan.nodes.count == snapshot.nodeCount)
    for node in plan.nodes { #expect(node.identity == snapshot.identity(for: node.identity.id)) }
    #expect(snapshot.document.root == root)
    #expect(snapshot.document.revision == UInt64.max)
    if case let .section(header, _) = plan.node(for: "section")?.recipe { #expect(header?.role == .caption) }
    else { Issue.record("Missing section recipe") }
    if case let .navigation(title, _, floor) = plan.node(for: "navigation")?.recipe {
        #expect(title?.role == .title)
        #expect(floor == 3200) // candidate title line box34 plus8 top/bottom
    } else { Issue.record("Missing navigation recipe") }
    if case let .list(metrics, floor) = plan.node(for: "list")?.recipe {
        #expect(metrics.insets64.leading == 1024)
        #expect(metrics.separator64 == 64)
        #expect(floor == 2816)
    } else { Issue.record("Missing list recipe") }
}

@Test func resolutionV1TextRolesFlagsAndAbsentHeaders() throws {
    let root = UINode(id: "root", kind: .vStack, children: [
        UINode(id: "default", kind: .text, properties: ["text": .string("Default")]),
        resolutionTextV1("headline", style: "headline"), resolutionTextV1("title", style: "title"),
        UINode(id: "caption", kind: .text, properties: ["text": .string("Caption"), "style": .string("caption"),
            "selectable": .bool(true), "maxLines": .number(2)]),
        UINode(id: "section", kind: .section),
        UINode(id: "navigation", kind: .navigation, children: [resolutionTextV1("content")])
    ])
    let plan = try resolutionPlanV1(root)
    let expected: [(String, UIResolvedTextRoleV1, UInt32, UIFontWeightV1, UInt32)] = [
        ("default", .body, 1088, .w400, 1408), ("headline", .headline, 1088, .w600, 1408),
        ("title", .title, 1792, .w400, 2176), ("caption", .caption, 768, .w400, 1024)
    ]
    for (id, role, size, weight, line) in expected {
        guard case let .text(text) = plan.node(for: id)?.recipe else { Issue.record("Missing text recipe"); continue }
        #expect(text.role == role && text.size64 == size && text.weight == weight && text.minimumLineBox64 == line)
        #expect(text.selectable == (id == "caption"))
        #expect(text.maximumLines == (id == "caption" ? 2 : nil))
    }
    if case let .section(header, _) = plan.node(for: "section")?.recipe { #expect(header == nil) }
    else { Issue.record("Missing section") }
    if case let .navigation(title, _, floor) = plan.node(for: "navigation")?.recipe {
        #expect(title == nil && floor == 2816)
    }
    else { Issue.record("Missing navigation") }
}

@Test func resolutionV1ExplicitSpacingAlignmentAndRTLKeepChildOrder() throws {
    let root = UINode(id: "root", kind: .vStack, properties: ["spacing": .number(0), "alignment": .string("leading")], children: [
        UINode(id: "horizontal", kind: .hStack, properties: ["spacing": .number(1.0078125), "alignment": .string("lastTextBaseline")],
            children: [resolutionTextV1("one"), resolutionTextV1("two")]),
        UINode(id: "overlay", kind: .zStack, properties: ["alignment": .string("bottomTrailing")]),
        UINode(id: "defaultVertical", kind: .vStack), UINode(id: "defaultHorizontal", kind: .hStack),
        UINode(id: "defaultOverlay", kind: .zStack)
    ])
    let rtl = UIAppearanceEnvironmentV1(scheme: .light, direction: .rightToLeft, textScale1024: 1024, density1024: 1024)
    let left = try resolutionPlanV1(root)
    let right = try resolutionPlanV1(root, environment: rtl)
    #expect(left.nodes == right.nodes)
    #expect(right.environment.direction == .rightToLeft)
    #expect(right.node(for: "horizontal")?.childIDs == ["one", "two"])
    #expect(right.node(for: "root")?.recipe == .vStack(spacing64: 0, alignment: .leading))
    #expect(right.node(for: "horizontal")?.recipe == .hStack(spacing64: 65, alignment: .lastTextBaseline))
    #expect(right.node(for: "overlay")?.recipe == .zStack(alignment: .bottomTrailing))
    #expect(right.node(for: "defaultVertical")?.recipe == .vStack(spacing64: 512, alignment: .center))
    #expect(right.node(for: "defaultHorizontal")?.recipe == .hStack(spacing64: 512, alignment: .center))
    #expect(right.node(for: "defaultOverlay")?.recipe == .zStack(alignment: .center))
}

@Test func resolutionV1AllPermittedLogicalAlignmentsResolve() throws {
    for raw in ["leading", "center", "trailing"] {
        let plan = try resolutionPlanV1(UINode(id: "v", kind: .vStack, properties: ["alignment": .string(raw)]))
        #expect(plan.node(for: "v")?.recipe == .vStack(spacing64: 512, alignment: UIHorizontalAlignmentV1(rawValue: raw)!))
    }
    for raw in ["top", "center", "bottom", "firstTextBaseline", "lastTextBaseline"] {
        let plan = try resolutionPlanV1(UINode(id: "h", kind: .hStack, properties: ["alignment": .string(raw)]))
        #expect(plan.node(for: "h")?.recipe == .hStack(spacing64: 512, alignment: UIVerticalAlignmentV1(rawValue: raw)!))
    }
    for raw in ["center", "leading", "trailing", "top", "bottom", "topLeading", "topTrailing", "bottomLeading", "bottomTrailing"] {
        let plan = try resolutionPlanV1(UINode(id: "z", kind: .zStack, properties: ["alignment": .string(raw)]))
        #expect(plan.node(for: "z")?.recipe == .zStack(alignment: UIOverlayAlignmentV1(rawValue: raw)!))
    }
}

@Test func resolutionV1InheritedDisabledClearsEphemeralStatesAndCannotBeReenabled() throws {
    let root = UINode(id: "root", kind: .vStack, properties: ["disabled": .bool(true)], children: [
        UINode(id: "nested", kind: .hStack, properties: ["disabled": .bool(false)], children: [
            resolutionButtonV1("button", role: "destructive"), resolutionToggleV1("toggle", checked: true),
            UINode(id: "field", kind: .textField, properties: ["label": .string("L"), "value": .string("V")],
                actions: [UIActionBinding(id: "change", event: .textChange)])
        ])
    ])
    let plan = try resolutionPlanV1(root)
    let theme = try resolutionThemeV1()
    for node in plan.nodes {
        #expect(node.disabled)
        let style = try #require(plan.style(nodeID: node.identity.id, pressed: true, focused: true))
        #expect(style.disabled && !style.pressed && !style.focused)
        #expect(style.pressedOverlay == nil && style.focusOutline == nil)
        #expect(style.foreground.color == theme.light.disabledText)
    }
    #expect(plan.style(nodeID: "toggle")?.toggleTrack?.color == theme.light.separator)
    #expect(plan.style(nodeID: "toggle")?.toggleThumb?.color == theme.light.toggleThumb)
    #expect(plan.style(nodeID: "field")?.placeholder?.color == theme.light.disabledText)
    #expect(plan.style(nodeID: "field")?.selection == nil && plan.style(nodeID: "field")?.caret == nil)
}

@Test func resolutionV1RolePressFocusAndNonopaquePaintKeepAlphaUnmodified() throws {
    let theme = try resolutionThemeV1()
    let accent = UIRGBA8V1(red: 11, green: 22, blue: 33, alpha: 128)
    let destructive = UIRGBA8V1(red: 44, green: 55, blue: 66, alpha: 64)
    let custom = resolutionRethemeV1(theme, light: resolutionPaletteV1(theme.light, accent: accent, destructive: destructive))
    let root = UINode(id: "root", kind: .vStack, children: [resolutionButtonV1("normal"),
        resolutionButtonV1("cancel", role: "cancel"), resolutionButtonV1("destructive", role: "destructive"),
        resolutionTextV1("text"), resolutionToggleV1("toggle", checked: true),
        UINode(id: "field", kind: .textField, properties: ["label": .string("L"), "value": .string("V")],
            actions: [UIActionBinding(id: "change", event: .textChange)])])
    let plan = try resolutionPlanV1(root, configuration: UIAppearanceConfigurationV1(id: "alpha", mode: .shared(custom)))
    for id in ["normal", "cancel", "destructive"] {
        let before = try #require(plan.node(for: id))
        let style = try #require(plan.style(nodeID: id, pressed: true, focused: true))
        let color = id == "destructive" ? destructive : accent
        #expect(style.foreground.color == color && style.foreground.opacityPermille == 1000)
        #expect(style.pressedOverlay?.color == color)
        #expect(style.pressedOverlay?.opacityPermille == 120)
        #expect(style.focusOutline?.paint.color == accent)
        #expect(style.focusOutline?.paint.opacityPermille == 1000)
        #expect(style.focusOutline?.width64 == 128 && style.focusOutline?.radius64 == 512)
        #expect(plan.node(for: id) == before)
        #expect(plan.style(nodeID: id)?.pressedOverlay == nil && plan.style(nodeID: id)?.focusOutline == nil)
    }
    #expect(plan.style(nodeID: "normal")?.background.color.alpha == 0)
    #expect(plan.style(nodeID: "field")?.selection?.color == accent)
    #expect(plan.style(nodeID: "field")?.selection?.opacityPermille == 240)
    #expect(plan.style(nodeID: "toggle")?.toggleTrack?.color == accent)
    #expect(plan.style(nodeID: "text", pressed: true, focused: true)?.pressed == false)
    #expect(plan.style(nodeID: "text", pressed: true, focused: true)?.focused == false)
    #expect(plan.node(for: "missing") == nil)
    #expect(plan.style(nodeID: "missing", pressed: true, focused: true) == nil)
}

@Test func resolutionV1FieldSelectionAndCheckedToggleColorsInBothSchemes() throws {
    let theme = try resolutionThemeV1()
    let root = UINode(id: "root", kind: .vStack, children: [resolutionToggleV1("on", checked: true),
        resolutionToggleV1("off", checked: false),
        UINode(id: "field", kind: .textField, properties: ["label": .string("L"), "value": .string("V")],
            actions: [UIActionBinding(id: "change", event: .textChange)])])
    for scheme in [UIColorSchemeV1.light, .dark] {
        let plan = try resolutionPlanV1(root, environment: UIAppearanceEnvironmentV1(scheme: scheme,
            direction: .leftToRight, textScale1024: 1024, density1024: 1024))
        let palette = scheme == .light ? theme.light : theme.dark
        #expect(plan.style(nodeID: "on")?.toggleTrack?.color == palette.accent)
        #expect(plan.style(nodeID: "off")?.toggleTrack?.color == palette.toggleOff)
        #expect(plan.style(nodeID: "on")?.toggleThumb?.color == palette.toggleThumb)
        let field = try #require(plan.style(nodeID: "field", pressed: true, focused: true))
        #expect(field.foreground.color == palette.primaryText)
        #expect(field.placeholder?.color == palette.secondaryText)
        #expect(field.caret?.color == palette.accent)
        #expect(field.selection?.color == palette.accent && field.selection?.opacityPermille == 240)
        #expect(field.border?.color == palette.separator)
        #expect(field.pressedOverlay?.color == palette.accent && field.focusOutline?.paint.color == palette.focus)
    }
}

@Test func resolutionV1SharedPlatformsMatchAndDeclaredOptInSelectsOnlyCompleteThemes() throws {
    let theme = try resolutionThemeV1()
    let root = resolutionButtonV1("button")
    let iOS = try resolutionPlanV1(root)
    let android = try resolutionPlanV1(root, platform: .android)
    #expect(iOS.nodes == android.nodes)
    #expect(iOS.style(nodeID: "button", pressed: true) == android.style(nodeID: "button", pressed: true))
    #expect(iOS.platformSpecificReason == nil && android.platformSpecificReason == nil)
    #expect(iOS.platform == .iOS && android.platform == .android)
    let custom = UIRGBA8V1(red: 1, green: 2, blue: 3, alpha: 99)
    let androidTheme = resolutionRethemeV1(theme, light: resolutionPaletteV1(theme.light, accent: custom))
    let configuration = UIAppearanceConfigurationV1(id: "explicit", mode: .platformSpecific(
        iOS: theme, android: androidTheme, reason: "Reviewed application distinction"))
    let first = try resolutionPlanV1(root, configuration: configuration, platform: .iOS)
    let second = try resolutionPlanV1(root, configuration: configuration, platform: .android)
    #expect(first.style(nodeID: "button")?.foreground.color == theme.light.accent)
    #expect(second.style(nodeID: "button")?.foreground.color == custom)
    #expect(second.platformSpecificReason == "Reviewed application distinction")
}

@Test func resolutionV1CanvasFollowsSchemeAndExplicitPlatformWithoutPremultiplyingAlpha() throws {
    let theme = try resolutionThemeV1()
    let root = resolutionTextV1("text")
    for scheme in [UIColorSchemeV1.light, .dark] {
        let environment = UIAppearanceEnvironmentV1(scheme: scheme, direction: .leftToRight,
            textScale1024: 1024, density1024: 1024)
        let iOS = try resolutionPlanV1(root, environment: environment)
        let android = try resolutionPlanV1(root, environment: environment, platform: .android)
        #expect(iOS.canvas == android.canvas)
        #expect(iOS.canvas.color == (scheme == .light ? theme.light.canvas : theme.dark.canvas))
        #expect(iOS.canvas.opacityPermille == 1000)
    }
    let first = UIRGBA8V1(red: 1, green: 2, blue: 3, alpha: 128)
    let second = UIRGBA8V1(red: 4, green: 5, blue: 6, alpha: 64)
    let iOSTheme = UIThemeV1(recipe: theme.recipe,
        light: resolutionPaletteV1(theme.light, accent: theme.light.accent, canvas: first),
        dark: resolutionPaletteV1(theme.dark, accent: theme.dark.accent, canvas: second),
        typography: theme.typography, layout: theme.layout, controls: theme.controls)
    let configuration = UIAppearanceConfigurationV1(id: "canvas", mode: .platformSpecific(
        iOS: iOSTheme, android: theme, reason: "Declared canvas distinction"))
    for scheme in [UIColorSchemeV1.light, .dark] {
        let environment = UIAppearanceEnvironmentV1(scheme: scheme, direction: .rightToLeft,
            textScale1024: 1024, density1024: 1024)
        let iOS = try resolutionPlanV1(root, configuration: configuration, environment: environment)
        let android = try resolutionPlanV1(root, configuration: configuration, environment: environment, platform: .android)
        #expect(iOS.canvas.color == (scheme == .light ? first : second))
        #expect(android.canvas.color == (scheme == .light ? theme.light.canvas : theme.dark.canvas))
        #expect(iOS.canvas.opacityPermille == 1000 && android.canvas.opacityPermille == 1000)
    }
}

@Test func resolutionV1TextScaleOnceDensityDoesNotScaleLogicalLayoutAndRowsGrow() throws {
    let root = UINode(id: "root", kind: .vStack, children: [resolutionTextV1("text"), resolutionButtonV1("button"),
        resolutionToggleV1("toggle", checked: false)])
    let scale = try UIAppearanceMetricMathV1.normalizeTextScale(4)
    let environment = UIAppearanceEnvironmentV1(scheme: .light, direction: .leftToRight,
        textScale1024: scale, density1024: 16384)
    let plan = try resolutionPlanV1(root, environment: environment)
    if case let .text(text) = plan.node(for: "text")?.recipe {
        #expect(text.size64 == 4352 && text.minimumLineBox64 == 5632)
    } else { Issue.record("Missing scaled text") }
    if case let .button(_, text, metrics, floor) = plan.node(for: "button")?.recipe {
        #expect(text.size64 == 4352 && text.minimumLineBox64 == 5632)
        #expect(metrics.minimumHeight64 == 2816 && metrics.radius64 == 512)
        #expect(floor == 5632)
    } else { Issue.record("Missing button") }
    if case let .toggle(_, _, metrics, floor) = plan.node(for: "toggle")?.recipe {
        #expect(metrics.trackWidth64 == 3264 && metrics.minimumRow64 == 2816)
        #expect(floor == 5632)
    } else { Issue.record("Missing toggle") }
    #expect(plan.node(for: "root")?.recipe == .vStack(spacing64: 512, alignment: .center))
    let lowerDensity = try resolutionPlanV1(root, environment: UIAppearanceEnvironmentV1(scheme: .light,
        direction: .leftToRight, textScale1024: scale, density1024: 128))
    #expect(plan.nodes == lowerDensity.nodes)
}

@Test func resolutionV1AggregateHeightFloorHasNoIndividualMetricCap() throws {
    let theme = try resolutionThemeV1()
    let large = UITextMetricV1(size64: 16384, weight: .w400, minimumLineBox64: 65536)
    let types = UITypographyV1(font: .systemSans, body: large, headline: theme.typography.headline,
        title: large, caption: theme.typography.caption)
    let inset = UIInsets64V1(top: 65536, leading: 0, bottom: 65536, trailing: 0)
    let controls = UIControlMetricsV1(button: UIButtonMetricsV1(labelInsets64: inset, minimumWidth64: 0,
        minimumHeight64: 0, radius64: 0), field: UIFieldMetricsV1(insets64: inset, minimumHeight64: 0, border64: 0),
        toggle: theme.controls.toggle, focusWidth64: 0, focusRadius64: 0,
        pressedOpacityPermille: 0, selectionOpacityPermille: 1000)
    let custom = resolutionRethemeV1(theme, typography: types, controls: controls)
    let environment = UIAppearanceEnvironmentV1(scheme: .light, direction: .leftToRight,
        textScale1024: 4096, density1024: 1024)
    let plan = try resolutionPlanV1(resolutionButtonV1("button"),
        configuration: UIAppearanceConfigurationV1(id: "large", mode: .shared(custom)), environment: environment)
    if case let .button(_, text, metrics, floor) = plan.node(for: "button")?.recipe {
        #expect(text.minimumLineBox64 == 262144)
        #expect(metrics.labelInsets64.top == 65536)
        #expect(floor == 393216)
    } else { Issue.record("Missing large button recipe") }
}

@Test func resolutionV1ResourceReferencesDoNotImplyFileOrCoverageVerification() throws {
    let theme = try resolutionThemeV1()
    let resources = [UIAppearanceResourceV1(id: "regular", kind: .fontSFNT, path: "does-not-exist/regular.ttf",
        sha256: String(repeating: "a", count: 64), bytes: 1, provenance: "Test descriptor metadata only",
        scale: 1, locale: "und", direction: .neutral),
        UIAppearanceResourceV1(id: "semibold", kind: .fontSFNT, path: "does-not-exist/semibold.ttf",
        sha256: String(repeating: "b", count: 64), bytes: 1, provenance: "Test descriptor metadata only",
        scale: 1, locale: "und", direction: .neutral)]
    let font = UIFontSourceV1.bundled(faces: [
        UIFontFaceV1(resourceID: "regular", postScriptName: "Fixture-Regular", weight: .w400, style: .normal),
        UIFontFaceV1(resourceID: "semibold", postScriptName: "Fixture-Semibold", weight: .w600, style: .normal)
    ], fallback: .none)
    let typography = UITypographyV1(font: font, body: theme.typography.body, headline: theme.typography.headline,
        title: theme.typography.title, caption: theme.typography.caption)
    let plan = try resolutionPlanV1(resolutionTextV1("text"), configuration: UIAppearanceConfigurationV1(id: "metadata",
        mode: .shared(resolutionRethemeV1(theme, typography: typography)), resources: resources))
    #expect(plan.resources == resources && plan.font == font)
}

@Test func resolutionV1RevalidatesUnselectedThemeAndWholeConfiguration() throws {
    let theme = try resolutionThemeV1()
    let invalidTypography = UITypographyV1(font: .systemSans,
        body: UITextMetricV1(size64: 0, weight: .w400, minimumLineBox64: 1), headline: theme.typography.headline,
        title: theme.typography.title, caption: theme.typography.caption)
    let invalid = resolutionRethemeV1(theme, typography: invalidTypography)
    for configuration in [UIAppearanceConfigurationV1(id: "", mode: .shared(theme)),
        UIAppearanceConfigurationV1(id: "bad", mode: .platformSpecific(iOS: theme, android: invalid, reason: "Complete validation")),
        UIAppearanceConfigurationV1(id: "bad", mode: .platformSpecific(iOS: invalid, android: theme, reason: "Complete validation")),
        UIAppearanceConfigurationV1(id: "bad", mode: .platformSpecific(iOS: theme, android: theme, reason: " "))] {
        #expect(throws: UIAppearanceErrorV1.self) {
            _ = try resolutionPlanV1(resolutionTextV1("text"), configuration: configuration)
        }
    }
}

@Test func resolutionV1ResourceCatalogLimitAppliesBeforePublication() throws {
    let theme = try resolutionThemeV1()
    let resources = (0..<65).map { index in
        UIAppearanceResourceV1(id: "icon\(index)", kind: .iconPNG, path: "missing/icon\(index).png",
            sha256: String(repeating: "a", count: 64), bytes: 1, provenance: "Metadata only fixture",
            scale: 1, locale: "und", direction: .neutral)
    }
    let accepted = try resolutionPlanV1(resolutionTextV1("text"), configuration:
        UIAppearanceConfigurationV1(id: "metadata", mode: .shared(theme), resources: Array(resources.prefix(64))))
    #expect(accepted.resources.count == 64)
    #expect(throws: UIAppearanceErrorV1.self) {
        _ = try resolutionPlanV1(resolutionTextV1("text"), configuration:
            UIAppearanceConfigurationV1(id: "metadata", mode: .shared(theme), resources: resources))
    }
}

@Test func resolutionV1RejectsWholeEnvironmentInsteadOfClamping() throws {
    for scale: UInt16 in [0, 511, 4097, .max] {
        #expect(throws: UIAppearanceErrorV1.number) {
            _ = try resolutionPlanV1(resolutionTextV1("text"), environment: UIAppearanceEnvironmentV1(scheme: .light,
                direction: .leftToRight, textScale1024: scale, density1024: 1024))
        }
    }
    for density: UInt16 in [0, 127, 16385, .max] {
        #expect(throws: UIAppearanceErrorV1.number) {
            _ = try resolutionPlanV1(resolutionTextV1("text"), environment: UIAppearanceEnvironmentV1(scheme: .light,
                direction: .leftToRight, textScale1024: 1024, density1024: density))
        }
    }
}

@Test func resolutionV1Standard4096BoundaryAndPermissiveSnapshotRejection() throws {
    func tree(_ count: Int) -> UINode {
        var remaining = count - 1
        var groups: [UINode] = []
        var next = 0
        while remaining > 0 {
            let children = min(999, remaining - 1)
            groups.append(UINode(id: "group\(next)", kind: .vStack,
                children: (0..<children).map { resolutionTextV1("text\(next)-\($0)") }))
            remaining -= children + 1
            next += 1
        }
        return UINode(id: "root", kind: .vStack, children: groups)
    }
    let accepted = try resolutionPlanV1(tree(4096))
    #expect(accepted.nodes.count == 4096)
    let larger = try resolutionSnapshotV1(tree(4097), limits: UIValidationLimits(maximumNodes: 8192))
    #expect(larger.nodeCount == 4097)
    #expect(throws: UIValidationError.limitExceeded("nodes")) {
        _ = try UIAppearanceResolverV1.prepare(snapshot: larger,
            configuration: UIAppearanceDescriptorCodecV1.mixerDefaultV1(), environment: resolutionEnvironmentV1, platform: .iOS)
    }
}

@Test func resolutionV1StandardDepthChildrenAndStringLimitsRechecked() throws {
    var deep = resolutionTextV1("leaf")
    for index in 0..<64 { deep = UINode(id: "deep\(index)", kind: .vStack, children: [deep]) }
    let wide = UINode(id: "wide", kind: .vStack, children: (0..<1001).map { resolutionTextV1("text\($0)") })
    let long = UINode(id: "long", kind: .text, properties: ["text": .string(String(repeating: "x", count: 16385))])
    let limits = UIValidationLimits(maximumNodes: 8192, maximumDepth: 128, maximumChildrenPerNode: 2000, maximumStringBytes: 32768)
    for (root, expected) in [(deep, "depth"), (wide, "children"), (long, "stringBytes")] {
        let snapshot = try resolutionSnapshotV1(root, limits: limits)
        #expect(throws: UIValidationError.limitExceeded(expected)) {
            _ = try UIAppearanceResolverV1.prepare(snapshot: snapshot,
                configuration: UIAppearanceDescriptorCodecV1.mixerDefaultV1(), environment: resolutionEnvironmentV1, platform: .iOS)
        }
    }
}

@Test func resolutionV1StandardAggregateContentBoundRechecked() throws {
    let root = UINode(id: "root", kind: .vStack, children: (0..<65).map { index in
        UINode(id: "text\(index)", kind: .text, properties: ["text": .string(String(repeating: "x", count: 16384))])
    })
    let snapshot = try resolutionSnapshotV1(root, limits: UIValidationLimits(maximumMessageBytes: 2_097_152))
    #expect(throws: UIValidationError.limitExceeded("contentBytes")) {
        _ = try UIAppearanceResolverV1.prepare(snapshot: snapshot,
            configuration: UIAppearanceDescriptorCodecV1.mixerDefaultV1(), environment: resolutionEnvironmentV1, platform: .iOS)
    }
}

@Test func resolutionV1DeclaredLayoutDefaultsRemainAuthoritativeUnderRTL() throws {
    let theme = try resolutionThemeV1()
    let layout = UILayoutMetricsV1(stackGap64: 123, vStackAlignment: .trailing,
        hStackAlignment: .firstTextBaseline, zStackAlignment: .topLeading,
        list: theme.layout.list, sectionHeaderInsets64: theme.layout.sectionHeaderInsets64,
        navigation: theme.layout.navigation)
    let configuration = UIAppearanceConfigurationV1(id: "customDefaults",
        mode: .shared(resolutionRethemeV1(theme, layout: layout)))
    let root = UINode(id: "root", kind: .vStack, children: [UINode(id: "h", kind: .hStack),
        UINode(id: "z", kind: .zStack), UINode(id: "explicit", kind: .vStack,
            properties: ["spacing": .number(256), "alignment": .string("center")])])
    let plan = try resolutionPlanV1(root, configuration: configuration,
        environment: UIAppearanceEnvironmentV1(scheme: .light, direction: .rightToLeft,
            textScale1024: 512, density1024: 128))
    #expect(plan.node(for: "root")?.recipe == .vStack(spacing64: 123, alignment: .trailing))
    #expect(plan.node(for: "h")?.recipe == .hStack(spacing64: 123, alignment: .firstTextBaseline))
    #expect(plan.node(for: "z")?.recipe == .zStack(alignment: .topLeading))
    #expect(plan.node(for: "explicit")?.recipe == .vStack(spacing64: 16384, alignment: .center))
}

@Test func resolutionV1FailedPreparationLeavesReconcilerAndRoutingUntouched() throws {
    var reconciler = UIReconciler()
    let root = resolutionButtonV1("button")
    try reconciler.apply(UIDocument(revision: 9, root: root))
    let snapshot = try reconciler.currentSnapshot()
    let identity = try #require(snapshot.identity(for: "button"))
    let bad = UIAppearanceEnvironmentV1(scheme: .dark, direction: .rightToLeft, textScale1024: 0, density1024: 1024)
    #expect(throws: UIAppearanceErrorV1.number) {
        _ = try UIAppearanceResolverV1.prepare(snapshot: snapshot,
            configuration: UIAppearanceDescriptorCodecV1.mixerDefaultV1(), environment: bad, platform: .android)
    }
    #expect(reconciler.snapshot?.identity(for: "button") == identity)
    #expect(reconciler.snapshot?.document.revision == 9)
    #expect(try snapshot.route(UIEventEnvelope(revision: 9, identity: identity, event: .activate)).actionID == "buttonAction")
    let first = try UIAppearanceResolverV1.prepare(snapshot: snapshot,
        configuration: UIAppearanceDescriptorCodecV1.mixerDefaultV1(), environment: resolutionEnvironmentV1, platform: .iOS)
    let changed = try UIAppearanceResolverV1.prepare(snapshot: snapshot,
        configuration: UIAppearanceDescriptorCodecV1.mixerDefaultV1(), environment: UIAppearanceEnvironmentV1(scheme: .dark,
            direction: .rightToLeft, textScale1024: 2048, density1024: 2048), platform: .iOS)
    #expect(first.revision == changed.revision && first.node(for: "button")?.identity == changed.node(for: "button")?.identity)
}
