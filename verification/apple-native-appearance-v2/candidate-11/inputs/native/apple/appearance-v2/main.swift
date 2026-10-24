import UIKit
import MixerUI
@testable import MixerAppearanceInternal

@MainActor final class HarnessController: UIViewController {
    var renderer: AppearanceNativeRendererV2!
    var actionLog: [[String:Any]] = []
    var observations: [[String:Any]] = []
    var checks: [[String:Any]] = []
    var timer: Timer?
    var lastCommand = ""
    let directory = FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0]
    var traitInputBefore: (focus:Bool,text:String,selection:[Int]?)?
    var environmentProbe: AppearanceNativeRendererV2?
    var revision: UInt64 = 1
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .white
        do {
            renderer = AppearanceNativeRendererV2(installed:try AppearanceInstalledV2.capture(bundle:.main))
            addChild(renderer); renderer.view.frame = view.bounds; renderer.view.autoresizingMask = [.flexibleWidth,.flexibleHeight]
            view.addSubview(renderer.view); renderer.didMove(toParent:self)
            renderer.onAction = { [weak self] action in
                self?.actionLog.append(["id":action.nodeID,"event":action.event.rawValue,"revision":action.revision])
                self?.save()
            }
        } catch { record("bootstrap",false,String(describing:error)) }
    }
    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        DispatchQueue.main.asyncAfter(deadline:.now()+0.6) { self.stage("initial") }
        timer = Timer.scheduledTimer(withTimeInterval:0.1,repeats:true) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self, let command = try? String(contentsOf:self.directory.appendingPathComponent("command.txt"),encoding:.utf8), command != self.lastCommand else { return }
                self.lastCommand = command; self.stage(command)
            }
        }
    }
    func makeOwner(bundle:Bundle = .main) throws -> AppearanceNativeRendererV2 {
        let other = AppearanceNativeRendererV2(installed:try AppearanceInstalledV2.capture(bundle:bundle))
        addChild(other); other.view.frame = view.bounds; view.addSubview(other.view); other.didMove(toParent:self); other.view.layoutIfNeeded()
        return other
    }
    func removeOwner(_ other:AppearanceNativeRendererV2) { other.willMove(toParent:nil); other.view.removeFromSuperview(); other.removeFromParent() }
    func fixture(_ rev: UInt64, suffix: String = "", disabled: Bool = false, checked: Bool = true) -> MixerUI.UIDocument {
        AppearanceFixtureV2.document(rev,suffix:suffix,disabled:disabled,checked:checked)
    }
    func record(_ name:String,_ pass:Bool,_ detail:String = "") { checks.append(["name":name,"pass":pass,"detail":detail]) }
    func expected(_ name:String,_ operation:() throws -> Void) {
        do { try operation(); record(name,false,"unexpected acceptance") } catch { record(name,true,String(describing:error)) }
    }
    func native(_ renderer: AppearanceNativeRendererV2? = nil) -> [String:Any] {
        let owner = renderer ?? self.renderer!
        var out: [String:Any] = ["revision":owner.snapshot?.document.revision as Any,"retired":owner.retiredReason as Any,
            "suspended":owner.suspendedReason as Any,"rootHidden":owner.view.isHidden,"interactionGeneration":owner.interactionGeneration,"rootInteraction":owner.view.isUserInteractionEnabled,"suppressedCallbacks":owner.suppressedCallbacks,
            "actions":actionLog,"operations":owner.lastAttachmentOperations]
        var nodes: [String:Any] = [:]
        for (id,view) in owner.records {
            var value: [String:Any] = ["nativeIdentity":String(describing:ObjectIdentifier(view)),"generation":view.identity.generation,
                "kind":view.kind.rawValue,"frame":rect(view.frame),"semantic":rect(CGRect(origin:.zero,size:view.semanticSize)),
                "content":rect(view.contentRect),"visual":rect(view.visualRect),"firstBaseline":view.firstBaseline as Any,"lastBaseline":view.lastBaseline as Any,
                "fontSize":view.label.font.pointSize,"fontName":view.label.font.fontName]
            if let field = view.field {
                value["inputIdentity"] = String(describing:ObjectIdentifier(field)); value["text"] = field.text ?? ""
                value["firstResponder"] = field.isFirstResponder; value["fontSize"] = field.font?.pointSize
                value["selectedRange"] = field.selectedTextRange.map { [field.offset(from:field.beginningOfDocument,to:$0.start),field.offset(from:field.beginningOfDocument,to:$0.end)] } as Any
                value["markedRange"] = field.markedTextRange.map { [field.offset(from:field.beginningOfDocument,to:$0.start),field.offset(from:field.beginningOfDocument,to:$0.end)] } as Any
                value["cursorInstalled"] = field.selectionDisplay?.cursorView === field.cursor
                value["cursorInWindow"] = field.cursor.window === field.window && field.window != nil
                value["cursorBlinking"] = field.cursor.isBlinking; value["cursorBlinkRequests"] = field.cursor.blinkRequestCount
                value["cursorBlinkResets"] = field.cursor.blinkResetCount
                value["cursorPresentationOpacity"] = field.cursor.layer.presentation()?.opacity as Any
                value["cursorRectInWindow"] = rect(field.cursor.convert(field.cursor.bounds,to:owner.view.window))
                value["highlightInWindow"] = field.highlight.window === field.window && field.window != nil
                value["highlightRectCount"] = field.highlight.selectionRects.count
            }
            if let toggle = view.toggle { value["inputIdentity"] = String(describing:ObjectIdentifier(toggle)); value["checked"] = toggle.isOn; value["tracking"] = toggle.isTracking; value["nativeMaskEmpty"] = (toggle.layer.mask as? CAShapeLayer)?.path?.isEmpty ?? false; value["accessibilityLabel"] = toggle.accessibilityLabel }
            if let scroll = view.scroll { value["scrollIdentity"] = String(describing:ObjectIdentifier(scroll)); value["offset"] = [scroll.contentOffset.x,scroll.contentOffset.y]; value["contentSize"] = [scroll.contentSize.width,scroll.contentSize.height] }
            nodes[id] = value
        }
        out["nodes"] = nodes
        if let env = owner.plan?.environment { out["environment"] = ["generation":env.generation,"profile":env.profile.rawValue,"density1024":env.density1024,"locale":env.localeIdentifier,"viewport":[env.viewport.width64,env.viewport.height64],"safeArea":[env.safeArea64.top,env.safeArea64.leading,env.safeArea64.bottom,env.safeArea64.trailing],"scheme":env.scheme.rawValue,"direction":env.direction.rawValue] }
        return out
    }
    func rect(_ rect:CGRect) -> [Double] { [rect.minX,rect.minY,rect.width,rect.height].map(Double.init) }
    func range(_ offset:Int,_ length:Int) -> UITextRange? {
        guard let field = renderer.records["field"]?.field, let start = field.position(from:field.beginningOfDocument,offset:offset),let end = field.position(from:start,offset:length) else { return nil }
        return field.textRange(from:start,to:end)
    }
    func stage(_ command:String) {
        guard let renderer else { return }
        let captured = command.hasSuffix("-captured")
        let name = captured ? String(command.dropLast(9)) : command
        let categories: [String:UIContentSizeCategory] = ["xs":.extraSmall,"s":.small,"m":.medium,"l":.large,"xl":.extraLarge,"xxl":.extraExtraLarge,"xxxl":.extraExtraExtraLarge,"a1":.accessibilityMedium,"a2":.accessibilityLarge,"a3":.accessibilityExtraLarge,"a4":.accessibilityExtraExtraLarge,"a5":.accessibilityExtraExtraExtraLarge]
        let traitStage = name.hasPrefix("profile-") || ["contrast","contrast-restore","dark","rtl","restore-environment"].contains(name)
        if traitStage && !captured {
            if let field = renderer.records["field"]?.field {
                traitInputBefore = (field.isFirstResponder,field.text ?? "",field.selectedTextRange.map { [field.offset(from:field.beginningOfDocument,to:$0.start),field.offset(from:field.beginningOfDocument,to:$0.end)] })
            }
            if name.hasPrefix("profile-"), let category = categories[String(name.dropFirst(8))] { renderer.traitOverrides.preferredContentSizeCategory = category }
            if name == "contrast" {
                do {
                    let other = try makeOwner()
                    _ = try other.commit(other.prepare(document:fixture(1)))
                    environmentProbe = other; other.traitOverrides.accessibilityContrast = .high
                } catch { record("contrast-probe-setup",false,String(describing:error)) }
            }
            
            if name == "dark" { renderer.traitOverrides.userInterfaceStyle = .dark }
            if name == "rtl" { renderer.traitOverrides.layoutDirection = .rightToLeft }
            if name == "restore-environment" { renderer.traitOverrides.layoutDirection = .leftToRight; renderer.traitOverrides.userInterfaceStyle = .light }
            DispatchQueue.main.asyncAfter(deadline:.now()+0.15) { self.stage(name+"-captured") }
            return
        }
        let before = native()
        do {
            switch name {
            case "initial":
                for fixture in ["BadDescriptor","UnsupportedResources"] {
                    if let path = Bundle.main.url(forResource:fixture,withExtension:"bundle"), let bundle = Bundle(url:path) {
                        expected("installed-"+fixture) { _ = try AppearanceInstalledV2.capture(bundle:bundle) }
                    } else { record("fixture-bundle-"+fixture,false) }
                }
                let candidate = try renderer.prepare(document:fixture(1))
                record("prepare-does-not-commit",renderer.snapshot == nil && renderer.records.isEmpty)
                _ = try renderer.commit(candidate)
                record("all-ten-native-kinds",Set(renderer.records.values.map(\.kind)) == Set(NodeKind.allCases))
                try UIValidator().encode(fixture(1)).write(to:directory.appendingPathComponent("fixture-document.json"))
                try renderer.snapshot!.encodeNativePacketV1().write(to:directory.appendingPathComponent("fixture-native-packet.bin"))
                exportFrames()
                record("native-accessibility-hstack-source-order",(renderer.records["h"]!.accessibilityElements as? [UIView]) == [renderer.records["short"]!,renderer.records["long"]!])
                record("native-section-heading-trait",renderer.records["navigation"]!.label.accessibilityTraits.contains(.header))
                record("real-native-controls",renderer.records["field"]?.field != nil && renderer.records["toggle"]?.toggle != nil && renderer.records["list"]?.scroll != nil && renderer.records["button"]?.button != nil && renderer.records["selectable"]?.selectable != nil)
            case "focus":
                let field = renderer.records["field"]!.field!
                _ = field.becomeFirstResponder(); field.selectedTextRange = range(5,0)
                record("native-focus",field.isFirstResponder)
            case "selection": renderer.records["field"]!.field!.selectedTextRange = range(5,6)
            case "caret": _ = renderer.records["field"]!.field!.becomeFirstResponder(); renderer.records["field"]!.field!.selectedTextRange = range(5,0)
            case "blink-a","blink-b","blink-c","blink-d":
                let cursor = renderer.records["field"]!.field!.cursor
                record("managed-blink-active-"+name,cursor.isBlinking && cursor.layer.animation(forKey:"mixer.native.cursor.blink") != nil)
            case "ordinary":
                let field = renderer.records["field"]!.field!, toggle = renderer.records["toggle"]!.toggle!, scroll = renderer.records["list"]!.scroll!
                let selected = field.selectedTextRange.map { [field.offset(from:field.beginningOfDocument,to:$0.start),field.offset(from:field.beginningOfDocument,to:$0.end)] }
                let offset = scroll.contentOffset
                let candidate = try renderer.prepare(document:fixture(2,suffix:" updated"))
                record("prepare-native-editor-unchanged",renderer.records["field"]!.field === field && field.isFirstResponder && selected == field.selectedTextRange.map { [field.offset(from:field.beginningOfDocument,to:$0.start),field.offset(from:field.beginningOfDocument,to:$0.end)] })
                _ = try renderer.commit(candidate); revision = 2
                record("surviving-input-list-identity",renderer.records["field"]!.field === field && renderer.records["toggle"]!.toggle === toggle && renderer.records["list"]!.scroll === scroll)
                record("selection-focus-offset-retained",field.isFirstResponder && selected == field.selectedTextRange.map { [field.offset(from:field.beginningOfDocument,to:$0.start),field.offset(from:field.beginningOfDocument,to:$0.end)] } && scroll.contentOffset == offset)
                expected("reused-candidate") { _ = try renderer.commit(candidate) }
            case "ancestor-move":
                let original = fixture(revision+1), field = renderer.records["field"]!.field!
                let list = original.root.children[0]
                let movedList = UINode(id:list.id,kind:list.kind,properties:list.properties,children:list.children.reversed())
                let moved = MixerUI.UIDocument(revision:revision+1,root:UINode(id:original.root.id,kind:.navigation,properties:original.root.properties,children:[movedList]))
                let parent = renderer.records["section"]!.superview
                let candidate = try renderer.prepare(document:moved)
                expected("focused-ancestor-parent-replacement-rejected") { _ = try renderer.commit(candidate) }
                record("ancestor-rejection-keeps-native-focus-tree-and-snapshot",renderer.retiredReason == nil && field.isFirstResponder && renderer.records["section"]!.superview === parent && renderer.snapshot!.document.revision == revision)
            case "composition":
                let field = renderer.records["field"]!.field!
                field.setMarkedText("にほん",selectedRange:NSRange(location:3,length:0))
                let text = field.text, marked = field.markedTextRange
                expected("composing-preflight") { _ = try renderer.prepare(document:fixture(revision+1)) }
                record("composition-not-serialized-or-mutated",marked != nil && field.markedTextRange != nil && field.text == text && field.isFirstResponder)
                field.unmarkText()
            case "environment":
                let previous = renderer.plan!.environment.generation, originalFocus = renderer.records["field"]!.field!.isFirstResponder
                let identities = renderer.records.mapValues { ObjectIdentifier($0) }
                renderer.invalidateEnvironment()
                let field = renderer.records["field"]!.field!, buffer = field.text, focus = field.isFirstResponder, actionCount = actionLog.count
                let inputPoint = field.convert(CGPoint(x:field.bounds.midX,y:field.bounds.midY),to:renderer.view)
                record("stale-environment-native-hit-blocker",renderer.view.hitTest(inputPoint,with:nil) === renderer.view)
                record("stale-environment-native-proposals-denied",!renderer.records["field"]!.textField(field,shouldChangeCharactersIn:NSRange(location:0,length:0),replacementString:"denied") && !renderer.records["field"]!.textFieldShouldReturn(field))
                field.insertText("denied"); field.deleteBackward(); field.setMarkedText("拒否",selectedRange:NSRange(location:1,length:0))
                renderer.records["button"]!.button!.sendActions(for:.touchUpInside)
                record("stale-environment-native-buffer-and-actions-gated",field.isFirstResponder == focus && field.text == buffer && field.markedTextRange == nil && field.selectedTextRange?.start != nil && actionLog.count == actionCount && renderer.suspendedReason != nil)
                let candidate = try renderer.prepareEnvironment()
                let changes = try renderer.commit(candidate)
                record("environment-same-guest-revision",changes == nil && renderer.snapshot!.document.revision == revision && renderer.plan!.environment.generation > previous)
                record("environment-same-native-identities",renderer.records.mapValues { ObjectIdentifier($0) } == identities && renderer.records["field"]!.field!.isFirstResponder == originalFocus)
            case "stale":
                let stale = try renderer.prepare(document:fixture(revision+1))
                let newest = try renderer.prepare(document:fixture(revision+2))
                _ = try renderer.commit(newest); revision += 2
                expected("stale-candidate") { _ = try renderer.commit(stale) }
                let changed = try renderer.prepareEnvironment(); renderer.invalidateEnvironment()
                expected("changed-environment-candidate") { _ = try renderer.commit(changed) }
                let discarded = try renderer.prepareEnvironment(); try renderer.discard(discarded)
                expected("discard-consumes") { _ = try renderer.commit(discarded) }
            case "interaction-stale":
                _ = try renderer.commit(renderer.prepareEnvironment())
                let candidate = try renderer.prepareEnvironment(), button = renderer.records["button"]!.button!
                let highlight = button.isHighlighted, focus = button.isFocused, generation = renderer.interactionGeneration
                button.sendActions(for:.touchUpInside)
                record("native-action-advances-interaction-with-same-final-paint",button.isHighlighted == highlight && button.isFocused == focus && renderer.interactionGeneration == generation+1)
                expected("routed-interaction-generation-stale-candidate") { _ = try renderer.commit(candidate) }
            case "native-state-stale":
                let candidate = try renderer.prepareEnvironment()
                renderer.records["field"]!.field!.text = "native unacknowledged draft"
                renderer.records["field"]!.field!.selectedTextRange = range(2,0)
                renderer.records["toggle"]!.toggle!.setOn(false,animated:false); renderer.records["toggle"]!.stateChanged?()
                expected("changed-native-selection-candidate") { _ = try renderer.commit(candidate) }
            case let profile where profile.hasPrefix("profile-"):
                let expectedProfile = UISharedTextProfileV1(rawValue:String(profile.dropFirst(8)))!
                let field = renderer.records["field"]!.field!, control = renderer.records["toggle"]!.toggle!
                let text = field.text, focus = field.isFirstResponder, checked = control.isOn
                let selection = field.selectedTextRange.map { [field.offset(from:field.beginningOfDocument,to:$0.start),field.offset(from:field.beginningOfDocument,to:$0.end)] }
                _ = try renderer.commit(renderer.prepareEnvironment())
                record("profile-retains-native-buffer-selection-focus-switch-"+profile,field.text == text && field.isFirstResponder == focus && field.isFirstResponder == traitInputBefore?.focus && field.text == traitInputBefore?.text && selection == traitInputBefore?.selection && control.isOn == checked && selection == field.selectedTextRange.map { [field.offset(from:field.beginningOfDocument,to:$0.start),field.offset(from:field.beginningOfDocument,to:$0.end)] })
                record("actual-owner-"+profile,renderer.plan!.environment.profile == expectedProfile && renderer.records["field"]!.field!.font!.pointSize == CGFloat(expectedProfile.metrics(for:.body).size64)/64)
            case "authoritative-bindings":
                let field = renderer.records["field"]!.field!, control = renderer.records["toggle"]!.toggle!
                record("same-revision-retains-unacknowledged-native-values",field.text == "native unacknowledged draft" && !control.isOn)
                _ = try renderer.commit(renderer.prepare(document:fixture(revision+1))); revision += 1
                record("new-guest-document-authoritative-even-unchanged-binding",field.text == "alpha      omega" && control.isOn && renderer.records["field"]!.field === field && renderer.records["toggle"]!.toggle === control)
            case "contrast":
                if let other = environmentProbe {
                    var actions = 0; other.onAction = { _ in actions += 1 }
                    expected("unqualified-increased-contrast-rejected") { _ = try other.prepareEnvironment() }
                    let field = other.records["field"]!.field!, text = field.text
                    field.insertText("denied"); field.setMarkedText("拒否",selectedRange:NSRange(location:1,length:0))
                    other.records["button"]!.button!.sendActions(for:.touchUpInside)
                    record("unsupported-recapture-retires-and-gates-existing-owner",other.retiredReason != nil && other.view.isHidden && !other.view.isUserInteractionEnabled && actions == 0 && field.text == text && field.markedTextRange == nil && !other.records["field"]!.textFieldShouldReturn(field))
                    observations.append(["stage":"unsupported-environment-owner","after":native(other)])
                }
            case "contrast-restore": if let other = environmentProbe { removeOwner(other); environmentProbe = nil }
            case "accessibility":
                let other = try makeOwner()
                defer { removeOwner(other) }
                let kinds:[NodeKind] = [.text,.button,.textField,.toggle,.text]
                let leaves = kinds.enumerated().map { i,kind -> UINode in
                    var props:[String:UIValue] = ["accessibilityLabel":.string("Label \(i)"),"accessibilityHint":.string("Hint \(i)"),"accessibilityValue":.string("Value \(i)"),"accessibilityIdentifier":.string("actual-leaf-\(i)")]
                    props[kind == .text ? "text" : "label"] = .string("Visible \(i)")
                    if kind == .textField { props["value"] = .string("text") }; if kind == .toggle { props["value"] = .bool(true) }; if i == 4 { props["selectable"] = .bool(true) }
                    let events:[UIEventKind] = kind == .button ? [.activate] : kind == .textField ? [.textChange,.submit] : kind == .toggle ? [.valueChange] : []
                    return UINode(id:"leaf\(i)",kind:kind,properties:props,actions:events.map { .init(id:"a\(i)-"+$0.rawValue,event:$0) })
                }
                _ = try other.commit(other.prepare(document:MixerUI.UIDocument(revision:1,root:UINode(id:"accessibility-root",kind:.vStack,children:leaves))))
                for i in 0..<kinds.count {
                    let leaf = other.records["leaf\(i)"]!.accessibilityLeaf!
                    record("native-accessibility-overrides-on-traversal-leaf-\(i)",leaf.accessibilityLabel == "Label \(i)" && leaf.accessibilityHint == "Hint \(i)" && leaf.accessibilityValue == "Value \(i)" && leaf.accessibilityIdentifier == "actual-leaf-\(i)")
                }
                let unsupported = MixerUI.UIDocument(revision:2,root:UINode(id:"accessibility-root",kind:.vStack,properties:["accessibilityLabel":.string("Hide children")],children:leaves))
                expected("nonleaf-accessibility-semantics-rejected-before-effects") { _ = try other.prepare(document:unsupported) }
                record("accessibility-rejection-keeps-committed-owner",other.retiredReason == nil && other.snapshot?.document.revision == 1)
                observations.append(["stage":"accessibility-owner","after":native(other)])
            case "short-rows":
                let url = Bundle.main.url(forResource:"ShortRows",withExtension:"bundle")!
                let other = try makeOwner(bundle:Bundle(url:url)!)
                defer { removeOwner(other) }
                for (kind,props) in [(NodeKind.button,["label":UIValue.string("Button")]),(.textField,["label":.string("Field"),"value":.string("text")]),(.toggle,["label":.string("Toggle"),"value":.bool(true)])] {
                    let document = MixerUI.UIDocument(revision:1,root:UINode(id:"short-list",kind:.list,children:[UINode(id:"short-control",kind:kind,properties:props)]))
                    expected("custom-short-row-hit-envelope-rejected-"+kind.rawValue) { _ = try other.prepare(document:document) }
                }
                record("row-hit-rejection-has-no-native-attachment",other.records.isEmpty && other.snapshot == nil && other.lastAttachmentOperations == 0)
            case "dark":
                _ = try renderer.commit(renderer.prepareEnvironment())
                record("actual-owner-dark-environment",renderer.plan!.environment.scheme == .dark)
            case "rtl":
                _ = try renderer.commit(renderer.prepareEnvironment())
                record("actual-owner-rtl-environment",renderer.plan!.environment.direction == .rightToLeft)
            case "restore-environment": _ = try renderer.commit(renderer.prepareEnvironment())
            case "outside-section":
                let other = AppearanceNativeRendererV2(installed:try AppearanceInstalledV2.capture(bundle:.main))
                addChild(other); other.view.frame = CGRect(x:0,y:0,width:320,height:400)
                other.view.semanticContentAttribute = .forceRightToLeft
                view.addSubview(other.view); other.didMove(toParent:self); other.view.layoutIfNeeded()
                let document = MixerUI.UIDocument(revision:1,root:UINode(id:"outside",kind:.section,properties:["title":.string("A much longer section heading")],children:[UINode(id:"outside-short",kind:.text,properties:["text":.string("short")])]))
                _ = try other.commit(other.prepare(document:document))
                let section = other.records["outside"]!, child = other.records["outside-short"]!
                record("outside-section-native-rtl-leading-alignment",other.plan!.environment.direction == .rightToLeft && abs(child.frame.maxX-section.bounds.width) < 0.34 && child.frame.minX > 0)
                record("outside-section-native-heading-trait",section.label.accessibilityTraits.contains(.header))
                observations.append(["stage":"outside-section-owner","after":native(other)])
                let image = UIGraphicsImageRenderer(bounds:other.view.bounds).image { _ in other.view.drawHierarchy(in:other.view.bounds,afterScreenUpdates:true) }
                try image.pngData()?.write(to:directory.appendingPathComponent("outside-section-native-hierarchy.png"))
                other.willMove(toParent:nil); other.view.removeFromSuperview(); other.removeFromParent()
            case "unsupported-contexts":
                let nested = MixerUI.UIDocument(revision:revision+1,root:UINode(id:"list",kind:.list,children:[UINode(id:"nested",kind:.vStack,children:[UINode(id:"nested-button",kind:.button,properties:["label":.string("Nested")],actions:[.init(id:"a",event:.activate)])])]))
                expected("nested-control-row-rejected") { _ = try renderer.prepare(document:nested) }
                let original = fixture(revision+1)
                let wrappedScroll = MixerUI.UIDocument(revision:revision+1,root:UINode(id:original.root.id,kind:.navigation,properties:original.root.properties,children:[UINode(id:"scrollWrapper",kind:.zStack,children:original.root.children)]))
                expected("navigation-indirect-scroll-context-rejected") { _ = try renderer.prepare(document:wrappedScroll) }
                func changedSelectable(_ node:UINode) -> UINode {
                    var properties = node.properties
                    if node.id == "selectable" { properties["selectable"] = .bool(false) }
                    return UINode(id:node.id,kind:node.kind,properties:properties,children:node.children.map(changedSelectable),actions:node.actions)
                }
                let topology = MixerUI.UIDocument(revision:revision+1,root:changedSelectable(original.root))
                expected("surviving-text-selectability-topology-change-rejected") { _ = try renderer.prepare(document:topology) }
                let baseline = MixerUI.UIDocument(revision:revision+1,root:UINode(id:"baseline",kind:.hStack,properties:["alignment":.string("firstTextBaseline")],children:[UINode(id:"baseline-field",kind:.textField,properties:["label":.string("Field"),"value":.string("text")],actions:[.init(id:"edit",event:.textChange)])]))
                expected("unavailable-field-baseline-rejected") { _ = try renderer.prepare(document:baseline) }
            case "interactive":
                _ = try renderer.commit(renderer.prepare(document:fixture(revision+1))); revision += 1
                renderer.records["list"]!.scroll!.setContentOffset(.zero,animated:false)
            case "selectable-retention":
                let text = renderer.records["selectable"]!.selectable!
                text.selectedRange = NSRange(location:2,length:6)
                _ = try renderer.commit(renderer.prepareEnvironment())
                record("native-selectable-view-and-selection-retained",renderer.records["selectable"]!.selectable === text && text.selectedRange == NSRange(location:2,length:6))
            case "callback":
                let count = actionLog.count
                renderer.records["button"]!.button!.sendActions(for:.touchUpInside)
                record("native-button-callback-at-most-once",actionLog.count == count+1)
                let control = renderer.records["button"]!.button!; control.isHidden = true
                control.sendActions(for:.touchUpInside)
                record("hidden-native-control-action-gated",actionLog.count == count+1)
                control.isHidden = false
            case "pressed": renderer.records["button"]!.button!.isHighlighted = true
            case "normal": renderer.records["button"]!.button!.isHighlighted = false
            case "toggle-input":
                let count = actionLog.count
                let control = renderer.records["toggle"]!.toggle!
                control.setOn(false,animated:false); control.sendActions(for:.valueChanged)
                record("native-switch-value-callback-once",actionLog.count == count+1 && !control.isOn)
            case "toggle-reset": renderer.records["toggle"]!.toggle!.setOn(true,animated:false); renderer.records["toggle"]!.stateChanged?()
            case "scroll-update":
                let scroll = renderer.records["list"]!.scroll!, offset = scroll.contentOffset
                let candidate = try renderer.prepare(document:fixture(revision+1))
                _ = try renderer.commit(candidate); revision += 1
                record("nonzero-scroll-offset-native-identity-retained",renderer.records["list"]!.scroll === scroll && scroll.contentOffset == offset)
                record("compact-native-presentation-retained-through-commit",renderer.records["navigation"]!.label.font.pointSize == 17)
            case "scroll":
                let scroll = renderer.records["list"]!.scroll!
                scroll.setContentOffset(CGPoint(x:0,y:120),animated:false)
                record("native-scroll-compact-threshold",renderer.records["navigation"]!.label.font.pointSize == 17 && renderer.records["list"]!.frame.minY == 44)
            case "scroll-top": renderer.records["list"]!.scroll!.setContentOffset(.zero,animated:false)
            case "foreign-fault":
                let other = AppearanceNativeRendererV2(installed:try AppearanceInstalledV2.capture(bundle:.main))
                addChild(other); other.view.frame = view.bounds; view.addSubview(other.view); other.didMove(toParent:self); other.view.layoutIfNeeded()
                let foreign = try other.prepare(document:fixture(1))
                expected("foreign-owner-candidate") { _ = try renderer.commit(foreign) }
                _ = try other.commit(foreign)
                let candidate = try other.prepare(document:fixture(2))
                let old = other.snapshot!.document
                other.onAttachmentOperation = { [weak other] _ in other?.records["button"]?.button?.sendActions(for:.touchUpInside) }
                other.failAttachmentAfterOperation = 1
                expected("attach-fault") { _ = try other.commit(candidate) }
                record("main-thread-native-callback-suppressed-during-attach",other.suppressedCallbacks > 0)
                record("attach-fault-explicit-retirement",other.retiredReason != nil && other.view.isHidden && !other.view.isUserInteractionEnabled && other.snapshot!.document == old)
                expected("retired-owner-denies-future-use") { _ = try other.prepare(document:fixture(3)) }
                observations.append(["stage":"retired-owner","after":native(other)])
                other.willMove(toParent:nil); other.view.removeFromSuperview(); other.removeFromParent()
            case "disabled":
                let candidate = try renderer.prepare(document:fixture(revision+1,disabled:true,checked:false)); _ = try renderer.commit(candidate); revision += 1
                let count = actionLog.count; renderer.records["button"]!.button!.sendActions(for:.touchUpInside)
                record("disabled-native-event-denied",actionLog.count == count && !renderer.records["button"]!.button!.isEnabled)
                let disabledField = renderer.records["field"]!.field!, buffer = disabledField.text
                disabledField.insertText("denied"); disabledField.setMarkedText("拒否",selectedRange:NSRange(location:1,length:0))
                record("disabled-native-buffer-proposals-denied",disabledField.text == buffer && disabledField.markedTextRange == nil && !renderer.records["field"]!.textField(disabledField,shouldChangeCharactersIn:NSRange(location:0,length:0),replacementString:"denied"))
            default: break
            }
        } catch { record("stage-"+name,false,String(describing:error)) }
        renderer.view.layoutIfNeeded()
        observations.append(["stage":name,"before":before,"after":native()])
        save()
        try? name.write(to:directory.appendingPathComponent("stage.txt"),atomically:true,encoding:.utf8)
    }
    func exportFrames() {
        guard let plan = renderer.plan else { return }
        func rgba(_ c: UIRGBA8V1) -> [UInt8] { [c.red,c.green,c.blue,c.alpha] }
        func paint(_ value: UIResolvedAppearancePaintsV2) -> [String:Any] {
            switch value {
            case let .text(f,b): return ["foreground":rgba(f),"background":rgba(b)]
            case let .container(b): return ["background":rgba(b)]
            case let .list(c,s,l): return ["canvas":rgba(c),"surface":rgba(s),"separator":rgba(l)]
            case let .section(h,b): return ["header":h.map(rgba) ?? [],"background":rgba(b)]
            case let .navigation(e,c,b): return ["expanded":e.map(rgba) ?? [],"compact":c.map(rgba) ?? [],"background":rgba(b)]
            case let .button(p,f): return ["label":rgba(p.label),"background":rgba(p.background),"focus":f.map { ["color":rgba($0.color),"width64":$0.width64,"radius64":$0.radius64] as [String:Any] } ?? [:]]
            case let .field(p): return ["text":rgba(p.text),"placeholder":rgba(p.placeholder),"background":rgba(p.background),"caret":rgba(p.caret),"selection":rgba(p.selection),"outline":["color":rgba(p.outline.color),"width64":p.outline.width64,"radius64":p.outline.radius64]]
            case let .toggle(p,f): return ["label":rgba(p.label),"track":rgba(p.track),"thumb":rgba(p.thumb),"overlay":rgba(p.overlay),"focus":f.map { ["color":rgba($0.color),"width64":$0.width64,"radius64":$0.radius64] as [String:Any] } ?? [:]]
            }
        }
        func r64(_ rect:CGRect) -> [Int64] { [rect.minX,rect.minY,rect.width,rect.height].map { Int64(($0*64).rounded()) } }
        func metric(_ text:UIResolvedTextV2) -> [String:Any] { ["role":text.role.rawValue,"size64":text.metrics.size64,"weight":text.metrics.weight.rawValue,"value":text.value] }
        var nodes: [[String:Any]] = []
        for node in plan.nodes {
            let view = renderer.records[node.identity.id]!
            var item: [String:Any] = ["id":node.identity.id,"generation":node.identity.generation,"kind":node.kind.rawValue,"frame64":r64(view.frame),"windowFrame64":r64(view.convert(view.bounds,to:renderer.view.window)),"semantic64":r64(CGRect(origin:.zero,size:view.semanticSize)),"content64":r64(view.contentRect),"visual64":r64(view.visualRect),"childIDs":node.childIDs,"disabled":node.disabled]
            switch node.recipe {
            case let .text(t),let .button(_,t,_),let .textField(_,_,t,_),let .toggle(t,_,_): item["text"] = metric(t)
            case let .section(s): item["text"] = s.header.map(metric)
            case let .navigation(n): item["expandedTitle"] = n.expandedTitle.map(metric); item["compactTitle"] = n.compactTitle.map(metric)
            default: break
            }
            item["enabledPaint"] = plan.style(nodeID:node.identity.id).map { paint($0.paints) }
            item["pressedPaint"] = plan.style(nodeID:node.identity.id,pressed:true).map { paint($0.paints) }
            item["focusedPaint"] = plan.style(nodeID:node.identity.id,focused:true).map { paint($0.paints) }
            nodes.append(item)
        }
        let env = plan.environment
        let output: [String:Any] = ["fixture":"AppearanceFixtureV2.document(1)","configuration":plan.configurationID,"viewport64":[env.viewport.width64,env.viewport.height64],"safeArea64":[env.safeArea64.top,env.safeArea64.leading,env.safeArea64.bottom,env.safeArea64.trailing],"density1024":env.density1024,"profile":env.profile.rawValue,"direction":env.direction.rawValue,"nodes":nodes]
        if let bytes = try? JSONSerialization.data(withJSONObject:output,options:[.prettyPrinted,.sortedKeys]) { try? bytes.write(to:directory.appendingPathComponent("fixture-frames-roles-states.json")) }
    }
    func save() {
        func clean(_ value:Any) -> Any {
            let mirror = Mirror(reflecting:value)
            if mirror.displayStyle == .optional { return mirror.children.first.map { clean($0.value) } ?? NSNull() }
            if let array = value as? [Any] { return array.map(clean) }
            if let dictionary = value as? [String:Any] { return dictionary.mapValues(clean) }
            return value
        }
        let data: [String:Any] = ["checks":checks,"observations":observations,"actions":actionLog,"runtime":UIDevice.current.systemVersion,"physicalDeviceTested":false,"realKeyboardIMEQualified":false,"voiceOverQualified":false]
        if let bytes = try? JSONSerialization.data(withJSONObject:clean(data),options:[.prettyPrinted,.sortedKeys]) { try? bytes.write(to:directory.appendingPathComponent("observations.json"),options:.atomic) }
    }
}
@MainActor final class AppDelegate: NSObject, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application:UIApplication,didFinishLaunchingWithOptions launchOptions:[UIApplication.LaunchOptionsKey:Any]?) -> Bool {
        let window = UIWindow(frame:UIScreen.main.bounds)
        let navigation = UINavigationController(rootViewController:HarnessController())
        navigation.setNavigationBarHidden(true,animated:false)
        window.rootViewController = navigation; window.makeKeyAndVisible(); self.window = window
        return true
    }
}
UIApplicationMain(CommandLine.argc,CommandLine.unsafeArgv,nil,NSStringFromClass(AppDelegate.self))
