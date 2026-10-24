#if canImport(UIKit)
import UIKit
import MixerUI

@MainActor enum AppearanceNativeMathV2 {
    static func points(_ value: UInt32) -> CGFloat { CGFloat(value) / 64 }
    static func extent(_ value: CGFloat) throws -> CGFloat { points(try UIAppearanceGeometryV2.measuredExtent64(Double(value))) }
    static func color(_ value: UIRGBA8V1) -> UIColor {
        UIColor(red: CGFloat(value.red)/255, green: CGFloat(value.green)/255, blue: CGFloat(value.blue)/255, alpha: CGFloat(value.alpha)/255)
    }
    static func font(_ text: UIResolvedTextV2) -> UIFont {
        let weight: UIFont.Weight = switch text.metrics.weight { case .w400: .regular; case .w500: .medium; case .w600: .semibold; case .w700: .bold }
        return .systemFont(ofSize: points(text.metrics.size64), weight: weight)
    }
    static func insets(_ value: UIInsets64V1, rtl: Bool) -> UIEdgeInsets {
        UIEdgeInsets(top: points(value.top), left: points(rtl ? value.trailing : value.leading), bottom: points(value.bottom), right: points(rtl ? value.leading : value.trailing))
    }
    static func path(_ geometry: UIAppearanceGeometryV2.Path, density: UInt16, origin: CGPoint = .zero) throws -> CGPath {
        let path = try AppearanceNativePathsV2.make(geometry, density1024: density)
        var transform = CGAffineTransform(translationX: origin.x * CGFloat(density)/1024, y: origin.y * CGFloat(density)/1024)
        guard let copy = path.copy(using: &transform) else { throw UIAppearanceErrorV2.geometry }
        return copy
    }
    static func outlinePath(_ bounds: CGRect, radius: UInt32, density: UInt16) throws -> CGPath {
        try path(UIAppearanceGeometryV2.group(width64: UIAppearanceGeometryV2.measuredExtent64(Double(bounds.width)),
            height64: UIAppearanceGeometryV2.measuredExtent64(Double(bounds.height)), radius64: radius), density: density, origin: bounds.origin)
    }
}

/// All paths are prepared physical pixels; draw performs exactly one inverse
/// density conversion to UIKit points. Colors remain unpremultiplied UIColor.
@MainActor class AppearancePaintViewV2: UIView {
    struct Shape { let path: CGPath; let fill: UIColor; let stroke: UIColor?; let width: CGFloat }
    var shapes: [Shape] = [] { didSet { setNeedsDisplay() } }
    var density: UInt16 = 1024
    override init(frame: CGRect) { super.init(frame: frame); isOpaque = false; backgroundColor = .clear }
    required init?(coder: NSCoder) { fatalError("init(coder:) unsupported") }
    override func draw(_ rect: CGRect) {
        guard let context = UIGraphicsGetCurrentContext() else { return }
        context.saveGState(); context.scaleBy(x: 1024/CGFloat(density), y: 1024/CGFloat(density))
        for shape in shapes {
            context.addPath(shape.path); context.setFillColor(shape.fill.cgColor); context.fillPath(using: .winding)
            if let stroke = shape.stroke, shape.width > 0 {
                context.addPath(shape.path); context.setStrokeColor(stroke.cgColor); context.setLineWidth(shape.width * CGFloat(density)/1024); context.strokePath()
            }
        }
        context.restoreGState()
    }
}

@MainActor final class AppearanceCursorV2: UIView, UITextCursorView {
    private(set) var blinkResetCount = 0
    private(set) var blinkRequestCount = 0
    var isBlinking = false { didSet { blinkRequestCount += 1; resetBlinkAnimation() } }
    func resetBlinkAnimation() {
        blinkResetCount += 1
        layer.removeAnimation(forKey: "mixer.native.cursor.blink")
        // Use the presentation layer instead of changing UIKit's alpha/hidden
        // lifecycle. An explicit key-frame cadence restarts visible on every reset.
        guard isBlinking, window != nil else { return }
        let animation = CAKeyframeAnimation(keyPath: "opacity")
        animation.values = [1, 1, 0, 0]
        animation.keyTimes = [0, 0.49, 0.50, 1]
        animation.calculationMode = .discrete; animation.duration = 1
        animation.repeatCount = .infinity; animation.isRemovedOnCompletion = true
        layer.add(animation, forKey: "mixer.native.cursor.blink")
    }
    override func didMoveToWindow() { super.didMoveToWindow(); resetBlinkAnimation() }
}

