import UIKit
import MixerUI

/// Qualification prototype only. Native UIButton owns activation, touch
/// tracking, cancellation, focus, keyboard and assistive-technology input.
/// Mixer owns the public selected-state mapping and closed authored paint.
@MainActor final class AuthoredToggleCarrier: UIButton, UIGestureRecognizerDelegate {
    var inputAllowed: (() -> Bool)? { didSet { if inputAllowed?() != true { cancelAuthoredInteraction() } } }
    var stateChanged: ((String) -> Void)?
    var authoredAccessibility: [String: String] = [:]
    var paints: UIToggleValuesV2!
    var direction: UILayoutDirectionV1 = .leftToRight { didSet { if oldValue != direction { cancelAuthoredInteraction() }; setNeedsDisplay() } }
    private(set) var retainedOn = false
    private(set) var primaryCount = 0
    private(set) var acceptedCount = 0
    private(set) var rejectedCount = 0
    private(set) var beginCount = 0
    private(set) var continueCount = 0
    private(set) var endCount = 0
    private(set) var cancellationCount = 0
    private(set) var accessibilityActivationCount = 0
    let slidePan = UIPanGestureRecognizer()
    private(set) var panAcceptedCount = 0
    private(set) var panNoChangeCount = 0
    private(set) var panCancellationCount = 0
    private(set) var previewThumbX: CGFloat?
    private(set) var panActive = false
    private var bindingGeneration: UInt64 = 0
    private var panBindingGeneration: UInt64?
    private var panStartThumbX: CGFloat = 2
    private weak var verticalScrollPan: UIPanGestureRecognizer?
    // Native pan recognition threshold is additionally bounded by this explicit
    // public-delegate admission policy. Translation is in native UIKit points.
    var isOn: Bool { isSelected }
    var authoredPressed: Bool { isHighlighted || panActive }

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
        slidePan.maximumNumberOfTouches = 1
        slidePan.cancelsTouchesInView = true
        slidePan.delaysTouchesBegan = false
        slidePan.delaysTouchesEnded = false
        slidePan.delegate = self
        slidePan.addTarget(self, action: #selector(slideChanged))
        addGestureRecognizer(slidePan)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) unsupported") }

    func setOn(_ value: Bool, animated: Bool) {
        // A binding write never emits valueChanged or primaryActionTriggered.
        cancelAuthoredInteraction()
        bindingGeneration &+= 1
        retainedOn = value
        isSelected = value
        stateChanged?("binding")
    }

