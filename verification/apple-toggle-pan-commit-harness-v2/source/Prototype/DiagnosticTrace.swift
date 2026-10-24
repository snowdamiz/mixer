import UIKit

/// Bounded observation only. No synthesized touches or recognizer state writes.
@MainActor final class DiagnosticTrace {
    static let shared = DiagnosticTrace()
    private(set) var entries: [[String: Any]] = []
    private(set) var dropped = 0
    private(set) var revision = 0
    func append(_ kind: String, _ fields: [String: Any] = [:]) {
        revision += 1
        guard entries.count < 8192 else { dropped += 1; return }
        entries.append(fields.merging(["sequence": revision, "uptime": ProcessInfo.processInfo.systemUptime, "kind": kind]) { _, new in new })
    }
    func gesture(_ gesture: UIGestureRecognizer) -> [String: Any] {
        var result: [String: Any] = ["identity": String(describing: ObjectIdentifier(gesture)), "class": String(describing: type(of: gesture)), "state": gesture.state.rawValue, "touchCount": gesture.numberOfTouches, "enabled": gesture.isEnabled, "allowedTouchTypes": gesture.allowedTouchTypes, "cancelsTouches": gesture.cancelsTouchesInView]
        if let pan = gesture as? UIPanGestureRecognizer {
            result["translationInWindow"] = point(pan.translation(in: nil))
            result["velocityInWindow"] = point(pan.velocity(in: nil))
        }
        return result
    }
    func point(_ point: CGPoint) -> [String: CGFloat] { ["x": point.x, "y": point.y] }
    func touches(_ kind: String, _ touches: Set<UITouch>, _ event: UIEvent?, in view: UIView) {
        for touch in touches {
            append(kind, ["touchIdentity": String(describing: ObjectIdentifier(touch)), "phase": touch.phase.rawValue, "type": touch.type.rawValue, "timestamp": touch.timestamp, "viewClass": String(describing: type(of: view)), "locationInView": point(touch.location(in: view)), "locationInWindow": point(touch.location(in: nil)), "eventTimestamp": event?.timestamp as Any? ?? NSNull(), "coalescedTouchCount": event?.coalescedTouches(for: touch)?.count as Any? ?? NSNull()])
        }
    }
}

/// Independent delivery reference: a public UIView and unfiltered native pan.
@MainActor final class DiagnosticPanSurface: UIView {
    let pan = UIPanGestureRecognizer()
    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = UIColor(white: 0.85, alpha: 1)
        accessibilityIdentifier = "diagnostic-pan-reference"
        let label = UILabel(frame: CGRect(x: 8, y: 8, width: 284, height: 28))
        label.text = "Native pan delivery reference"
        label.isUserInteractionEnabled = false
        addSubview(label)
        pan.addTarget(self, action: #selector(panChanged))
        addGestureRecognizer(pan)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) unsupported") }
    @objc private func panChanged() { DiagnosticTrace.shared.append("referencePan", DiagnosticTrace.shared.gesture(pan)) }
    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) { DiagnosticTrace.shared.touches("referenceTouchesBegan", touches, event, in: self); super.touchesBegan(touches, with: event) }
    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) { DiagnosticTrace.shared.touches("referenceTouchesMoved", touches, event, in: self); super.touchesMoved(touches, with: event) }
    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) { DiagnosticTrace.shared.touches("referenceTouchesEnded", touches, event, in: self); super.touchesEnded(touches, with: event) }
    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) { DiagnosticTrace.shared.touches("referenceTouchesCancelled", touches, event, in: self); super.touchesCancelled(touches, with: event) }
}
