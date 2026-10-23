#if canImport(SwiftUI) && canImport(MixerApple)
import SwiftUI
import Dispatch
import MixerApple
import MixerUI
import QuartzCore

/// A single bound native attachment. The wrapper privately creates its renderer
/// and forwards actions only to the currently bound signed guest attempt.
@MainActor
public struct MixerGuestScreen: View {
    @ObservedObject private var presentation: GuestUIPresentation

    public init(presentation: GuestUIPresentation) { self.presentation = presentation }

    public var body: some View {
        CapabilityGuestUIPlatformScreen(presentation: presentation)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

@MainActor
private struct CapabilityGuestUIRenderedContent: View {
    @ObservedObject var presentation: GuestUIPresentation
    let attachment: CapabilityGuestUIAttachmentIdentity

    var body: some View {
        if let host = presentation.renderHost {
            MixerNativeView(host: host, onAction: presentation.actionHandler(host: host, attachment: attachment))
                .disabled(!presentation.inputEnabled)
        } else {
            Color.clear
        }
    }
}

#if canImport(UIKit)
import UIKit

@MainActor
private struct CapabilityGuestUIPlatformScreen: UIViewControllerRepresentable {
    let presentation: GuestUIPresentation
    func makeUIViewController(context: Context) -> CapabilityGuestUIIOSController {
        CapabilityGuestUIIOSController(presentation: presentation)
    }
    func updateUIViewController(_ controller: CapabilityGuestUIIOSController, context: Context) {
        controller.presentationChanged()
    }
    static func dismantleUIViewController(_ controller: CapabilityGuestUIIOSController, coordinator: ()) {
        controller.detach()
    }
}

@MainActor
private final class CapabilityGuestUIIOSController: UIViewController, CapabilityGuestUIAttachmentObserver {
    private weak var presentation: GuestUIPresentation?
    private let attachment: CapabilityGuestUIAttachmentIdentity?
    private var hosting: UIHostingController<CapabilityGuestUIRenderedContent>?
    private var probe: CapabilityGuestUIIOSProbe?

    init(presentation: GuestUIPresentation) {
        self.presentation = presentation
        // The check precedes hosting/probe creation, including a second wrapper.
        attachment = presentation.claimNativeAttachment()
        super.init(nibName: nil, bundle: nil)
        guard let attachment else { return }
        NotificationCenter.default.addObserver(self, selector: #selector(sceneChanged(_:)),
                                               name: UIScene.didActivateNotification, object: nil)
        NotificationCenter.default.addObserver(self, selector: #selector(sceneChanged(_:)),
                                               name: UIScene.willDeactivateNotification, object: nil)
        hosting = UIHostingController(rootView: CapabilityGuestUIRenderedContent(presentation: presentation,
                                                                                 attachment: attachment))
        probe = CapabilityGuestUIIOSProbe(presentation: presentation, attachment: attachment)
        presentation.installNativeAttachment(self, identity: attachment)
    }
    @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }

    override func loadView() {
        let container = CapabilityGuestUIIOSRootView()
        container.owner = self; view = container
        guard let hosting else { return }
        addChild(hosting); container.addSubview(hosting.view)
        hosting.view.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            hosting.view.leadingAnchor.constraint(equalTo: container.leadingAnchor),
            hosting.view.trailingAnchor.constraint(equalTo: container.trailingAnchor),
            hosting.view.topAnchor.constraint(equalTo: container.topAnchor),
            hosting.view.bottomAnchor.constraint(equalTo: container.bottomAnchor),
        ])
        hosting.didMove(toParent: self)
    }
    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated); probe?.appeared = true; view.setNeedsLayout()
    }
    override func viewWillDisappear(_ animated: Bool) {
        probe?.appeared = false; probe?.invalidatePresentationProbe()
        super.viewWillDisappear(animated)
    }
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        guard let hosting else { return }
        probe?.nativeLayoutCompleted(root: view, renderer: hosting.view)
    }
    func presentationChanged() {
        if isViewLoaded { view.setNeedsLayout() }
    }
    func invalidatePresentationProbe() { probe?.invalidatePresentationProbe() }
    func attachmentChanged() {
        probe?.invalidatePresentationProbe(); view.setNeedsLayout()
    }
    @objc private func sceneChanged(_ notification: Notification) {
        guard isViewLoaded, let scene = notification.object as? UIWindowScene,
              scene === view.window?.windowScene else { return }
        attachmentChanged()
    }
    func detach() {
        probe?.invalidatePresentationProbe()
        if let attachment { presentation?.detachNativeAttachment(attachment) }
        presentation = nil
    }
}

@MainActor
private final class CapabilityGuestUIIOSRootView: UIView {
    weak var owner: CapabilityGuestUIIOSController?
    override func didMoveToWindow() { super.didMoveToWindow(); owner?.attachmentChanged() }
}

