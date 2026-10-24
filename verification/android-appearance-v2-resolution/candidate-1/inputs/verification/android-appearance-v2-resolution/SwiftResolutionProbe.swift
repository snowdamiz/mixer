import Foundation
import MixerUI

// Verification-only projection. It serializes actual product output; reflection
// never participates in product admission or grants operation authority.
func tree(_ value: Any) -> Any {
    if let identity = value as? UINodeIdentity { return ["id": identity.id, "generation": String(identity.generation)] }
    if let font = value as? UIFontSourceV1 {
        switch font {
        case .systemSans: return ["kind": "systemSans"]
        case let .bundled(faces, fallback): return ["kind":"bundled", "faces":tree(faces), "fallback":tree(fallback)]
        }
    }
    if let raw = value as? any RawRepresentable { return tree(raw.rawValue) }
    let mirror = Mirror(reflecting: value)
    if mirror.displayStyle == .optional { return mirror.children.first.map { tree($0.value) } ?? NSNull() }
    if mirror.displayStyle == .collection { return mirror.children.map { tree($0.value) } }
    if mirror.displayStyle == .struct {
        var fields: [String:Any] = [:]
        for field in mirror.children { fields[field.label!] = tree(field.value) }
        return fields
    }
    return value
}
func recipe(_ value: UIResolvedAppearanceRecipeV2) -> Any {
    switch value {
    case let .text(text): return ["text":tree(text)]
    case let .button(role,text,metrics): return ["role":tree(role),"text":tree(text),"metrics":tree(metrics)]
    case let .textField(label,value,text,metrics): return ["label":label,"value":value,"text":tree(text),"metrics":tree(metrics)]
    case let .toggle(text,checked,metrics): return ["text":tree(text),"checked":checked,"metrics":tree(metrics)]
    case let .vStack(gaps,alignment): return ["gaps64":gaps,"alignment":tree(alignment)]
    case let .hStack(gaps,alignment): return ["gaps64":gaps,"alignment":tree(alignment)]
    case let .zStack(alignment): return ["alignment":tree(alignment)]
    case let .list(list):
        let groups = list.groups.map { group -> [String:Any] in
            let source: [String:Any]
            switch group.source {
            case let .section(identity): source = ["identity":tree(identity)]
            case let .directRun(identity): source = ["firstRow":tree(identity)]
            }
            return ["source":source,"header":tree(group.header),"rowIdentities":tree(group.rowIdentities),
                "visible":group.visible,"leadingGap64":group.leadingGap64,"headerToRowsGap64":group.headerToRowsGap64]
        }
        return ["metrics":tree(list.metrics),"rowHeightFloor64":list.rowHeightFloor64,"groups":groups,"trailingPadding64":list.trailingPadding64]
    case let .section(section):
        let context: [String:Any]
        switch section.context {
        case .outsideList: context = [:]
        case let .listGroup(owner,index): context = ["listIdentity":tree(owner),"groupIndex":index]
        case let .withinListRow(owner): context = ["listIdentity":tree(owner)]
        }
        return ["header":tree(section.header),"context":context,"headerToContentGap64":section.headerToContentGap64,
            "contentGaps64":section.contentGaps64,"alignment":tree(section.alignment)]
    case let .navigation(value): return tree(value)
    }
}
func style(_ value: UIResolvedAppearanceStyleV2) -> Any {
    let paints: Any
    switch value.paints {
    case let .text(foreground,background): paints = ["foreground":tree(foreground),"background":tree(background)]
    case let .container(background): paints = ["background":tree(background)]
    case let .list(canvas,surface,separator): paints = ["canvas":tree(canvas),"surface":tree(surface),"separator":tree(separator)]
    case let .section(header,background): paints = ["header":tree(header),"background":tree(background)]
    case let .navigation(expanded,compact,background): paints = ["expanded":tree(expanded),"compact":tree(compact),"background":tree(background)]
    case let .button(paint,focus): paints = ["paint":tree(paint),"focus":tree(focus)]
    case let .field(paint): paints = ["paint":tree(paint)]
    case let .toggle(paint,focus): paints = ["paint":tree(paint),"focus":tree(focus)]
    }
    return ["disabled":value.disabled,"pressed":value.pressed,"focused":value.focused,"paints":paints]
}
func projection(_ plan: UIResolvedAppearancePlanV2) -> Any {
    let nodes = plan.nodes.map { node -> [String:Any] in
        ["identity":tree(node.identity),"kind":node.kind.rawValue,"childIDs":node.childIDs,"disabled":node.disabled,
         "rowPlacement":tree(node.rowPlacement),"recipe":recipe(node.recipe),
         "styles":[style(plan.style(nodeID:node.identity.id)!),style(plan.style(nodeID:node.identity.id,pressed:true)!),
             style(plan.style(nodeID:node.identity.id,focused:true)!),style(plan.style(nodeID:node.identity.id,pressed:true,focused:true)!)]]
    }
    let e = plan.environment
    let environment: [String:Any] = ["scheme":tree(e.scheme),"direction":tree(e.direction),"profile":tree(e.profile),"density1024":e.density1024,
        "viewport":tree(e.viewport),"safeArea64":tree(e.safeArea64),"localeIdentifier":e.localeIdentifier,
        "accessibility":tree(e.accessibility),"generation":String(e.generation)]
    return ["revision":String(plan.revision),"configurationID":plan.configurationID,"recipe":tree(plan.recipe),"canvas":tree(plan.canvas),
        "environment":environment,"platform":tree(plan.platform),"platformSpecificReason":tree(plan.platformSpecificReason),
        "font":tree(plan.font),"resources":tree(plan.resources),"nodes":nodes]
}
@main struct Probe {
    static func main() throws {
        let input = try String(contentsOfFile:CommandLine.arguments[1],encoding:.utf8)
        var reconciler = UIReconciler()
        var count = 0
        for line in input.split(separator:"\n") {
            let f = line.split(separator:"\t",omittingEmptySubsequences:false).map(String.init)
            let document = try UIDocument.decode(Data(base64Encoded:f[1])!)
            try reconciler.apply(document)
            let snapshot = try reconciler.currentSnapshot()
            let packet = try snapshot.encodeNativePacketV1()
            let e = f[3].split(separator:"|",omittingEmptySubsequences:false).map(String.init)
            let environment = UIAppearanceEnvironmentV2(scheme:UIColorSchemeV1(rawValue:e[0])!,direction:UILayoutDirectionV1(rawValue:e[1])!,
                profile:UISharedTextProfileV1(rawValue:e[2])!,density1024:UInt16(e[3])!,
                viewport:UIAppearanceViewportV2(width64:UInt32(e[4])!,height64:UInt32(e[5])!),
                safeArea64:UIInsets64V1(top:UInt32(e[6])!,leading:UInt32(e[7])!,bottom:UInt32(e[8])!,trailing:UInt32(e[9])!),
                localeIdentifier:String(data:Data(base64Encoded:e[10])!,encoding:.utf8)!,
                accessibility:UIAppearanceAccessibilityV2(boldText:e[11]=="1",increasedContrast:e[12]=="1",reduceMotion:e[13]=="1"),generation:UInt64(e[14])!)
            let result: Data
            do {
                let bytes = Data(base64Encoded:f[2])!
                let configuration = try UIAppearanceDescriptorCodecV2.decode(bytes)
                precondition(try UIAppearanceDescriptorCodecV2.canonicalData(configuration) == bytes)
                let plan = try UIAppearanceResolverV2.prepare(snapshot:snapshot,configuration:configuration,environment:environment,
                    platform:UIAppearancePlatformV2(rawValue:f[4])!)
                result = try JSONSerialization.data(withJSONObject:projection(plan),options:[.sortedKeys,.withoutEscapingSlashes])
                precondition(plan.nodes.count == snapshot.nodeCount && snapshot.document == document)
            } catch let error as UIAppearanceErrorV2 { result = Data(("error:"+String(describing:error)).utf8) }
            print([f[0],packet.base64EncodedString(),f[2],f[3],f[4],result.base64EncodedString()].joined(separator:"\t"))
            count += 1
        }
        FileHandle.standardError.write(Data("PASS actual Swift resolver cases=\(count)\n".utf8))
    }
}
