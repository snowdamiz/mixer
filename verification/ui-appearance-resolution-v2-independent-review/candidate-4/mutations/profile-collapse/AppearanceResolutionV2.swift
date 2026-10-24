import Foundation

/// Public V2 values are untrusted, immutable data. They neither capture native
/// resources nor advertise build support, installed provenance or display authority.
public enum UIAppearancePlatformV2: String, Sendable, Equatable { case iOS, android }
public enum UIResolvedButtonRoleV2: String, Sendable, Equatable { case normal, destructive, cancel }

public struct UIAppearanceViewportV2: Sendable, Equatable {
    public let width64: UInt32
    public let height64: UInt32
    public init(width64: UInt32, height64: UInt32) {
        self.width64 = width64; self.height64 = height64
    }
}

public struct UIAppearanceAccessibilityV2: Sendable, Equatable {
    public let boldText: Bool
    public let increasedContrast: Bool
    public let reduceMotion: Bool
    public init(boldText: Bool, increasedContrast: Bool, reduceMotion: Bool) {
        self.boldText = boldText; self.increasedContrast = increasedContrast; self.reduceMotion = reduceMotion
    }
}

/// Already normalized host input, not a native capture receipt. Native ownership
/// must later enforce coherent capture and monotonic generations. No uniform
/// text scale exists: the selected profile supplies all six metrics together.
public struct UIAppearanceEnvironmentV2: Sendable, Equatable {
    public let scheme: UIColorSchemeV1
    public let direction: UILayoutDirectionV1
    public let profile: UISharedTextProfileV1
    public let density1024: UInt16
    public let viewport: UIAppearanceViewportV2
    public let safeArea64: UIInsets64V1
    public let localeIdentifier: String
    public let accessibility: UIAppearanceAccessibilityV2
    public let generation: UInt64
    public init(scheme: UIColorSchemeV1, direction: UILayoutDirectionV1, profile: UISharedTextProfileV1,
                density1024: UInt16, viewport: UIAppearanceViewportV2, safeArea64: UIInsets64V1,
                localeIdentifier: String, accessibility: UIAppearanceAccessibilityV2, generation: UInt64) {
        self.scheme = scheme; self.direction = direction; self.profile = profile
        self.density1024 = density1024; self.viewport = viewport; self.safeArea64 = safeArea64
        self.localeIdentifier = localeIdentifier; self.accessibility = accessibility; self.generation = generation
    }
}

/// The original string and exact selected metric. There is no inferred line box,
/// glyph extent, native font coverage, truncation result or shaped measurement.
public struct UIResolvedTextV2: Sendable, Equatable {
    public let value: String
    public let role: UISharedTextRoleV1
    public let metrics: UISharedTextMetricsV1
    public let selectable: Bool
    public let maximumLines: Int?
}

public struct UIResolvedRowPlacementV2: Sendable, Equatable {
    public let listIdentity: UINodeIdentity
    public let groupIndex: Int
    public let rowIndex: Int
    public let separatorAfter: Bool
}

public enum UIResolvedGroupSourceV2: Sendable, Equatable {
    case section(UINodeIdentity)
    case directRun(firstRow: UINodeIdentity)
}

/// Group records are metadata only; their source/rows reference existing snapshot
/// identities. They never create a document node, callback or event identity.
public struct UIResolvedGroupV2: Sendable, Equatable {
    public let source: UIResolvedGroupSourceV2
    public let header: UIResolvedTextV2?
    public let rowIdentities: [UINodeIdentity]
    public let visible: Bool
    public let leadingGap64: UInt32
    public let headerToRowsGap64: UInt32
    public var drawsOutline: Bool { !rowIdentities.isEmpty }
}

public struct UIResolvedListV2: Sendable, Equatable {
    public let metrics: UIGroupedListMetricsV2
    public let rowHeightFloor64: UInt32
    public let groups: [UIResolvedGroupV2]
    public let trailingPadding64: UInt32
}

public enum UIResolvedSectionContextV2: Sendable, Equatable {
    case outsideList
    case listGroup(listIdentity: UINodeIdentity, groupIndex: Int)
    /// Semantic content inside a row; receives no independent group wrappers.
    case withinListRow(listIdentity: UINodeIdentity)
}

