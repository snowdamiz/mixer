import Foundation
import CryptoKit
import MixerUI

// Public API consumer only. Inputs are generated independently of either resolver;
// the original Swift snapshot supplies the native packet's true identities.
private func object(_ value: Any?) -> [String: Any] { value as! [String: Any] }
private func decimal(_ value: some BinaryInteger) -> String { String(value) }
private func rgba(_ c: UIRGBA8V1) -> String {
    String(format: "#%02X%02X%02X%02X", c.red, c.green, c.blue, c.alpha)
}
private func paint(_ p: UIAppearancePaintV1?) -> Any {
    guard let p else { return NSNull() }
    return ["color": rgba(p.color), "opacityPermille": decimal(p.opacityPermille)]
}
private func text(_ t: UIResolvedTextV1?) -> Any {
    guard let t else { return NSNull() }
    return ["role": t.role.rawValue, "size64": decimal(t.size64), "weight": decimal(t.weight.rawValue),
            "minimumLineBox64": decimal(t.minimumLineBox64), "selectable": t.selectable,
            "maximumLines": t.maximumLines.map(String.init) as Any? ?? NSNull()] as [String: Any]
}
private func insets(_ v: UIInsets64V1) -> [String: Any] {
    ["top": decimal(v.top), "leading": decimal(v.leading), "bottom": decimal(v.bottom), "trailing": decimal(v.trailing)]
}
private func navigation(_ v: UINavigationMetricsV1) -> [String: Any] {
    ["titleInsets64": insets(v.titleInsets64), "minimumBarHeight64": decimal(v.minimumBarHeight64), "titleAlignment": v.titleAlignment.rawValue]
}
private func recipe(_ value: UIResolvedAppearanceRecipeV1) -> [String: Any] {
    switch value {
    case let .text(t): return ["case": "TextRecipe", "text": text(t)]
    case let .button(role, t, m, floor): return ["case": "ButtonRecipe", "role": role.rawValue, "text": text(t),
        "metrics": ["labelInsets64": insets(m.labelInsets64), "minimumWidth64": decimal(m.minimumWidth64),
                    "minimumHeight64": decimal(m.minimumHeight64), "radius64": decimal(m.radius64)], "contentHeightFloor64": decimal(floor)]
    case let .textField(t, m, floor): return ["case": "FieldRecipe", "text": text(t),
        "metrics": ["insets64": insets(m.insets64), "minimumHeight64": decimal(m.minimumHeight64), "border64": decimal(m.border64)], "contentHeightFloor64": decimal(floor)]
    case let .toggle(t, checked, m, floor): return ["case": "ToggleRecipe", "text": text(t), "checked": checked,
        "metrics": ["trackWidth64": decimal(m.trackWidth64), "trackHeight64": decimal(m.trackHeight64), "thumb64": decimal(m.thumb64),
                    "inset64": decimal(m.inset64), "labelGap64": decimal(m.labelGap64), "minimumRow64": decimal(m.minimumRow64)], "contentHeightFloor64": decimal(floor)]
    case let .vStack(spacing, a): return ["case": "VStackRecipe", "spacing64": decimal(spacing), "alignment": a.rawValue]
    case let .hStack(spacing, a): return ["case": "HStackRecipe", "spacing64": decimal(spacing), "alignment": a.rawValue]
    case let .zStack(a): return ["case": "ZStackRecipe", "alignment": a.rawValue]
    case let .list(m, floor): return ["case": "ListRecipe", "metrics": ["insets64": insets(m.insets64), "minimumRow64": decimal(m.minimumRow64),
        "rowGap64": decimal(m.rowGap64), "groupGap64": decimal(m.groupGap64), "separator64": decimal(m.separator64)], "rowHeightFloor64": decimal(floor)]
    case let .section(header, i): return ["case": "SectionRecipe", "header": text(header), "headerInsets64": insets(i)]
    case let .navigation(title, m, floor): return ["case": "NavigationRecipe", "title": text(title), "metrics": navigation(m), "barHeightFloor64": decimal(floor)]
    }
}
private func style(_ s: UIResolvedAppearanceStyleV1) -> [String: Any] {
    ["disabled": s.disabled, "pressed": s.pressed, "focused": s.focused,
     "foreground": paint(s.foreground), "background": paint(s.background), "rowBackground": paint(s.rowBackground),
     "separator": paint(s.separator), "placeholder": paint(s.placeholder), "caret": paint(s.caret), "selection": paint(s.selection),
     "border": paint(s.border), "toggleTrack": paint(s.toggleTrack), "toggleThumb": paint(s.toggleThumb), "pressedOverlay": paint(s.pressedOverlay),
     "focusOutline": s.focusOutline.map { ["paint": paint($0.paint), "width64": decimal($0.width64), "radius64": decimal($0.radius64)] } as Any? ?? NSNull()]
}
private func referenceData(_ value: Any) -> Any {
    if let map = value as? [String: Any] { return map.mapValues(referenceData) }
    if let list = value as? [Any] { return list.map(referenceData) }
    if let number = value as? NSNumber { return number.stringValue }
    return value
}
private func canonical(_ value: Any) throws -> String {
    if value is NSNull { return "null" }
    if let map = value as? [String: Any] {
        return "{" + (try map.keys.sorted().map { key in
            try canonical(key) + ":" + canonical(map[key]!)
        }).joined(separator: ",") + "}"
    }
    if let list = value as? [Any] { return "[" + (try list.map(canonical)).joined(separator: ",") + "]" }
    return String(decoding: try JSONSerialization.data(withJSONObject: value,
        options: [.fragmentsAllowed, .withoutEscapingSlashes]), as: UTF8.self)
}
private func output(_ p: UIResolvedAppearancePlanV1, descriptor: Data) throws -> Data {
    // Retained descriptor references are read independently from the canonical
    // bytes, not reconstructed from a duplicate font/resource implementation.
    let raw = object(try JSONSerialization.jsonObject(with: descriptor))
    let theme = object(raw["mode"] as? String == "shared" ? raw["theme"] : raw[p.platform.rawValue])
    let typography = object(theme["typography"])
    let nodes = p.nodes.map { n -> [String: Any] in
        ["identity": ["id": n.identity.id, "generation": decimal(n.identity.generation)], "kind": n.kind.rawValue,
         "disabled": n.disabled, "childIDs": n.childIDs, "recipe": recipe(n.recipe),
         "styles": (0..<4).map { style(p.style(nodeID: n.identity.id, pressed: $0 & 1 != 0, focused: $0 & 2 != 0)!) }]
    }
    let value: [String: Any] = ["revision": decimal(p.revision), "configurationID": p.configurationID, "recipe": p.recipe.rawValue,
        "canvas": paint(p.canvas), "environment": ["scheme": p.environment.scheme.rawValue, "direction": p.environment.direction.rawValue,
            "textScale1024": decimal(p.environment.textScale1024), "density1024": decimal(p.environment.density1024)],
        "platform": p.platform.rawValue, "platformSpecificReason": p.platformSpecificReason as Any? ?? NSNull(),
        "font": referenceData(typography["font"]!), "resources": referenceData(raw["resources"]!), "nodes": nodes]
    return Data(try canonical(value).utf8)
}
@main struct Oracle {
    static func main() throws {
        guard CommandLine.arguments.count == 3 else { fatalError("input JSONL output TSV") }
        let lines = try String(contentsOfFile: CommandLine.arguments[1], encoding: .utf8).split(separator: "\n")
        let destination = URL(fileURLWithPath: CommandLine.arguments[2])
        _ = FileManager.default.createFile(atPath: destination.path, contents: nil)
        let file = try FileHandle(forWritingTo: destination)
        let valuesURL = URL(fileURLWithPath: destination.path + ".values.jsonl")
        _ = FileManager.default.createFile(atPath: valuesURL.path, contents: nil)
        let valuesFile = try FileHandle(forWritingTo: valuesURL)
        defer { try? file.close(); try? valuesFile.close() }
        var accepted = 0, rejected = 0
        for line in lines {
            let request = object(try JSONSerialization.jsonObject(with: Data(line.utf8)))
            let id = request["id"] as! String, descriptor64 = request["descriptor"] as! String
            let env = object(request["environment"]), platform = request["platform"] as! String
            var packet64 = request["packet"] as! String, digest = "-", status = "rejected"
            var normalized = Data("null".utf8)
            do {
                var reconciler = UIReconciler()
                for history in request["history"] as! [String] {
                    try reconciler.apply(UIDocument.decode(Data(base64Encoded: history)!))
                }
                try reconciler.apply(UIDocument.decode(Data(base64Encoded: request["document"] as! String)!))
                let snapshot = try reconciler.currentSnapshot()
                packet64 = try snapshot.encodeNativePacketV1().base64EncodedString()
                let descriptor = Data(base64Encoded: descriptor64)!
                let config = try UIAppearanceDescriptorCodecV1.decode(descriptor)
                guard let scheme = UIColorSchemeV1(rawValue: env["scheme"] as! String),
                      let direction = UILayoutDirectionV1(rawValue: env["direction"] as! String),
                      let selected = UIAppearancePlatformV1(rawValue: platform),
                      let scale = UInt16(exactly: (env["textScale1024"] as! NSNumber).int64Value),
                      let density = UInt16(exactly: (env["density1024"] as! NSNumber).int64Value) else { throw UIAppearanceErrorV1.number }
                let plan = try UIAppearanceResolverV1.prepare(snapshot: snapshot, configuration: config,
                    environment: UIAppearanceEnvironmentV1(scheme: scheme, direction: direction, textScale1024: scale, density1024: density), platform: selected)
                normalized = try output(plan, descriptor: descriptor)
                digest = SHA256.hash(data: normalized).map { String(format: "%02x", $0) }.joined()
                status = "accepted"; accepted += 1
            } catch { rejected += 1 }
            try valuesFile.write(contentsOf: normalized + Data("\n".utf8))
            let env64 = try JSONSerialization.data(withJSONObject: env, options: [.sortedKeys]).base64EncodedString()
            let fields = [id, status, descriptor64, env64, platform, packet64, digest, request["boundary"] as! String]
            try file.write(contentsOf: Data((fields.joined(separator: "\t") + "\n").utf8))
        }
        print("public Swift oracle cases=\(lines.count) accepted=\(accepted) rejected=\(rejected)")
    }
}