    func participateInVerticalScroll(_ scrollView: UIScrollView?) {
        // Rebinding this weak public reference supports stable-identity moves;
        // unlike a permanent require(toFail:), it leaves no old-parent relation.
        cancelAuthoredInteraction()
        verticalScrollPan = scrollView?.panGestureRecognizer
    }

    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldBeRequiredToFailBy otherGestureRecognizer: UIGestureRecognizer) -> Bool {
        // The current native vertical scroll pan waits for our horizontal pan
        // to fail. Vertical admission failure therefore yields to native scroll.
        let result = gestureRecognizer === slidePan && otherGestureRecognizer === verticalScrollPan
        DiagnosticTrace.shared.append("dynamicFailureDecision", ["gesture": DiagnosticTrace.shared.gesture(gestureRecognizer), "other": DiagnosticTrace.shared.gesture(otherGestureRecognizer), "result": result])
        return result
    }

    func cancelAuthoredInteraction() {
        cancelTracking(with: nil)
        if slidePan.state == .began || slidePan.state == .changed {
            slidePan.isEnabled = false
            slidePan.isEnabled = isEnabled
        }
        if panActive || previewThumbX != nil { restorePan("panInvalidated") }
    }

    override func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        let result: Bool
        if gestureRecognizer === slidePan {
            result = isEnabled && inputAllowed?() == true && TogglePanPolicy.admits(slidePan.translation(in: self))
        } else { result = super.gestureRecognizerShouldBegin(gestureRecognizer) }
        DiagnosticTrace.shared.append("shouldBeginDecision", ["gesture": DiagnosticTrace.shared.gesture(gestureRecognizer), "isAuthoredPan": gestureRecognizer === slidePan, "translationInCarrier": DiagnosticTrace.shared.point(slidePan.translation(in: self)), "enabled": isEnabled, "inputAllowed": inputAllowed?() == true, "result": result])
        return result
    }

    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
        DiagnosticTrace.shared.touches("recognizerShouldReceiveTouch", [touch], nil, in: self)
        DiagnosticTrace.shared.append("recognizerReceiveDecision", ["gesture": DiagnosticTrace.shared.gesture(gestureRecognizer), "result": true])
        return true // UIKit's default admission; no additional filter.
    }

    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive event: UIEvent) -> Bool {
        DiagnosticTrace.shared.append("recognizerShouldReceiveEvent", ["gesture": DiagnosticTrace.shared.gesture(gestureRecognizer), "eventTimestamp": event.timestamp, "eventType": event.type.rawValue, "result": true])
        return true // UIKit's default admission; no additional filter.
    }

    private func restorePan(_ reason: String) {
        panCancellationCount += 1
        panActive = false; previewThumbX = nil; panBindingGeneration = nil
        isSelected = retainedOn
        setNeedsDisplay(); stateChanged?(reason)
    }

    @objc private func slideChanged() {
        DiagnosticTrace.shared.append("authoredPanCallback", DiagnosticTrace.shared.gesture(slidePan))
        switch slidePan.state {
        case .began:
            guard isEnabled, inputAllowed?() == true else { restorePan("panBeginRejected"); return }
            panBindingGeneration = bindingGeneration
            panStartThumbX = CGFloat(UIAppearanceGeometryV2.thumbOrigin(checked: retainedOn, direction: direction).x64) / 64
            panActive = true
            updatePanPreview()
        case .changed:
            guard isEnabled, inputAllowed?() == true, panBindingGeneration == bindingGeneration else { cancelAuthoredInteraction(); return }
            updatePanPreview()
        case .ended:
            guard isEnabled, inputAllowed?() == true, panBindingGeneration == bindingGeneration else { restorePan("panEndRejected"); return }
            let point = slidePan.location(in: self)
            guard TogglePanPolicy.permitsRelease(y:point.y, height:bounds.height) else { restorePan("panVerticalExit"); return }
            let x = TogglePanPolicy.previewX(startX:panStartThumbX, translationX:slidePan.translation(in:self).x)
            let checked = TogglePanPolicy.checked(x:x, previous:retainedOn, direction:direction)
            let changed = checked != retainedOn
            panActive = false; previewThumbX = nil; panBindingGeneration = nil
            retainedOn = checked; isSelected = checked
            if changed {
                acceptedCount += 1; panAcceptedCount += 1
                stateChanged?("panAccepted"); sendActions(for: .valueChanged)
            } else { panNoChangeCount += 1; stateChanged?("panNoChange") }
            setNeedsDisplay()
        case .cancelled, .failed:
            if panActive || previewThumbX != nil { restorePan("panCancelled") }
        default: break
        }
    }

    private func updatePanPreview() {
        previewThumbX = TogglePanPolicy.previewX(startX:panStartThumbX, translationX:slidePan.translation(in:self).x)
        setNeedsDisplay(); stateChanged?("panPreview")
    }

    @objc private func primaryAction() {
        DiagnosticTrace.shared.append("carrierPrimaryTarget", ["selectedOnEntry": isSelected, "retainedOnEntry": retainedOn, "enabled": isEnabled, "inputAllowed": inputAllowed?() == true])
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
            if !isEnabled { cancelAuthoredInteraction() }
            slidePan.isEnabled = isEnabled
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
        DiagnosticTrace.shared.append("carrierAccessibilityActivateEnter", ["selected": isSelected, "enabled": isEnabled, "inputAllowed": inputAllowed?() == true])
        guard isEnabled, inputAllowed?() == true else {
            DiagnosticTrace.shared.append("carrierAccessibilityActivateReturn", ["result": false, "gateRejected": true, "selected": isSelected]); return false
        }
        let result = super.accessibilityActivate()
        DiagnosticTrace.shared.append("carrierAccessibilityActivateReturn", ["result": result, "gateRejected": false, "selected": isSelected])
        return result
    }
    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) { DiagnosticTrace.shared.touches("carrierTouchesBegan", touches, event, in: self); super.touchesBegan(touches, with: event) }
    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) { DiagnosticTrace.shared.touches("carrierTouchesMoved", touches, event, in: self); super.touchesMoved(touches, with: event) }
    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) { DiagnosticTrace.shared.touches("carrierTouchesEnded", touches, event, in: self); super.touchesEnded(touches, with: event) }
    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) { DiagnosticTrace.shared.touches("carrierTouchesCancelled", touches, event, in: self); super.touchesCancelled(touches, with: event) }
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
        let paintOn = previewThumbX.map { TogglePanPolicy.checked(x:$0, previous:isOn, direction:direction) } ?? isOn
        let states = paintOn ? paints.on : paints.off
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
        context.addPath(path(UIAppearanceGeometryV2.thumb(), CGPoint(x: origin.x+(previewThumbX ?? CGFloat(thumb.x64)/64), y: origin.y+CGFloat(thumb.y64)/64)))
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
    override func touchesShouldBegin(_ touches: Set<UITouch>, with event: UIEvent?, in view: UIView) -> Bool {
        let result = super.touchesShouldBegin(touches, with: event, in: view)
        DiagnosticTrace.shared.touches("scrollTouchesShouldBegin", touches, event, in: view)
        DiagnosticTrace.shared.append("scrollBeginDecision", ["viewClass": String(describing: type(of: view)), "result": result])
        return result
    }
    override func touchesShouldCancel(in view: UIView) -> Bool {
        let result = view is AuthoredToggleCarrier ? true : super.touchesShouldCancel(in: view)
        DiagnosticTrace.shared.append("scrollCancelDecision", ["viewClass": String(describing: type(of: view)), "result": result])
        return result
    }
}