public struct UIResolvedSectionV2: Sendable, Equatable {
    public let header: UIResolvedTextV2?
    public let context: UIResolvedSectionContextV2
    public let headerToContentGap64: UInt32
    public let contentGaps64: [UInt32]
    public let alignment: UIHorizontalAlignmentV1
}

public struct UIResolvedNavigationV2: Sendable, Equatable {
    public let expandedTitle: UIResolvedTextV2?
    public let compactTitle: UIResolvedTextV2?
    public let metrics: UINavigationMetricsV2
}

/// Logical recipes preserve child order. Native adapters must still measure
/// text/layout and separate semantic content, control visuals and hit envelopes.
/// No final row, group, navigation or raster extent is manufactured here.
public enum UIResolvedAppearanceRecipeV2: Sendable, Equatable {
    case text(UIResolvedTextV2)
    case button(role: UIResolvedButtonRoleV2, text: UIResolvedTextV2, metrics: UIButtonMetricsV2)
    case textField(label: String, value: String, text: UIResolvedTextV2, metrics: UIFieldMetricsV2)
    case toggle(text: UIResolvedTextV2, checked: Bool, metrics: UIToggleMetricsV2)
    case vStack(gaps64: [UInt32], alignment: UIHorizontalAlignmentV1)
    case hStack(gaps64: [UInt32], alignment: UIVerticalAlignmentV1)
    case zStack(alignment: UIOverlayAlignmentV1)
    case list(UIResolvedListV2)
    case section(UIResolvedSectionV2)
    case navigation(UIResolvedNavigationV2)
}

public struct UIResolvedAppearanceNodeV2: Sendable, Equatable {
    public let identity: UINodeIdentity
    public let kind: NodeKind
    public let childIDs: [String]
    public let disabled: Bool
    public let rowPlacement: UIResolvedRowPlacementV2?
    public let recipe: UIResolvedAppearanceRecipeV2
}

/// Concrete unpremultiplied RGBA8 values; authored alpha is applied exactly once.
/// Clear is an explicit paint, never permission to inherit a toolkit decoration.
public enum UIResolvedAppearancePaintsV2: Sendable, Equatable {
    case text(foreground: UIRGBA8V1, background: UIRGBA8V1)
    case container(background: UIRGBA8V1)
    case list(canvas: UIRGBA8V1, surface: UIRGBA8V1, separator: UIRGBA8V1)
    case section(header: UIRGBA8V1?, background: UIRGBA8V1)
    case navigation(expanded: UIRGBA8V1?, compact: UIRGBA8V1?, background: UIRGBA8V1)
    case button(UIButtonPaintV2, focus: UIOutlineV2?)
    case field(UIFieldPaintV2)
    case toggle(UITogglePaintV2, focus: UIOutlineV2?)
}

public struct UIResolvedAppearanceStyleV2: Sendable, Equatable {
    public let disabled: Bool
    public let pressed: Bool
    public let focused: Bool
    public let paints: UIResolvedAppearancePaintsV2
}

public struct UIResolvedAppearancePlanV2: Sendable {
    public let revision: UInt64
    public let configurationID: String
    public let recipe: UIRecipeV2
    public let canvas: UIRGBA8V1
    public let environment: UIAppearanceEnvironmentV2
    public let platform: UIAppearancePlatformV2
    public let platformSpecificReason: String?
    /// Validated references only, not captured bytes or font/coverage evidence.
    public let font: UIFontSourceV1
    public let resources: [UIAppearanceResourceV1]
    /// Exactly one record per snapshot node in immutable document preorder.
    public let nodes: [UIResolvedAppearanceNodeV2]
    private let indices: [String: Int]
    private let paints: UIPaintsV2

    fileprivate init(snapshot: UIRenderSnapshot, configuration: UIAppearanceConfigurationV2,
                     environment: UIAppearanceEnvironmentV2, platform: UIAppearancePlatformV2,
                     reason: String?, theme: UIThemeV2, nodes: [UIResolvedAppearanceNodeV2], indices: [String: Int]) {
        revision = snapshot.document.revision; configurationID = configuration.id; recipe = theme.recipe
        self.environment = environment; self.platform = platform; platformSpecificReason = reason
        font = theme.typography.font; resources = configuration.resources; self.nodes = nodes; self.indices = indices
        paints = environment.scheme == .light ? theme.light : theme.dark; canvas = paints.canvas
    }

