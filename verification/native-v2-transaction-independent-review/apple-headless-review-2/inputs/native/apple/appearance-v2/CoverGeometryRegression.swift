import CoreGraphics
import MixerUI
#if canImport(UIKit)
import UIKit
@testable import MixerAppearanceInternal
#endif

/// Pure macOS CoreGraphics regressions execute against the production helper.
/// Detached UIKit regressions are compiled only; neither confers native UI qualification.
enum AppearanceCoverGeometryRegressionV2 {
    struct Outcome { let name: String; let passed: Bool }
    struct Fixture {
        let placements: [AppearanceNativeGeometryV2.Placement]
        let coverLocal: CGRect
        let fieldLocal: CGRect
    }
    static func fixture() -> Fixture {
        let floor: CGFloat = 3347/64, fieldHeight: CGFloat = 3821/64
        let toggleHit = CGRect(x:291,y:(floor-44)/2,width:63,height:44)
        return Fixture(placements:[
            .init(key:"group",parent:"$root",frame:CGRect(x:0,y:3053/64,width:370,height:floor*2+fieldHeight),index:0),
            .init(key:"empty",parent:"group",frame:CGRect(x:0,y:0,width:370,height:floor),index:0),
            .init(key:"toggle",parent:"group",frame:CGRect(x:0,y:floor,width:370,height:floor),index:1),
            .init(key:"field",parent:"group",frame:CGRect(x:0,y:floor*2,width:370,height:fieldHeight),index:2)],
            coverLocal:toggleHit.insetBy(dx:-12,dy:-12),fieldLocal:CGRect(x:16,y:(fieldHeight-44)/2,width:338,height:44))
    }
    static func rejects(_ operation: () throws -> Void) -> Bool { do { try operation(); return false } catch { return true } }
    static func pure() throws -> [Outcome] {
        let fixture = fixture(), path = CGPath(rect:CGRect(x:0,y:0,width:370,height:200),transform:nil)
        let logical = Dictionary(uniqueKeysWithValues:fixture.placements.map { ($0.key,$0.frame) })
        let oldCover = fixture.coverLocal.offsetBy(dx:0,dy:logical["toggle"]!.minY)
        let oldField = fixture.fieldLocal.offsetBy(dx:0,dy:logical["field"]!.minY)
        let final = Dictionary(uniqueKeysWithValues:try AppearanceNativeGeometryV2.prepare(fixture.placements,density1024:1024).map { ($0.key,$0.frame) })
        let cover = fixture.coverLocal.offsetBy(dx:0,dy:final["toggle"]!.minY)
        let field = fixture.fieldLocal.offsetBy(dx:0,dy:final["field"]!.minY)
        let groupBounds = CGRect(origin:.zero,size:final["group"]!.size)
        var outcomes = [Outcome(name:"logical-touch-is-empty-before-snap",passed:oldCover.intersection(oldField).isEmpty),
            Outcome(name:"final-row-overlap-exact-19-over64",passed:cover.intersection(field).height == 19/64),
            Outcome(name:"same-helper-rejects-final-cover-overlap",passed:rejects { try AppearanceNativeGeometryV2.validateCover(cover,foreground:[field],groupBounds:groupBounds,groupPath:path,density1024:1024) })]
        try AppearanceNativeGeometryV2.validateCover(cover,foreground:[CGRect(x:0,y:cover.minY,width:100,height:44)],groupBounds:groupBounds,groupPath:path,density1024:1024)
        outcomes.append(Outcome(name:"disjoint-final-foreground-admitted",passed:true))
        let logicalRowHeight: CGFloat = 2835/64
        let carrier = CGRect(x:16,y:(logicalRowHeight-44)/2,width:338,height:44)
        let row = try AppearanceNativeGeometryV2.snapped(CGRect(x:0,y:0,width:370,height:logicalRowHeight),parentOrigin:.zero,density1024:1024)
        outcomes.append(Outcome(name:"logical-carrier-fit-before-snap",passed:CGRect(x:0,y:0,width:370,height:logicalRowHeight).contains(carrier)))
        outcomes.append(Outcome(name:"same-helper-rejects-final-carrier-spill",passed:rejects { try AppearanceNativeGeometryV2.validateCarrier(carrier,rowBounds:CGRect(origin:.zero,size:row.size)) }))
        outcomes.append(Outcome(name:"actual-group-bounds-required-besides-mask",passed:rejects { try AppearanceNativeGeometryV2.validateCover(CGRect(x:20,y:99.875,width:20,height:0.25),foreground:[],groupBounds:CGRect(x:0,y:0,width:370,height:100),groupPath:path,density1024:1024) }))
        // A scroll alias contributes the same logical parent origin as its List;
        // contentOffset is a common ancestor translation, not an edge-snap input.
        let aliases:[AppearanceNativeGeometryV2.Placement] = [
            .init(key:"list",parent:"$root",frame:CGRect(x:0,y:47.703125,width:370,height:400),index:0),
            .init(key:"group",parent:"$scroll:list",frame:CGRect(x:0,y:52.296875,width:370,height:100),index:0),
            .init(key:"row",parent:"group",frame:CGRect(x:0,y:52.296875,width:370,height:44),index:0)]
        let projected = try AppearanceNativeGeometryV2.prepare(aliases,density1024:1024)
        outcomes.append(Outcome(name:"nested-parent-scroll-alias-final-edges",passed:projected[0].frame.minY+projected[1].frame.minY+projected[2].frame.minY == 152))
        return outcomes
    }
#if canImport(UIKit)
    @MainActor static func nativeDetached() throws -> [Outcome] {
        let fixture = fixture(), final = try AppearanceNativeGeometryV2.prepare(fixture.placements,density1024:1024)
        var views: [String:UIView] = ["$root":UIView(frame:CGRect(x:0,y:0,width:400,height:400))]
        for placement in final {
            let child = UIView(frame:placement.frame); views[placement.key] = child
            views[placement.parent]!.addSubview(child)
        }
        let field = UITextField(frame:fixture.fieldLocal); views["field"]!.addSubview(field)
        let plane = views["group"]!, cover = views["toggle"]!.convert(fixture.coverLocal,to:plane), hit = field.convert(field.bounds,to:plane)
        let path = CGPath(rect:CGRect(x:0,y:0,width:370,height:200),transform:nil)
        return [Outcome(name:"detached-uikit-final-overlap-exact-19-over64",passed:cover.intersection(hit).height == 19/64),
            Outcome(name:"detached-uikit-final-conversion-rejects-cover",passed:rejects { try AppearanceNativeGeometryV2.validateCover(cover,foreground:[hit],groupBounds:plane.bounds,groupPath:path,density1024:1024) })]
    }
#endif
}
