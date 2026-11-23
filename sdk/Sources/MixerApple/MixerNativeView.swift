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
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @Environment(\.colorSchemeContrast) private var colorSchemeContrast
    @Environment(\.legibilityWeight) private var legibilityWeight
    private let dispatch: @MainActor (UIEventEnvelope) throws -> Void
    private let onEventFailure: @MainActor (UIEventEnvelope, any Error) -> Void
    private let trackSynchronousTextChanges: Bool
    private var theme: MixerNativeTheme?

    public init(host: MixerUIHost, onAction: @escaping @MainActor (RoutedUIAction) -> Void,
                onEventFailure: @escaping @MainActor (any Error) -> Void = { _ in }) {
        self.host = host
        self.dispatch = { onAction(try host.route($0)) }
        self.onEventFailure = { _, error in onEventFailure(error) }
        self.trackSynchronousTextChanges = false
    }

    public init(host: MixerUIHost, onIssuedAction: @escaping @MainActor (IssuedUIAction) -> Void,
                onEventFailure: @escaping @MainActor (any Error) -> Void = { _ in }) {
        self.init(host: host, trackSynchronousTextChanges: false, onIssuedAction: onIssuedAction,
                  onEventFailure: { _, error in onEventFailure(error) })
    }

    /// Opt in when the issued-action handler synchronously installs the exact
    /// text it accepts. The same SwiftUI binding can then deliver another edit
    /// before SwiftUI installs a binding for the new render. Failures include
    /// the original envelope so the consumer can attribute them to that render.
    public init(host: MixerUIHost, trackSynchronousTextChanges: Bool,
                onIssuedAction: @escaping @MainActor (IssuedUIAction) throws -> Void,
                onEventFailure: @escaping @MainActor (UIEventEnvelope, any Error) -> Void = { _, _ in }) {
        self.host = host
        self.dispatch = { try onIssuedAction(host.routeIssued($0)) }
        self.onEventFailure = onEventFailure
        self.trackSynchronousTextChanges = trackSynchronousTextChanges
    }

    #if os(iOS)
    /// Installs the app's shared Text and Button appearance in this renderer.
    public func sharedTheme(_ theme: MixerNativeTheme?) -> Self {
        var view = self
        view.theme = theme
        return view
    }
    #endif

    public var body: some SwiftUI.View {
        NativeNode(node: host.snapshot.document.root, snapshot: host.snapshot,
                   textHost: trackSynchronousTextChanges ? host : nil,
                   theme: theme?.resolve(scheme: colorScheme, size: dynamicTypeSize,
                                         contrast: colorSchemeContrast, legibility: legibilityWeight),
                   dispatch: dispatchEvent)
        .id(host.snapshot.identity(for: host.snapshot.document.root.id))
        .background(FeatureDisplayCompletion(id: host.featureDisplayID) { host.completeFeatureDisplay($0) })
    }

    func dispatchEvent(_ envelope: UIEventEnvelope) -> Bool {
        do { try dispatch(envelope); return true }
        catch { onEventFailure(envelope, error); return false }
    }
}

/// Only the edit initiated by this binding may advance its render cursor.
/// A separate update (including another control's edit) leaves it stale.
@MainActor
func mixerNativeTextBinding(node: UINode, snapshot: UIRenderSnapshot, host: MixerUIHost?,
                            dispatch: @escaping @MainActor (UIEventEnvelope) -> Bool) -> Binding<String> {
    let rendered = node.properties["value"]!.string!
    let renderedRevision = snapshot.document.revision
    guard let identity = snapshot.identity(for: node.id),
          node.actions.contains(where: { $0.event == .textChange }) else {
        return Binding(get: { rendered }, set: { _ in })
    }
    guard let host else {
        return Binding(get: { rendered }, set: { value in
            _ = dispatch(UIEventEnvelope(revision: renderedRevision, identity: identity,
                                         event: .textChange, value: .string(value)))
        })
    }

    var revision = renderedRevision
    var accepted = rendered
    var writing = false
    return Binding(get: { accepted }, set: { [weak host] value in
        guard !writing else { return }
        writing = true
        defer { writing = false }
        guard let host else { return }
        let before = host.snapshot
        let issuedRevision = revision
        guard dispatch(UIEventEnvelope(revision: issuedRevision, identity: identity, event: .textChange,
                                       value: .string(value))) else { return }
        let after = host.snapshot
        guard before.document.revision == issuedRevision,
              issuedRevision < UInt64.max, after.document.revision == issuedRevision + 1,
              after.document.schemaVersion == before.document.schemaVersion,
              after.identity(for: node.id) == identity,
              matchesTextEdit(value, nodeID: node.id, before: before.document.root,
                              after: after.document.root) else { return }
        revision = after.document.revision
        accepted = value
    })
}

