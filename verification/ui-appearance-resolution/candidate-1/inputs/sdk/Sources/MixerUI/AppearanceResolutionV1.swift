/// Pure appearance data. This file does not install resources, advertise renderer
/// support, mutate a reconciler, or establish presentation/release authority.
public enum UIAppearancePlatformV1: String, Sendable, Equatable {
    case iOS, android
}

public enum UIResolvedTextRoleV1: String, Sendable, Equatable {
    case body, headline, title, caption
}

public enum UIResolvedButtonRoleV1: String, Sendable, Equatable {
    case normal, destructive, cancel
}

/// Unpremultiplied sRGB color plus ONE additional opacity modulation. A consumer
/// applies color.alpha / 255 * opacityPermille / 1000 exactly once; color.alpha
/// has not already been multiplied by opacityPermille.
public struct UIAppearancePaintV1: Sendable, Equatable {
    public let color: UIRGBA8V1
    public let opacityPermille: UInt16
}

public struct UIResolvedTextV1: Sendable, Equatable {
    public let role: UIResolvedTextRoleV1
    public let size64: UInt32
    public let weight: UIFontWeightV1
    public let minimumLineBox64: UInt32
    public let selectable: Bool
    public let maximumLines: Int?
}

/// Values remain logical units and leading/trailing remain logical. Direction is
/// carried by the plan; consumers map these values at their native layout edge.
/// Height floors are aggregate lower bounds, never fixed heights or text shaping
/// measurements; native rows must grow further when content requires it. Aggregate
/// extents may exceed the individual-metric range of MetricMath.pixels.
/// These cases describe recipes, not a native adapter's implemented support set.
public enum UIResolvedAppearanceRecipeV1: Sendable, Equatable {
    case text(UIResolvedTextV1)
    case button(role: UIResolvedButtonRoleV1, text: UIResolvedTextV1,
                metrics: UIButtonMetricsV1, contentHeightFloor64: UInt32)
    case textField(text: UIResolvedTextV1, metrics: UIFieldMetricsV1, contentHeightFloor64: UInt32)
    case toggle(text: UIResolvedTextV1, checked: Bool, metrics: UIToggleMetricsV1, contentHeightFloor64: UInt32)
    case vStack(spacing64: UInt32, alignment: UIHorizontalAlignmentV1)
    case hStack(spacing64: UInt32, alignment: UIVerticalAlignmentV1)
    case zStack(alignment: UIOverlayAlignmentV1)
    case list(metrics: UIListMetricsV1, rowHeightFloor64: UInt32)
    case section(header: UIResolvedTextV1?, headerInsets64: UIInsets64V1)
    case navigation(title: UIResolvedTextV1?, metrics: UINavigationMetricsV1, barHeightFloor64: UInt32)
}

public struct UIResolvedAppearanceNodeV1: Sendable, Equatable {
    public let identity: UINodeIdentity
    public let kind: NodeKind
    public let disabled: Bool
    /// Original document order, including under RTL. No child order is inferred.
    public let childIDs: [String]
    public let recipe: UIResolvedAppearanceRecipeV1
}

public struct UIAppearanceFocusOutlineV1: Sendable, Equatable {
    public let paint: UIAppearancePaintV1
    public let width64: UInt32
    public let radius64: UInt32
}

/// State decoration never changes recipe geometry or identity. Optional fields
/// exist only for the corresponding control/collection, never as a fallback.
public struct UIResolvedAppearanceStyleV1: Sendable, Equatable {
    public let disabled: Bool
    public let pressed: Bool
    public let focused: Bool
    public let foreground: UIAppearancePaintV1
    public let background: UIAppearancePaintV1
    public let rowBackground: UIAppearancePaintV1?
    public let separator: UIAppearancePaintV1?
    public let placeholder: UIAppearancePaintV1?
    public let caret: UIAppearancePaintV1?
    public let selection: UIAppearancePaintV1?
    public let border: UIAppearancePaintV1?
    public let toggleTrack: UIAppearancePaintV1?
    public let toggleThumb: UIAppearancePaintV1?
    public let pressedOverlay: UIAppearancePaintV1?
    public let focusOutline: UIAppearanceFocusOutlineV1?
}

