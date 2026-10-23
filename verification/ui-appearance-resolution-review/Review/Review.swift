import Foundation
import MixerUI

struct ReviewFailure: Error { let message: String }
struct Checks {
    var cases = 0
    var assertions = 0
    var groups: [[String: Any]] = []
    mutating func expect(_ condition: @autoclosure () throws -> Bool, _ detail: String,
                         line: Int = #line) throws {
        assertions += 1
        guard try condition() else { throw ReviewFailure(message: "line \(line): \(detail)") }
    }
    mutating func require<T>(_ value: T?, _ detail: String, line: Int = #line) throws -> T {
        assertions += 1
        guard let value else { throw ReviewFailure(message: "line \(line): \(detail)") }
        return value
    }
    mutating func rejects<E: Error & Equatable>(_ error: E, _ body: () throws -> Void) throws {
        cases += 1
        do { try body() }
        catch let actual as E { try expect(actual == error, "error \(actual) expected \(error)"); return }
        catch { throw ReviewFailure(message: "unexpected error \(error)") }
        throw ReviewFailure(message: "expected rejection \(error)")
    }
    mutating func rejectsAppearance(_ body: () throws -> Void) throws {
        cases += 1
        do { try body() }
        catch is UIAppearanceErrorV1 { assertions += 1; return }
        catch { throw ReviewFailure(message: "unexpected nonappearance error \(error)") }
        throw ReviewFailure(message: "expected appearance rejection")
    }
    mutating func group(_ name: String, _ work: (inout Checks) throws -> Void) throws {
        let startCases = cases, startAssertions = assertions
        try work(&self)
        let result: [String: Any] = ["group": name, "cases": cases - startCases,
                                    "assertions": assertions - startAssertions]
        groups.append(result)
        print(String(data: try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]), encoding: .utf8)!)
    }
}