@MainActor final class AppearanceHighlightV2: UIView, UITextSelectionHighlightView {
    var selectionRects: [UITextSelectionRect] = [] { didSet { setNeedsDisplay() } }
    var paint: UIColor = .clear { didSet { setNeedsDisplay() } }
    override func draw(_ rect: CGRect) {
        guard let context = UIGraphicsGetCurrentContext() else { return }
        context.setFillColor(paint.cgColor)
        for value in selectionRects { context.fill(value.rect) }
    }
}

@MainActor final class AppearanceFieldV2: UITextField {
    var inputAllowed: (() -> Bool)?
    override func insertText(_ text: String) { guard inputAllowed?() == true else { return }; super.insertText(text) }
    override func deleteBackward() { guard inputAllowed?() == true else { return }; super.deleteBackward() }
    override func setMarkedText(_ markedText: String?, selectedRange: NSRange) { guard inputAllowed?() == true else { return }; super.setMarkedText(markedText,selectedRange:selectedRange) }
    override func unmarkText() { guard inputAllowed?() == true else { return }; super.unmarkText() }
    var authoredInsets = UIEdgeInsets.zero
    let cursor = AppearanceCursorV2()
    let highlight = AppearanceHighlightV2()
    private(set) var selectionDisplay: UITextSelectionDisplayInteraction?
    override func textRect(forBounds bounds: CGRect) -> CGRect { bounds.inset(by: authoredInsets) }
    override func editingRect(forBounds bounds: CGRect) -> CGRect { textRect(forBounds: bounds) }
    override func placeholderRect(forBounds bounds: CGRect) -> CGRect { textRect(forBounds: bounds) }
    func installManagedPaints() throws {
        let displays = (interactions + textInputView.interactions).compactMap { $0 as? UITextSelectionDisplayInteraction }.filter { $0.textInput === self }
        guard let display = displays.first, displays.allSatisfy({ $0 === display }), let host = display.view else { throw UIAppearanceErrorV2.unsupportedNativeOperation }
        if selectionDisplay !== display || display.cursorView !== cursor || display.highlightView !== highlight {
            cursor.isUserInteractionEnabled = false; highlight.isUserInteractionEnabled = false
            highlight.backgroundColor = .clear; highlight.isOpaque = false
            display.cursorView = cursor; display.highlightView = highlight
            // Reinstall the SAME public interaction: property assignment alone
            // leaves the native-managed views detached on the qualified runtime.
            host.removeInteraction(display); host.addInteraction(display)
            selectionDisplay = display
        }
        display.isActivated = isFirstResponder
        display.setNeedsSelectionUpdate(); display.layoutManagedSubviews()
        if isFirstResponder {
            guard cursor.window === window, highlight.window === window else { throw UIAppearanceErrorV2.unsupportedNativeOperation }
        }
    }
}

@MainActor final class AppearanceButtonV2: UIButton {
    var stateChanged: (() -> Void)?
    override var isHighlighted: Bool { didSet { stateChanged?() } }
    override func didUpdateFocus(in context: UIFocusUpdateContext, with coordinator: UIFocusAnimationCoordinator) { super.didUpdateFocus(in: context, with: coordinator); stateChanged?() }
}

