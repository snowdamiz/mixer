#if os(iOS) && canImport(SwiftUI)
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
    private(set) var presentation: Task<Void, Never>?

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
        guard status == .starting, presentation == nil, !Task.isCancelled else { return }
        let task = schedulePresentation()
        await withTaskCancellationHandler {
            await task.value
        } onCancel: {
            task.cancel()
        }
    }

    func receive(_ issued: IssuedUIAction) throws {
        guard status == .ready, presentation == nil, let displayed else {
            throw UIRoutingError.staleRevision
        }
        let envelope = try displayed.snapshot.checkedEnvelope(for: issued)
        // The native renderer and session independently assign generation numbers.
        guard let identity = displayed.frame.snapshot.identity(for: envelope.identity.id) else {
            throw UIRoutingError.staleIdentity
        }
        let sessionEnvelope = UIEventEnvelope(revision: envelope.revision, identity: identity,
                                             event: envelope.event, value: envelope.value)
        let outcome = session.dispatch(displayed.frame.token, sessionEnvelope)
        guard status == .ready else {
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

    @discardableResult
    private func schedulePresentation() -> Task<Void, Never> {
        let task = Task { @MainActor in
            defer {
                presentation = nil
                if status == .closed || status == .failed { session.detach() }
            }
            do {
                try Task.checkCancellation()
                let frame = try session.prepare(environment: environment(), content).presentation
                let display = BundledFeatureDisplay(document: try validator.validate(frame.snapshot.document))
                let receipt = try await host.presentFeature(display.request)
                try Task.checkCancellation()
                guard display.accepts(receipt),
                      session.finish(frame.token, outcome: .drawnAndInputReady) else {
                    close(.failed)
                    return
                }
                displayed = (frame, receipt.snapshot)
                if status == .starting { status = .ready }
            } catch {
                close(error is CancellationError ? .closed : .failed)
            }
        }
        presentation = task
        return task
    }

    private func close(_ terminal: Status) {
        guard status == .starting || status == .ready else { return }
        presentation?.cancel()
        displayed = nil
        session.detach()
        status = terminal
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
                MixerNativeView(host: mount.host, trackSynchronousTextChanges: false, onIssuedAction: mount.receive)
                    .sharedTheme(theme)
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