    public func node(for nodeID: String) -> UIResolvedAppearanceNodeV2? {
        indices[nodeID].map { nodes[$0] }
    }

    /// Native ephemeral state data only. No event routing/display witness is
    /// created. Disabled dominates; fields ignore press and select editor focus.
    public func style(nodeID: String, pressed: Bool = false, focused: Bool = false) -> UIResolvedAppearanceStyleV2? {
        guard let node = node(for: nodeID) else { return nil }
        let control = node.kind == .button || node.kind == .textField || node.kind == .toggle
        let press = !node.disabled && pressed && (node.kind == .button || node.kind == .toggle)
        let focus = !node.disabled && focused && control
        let clear = UIRGBA8V1(red: 0, green: 0, blue: 0, alpha: 0)
        let resolved: UIResolvedAppearancePaintsV2
        switch node.recipe {
        case let .text(text): resolved = .text(foreground: rolePaint(text.role), background: clear)
        case let .button(role, _, _):
            let states: UIButtonStatesV2 = switch role {
            case .normal: paints.button.normal
            case .destructive: paints.button.destructive
            case .cancel: paints.button.cancel
            }
            resolved = .button(node.disabled ? states.disabled : (press ? states.pressed : states.enabled),
                focus: focus ? states.focus : nil)
        case .textField:
            resolved = .field(node.disabled ? paints.field.disabled : (focus ? paints.field.focused : paints.field.enabled))
        case let .toggle(_, checked, _):
            let states = checked ? paints.toggle.on : paints.toggle.off
            resolved = .toggle(node.disabled ? states.disabled : (press ? states.pressed : states.enabled),
                focus: focus ? states.focus : nil)
        case .list: resolved = .list(canvas: paints.canvas, surface: paints.surface, separator: paints.separator)
        case let .section(section):
            resolved = .section(header: section.header.map { rolePaint($0.role) }, background: clear)
        case let .navigation(navigation):
            resolved = .navigation(expanded: navigation.expandedTitle.map { rolePaint($0.role) },
                compact: navigation.compactTitle.map { rolePaint($0.role) }, background: paints.canvas)
        case .vStack, .hStack, .zStack: resolved = .container(background: clear)
        }
        return UIResolvedAppearanceStyleV2(disabled: node.disabled, pressed: press, focused: focus, paints: resolved)
    }

    private func rolePaint(_ role: UISharedTextRoleV1) -> UIRGBA8V1 {
        switch role {
        case .body: paints.text.body
        case .headline: paints.text.headline
        case .title: paints.text.title
        case .caption: paints.text.caption
        case .sectionHeader: paints.text.sectionHeader
        case .navigationExpanded: paints.text.navigationExpanded
        }
    }
}

public enum UIAppearanceResolverV2 {
    /// Whole descriptor, normalized environment and standard document bounds are
    /// checked before node output. This is pure data admission, not native support.
    public static func prepare(snapshot: UIRenderSnapshot, configuration: UIAppearanceConfigurationV2,
                               environment: UIAppearanceEnvironmentV2,
                               platform: UIAppearancePlatformV2) throws -> UIResolvedAppearancePlanV2 {
        try UIAppearanceDescriptorCodecV2.validate(configuration)
        try validate(environment)
        let validated = try UIValidator().validate(snapshot.document)
        guard validated.nodeCount == snapshot.nodeCount else { throw UIAppearanceErrorV2.shape }
        try preflight(snapshot)
        let theme: UIThemeV2
        let reason: String?
        switch configuration.mode {
        case let .shared(value): theme = value; reason = nil
        case let .platformSpecific(iOS, android, value):
            theme = platform == .iOS ? iOS : android; reason = value
        }
        let resolver = AppearanceDataResolverV2(snapshot: snapshot, theme: theme, profile: .l)
        let placements = try resolver.placements()
        var nodes: [UIResolvedAppearanceNodeV2] = []
        var indices: [String: Int] = [:]
        nodes.reserveCapacity(validated.nodeCount); indices.reserveCapacity(validated.nodeCount)
        var pending: [(UINode, Bool, UINodeIdentity?)] = [(snapshot.document.root, false, nil)]
        while let (node, ancestorDisabled, listAncestor) = pending.popLast() {
            guard nodes.count < UIValidationLimits.standard.maximumNodes,
                  let identity = snapshot.identity(for: node.id) else { throw UIAppearanceErrorV2.shape }
            let disabled = ancestorDisabled || node.properties["disabled"]?.bool == true
            let resolved = try resolver.recipe(node, listAncestor: listAncestor, placements: placements)
            indices[node.id] = nodes.count
            nodes.append(UIResolvedAppearanceNodeV2(identity: identity, kind: node.kind, childIDs: node.children.map(\.id),
                disabled: disabled, rowPlacement: placements.rows[node.id], recipe: resolved))
            let available = UIValidationLimits.standard.maximumNodes - nodes.count - pending.count
            guard node.children.count <= available else { throw UIAppearanceErrorV2.valueLimit }
            for child in node.children.reversed() {
                pending.append((child, disabled, node.kind == .list ? identity : listAncestor))
            }
        }
        guard nodes.count == validated.nodeCount else { throw UIAppearanceErrorV2.shape }
        return UIResolvedAppearancePlanV2(snapshot: snapshot, configuration: configuration, environment: environment,
            platform: platform, reason: reason, theme: theme, nodes: nodes, indices: indices)
    }

