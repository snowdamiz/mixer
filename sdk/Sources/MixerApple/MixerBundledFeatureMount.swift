#if canImport(SwiftUI) && (os(iOS) || MIXER_BUNDLED_MOUNT_REPLAY)
import SwiftUI
import MixerSwiftUI
import MixerUI

/// Owns one bundled feature session and its native surface on the main executor.
@MainActor
public final class MixerBundledFeatureMount<Content: MixerSwiftUI.View>: ObservableObject {
    public enum Status: Equatable, Sendable {
        case starting
        case ready
        case failed
        case closed
    }

    @Published public private(set) var status: Status = .starting
    let host: MixerUIHost

    private let session: FeatureSession
    private let validator: UIValidator
    private let environment: @MainActor () -> UIAppearanceEnvironmentV2?
    private let content: @MainActor () -> Content
    private var displayed: (frame: FramePresentation, snapshot: UIRenderSnapshot)?
    private var lastConsumedActionSerial: UInt64 = 0
    private(set) var presentation: Task<Void, Never>?
    private var terminalStatus: Status?
    private var publishingReady = false

    // Only the binding that initiated the edit and bindings rendered from its
    // own in-flight frame can share this cursor.
    private final class TextEdit {
        let identity: UINodeIdentity
        let actionID: String
        var snapshot: UIRenderSnapshot
        var committedValue: String
        var value: String

        init(identity: UINodeIdentity, actionID: String, snapshot: UIRenderSnapshot, value: String) {
            self.identity = identity
            self.actionID = actionID
            self.snapshot = snapshot
            self.committedValue = value
            self.value = value
        }

        func envelope(in snapshot: UIRenderSnapshot, value: String) -> UIEventEnvelope {
            UIEventEnvelope(revision: snapshot.document.revision, identity: identity,
                            event: .textChange, value: .string(value))
        }

        func permits(_ value: String, in snapshot: UIRenderSnapshot) -> Bool {
            (try? snapshot.route(envelope(in: snapshot, value: value)))?.actionID == actionID
        }
    }

    private struct PendingTextEdit {
        let edit: TextEdit
        let submitted: String
        var document: MixerUI.UIDocument?

        func isRendered(in snapshot: UIRenderSnapshot) -> Bool {
            guard document == snapshot.document,
                  let rendered = snapshot.node(for: edit.identity)?.properties["value"]?.string else { return false }
            return rendered.utf8.elementsEqual(submitted.utf8)
        }
    }

    private var pendingTextEdit: PendingTextEdit?

    public init(environment: @escaping @MainActor () -> UIAppearanceEnvironmentV2? = { nil },
                content: @escaping @MainActor () -> Content) throws {
        let validator = UIValidator()
        self.validator = validator
        self.environment = environment
        self.content = content
        session = FeatureSession(executor: FeatureExecutor(serialQueue: .main), validator: validator)
        host = try MixerUIHost(document: UIDocument(revision: 0, root: UINode(id: "startup", kind: .vStack)),
                               validator: validator)
    }

    /// Attach this mount to one surface. Create a new mount after this surface disappears.
    public func view(theme: MixerNativeTheme? = nil) -> some SwiftUI.View {
        BundledFeatureSurface(mount: self, theme: theme)
    }

    public func cancel() {
        close(.closed)
    }

    func start() async {
        guard terminalStatus == nil, status == .starting, presentation == nil, !Task.isCancelled else { return }
        let task = schedulePresentation()
        await withTaskCancellationHandler {
            await task.value
        } onCancel: {
            task.cancel()
        }
    }

    func receive(_ issued: IssuedUIAction) throws {
        guard terminalStatus == nil, status == .ready, presentation == nil, let displayed,
              host.isCurrent(displayed.snapshot) else {
            throw UIRoutingError.staleRevision
        }
        let envelope = try displayed.snapshot.checkedEnvelope(for: issued)
        // The native renderer and session independently assign generation numbers.
        guard let identity = displayed.frame.snapshot.identity(for: envelope.identity.id) else {
            throw UIRoutingError.staleIdentity
        }
        let sessionEnvelope = UIEventEnvelope(revision: envelope.revision, identity: identity,
                                             event: envelope.event, value: envelope.value)
        guard issued.serial > lastConsumedActionSerial else { throw UIRoutingError.staleRevision }
        // A failed state write leaves this frame live even though the handler ran.
        lastConsumedActionSerial = issued.serial
        let outcome = session.dispatch(displayed.frame.token, sessionEnvelope)
        guard terminalStatus == nil else {
            session.detach()
            throw CancellationError()
        }
        switch outcome {
        case .handled:
            schedulePresentation()
        case .rejected:
            throw UIRoutingError.unboundEvent
        case let .invalidState(error, _):
            throw error
        }
    }