/// Bounded immutable data only. `resources` and `font` are validated descriptor
/// references, NOT captured bytes, file/digest/font coverage checks or provenance.
public struct UIResolvedAppearancePlanV1: Sendable {
    public let revision: UInt64
    public let configurationID: String
    public let recipe: UIRecipeV1
    public let environment: UIAppearanceEnvironmentV1
    public let platform: UIAppearancePlatformV1
    public let platformSpecificReason: String?
    public let font: UIFontSourceV1
    public let resources: [UIAppearanceResourceV1]
    /// Exactly one record per node, in document preorder, at most 4096 records.
    public let nodes: [UIResolvedAppearanceNodeV1]
    private let indices: [String: Int]
    private let palette: UIPaletteV1
    private let controls: UIControlMetricsV1

    fileprivate init(snapshot: UIRenderSnapshot, configuration: UIAppearanceConfigurationV1,
                     environment: UIAppearanceEnvironmentV1, platform: UIAppearancePlatformV1,
                     reason: String?, theme: UIThemeV1, palette: UIPaletteV1,
                     nodes: [UIResolvedAppearanceNodeV1], indices: [String: Int]) {
        revision = snapshot.document.revision
        configurationID = configuration.id
        recipe = theme.recipe
        self.environment = environment
        self.platform = platform
        platformSpecificReason = reason
        font = theme.typography.font
        resources = configuration.resources
        self.nodes = nodes
        self.indices = indices
        self.palette = palette
        controls = theme.controls
    }

    public func node(for nodeID: String) -> UIResolvedAppearanceNodeV1? {
        guard let index = indices[nodeID] else { return nil }
        return nodes[index]
    }

    /// Press/focus are native ephemeral input data, not an event or a display
    /// witness. Disabled ancestors clear both; non-controls ignore both.
    public func style(nodeID: String, pressed: Bool = false, focused: Bool = false) -> UIResolvedAppearanceStyleV1? {
        guard let node = node(for: nodeID) else { return nil }
        let interactive = node.kind == .button || node.kind == .textField || node.kind == .toggle
        let pressed = interactive && !node.disabled && pressed
        let focused = interactive && !node.disabled && focused
        let field = node.kind == .textField
        let list = node.kind == .list
        let toggle = node.kind == .toggle
        var roleColor = palette.accent
        if case let .button(role, _, _, _) = node.recipe, role == .destructive {
            roleColor = palette.destructive
        }
        let foreground = node.disabled ? palette.disabledText : (node.kind == .button ? roleColor : palette.primaryText)
        var track: UIRGBA8V1?
        if case let .toggle(_, checked, _, _) = node.recipe {
            track = node.disabled ? palette.separator : (checked ? palette.accent : palette.toggleOff)
        }
        let clear = UIRGBA8V1(red: 0, green: 0, blue: 0, alpha: 0)
        let outline = focused ? UIAppearanceFocusOutlineV1(paint: paint(palette.focus),
            width64: controls.focusWidth64, radius64: controls.focusRadius64) : nil
        return UIResolvedAppearanceStyleV1(disabled: node.disabled, pressed: pressed, focused: focused,
            foreground: paint(foreground), background: paint(list || node.kind == .navigation ? palette.canvas : clear),
            rowBackground: list ? paint(palette.surface) : nil, separator: list ? paint(palette.separator) : nil,
            placeholder: field ? paint(node.disabled ? palette.disabledText : palette.secondaryText) : nil,
            caret: field && !node.disabled ? paint(palette.accent) : nil,
            selection: field && !node.disabled ? paint(palette.accent, opacity: controls.selectionOpacityPermille) : nil,
            border: field ? paint(palette.separator) : nil,
            toggleTrack: track.map { paint($0) }, toggleThumb: toggle ? paint(palette.toggleThumb) : nil,
            pressedOverlay: pressed ? paint(roleColor, opacity: controls.pressedOpacityPermille) : nil,
            focusOutline: outline)
    }

    private func paint(_ color: UIRGBA8V1, opacity: UInt16 = 1000) -> UIAppearancePaintV1 {
        UIAppearancePaintV1(color: color, opacityPermille: opacity)
    }
}

