#if canImport(SwiftUI)
import SwiftUI
import MixerUI
import Foundation

/// The adapter publishes one validated batch at a time. Failed updates preserve the
/// displayed tree. Dispatch always consults the current snapshot, not a captured one.
@MainActor
public final class MixerUIHost: ObservableObject {
    @Published public private(set) var snapshot: UIRenderSnapshot
    private let router: UINativeActionRouter
    @Published internal private(set) var featureDisplayID: UUID?
    private var featurePresentation: (NativePresentationRequest, CheckedContinuation<NativeDisplayAcknowledgement, any Error>)?

    public init(document: MixerUI.UIDocument,
                validator: UIValidator = UIValidator(supportedTextFieldAxes: [.horizontal, .vertical])) throws {
        let router = try UINativeActionRouter(document: document, validator: validator)
        snapshot = try router.snapshot
        self.router = router
    }

    @discardableResult
    public func update(_ document: MixerUI.UIDocument) throws -> UIChangeSet {
        let changes = try router.update(document)
        snapshot = try router.snapshot
        return changes
    }

    public func routeIssued(_ envelope: UIEventEnvelope) throws -> IssuedUIAction { try router.route(envelope) }

    public func route(_ envelope: UIEventEnvelope) throws -> RoutedUIAction {
        try snapshot.route(envelope)
    }

    /// Completes through the installed native view's layout/display transaction.
    public func presentFeature(_ request: NativePresentationRequest) async throws -> NativeDisplayAcknowledgement {
        try Task.checkCancellation()
        guard featurePresentation == nil else { throw FeatureDisplayError.busy }
        return try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { continuation in
                featurePresentation = (request, continuation)
                do {
                    try update(request.document.document)
                    featureDisplayID = request.id
                } catch {
                    featurePresentation = nil; continuation.resume(throwing: error)
                }
            }
        } onCancel: { Task { @MainActor in self.cancelFeatureDisplay(request.id) } }
    }

    internal func completeFeatureDisplay(_ id: UUID) {
        guard let (request, continuation) = featurePresentation, request.id == id, featureDisplayID == id else { return }
        featurePresentation = nil; featureDisplayID = nil
        continuation.resume(returning: request.acknowledgement(snapshot: snapshot))
    }
    private func cancelFeatureDisplay(_ id: UUID) {
        guard let (request, continuation) = featurePresentation, request.id == id else { return }
        featurePresentation = nil; featureDisplayID = nil
        continuation.resume(throwing: CancellationError())
    }
}

private enum FeatureDisplayError: Error { case busy }

/// Renders owned UI nodes as native SwiftUI controls, with native text input, lists,
/// layout and accessibility semantics. No HTML, web views or interpreted layout.
@MainActor
public struct MixerNativeView: SwiftUI.View {
    @ObservedObject private var host: MixerUIHost
    private let dispatch: @MainActor (UIEventEnvelope) throws -> Void
    private let onEventFailure: @MainActor (any Error) -> Void

    public init(host: MixerUIHost, onAction: @escaping @MainActor (RoutedUIAction) -> Void,
                onEventFailure: @escaping @MainActor (any Error) -> Void = { _ in }) {
        self.host = host; self.dispatch = { onAction(try host.route($0)) }; self.onEventFailure = onEventFailure
    }

    public init(host: MixerUIHost, onIssuedAction: @escaping @MainActor (IssuedUIAction) -> Void,
                onEventFailure: @escaping @MainActor (any Error) -> Void = { _ in }) {
        self.host = host; self.dispatch = { onIssuedAction(try host.routeIssued($0)) }; self.onEventFailure = onEventFailure
    }

    public var body: some SwiftUI.View {
        NativeNode(node: host.snapshot.document.root, snapshot: host.snapshot) { envelope in
            do { try dispatch(envelope) }
            catch { onEventFailure(error) }
        }
        .id(host.snapshot.identity(for: host.snapshot.document.root.id))
        .background(FeatureDisplayCompletion(id: host.featureDisplayID) { host.completeFeatureDisplay($0) })
    }
}

@MainActor
private struct NativeNode: SwiftUI.View {
    let node: UINode
    let snapshot: UIRenderSnapshot
    let dispatch: @MainActor (UIEventEnvelope) -> Void

    var body: some SwiftUI.View {
        accessibility(accessibilityContainer(render()))
            .disabled(node.properties["disabled"]?.bool == true)
            .accessibilityIdentifier(node.properties["accessibilityIdentifier"]?.string ?? node.id)
    }

    private func accessibilityContainer(_ view: AnyView) -> AnyView {
        switch node.kind {
        case .vStack, .hStack, .zStack, .list, .section, .navigation:
            return AnyView(view.accessibilityElement(children: .contain))
        default:
            return view
        }
    }

