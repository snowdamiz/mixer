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
    private var layouts = 0
    private var transactions = 0
    private var completions = 0
    private var intervals = 0
    var appeared = false {
        didSet { record(appeared ? "appeared" : "disappearing") }
    }

    init(presentation: GuestUIPresentation, attachment: CapabilityGuestUIAttachmentIdentity) {
        self.presentation = presentation
        self.attachment = attachment
    }

    func invalidatePresentationProbe() {
        resetProbe()
        record("invalidated")
    }

    private func resetProbe() {
        ticket = nil
        displayLink?.invalidate()
        displayLink = nil
        firstTimestamp = nil
        // The pending CA completion owns its slot until it returns.
    }

    private func visibilityRefusal(_ root: UIView, _ renderer: UIView) -> String? {
        guard appeared else { return "not-appeared" }
        guard let window = root.window else { return "no-window" }
        guard renderer.window === window else { return "renderer-window" }
        guard !root.isHidden, root.alpha > 0 else { return "root-hidden" }
        guard !renderer.isHidden, renderer.alpha > 0 else { return "renderer-hidden" }
        guard !window.isHidden, window.alpha > 0 else { return "window-hidden" }
        guard window.windowScene?.activationState == .foregroundActive else { return "scene-inactive" }
        guard root.bounds.width > 0, root.bounds.height > 0 else { return "root-bounds" }
        guard renderer.bounds.width > 0, renderer.bounds.height > 0 else { return "renderer-bounds" }
        var ancestor: UIView? = renderer
        while let view = ancestor {
            guard !view.isHidden, view.alpha > 0 else { return "ancestor-hidden" }
            ancestor = view.superview
        }
        guard !root.convert(root.bounds, to: window).intersection(window.bounds).isEmpty else {
            return "outside-window"
        }
        return nil
    }

    func nativeLayoutCompleted(root: UIView, renderer: UIView) {
        layouts = min(layouts + 1, 9999)
        self.root = root
        self.renderer = renderer
        if transactionPending { record("layout", "transaction-pending"); return }
        if displayLink != nil { record("layout", "link-active"); return }
        if let refusal = visibilityRefusal(root, renderer) { record("layout", refusal); return }
        guard let presentation else { return }
        guard let value = presentation.nativeDisplayTicket(attachment: attachment) else {
            record("layout", presentation.f11TicketRefusal(attachment) ?? "ticket-unavailable")
            return
        }
        ticket = value
        transactionPending = true
        transactions = min(transactions + 1, 9999)
        CATransaction.begin()
        CATransaction.setCompletionBlock { [weak self] in
            DispatchQueue.main.async { [weak self] in self?.transactionCompleted() }
        }
        renderer.layer.setNeedsDisplay()
        renderer.layer.displayIfNeeded()
        CATransaction.commit()
        record("ca-committed")
    }

    private func displayRefusal() -> String? {
        guard let ticket else { return "probe-ticket-missing" }
        guard let root, let renderer else { return "views-released" }
        if let refusal = visibilityRefusal(root, renderer) { return refusal }
        guard let presentation else { return "presentation-released" }
        return presentation.f11CurrentDisplayRefusal(ticket)
    }

    private func transactionCompleted() {
        completions = min(completions + 1, 9999)
        transactionPending = false
        if let refusal = displayRefusal() {
            record("ca-completed", refusal)
            ticket = nil
            root?.setNeedsLayout()
            return
        }
        let proxy = CapabilityGuestUIDisplayLinkProxy(self)
        let link = CADisplayLink(target: proxy, selector: #selector(CapabilityGuestUIDisplayLinkProxy.interval(_:)))
        displayLink = link
        firstTimestamp = nil
        link.add(to: .main, forMode: .common)
        record("ca-completed")
    }

    func displayInterval(_ link: CADisplayLink) {
        intervals = min(intervals + 1, 9999)
        if let refusal = displayRefusal() {
            record("display-link", refusal)
            resetProbe()
            root?.setNeedsLayout()
            return
        }
        guard let firstTimestamp else {
            self.firstTimestamp = link.timestamp
            record("first-interval")
            return
        }
        guard link.timestamp > firstTimestamp else { record("display-link", "same-timestamp"); return }
        guard let ticket, let presentation else { return }
        let accepted = presentation.observeNativeDisplay(ticket)
        record("second-interval", accepted ? "acknowledged" : "acknowledgment-refused")
        resetProbe()
    }

    func record(_ phase: String, _ refusal: String = "none") {
        let visible = if let root, let renderer { visibilityRefusal(root, renderer) ?? "yes" } else { "no-views" }
        let scene = root?.window?.windowScene?.activationState.rawValue ?? -2
        let current = ticket.map { presentation?.f11CurrentDisplayRefusal($0) ?? "yes" } ?? "no-probe-ticket"
        let stamp = ticket.map { "\($0.ticket.generation),\($0.ticket.frameSerial),\($0.ticket.revision)" } ?? "-"
        let facts = "phase=\(phase) gate=\(refusal) visibility=\(visible) scene=\(scene) appeared=\(appeared)"
            + " root=\(f11DiagnosticSize(root)) renderer=\(f11DiagnosticSize(renderer)) pending=\(transactionPending) link=\(displayLink != nil)"
            + " layout=\(layouts) ca=\(transactions),\(completions) intervals=\(intervals) probe=\(stamp) current=\(current)"
        presentation?.f11Trace.probe(phase: phase, refusal: refusal, facts: facts)
    }
}
