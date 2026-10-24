// Compiler-only feasibility probe. No controller/widget is executed.
import UIKit
import CoreText

@MainActor
func windowCaptureDeclarations(_ view: UIView) -> (CGFloat, UIContentSizeCategory, Bool, Bool, Bool)? {
    guard let window = view.window else { return nil }
    _ = view.bounds
    _ = view.safeAreaInsets
    _ = view.effectiveUserInterfaceLayoutDirection
    _ = Locale.current.identifier
    return (window.screen.scale, view.traitCollection.preferredContentSizeCategory,
            UIAccessibility.isBoldTextEnabled, UIAccessibility.isDarkerSystemColorsEnabled,
            UIAccessibility.isReduceMotionEnabled)
}

@MainActor
func selectionAPIDeclarations(_ field: UITextField, caret: UIColor, selection: UIColor) -> Bool {
    // This conditional is intentional: compilation does not prove a built-in
    // editor exposes this interaction or that tint yields exact authored pixels.
    guard let interaction = field.textInputView.interactions.compactMap({ $0 as? UITextSelectionDisplayInteraction }).first else {
        return false
    }
    interaction.cursorView.tintColor = caret
    interaction.highlightView.tintColor = selection
    interaction.setNeedsSelectionUpdate()
    _ = field.markedTextRange
    _ = field.selectedTextRange
    _ = field.interactionState
    return true
}

@MainActor
func switchMaskDeclarations(_ control: UISwitch) {
    let mask = CALayer()
    mask.backgroundColor = UIColor.clear.cgColor
    mask.frame = control.bounds
    control.layer.mask = mask
    control.setOn(true, animated: false)
    _ = control.isTracking
    _ = control.isTouchInside
}

func capturedFontDeclarations(_ data: Data) -> CTFont? {
    guard let provider = CGDataProvider(data: data as CFData), let font = CGFont(provider) else { return nil }
    _ = font.postScriptName
    return CTFontCreateWithGraphicsFont(font, 17, nil, nil)
}