/// Observe native carrier touches without preventing its own gesture recognizers.
/// Qualified UISwitch gestures do not expose UIControl.isTracking while held.
@MainActor final class AppearancePressObservationV2: UIGestureRecognizer {
    var inputAllowed: (() -> Bool)?
    override func canPrevent(_ preventedGestureRecognizer: UIGestureRecognizer) -> Bool { false }
    override func canBePrevented(by preventingGestureRecognizer: UIGestureRecognizer) -> Bool { false }
    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent) {
        guard inputAllowed?() == true else { state = .failed; return }
        state = state == .possible ? .began : .changed
    }
    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent) { if state == .began || state == .changed { state = .changed } }
    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent) { state = .ended }
    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent) { state = .cancelled }
}
@MainActor final class AppearanceSwitchV2: UISwitch {
    let pressObservation = AppearancePressObservationV2()
    // Store explicit author metadata separately from UIKit's derived checked
    // value; nil continues to use the native control's accessibility semantics.
    var authoredAccessibility: [String:String] = [:]
    override var accessibilityLabel: String? { get { authoredAccessibility["accessibilityLabel"] ?? super.accessibilityLabel } set { super.accessibilityLabel = newValue } }
    override var accessibilityHint: String? { get { authoredAccessibility["accessibilityHint"] ?? super.accessibilityHint } set { super.accessibilityHint = newValue } }
    override var accessibilityValue: String? { get { authoredAccessibility["accessibilityValue"] ?? super.accessibilityValue } set { super.accessibilityValue = newValue } }
    override var accessibilityIdentifier: String? { get { authoredAccessibility["accessibilityIdentifier"] ?? super.accessibilityIdentifier } set { super.accessibilityIdentifier = newValue } }
    var authoredPressed: Bool { isTracking || pressObservation.state == .began || pressObservation.state == .changed }
    var inputAllowed: (() -> Bool)? { didSet { pressObservation.inputAllowed = inputAllowed } }
    var stateChanged: (() -> Void)?
    private(set) var pressObservationCount: UInt64 = 0
    private(set) var cancellationCount: UInt64 = 0
    override var isEnabled: Bool { didSet { pressObservation.isEnabled = isEnabled } }
    override init(frame: CGRect) {
        super.init(frame:frame)
        pressObservation.cancelsTouchesInView = false
        pressObservation.delaysTouchesBegan = false; pressObservation.delaysTouchesEnded = false
        pressObservation.addTarget(self,action:#selector(observedPress))
        addGestureRecognizer(pressObservation)
    }
    required init?(coder:NSCoder) { fatalError("init(coder:) unsupported") }
    @objc private func observedPress() {
        if pressObservation.state == .began, pressObservationCount < UInt64.max { pressObservationCount += 1 }
        if pressObservation.state == .cancelled, cancellationCount < UInt64.max { cancellationCount += 1 }
        stateChanged?()
    }
    override func beginTracking(_ touch: UITouch, with event: UIEvent?) -> Bool { let result = super.beginTracking(touch, with: event); stateChanged?(); return result }
    override func continueTracking(_ touch: UITouch, with event: UIEvent?) -> Bool { let result = super.continueTracking(touch, with: event); stateChanged?(); return result }
    override func endTracking(_ touch: UITouch?, with event: UIEvent?) { super.endTracking(touch, with: event); stateChanged?() }
    override func cancelTracking(with event: UIEvent?) { super.cancelTracking(with: event); stateChanged?() }
    override func didUpdateFocus(in context: UIFocusUpdateContext, with coordinator: UIFocusAnimationCoordinator) { super.didUpdateFocus(in: context, with: coordinator); stateChanged?() }
}

/// Stable native identity record. Owns native input/selection/scroll objects for
/// its entire identity generation; staged records never borrow live controls.
@MainActor final class AppearanceNodeViewV2: AppearancePaintViewV2, UITextFieldDelegate, UIScrollViewDelegate {
    let identity: UINodeIdentity
    let kind: NodeKind
    let label = UILabel()
    var selectable: UITextView?
    var button: AppearanceButtonV2?
    var field: AppearanceFieldV2?
    var toggle: AppearanceSwitchV2?
    var scroll: UIScrollView?
    var inputAllowed: (() -> Bool)?
    var event: ((UIEventKind, UIValue) -> Void)?
    var stateChanged: (() -> Void)?
    var fault: ((Error) -> Void)?
    var scrollChanged: (() -> Void)?
    var togglePaints: UIToggleValuesV2?
    private var retainedToggleValue: Bool?
    var maximumStringBytes = 16_384
    var semanticSize = CGSize.zero
    var firstBaseline: CGFloat?
    var lastBaseline: CGFloat?
    var visualRect = CGRect.zero
    var contentRect = CGRect.zero
    var node: UIResolvedAppearanceNodeV2
    var plan: UIResolvedAppearancePlanV2

