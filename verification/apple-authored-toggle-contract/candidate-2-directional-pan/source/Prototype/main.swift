import UIKit
import MixerUI

@MainActor final class PrototypeController: UIViewController {
    let toggle = AuthoredToggleCarrier(type: .custom)
    let scroll = ToggleScrollView()
    let titleLabel = UILabel()
    let stateLabel = UILabel()
    let rowLabel = UILabel()
    let nextButton = UIButton(type: .custom)
    let theme: UIThemeV2
    var allowed = true
    var eventCount = 0
    var eventValues: [Bool] = []
    var events: [[String: Any]] = []
    var checks: [[String: Any]] = []
    var timer: Timer?
    var stage = "initial"
    var recording = false
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
        toggle.stateChanged = { [weak self] reason in self?.record(reason) }
        toggle.addTarget(self, action: #selector(changed), for: .valueChanged)
        scroll.addSubview(rowLabel); scroll.addSubview(toggle)
        toggle.participateInVerticalScroll(scroll)
        for n in 1...12 {
            let label = UILabel(frame: CGRect(x: 16, y: 110+n*70, width: 300, height: 32))
            label.text = "Native scroll row \(n)"; label.font = .systemFont(ofSize: 17)
            scroll.addSubview(label)
        }
        nextButton.setTitle("Next native focus target", for: .normal)
        nextButton.setTitleColor(.systemBlue, for: .normal)
        nextButton.accessibilityIdentifier = "next-focus"
        nextButton.addAction(UIAction { [weak self] _ in self?.record("nextButton") }, for: .primaryActionTriggered)
        view.addSubview(nextButton)
        timer = Timer.scheduledTimer(withTimeInterval: 0.03, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated { self?.readCommand() }
        }
    }
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        titleLabel.frame = CGRect(x: 24, y: view.safeAreaInsets.top+20, width: view.bounds.width-48, height: 34)
        stateLabel.frame = CGRect(x: 24, y: titleLabel.frame.maxY+10, width: view.bounds.width-48, height: 76)
        scroll.frame = CGRect(x: 16, y: stateLabel.frame.maxY+12, width: view.bounds.width-32, height: 390)
        rowLabel.frame = CGRect(x: 16, y: 30, width: scroll.bounds.width-110, height: 44)
        toggle.frame = CGRect(x: scroll.bounds.width-83, y: 30, width: 63, height: 44)
        nextButton.frame = CGRect(x: 24, y: scroll.frame.maxY+24, width: view.bounds.width-48, height: 44)
        if events.isEmpty { record("initial") }
    }
    @objc func changed() { eventCount += 1; eventValues.append(toggle.isOn); record("valueChanged") }
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
        let result: [String:Any] = ["scope":"Installed UIKit prototype; simulator only; no production adapter or physical VoiceOver qualification", "stage":stage, "state":snapshot(), "events":events, "checks":checks]
        let data = try! JSONSerialization.data(withJSONObject:result, options:[.prettyPrinted,.sortedKeys])
        try! data.write(to:documents.appendingPathComponent("observations.json"), options:.atomic)
        try! stage.write(to:documents.appendingPathComponent("stage.txt"), atomically:true, encoding:.utf8)
    }
    func check(_ name: String, _ pass: Bool) { checks.append(["name":name,"pass":pass]) }
    func selfTests() {
        let identity = ObjectIdentifier(toggle)
        let start = eventCount
        toggle.setOn(false, animated:false); toggle.setOn(true, animated:false); toggle.setOn(false, animated:false)
        check("binding writes emit no events", eventCount == start)
        toggle.performPrimaryAction()
        check("UIKit primary activation selects and emits once", toggle.isOn && eventCount == start+1 && eventValues.last == true)
        toggle.performPrimaryAction()
        check("UIKit second activation deselects and emits once", !toggle.isOn && eventCount == start+2 && eventValues.last == false)
        allowed = false; toggle.performPrimaryAction()
        check("stale native primary action restores value without event", !toggle.isOn && eventCount == start+2)
        allowed = true; toggle.isEnabled = false; toggle.performPrimaryAction()
        check("disabled primary action has no value event", !toggle.isOn && eventCount == start+2)
        check("disabled native trait", toggle.accessibilityTraits.contains(.notEnabled))
        check("disabled accessibility activation rejected", !toggle.accessibilityActivate() && eventCount == start+2)
        toggle.isEnabled = true
        let activation = toggle.accessibilityActivate()
        check("UIButton accessibility activation selects and emits once", activation && toggle.isOn && eventCount == start+3)
        check("public native toggle and button traits", toggle.accessibilityTraits.contains(.toggleButton) && toggle.accessibilityTraits.contains(.button))
        toggle.authoredAccessibility["accessibilityValue"] = "Authored sync status"
        check("authored metadata survives native state", toggle.accessibilityValue == "Authored sync status" && toggle.accessibilityLabel == "Sync entries" && toggle.accessibilityHint == "Updates the sync preference")
        toggle.authoredAccessibility.removeValue(forKey:"accessibilityValue")
        toggle.setOn(false, animated:false); toggle.direction = .rightToLeft; toggle.direction = .leftToRight
        toggle.paints = theme.dark.toggle; toggle.paints = theme.light.toggle
        check("binding environment and theme preserve native identity", ObjectIdentifier(toggle) == identity)
        check("native visual carrier is custom unconfigured UIButton", toggle.buttonType == .custom && toggle.configuration == nil && toggle.menu == nil)
        record("selfTests")
    }
    func readCommand() {
        guard let command = try? String(contentsOf:documents.appendingPathComponent("command.txt"), encoding:.utf8), command != stage else { return }
        stage = command
        switch command {
        case "self-tests": selfTests()
        case "reset":
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
    override var preferredFocusEnvironments: [UIFocusEnvironment] { [toggle] }
}

@MainActor final class PrototypeDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey:Any]?) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds); window.rootViewController = PrototypeController()
        window.makeKeyAndVisible(); self.window = window; return true
    }
}
UIApplicationMain(CommandLine.argc, CommandLine.unsafeArgv, nil, NSStringFromClass(PrototypeDelegate.self))