func environment(_ scale: UInt16 = 1024, _ density: UInt16 = 1024,
                 _ scheme: UIColorSchemeV1 = .light, _ direction: UILayoutDirectionV1 = .leftToRight) -> UIAppearanceEnvironmentV1 {
    UIAppearanceEnvironmentV1(scheme: scheme, direction: direction, textScale1024: scale, density1024: density)
}
func snapshot(_ root: UINode, _ limits: UIValidationLimits = .standard,
              revision: UInt64 = 907) throws -> UIRenderSnapshot {
    var reconciler = UIReconciler(validator: UIValidator(limits: limits))
    try reconciler.apply(UIDocument(revision: revision, root: root))
    return try reconciler.currentSnapshot()
}
func plan(_ snapshot: UIRenderSnapshot, _ theme: UIThemeV1,
          _ env: UIAppearanceEnvironmentV1 = environment(), _ platform: UIAppearancePlatformV1 = .iOS) throws -> UIResolvedAppearancePlanV1 {
    try UIAppearanceResolverV1.prepare(snapshot: snapshot,
        configuration: UIAppearanceConfigurationV1(id: "review", mode: .shared(theme)), environment: env, platform: platform)
}
func baseTheme() throws -> UIThemeV1 {
    guard case let .shared(theme) = try UIAppearanceDescriptorCodecV1.mixerDefaultV1().mode else {
        throw ReviewFailure(message: "default was not shared")
    }
    return theme
}
func theme(_ base: UIThemeV1, light: UIPaletteV1? = nil, dark: UIPaletteV1? = nil,
           type: UITypographyV1? = nil, layout: UILayoutMetricsV1? = nil, controls: UIControlMetricsV1? = nil) -> UIThemeV1 {
    UIThemeV1(recipe: base.recipe, light: light ?? base.light, dark: dark ?? base.dark,
        typography: type ?? base.typography, layout: layout ?? base.layout, controls: controls ?? base.controls)
}
func palette(_ seed: UInt8, _ alpha: UInt8) -> UIPaletteV1 {
    func color(_ n: UInt8) -> UIRGBA8V1 {
        UIRGBA8V1(red: seed &+ n, green: seed &+ n &+ 17, blue: seed &+ n &+ 43,
                   alpha: alpha &+ n)
    }
    return UIPaletteV1(canvas: color(0), surface: color(1), primaryText: color(2), secondaryText: color(3),
        accent: color(4), destructive: color(5), disabledText: color(6), separator: color(7),
        focus: color(8), toggleOff: color(9), toggleThumb: color(10))
}
func control(_ base: UIControlMetricsV1, pressed: UInt16, selection: UInt16) -> UIControlMetricsV1 {
    UIControlMetricsV1(button: base.button, field: base.field, toggle: base.toggle,
        focusWidth64: 37, focusRadius64: 901, pressedOpacityPermille: pressed, selectionOpacityPermille: selection)
}
func text(_ id: String, _ style: String? = nil) -> UINode {
    var properties: [String: UIValue] = ["text": .string("\(id) العربية 👩🏽‍💻")]
    if let style { properties["style"] = .string(style) }
    return UINode(id: id, kind: .text, properties: properties)
}
func button(_ id: String, _ role: String = "normal", disabled: Bool = false) -> UINode {
    UINode(id: id, kind: .button, properties: ["label": .string(id), "role": .string(role), "disabled": .bool(disabled)],
        actions: [UIActionBinding(id: id + ".activate", event: .activate)])
}
func toggle(_ id: String, _ checked: Bool) -> UINode {
    UINode(id: id, kind: .toggle, properties: ["label": .string(id), "value": .bool(checked), "disabled": .bool(false)],
        actions: [UIActionBinding(id: id + ".change", event: .valueChange)])
}
func field(_ id: String) -> UINode {
    UINode(id: id, kind: .textField, properties: ["label": .string(id), "value": .string("かな")],
        actions: [UIActionBinding(id: id + ".change", event: .textChange)])
}
func everyKindTree(_ disabled: Bool) -> UINode {
    UINode(id: "navigation", kind: .navigation, properties: ["title": .string("A"), "disabled": .bool(disabled)], children: [
        UINode(id: "list", kind: .list, children: [
            UINode(id: "section", kind: .section, properties: ["title": .string("B"), "disabled": .bool(false)], children: [
                UINode(id: "v", kind: .vStack, children: [text("body"), text("head", "headline"), text("title", "title"),
                    text("caption", "caption"), button("normal"), button("cancel", "cancel"),
                    button("destructive", "destructive"), button("localDisabled", "destructive", disabled: true),
                    field("field"), toggle("on", true), toggle("off", false),
                    UINode(id: "h", kind: .hStack, children: [text("a"), text("b")]),
                    UINode(id: "z", kind: .zStack), UINode(id: "noHeader", kind: .section)])])])])
}
func preorder(_ node: UINode, inherited: Bool = false) -> [(UINode, Bool)] {
    let disabled = inherited || node.properties["disabled"]?.bool == true
    return [(node, disabled)] + node.children.flatMap { preorder($0, inherited: disabled) }
}
func assertPaint(_ value: UIAppearancePaintV1?, _ expected: UIRGBA8V1?, _ opacity: UInt16 = 1000,
                 _ label: String, _ c: inout Checks) throws {
    try c.expect(value?.color == expected, label + " color")
    try c.expect(value?.opacityPermille == (expected == nil ? nil : opacity), label + " opacity")
}

