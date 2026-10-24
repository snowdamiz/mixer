import Foundation
import MixerUI

// Serialization only. Expected semantics live in the independent Python oracle.
func jsonValue(_ value: Any) -> Any {
    switch value {
    case let v as String: return v
    case let v as Bool: return v
    case let v as UInt8: return Int(v)
    case let v as UInt16: return Int(v)
    case let v as UInt32: return Int(v)
    case let v as UInt64: return String(v)
    case let v as Int: return v
    case let v as UIRGBA8V1: return String(format: "#%02X%02X%02X%02X", v.red, v.green, v.blue, v.alpha)
    default:
        let m = Mirror(reflecting: value)
        if m.displayStyle == .enum { return String(describing: value) }
        if m.displayStyle == .collection { return m.children.map { jsonValue($0.value) } }
        var result: [String: Any] = [:]
        for child in m.children { result[child.label!] = jsonValue(child.value) }
        return result
    }
}
func identity(_ value: UINodeIdentity) -> [String: Any] { ["id": value.id, "generation": String(value.generation)] }
func text(_ value: UIResolvedTextV2?) -> Any {
    guard let value else { return NSNull() }
    return ["value": value.value, "role": value.role.rawValue, "size64": Int(value.metrics.size64),
            "weight": Int(value.metrics.weight.rawValue), "selectable": value.selectable,
            "maximumLines": value.maximumLines.map { $0 as Any } ?? NSNull()] as [String: Any]
}
func recipe(_ value: UIResolvedAppearanceRecipeV2) -> [String: Any] {
    switch value {
    case let .text(v): return ["text": text(v)]
    case let .button(role, v, metrics): return ["role": role.rawValue, "text": text(v), "metrics": jsonValue(metrics)]
    case let .textField(label, value, v, metrics): return ["label": label, "value": value, "text": text(v), "metrics": jsonValue(metrics)]
    case let .toggle(v, checked, metrics): return ["text": text(v), "checked": checked, "metrics": jsonValue(metrics)]
    case let .vStack(gaps, alignment): return ["gaps64": gaps, "alignment": alignment.rawValue]
    case let .hStack(gaps, alignment): return ["gaps64": gaps, "alignment": alignment.rawValue]
    case let .zStack(alignment): return ["alignment": alignment.rawValue]
    case let .list(v):
        let groups = v.groups.map { g -> [String: Any] in
            let source: [String: Any]
            switch g.source {
            case let .section(id): source = ["section": identity(id)]
            case let .directRun(id): source = ["directRun": identity(id)]
            }
            return ["source": source, "header": text(g.header), "rows": g.rowIdentities.map(identity), "visible": g.visible,
                    "drawsOutline": g.drawsOutline, "leadingGap64": g.leadingGap64, "headerToRowsGap64": g.headerToRowsGap64]
        }
        return ["groups": groups, "metrics": jsonValue(v.metrics), "rowHeightFloor64": v.rowHeightFloor64, "trailingPadding64": v.trailingPadding64]
    case let .section(v):
        let context: [String: Any]
        switch v.context {
        case .outsideList: context = ["kind": "outsideList"]
        case let .withinListRow(id): context = ["kind": "withinListRow", "list": identity(id)]
        case let .listGroup(id, index): context = ["kind": "listGroup", "list": identity(id), "groupIndex": index]
        }
        return ["header": text(v.header), "context": context, "headerToContentGap64": v.headerToContentGap64,
                "contentGaps64": v.contentGaps64, "alignment": v.alignment.rawValue]
    case let .navigation(v): return ["expandedTitle": text(v.expandedTitle), "compactTitle": text(v.compactTitle), "metrics": jsonValue(v.metrics)]
    }
}
func style(_ value: UIResolvedAppearanceStyleV2) -> [String: Any] {
    let paints: [String: Any]
    switch value.paints {
    case let .text(foreground, background): paints = ["foreground": jsonValue(foreground), "background": jsonValue(background)]
    case let .container(background): paints = ["background": jsonValue(background)]
    case let .list(canvas, surface, separator): paints = ["canvas": jsonValue(canvas), "surface": jsonValue(surface), "separator": jsonValue(separator)]
    case let .section(header, background): paints = ["header": header.map(jsonValue) ?? NSNull(), "background": jsonValue(background)]
    case let .navigation(expanded, compact, background): paints = ["expanded": expanded.map(jsonValue) ?? NSNull(), "compact": compact.map(jsonValue) ?? NSNull(), "background": jsonValue(background)]
    case let .button(paint, focus): paints = ["paint": jsonValue(paint), "focus": focus.map(jsonValue) ?? NSNull()]
    case let .field(paint): paints = ["paint": jsonValue(paint)]
    case let .toggle(paint, focus): paints = ["paint": jsonValue(paint), "focus": focus.map(jsonValue) ?? NSNull()]
    }
    return ["disabled": value.disabled, "pressed": value.pressed, "focused": value.focused, "paints": paints]
}
func integer(_ value: Any?) -> UInt32 { (value as! NSNumber).uint32Value }
@main struct Probe {
    static func main() throws {
        let input = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))) as! [[String: Any]]
        var result: [[String: Any]] = []
        for item in input {
            do {
                let source = item["document"] as! [String: Any]
                let limits: UIValidationLimits = (item["wideLimits"] as? Bool == true) ?
                    UIValidationLimits(maximumMessageBytes: 2097152, maximumNodes: 8192, maximumDepth: 128, maximumChildrenPerNode: 2000, maximumStringBytes: 32768) : .standard
                let document = try UIDocument.decode(JSONSerialization.data(withJSONObject: source), validator: UIValidator(limits: limits))
                var reconciler = UIReconciler(validator: UIValidator(limits: limits))
                try reconciler.apply(document)
                let snapshot = try reconciler.currentSnapshot()
                let c = try UIAppearanceDescriptorCodecV2.decode(Data((item["configuration"] as! String).utf8))
                let e = item["environment"] as! [String: Any]
                let safe = e["safeArea64"] as! [String: Any]
                let environment = UIAppearanceEnvironmentV2(scheme: UIColorSchemeV1(rawValue: e["scheme"] as! String)!,
                    direction: UILayoutDirectionV1(rawValue: e["direction"] as! String)!,
                    profile: UISharedTextProfileV1(rawValue: e["profile"] as! String)!, density1024: UInt16(integer(e["density1024"])),
                    viewport: UIAppearanceViewportV2(width64: integer(e["width64"]), height64: integer(e["height64"])),
                    safeArea64: UIInsets64V1(top: integer(safe["top"]), leading: integer(safe["leading"]), bottom: integer(safe["bottom"]), trailing: integer(safe["trailing"])),
                    localeIdentifier: e["locale"] as! String,
                    accessibility: UIAppearanceAccessibilityV2(boldText: e["bold"] as! Bool, increasedContrast: e["contrast"] as! Bool, reduceMotion: e["motion"] as! Bool),
                    generation: UInt64(e["generation"] as! String)!)
                let plan = try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: c, environment: environment,
                    platform: UIAppearancePlatformV2(rawValue: item["platform"] as! String)!)
                let before = plan.nodes
                let nodes = plan.nodes.map { n -> [String: Any] in
                    let row = n.rowPlacement.map { ["list": identity($0.listIdentity), "groupIndex": $0.groupIndex, "rowIndex": $0.rowIndex, "separatorAfter": $0.separatorAfter] as [String: Any] }
                    var styles: [[String: Any]] = []
                    for pressed in [false, true] { for focused in [false, true] { styles.append(style(plan.style(nodeID: n.identity.id, pressed: pressed, focused: focused)!)) } }
                    return ["identity": identity(n.identity), "kind": n.kind.rawValue, "children": n.childIDs, "disabled": n.disabled,
                            "row": row as Any? ?? NSNull(), "recipe": recipe(n.recipe), "styles": styles,
                            "snapshotIdentityMatches": snapshot.identity(for: n.identity.id) == n.identity]
                }
                result.append(["name": item["name"]!, "nodes": nodes, "canvas": jsonValue(plan.canvas),
                    "revision": String(plan.revision), "configurationID": plan.configurationID, "platform": plan.platform.rawValue,
                    "reason": plan.platformSpecificReason as Any? ?? NSNull(), "environment": jsonValue(plan.environment),
                    "stylesPreserveNodes": before == plan.nodes,
                    "missingReturnsNil": plan.node(for: "\u{0000}missing") == nil && plan.style(nodeID: "\u{0000}missing") == nil,
                    "resourceCount": plan.resources.count])
            } catch { result.append(["name": item["name"]!, "error": String(reflecting: error)]) }
        }
        let output = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys, .withoutEscapingSlashes])
        try output.write(to: URL(fileURLWithPath: CommandLine.arguments[2]))
        print("Produced \(result.count) independently comparable case results")
    }
}
