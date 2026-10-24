import Foundation
import CoreGraphics
import MixerUI

@main enum PolicyProbe {
    static func main() throws {
        var checks: [[String:Any]] = []
        func check(_ name: String, _ pass: Bool) { checks.append(["name":name,"pass":pass]) }
        check("horizontal floor excludes 5.999", !TogglePanPolicy.admits(CGPoint(x:5.999,y:0)))
        check("horizontal floor admits 6", TogglePanPolicy.admits(CGPoint(x:6,y:0)))
        check("equal 1.2 dominance fails", !TogglePanPolicy.admits(CGPoint(x:6,y:5)))
        check("predominantly horizontal admits negative direction", TogglePanPolicy.admits(CGPoint(x:-8,y:1)))
        check("vertical start yields", !TogglePanPolicy.admits(CGPoint(x:2,y:40)))
        check("LTR off right clamps at checked endpoint", TogglePanPolicy.previewX(startX:2,translationX:100) == 24)
        check("LTR on left clamps at unchecked endpoint", TogglePanPolicy.previewX(startX:24,translationX:-100) == 2)
        check("thumb follows intermediate translation", TogglePanPolicy.previewX(startX:2,translationX:8) == 10)
        check("midpoint tie preserves off", !TogglePanPolicy.checked(x:13,previous:false,direction:.leftToRight))
        check("midpoint tie preserves on", TogglePanPolicy.checked(x:13,previous:true,direction:.rightToLeft))
        check("LTR sides map explicitly", !TogglePanPolicy.checked(x:12,previous:true,direction:.leftToRight) && TogglePanPolicy.checked(x:14,previous:false,direction:.leftToRight))
        check("RTL sides map explicitly", TogglePanPolicy.checked(x:12,previous:false,direction:.rightToLeft) && !TogglePanPolicy.checked(x:14,previous:true,direction:.rightToLeft))
        check("top corridor edge accepted", TogglePanPolicy.permitsRelease(y:-22,height:44))
        check("above corridor rejected", !TogglePanPolicy.permitsRelease(y:-22.01,height:44))
        check("bottom corridor edge accepted", TogglePanPolicy.permitsRelease(y:66,height:44))
        check("below corridor rejected", !TogglePanPolicy.permitsRelease(y:66.01,height:44))
        let track = try AppearanceNativePathsV2.make(UIAppearanceGeometryV2.track(),density1024:3072)
        let thumb = try AppearanceNativePathsV2.make(UIAppearanceGeometryV2.thumb(),density1024:3072)
        check("canonical track exact threefold pixel bounds", track.boundingBoxOfPath == CGRect(x:0,y:0,width:189,height:84))
        check("canonical thumb exact threefold pixel bounds", thumb.boundingBoxOfPath == CGRect(x:0,y:0,width:111,height:72))
        check("canonical endpoint travel is 22 points in both directions", UIAppearanceGeometryV2.thumbOrigin(checked:true,direction:.leftToRight).x64 == 1536 && UIAppearanceGeometryV2.thumbOrigin(checked:false,direction:.leftToRight).x64 == 128 && UIAppearanceGeometryV2.thumbOrigin(checked:true,direction:.rightToLeft).x64 == 128 && UIAppearanceGeometryV2.thumbOrigin(checked:false,direction:.rightToLeft).x64 == 1536)
        func context(carrier: String = "carrier-A", window: String = "window-A", binding: UInt64 = 0,
                     x: CGFloat = 20, width: CGFloat = 63, scale: CGFloat = 1) -> TogglePanAdmission.Context {
            TogglePanAdmission.Context(carrier: carrier, window: window, binding: binding, frameInWindow: CGRect(x:x,y:20,width:width,height:44),
                carrierBounds:CGRect(x:0,y:0,width:63,height:44), carrierTransform:.identity, windowBounds:CGRect(x:0,y:0,width:400,height:800),
                basisInWindow:[CGPoint(x:x,y:20),CGPoint(x:x+scale,y:20),CGPoint(x:x,y:21)])
        }
        func captured() -> TogglePanAdmission {
            var value=TogglePanAdmission(); value.capture(touch:"touch-A",point:CGPoint(x:34,y:42),timestamp:1,context:context()); return value
        }
        func decide(_ value: inout TogglePanAdmission, x: CGFloat = 44, y: CGFloat = 42, timestamp: Double = 2,
                    ctx: TogglePanAdmission.Context? = context(), touch: String? = "touch-A", count: Int = 1,
                    active: Bool = true, enabled: Bool = true, allowed: Bool = true) -> TogglePanAdmission.Decision {
            value.decide(touch:touch,current:CGPoint(x:x,y:y),timestamp:timestamp,context:ctx,touchCount:count,touchActive:active,enabled:enabled,allowed:allowed)
        }
        var value=captured(); let accepted=decide(&value)
        check("full public touch displacement admits even if native translation would be two", accepted.accepted && accepted.displacement == CGPoint(x:10,y:0))
        check("decision retains exact origin and attempt for native proof", accepted.origin?.point == CGPoint(x:34,y:42) && accepted.origin?.attempt == accepted.attempt)
        check("repeated same attempt native query stays accepted", decide(&value).accepted && value.origin?.attempt == accepted.attempt)
        check("accepted repeated query still checks geometry", !decide(&value,ctx:context(x:21)).accepted)
        check("restored geometry cannot revive invalidated attempt", !decide(&value).accepted)
        value=captured(); check("repeated query input gate fails closed", decide(&value).accepted && !decide(&value,allowed:false).accepted)
        value=captured(); check("repeated query touch identity fails closed", decide(&value).accepted && !decide(&value,touch:"B").accepted)
        value=captured(); check("repeated query multiple touches fail closed", decide(&value).accepted && !decide(&value,count:2).accepted)
        value=captured(); check("policy failure stable within native attempt", !decide(&value,x:39).accepted && !decide(&value,x:50).accepted)
        value.reset(); check("terminal reset cannot reuse accepted decision", !decide(&value).accepted)
        value=captured(); check("origin five point displacement rejects", !decide(&value,x:39).accepted)
        value=captured(); check("origin exact six point displacement admits", decide(&value,x:40).accepted)
        value=captured(); check("origin exact dominance boundary rejects", !decide(&value,x:40,y:47).accepted)
        value=captured(); check("origin negative horizontal displacement admits", decide(&value,x:24).accepted)
        value=captured(); check("origin vertical displacement rejects", !decide(&value,x:36,y:82).accepted)
        value=captured(); value.capture(touch:"touch-B",point:.zero,timestamp:1.1,context:context())
        check("second touch invalidates instead of replacing initial origin", value.invalidated && value.origin?.touch == "touch-A" && !decide(&value).accepted)
        value=captured(); value.capture(touch:"touch-A",point:.zero,timestamp:1.1,context:context())
        check("duplicate touch capture fails closed", !decide(&value).accepted)
        value=captured(); check("multi touch count rejects", !decide(&value,count:2).accepted)
        value=captured(); check("zero touch count rejects", !decide(&value,count:0).accepted)
        value=captured(); check("different touch identity rejects", !decide(&value,touch:"touch-B").accepted)
        value=captured(); check("released weak touch rejects", !decide(&value,touch:nil).accepted)
        value=captured(); check("terminal touch phase rejects", !decide(&value,active:false).accepted)
        value=captured(); check("disabled admission rejects", !decide(&value,enabled:false).accepted)
        value=captured(); check("stale input gate rejects", !decide(&value,allowed:false).accepted)
        for (name, ctx) in [("carrier identity",context(carrier:"B")),("window identity",context(window:"B")),("binding generation",context(binding:1)),
                            ("carrier movement",context(x:21)),("carrier size",context(width:64)),("ancestor basis transform",context(scale:-1))] {
            value=captured(); check("changed \(name) rejects origin", !decide(&value,ctx:ctx).accepted)
        }
        value=captured(); check("detached window rejects", !decide(&value,ctx:nil).accepted)
        value=captured(); check("backwards native touch time rejects", !decide(&value,timestamp:0.9).accepted)
        value=captured(); check("nonfinite current point rejects", !decide(&value,x:.infinity).accepted)
        value=captured(); check("nonfinite native touch time rejects", !decide(&value,timestamp:.nan).accepted)
        value=TogglePanAdmission(); value.capture(touch:"A",point:CGPoint(x:CGFloat.infinity,y:0),timestamp:1,context:context())
        check("nonfinite origin never accepted", value.invalidated && !decide(&value,touch:"A").accepted)
        value=TogglePanAdmission(); value.capture(touch:"A",point:.zero,timestamp:1,context:context(width:0))
        check("empty geometry never captures", value.invalidated && value.origin == nil)
        value=captured(); value.reset(); check("cancel reset cannot reuse old origin", !decide(&value).accepted)
        value=captured(); value.invalidate(); check("geometry invalidation persists through decision", !decide(&value).accepted)
        value.reset(); value.capture(touch:"new-touch",point:CGPoint(x:34,y:42),timestamp:3,context:context(binding:2))
        check("fresh post cancellation attempt can admit", decide(&value,timestamp:4,ctx:context(binding:2),touch:"new-touch").accepted)
        let result: [String:Any] = ["scope":"Host executable policy and CoreGraphics path checks only; no UIKit input/runtime/VoiceOver/visual qualification", "checks":checks, "pass":checks.allSatisfy { $0["pass"] as? Bool == true }]
        let data = try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys])
        FileHandle.standardOutput.write(data);FileHandle.standardOutput.write(Data([10]))
        if checks.contains(where: { $0["pass"] as? Bool != true }) { exit(1) }
    }
}