@MainActor
private final class CapabilityGuestUIDisplayLinkProxy: NSObject {
    weak var probe: CapabilityGuestUIIOSProbe?
    init(_ probe: CapabilityGuestUIIOSProbe) { self.probe = probe }
    @objc func interval(_ link: CADisplayLink) { probe?.displayInterval(link) }
}

@MainActor
private final class CapabilityGuestUIIOSProbe {
    private weak var presentation: GuestUIPresentation?
    private let attachment: CapabilityGuestUIAttachmentIdentity
    private weak var root: UIView?
    private weak var renderer: UIView?
    private var ticket: CapabilityGuestUIDisplayTicket?
    private var transactionPending = false
    private var displayLink: CADisplayLink?
    private var firstTimestamp: CFTimeInterval?
    var appeared = false

    init(presentation: GuestUIPresentation, attachment: CapabilityGuestUIAttachmentIdentity) {
        self.presentation = presentation; self.attachment = attachment
    }
    func invalidatePresentationProbe() {
        ticket = nil; displayLink?.invalidate(); displayLink = nil; firstTimestamp = nil
        // An already committed CA completion cannot be cancelled. Keep its sole
        // slot occupied until it actually returns; it holds only a weak probe.
    }
    private func visible(_ root: UIView, _ renderer: UIView) -> Bool {
        guard appeared, let window = root.window, renderer.window === window,
              !root.isHidden, root.alpha > 0, !renderer.isHidden, renderer.alpha > 0,
              !window.isHidden, window.alpha > 0,
              window.windowScene?.activationState == .foregroundActive,
              root.bounds.width > 0, root.bounds.height > 0,
              renderer.bounds.width > 0, renderer.bounds.height > 0 else { return false }
        var ancestor: UIView? = renderer
        while let view = ancestor {
            guard !view.isHidden, view.alpha > 0 else { return false }
            ancestor = view.superview
        }
        return !root.convert(root.bounds, to: window).intersection(window.bounds).isEmpty
    }
    func nativeLayoutCompleted(root: UIView, renderer: UIView) {
        self.root = root; self.renderer = renderer
        guard !transactionPending, displayLink == nil, visible(root, renderer),
              let value = presentation?.nativeDisplayTicket(attachment: attachment) else { return }
        ticket = value; transactionPending = true
        CATransaction.begin()
        CATransaction.setCompletionBlock { [weak self] in
            DispatchQueue.main.async { [weak self] in self?.transactionCompleted() }
        }
        renderer.layer.setNeedsDisplay()
        renderer.layer.displayIfNeeded()
        CATransaction.commit()
    }
    private func transactionCompleted() {
        transactionPending = false
        guard let ticket, let root, let renderer, visible(root, renderer),
              presentation?.isCurrentNativeDisplay(ticket) == true else {
            self.ticket = nil; self.root?.setNeedsLayout(); return
        }
        let proxy = CapabilityGuestUIDisplayLinkProxy(self)
        let link = CADisplayLink(target: proxy, selector: #selector(CapabilityGuestUIDisplayLinkProxy.interval(_:)))
        displayLink = link; firstTimestamp = nil
        link.add(to: .main, forMode: .common)
    }
    func displayInterval(_ link: CADisplayLink) {
        guard let ticket, let root, let renderer, visible(root, renderer),
              presentation?.isCurrentNativeDisplay(ticket) == true else {
            invalidatePresentationProbe(); root?.setNeedsLayout(); return
        }
        // The first callback establishes a native display timestamp. The next
        // distinct timestamp proves a subsequent display interval elapsed.
        guard let firstTimestamp else { self.firstTimestamp = link.timestamp; return }
        guard link.timestamp > firstTimestamp else { return }
        _ = presentation?.observeNativeDisplay(ticket)
        invalidatePresentationProbe()
    }
}
#elseif canImport(AppKit)
import AppKit

@MainActor
private struct CapabilityGuestUIPlatformScreen: NSViewControllerRepresentable {
    let presentation: GuestUIPresentation
    func makeNSViewController(context: Context) -> CapabilityGuestUIMacController {
        CapabilityGuestUIMacController(presentation: presentation)
    }
    func updateNSViewController(_ controller: CapabilityGuestUIMacController, context: Context) {
        controller.presentationChanged()
    }
    static func dismantleNSViewController(_ controller: CapabilityGuestUIMacController, coordinator: ()) {
        controller.detach()
    }
}

@MainActor
private final class CapabilityGuestUIMacController: NSViewController, CapabilityGuestUIAttachmentObserver {
    private weak var presentation: GuestUIPresentation?
    private let attachment: CapabilityGuestUIAttachmentIdentity?
    private var hosting: NSHostingView<CapabilityGuestUIRenderedContent>?
    private var probe: CapabilityGuestUIMacProbe?