public enum UIAppearanceResolverV1 {
    /// Revalidates the WHOLE raw configuration, normalized environment and
    /// standard UI document before allocating per-node output. A snapshot made
    /// with more permissive custom UI limits is not admitted by that fact alone.
    public static func prepare(snapshot: UIRenderSnapshot, configuration: UIAppearanceConfigurationV1,
                               environment: UIAppearanceEnvironmentV1,
                               platform: UIAppearancePlatformV1) throws -> UIResolvedAppearancePlanV1 {
        try UIAppearanceDescriptorCodecV1.validate(configuration)
        _ = try UIAppearanceMetricMathV1.scaled64(0, textScale1024: environment.textScale1024)
        _ = try UIAppearanceMetricMathV1.pixels(0, density1024: environment.density1024)
        let validated = try UIValidator().validate(snapshot.document)
        guard validated.nodeCount == snapshot.nodeCount else { throw UIAppearanceErrorV1.shape }

        let theme: UIThemeV1
        let reason: String?
        switch configuration.mode {
        case let .shared(shared): theme = shared; reason = nil
        case let .platformSpecific(iOS, android, declaredReason):
            theme = platform == .iOS ? iOS : android
            reason = declaredReason
        }
        let palette = environment.scheme == .light ? theme.light : theme.dark
        let types = try AppearanceResolvedTypesV1(theme.typography, scale: environment.textScale1024)
        // All derived geometry is admitted before any per-node record is retained.
        let heights = try AppearanceResolvedHeightsV1(theme: theme, types: types)
        var nodes: [UIResolvedAppearanceNodeV1] = []
        var indices: [String: Int] = [:]
        nodes.reserveCapacity(validated.nodeCount)
        indices.reserveCapacity(validated.nodeCount)
        var pending: [(UINode, Bool)] = [(snapshot.document.root, false)]
        while let (node, ancestorDisabled) = pending.popLast() {
            guard nodes.count < UIValidationLimits.standard.maximumNodes,
                  let identity = snapshot.identity(for: node.id) else { throw UIAppearanceErrorV1.shape }
            let disabled = ancestorDisabled || node.properties["disabled"]?.bool == true
            let recipe = try resolve(node, theme: theme, types: types, heights: heights)
            indices[node.id] = nodes.count
            nodes.append(UIResolvedAppearanceNodeV1(identity: identity, kind: node.kind, disabled: disabled,
                childIDs: node.children.map(\.id), recipe: recipe))
            // Admit the entire frontier before retaining children, even though
            // standard validation already established this same bound.
            let available = UIValidationLimits.standard.maximumNodes - nodes.count - pending.count
            guard node.children.count <= available else { throw UIAppearanceErrorV1.valueLimit }
            for child in node.children.reversed() { pending.append((child, disabled)) }
        }
        return UIResolvedAppearancePlanV1(snapshot: snapshot, configuration: configuration,
            environment: environment, platform: platform, reason: reason, theme: theme, palette: palette,
            nodes: nodes, indices: indices)
    }

