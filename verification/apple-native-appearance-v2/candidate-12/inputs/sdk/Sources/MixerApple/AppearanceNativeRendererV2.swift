#if canImport(UIKit)
import UIKit
import MixerUI

private final class AppearanceObserverTokenV2 {
    let value: NSObjectProtocol
    init(_ value: NSObjectProtocol) { self.value = value }
    deinit { NotificationCenter.default.removeObserver(value) }
}

/// Internal ordinary UIKit consumer. It supplies no signed presentation or
/// release authority and is intentionally absent from the legacy public facade.
@MainActor final class AppearanceNativeRendererV2: UIViewController {
    enum Failure: Error { case retired, foreignCandidate, consumedCandidate, staleCandidate, composingEditor, focusedReparent, attachmentFault, attachmentInProgress }
    final class Candidate {
        fileprivate let owner: UUID
        fileprivate let baseSerial: UInt64
        fileprivate let interactionGeneration: UInt64
        fileprivate let nativeState: [String:String]
        fileprivate let environment: UIAppearanceEnvironmentV2
        fileprivate let reconciler: UIReconciler
        fileprivate let snapshot: UIRenderSnapshot
        fileprivate let changes: UIChangeSet?
        fileprivate let layout: AppearanceNativeLayoutV2
        fileprivate var consumed = false
        fileprivate init(owner: UUID, baseSerial: UInt64, interactionGeneration: UInt64, nativeState: [String:String], environment: UIAppearanceEnvironmentV2,
                         reconciler: UIReconciler, snapshot: UIRenderSnapshot, changes: UIChangeSet?, layout: AppearanceNativeLayoutV2) {
            self.owner = owner; self.baseSerial = baseSerial; self.interactionGeneration = interactionGeneration; self.nativeState = nativeState; self.environment = environment
            self.reconciler = reconciler; self.snapshot = snapshot; self.changes = changes; self.layout = layout
        }
    }
    private final class Root: UIView {
        weak var owner: AppearanceNativeRendererV2?
        override func didMoveToWindow() { super.didMoveToWindow(); owner?.environmentDidInvalidate() }
        override func safeAreaInsetsDidChange() { super.safeAreaInsetsDidChange(); owner?.environmentDidInvalidate() }
        override func hitTest(_ point: CGPoint, with event: UIEvent?) -> UIView? {
            guard !isHidden, isUserInteractionEnabled, alpha > 0.01 else { return nil }
            if let owner, owner.snapshot != nil, !owner.callbacksOpen { return bounds.contains(point) ? self : nil }
            return super.hitTest(point,with:event)
        }
    }
    private let ownerID = UUID()
    private let installed: AppearanceInstalledV2
    private let environment = AppearanceEnvironmentV2()
    private var reconciler = UIReconciler()
    private(set) var snapshot: UIRenderSnapshot?
    private(set) var plan: UIResolvedAppearancePlanV2?
    private(set) var records: [String: AppearanceNodeViewV2] = [:]
    private var decorations: [String: UIView] = [:]
    private var committedLayout: AppearanceNativeLayoutV2?
    private var serial: UInt64 = 0
    private(set) var interactionGeneration: UInt64 = 0
    private var callbacksOpen = false
    private var callbackDepth = 0
    private var notifications: [AppearanceObserverTokenV2] = []
    private(set) var retiredReason: String?
    private(set) var suspendedReason: String?
    /// Internal fault seam exercised by the native harness, never an app proof.
    var failAttachmentAfterOperation: Int?
    var onAttachmentOperation: ((Int) -> Void)?
    private var attaching = false
    var onAction: ((RoutedUIAction) -> Void)?
    var onRetired: ((String) -> Void)?
    private(set) var lastAttachmentOperations = 0
    private(set) var suppressedCallbacks = 0
    private var lastBounds = CGRect.zero

