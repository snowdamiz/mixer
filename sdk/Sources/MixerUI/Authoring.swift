public protocol MixerView: Sendable {
    var uiNode: UINode { get }
}

@resultBuilder
public enum MixerViewBuilder {
    public static func buildExpression<V: MixerView>(_ expression: V) -> [UINode] { [expression.uiNode] }
    public static func buildBlock(_ components: [UINode]...) -> [UINode] { components.flatMap { $0 } }
    public static func buildOptional(_ component: [UINode]?) -> [UINode] { component ?? [] }
    public static func buildEither(first: [UINode]) -> [UINode] { first }
    public static func buildEither(second: [UINode]) -> [UINode] { second }
    public static func buildArray(_ components: [[UINode]]) -> [UINode] { components.flatMap { $0 } }
    public static func buildLimitedAvailability(_ component: [UINode]) -> [UINode] { component }
}

public struct ModifiedMixerView: MixerView {
    public let uiNode: UINode
}

extension MixerView {
    private func setting(_ key: String, _ value: UIValue) -> ModifiedMixerView {
        var node = uiNode; node.properties[key] = value
        return ModifiedMixerView(uiNode: node)
    }

    public func accessibilityLabel(_ label: String) -> ModifiedMixerView { setting("accessibilityLabel", .string(label)) }
    public func accessibilityHint(_ hint: String) -> ModifiedMixerView { setting("accessibilityHint", .string(hint)) }
    public func accessibilityValue(_ value: String) -> ModifiedMixerView { setting("accessibilityValue", .string(value)) }
    public func accessibilityIdentifier(_ id: String) -> ModifiedMixerView { setting("accessibilityIdentifier", .string(id)) }
    public func disabled(_ disabled: Bool = true) -> ModifiedMixerView { setting("disabled", .bool(disabled)) }

    public func document(revision: UInt64) -> UIDocument { UIDocument(revision: revision, root: uiNode) }
}

public enum TextStyle: String, Sendable { case body, headline, title, caption }

public struct Text: MixerView {
    public let uiNode: UINode
    public init(_ id: String, _ text: String, style: TextStyle = .body,
                selectable: Bool = false, maximumLines: Int? = nil) {
        var properties: [String: UIValue] = ["text": .string(text), "style": .string(style.rawValue), "selectable": .bool(selectable)]
        if let maximumLines { properties["maxLines"] = .number(Double(maximumLines)) }
        uiNode = UINode(id: id, kind: .text, properties: properties)
    }
}

public enum ButtonRole: String, Sendable { case normal, destructive, cancel }

public struct Button: MixerView {
    public let uiNode: UINode
    public init(_ id: String, _ label: String, action: String, role: ButtonRole = .normal) {
        uiNode = UINode(id: id, kind: .button, properties: ["label": .string(label), "role": .string(role.rawValue)],
                        actions: [UIActionBinding(id: action, event: .activate)])
    }
}

public enum TextFieldAxis: String, CaseIterable, Hashable, Sendable { case horizontal, vertical }

/// Bindings are explicit values plus action IDs; they never serialize a Swift closure.
/// Vertical fields require an adapter that explicitly admits that axis.
public struct TextField: MixerView {
    public let uiNode: UINode
    public init(_ id: String, _ label: String, value: String, action: String,
                onSubmit: String? = nil, axis: TextFieldAxis = .horizontal) {
        var actions = [UIActionBinding(id: action, event: .textChange)]
        if let onSubmit { actions.append(UIActionBinding(id: onSubmit, event: .submit)) }
        var properties: [String: UIValue] = ["label": .string(label), "value": .string(value)]
        // Preserve the existing schema-1 wire shape for the default field.
        if axis != .horizontal { properties["axis"] = .string(axis.rawValue) }
        uiNode = UINode(id: id, kind: .textField, properties: properties, actions: actions)
    }
}

public struct Toggle: MixerView {
    public let uiNode: UINode
    public init(_ id: String, _ label: String, value: Bool, action: String) {
        uiNode = UINode(id: id, kind: .toggle, properties: ["label": .string(label), "value": .bool(value)],
                        actions: [UIActionBinding(id: action, event: .valueChange)])
    }
}

public enum StackHorizontalAlignment: String, Sendable { case leading, center, trailing }
public enum StackVerticalAlignment: String, Sendable { case top, center, bottom, firstTextBaseline, lastTextBaseline }
public enum StackAlignment: String, Sendable {
    case center, leading, trailing, top, bottom, topLeading, topTrailing, bottomLeading, bottomTrailing
}

public struct VStack: MixerView {
    public let uiNode: UINode
    public init(_ id: String, alignment: StackHorizontalAlignment = .center, spacing: Double = 8,
                @MixerViewBuilder content: () -> [UINode]) {
        uiNode = UINode(id: id, kind: .vStack, properties: ["spacing": .number(spacing), "alignment": .string(alignment.rawValue)], children: content())
    }
}

public struct HStack: MixerView {
    public let uiNode: UINode
    public init(_ id: String, alignment: StackVerticalAlignment = .center, spacing: Double = 8,
                @MixerViewBuilder content: () -> [UINode]) {
        uiNode = UINode(id: id, kind: .hStack, properties: ["spacing": .number(spacing), "alignment": .string(alignment.rawValue)], children: content())
    }
}

public struct ZStack: MixerView {
    public let uiNode: UINode
    public init(_ id: String, alignment: StackAlignment = .center, @MixerViewBuilder content: () -> [UINode]) {
        uiNode = UINode(id: id, kind: .zStack, properties: ["alignment": .string(alignment.rawValue)], children: content())
    }
}

public struct List: MixerView {
    public let uiNode: UINode
    public init(_ id: String, @MixerViewBuilder content: () -> [UINode]) {
        uiNode = UINode(id: id, kind: .list, children: content())
    }
}

public struct Section: MixerView {
    public let uiNode: UINode
    public init(_ id: String, title: String? = nil, @MixerViewBuilder content: () -> [UINode]) {
        uiNode = UINode(id: id, kind: .section, properties: title.map { ["title": .string($0)] } ?? [:], children: content())
    }
}

/// This initial navigation container hosts exactly one root. Route destinations,
/// interactive back and sheets are not yet part of the version-1 UI surface.
public struct Navigation: MixerView {
    public let uiNode: UINode
    public init(_ id: String, title: String? = nil, @MixerViewBuilder content: () -> [UINode]) {
        uiNode = UINode(id: id, kind: .navigation, properties: title.map { ["title": .string($0)] } ?? [:], children: content())
    }
}
