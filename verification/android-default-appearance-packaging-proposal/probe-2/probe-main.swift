import Foundation
import MixerUI
let value = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
guard case let .shared(theme) = value.mode, value.resources.isEmpty,
      case .systemSans = theme.typography.font else { fatalError("unexpected default") }
let bytes = try UIAppearanceDescriptorCodecV2.canonicalData(value)
guard try UIAppearanceDescriptorCodecV2.decode(bytes) == value else { fatalError("round trip") }
try bytes.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
print("default=\(value.id) mode=shared resources=0 font=systemSans bytes=\(bytes.count)")
