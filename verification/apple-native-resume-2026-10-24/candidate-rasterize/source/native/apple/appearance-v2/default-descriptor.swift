import Foundation
import MixerUI
@main struct DescriptorEmitter {
static func main() throws {
let destination = URL(fileURLWithPath:CommandLine.arguments[1])
let configuration = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
let bytes = try UIAppearanceDescriptorCodecV2.canonicalData(configuration)
try bytes.write(to:destination)
let resource = UIAppearanceResourceV1(id:"unused",kind:.iconPNG,path:"unused.png",sha256:String(repeating:"0",count:64),bytes:1,provenance:"owned rejection fixture; no redistributed image",scale:1,locale:"und",direction:.neutral)
let unsupported = UIAppearanceConfigurationV2(id:configuration.id,mode:configuration.mode,resources:[resource])
try UIAppearanceDescriptorCodecV2.canonicalData(unsupported).write(to:URL(fileURLWithPath:CommandLine.arguments[2]))

if CommandLine.arguments.count > 4, case let .shared(theme) = configuration.mode {
    let m = theme.groupedList
    let floors = UIProfileFloorsV2(xs:1792,s:1792,m:1792,l:1792,xl:1792,xxl:1792,xxxl:1792,a1:1792,a2:1792,a3:1792,a4:1792,a5:1792)
    let rows = UIGroupedListMetricsV2(outerHorizontal64:m.outerHorizontal64,contentInsets64:UIInsets64V1(top:0,leading:m.contentInsets64.leading,bottom:0,trailing:m.contentInsets64.trailing),topPadding64:m.topPadding64,bottomPadding64:m.bottomPadding64,headerToGroup64:m.headerToGroup64,groupToNextHeader64:m.groupToNextHeader64,groupWithoutHeaderGap64:m.groupWithoutHeaderGap64,profileFloors64:floors,separatorInset64:m.separatorInset64,separatorThickness64:m.separatorThickness64,outline:m.outline,radius64:m.radius64,rowPolicy:m.rowPolicy,separatorPolicy:m.separatorPolicy)
    let short = UIThemeV2(recipe:theme.recipe,typography:theme.typography,light:theme.light,dark:theme.dark,stacks:theme.stacks,groupedList:rows,button:theme.button,field:theme.field,toggle:theme.toggle,navigation:theme.navigation)
    try UIAppearanceDescriptorCodecV2.canonicalData(UIAppearanceConfigurationV2(id:"short-rows-fixture",mode:.shared(short))).write(to:URL(fileURLWithPath:CommandLine.arguments[4]))
}
var reconciler = UIReconciler()
_ = try reconciler.apply(AppearanceFixtureV2.document(1))
if CommandLine.arguments.count > 3 {
try reconciler.currentSnapshot().encodeNativePacketV1().write(to:URL(fileURLWithPath:CommandLine.arguments[3]))
}
}
}
