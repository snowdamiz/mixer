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

var reconciler = UIReconciler()
_ = try reconciler.apply(AppearanceFixtureV2.document(1))
if CommandLine.arguments.count > 3 {
try reconciler.currentSnapshot().encodeNativePacketV1().write(to:URL(fileURLWithPath:CommandLine.arguments[3]))
}
}
}
