import MixerUI

@main struct PublicResolutionConsumerV2 {
    static func main() throws {
        let root = UINode(id: "nav", kind: .navigation, properties: ["title": .string("Title")], children: [
            UINode(id: "list", kind: .list, children: [UINode(id: "section", kind: .section, properties: ["title": .string("Header")], children: [
                UINode(id: "v", kind: .vStack, children: [
                    UINode(id: "text", kind: .text, properties: ["text": .string("Body")]),
                    UINode(id: "caption", kind: .text, properties: ["text": .string("Caption"), "style": .string("caption")]),
                    UINode(id: "button", kind: .button, properties: ["label": .string("Action")], actions: [UIActionBinding(id: "action", event: .activate)]),
                    UINode(id: "field", kind: .textField, properties: ["label": .string("Placeholder"), "value": .string("Value")], actions: [UIActionBinding(id: "edit", event: .textChange)]),
                    UINode(id: "toggle", kind: .toggle, properties: ["label": .string("Toggle"), "value": .bool(true)], actions: [UIActionBinding(id: "switch", event: .valueChange)]),
                    UINode(id: "h", kind: .hStack), UINode(id: "z", kind: .zStack)])])])])
        var reconciler = UIReconciler()
        try reconciler.apply(UIDocument(revision: 7, root: root))
        let snapshot = try reconciler.currentSnapshot()
        let configuration = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
        for profile in UISharedTextProfileV1.allCases {
            let environment = UIAppearanceEnvironmentV2(scheme: .light, direction: .rightToLeft, profile: profile,
                density1024: 3072, viewport: UIAppearanceViewportV2(width64: 25728, height64: 55936),
                safeArea64: UIInsets64V1(top: 0, leading: 0, bottom: 0, trailing: 0), localeIdentifier: "ar",
                accessibility: UIAppearanceAccessibilityV2(boldText: false, increasedContrast: false, reduceMotion: true), generation: 2)
            let plan = try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: configuration, environment: environment, platform: .android)
            precondition(plan.nodes.count == 11 && plan.revision == 7 && plan.canvas.alpha == 255)
            precondition(plan.nodes.map(\.identity.id) == ["nav","list","section","v","text","caption","button","field","toggle","h","z"])
            for node in plan.nodes { precondition(node.identity == snapshot.identity(for: node.identity.id)) }
            guard case let .vStack(gaps, _) = plan.node(for: "v")?.recipe,
                  case let .list(list) = plan.node(for: "list")?.recipe,
                  case let .navigation(nav) = plan.node(for: "nav")?.recipe,
                  case let .button(paint, focus) = plan.style(nodeID: "button", pressed: true, focused: true)?.paints,
                  case let .field(field) = plan.style(nodeID: "field", pressed: true, focused: true)?.paints,
                  case let .toggle(toggle, _) = plan.style(nodeID: "toggle", pressed: true)?.paints else { fatalError("Missing V2 payload") }
            precondition(gaps == [128,512,512,512,512,512] && list.groups.count == 1)
            precondition(list.groups[0].rowIdentities == [plan.node(for: "v")!.identity])
            precondition(plan.node(for: "v")?.rowPlacement?.separatorAfter == false)
            precondition(nav.expandedTitle?.role == .navigationExpanded && nav.compactTitle?.maximumLines == 1)
            precondition(paint.background.alpha == 31 && focus?.width64 == 128 && field.selection.alpha == 61 && toggle.overlay.alpha == 31)
            let origin = UIAppearanceGeometryV2.thumbOrigin(checked: true, direction: environment.direction)
            precondition(origin.x64 == 128)
            let path = try UIAppearanceGeometryV2.group(width64: 100, height64: 100, radius64: 1664)
            let pixelEdge = try UIAppearanceGeometryV2.pixelEdge(64, density1024: environment.density1024)
            precondition(path.commands.count == 18 && pixelEdge == 3)
        }
        print("PASS public V2 resolver: 12 profiles, 11 nodes, all 10 kinds, exact gaps/groups/state/identity and V2 geometry reuse")
    }
}