    init(node: UIResolvedAppearanceNodeV2, plan: UIResolvedAppearancePlanV2) {
        identity = node.identity; kind = node.kind; self.node = node; self.plan = plan
        super.init(frame: .zero)
        label.backgroundColor = .clear; label.adjustsFontForContentSizeCategory = false
        label.numberOfLines = 0; label.lineBreakMode = .byTruncatingTail
        switch node.recipe {
        case let .text(text) where text.selectable:
            let textView = UITextView(); textView.isEditable = false; textView.isSelectable = true; textView.isScrollEnabled = false
            textView.textContainerInset = .zero; textView.textContainer.lineFragmentPadding = 0
            textView.backgroundColor = .clear; textView.adjustsFontForContentSizeCategory = false
            selectable = textView; addSubview(textView)
        case .text, .section, .navigation:
            addSubview(label)
            if node.kind == .section || node.kind == .navigation { label.accessibilityTraits.insert(.header) }
        case .button:
            let control = AppearanceButtonV2(type: .custom)
            control.backgroundColor = .clear; control.tintColor = .clear
            control.titleLabel?.adjustsFontForContentSizeCategory = false
            control.titleLabel?.numberOfLines = 0; control.titleLabel?.lineBreakMode = .byTruncatingTail
            control.addTarget(self, action: #selector(activate), for: .touchUpInside)
            control.stateChanged = { [weak self] in self?.stateChanged?() }
            button = control; addSubview(control)
        case .textField:
            let control = AppearanceFieldV2(); control.borderStyle = .none
            control.clearButtonMode = .never; control.backgroundColor = .clear
            control.adjustsFontForContentSizeCategory = false; control.delegate = self
            control.addTarget(self, action: #selector(changedText), for: .editingChanged)
            control.addTarget(self, action: #selector(focusChanged), for: [.editingDidBegin, .editingDidEnd])
            field = control; addSubview(control)
        case .toggle:
            addSubview(label); label.isAccessibilityElement = false
            let control = AppearanceSwitchV2()
            // Public layer mask suppresses toolkit visuals without replacing its
            // native input, tracking/cancel, keyboard or accessibility carrier.
            let mask = CAShapeLayer(); mask.path = CGPath(rect: .zero, transform: nil); control.layer.mask = mask
            // UIKit's elevated glass thumb can escape the mask while held.
            // Layer opacity suppresses native rendering without changing the
            // UIView alpha/hidden/input/accessibility properties.
            control.layer.opacity = 0
            control.addTarget(self, action: #selector(changedToggle), for: .valueChanged)
            control.stateChanged = { [weak self] in self?.stateChanged?() }
            toggle = control; addSubview(control)
        case .list:
            let control = UIScrollView(); control.contentInsetAdjustmentBehavior = .never
            control.contentInset = .zero; control.scrollIndicatorInsets = .zero
            control.delegate = self; scroll = control; addSubview(control)
        default: break
        }
        accessibilityIdentifier = node.identity.id
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) unsupported") }

    override func point(inside point: CGPoint, with event: UIEvent?) -> Bool {
        if super.point(inside:point,with:event) { return true }
        guard !isHidden, isUserInteractionEnabled, kind != .list, kind != .navigation else { return false }
        // Semantic row measurement never shrinks the actual input envelope.
        // The final full row ancestor still bounds cross-row hit delivery.
        for input in [button as UIView?,field as UIView?,toggle as UIView?].compactMap({ $0 }) {
            if input.point(inside:convert(point,to:input),with:event) { return true }
        }
        for child in subviews.compactMap({ $0 as? AppearanceNodeViewV2 }) where child.isUserInteractionEnabled && !child.isHidden {
            if child.point(inside:convert(point,to:child),with:event) { return true }
        }
        return false
    }

    @objc private func activate() { event?(.activate, .null) }
    @objc private func changedText() { event?(.textChange, .string(field?.text ?? "")) }
    @objc private func changedToggle() {
        guard let toggle else { return }
        guard inputAllowed?() == true else {
            // A platform gesture can finish after native disable. Restore only
            // this scalar switch value, never serialize/restore an IME buffer.
            if let retainedToggleValue { toggle.setOn(retainedToggleValue,animated:false) }
            return
        }
        retainedToggleValue = toggle.isOn
        stateChanged?(); event?(.valueChange,.bool(toggle.isOn))
    }
    @objc private func focusChanged() {
        guard inputAllowed?() == true else { return }
        do { try field?.installManagedPaints(); stateChanged?() } catch { fault?(error) }
    }
    func textFieldShouldBeginEditing(_ textField: UITextField) -> Bool { inputAllowed?() == true }
    func textFieldShouldClear(_ textField: UITextField) -> Bool { inputAllowed?() == true }
    func textFieldShouldReturn(_ textField: UITextField) -> Bool { guard inputAllowed?() == true else { return false }; event?(.submit, .null); return true }
    func textField(_ textField: UITextField, shouldChangeCharactersIn range: NSRange, replacementString string: String) -> Bool {
        guard inputAllowed?() == true else { return false }
        let proposed = (textField.text ?? "") as NSString
        guard range.location <= proposed.length, range.length <= proposed.length-range.location else { return false }
        return proposed.replacingCharacters(in: range, with: string).utf8.count <= maximumStringBytes
    }
    func scrollViewDidScroll(_ scrollView: UIScrollView) { scrollChanged?() }

    func configure(from staged: AppearanceNodeViewV2, preserveEditing: Bool) throws {
        node = staged.node; plan = staged.plan; density = staged.density; togglePaints = staged.togglePaints
        semanticContentAttribute = staged.semanticContentAttribute
        semanticSize = staged.semanticSize; firstBaseline = staged.firstBaseline; lastBaseline = staged.lastBaseline
        visualRect = staged.visualRect; contentRect = staged.contentRect
        label.frame = staged.label.frame; label.font = staged.label.font; label.text = staged.label.text
        label.numberOfLines = staged.label.numberOfLines; label.textAlignment = staged.label.textAlignment; label.isHidden = staged.label.isHidden; label.accessibilityTraits = staged.label.accessibilityTraits
        if let target = selectable, let source = staged.selectable {
            target.font = source.font
            if target.text != source.text {
                let selection = target.selectedRange
                target.text = source.text
                let count = (target.text ?? "").utf16.count, start = min(selection.location,(target.text ?? "").utf16.count)
                target.selectedRange = NSRange(location:start,length:min(selection.length,count-start))
            }
            target.frame = source.frame; target.textContainer.maximumNumberOfLines = source.textContainer.maximumNumberOfLines
            target.textContainer.lineBreakMode = source.textContainer.lineBreakMode
            target.textAlignment = source.textAlignment
        }
        if let target = button, let source = staged.button {
            target.titleLabel?.font = source.titleLabel?.font; target.setTitle(source.title(for: .normal), for: .normal)
            target.contentHorizontalAlignment = source.contentHorizontalAlignment
            target.titleEdgeInsets = source.titleEdgeInsets; target.contentEdgeInsets = source.contentEdgeInsets
            target.frame = source.frame
        }
        if let target = field, let source = staged.field {
            target.font = source.font; target.authoredInsets = source.authoredInsets; target.frame = source.frame; target.textAlignment = source.textAlignment
            target.accessibilityLabel = source.accessibilityLabel
            if !preserveEditing && target.text != source.text {
                let range = target.selectedTextRange.map { (target.offset(from: target.beginningOfDocument, to: $0.start), target.offset(from: target.beginningOfDocument, to: $0.end)) }
                target.text = source.text
                if let range, let start = target.position(from: target.beginningOfDocument, offset: min(range.0, (target.text ?? "").utf16.count)),
                   let end = target.position(from: target.beginningOfDocument, offset: min(range.1, (target.text ?? "").utf16.count)) {
                    target.selectedTextRange = target.textRange(from: start, to: end)
                }
            }
        }
        if let target = toggle, let source = staged.toggle {
            target.frame = source.frame; target.accessibilityLabel = source.accessibilityLabel
            if !preserveEditing { target.setOn(source.isOn, animated: false) }
            retainedToggleValue = target.isOn
        }
        if let target = scroll, let source = staged.scroll {
            target.frame = source.frame; target.contentSize = source.contentSize
        }
        copyAccessibility(from:staged)
        try repaint()
    }
    var accessibilityLeaf: UIView? { (selectable as UIView?) ?? button ?? field ?? toggle ?? ((kind == .text) ? label : nil) }
    func applyAccessibility(_ properties: [String:UIValue]) throws {
        if accessibilityLeaf == nil, ["accessibilityLabel","accessibilityHint","accessibilityValue"].contains(where: { properties[$0] != nil }) { throw UIAppearanceErrorV2.unsupportedNativeOperation }
        func value(_ key:String) -> String? { if case let .string(value)? = properties[key] { return value }; return nil }
        let target = accessibilityLeaf ?? self
        if let toggle { toggle.authoredAccessibility = properties.compactMapValues { if case let .string(value) = $0 { return value }; return nil } }
        if let label = value("accessibilityLabel") { target.accessibilityLabel = label }
        target.accessibilityHint = value("accessibilityHint")
        target.accessibilityValue = value("accessibilityValue")
        target.accessibilityIdentifier = value("accessibilityIdentifier") ?? identity.id
        if target !== self { accessibilityIdentifier = nil }
    }
    private func copyAccessibility(from staged: AppearanceNodeViewV2) {
        let target = accessibilityLeaf ?? self, source = staged.accessibilityLeaf ?? staged
        toggle?.authoredAccessibility = staged.toggle?.authoredAccessibility ?? [:]
        target.accessibilityLabel = source.accessibilityLabel
        target.accessibilityHint = source.accessibilityHint
        target.accessibilityValue = source.accessibilityValue
        target.accessibilityIdentifier = source.accessibilityIdentifier
        if target !== self { accessibilityIdentifier = nil }
    }

    func repaint() throws {
        if retainedToggleValue == nil, let toggle { retainedToggleValue = toggle.isOn }
        guard let style = plan.style(nodeID: identity.id, pressed: button?.isHighlighted ?? toggle?.authoredPressed ?? false,
                                      focused: field?.isFirstResponder ?? button?.isFocused ?? toggle?.isFocused ?? false) else { throw UIAppearanceErrorV2.shape }
        isUserInteractionEnabled = !node.disabled
        button?.isEnabled = !node.disabled; field?.isEnabled = !node.disabled; toggle?.isEnabled = !node.disabled
        toggle?.layer.opacity = 0
        var result: [Shape] = []
        func rounded(_ rect: CGRect, _ color: UIColor, _ radius: UInt32, _ outline: UIOutlineV2? = nil) throws {
            guard rect.width >= 0, rect.height >= 0 else { throw UIAppearanceErrorV2.layout }
            result.append(Shape(path: try AppearanceNativeMathV2.outlinePath(rect, radius: radius, density: density), fill: color, stroke: nil, width: 0))
            if let outline, outline.width64 > 0 {
                let width = AppearanceNativeMathV2.points(outline.width64), inner = rect.insetBy(dx:width/2,dy:width/2)
                guard inner.width >= 0, inner.height >= 0 else { throw UIAppearanceErrorV2.layout }
                let radius = outline.radius64 > outline.width64/2 ? outline.radius64-outline.width64/2 : 0
                result.append(Shape(path:try AppearanceNativeMathV2.outlinePath(inner,radius:radius,density:density),fill:.clear,stroke:AppearanceNativeMathV2.color(outline.color),width:width))
            }
        }
        switch style.paints {
        case let .text(foreground, background):
            label.textColor = AppearanceNativeMathV2.color(foreground); selectable?.textColor = AppearanceNativeMathV2.color(foreground)
            backgroundColor = AppearanceNativeMathV2.color(background)
        case let .container(background): backgroundColor = AppearanceNativeMathV2.color(background)
        case let .button(paint, focus):
            button?.setTitleColor(AppearanceNativeMathV2.color(paint.label), for: .normal)
            button?.setTitleColor(AppearanceNativeMathV2.color(paint.label), for: .disabled)
            button?.setTitleColor(AppearanceNativeMathV2.color(paint.label), for: .highlighted)
            guard case let .button(_, _, metrics) = node.recipe else { throw UIAppearanceErrorV2.shape }
            try rounded(visualRect, AppearanceNativeMathV2.color(paint.background), metrics.overlayRadius64)
            if let focus { try rounded(visualRect, .clear, focus.radius64, focus) }
        case let .field(paint):
            field?.textColor = AppearanceNativeMathV2.color(paint.text)
            guard case let .textField(placeholder, _, _, _) = node.recipe else { throw UIAppearanceErrorV2.shape }
            field?.attributedPlaceholder = NSAttributedString(string: placeholder, attributes: [.font: field?.font ?? UIFont.systemFont(ofSize: 17), .foregroundColor: AppearanceNativeMathV2.color(paint.placeholder)])
            field?.cursor.backgroundColor = AppearanceNativeMathV2.color(paint.caret)
            field?.highlight.paint = AppearanceNativeMathV2.color(paint.selection)
            try rounded(visualRect, AppearanceNativeMathV2.color(paint.background), paint.outline.radius64, paint.outline)
        case let .toggle(resolvedPaint, resolvedFocus):
            let states = (toggle?.isOn ?? false) ? togglePaints?.on : togglePaints?.off
            let paint = states.map { node.disabled ? $0.disabled : ((toggle?.authoredPressed ?? false) ? $0.pressed : $0.enabled) } ?? resolvedPaint
            let focus = (!node.disabled && (toggle?.isFocused ?? false)) ? states?.focus : resolvedFocus
            label.textColor = AppearanceNativeMathV2.color(paint.label)
            let track = try AppearanceNativeMathV2.path(UIAppearanceGeometryV2.track(), density: density, origin: visualRect.origin)
            result.append(Shape(path: track, fill: AppearanceNativeMathV2.color(paint.track), stroke: nil, width: 0))
            result.append(Shape(path: track, fill: AppearanceNativeMathV2.color(paint.overlay), stroke: nil, width: 0))
            let thumb = UIAppearanceGeometryV2.thumbOrigin(checked: toggle?.isOn ?? false, direction: plan.environment.direction)
            result.append(Shape(path: try AppearanceNativeMathV2.path(UIAppearanceGeometryV2.thumb(), density: density,
                origin: CGPoint(x: visualRect.minX+AppearanceNativeMathV2.points(thumb.x64), y: visualRect.minY+AppearanceNativeMathV2.points(thumb.y64))),
                fill: AppearanceNativeMathV2.color(paint.thumb), stroke: nil, width: 0))
            if let focus { try rounded(visualRect, .clear, focus.radius64, focus) }
        case let .list(canvas, _, _): backgroundColor = AppearanceNativeMathV2.color(canvas)
        case let .section(header, background): label.textColor = header.map(AppearanceNativeMathV2.color); backgroundColor = AppearanceNativeMathV2.color(background)
        case let .navigation(expanded, _, background): label.textColor = expanded.map(AppearanceNativeMathV2.color); backgroundColor = AppearanceNativeMathV2.color(background)
        }
        shapes = result
    }
}
#endif