    private static func validate(_ environment: UIAppearanceEnvironmentV2) throws {
        _ = try UIAppearanceGeometryV2.pixelEdge(0, density1024: environment.density1024)
        let viewport = environment.viewport, safe = environment.safeArea64
        guard viewport.width64 > 0, viewport.height64 > 0,
              viewport.width64 <= UIAppearanceGeometryV2.maximumExtent64,
              viewport.height64 <= UIAppearanceGeometryV2.maximumExtent64,
              UInt64(safe.leading) + UInt64(safe.trailing) <= UInt64(viewport.width64),
              UInt64(safe.top) + UInt64(safe.bottom) <= UInt64(viewport.height64) else {
            throw UIAppearanceErrorV2.geometry
        }
        guard !environment.localeIdentifier.isEmpty, environment.localeIdentifier.utf8.count <= 128,
              !environment.localeIdentifier.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else {
            throw UIAppearanceErrorV2.shape
        }
        guard !environment.accessibility.boldText, !environment.accessibility.increasedContrast else {
            throw UIAppearanceErrorV2.unsupportedNativeOperation
        }
    }

    private static func preflight(_ snapshot: UIRenderSnapshot) throws {
        let maximum = UIValidationLimits.standard.maximumNodes
        var pending: [(UINode, Bool, Bool)] = [(snapshot.document.root, false, true)]
        var visited = 0, childReferences = 0, groups = 0, rows = 0, gaps = 0
        while let (node, insideList, root) = pending.popLast() {
            guard visited < maximum, let record = snapshot.nodes[node.id], record.node == node,
                  record.identity.id == node.id, record.identity == snapshot.identity(for: node.id) else {
                throw UIAppearanceErrorV2.shape
            }
            guard !(node.kind == .list && insideList), !(node.kind == .navigation && !root) else {
                throw UIAppearanceErrorV2.unsupportedNativeOperation
            }
            visited += 1; childReferences += node.children.count
            if node.kind == .vStack || node.kind == .hStack || node.kind == .section {
                gaps += max(0, node.children.count - 1)
            }
            if node.kind == .list {
                var inRun = false
                for child in node.children {
                    if child.kind == .section { groups += 1; rows += child.children.count; inRun = false }
                    else { if !inRun { groups += 1 }; rows += 1; inRun = true }
                }
            }
            guard childReferences < maximum, groups <= maximum, rows < maximum, gaps < maximum,
                  node.children.count <= maximum - visited - pending.count else { throw UIAppearanceErrorV2.valueLimit }
            for child in node.children.reversed() { pending.append((child, insideList || node.kind == .list, false)) }
        }
        // Explicitly admit aggregate derived references before any recipe/placement
        // output: node+child, group sources, group rows, and row placement owners.
        let references = UInt64(visited) + UInt64(childReferences) + UInt64(groups) + 2 * UInt64(rows)
        guard visited == snapshot.nodeCount, references <= UInt64(maximum) * 5 else { throw UIAppearanceErrorV2.valueLimit }
    }
}