    private static func resolve(_ node: UINode, theme: UIThemeV1, types: AppearanceResolvedTypesV1,
                                heights: AppearanceResolvedHeightsV1) throws -> UIResolvedAppearanceRecipeV1 {
        switch node.kind {
        case .text:
            let role: UIResolvedTextRoleV1 = try value(node, "style", default: .body)
            return .text(types.text(role, selectable: node.properties["selectable"]?.bool == true,
                maximumLines: node.properties["maxLines"]?.number.map { Int($0) }))
        case .button:
            return .button(role: try value(node, "role", default: .normal), text: types.text(.body),
                metrics: theme.controls.button, contentHeightFloor64: heights.button)
        case .textField:
            return .textField(text: types.text(.body), metrics: theme.controls.field, contentHeightFloor64: heights.field)
        case .toggle:
            guard let checked = node.properties["value"]?.bool else { throw UIAppearanceErrorV1.shape }
            return .toggle(text: types.text(.body), checked: checked,
                metrics: theme.controls.toggle, contentHeightFloor64: heights.toggle)
        case .vStack:
            return .vStack(spacing64: try spacing(node, theme: theme),
                alignment: try value(node, "alignment", default: theme.layout.vStackAlignment))
        case .hStack:
            return .hStack(spacing64: try spacing(node, theme: theme),
                alignment: try value(node, "alignment", default: theme.layout.hStackAlignment))
        case .zStack:
            return .zStack(alignment: try value(node, "alignment", default: theme.layout.zStackAlignment))
        case .list:
            return .list(metrics: theme.layout.list, rowHeightFloor64: heights.row)
        case .section:
            return .section(header: node.properties["title"] == nil ? nil : types.text(.caption),
                headerInsets64: theme.layout.sectionHeaderInsets64)
        case .navigation:
            return .navigation(title: node.properties["title"] == nil ? nil : types.text(.title),
                metrics: theme.layout.navigation, barHeightFloor64: node.properties["title"] == nil
                    ? theme.layout.navigation.minimumBarHeight64 : heights.navigation)
        }
    }

    private static func value<T: RawRepresentable>(_ node: UINode, _ key: String, default fallback: T) throws -> T
        where T.RawValue == String {
        guard let raw = node.properties[key] else { return fallback }
        guard let string = raw.string, let value = T(rawValue: string) else { throw UIAppearanceErrorV1.shape }
        return value
    }

    private static func spacing(_ node: UINode, theme: UIThemeV1) throws -> UInt32 {
        guard let raw = node.properties["spacing"] else { return theme.layout.stackGap64 }
        guard let number = raw.number else { throw UIAppearanceErrorV1.shape }
        return try UIAppearanceMetricMathV1.spacing64(number)
    }
}

private struct AppearanceResolvedTypesV1 {
    let body, headline, title, caption: UITextMetricV1

    init(_ typography: UITypographyV1, scale: UInt16) throws {
        func scaled(_ metric: UITextMetricV1) throws -> UITextMetricV1 {
            UITextMetricV1(size64: try UIAppearanceMetricMathV1.scaled64(metric.size64, textScale1024: scale),
                weight: metric.weight,
                minimumLineBox64: try UIAppearanceMetricMathV1.scaled64(metric.minimumLineBox64, textScale1024: scale))
        }
        body = try scaled(typography.body)
        headline = try scaled(typography.headline)
        title = try scaled(typography.title)
        caption = try scaled(typography.caption)
    }

    func text(_ role: UIResolvedTextRoleV1, selectable: Bool = false, maximumLines: Int? = nil) -> UIResolvedTextV1 {
        let metric: UITextMetricV1 = switch role {
        case .body: body
        case .headline: headline
        case .title: title
        case .caption: caption
        }
        return UIResolvedTextV1(role: role, size64: metric.size64, weight: metric.weight,
            minimumLineBox64: metric.minimumLineBox64, selectable: selectable, maximumLines: maximumLines)
    }
}

private struct AppearanceResolvedHeightsV1 {
    let button, field, toggle, row, navigation: UInt32

    init(theme: UIThemeV1, types: AppearanceResolvedTypesV1) throws {
        func height(_ floor: UInt32, _ line: UInt32, _ insets: UIInsets64V1) throws -> UInt32 {
            let content = UInt64(line) + UInt64(insets.top) + UInt64(insets.bottom)
            guard content <= UInt64(UInt32.max) else { throw UIAppearanceErrorV1.geometry }
            return max(floor, UInt32(content))
        }
        button = try height(theme.controls.button.minimumHeight64, types.body.minimumLineBox64,
            theme.controls.button.labelInsets64)
        field = try height(theme.controls.field.minimumHeight64, types.body.minimumLineBox64, theme.controls.field.insets64)
        toggle = max(theme.controls.toggle.minimumRow64, theme.controls.toggle.trackHeight64, types.body.minimumLineBox64)
        row = max(theme.layout.list.minimumRow64, types.body.minimumLineBox64)
        navigation = try height(theme.layout.navigation.minimumBarHeight64, types.title.minimumLineBox64,
            theme.layout.navigation.titleInsets64)
    }
}
