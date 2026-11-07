import UIKit

/// Bounded observation only. No synthesized touches or recognizer state writes.
@MainActor final class DiagnosticTrace {
    static let shared = DiagnosticTrace()
    var focusSystemObserver: ((String, Int?) -> Void)?
    private(set) var entries: [[String: Any]] = []
    private(set) var dropped = 0
    private(set) var revision = 0
    // Diagnostic-only context trace, separate from the original strict trace.
    private(set) var focusContextEntries: [[String: Any]] = []
    private(set) var focusContextDropped = 0
    private(set) var focusContextRevision = 0
    private func focusEndpoint(_ item: (any UIFocusItem)?) -> [String: Any] {
        guard let item else {
            return ["state": "null", "identifier": NSNull(), "class": NSNull(),
                    "identity": NSNull(), "frame": NSNull(), "frameInWindow": NSNull(), "attachedToWindow": NSNull()]
        }
        let frame = item.frame
        var value: [String: Any] = ["state": "item", "class": String(describing: type(of: item)),
            "identity": String(describing: ObjectIdentifier(item)),
            "identifier": (item as? any UIAccessibilityIdentification)?.accessibilityIdentifier as Any? ?? NSNull(),
            "frame": ["x": frame.minX, "y": frame.minY, "width": frame.width, "height": frame.height],
            "frameInWindow": NSNull(), "attachedToWindow": NSNull()]
        if let view = item as? UIView {
            value["attachedToWindow"] = view.window != nil
            if view.window != nil {
                let attached = view.convert(view.bounds, to: nil)
                value["frameInWindow"] = ["x": attached.minX, "y": attached.minY, "width": attached.width, "height": attached.height]
            }
        }
        return value
    }
    func focusContext(_ source: String, _ context: UIFocusUpdateContext) {
        focusContextRevision += 1
        guard focusContextEntries.count < 128 else { focusContextDropped += 1; return }
        focusContextEntries.append(["sequence": focusContextRevision, "uptime": ProcessInfo.processInfo.systemUptime,
            "source": source, "heading": context.focusHeading.rawValue,
            "previous": focusEndpoint(context.previouslyFocusedItem), "next": focusEndpoint(context.nextFocusedItem)])
        focusSystemObserver?(source + "-callback", focusContextRevision)
    }
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

/// Private, bounded, read-only supplemental observation. Never an oracle input.
@MainActor final class FocusSystemObservation {
    static let shared = FocusSystemObservation()
    static let schema = "mixer.apple-toggle.focus-system.1"
    private let slots = ["authored-toggle", "plain-uibutton-reference", "next-focus"]
    private let counterLimit = 2_147_483_647
    private var entries: [[String: Any]] = []
    private var dropped = 0
    private var revision = 0
    private var status = "complete"
    var value: [String: Any] {
        envelope(entries: entries, dropped: dropped, revision: revision, status: status)
    }
    private func envelope(entries: [[String: Any]], dropped: Int, revision: Int, status: String) -> [String: Any] {
        ["schema": Self.schema, "authoritative": false, "atomic": false,
         "entries": entries, "dropped": dropped, "revision": revision, "captureStatus": status]
    }
    private func encoded(_ value: Any) -> Data? {
        try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes])
    }
    private func token(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 128 && value.utf8.allSatisfy { (33...126).contains($0) }
    }
    private func identity(_ value: AnyObject?) -> Any {
        value.map { String(describing: ObjectIdentifier($0)) as Any } ?? NSNull()
    }
    private func fail(_ reason: String) {
        if status == "complete" { status = reason }
        if dropped < counterLimit { dropped += 1 } else { status = "incomplete-counter" }
    }
    private func item(_ item: (any UIFocusItem)?, controls: [UIView], available: Bool) -> [String: Any] {
        guard available else { return ["state": "unavailable", "identity": NSNull(), "fixedMatches": [false, false, false]] }
        guard let item else { return ["state": "null", "identity": NSNull(), "fixedMatches": [false, false, false]] }
        let matches = controls.map { (item as AnyObject) === $0 }
        return ["state": matches.contains(true) ? "fixed" : "other", "identity": identity(item), "fixedMatches": matches]
    }
    func capture(site: String, contextSequence: Int?, stage: String, controller: UIViewController, controls: [UIView]) {
        guard revision < counterLimit else { fail("incomplete-counter"); return }
        revision += 1
        guard status == "complete" else { fail(status); return }
        guard entries.count < 128 else { fail("incomplete-count"); return }
        guard controls.count == 3, Set(controls.map(ObjectIdentifier.init)).count == 3,
              ["snapshot", "controller-callback", "carrier-callback"].contains(site), token(stage),
              (site == "snapshot" ? contextSequence == nil : contextSequence.map { $0 > 0 && $0 <= counterLimit } == true) else {
            fail("incomplete-metadata"); return
        }
        let started = ProcessInfo.processInfo.systemUptime
        let window = controller.viewIfLoaded?.window
        let environment: any UIFocusEnvironment = window ?? controller
        let system = UIFocusSystem.focusSystem(for: environment)
        let focusedItem = system?.focusedItem
        var rows: [[String: Any]] = []
        for (index, control) in controls.enumerated() {
            let group = control.focusGroupIdentifier
            guard group.map({ $0.utf8.count <= 128 }) ?? true else { fail("incomplete-metadata"); return }
            rows.append(["slot": slots[index], "identity": identity(control), "isFocused": control.isFocused,
                         "attachedToWindow": control.window != nil, "windowIdentity": identity(control.window),
                         "canBecomeFocused": control.canBecomeFocused, "focusGroupIdentifier": group as Any? ?? NSNull(),
                         "focusGroupPriority": control.focusGroupPriority.rawValue])
        }
        var sceneRow: [String: Any] = ["state": "absent", "identity": NSNull(), "systemIdentity": NSNull(), "itemIdentity": NSNull()]
        if let scene = window?.windowScene {
            let sceneSystem = scene.focusSystem
            sceneRow = ["state": sceneSystem == nil ? "unavailable" : "present", "identity": identity(scene),
                        "systemIdentity": identity(sceneSystem), "itemIdentity": identity(sceneSystem?.focusedItem)]
        }
        let finished = ProcessInfo.processInfo.systemUptime
        guard started.isFinite, finished.isFinite, started >= 0, finished >= started,
              entries.last.map({ ($0["finishedUptime"] as? Double ?? .infinity) <= started }) ?? true else {
            fail("incomplete-time"); return
        }
        let entry: [String: Any] = ["sequence": revision, "startedUptime": started, "finishedUptime": finished,
            "site": site, "contextSequence": contextSequence as Any? ?? NSNull(), "stage": stage,
            "environment": ["selection": window == nil ? "controller" : "window", "identity": identity(environment), "windowIdentity": identity(window)],
            "system": ["state": system == nil ? "unavailable" : "present", "identity": identity(system),
                       "item": item(focusedItem, controls: controls, available: system != nil)],
            "controls": rows, "scene": sceneRow]
        guard let bytes = encoded(entry), bytes.count <= 4096 else { fail("incomplete-entry-size"); return }
        let next = entries + [entry]
        // Reserve the largest bounded counter/status envelope before retaining a row.
        let reserved = envelope(entries: next, dropped: counterLimit, revision: counterLimit, status: "incomplete-entry-size")
        guard let total = encoded(reserved), total.count <= 65536 else { fail("incomplete-total-size"); return }
        entries = next
    }
}