func stateMatrix(_ c: inout Checks) throws {
    let base = try baseTheme()
    let clear = UIRGBA8V1(red: 0, green: 0, blue: 0, alpha: 0)
    for alpha: UInt8 in [0, 1, 64, 127, 128, 254, 255] {
        for opacity: UInt16 in [0, 1, 499, 1000] {
            let controls = control(base.controls, pressed: opacity, selection: 1000 - opacity)
            let custom = theme(base, light: palette(13, alpha), dark: palette(139, alpha), controls: controls)
            for ancestorDisabled in [false, true] {
                let root = everyKindTree(ancestorDisabled), expected = preorder(root)
                let snap = try snapshot(root, revision: UInt64.max)
                for scheme in [UIColorSchemeV1.light, .dark] {
                    let selected = scheme == .light ? custom.light : custom.dark
                    let env = environment(1024, 128, scheme, .rightToLeft)
                    let apple = try plan(snap, custom, env, .iOS), android = try plan(snap, custom, env, .android)
                    c.cases += 1
                    try c.expect(apple.nodes == android.nodes, "shared platform node equality")
                    try c.expect(apple.nodes.map(\.identity.id) == expected.map { $0.0.id }, "exact preorder")
                    try c.expect(Set(apple.nodes.map(\.kind)) == Set(NodeKind.allCases), "all ten kinds")
                    try c.expect(apple.revision == UInt64.max && android.revision == UInt64.max, "revision exact")
                    try c.expect(apple.environment == env && android.environment == env, "environment exact")
                    try c.expect(apple.platformSpecificReason == nil && android.platformSpecificReason == nil, "no implicit platform branch")
                    try assertPaint(apple.canvas, selected.canvas, 1000, "canvas", &c)
                    try c.expect(apple.canvas == android.canvas, "shared canvas equality")
                    for (raw, disabled) in expected {
                        let record = try c.require(apple.node(for: raw.id), "record exists")
                        try c.expect(record.identity == snap.identity(for: raw.id), "identity exact")
                        try c.expect(record.childIDs == raw.children.map(\.id), "RTL order exact")
                        try c.expect(record.disabled == disabled && record.kind == raw.kind, "inherited disabled and kind")
                        for pressed in [false, true] { for focused in [false, true] {
                            c.cases += 1
                            let style = try c.require(apple.style(nodeID: raw.id, pressed: pressed, focused: focused), "style exists")
                            try c.expect(style == android.style(nodeID: raw.id, pressed: pressed, focused: focused), "shared style equality")
                            let interactive = [.button, .toggle, .textField].contains(raw.kind)
                            let p = !disabled && interactive && pressed, f = !disabled && interactive && focused
                            let roleColor = raw.properties["role"]?.string == "destructive" ? selected.destructive : selected.accent
                            let foreground = disabled ? selected.disabledText : raw.kind == .button ? roleColor : selected.primaryText
                            try c.expect(style.disabled == disabled && style.pressed == p && style.focused == f, "state flags")
                            try assertPaint(style.foreground, foreground, 1000, "foreground", &c)
                            try assertPaint(style.background, [.list, .navigation].contains(raw.kind) ? selected.canvas : clear, 1000, "background", &c)
                            try assertPaint(style.rowBackground, raw.kind == .list ? selected.surface : nil, 1000, "row", &c)
                            try assertPaint(style.separator, raw.kind == .list ? selected.separator : nil, 1000, "separator", &c)
                            try assertPaint(style.placeholder, raw.kind == .textField ? (disabled ? selected.disabledText : selected.secondaryText) : nil, 1000, "placeholder", &c)
                            try assertPaint(style.caret, raw.kind == .textField && !disabled ? selected.accent : nil, 1000, "caret", &c)
                            try assertPaint(style.selection, raw.kind == .textField && !disabled ? selected.accent : nil, 1000 - opacity, "selection", &c)
                            try assertPaint(style.border, raw.kind == .textField ? selected.separator : nil, 1000, "border", &c)
                            let track = disabled ? selected.separator : raw.properties["value"]?.bool == true ? selected.accent : selected.toggleOff
                            try assertPaint(style.toggleTrack, raw.kind == .toggle ? track : nil, 1000, "track", &c)
                            try assertPaint(style.toggleThumb, raw.kind == .toggle ? selected.toggleThumb : nil, 1000, "thumb", &c)
                            try assertPaint(style.pressedOverlay, p ? roleColor : nil, opacity, "overlay", &c)
                            try assertPaint(style.focusOutline?.paint, f ? selected.focus : nil, 1000, "focus", &c)
                            try c.expect(style.focusOutline?.width64 == (f ? 37 : nil), "focus width")
                            try c.expect(style.focusOutline?.radius64 == (f ? 901 : nil), "focus radius")
                            try c.expect(apple.node(for: raw.id) == record, "state does not mutate node")
                        }}
                    }
                    try c.expect(apple.node(for: "missing") == nil && apple.style(nodeID: "missing", pressed: true, focused: true) == nil, "missing stays nil")
                    try c.expect(snap.document.root == root, "snapshot unchanged")
                }
            }
        }
    }
}

