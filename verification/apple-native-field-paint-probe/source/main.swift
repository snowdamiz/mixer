import UIKit

// An isolated public-UIKit feasibility probe. No Mixer module is linked.
// Views are installed only through UITextSelectionDisplayInteraction's public
// managed-view properties. No private selectors, KVC, or subview traversal.
@MainActor final class AuthoredCursor: UIView, UITextCursorView {
    var isBlinking = false
    func resetBlinkAnimation() {}
}

@MainActor final class AuthoredHighlight: UIView, UITextSelectionHighlightView {
    var selectionRects: [UITextSelectionRect] = [] { didSet { setNeedsDisplay() } }
    var paint = UIColor.clear { didSet { setNeedsDisplay() } }
    override func draw(_ rect: CGRect) {
        guard let context = UIGraphicsGetCurrentContext() else { return }
        context.setFillColor(paint.cgColor)
        for selection in selectionRects { context.fill(selection.rect) }
    }
}

@MainActor final class ProbeController: UIViewController {
    let field = UITextField(frame: CGRect(x: 30, y: 180, width: 330, height: 60))
    let label = UILabel(frame: CGRect(x: 24, y: 80, width: 345, height: 80))
    var display: UITextSelectionDisplayInteraction?
    var customCursor: AuthoredCursor?
    var customHighlight: AuthoredHighlight?
    var originalCursor: (UIView & UITextCursorView)?
    var originalHighlight: (UIView & UITextSelectionHighlightView)?
    var observations: [[String: Any]] = []
    var commandTimer: Timer?
    var lastCommand = ""
    let directory = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .white
        label.numberOfLines = 4
        label.font = .systemFont(ofSize: 15)
        label.textColor = .black
        view.addSubview(label)
        field.borderStyle = .none
        field.backgroundColor = .white
        field.textColor = .black
        field.tintColor = .blue // Deliberately different from authored paints.
        field.font = .monospacedSystemFont(ofSize: 24, weight: .regular)
        field.autocorrectionType = .no
        field.spellCheckingType = .no
        field.smartQuotesType = .no
        field.smartDashesType = .no
        field.text = "alpha      omega"
        view.addSubview(field)
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        field.becomeFirstResponder()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { self.stage("discovery") }
        commandTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self, let command = try? String(contentsOf: self.directory.appendingPathComponent("command.txt"), encoding: .utf8),
                      command != self.lastCommand else { return }
                self.lastCommand = command
                self.stage(command)
            }
        }
    }

    func range(_ offset: Int, _ length: Int) -> UITextRange? {
        guard let start = field.position(from: field.beginningOfDocument, offset: offset),
              let end = field.position(from: start, offset: length) else { return nil }
        return field.textRange(from: start, to: end)
    }

    func snapshot() -> [String: Any] {
        var result: [String: Any] = [
            "firstResponder": field.isFirstResponder,
            "enabled": field.isEnabled,
            "text": field.text ?? "",
            "secure": field.isSecureTextEntry,
            "fieldIdentity": String(describing: ObjectIdentifier(field)),
            "textInputViewIdentity": String(describing: ObjectIdentifier(field.textInputView)),
            "publicFieldInteractionCount": field.interactions.count,
            "publicTextInputViewInteractionCount": field.textInputView.interactions.count,
            "fieldSelectionDisplayInteractionCount": field.interactions.filter { $0 is UITextSelectionDisplayInteraction }.count,
            "textInputViewSelectionDisplayInteractionCount": field.textInputView.interactions.filter { $0 is UITextSelectionDisplayInteraction }.count,
            "os": UIDevice.current.systemVersion,
            "scale": view.window?.screen.scale ?? 0,
            "fieldTintRGBA": rgba(field.tintColor),
            "fieldRectInWindow": rectArray(field.convert(field.bounds, to: view.window))
        ]
        if let selection = field.selectedTextRange {
            result["selectedRange"] = [field.offset(from: field.beginningOfDocument, to: selection.start), field.offset(from: selection.start, to: selection.end)]
            result["selectionRectsInWindow"] = field.selectionRects(for: selection).map { rectArray(field.textInputView.convert($0.rect, to: view.window)) }
            result["caretRectInWindow"] = rectArray(field.textInputView.convert(field.caretRect(for: selection.start), to: view.window))
        }
        if let marked = field.markedTextRange {
            result["markedRange"] = [field.offset(from: field.beginningOfDocument, to: marked.start), field.offset(from: marked.start, to: marked.end)]
            result["markedText"] = field.text(in: marked) ?? ""
        } else { result["markedRange"] = NSNull() }
        if let display {
            result["displayActivated"] = display.isActivated
            result["cursorHidden"] = display.cursorView.isHidden
            result["cursorAlpha"] = display.cursorView.alpha
            result["cursorRectInWindow"] = rectArray(display.cursorView.convert(display.cursorView.bounds, to: view.window))
            result["highlightHidden"] = display.highlightView.isHidden
            result["highlightAlpha"] = display.highlightView.alpha
            result["managedHighlightSelectionRects"] = display.highlightView.selectionRects.map { rectArray($0.rect) }
            result["highlightRectInWindow"] = rectArray(display.highlightView.convert(display.highlightView.bounds, to: view.window))
            result["cursorIsAuthored"] = display.cursorView === customCursor
            result["highlightIsAuthored"] = display.highlightView === customHighlight
            result["displayTextInputIsField"] = display.textInput === field
            result["cursorInNativeWindow"] = display.cursorView.window === view.window
            result["highlightInNativeWindow"] = display.highlightView.window === view.window
            result["displayViewIsField"] = display.view === field
            result["displayViewIsTextInputView"] = display.view === field.textInputView
            result["cursorTintRGBA"] = rgba(display.cursorView.tintColor)
            result["highlightTintRGBA"] = rgba(display.highlightView.tintColor)
            if let color = display.cursorView.backgroundColor { result["cursorBackgroundRGBA"] = rgba(color) }
            if let customHighlight { result["authoredHighlightPaintRGBA"] = rgba(customHighlight.paint) }
            result["cursorBlinkRequested"] = display.cursorView.isBlinking
            result["originalCursorInWindow"] = originalCursor?.window === view.window
            result["originalHighlightInWindow"] = originalHighlight?.window === view.window
            result["originalHighlightHidden"] = originalHighlight?.isHidden ?? true
        }
        return result
    }

    func rectArray(_ rect: CGRect) -> [Double] {
        [rect.minX, rect.minY, rect.width, rect.height].map(Double.init)
    }

    func rgba(_ color: UIColor) -> [Double] {
        var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        color.getRed(&r, green: &g, blue: &b, alpha: &a)
        return [r, g, b, a].map(Double.init)
    }

    func discover() {
        // Both receivers are public APIs. No recursive or private-view search.
        let candidates = field.textInputView.interactions + field.interactions
        display = candidates.compactMap { $0 as? UITextSelectionDisplayInteraction }.first
    }

    func replacePaintViews() {
        guard let display else { return }
        originalCursor = display.cursorView
        originalHighlight = display.highlightView
        let cursor = AuthoredCursor(frame: .zero)
        cursor.backgroundColor = UIColor(red: 1, green: 0, blue: 0, alpha: 1)
        cursor.isUserInteractionEnabled = false
        let highlight = AuthoredHighlight(frame: .zero)
        highlight.backgroundColor = .clear
        highlight.isOpaque = false
        highlight.isUserInteractionEnabled = false
        highlight.paint = UIColor(red: 0, green: 1, blue: 0, alpha: 61.0 / 255.0)
        customCursor = cursor
        customHighlight = highlight
        display.cursorView = cursor
        display.highlightView = highlight
    }

    func stage(_ name: String) {
        discover()
        let before = snapshot()
        switch name {
        case "discovery":
            field.selectedTextRange = range(5, 6)
        case "native-selection":
            field.selectedTextRange = range(5, 6)
        case "native-managed-tints":
            display?.cursorView.tintColor = .red
            display?.highlightView.tintColor = UIColor(red: 0, green: 1, blue: 0, alpha: 61.0 / 255.0)
        case "native-caret-red":
            field.selectedTextRange = range(5, 0)
        case "native-selection-alpha128":
            display?.highlightView.tintColor = UIColor(red: 0, green: 1, blue: 0, alpha: 128.0 / 255.0)
            field.selectedTextRange = range(5, 6)
        case "native-selection-opaque":
            display?.highlightView.tintColor = .green
        case "native-selection-clear":
            display?.highlightView.tintColor = .clear
        case "install-selection":
            field.selectedTextRange = range(5, 6)
            replacePaintViews()
        case "reactivate-selection":
            display?.isActivated = false
            display?.isActivated = true
        case "reinstall-selection", "reinstall-marked":
            if let display, let host = display.view {
                host.removeInteraction(display)
                host.addInteraction(display)
                display.isActivated = true
            }
        case "authored-caret":
            field.selectedTextRange = range(5, 0)
        case "caret-alpha61":
            customCursor?.backgroundColor = UIColor(red: 1, green: 0, blue: 0, alpha: 61.0 / 255.0)
        case "caret-alpha128":
            customCursor?.backgroundColor = UIColor(red: 1, green: 0, blue: 0, alpha: 128.0 / 255.0)
        case "selection-alpha61":
            field.selectedTextRange = range(5, 6)
        case "selection-alpha128":
            customHighlight?.paint = UIColor(red: 0, green: 1, blue: 0, alpha: 128.0 / 255.0)
        case "selection-clear":
            customHighlight?.paint = .clear
        case "selection-caret-green":
            customCursor?.backgroundColor = .green
            customHighlight?.paint = UIColor(red: 1, green: 0, blue: 0, alpha: 61.0 / 255.0)
        case "caret-green":
            field.selectedTextRange = range(5, 0)
        case "caret-clear":
            customCursor?.backgroundColor = .clear
        case "marked-text":
            field.selectedTextRange = range(5, 0)
            field.setMarkedText("にほん", selectedRange: NSRange(location: 3, length: 0))
        case "restyle-marked":
            customCursor?.backgroundColor = .red
            customHighlight?.paint = UIColor(red: 0, green: 1, blue: 0, alpha: 61.0 / 255.0)
            field.font = .monospacedSystemFont(ofSize: 25, weight: .regular)
            field.textColor = .darkGray
        case "commit-marked":
            field.unmarkText()
            field.insertText("!")
        case "delete-native":
            field.deleteBackward()
        case "disable":
            customCursor?.backgroundColor = .clear
            customHighlight?.paint = .clear
            field.isEnabled = false
        default: break
        }
        label.text = "Public UIKit field paint probe\n\(name)\nNative display interaction: \(display != nil)"
        display?.setNeedsSelectionUpdate()
        display?.layoutManagedSubviews()
        view.setNeedsLayout()
        view.layoutIfNeeded()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
            self.display?.layoutManagedSubviews()
            var observation: [String: Any] = ["stage": name, "before": before, "after": self.snapshot()]
            observation["paintMutationUsesOnlyManagedPublicProperties"] = true
            self.observations.append(observation)
            let data = try! JSONSerialization.data(withJSONObject: self.observations, options: [.prettyPrinted, .sortedKeys])
            try! data.write(to: self.directory.appendingPathComponent("observations.json"), options: .atomic)
            // Raster from native hierarchy supplements the simctl compositor PNG.
            let image = UIGraphicsImageRenderer(bounds: self.view.window!.bounds).image { _ in
                self.view.window!.drawHierarchy(in: self.view.window!.bounds, afterScreenUpdates: true)
            }
            try! image.pngData()!.write(to: self.directory.appendingPathComponent(name + "-hierarchy.png"))
            try! name.write(to: self.directory.appendingPathComponent("stage.txt"), atomically: true, encoding: .utf8)
        }
    }
}

@MainActor final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    let controller = ProbeController()
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        window = UIWindow(frame: UIScreen.main.bounds)
        window?.rootViewController = controller
        window?.makeKeyAndVisible()
        return true
    }
    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey: Any] = [:]) -> Bool {
        controller.stage(url.lastPathComponent)
        return true
    }
}

UIApplicationMain(CommandLine.argc, CommandLine.unsafeArgv, nil, NSStringFromClass(AppDelegate.self))