    func textBinding(node: UINode, snapshot: UIRenderSnapshot) -> SwiftUI.Binding<String>? {
        guard let value = node.properties["value"]?.string, let identity = snapshot.identity(for: node.id),
              let actionID = node.actions.first(where: { $0.event == .textChange })?.id else { return nil }

        let edit: TextEdit
        if let pending = pendingTextEdit, pending.edit.identity == identity, pending.edit.actionID == actionID,
           pending.isRendered(in: snapshot), host.isCurrent(snapshot) {
            edit = pending.edit
        } else {
            edit = TextEdit(identity: identity, actionID: actionID, snapshot: snapshot, value: value)
        }
        return SwiftUI.Binding(get: { edit.value }, set: { [weak self] value in self?.write(value, to: edit) })
    }

    private func write(_ value: String, to edit: TextEdit) {
        guard terminalStatus == nil else { return }
        let live = host.snapshot
        guard host.isCurrent(live), edit.permits(value, in: live) else { return }
        if let pending = pendingTextEdit, pending.edit === edit {
            // SwiftUI can deliver another full field value while drawing the
            // previous one. Keep one bounded, validated value for that draw.
            guard edit.snapshot.isSameRender(as: live) || pending.isRendered(in: live) else { return }
        } else {
            guard edit.snapshot.isSameRender(as: live),
                  let issued = try? host.routeIssued(edit.envelope(in: live, value: value)) else { return }
            do {
                try receive(issued)
            } catch {
                return
            }
            pendingTextEdit = PendingTextEdit(edit: edit, submitted: value)
        }
        edit.value = value
    }

    @discardableResult
    private func schedulePresentation() -> Task<Void, Never> {
        let task = Task { @MainActor in
            do {
                try Task.checkCancellation()
                let frame = try session.prepare(environment: environment(), content).presentation
                try Task.checkCancellation()
                let display = BundledFeatureDisplay(document: try validator.validate(frame.snapshot.document))
                pendingTextEdit?.document = frame.snapshot.document
                let receipt = try await host.presentFeature(display.request)
                try Task.checkCancellation()
                if display.accepts(receipt), host.isCurrent(receipt.snapshot),
                   session.finish(frame.token, outcome: .drawnAndInputReady) {
                    displayed = (frame, receipt.snapshot)
                } else {
                    close(.failed)
                }
            } catch {
                close(error is CancellationError ? .closed : .failed)
            }
            presentation = nil
            guard terminalStatus == nil, let displayed else {
                session.detach()
                return
            }
            if status == .starting { publishReady() }
            finishTextEdit(in: displayed.snapshot)
        }
        presentation = task
        return task
    }

    private func finishTextEdit(in snapshot: UIRenderSnapshot) {
        guard let pending = pendingTextEdit else { return }
        pendingTextEdit = nil
        let edit = pending.edit
        let latest = edit.value
        let installed = snapshot.node(for: edit.identity)?.properties["value"]?.string
        edit.value = installed ?? edit.committedValue
        guard let installed, installed.utf8.elementsEqual(pending.submitted.utf8),
              edit.permits(installed, in: snapshot) else { return }
        edit.committedValue = installed
        edit.snapshot = snapshot
        if !latest.utf8.elementsEqual(installed.utf8) {
            write(latest, to: edit)
        }
    }

    private func publishReady() {
        // @Published delivers in willSet. Serialize a terminal notification
        // requested synchronously by a ready observer after that write.
        publishingReady = true
        status = .ready
        publishingReady = false
        if let terminalStatus { status = terminalStatus }
    }

    private func close(_ terminal: Status) {
        guard terminalStatus == nil else { return }
        terminalStatus = terminal
        presentation?.cancel()
        displayed = nil
        if let edit = pendingTextEdit?.edit { edit.value = edit.committedValue }
        pendingTextEdit = nil
        session.detach()
        if !publishingReady { status = terminal }
    }
}

struct BundledFeatureDisplay {
    let request: NativePresentationRequest

    init(document: ValidatedUIDocument) {
        request = NativePresentationRequest(document: document)
    }

    func accepts(_ receipt: NativeDisplayAcknowledgement) -> Bool {
        request.accepts(receipt) && request.document.document == receipt.snapshot.document
    }
}

@MainActor
private struct BundledFeatureSurface<Content: MixerSwiftUI.View>: SwiftUI.View {
    @ObservedObject var mount: MixerBundledFeatureMount<Content>
    let theme: MixerNativeTheme?

    var body: some SwiftUI.View {
        Group {
            switch mount.status {
            case .starting, .ready:
                MixerNativeView(host: mount.host, theme: theme, bundledTextBinding: mount.textBinding,
                                onIssuedAction: mount.receive)
            case .failed:
                SwiftUI.Text("Feature unavailable")
            case .closed:
                EmptyView()
            }
        }
        .task { await mount.start() }
        .onDisappear { mount.cancel() }
    }
}
#endif