func metricText(_ p: UIResolvedAppearancePlanV1, _ id: String) throws -> UIResolvedTextV1 {
    guard case let .text(text) = p.node(for: id)?.recipe else { throw ReviewFailure(message: "missing text \(id)") }
    return text
}
func geometryCorpus(_ c: inout Checks) throws {
    let base = try baseTheme()
    let raw: [(String, UIResolvedTextRoleV1, UITextMetricV1)] = [
        ("body", .body, UITextMetricV1(size64: 65, weight: .w700, minimumLineBox64: 127)),
        ("head", .headline, UITextMetricV1(size64: 127, weight: .w500, minimumLineBox64: 257)),
        ("title", .title, UITextMetricV1(size64: 129, weight: .w600, minimumLineBox64: 513)),
        ("caption", .caption, UITextMetricV1(size64: 64, weight: .w400, minimumLineBox64: 64))]
    let type = UITypographyV1(font: .systemSans, body: raw[0].2, headline: raw[1].2, title: raw[2].2, caption: raw[3].2)
    let custom = theme(base, type: type)
    let snap = try snapshot(everyKindTree(false))
    for scale in UInt16(512)...UInt16(4096) {
        c.cases += 1
        let p = try plan(snap, custom, environment(scale, scale % 2 == 0 ? 128 : 16384))
        for (id, role, rawType) in raw {
            let actual = try metricText(p, id)
            // Independent integer quotient/remainder oracle, not MetricMath calls.
            func expected(_ x: UInt32) -> UInt32 {
                let product = UInt64(x) * UInt64(scale)
                return UInt32(product / 1024 + (product % 1024 >= 512 ? 1 : 0))
            }
            try c.expect(actual.role == role && actual.weight == rawType.weight, "role and weight")
            try c.expect(actual.size64 == expected(rawType.size64), "size scales once ties up")
            try c.expect(actual.minimumLineBox64 == expected(rawType.minimumLineBox64), "line scales once ties up")
        }
        if case let .button(_, type, metrics, floor) = p.node(for: "normal")?.recipe {
            try c.expect(type.size64 == UInt32((65 * UInt64(scale) + 512) / 1024), "control body scaled")
            try c.expect(metrics == base.controls.button, "configured button stays unscaled")
            try c.expect(floor == max(metrics.minimumHeight64, type.minimumLineBox64 + metrics.labelInsets64.top + metrics.labelInsets64.bottom), "button derived floor")
        } else { throw ReviewFailure(message: "button recipe missing") }
    }
    let edge = UIInsets64V1(top: 65536, leading: 101, bottom: 65536, trailing: 303)
    let extremeType = UITypographyV1(font: .systemSans,
        body: UITextMetricV1(size64: 16384, weight: .w400, minimumLineBox64: 65536),
        headline: base.typography.headline, title: UITextMetricV1(size64: 16384, weight: .w700, minimumLineBox64: 65536),
        caption: base.typography.caption)
    let controls = UIControlMetricsV1(button: UIButtonMetricsV1(labelInsets64: edge, minimumWidth64: 19, minimumHeight64: 3, radius64: 7),
        field: UIFieldMetricsV1(insets64: edge, minimumHeight64: 5, border64: 0), toggle: base.controls.toggle,
        focusWidth64: 17, focusRadius64: 31, pressedOpacityPermille: 7, selectionOpacityPermille: 13)
    let layout = UILayoutMetricsV1(stackGap64: 59, vStackAlignment: .trailing, hStackAlignment: .lastTextBaseline,
        zStackAlignment: .bottomLeading, list: UIListMetricsV1(insets64: edge, minimumRow64: 11, rowGap64: 13, groupGap64: 17, separator64: 19),
        sectionHeaderInsets64: edge, navigation: UINavigationMetricsV1(titleInsets64: edge, minimumBarHeight64: 23, titleAlignment: .trailing))
    let extreme = theme(base, type: extremeType, layout: layout, controls: controls)
    for scale: UInt16 in [512, 513, 1024, 2049, 4095, 4096] {
        for density: UInt16 in [128, 1024, 16384] {
            c.cases += 1
            let p = try plan(snap, extreme, environment(scale, density, .dark, .rightToLeft), .android)
            let bodyLine = UInt32((UInt64(65536) * UInt64(scale) + 512) / 1024)
            let aggregate = bodyLine + 131072
            guard case let .button(_, _, buttonMetrics, buttonFloor) = p.node(for: "normal")?.recipe,
                  case let .textField(_, fieldMetrics, fieldFloor) = p.node(for: "field")?.recipe,
                  case let .navigation(_, navigationMetrics, navigationFloor) = p.node(for: "navigation")?.recipe,
                  case let .list(listMetrics, rowFloor) = p.node(for: "list")?.recipe,
                  case let .toggle(_, _, toggleMetrics, toggleFloor) = p.node(for: "on")?.recipe else {
                throw ReviewFailure(message: "geometry recipe missing")
            }
            try c.expect(buttonFloor == aggregate && fieldFloor == aggregate && navigationFloor == aggregate, "aggregate beyond 262144 remains valid")
            try c.expect(buttonMetrics.minimumHeight64 == 3 && fieldMetrics.minimumHeight64 == 5 && navigationMetrics.minimumBarHeight64 == 23, "configured minima distinct")
            try c.expect(buttonMetrics.labelInsets64 == edge && fieldMetrics.insets64 == edge && navigationMetrics.titleInsets64 == edge, "logical insets retain asymmetry")
            try c.expect(listMetrics == layout.list && rowFloor == bodyLine, "list floor")
            try c.expect(toggleMetrics == controls.toggle && toggleFloor == max(bodyLine, controls.toggle.minimumRow64, controls.toggle.trackHeight64), "toggle floor")
            try c.expect(p.node(for: "v")?.recipe == .vStack(spacing64: 59, alignment: .trailing), "layout remains unscaled")
            if scale == 4096 { try c.expect(aggregate == 393216, "maximum aggregate exact") }
        }
    }
    for titled in [false, true] {
        c.cases += 1
        let root = UINode(id: "nav", kind: .navigation, properties: titled ? ["title": .string("")] : [:], children: [text("t")])
        let p = try plan(snapshot(root), extreme, environment(4096))
        guard case let .navigation(title, _, floor) = p.node(for: "nav")?.recipe else { throw ReviewFailure(message: "navigation absent") }
        try c.expect((title != nil) == titled && floor == (titled ? 393216 : 23), "absent vs empty title")
    }
}

