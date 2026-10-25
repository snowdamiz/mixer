import UIKit
import MixerUI

@MainActor final class PrototypeController: UIViewController {
    let toggle = AuthoredToggleCarrier(type: .custom)
    let scroll = ToggleScrollView()
    let titleLabel = UILabel()
    let stateLabel = UILabel()
    let rowLabel = UILabel()
    let nextButton = UIButton(type: .custom)
    let referenceButton = UIButton(type: .custom)
    let referencePanSurface = DiagnosticPanSurface(frame: .zero)
    let theme: UIThemeV2
    var allowed = true
    var eventCount = 0
    var eventValues: [Bool] = []
    var events: [[String: Any]] = []
    var checks: [[String: Any]] = []
    var timer: Timer?
    var stage = "initial"
    var recording = false
    var referencePrimaryCount = 0
    var referenceValueCount = 0
    var referencePrimaryValues: [Bool] = []
    var diagnosticOperations: [[String: Any]] = []
    var semanticOperations: [[String: Any]] = []
    var panCommitMode: String?
    var panCommitHookFired = false
    var panCommitInitial = false
    var panCommitRecords: [[String: Any]] = []
    var interruptionMode: String?
    var interruptionQueued = false
    var nativeInterruptions: [[String: Any]] = []
    var diagnosticSuiteState = "not-run"
    var diagnosticSuiteActive = false
    var lastTraceRevision = 0
    var lastFocusContextRevision = 0
    let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]

    init() {
        guard case let .shared(theme) = try! UIAppearanceDescriptorCodecV2.mixerDefaultV2().mode else { fatalError() }
        self.theme = theme
        super.init(nibName: nil, bundle: nil)
    }
    required init?(coder: NSCoder) { fatalError() }
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(white: 0.95, alpha: 1)
        titleLabel.text = "Authored UIKit toggle"; titleLabel.font = .systemFont(ofSize: 24, weight: .bold)
        stateLabel.font = .monospacedSystemFont(ofSize: 13, weight: .regular); stateLabel.numberOfLines = 0
        view.addSubview(titleLabel); view.addSubview(stateLabel); view.addSubview(scroll)
        scroll.backgroundColor = .white; scroll.layer.cornerRadius = 20
        scroll.canCancelContentTouches = true; scroll.delaysContentTouches = true
        scroll.contentSize = CGSize(width: 1, height: 1200)
        rowLabel.text = "Sync entries"; rowLabel.font = .systemFont(ofSize: 17)
        rowLabel.isAccessibilityElement = false
        toggle.paints = theme.light.toggle
        toggle.authoredAccessibility = ["accessibilityLabel":"Sync entries", "accessibilityHint":"Updates the sync preference", "accessibilityIdentifier":"authored-toggle"]
        toggle.inputAllowed = { [weak self] in self?.allowed == true }
        toggle.stateChanged = { [weak self] reason in self?.record(reason); self?.queueNativeInterruption(reason); self?.exercisePanCommitHook(reason) }
        toggle.addTarget(self, action: #selector(changed), for: .valueChanged)
        scroll.addSubview(rowLabel); scroll.addSubview(toggle)
        toggle.participateInVerticalScroll(scroll)
        scroll.panGestureRecognizer.addTarget(self, action: #selector(scrollPanChanged))
        referenceButton.configuration = nil
        referenceButton.menu = nil
        referenceButton.showsMenuAsPrimaryAction = false
        referenceButton.changesSelectionAsPrimaryAction = true
        referenceButton.isAccessibilityElement = true
        referenceButton.accessibilityIdentifier = "plain-uibutton-reference"
        referenceButton.accessibilityLabel = "Plain UIKit selection reference"
        referenceButton.setTitle("Plain UIButton reference", for: .normal)
        referenceButton.setTitleColor(.systemBlue, for: .normal)
        referenceButton.addTarget(self, action: #selector(referencePrimary), for: .primaryActionTriggered)
        referenceButton.addTarget(self, action: #selector(referenceValueChanged), for: .valueChanged)
        let referenceEvents: [(UIControl.Event, String)] = [(.touchDown, "touchDown"), (.touchDragInside, "touchDragInside"), (.touchDragOutside, "touchDragOutside"), (.touchUpInside, "touchUpInside"), (.touchUpOutside, "touchUpOutside"), (.touchCancel, "touchCancel")]
        for (event, name) in referenceEvents {
            referenceButton.addAction(UIAction { _ in DiagnosticTrace.shared.append("referenceControlEvent", ["event": name]) }, for: event)
        }
        scroll.addSubview(referenceButton)
        view.addSubview(referencePanSurface)
        for n in 1...12 {
            let label = UILabel(frame: CGRect(x: 16, y: 230+n*70, width: 300, height: 32))
            label.text = "Native scroll row \(n)"; label.font = .systemFont(ofSize: 17)
            scroll.addSubview(label)
        }
        nextButton.setTitle("Next native focus target", for: .normal)
        nextButton.setTitleColor(.systemBlue, for: .normal)
        nextButton.accessibilityIdentifier = "next-focus"
        nextButton.addAction(UIAction { [weak self] _ in self?.record("nextButton") }, for: .primaryActionTriggered)
        view.addSubview(nextButton)
        timer = Timer.scheduledTimer(withTimeInterval: 0.03, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated {
                self?.readCommand()
                if let self, (self.lastTraceRevision != DiagnosticTrace.shared.revision || self.lastFocusContextRevision != DiagnosticTrace.shared.focusContextRevision) { self.persist() }
            }
        }
    }
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        titleLabel.frame = CGRect(x: 24, y: view.safeAreaInsets.top+20, width: view.bounds.width-48, height: 34)
        stateLabel.frame = CGRect(x: 24, y: titleLabel.frame.maxY+10, width: view.bounds.width-48, height: 76)
        scroll.frame = CGRect(x: 16, y: stateLabel.frame.maxY+12, width: view.bounds.width-32, height: 390)
        rowLabel.frame = CGRect(x: 16, y: 30, width: scroll.bounds.width-110, height: 44)
        toggle.frame = CGRect(x: scroll.bounds.width-83, y: 30, width: 63, height: 44)
        referenceButton.frame = CGRect(x: 16, y: 100, width: 280, height: 44)
        nextButton.frame = CGRect(x: 24, y: scroll.frame.maxY+24, width: view.bounds.width-48, height: 44)
        referencePanSurface.frame = CGRect(x: 24, y: nextButton.frame.maxY+20, width: min(300, view.bounds.width-48), height: 60)
        if events.isEmpty { record("initial") }
    }
    @objc func changed() { eventCount += 1; eventValues.append(toggle.isOn); record("valueChanged") }
    @objc func referencePrimary() {
        referencePrimaryCount += 1; referencePrimaryValues.append(referenceButton.isSelected)
        DiagnosticTrace.shared.append("referencePrimaryTarget", ["selectedOnEntry": referenceButton.isSelected])
        record("referencePrimary")
    }
    @objc func referenceValueChanged() { referenceValueCount += 1; record("referenceValueChanged") }
    @objc func scrollPanChanged() {
        DiagnosticTrace.shared.append("scrollPanCallback", ["gesture": DiagnosticTrace.shared.gesture(scroll.panGestureRecognizer), "contentOffset": DiagnosticTrace.shared.point(scroll.contentOffset), "dragging": scroll.isDragging, "tracking": scroll.isTracking])
    }
    func snapshot() -> [String:Any] {
        ["identity":String(describing: ObjectIdentifier(toggle)), "isOn":toggle.isOn, "retainedOn":toggle.retainedOn,
         "enabled":toggle.isEnabled, "allowed":allowed, "highlighted":toggle.isHighlighted, "authoredPressed":toggle.authoredPressed, "tracking":toggle.isTracking,
         "touchInside":toggle.isTouchInside, "focused":toggle.isFocused, "firstResponder":toggle.isFirstResponder,
         "panState":toggle.slidePan.state.rawValue, "panActive":toggle.panActive, "previewThumbX":toggle.previewThumbX.map { $0 as Any } ?? NSNull(),
         "panAcceptedCount":toggle.panAcceptedCount, "panNoChangeCount":toggle.panNoChangeCount, "panCancellationCount":toggle.panCancellationCount,
         "primaryCount":toggle.primaryCount, "acceptedCount":toggle.acceptedCount, "rejectedCount":toggle.rejectedCount,
         "beginCount":toggle.beginCount, "continueCount":toggle.continueCount, "endCount":toggle.endCount,
         "cancellationCount":toggle.cancellationCount, "accessibilityActivationCount":toggle.accessibilityActivationCount,
         "eventCount":eventCount, "eventValues":eventValues, "traits":toggle.accessibilityTraits.rawValue,
         "toggleTrait":toggle.accessibilityTraits.contains(.toggleButton), "buttonTrait":toggle.accessibilityTraits.contains(.button),
         "selectedTrait":toggle.accessibilityTraits.contains(.selected), "notEnabledTrait":toggle.accessibilityTraits.contains(.notEnabled),
         "label":toggle.accessibilityLabel ?? NSNull(), "hint":toggle.accessibilityHint ?? NSNull(), "value":toggle.accessibilityValue ?? NSNull(),
         "buttonType":toggle.buttonType.rawValue, "configurationNil":toggle.configuration == nil, "menuNil":toggle.menu == nil,
         "nativeToggleSelection":toggle.changesSelectionAsPrimaryAction, "rtl":toggle.direction == .rightToLeft,
         "scrollOffsetY":scroll.contentOffset.y, "frameInWindow":NSCoder.string(for:toggle.convert(toggle.bounds, to: nil)),
         "bounds":NSCoder.string(for:toggle.bounds), "displayScale":view.window?.screen.scale ?? 0]
    }
    func record(_ reason: String) {
        guard !recording else { return }; recording = true; defer { recording = false }
        let current = snapshot()
        events.append(["sequence":events.count, "uptime":ProcessInfo.processInfo.systemUptime, "stage":stage, "reason":reason, "state":current])
        stateLabel.text = "\(stage)\nvalue \(toggle.isOn) · events \(eventCount)\npressed \(toggle.authoredPressed) · focus \(toggle.isFocused)"
        persist()
    }
    func persist() {
        let trace = DiagnosticTrace.shared
        let result: [String:Any] = ["scope":"Isolated UIKit diagnostics; no production adapter, original candidate repair, native qualification, or physical VoiceOver qualification", "stage":stage, "state":snapshot(), "events":events, "checks":checks, "diagnosticSuiteState": diagnosticSuiteState, "diagnosticOperations": diagnosticOperations, "semanticOperations": semanticOperations, "nativeInterruptions": nativeInterruptions, "panCommitRecords": panCommitRecords, "diagnosticTrace": trace.entries, "diagnosticTraceDropped": trace.dropped, "focusContextSchema": "mixer.apple-toggle.focus-context.1", "focusContexts": trace.focusContextEntries, "focusContextDropped": trace.focusContextDropped, "focusContextRevision": trace.focusContextRevision, "reference": operationSnapshot(reference: true), "referencePan": trace.gesture(referencePanSurface.pan)]
        let data = try! JSONSerialization.data(withJSONObject:result, options:[.prettyPrinted,.sortedKeys])
        try! data.write(to:documents.appendingPathComponent("observations.json"), options:.atomic)
        try! stage.write(to:documents.appendingPathComponent("stage.txt"), atomically:true, encoding:.utf8)
        lastTraceRevision = trace.revision
        lastFocusContextRevision = trace.focusContextRevision
    }
    func check(_ name: String, _ pass: Bool) { checks.append(["name":name,"pass":pass]) }
    struct DiagnosticOperation {
        let name: String
        let reference: Bool
        let initial: Bool
        let accessibility: Bool
        var enabled = true
        var allowed = true
    }
    var operations: [DiagnosticOperation] {
        [DiagnosticOperation(name: "carrier-primary-off-to-on", reference: false, initial: false, accessibility: false),
         DiagnosticOperation(name: "carrier-primary-on-to-off", reference: false, initial: true, accessibility: false),
         DiagnosticOperation(name: "carrier-stale-primary", reference: false, initial: false, accessibility: false, allowed: false),
         DiagnosticOperation(name: "carrier-disabled-primary", reference: false, initial: false, accessibility: false, enabled: false),
         DiagnosticOperation(name: "carrier-disabled-accessibility", reference: false, initial: false, accessibility: true, enabled: false),
         DiagnosticOperation(name: "carrier-accessibility-off-to-on", reference: false, initial: false, accessibility: true),
         DiagnosticOperation(name: "carrier-accessibility-on-to-off", reference: false, initial: true, accessibility: true),
         DiagnosticOperation(name: "reference-primary-off-to-on", reference: true, initial: false, accessibility: false),
         DiagnosticOperation(name: "reference-primary-on-to-off", reference: true, initial: true, accessibility: false),
         DiagnosticOperation(name: "reference-accessibility-off-to-on", reference: true, initial: false, accessibility: true),
         DiagnosticOperation(name: "reference-accessibility-on-to-off", reference: true, initial: true, accessibility: true)]
    }
    func operationSnapshot(reference: Bool) -> [String: Any] {
        let button: UIButton = reference ? referenceButton : toggle
        return ["uptime": ProcessInfo.processInfo.systemUptime, "identity": String(describing: ObjectIdentifier(button)), "class": String(describing: type(of: button)), "selected": button.isSelected, "enabled": button.isEnabled, "allowed": reference || allowed, "tracking": button.isTracking, "highlighted": button.isHighlighted, "attachedToWindow": button.window != nil, "primaryCount": reference ? referencePrimaryCount : toggle.primaryCount, "valueCount": reference ? referenceValueCount : eventCount, "primaryValues": reference ? referencePrimaryValues : eventValues, "traits": button.accessibilityTraits.rawValue, "buttonType": button.buttonType.rawValue, "configurationNil": button.configuration == nil, "menuNil": button.menu == nil, "changesSelectionAsPrimaryAction": button.changesSelectionAsPrimaryAction]
    }
    func operationMeetsRequirement(_ op: DiagnosticOperation, before: [String: Any], after: [String: Any], returned: Bool?) -> Bool {
        func state(_ value: [String: Any]) -> DiagnosticActivationState {
            DiagnosticActivationState(selected: value["selected"] as! Bool, attachedToWindow: value["attachedToWindow"] as! Bool, identity: value["identity"] as! String, primaryCount: value["primaryCount"] as! Int, valueCount: value["valueCount"] as! Int, lastValue: (value["primaryValues"] as! [Bool]).last)
        }
        return DiagnosticRequirement.meets(initial: op.initial, expectedActivation: op.enabled && op.allowed, requiresValueEvent: !op.reference, accessibility: op.accessibility, returned: returned, before: state(before), after: state(after))
    }
    func selfTests() {
        guard !diagnosticSuiteActive else { return }
        diagnosticSuiteActive = true; diagnosticSuiteState = "running"
        checks.removeAll(); diagnosticOperations.removeAll(); semanticOperations.removeAll()
        let identity = ObjectIdentifier(toggle)
        let start = eventCount
        allowed = true; toggle.isEnabled = true
        toggle.setOn(false, animated: false); toggle.setOn(true, animated: false); toggle.setOn(false, animated: false)
        check("binding writes emit no events", eventCount == start)
        toggle.isEnabled = false
        check("disabled native trait", toggle.accessibilityTraits.contains(.notEnabled))
        toggle.isEnabled = true
        check("public native toggle and button traits", toggle.accessibilityTraits.contains(.toggleButton) && toggle.accessibilityTraits.contains(.button))
        toggle.authoredAccessibility["accessibilityValue"] = "Authored sync status"
        check("authored metadata survives native state", toggle.accessibilityValue == "Authored sync status" && toggle.accessibilityLabel == "Sync entries" && toggle.accessibilityHint == "Updates the sync preference")
        toggle.authoredAccessibility.removeValue(forKey: "accessibilityValue")
        toggle.direction = .rightToLeft; toggle.direction = .leftToRight
        toggle.paints = theme.dark.toggle; toggle.paints = theme.light.toggle
        check("binding environment and theme preserve native identity", ObjectIdentifier(toggle) == identity)
        check("native visual carrier is custom unconfigured UIButton", toggle.buttonType == .custom && toggle.configuration == nil && toggle.menu == nil)
        check("pan reference is attached directly to root view outside scroll", referencePanSurface.superview === view && !(view is UIScrollView))
        runDiagnosticOperation(0)
    }
    func runDiagnosticOperation(_ index: Int) {
        guard index < operations.count else {
            semanticOperations = semanticActivationChecks()
            diagnosticSuiteActive = false; diagnosticSuiteState = "complete"
            allowed = true; toggle.isEnabled = true
            check("diagnostic trace has not overflowed", DiagnosticTrace.shared.dropped == 0)
            record("diagnosticSuiteComplete"); return
        }
        let op = operations[index]
        // Each direction establishes its own starting selection; no earlier pass
        // or failed transition can supply the premise for this operation.
        allowed = true; toggle.isEnabled = true
        toggle.setOn(op.initial, animated: false)
        referenceButton.isEnabled = true; referenceButton.isSelected = op.initial
        allowed = op.allowed; toggle.isEnabled = op.enabled
        let button: UIButton = op.reference ? referenceButton : toggle
        let before = operationSnapshot(reference: op.reference)
        DiagnosticTrace.shared.append("programmaticOperationBegin", ["name": op.name, "before": before])
        let returned: Bool?
        if op.accessibility { returned = button.accessibilityActivate() }
        else { button.performPrimaryAction(); returned = nil }
        let immediate = operationSnapshot(reference: op.reference)
        record("diagnosticOperationImmediate")
        // A separate main-queue turn and a bounded 250ms observation distinguish
        // immediate effects from deferred native work without driving input.
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            let nextTurn = self.operationSnapshot(reference: op.reference)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) { [weak self] in
                guard let self else { return }
                let settled = self.operationSnapshot(reference: op.reference)
                let pass = self.operationMeetsRequirement(op, before: before, after: settled, returned: returned)
                self.diagnosticOperations.append(["name": op.name, "initialSelection": op.initial, "reference": op.reference, "action": op.accessibility ? "accessibilityActivate" : "performPrimaryAction", "directReturn": returned as Any? ?? NSNull(), "before": before, "immediate": immediate, "nextMainQueueTurn": nextTurn, "settledAfter250ms": settled, "immediateRequirementSatisfied": self.operationMeetsRequirement(op, before: before, after: immediate, returned: returned), "settledRequirementSatisfied": pass, "scope": "Diagnostic contract; original frozen failures remain retained"])
                self.check(op.name + " strict settled transition", pass)
                DiagnosticTrace.shared.append("programmaticOperationSettled", ["name": op.name, "pass": pass, "after": settled])
                self.record("diagnosticOperationSettled")
                self.runDiagnosticOperation(index + 1)
            }
        }
    }
    func readCommand() {
        guard !diagnosticSuiteActive else { return }
        guard let command = try? String(contentsOf:documents.appendingPathComponent("command.txt"), encoding:.utf8), command != stage else { return }
        stage = command
        switch command {
        case "self-tests": selfTests()
        case "arm-commit-rebind", "arm-commit-stale", "arm-commit-disable", "arm-commit-cancel", "arm-commit-direction", "arm-commit-nested-primary", "arm-commit-nested-accessibility", "arm-commit-after-event-rebind":
            panCommitMode = command; panCommitHookFired = false; panCommitInitial = toggle.retainedOn; panCommitRecords = []
        case "arm-pan-accessibility", "arm-pan-cancel", "arm-pan-disable", "arm-pan-stale", "arm-pan-binding":
            interruptionMode = command; interruptionQueued = false; nativeInterruptions = []
        case "reset":
            panCommitMode = nil; panCommitHookFired = false; panCommitRecords = []
            interruptionMode = nil; interruptionQueued = false; nativeInterruptions = []
            allowed = true; toggle.isEnabled = true; toggle.setOn(false,animated:false); toggle.direction = .leftToRight
            toggle.paints = theme.light.toggle; scroll.backgroundColor = .white; rowLabel.textColor = .black; scroll.setContentOffset(.zero,animated:false)
        case "set-on": toggle.setOn(true, animated:false)
        case "disable": toggle.isEnabled = false
        case "stale": allowed = false; toggle.cancelAuthoredInteraction()
        case "resume": allowed = true; toggle.isEnabled = true
        case "rtl": toggle.direction = .rightToLeft
        case "dark": toggle.paints = theme.dark.toggle; scroll.backgroundColor = UIColor(white:0.11,alpha:1); rowLabel.textColor = .white
        case "cancel": toggle.cancelAuthoredInteraction()
        case "focus": setNeedsFocusUpdate(); updateFocusIfNeeded()
        case "authored-value": toggle.authoredAccessibility["accessibilityValue"] = "Authored sync status"
        case "clear-authored-value": toggle.authoredAccessibility.removeValue(forKey:"accessibilityValue")
        default: break
        }
        toggle.setNeedsDisplay(); record("command")
    }
    override func didUpdateFocus(in context: UIFocusUpdateContext, with coordinator: UIFocusAnimationCoordinator) {
        super.didUpdateFocus(in: context, with: coordinator)
        DiagnosticTrace.shared.focusContext("controller", context)
    }
    override var preferredFocusEnvironments: [UIFocusEnvironment] { [referenceButton] }
}

@MainActor final class PrototypeDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey:Any]?) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds); window.rootViewController = PrototypeController()
        window.makeKeyAndVisible(); self.window = window; return true
    }
}
UIApplicationMain(CommandLine.argc, CommandLine.unsafeArgv, nil, NSStringFromClass(PrototypeDelegate.self))
