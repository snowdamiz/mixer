import Foundation

public protocol View {
    associatedtype Body: View

    @ViewBuilder var body: Body { get }
}

extension View where Body == Never {
    public var body: Never { fatalError("A primitive view has no body") }
}

extension View {
    /// Binds the view's identity to an `Int` or `String` key within its parent.
    /// Evaluation rejects other key types and strings over 256 UTF-8 bytes.
    public func id<ID: Hashable>(_ id: ID) -> some View {
        IdentifiedView(content: self, id: id)
    }

    /// Disables interaction throughout this view. A descendant cannot override a disabled ancestor.
    public func disabled(_ disabled: Bool) -> some View {
        NodeModifiedView(content: self, modifier: .disabled(disabled))
    }

    /// Sets a verbatim label on a view that renders exactly one Text, Button, TextField, or Toggle.
    /// Evaluation rejects ambiguous targets and multiple labels on the same node.
    public func accessibilityLabel(_ label: String) -> some View {
        NodeModifiedView(content: self, modifier: .accessibilityLabel(label))
    }

    /// Sets a verbatim hint on a view that renders exactly one Text, Button, TextField, or Toggle.
    /// Evaluation rejects ambiguous targets and multiple hints on the same node.
    public func accessibilityHint(_ hint: String) -> some View {
        NodeModifiedView(content: self, modifier: .accessibilityHint(hint))
    }
}

enum NodeModifier {
    case disabled(Bool)
    case accessibilityLabel(String)
    case accessibilityHint(String)
}

struct NodeModifiedView<Content: View>: View {
    typealias Body = Never
    let content: Content
    let modifier: NodeModifier
}

struct IdentifiedView<Content: View, ID: Hashable>: View {
    typealias Body = Never
    let content: Content
    let id: ID
}

extension Never: View {
    public typealias Body = Never
}

@resultBuilder
public enum ViewBuilder {
    public static func buildBlock<Content: View>(_ content: Content) -> Content {
        content
    }

    public static func buildBlock(_ children: any View...) -> ViewGroup {
        ViewGroup(children: children)
    }

    public static func buildOptional<Content: View>(_ content: Content?) -> OptionalContent<Content> {
        OptionalContent(content: content)
    }

    public static func buildEither<First: View, Second: View>(
        first: First
    ) -> ConditionalContent<First, Second> {
        .first(first)
    }

    public static func buildEither<First: View, Second: View>(
        second: Second
    ) -> ConditionalContent<First, Second> {
        .second(second)
    }

    public struct ViewGroup: View {
        public typealias Body = Never
        let children: [any View]
    }

    public struct OptionalContent<Content: View>: View {
        public typealias Body = Never
        let content: Content?
    }

    public enum ConditionalContent<First: View, Second: View>: View {
        public typealias Body = Never
        case first(First)
        case second(Second)
    }
}

public struct Text: View {
    public typealias Body = Never
    let title: String

    public init(_ title: String) {
        self.title = title
    }
}

public struct VStack<Content: View>: View {
    public typealias Body = Never
    let content: Content

    public init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }
}

public struct VerticalAlignment: Equatable, Sendable {
    public static let top = Self("top")
    public static let center = Self("center")
    public static let bottom = Self("bottom")

    let wireValue: String

    private init(_ wireValue: String) {
        self.wireValue = wireValue
    }
}

public struct HStack<Content: View>: View {
    public typealias Body = Never
    let alignment: VerticalAlignment
    let spacing: CGFloat?
    let content: Content

    public init(
        alignment: VerticalAlignment = .center, spacing: CGFloat? = nil, @ViewBuilder content: () -> Content
    ) {
        self.alignment = alignment
        self.spacing = spacing
        self.content = content()
    }
}

public struct List<Content: View>: View {
    public typealias Body = Never
    let content: Content

    public init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }
}

public struct Section<Content: View>: View {
    public typealias Body = Never
    let title: String?
    let content: Content

    public init(@ViewBuilder content: () -> Content) {
        title = nil
        self.content = content()
    }

    public init(_ title: String, @ViewBuilder content: () -> Content) {
        self.title = title
        self.content = content()
    }

    public init(@ViewBuilder content: () -> Content, @ViewBuilder header: () -> Text) {
        self.content = content()
        title = header().title
    }
}

public struct Button: View {
    public typealias Body = Never
    let title: String
    let action: () -> Void

    public init(_ title: String, action: @escaping () -> Void) {
        self.title = title
        self.action = action
    }
}

public struct TextField: View {
    public typealias Body = Never
    let title: String
    let text: Binding<String>

    public init(_ title: String, text: Binding<String>) {
        self.title = title
        self.text = text
    }
}

public struct Toggle: View {
    public typealias Body = Never
    let title: String
    let isOn: Binding<Bool>

    public init(_ title: String, isOn: Binding<Bool>) {
        self.title = title
        self.isOn = isOn
    }
}

public struct ForEach<Element, ID: Hashable, Content: View>: View {
    public typealias Body = Never
    let data: [Element]
    let id: KeyPath<Element, ID>
    let content: (Element) -> Content

    public init(_ data: [Element], id: KeyPath<Element, ID>, @ViewBuilder content: @escaping (Element) -> Content) {
        self.data = data
        self.id = id
        self.content = content
    }
}