func overrideCorpus(_ c: inout Checks) throws {
    let base = try baseTheme()
    let layout = UILayoutMetricsV1(stackGap64: 601, vStackAlignment: .trailing, hStackAlignment: .lastTextBaseline,
        zStackAlignment: .topTrailing, list: base.layout.list, sectionHeaderInsets64: base.layout.sectionHeaderInsets64,
        navigation: base.layout.navigation)
    let custom = theme(base, layout: layout)
    let vectors: [(NodeKind, [String])] = [(.vStack, ["leading", "center", "trailing"]),
        (.hStack, ["top", "center", "bottom", "firstTextBaseline", "lastTextBaseline"]),
        (.zStack, ["center", "leading", "trailing", "top", "bottom", "topLeading", "topTrailing", "bottomLeading", "bottomTrailing"])]
    for (kind, alignments) in vectors { for alignment in alignments {
        for direction in [UILayoutDirectionV1.leftToRight, .rightToLeft] {
            c.cases += 1
            let root = UINode(id: "root", kind: kind, properties: ["alignment": .string(alignment)], children: [text("b"), text("a")])
            let p = try plan(snapshot(root), custom, environment(4096, 16384, .light, direction))
            let record = try c.require(p.node(for: "root"), "stack")
            try c.expect(record.childIDs == ["b", "a"], "no RTL reorder")
            switch record.recipe {
            case let .vStack(spacing, actual): try c.expect(spacing == 601 && actual.rawValue == alignment, "v alignment")
            case let .hStack(spacing, actual): try c.expect(spacing == 601 && actual.rawValue == alignment, "h alignment")
            case let .zStack(actual): try c.expect(actual.rawValue == alignment, "z alignment")
            default: throw ReviewFailure(message: "stack recipe missing")
            }
        }
    }}
    // All half-unit quantization ties plus immediate representable neighbors.
    for step in 0..<16384 {
        let tie = (Double(step) + 0.5) / 64
        for (value, expected) in [(tie, UInt32(step + 1))] {
            c.cases += 1
            let kind: NodeKind = step % 2 == 0 ? .vStack : .hStack
            let root = UINode(id: "root", kind: kind, properties: ["spacing": .number(value)])
            let p = try plan(snapshot(root), custom)
            switch p.node(for: "root")?.recipe {
            case let .vStack(actual, _), let .hStack(actual, _): try c.expect(actual == expected, "spacing exact tie")
            default: throw ReviewFailure(message: "spacing recipe missing")
            }
        }
    }
    for value in [0.0, 256.0, 1.0 / 256, 3.0 / 256, 255.999] {
        c.cases += 1
        let root = UINode(id: "root", kind: .vStack, properties: ["spacing": .number(value)])
        let p = try plan(snapshot(root), custom)
        try c.expect(p.node(for: "root")?.recipe == .vStack(spacing64: UInt32((value * 64).rounded(.toNearestOrAwayFromZero)), alignment: .trailing), "spacing edge override")
    }
}