private struct AppearancePlacementsV2 {
    var groups: [String: [UIResolvedGroupV2]] = [:]
    var sections: [String: UIResolvedSectionContextV2] = [:]
    var rows: [String: UIResolvedRowPlacementV2] = [:]
}

private struct AppearanceDataResolverV2 {
    let snapshot: UIRenderSnapshot
    let theme: UIThemeV2
    let profile: UISharedTextProfileV1

    func identity(_ node: UINode) throws -> UINodeIdentity {
        guard let identity = snapshot.identity(for: node.id) else { throw UIAppearanceErrorV2.shape }
        return identity
    }

    func text(_ value: String, _ role: UISharedTextRoleV1, selectable: Bool = false,
              maximumLines: Int? = nil) -> UIResolvedTextV2 {
        let row: UIRoleMetricsV2 = switch profile {
        case .xs: theme.typography.profiles.xs
        case .s: theme.typography.profiles.s
        case .m: theme.typography.profiles.m
        case .l: theme.typography.profiles.l
        case .xl: theme.typography.profiles.xl
        case .xxl: theme.typography.profiles.xxl
        case .xxxl: theme.typography.profiles.xxxl
        case .a1: theme.typography.profiles.a1
        case .a2: theme.typography.profiles.a2
        case .a3: theme.typography.profiles.a3
        case .a4: theme.typography.profiles.a4
        case .a5: theme.typography.profiles.a5
        }
        let metric: UISharedTextMetricsV1 = switch role {
        case .body: row.body
        case .headline: row.headline
        case .title: row.title
        case .caption: row.caption
        case .sectionHeader: row.sectionHeader
        case .navigationExpanded: row.navigationExpanded
        }
        return UIResolvedTextV2(value: value, role: role, metrics: metric, selectable: selectable, maximumLines: maximumLines)
    }

    func header(_ node: UINode) -> UIResolvedTextV2? {
        guard let title = node.properties["title"]?.string, !title.isEmpty else { return nil }
        return text(title, .sectionHeader)
    }

    func placements() throws -> AppearancePlacementsV2 {
        var result = AppearancePlacementsV2()
        var pending = [snapshot.document.root]
        while let node = pending.popLast() {
            if node.kind == .list {
                let owner = try identity(node)
                var groups: [UIResolvedGroupV2] = []
                var run: [UINode] = []
                var hasVisible = false
                func append(_ rows: [UINode], section: UINode?) throws {
                    guard let sourceNode = section ?? rows.first else { throw UIAppearanceErrorV2.shape }
                    let sourceIdentity = try identity(sourceNode)
                    let title = section.flatMap { header($0) }
                    let visible = title != nil || !rows.isEmpty
                    let gap: UInt32 = !visible ? 0 : (!hasVisible ? theme.groupedList.topPadding64 :
                        (title != nil ? theme.groupedList.groupToNextHeader64 : theme.groupedList.groupWithoutHeaderGap64))
                    let index = groups.count
                    if let section { result.sections[section.id] = .listGroup(listIdentity: owner, groupIndex: index) }
                    for (rowIndex, row) in rows.enumerated() {
                        result.rows[row.id] = UIResolvedRowPlacementV2(listIdentity: owner, groupIndex: index,
                            rowIndex: rowIndex, separatorAfter: rowIndex + 1 < rows.count)
                    }
                    groups.append(UIResolvedGroupV2(source: section != nil ? .section(sourceIdentity) : .directRun(firstRow: sourceIdentity),
                        header: title, rowIdentities: try rows.map { try identity($0) }, visible: visible,
                        leadingGap64: gap, headerToRowsGap64: title != nil && !rows.isEmpty ? theme.groupedList.headerToGroup64 : 0))
                    hasVisible = hasVisible || visible
                }
                for child in node.children {
                    if child.kind == .section {
                        if !run.isEmpty { try append(run, section: nil); run.removeAll(keepingCapacity: true) }
                        try append(child.children, section: child)
                    } else { run.append(child) }
                }
                if !run.isEmpty { try append(run, section: nil) }
                result.groups[node.id] = groups
            }
            for child in node.children.reversed() { pending.append(child) }
        }
        return result
    }