    private var children: some SwiftUI.View {
        ForEach(node.children, id: \.id) { child in
            NativeNode(node: child, snapshot: snapshot, dispatch: dispatch)
                .id(snapshot.identity(for: child.id))
        }
    }

    private func emit(_ event: UIEventKind, value: UIValue = .null) {
        guard node.actions.contains(where: { $0.event == event }), let identity = snapshot.identity(for: node.id) else { return }
        dispatch(UIEventEnvelope(revision: snapshot.document.revision, identity: identity, event: event, value: value))
    }

    private func render() -> AnyView {
        switch node.kind {
        case .text:
            let text = SwiftUI.Text(node.properties["text"]!.string!)
                .font(font)
                .lineLimit(number("maxLines").map(Int.init))
            if node.properties["selectable"]?.bool == true { return AnyView(text.textSelection(.enabled)) }
            return AnyView(text.textSelection(.disabled))
        case .button:
            return AnyView(SwiftUI.Button(node.properties["label"]!.string!, role: buttonRole) { emit(.activate) })
        case .textField:
            let binding = Binding<String>(get: { node.properties["value"]!.string! }, set: { emit(.textChange, value: .string($0)) })
            let axis: SwiftUI.Axis = node.properties["axis"]?.string == TextFieldAxis.vertical.rawValue ? .vertical : .horizontal
            return AnyView(SwiftUI.TextField(node.properties["label"]!.string!, text: binding, axis: axis).onSubmit { emit(.submit) })
        case .toggle:
            let binding = Binding<Bool>(get: { node.properties["value"]!.bool! }, set: { emit(.valueChange, value: .bool($0)) })
            return AnyView(SwiftUI.Toggle(node.properties["label"]!.string!, isOn: binding))
        case .vStack:
            return AnyView(SwiftUI.VStack(alignment: horizontalAlignment, spacing: number("spacing").map { CGFloat($0) }) { children })
        case .hStack:
            return AnyView(SwiftUI.HStack(alignment: verticalAlignment, spacing: number("spacing").map { CGFloat($0) }) { children })
        case .zStack:
            return AnyView(SwiftUI.ZStack(alignment: alignment) { children })
        case .list:
            return AnyView(SwiftUI.List { children })
        case .section:
            if let title = node.properties["title"]?.string {
                return AnyView(SwiftUI.Section { children } header: { SwiftUI.Text(title) })
            }
            return AnyView(SwiftUI.Section { children })
        case .navigation:
            return AnyView(SwiftUI.NavigationStack {
                NativeNode(node: node.children[0], snapshot: snapshot, dispatch: dispatch)
                    .id(snapshot.identity(for: node.children[0].id))
                    .navigationTitle(node.properties["title"]?.string ?? "")
            })
        }
    }

    private func accessibility(_ view: AnyView) -> AnyView {
        var result = view
        if let label = node.properties["accessibilityLabel"]?.string { result = AnyView(result.accessibilityLabel(SwiftUI.Text(label))) }
        if let hint = node.properties["accessibilityHint"]?.string { result = AnyView(result.accessibilityHint(SwiftUI.Text(hint))) }
        if let value = node.properties["accessibilityValue"]?.string { result = AnyView(result.accessibilityValue(SwiftUI.Text(value))) }
        return result
    }

    private func number(_ key: String) -> Double? {
        guard case let .number(value)? = node.properties[key] else { return nil }
        return value
    }

    private var font: Font {
        switch node.properties["style"]?.string {
        case "headline": .headline
        case "title": .title
        case "caption": .caption
        default: .body
        }
    }

    private var buttonRole: SwiftUI.ButtonRole? {
        switch node.properties["role"]?.string {
        case "destructive": .destructive
        case "cancel": .cancel
        default: nil
        }
    }

    private var horizontalAlignment: SwiftUI.HorizontalAlignment {
        switch node.properties["alignment"]?.string {
        case "leading": .leading
        case "trailing": .trailing
        default: .center
        }
    }

    private var verticalAlignment: SwiftUI.VerticalAlignment {
        switch node.properties["alignment"]?.string {
        case "top": .top
        case "bottom": .bottom
        case "firstTextBaseline": .firstTextBaseline
        case "lastTextBaseline": .lastTextBaseline
        default: .center
        }
    }

    private var alignment: Alignment {
        switch node.properties["alignment"]?.string {
        case "leading": .leading
        case "trailing": .trailing
        case "top": .top
        case "bottom": .bottom
        case "topLeading": .topLeading
        case "topTrailing": .topTrailing
        case "bottomLeading": .bottomLeading
        case "bottomTrailing": .bottomTrailing
        default: .center
        }
    }
}
#else
#error("MixerApple requires an Apple platform with SwiftUI; use a qualified native adapter for another platform.")
#endif
