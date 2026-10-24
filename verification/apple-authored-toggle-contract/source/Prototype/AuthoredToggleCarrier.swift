import UIKit
import MixerUI

/// Qualification prototype only. Native UIButton owns activation, touch
/// tracking, cancellation, focus, keyboard and assistive-technology input.
/// Mixer owns the public selected-state mapping and closed authored paint.
@MainActor final class AuthoredToggleCarrier: UIButton {
    var inputAllowed: (() -> Bool)?
    var stateChanged: ((String) -> Void)?
    var authoredAccessibility: [String: String] = [:]
    var paints: UIToggleValuesV2!
    var direction: UILayoutDirectionV1 = .leftToRight { didSet { setNeedsDisplay() } }
    private(set) var retainedOn = false
    private(set) var primaryCount = 0
    private(set) var acceptedCount = 0
    private(set) var rejectedCount = 0
    private(set) var beginCount = 0
    private(set) var continueCount = 0
    private(set) var endCount = 0
    private(set) var cancellationCount = 0
    private(set) var accessibilityActivationCount = 0
    var isOn: Bool { isSelected }
    var authoredPressed: Bool { isHighlighted }

    override init(frame: CGRect) {
        super.init(frame: frame)
        configuration = nil
        menu = nil
        showsMenuAsPrimaryAction = false
        changesSelectionAsPrimaryAction = true
        showsTouchWhenHighlighted = false
        backgroundColor = .clear
        isOpaque = false
        isAccessibilityElement = true
        addTarget(self, action: #selector(primaryAction), for: .primaryActionTriggered)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) unsupported") }

    func setOn(_ value: Bool, animated: Bool) {
        // A binding write never emits valueChanged or primaryActionTriggered.
        retainedOn = value
        isSelected = value
        stateChanged?("binding")
    }

    @objc private func primaryAction() {
        primaryCount += 1
        guard isEnabled, inputAllowed?() == true else {
            isSelected = retainedOn
            rejectedCount += 1
            stateChanged?("primaryRejected")
            return
        }
        // UIButton changes its selected state before invoking this target.
        retainedOn = isSelected
        acceptedCount += 1
        stateChanged?("primaryAccepted")
        sendActions(for: .valueChanged)
    }

    override var isHighlighted: Bool {
        didSet { setNeedsDisplay(); stateChanged?("highlight") }
    }
    override var isSelected: Bool {
        didSet { setNeedsDisplay(); stateChanged?("selection") }
    }
    override var isEnabled: Bool {
        didSet {
            if !isEnabled { cancelTracking(with: nil) }
            setNeedsDisplay(); stateChanged?("enabled")
        }
    }
    override var accessibilityTraits: UIAccessibilityTraits {
        get { super.accessibilityTraits.union([.button, .toggleButton]) }
        set { super.accessibilityTraits = newValue }
    }
    override var accessibilityLabel: String? {
        get { authoredAccessibility["accessibilityLabel"] ?? super.accessibilityLabel }
        set { super.accessibilityLabel = newValue }
    }
    override var accessibilityHint: String? {
        get { authoredAccessibility["accessibilityHint"] ?? super.accessibilityHint }
        set { super.accessibilityHint = newValue }
    }
    override var accessibilityValue: String? {
        get { authoredAccessibility["accessibilityValue"] ?? super.accessibilityValue }
        set { super.accessibilityValue = newValue }
    }
    override var accessibilityIdentifier: String? {
        get { authoredAccessibility["accessibilityIdentifier"] ?? super.accessibilityIdentifier }
        set { super.accessibilityIdentifier = newValue }
    }
    override func accessibilityActivate() -> Bool {
        accessibilityActivationCount += 1
        guard isEnabled, inputAllowed?() == true else { return false }
        return super.accessibilityActivate()
    }
    override func beginTracking(_ touch: UITouch, with event: UIEvent?) -> Bool {
        beginCount += 1
        guard isEnabled, inputAllowed?() == true else { stateChanged?("beginRejected"); return false }
        let result = super.beginTracking(touch, with: event)
        stateChanged?("begin"); return result
    }
    override func continueTracking(_ touch: UITouch, with event: UIEvent?) -> Bool {
        continueCount += 1
        let result = super.continueTracking(touch, with: event)
        stateChanged?("continue"); return result
    }
    override func endTracking(_ touch: UITouch?, with event: UIEvent?) {
        endCount += 1
        super.endTracking(touch, with: event)
        stateChanged?("end")
    }
    override func cancelTracking(with event: UIEvent?) {
        cancellationCount += 1
        super.cancelTracking(with: event)
        stateChanged?("cancel")
    }
    override func didUpdateFocus(in context: UIFocusUpdateContext, with coordinator: UIFocusAnimationCoordinator) {
        super.didUpdateFocus(in: context, with: coordinator)
        setNeedsDisplay(); stateChanged?("focus")
    }

    override func draw(_ rect: CGRect) {
        guard let context = UIGraphicsGetCurrentContext(), let paints else { return }
        let states = isOn ? paints.on : paints.off
        let paint = !isEnabled ? states.disabled : (authoredPressed ? states.pressed : states.enabled)
        let origin = CGPoint(x: (bounds.width - 63) / 2, y: (bounds.height - 28) / 2)
        func color(_ v: UIRGBA8V1) -> CGColor {
            UIColor(red: CGFloat(v.red)/255, green: CGFloat(v.green)/255, blue: CGFloat(v.blue)/255, alpha: CGFloat(v.alpha)/255).cgColor
        }
        func path(_ geometry: UIAppearanceGeometryV2.Path, _ at: CGPoint) -> CGPath {
            var translation = CGAffineTransform(translationX: at.x, y: at.y)
            return try! AppearanceNativePathsV2.make(geometry, density1024: 1024).copy(using: &translation)!
        }
        let track = path(UIAppearanceGeometryV2.track(), origin)
        context.addPath(track); context.setFillColor(color(paint.track)); context.fillPath(using: .winding)
        context.addPath(track); context.setFillColor(color(paint.overlay)); context.fillPath(using: .winding)
        let thumb = UIAppearanceGeometryV2.thumbOrigin(checked: isOn, direction: direction)
        context.addPath(path(UIAppearanceGeometryV2.thumb(), CGPoint(x: origin.x+CGFloat(thumb.x64)/64, y: origin.y+CGFloat(thumb.y64)/64)))
        context.setFillColor(color(paint.thumb)); context.fillPath(using: .winding)
        if isFocused && isEnabled {
            let lineWidth = CGFloat(states.focus.width64)/64
            let box = CGRect(origin: origin, size: CGSize(width: 63, height: 28)).insetBy(dx: lineWidth/2, dy: lineWidth/2)
            let outline = try! UIAppearanceGeometryV2.group(width64: UIAppearanceGeometryV2.measuredExtent64(Double(box.width)), height64: UIAppearanceGeometryV2.measuredExtent64(Double(box.height)), radius64: states.focus.radius64-states.focus.width64/2)
            context.addPath(path(outline, box.origin)); context.setStrokeColor(color(states.focus.color)); context.setLineWidth(lineWidth); context.strokePath()
        }
    }
}

/// UIKit's documented scroll arbitration is retained, with the explicit
/// UIControl exception needed so a touch that starts on this toggle can scroll.
@MainActor final class ToggleScrollView: UIScrollView {
    override func touchesShouldCancel(in view: UIView) -> Bool {
        if view is AuthoredToggleCarrier { return true }
        return super.touchesShouldCancel(in: view)
    }
}
