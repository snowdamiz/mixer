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
        let result: [String:Any] = ["scope":"Host executable policy and CoreGraphics path checks only; no UIKit input/runtime/VoiceOver/visual qualification", "checks":checks, "pass":checks.allSatisfy { $0["pass"] as? Bool == true }]
        let data = try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys])
        FileHandle.standardOutput.write(data);FileHandle.standardOutput.write(Data([10]))
        if checks.contains(where: { $0["pass"] as? Bool != true }) { exit(1) }
    }
}