func tree(_ count: Int) -> UINode {
    // Deepest-left branch maximizes the pending siblings frontier at its leaf.
    var remaining = count - 1, id = 0, groups: [UINode] = []
    while remaining > 0 {
        let childCount = min(999, remaining - 1)
        let groupID = "g\(id)"
        let children = (0..<childCount).map { text("t\(id)-\($0)") }
        groups.append(UINode(id: groupID, kind: .vStack, children: children))
        remaining -= 1 + childCount; id += 1
    }
    return UINode(id: "root", kind: .vStack, children: groups)
}
func boundaryCorpus(_ c: inout Checks) throws {
    let base = try baseTheme()
    let generous = UIValidationLimits(maximumMessageBytes: 4_194_304, maximumNodes: 8192, maximumDepth: 128,
        maximumChildrenPerNode: 2000, maximumStringBytes: 32768)
    for count in [1, 2, 4095, 4096] {
        c.cases += 1
        let root = tree(count), s = try snapshot(root, generous), p = try plan(s, base)
        try c.expect(p.nodes.count == count && p.nodes.map(\.identity.id) == preorder(root).map { $0.0.id }, "node bound accepted exact")
    }
    try c.rejects(UIValidationError.limitExceeded("nodes")) { _ = try plan(snapshot(tree(4097), generous), base) }
    for children in [999, 1000, 1001] {
        let root = UINode(id: "wide", kind: .hStack, children: (0..<children).map { text("w\($0)") })
        if children > 1000 { try c.rejects(UIValidationError.limitExceeded("children")) { _ = try plan(snapshot(root, generous), base) } }
        else { c.cases += 1; try c.expect(plan(snapshot(root, generous), base).nodes.count == children + 1, "child bound accepted") }
    }
    for depth in [63, 64, 65] {
        var root = text("leaf")
        for i in 1..<depth { root = UINode(id: "d\(i)", kind: .vStack, children: [root]) }
        let s = try snapshot(root, generous)
        if depth > 64 { try c.rejects(UIValidationError.limitExceeded("depth")) { _ = try plan(s, base) } }
        else { c.cases += 1; try c.expect(plan(s, base).nodes.count == depth, "depth bound accepted") }
    }
    for bytes in [16383, 16384, 16385] {
        let root = UINode(id: "t", kind: .text, properties: ["text": .string(String(repeating: "x", count: bytes))])
        let s = try snapshot(root, generous)
        if bytes > 16384 { try c.rejects(UIValidationError.limitExceeded("stringBytes")) { _ = try plan(s, base) } }
        else { c.cases += 1; try c.expect(plan(s, base).nodes.count == 1, "string bound accepted") }
    }
    // Exact content accounting: each text contributes id bytes+4+4+payload.
    let first = UINode(id: "a", kind: .text, properties: ["text": .string(String(repeating: "x", count: 16384))])
    let emptyRoot = UINode(id: "r", kind: .vStack, children: [])
    let baseBytes = emptyRoot.id.utf8.count + emptyRoot.kind.rawValue.utf8.count
    var children: [UINode] = [], used = baseBytes
    while used + 16384 + 12 <= 1_048_576 {
        let id = String(format: "%04d", children.count)
        children.append(UINode(id: id, kind: .text, properties: ["text": first.properties["text"]!]))
        used += 16384 + id.utf8.count + 8
    }
    let finalID = "last", finalPayload = 1_048_576 - used - finalID.utf8.count - 8
    for delta in [0, 1] {
        let final = UINode(id: finalID, kind: .text, properties: ["text": .string(String(repeating: "x", count: finalPayload + delta))])
        let s = try snapshot(UINode(id: "r", kind: .vStack, children: children + [final]), generous)
        if delta == 1 { try c.rejects(UIValidationError.limitExceeded("contentBytes")) { _ = try plan(s, base) } }
        else { c.cases += 1; try c.expect(plan(s, base).nodes.count == children.count + 2, "exact aggregate accepted") }
    }
    for scale: UInt16 in [0, 511, 4097, .max] {
        try c.rejects(UIAppearanceErrorV1.number) { _ = try plan(snapshot(text("t")), base, environment(scale)) }
    }
    for density: UInt16 in [0, 127, 16385, .max] {
        try c.rejects(UIAppearanceErrorV1.number) { _ = try plan(snapshot(text("t")), base, environment(1024, density)) }
    }
}