    func recipe(_ node: UINode, listAncestor: UINodeIdentity?, placements: AppearancePlacementsV2) throws -> UIResolvedAppearanceRecipeV2 {
        let label = node.properties["label"]?.string ?? ""
        switch node.kind {
        case .text:
            return .text(text(node.properties["text"]?.string ?? "", try value(node, "style", default: .body),
                selectable: node.properties["selectable"]?.bool == true,
                maximumLines: node.properties["maxLines"]?.number.map { Int($0) }))
        case .button:
            return .button(role: try value(node, "role", default: .normal), text: text(label, .body), metrics: theme.button)
        case .textField:
            let content = node.properties["value"]?.string ?? ""
            return .textField(label: label, value: content, text: text(content, .body), metrics: theme.field)
        case .toggle:
            guard let checked = node.properties["value"]?.bool else { throw UIAppearanceErrorV2.shape }
            return .toggle(text: text(label, .body), checked: checked, metrics: theme.toggle)
        case .vStack:
            let explicit = try node.properties["spacing"]?.number.map { try UIAppearanceGeometryV2.spacing64($0) }
            let gaps = node.children.indices.dropLast().map { index -> UInt32 in
                if let explicit { return explicit }
                let first = node.children[index], second = node.children[index + 1]
                let bodyCaption = first.kind == .text && second.kind == .text &&
                    (first.properties["style"]?.string ?? "body") == "body" && second.properties["style"]?.string == "caption"
                return bodyCaption ? theme.stacks.bodyCaptionGap64 : theme.stacks.defaultGap64
            }
            return .vStack(gaps64: gaps, alignment: try value(node, "alignment", default: theme.stacks.vStackAlignment))
        case .hStack:
            let gap = try node.properties["spacing"]?.number.map { try UIAppearanceGeometryV2.spacing64($0) } ?? theme.stacks.defaultGap64
            return .hStack(gaps64: Array(repeating: gap, count: max(0, node.children.count - 1)),
                alignment: try value(node, "alignment", default: theme.stacks.hStackAlignment))
        case .zStack: return .zStack(alignment: try value(node, "alignment", default: theme.stacks.zStackAlignment))
        case .list:
            guard let groups = placements.groups[node.id] else { throw UIAppearanceErrorV2.shape }
            let floors = theme.groupedList.profileFloors64
            let floor: UInt32 = switch profile {
            case .xs: floors.xs
            case .s: floors.s
            case .m: floors.m
            case .l: floors.l
            case .xl: floors.xl
            case .xxl: floors.xxl
            case .xxxl: floors.xxxl
            case .a1: floors.a1
            case .a2: floors.a2
            case .a3: floors.a3
            case .a4: floors.a4
            case .a5: floors.a5
            }
            return .list(UIResolvedListV2(metrics: theme.groupedList, rowHeightFloor64: floor, groups: groups,
                trailingPadding64: groups.contains(where: \.visible) ? theme.groupedList.bottomPadding64 : 0))
        case .section:
            let title = header(node)
            let context = placements.sections[node.id] ?? listAncestor.map { .withinListRow(listIdentity: $0) } ?? .outsideList
            // Immediate list Sections are structural; their list owns header and row
            // placement. Only semantic Sections lay out their own vertical content.
            let grouped: Bool
            if case .listGroup = context { grouped = true } else { grouped = false }
            return .section(UIResolvedSectionV2(header: title, context: context,
                headerToContentGap64: !grouped && title != nil && !node.children.isEmpty ? theme.groupedList.headerToGroup64 : 0,
                contentGaps64: grouped ? [] : Array(repeating: theme.stacks.defaultGap64, count: max(0, node.children.count - 1)),
                alignment: .leading))
        case .navigation:
            let title = node.properties["title"]?.string
            let nonempty = title.flatMap { $0.isEmpty ? nil : $0 }
            return .navigation(UIResolvedNavigationV2(expandedTitle: nonempty.map { text($0, .navigationExpanded) },
                compactTitle: nonempty.map { text($0, .headline, maximumLines: 1) }, metrics: theme.navigation))
        }
    }

    private func value<T: RawRepresentable>(_ node: UINode, _ key: String, default fallback: T) throws -> T where T.RawValue == String {
        guard let raw = node.properties[key] else { return fallback }
        guard let string = raw.string, let result = T(rawValue: string) else { throw UIAppearanceErrorV2.shape }
        return result
    }
}
