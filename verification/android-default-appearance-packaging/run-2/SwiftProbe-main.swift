import Foundation
import MixerUI
let bytes = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
let value = try UIAppearanceDescriptorCodecV2.decode(bytes)
let selectedDefault = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
let canonical = try UIAppearanceDescriptorCodecV2.canonicalData(value)
guard value == selectedDefault, canonical == bytes, value.resources.isEmpty,
      case let .shared(theme) = value.mode, theme.typography.font == .systemSans else { fatalError("shape/default/bytes") }
print("production Swift codec accepted selected SDK observed default equality; bytes=\(bytes.count); id=\(value.id)")