    init(installed: AppearanceInstalledV2) { self.installed = installed; super.init(nibName:nil,bundle:nil) }
    required init?(coder: NSCoder) { fatalError("init(coder:) unsupported") }
    override func loadView() { let root = Root(); root.owner = self; root.backgroundColor = .clear; view = root }
    override func viewDidLoad() {
        super.viewDidLoad()
        for name in [UIContentSizeCategory.didChangeNotification, NSLocale.currentLocaleDidChangeNotification,
                     UIAccessibility.boldTextStatusDidChangeNotification, UIAccessibility.darkerSystemColorsStatusDidChangeNotification,
                     UIAccessibility.reduceMotionStatusDidChangeNotification] {
            notifications.append(AppearanceObserverTokenV2(NotificationCenter.default.addObserver(forName:name,object:nil,queue:.main) { [weak self] _ in
                MainActor.assumeIsolated { self?.environmentDidInvalidate() }
            }))
        }
        registerForTraitChanges([UITraitUserInterfaceStyle.self, UITraitLayoutDirection.self,
                                UITraitPreferredContentSizeCategory.self, UITraitAccessibilityContrast.self]) { (owner: AppearanceNativeRendererV2, _: UITraitCollection) in
            owner.environmentDidInvalidate()
        }
    }
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        if view.bounds != lastBounds { lastBounds = view.bounds; environmentDidInvalidate() }
    }
    func invalidateEnvironment() { environmentDidInvalidate() }
    private func environmentDidInvalidate() {
        environment.invalidate()
        if snapshot != nil, retiredReason == nil {
            callbacksOpen = false; suspendedReason = "environmentInvalidated"
        }
    }

    func prepare(document: MixerUI.UIDocument) throws -> Candidate {
        try active()
        var staged = reconciler
        let changes: UIChangeSet?
        if let snapshot, snapshot.document == document { changes = nil }
        else { changes = try staged.apply(document) }
        let snapshot = try staged.currentSnapshot()
        return try prepare(staged, snapshot, changes)
    }
    func prepareEnvironment() throws -> Candidate {
        try active()
        return try prepare(reconciler, try reconciler.currentSnapshot(), nil)
    }
    private func prepare(_ staged: UIReconciler, _ snapshot: UIRenderSnapshot, _ changes: UIChangeSet?) throws -> Candidate {
        let baseSerial = serial, baseInteraction = interactionGeneration, baseNativeState = nativeState()
        // No setter, listener change or native parent mutation occurs here.
        // A marked native buffer is not serializable transaction state.
        let captured = try captureEnvironment()
        guard !records.values.contains(where: { $0.field?.markedTextRange != nil }) else { throw Failure.composingEditor }
        let plan = try UIAppearanceResolverV2.prepare(snapshot:snapshot,configuration:installed.configuration,environment:captured,platform:.iOS)
        if let root = plan.nodes.first, case .navigation = root.recipe,
           let child = root.childIDs.first, plan.node(for:child)?.kind != .list,
           plan.nodes.contains(where: { $0.kind == .list }) { throw UIAppearanceErrorV2.unsupportedNativeOperation }
        // First native slices agree across both adapters: nested control rows
        // need separate gesture/hit-envelope proof before admission.
        for row in plan.nodes where row.rowPlacement != nil && !row.childIDs.isEmpty {
            var pending = row.childIDs
            while let id = pending.popLast(), let child = plan.node(for:id) {
                guard child.kind != .button, child.kind != .textField, child.kind != .toggle else { throw UIAppearanceErrorV2.unsupportedNativeOperation }
                pending.append(contentsOf:child.childIDs)
            }
        }
        var editing: [String:String] = [:]
        for node in plan.nodes {
            if let old = records[node.identity.id], old.identity == node.identity,
               case let .text(before) = old.node.recipe, case let .text(after) = node.recipe,
               before.selectable != after.selectable { throw UIAppearanceErrorV2.unsupportedNativeOperation }
            if let old = records[node.identity.id], old.identity == node.identity,
               changes == nil, preservesBoundValue(old.node.recipe,node.recipe), let text = old.field?.text { editing[node.identity.id] = text }
        }
        var sourceNodes: [String:UINode] = [:]
        func index(_ node: UINode) { sourceNodes[node.id] = node; for child in node.children { index(child) } }
        index(snapshot.document.root)
        let layout = AppearanceNativeLayoutV2(plan:plan)
        let theme: UIThemeV2 = switch installed.configuration.mode { case let .shared(theme): theme; case let .platformSpecific(iOS,_,_): iOS }
        let togglePaints = captured.scheme == .light ? theme.light.toggle : theme.dark.toggle
        for record in layout.records.values { record.togglePaints = togglePaints }
        let offsets = records.compactMapValues { $0.scroll?.contentOffset }
        try layout.prepare(rootID:snapshot.document.root.id,editing:editing,scrollOffsets:offsets)
        for (id,record) in layout.records { try record.applyAccessibility(sourceNodes[id]!.properties) }
        guard layout.placements.count <= 16_384 else { throw UIAppearanceErrorV2.layout }
        return Candidate(owner:ownerID,baseSerial:baseSerial,interactionGeneration:baseInteraction,nativeState:baseNativeState,environment:captured,reconciler:staged,snapshot:snapshot,changes:changes,layout:layout)
    }
    func discard(_ candidate: Candidate) throws {
        guard candidate.owner == ownerID else { throw Failure.foreignCandidate }
        guard !candidate.consumed else { throw Failure.consumedCandidate }
        candidate.consumed = true
    }
    /// nil means a successful same-revision environment transaction. It never
    /// means failure; all failed transactions throw and yield no committed plan.
    @discardableResult func commit(_ candidate: Candidate) throws -> UIChangeSet? {
        try active()
        guard candidate.owner == ownerID else { throw Failure.foreignCandidate }
        guard !candidate.consumed else { throw Failure.consumedCandidate }
        candidate.consumed = true
        guard candidate.baseSerial == serial, candidate.interactionGeneration == interactionGeneration, candidate.nativeState == nativeState(), try captureEnvironment() == candidate.environment else { throw Failure.staleCandidate }
        guard !records.values.contains(where: { $0.field?.markedTextRange != nil }) else { throw Failure.composingEditor }
        guard serial < UInt64.max else { retire(Failure.retired); throw Failure.retired }
        var chosen: [String: AppearanceNodeViewV2] = [:]
        for (id,staged) in candidate.layout.records {
            chosen[id] = records[id].flatMap { $0.identity == staged.identity && $0.kind == staged.kind ? $0 : nil } ?? staged
        }
        // Reuse stable decoration parents as well as actual editors/lists. This
        // keeps an unchanged focused field in its native window and parent.
        var chosenDecorations: [String:UIView] = [:]
        for (key,staged) in candidate.layout.decorations {
            if let old = decorations[key], type(of:old) == type(of:staged) { chosenDecorations[key] = old }
            else { chosenDecorations[key] = staged }
        }
        func selected(_ key: String) -> UIView {
            if key == "$root" { return view }
            if key.hasPrefix("$scroll:") { return chosen[String(key.dropFirst(8))]!.scroll! }
            return chosen[key] ?? chosenDecorations[key]!
        }
        let focusedInputs: [UIView] = chosen.values.flatMap { record -> [UIView] in
            var values = [record.field as UIView?,record.button as UIView?,record.toggle as UIView?].compactMap { $0 }
                .filter { $0.isFirstResponder || $0.isFocused }
            if let text = record.selectable, text.isFirstResponder || text.selectedRange.length > 0 { values.append(text) }
            return values
        }
        for placement in candidate.layout.placements {
            let child = selected(placement.key), parent = selected(placement.parent)
            // Moving an ancestor removes its focused descendants from the
            // native window too. Checking only the field's immediate parent
            // would falsely admit that transaction.
            if child.superview !== parent && focusedInputs.contains(where: { $0.isDescendant(of:child) }) {
                throw Failure.focusedReparent
            }
        }
        // Every potentially failing operation is inside the bounded attachment
        // journal. The finish below consists only of prebuilt reference swaps.
        callbacksOpen = false; lastAttachmentOperations = 0; attaching = true
        CATransaction.begin(); CATransaction.setDisableActions(true)
        defer { CATransaction.commit(); attaching = false }
        func journalOperation() throws {
            lastAttachmentOperations += 1
            onAttachmentOperation?(lastAttachmentOperations)
            guard retiredReason == nil else { throw Failure.retired }
            if failAttachmentAfterOperation == lastAttachmentOperations { throw Failure.attachmentFault }
        }
        do {
            for (key,staged) in candidate.layout.decorations {
                let target = chosenDecorations[key]!
                if let target = target as? AppearancePaintViewV2, let source = staged as? AppearancePaintViewV2 {
                    target.density = source.density; target.shapes = source.shapes
                    target.layer.mask = source.layer.mask
                } else if let target = target as? UILabel, let source = staged as? UILabel {
                    target.font = source.font; target.text = source.text; target.numberOfLines = source.numberOfLines
                    target.textColor = source.textColor; target.backgroundColor = source.backgroundColor
                    target.textAlignment = source.textAlignment
                } else { target.backgroundColor = staged.backgroundColor }
                try journalOperation()
            }
            for (id,staged) in candidate.layout.records {
                let target = chosen[id]!
                let sameValue = candidate.changes == nil && preservesBoundValue(target.node.recipe,staged.node.recipe)
                if target !== staged { try target.configure(from:staged,preserveEditing:sameValue) }
                target.inputAllowed = { [weak self, weak target] in
                    guard let self, let target, self.callbacksOpen, self.retiredReason == nil,
                          self.records[target.identity.id] === target, !target.node.disabled else { return false }
                    let input: UIView = (target.field as UIView?) ?? target.button ?? target.toggle ?? target.selectable ?? target
                    guard input.isUserInteractionEnabled, input.isDescendant(of:self.view),
                          let window = self.view.window, input.window === window, window.isKeyWindow,
                          window.windowScene?.activationState == .foregroundActive else { return false }
                    if let control = input as? UIControl, !control.isEnabled { return false }
                    var ancestor: UIView? = input
                    while let view = ancestor { if view.isHidden { return false }; ancestor = view.superview }
                    return self.currentEnvironmentAllowsInput()
                }
                target.field?.inputAllowed = target.inputAllowed; target.toggle?.inputAllowed = target.inputAllowed
                target.event = { [weak self, weak target] kind,value in
                    guard let self, let target else { return }; self.deliver(target,kind,value)
                }
                target.stateChanged = { [weak self, weak target] in
                    guard let self, let target else { return }
                    guard self.callbacksOpen, self.retiredReason == nil, self.currentEnvironmentAllowsInput() else { self.suppressedCallbacks += 1; return }
                    do { try target.repaint() } catch { self.retire(error) }
                }
                target.fault = { [weak self] error in self?.retire(error) }
                target.scrollChanged = { [weak self] in self?.updateNavigation() }
                try journalOperation()
            }
            var origins: [String:CGPoint] = ["$root":.zero]
            func origin(_ key: String) -> CGPoint {
                if let value = origins[key] { return value }
                if key.hasPrefix("$scroll:") { return origin(String(key.dropFirst(8))) }
                guard let placement = candidate.layout.placements.first(where: { $0.key == key }) else { return .zero }
                let parent = origin(placement.parent)
                let value = CGPoint(x:parent.x+placement.frame.minX,y:parent.y+placement.frame.minY)
                origins[key] = value; return value
            }
            for placement in candidate.layout.placements {
                let child = selected(placement.key), parent = selected(placement.parent)
                child.frame = try snapped(placement.frame, origin:origin(placement.parent), environment:candidate.environment)
                if child.superview !== parent { parent.addSubview(child) }
                else if parent.subviews.firstIndex(of:child) != placement.index {
                    parent.insertSubview(child,at:min(placement.index,parent.subviews.count-1))
                }
                try journalOperation()
            }
            // Explicit native container traversal preserves source order even
            // when unequal multiline HStack baselines have different top edges.
            for (id,target) in chosen {
                let children = target.node.childIDs.compactMap { chosen[$0] as UIView? }
                switch target.node.recipe {
                case .text: target.accessibilityElements = [target.selectable as UIView? ?? target.label]
                case .button: target.accessibilityElements = [target.button!]
                case .textField: target.accessibilityElements = [target.field!]
                case .toggle: target.accessibilityElements = [target.toggle!]
                case .list: target.accessibilityElements = [target.scroll!]
                case .section: target.accessibilityElements = (target.label.isHidden || target.label.text?.isEmpty != false ? [] : [target.label as UIView])+children
                case .navigation: target.accessibilityElements = (target.label.text?.isEmpty != false ? [] : [target.label as UIView])+children
                case .vStack,.hStack,.zStack: target.accessibilityElements = children
                }
                if target.scroll != nil {
                    target.scroll!.accessibilityElements = candidate.layout.placements.filter { $0.parent == "$scroll:"+id }.sorted { $0.index < $1.index }.map { selected($0.key) }
                }
                try journalOperation()
            }
            for key in chosenDecorations.keys where key.hasPrefix("$group:") {
                chosenDecorations[key]!.accessibilityElements = candidate.layout.placements.filter { $0.parent == key }.sorted { $0.index < $1.index }.map { selected($0.key) }
                try journalOperation()
            }
            let retained = Set(candidate.layout.placements.map(\.key))
            for (id,record) in records where !retained.contains(id) || chosen[id] !== record {
                record.inputAllowed = nil; record.field?.inputAllowed = nil; record.toggle?.inputAllowed = nil; record.event = nil; record.stateChanged = nil; record.scrollChanged = nil; record.removeFromSuperview()
                try journalOperation()
            }
            for (key,decoration) in decorations where chosenDecorations[key] !== decoration { decoration.removeFromSuperview(); try journalOperation() }
            for record in chosen.values where record.field?.isFirstResponder == true { try record.field!.installManagedPaints(); try journalOperation() }
            guard try captureEnvironment() == candidate.environment else { throw Failure.staleCandidate }
            view.backgroundColor = AppearanceNativeMathV2.color(candidate.layout.plan.canvas)
            view.isUserInteractionEnabled = true
            // Prepared finish: no native setter/listener/allocation/shaping/JNI.
            reconciler = candidate.reconciler; snapshot = candidate.snapshot; plan = candidate.layout.plan
            records = chosen; decorations = chosenDecorations; committedLayout = candidate.layout
            serial += 1; suspendedReason = nil; callbacksOpen = true
            return candidate.changes
        } catch {
            // Partial native setters cannot prove restoration of an IME buffer.
            // Retire and gate the whole owner; never report the old tree preserved.
            retire(error); throw error
        }
    }
    private func snapped(_ rect: CGRect, origin: CGPoint, environment: UIAppearanceEnvironmentV2) throws -> CGRect {
        // Shared absolute edges, then edge subtraction. Child positions can have
        // negative control hit origins inside their authored wrappers; parent
        // placement rectangles themselves are always admitted nonnegative.
        func edge(_ value: CGFloat) throws -> CGFloat {
            let logical = try UIAppearanceGeometryV2.measuredExtent64(Double(value))
            return CGFloat(try UIAppearanceGeometryV2.pixelEdge(logical,density1024:environment.density1024))*1024/CGFloat(environment.density1024)
        }
        let x = try edge(rect.minX+origin.x), y = try edge(rect.minY+origin.y), right = try edge(rect.maxX+origin.x), bottom = try edge(rect.maxY+origin.y)
        return CGRect(x:x-(try edge(origin.x)),y:y-(try edge(origin.y)),width:right-x,height:bottom-y)
    }
    private func preservesBoundValue(_ old: UIResolvedAppearanceRecipeV2,_ new: UIResolvedAppearanceRecipeV2) -> Bool {
        switch (old,new) {
        case let (.textField(_,oldValue,_,_),.textField(_,newValue,_,_)): return oldValue == newValue
        case let (.toggle(_,oldValue,_),.toggle(_,newValue,_)): return oldValue == newValue
        default: return false
        }
    }
    private func nativeState() -> [String:String] {
        var result: [String:String] = [:]
        for (id,record) in records {
            if let field = record.field {
                let selection = field.selectedTextRange.map { "\(field.offset(from:field.beginningOfDocument,to:$0.start)):\(field.offset(from:field.beginningOfDocument,to:$0.end))" } ?? "nil"
                result[id] = "field:\(field.text ?? ""):\(selection):\(field.isFirstResponder):\(field.markedTextRange != nil)"
            } else if let text = record.selectable { result[id] = "selectable:\(text.selectedRange.location):\(text.selectedRange.length):\(text.isFirstResponder):\(text.contentOffset.x):\(text.contentOffset.y)" }
            else if let scroll = record.scroll { result[id] = "scroll:\(scroll.contentOffset.x):\(scroll.contentOffset.y)" }
            else if let toggle = record.toggle { result[id] = "toggle:\(toggle.isOn):\(toggle.isTracking):\(toggle.authoredPressed):\(toggle.isFocused)" }
            else if let button = record.button { result[id] = "button:\(button.isHighlighted):\(button.isFocused)" }
        }
        return result
    }
    private func deliver(_ record: AppearanceNodeViewV2,_ kind: UIEventKind,_ value: UIValue) {
        guard record.inputAllowed?() == true, let snapshot else { suppressedCallbacks += 1; return }
        callbackDepth += 1
        defer { callbackDepth -= 1 }
        do {
            let action = try snapshot.route(UIEventEnvelope(revision:snapshot.document.revision,identity:record.identity,event:kind,value:value))
            guard interactionGeneration < UInt64.max else { retire(Failure.retired); return }
            interactionGeneration += 1
            onAction?(action)
        } catch { /* Native unbound/stale/disabled inputs confer no action. */ }
    }
    private func updateNavigation() {
        guard callbacksOpen, retiredReason == nil, currentEnvironmentAllowsInput(), let layout = committedLayout, let navigation = layout.navigation,
              let record = records[navigation.key], case let .navigation(recipe) = record.node.recipe,
              let child = record.node.childIDs.first, let content = records[child] else { return }
        let scroll = records.values.first(where: { $0.scroll != nil })?.scroll
        let overflow = navigation.expanded-navigation.compact
        let compact = overflow <= 0 || (scroll?.contentOffset.y ?? 0) >= overflow
        let title = compact ? recipe.compactTitle : recipe.expandedTitle
        record.label.font = title.map(AppearanceNativeMathV2.font)
        record.label.text = title?.value; record.label.numberOfLines = compact ? 1 : 0
        record.label.frame = compact ? navigation.compactLabel : navigation.expandedLabel
        if case let .navigation(expanded,compactPaint,_) = record.plan.style(nodeID:record.identity.id)!.paints {
            record.label.textColor = (compact ? compactPaint : expanded).map(AppearanceNativeMathV2.color)
        }
        let bar = compact ? navigation.compact : navigation.expanded
        content.frame.origin.y = bar
        let h = record.bounds.height-bar
        content.frame.size.height = h
        if let scroll = content.scroll { scroll.frame.size.height = h }
    }
    private func currentEnvironmentAllowsInput() -> Bool {
        guard let plan else { return false }
        do {
            guard try captureEnvironment() == plan.environment else {
                callbacksOpen = false; suspendedReason = "staleEnvironment"
                return false
            }
            return true
        } catch { return false }
    }
    private func captureEnvironment() throws -> UIAppearanceEnvironmentV2 {
        do { return try environment.capture(view) }
        catch {
            // Initial attachment may still be pending. A failed recapture after
            // commit cannot leave an active old presentation in a new context.
            if snapshot != nil { retire(error) }
            throw error
        }
    }
    private func active() throws { guard retiredReason == nil else { throw Failure.retired }; guard !attaching else { throw Failure.attachmentInProgress } }
    private func retire(_ error: Error) {
        guard retiredReason == nil else { return }
        callbacksOpen = false; suspendedReason = nil; retiredReason = String(describing:error)
        // Strong records remain owned even through the current callback exit.
        view.isHidden = true; view.isUserInteractionEnabled = false
        for record in records.values { record.inputAllowed = nil; record.field?.inputAllowed = nil; record.toggle?.inputAllowed = nil; record.event = nil; record.stateChanged = nil; record.scrollChanged = nil }
        onRetired?(retiredReason!)
    }
}
#endif