func configurationCorpus(_ c: inout Checks) throws {
    let base = try baseTheme(), s = try snapshot(button("button", "destructive"))
    let custom = theme(base, light: palette(93, 121), dark: palette(171, 233))
    let config = UIAppearanceConfigurationV1(id: "explicit", mode: .platformSpecific(iOS: base, android: custom, reason: "Review distinction"))
    for scheme in [UIColorSchemeV1.light, .dark] { for platform in [UIAppearancePlatformV1.iOS, .android] {
        c.cases += 1
        let p = try UIAppearanceResolverV1.prepare(snapshot: s, configuration: config, environment: environment(1024, 1024, scheme), platform: platform)
        let selectedTheme = platform == .iOS ? base : custom, selected = scheme == .light ? selectedTheme.light : selectedTheme.dark
        try c.expect(p.platform == platform && p.configurationID == "explicit" && p.platformSpecificReason == "Review distinction", "declared metadata")
        try assertPaint(p.canvas, selected.canvas, 1000, "declared canvas", &c)
        try assertPaint(p.style(nodeID: "button")?.foreground, selected.destructive, 1000, "declared role", &c)
    }}
    let invalidType = UITypographyV1(font: .systemSans, body: UITextMetricV1(size64: 128, weight: .w400, minimumLineBox64: 127),
        headline: base.typography.headline, title: base.typography.title, caption: base.typography.caption)
    let invalid = theme(base, type: invalidType)
    let invalidControls = UIControlMetricsV1(button: base.controls.button, field: base.controls.field, toggle: base.controls.toggle,
        focusWidth64: 1, focusRadius64: 1, pressedOpacityPermille: 1001, selectionOpacityPermille: 1000)
    let invalidLayout = UILayoutMetricsV1(stackGap64: 65537, vStackAlignment: .center, hStackAlignment: .center,
        zStackAlignment: .center, list: base.layout.list, sectionHeaderInsets64: base.layout.sectionHeaderInsets64, navigation: base.layout.navigation)
    let badThemes = [invalid, theme(base, controls: invalidControls), theme(base, layout: invalidLayout)]
    for bad in badThemes { for platform in [UIAppearancePlatformV1.iOS, .android] {
        let cfg = UIAppearanceConfigurationV1(id: "invalidUnselected", mode: .platformSpecific(
            iOS: platform == .iOS ? base : bad, android: platform == .android ? base : bad, reason: "Must validate both"))
        try c.rejectsAppearance { _ = try UIAppearanceResolverV1.prepare(snapshot: s, configuration: cfg, environment: environment(), platform: platform) }
    }}
    for reason in ["", " ", " leading", "trailing "] {
        let cfg = UIAppearanceConfigurationV1(id: "reason", mode: .platformSpecific(iOS: base, android: custom, reason: reason))
        try c.rejectsAppearance { _ = try UIAppearanceResolverV1.prepare(snapshot: s, configuration: cfg, environment: environment(), platform: .iOS) }
    }
    func resource(_ id: String, path: String? = nil, bytes: UInt32 = 1, kind: UIResourceKindV1 = .iconPNG) -> UIAppearanceResourceV1 {
        UIAppearanceResourceV1(id: id, kind: kind, path: path ?? "not-installed/\(id).bin", sha256: String(repeating: "0", count: 64),
            bytes: bytes, provenance: "Independent metadata fixture", scale: 1, locale: "und", direction: .neutral)
    }
    let resources = (0..<65).map { resource("r\($0)") }
    for count in [0, 64, 65] {
        let cfg = UIAppearanceConfigurationV1(id: "metadata", mode: .shared(base), resources: Array(resources.prefix(count)))
        if count == 65 { try c.rejectsAppearance { _ = try UIAppearanceResolverV1.prepare(snapshot: s, configuration: cfg, environment: environment(), platform: .iOS) } }
        else { c.cases += 1; let p = try UIAppearanceResolverV1.prepare(snapshot: s, configuration: cfg, environment: environment(), platform: .iOS); try c.expect(p.resources == cfg.resources, "metadata only exact") }
    }
    for entries in [[resource("a", path: "same.bin"), resource("b", path: "SAME.bin")],
        [resource("a"), resource("a")], [resource("a", path: "../escape.bin")],
        [resource("a", bytes: 0)], [resource("a", bytes: 4_194_305)]] {
        let cfg = UIAppearanceConfigurationV1(id: "resource", mode: .shared(base), resources: entries)
        try c.rejectsAppearance { _ = try UIAppearanceResolverV1.prepare(snapshot: s, configuration: cfg, environment: environment(), platform: .iOS) }
    }
    let fontResource = resource("font", kind: .fontSFNT)
    let faces = [UIFontWeightV1.w400, .w500, .w600, .w700].map {
        UIFontFaceV1(resourceID: "font", postScriptName: "Nonexistent-\($0.rawValue)", weight: $0, style: .normal)
    }
    let fontType = UITypographyV1(font: .bundled(faces: faces, fallback: .none), body: base.typography.body,
        headline: base.typography.headline, title: base.typography.title, caption: base.typography.caption)
    let fontTheme = theme(base, type: fontType)
    let fontConfig = UIAppearanceConfigurationV1(id: "font", mode: .shared(fontTheme), resources: [fontResource])
    c.cases += 1
    let fontPlan = try UIAppearanceResolverV1.prepare(snapshot: s, configuration: fontConfig, environment: environment(), platform: .android)
    try c.expect(fontPlan.font == fontType.font && fontPlan.resources == [fontResource], "nonexistent bundled font remains descriptor data")
    let broken = UIAppearanceConfigurationV1(id: "font", mode: .shared(fontTheme), resources: [])
    try c.rejects(UIAppearanceErrorV1.fontCatalog) { _ = try UIAppearanceResolverV1.prepare(snapshot: s, configuration: broken, environment: environment(), platform: .iOS) }
}

