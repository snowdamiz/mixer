import Foundation
import MixerUI
while let line=readLine() {
    guard let bytes=Data(base64Encoded:line) else { fatalError("invalid fixture") }
    do {
        let value=try UIAppearanceDescriptorCodecV2.decode(bytes)
        try UIAppearanceDescriptorCodecV2.validate(value)
        let output=try UIAppearanceDescriptorCodecV2.canonicalData(value)
        print(output == bytes ? "accept" : "roundtripMismatch")
    } catch { print("reject") }
}