// Swift String equality treats canonically equivalent spellings as equal.
// Check the actual bytes so a simultaneous change elsewhere cannot advance the binding.
private func matchesTextEdit(_ value: String, nodeID: String, before: UINode, after: UINode) -> Bool {
    guard before.id.utf8.elementsEqual(after.id.utf8), before.kind == after.kind,
          before.children.count == after.children.count, before.actions.count == after.actions.count,
          before.properties.count == after.properties.count else { return false }
    for (old, new) in zip(before.actions, after.actions) {
        guard old.event == new.event, old.id.utf8.elementsEqual(new.id.utf8) else { return false }
    }
    for (key, property) in before.properties {
        guard let index = after.properties.index(forKey: key),
              key.utf8.elementsEqual(after.properties[index].key.utf8) else { return false }
        let expected = before.id == nodeID && key == "value" ? UIValue.string(value) : property
        let installed = after.properties[index].value
        switch (expected, installed) {
        case let (.string(expected), .string(installed)):
            guard expected.utf8.elementsEqual(installed.utf8) else { return false }
        case let (.number(expected), .number(installed)):
            guard expected.bitPattern == installed.bitPattern else { return false }
        default:
            guard expected == installed else { return false }
        }
    }
    return zip(before.children, after.children).allSatisfy { old, new in
        matchesTextEdit(value, nodeID: nodeID, before: old, after: new)
    }
}

@MainActor
private struct NativeNode: SwiftUI.View {
    let node: UINode
    let snapshot: UIRenderSnapshot
    let textHost: MixerUIHost?
    let theme: ResolvedNativeTheme?
    let dispatch: @MainActor (UIEventEnvelope) -> Bool

    private var accessibilityID: String {
        node.properties["accessibilityIdentifier"]?.string ?? node.id
    }

    @ViewBuilder
    var body: some SwiftUI.View {
        if node.kind == .section, let title = node.properties["title"]?.string, !title.isEmpty {
            SwiftUI.Section { children } header: {
                accessibility(AnyView(SwiftUI.Text(title)))
                    .accessibilityIdentifier(accessibilityID)
            }
            .disabled(node.properties["disabled"]?.bool == true)
        } else {
            accessibility(accessibilityContainer(render()))
                .disabled(node.properties["disabled"]?.bool == true)
                .accessibilityIdentifier(accessibilityID)
        }
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
            NativeNode(node: child, snapshot: snapshot, textHost: textHost, theme: theme, dispatch: dispatch)
                .id(snapshot.identity(for: child.id))
        }
    }

    private func emit(_ event: UIEventKind, value: UIValue = .null) {
        guard node.actions.contains(where: { $0.event == event }), let identity = snapshot.identity(for: node.id) else { return }
        _ = dispatch(UIEventEnvelope(revision: snapshot.document.revision, identity: identity, event: event, value: value))
    }

    private func render() -> AnyView {
        switch node.kind {
        case .text:
            return AnyView(renderText())
        case .button:
            let button = SwiftUI.Button(node.properties["label"]!.string!, role: buttonRole) { emit(.activate) }
            if let theme { return AnyView(button.buttonStyle(NativeThemedButtonStyle(theme: theme, role: buttonAppearanceRole))) }
            return AnyView(button)
        case .textField:
            let binding = mixerNativeTextBinding(node: node, snapshot: snapshot, host: textHost, dispatch: dispatch)
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
                NativeNode(node: node.children[0], snapshot: snapshot, textHost: textHost, theme: theme, dispatch: dispatch)
                    .id(snapshot.identity(for: node.children[0].id))
                    .navigationTitle(node.properties["title"]?.string ?? "")
            })
        }
    }

    @ViewBuilder
    private func renderText() -> some SwiftUI.View {
        let text = styledText(SwiftUI.Text(node.properties["text"]!.string!))
            .lineLimit(number("maxLines").map(Int.init))
        if node.properties["selectable"]?.bool == true {
            text.textSelection(.enabled)
        } else {
            text.textSelection(.disabled)
        }
    }

    @ViewBuilder
    private func styledText(_ text: SwiftUI.Text) -> some SwiftUI.View {
        let role = UISharedTextRoleV1(rawValue: node.properties["style"]?.string ?? "body") ?? .body
        if let theme {
            text.font(theme.font(role))
                .foregroundStyle(Color(mixerRGBA: theme.textPaint(role)))
                .background {
                    if let contrast = theme.contrast { Color(mixerRGBA: contrast.backdrop) }
                }
        } else {
            text.font(font)
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

    private var buttonAppearanceRole: UIResolvedButtonRoleV2 {
        UIResolvedButtonRoleV2(rawValue: node.properties["role"]?.string ?? "normal") ?? .normal
    }

    private var buttonRole: SwiftUI.ButtonRole? {
        switch buttonAppearanceRole {
        case .destructive: .destructive
        case .cancel: .cancel
        case .normal: nil
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