    init(presentation: GuestUIPresentation) {
        self.presentation = presentation
        attachment = presentation.claimNativeAttachment()
        super.init(nibName: nil, bundle: nil)
        guard let attachment else { return }
        NotificationCenter.default.addObserver(self, selector: #selector(windowChanged(_:)),
                                               name: NSWindow.didChangeOcclusionStateNotification, object: nil)
        NotificationCenter.default.addObserver(self, selector: #selector(windowChanged(_:)),
                                               name: NSWindow.didMiniaturizeNotification, object: nil)
        NotificationCenter.default.addObserver(self, selector: #selector(windowChanged(_:)),
                                               name: NSWindow.didDeminiaturizeNotification, object: nil)
        hosting = NSHostingView(rootView: CapabilityGuestUIRenderedContent(presentation: presentation,
                                                                          attachment: attachment))
        probe = CapabilityGuestUIMacProbe(presentation: presentation, attachment: attachment)
        presentation.installNativeAttachment(self, identity: attachment)
    }
    @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }
    override func loadView() {
        let container = CapabilityGuestUIMacRootView()
        container.owner = self; view = container
        guard let hosting else { return }
        container.addSubview(hosting)
    }
    func nativeLayoutCompleted() {
        guard let hosting else { return }
        hosting.frame = view.bounds
        probe?.nativeLayoutCompleted(root: view, renderer: hosting)
    }
    override func viewDidAppear() {
        super.viewDidAppear(); attachmentChanged()
    }
    func attachmentChanged() {
        probe?.invalidatePresentationProbe()
        guard isViewLoaded else { return }
        view.needsLayout = true
        view.layoutSubtreeIfNeeded()
        nativeLayoutCompleted()
    }
    func presentationChanged() {
        if isViewLoaded { view.needsLayout = true }
    }
    func invalidatePresentationProbe() { probe?.invalidatePresentationProbe() }
    @objc private func windowChanged(_ notification: Notification) {
        guard isViewLoaded, let window = notification.object as? NSWindow,
              window === view.window else { return }
        attachmentChanged()
    }
    func detach() {
        probe?.invalidatePresentationProbe()
        if let attachment { presentation?.detachNativeAttachment(attachment) }
        presentation = nil
    }
}

@MainActor
private final class CapabilityGuestUIMacRootView: NSView {
    weak var owner: CapabilityGuestUIMacController?
    override func layout() { super.layout(); owner?.nativeLayoutCompleted() }
    override func viewDidMoveToWindow() { super.viewDidMoveToWindow(); owner?.attachmentChanged() }
}

@MainActor
private final class CapabilityGuestUIMacProbe {
    private weak var presentation: GuestUIPresentation?
    private let attachment: CapabilityGuestUIAttachmentIdentity
    private weak var root: NSView?
    private weak var renderer: NSView?
    private var ticket: CapabilityGuestUIDisplayTicket?
    private var transactionPending = false

    init(presentation: GuestUIPresentation, attachment: CapabilityGuestUIAttachmentIdentity) {
        self.presentation = presentation; self.attachment = attachment
    }
    func invalidatePresentationProbe() { ticket = nil }
    private func visible(_ root: NSView, _ renderer: NSView) -> Bool {
        guard let window = root.window, renderer.window === window, window.isVisible,
              !window.isMiniaturized, window.occlusionState.contains(.visible),
              !root.isHiddenOrHasHiddenAncestor, !renderer.isHiddenOrHasHiddenAncestor,
              root.bounds.width > 0, root.bounds.height > 0,
              renderer.bounds.width > 0, renderer.bounds.height > 0 else { return false }
        return !root.visibleRect.isEmpty && !renderer.visibleRect.isEmpty
    }
    func nativeLayoutCompleted(root: NSView, renderer: NSView) {
        self.root = root; self.renderer = renderer
        guard !transactionPending, visible(root, renderer),
              let value = presentation?.nativeDisplayTicket(attachment: attachment) else { return }
        transactionPending = true; ticket = value
        // AppKit's displayIfNeeded synchronously displays the view/subviews.
        // Recheck the same native window and exact ticket after it completes;
        // this observes native display, not compositor/pixel delivery.
        renderer.layoutSubtreeIfNeeded()
        renderer.needsDisplay = true
        renderer.displayIfNeeded()
        if !renderer.needsDisplay { nativeDisplayCompleted() }
        else { transactionPending = false; ticket = nil }
    }
    private func nativeDisplayCompleted() {
        transactionPending = false
        guard let ticket, let root, let renderer, visible(root, renderer),
              presentation?.isCurrentNativeDisplay(ticket) == true else {
            self.ticket = nil; self.root?.needsLayout = true; return
        }
        _ = presentation?.observeNativeDisplay(ticket)
        self.ticket = nil
    }
}
#endif
#endif