func identityCorpus(_ c: inout Checks) throws {
    let base = try baseTheme()
    var reconciler = UIReconciler()
    let start = UINode(id: "root", kind: .vStack, children: [button("survivor"), text("replace"), toggle("value", false)])
    try reconciler.apply(UIDocument(revision: 1, root: start))
    let old = try reconciler.currentSnapshot(), oldIdentity = old.identity(for: "survivor")!
    let oldPlan = try plan(old, base)
    let update = UINode(id: "root", kind: .hStack, children: [toggle("value", true), button("replace"), button("survivor")])
    try reconciler.apply(UIDocument(revision: UInt64.max, root: update))
    let current = try reconciler.currentSnapshot(), survivor = current.identity(for: "survivor")!
    for i in 0..<64 {
        c.cases += 1
        let p = try plan(current, base, environment(i % 2 == 0 ? 512 : 4096, i % 3 == 0 ? 128 : 16384,
            i % 2 == 0 ? .dark : .light, i % 3 == 0 ? .rightToLeft : .leftToRight), i % 2 == 0 ? .iOS : .android)
        try c.expect(p.revision == UInt64.max && p.node(for: "survivor")?.identity == oldIdentity && survivor == oldIdentity, "survivor identity across reorders/environment")
        try c.expect(p.node(for: "replace")?.identity != old.identity(for: "replace"), "kind replacement identity")
        try c.expect(p.node(for: "root")?.identity != old.identity(for: "root"), "root kind replacement identity")
        try c.expect(p.node(for: "root")?.childIDs == ["value", "replace", "survivor"], "new order exact")
        try c.expect(oldPlan.revision == 1 && oldPlan.node(for: "root")?.childIDs == ["survivor", "replace", "value"], "old immutable plan independent")
        guard case let .toggle(_, checked, _, _) = p.node(for: "value")?.recipe else { throw ReviewFailure(message: "toggle value") }
        try c.expect(checked, "new snapshot checked state")
        try c.expect(current.document.root == update && reconciler.snapshot?.document.root == update, "reconciler unchanged by resolution")
        try c.expect(current.route(UIEventEnvelope(revision: UInt64.max, identity: survivor, event: .activate)).actionID == "survivor.activate", "routing unchanged")
        try c.rejects(UIAppearanceErrorV1.number) { _ = try plan(current, base, environment(0)) }
        try c.expect(reconciler.snapshot?.identity(for: "survivor") == survivor && reconciler.snapshot?.document.revision == UInt64.max, "failed resolution preserves reconciliation")
    }
    try c.rejects(UIRoutingError.staleRevision) { _ = try current.route(UIEventEnvelope(revision: 1, identity: oldIdentity, event: .activate)) }
    try c.rejects(UIRoutingError.staleIdentity) { _ = try current.route(UIEventEnvelope(revision: UInt64.max, identity: old.identity(for: "replace")!, event: .activate)) }
}

@main struct Review {
    static func main() throws {
        var checks = Checks()
        try checks.group("distinct-palette-state-matrix", stateMatrix)
        try checks.group("exhaustive-normalized-scale-and-aggregate-geometry", geometryCorpus)
        try checks.group("logical-overrides-and-all-spacing-ties", overrideCorpus)
        try checks.group("standard-tree-and-environment-boundaries", boundaryCorpus)
        try checks.group("whole-configuration-and-resource-metadata", configurationCorpus)
        try checks.group("reconciliation-identity-and-routing-preservation", identityCorpus)
        let output: [String: Any] = ["status": "passed", "cases": checks.cases, "assertions": checks.assertions, "groups": checks.groups]
        print("REVIEW_RESULT " + String(data: try JSONSerialization.data(withJSONObject: output, options: [.sortedKeys]), encoding: .utf8)!)
    }
}
