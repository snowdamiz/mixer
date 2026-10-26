import Foundation
import Testing
import MixerUI

// New independent consumer of the exported SDK and the actual generated asset.
private func exportedDescriptor() throws -> Data {
    try Data(contentsOf: #require(Bundle.module.url(forResource: "descriptor", withExtension: "json")))
}

@Test func independentExportedAssetMatchesLinkedTypedDefault() throws {
    let bytes = try exportedDescriptor()
    let typed = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
    #expect(bytes.count == 9587)
    #expect(try UIAppearanceDescriptorCodecV2.canonicalData(typed) == bytes)
    #expect(try UIAppearanceDescriptorCodecV2.decode(bytes) == typed)
    #expect(typed.resources.isEmpty)
    guard case .shared(let theme) = typed.mode else {
        Issue.record("Generated asset must retain the selected shared mode")
        return
    }
    #expect(theme.typography.font == .systemSans)
}

@Test func independentExportedDefaultRemainsV2AndCanonical() throws {
    let bytes = try exportedDescriptor()
    #expect(throws: UIAppearanceErrorV1.self) { _ = try UIAppearanceDescriptorCodecV1.decode(bytes) }
    for altered in [bytes + Data([10]), Data(bytes.dropLast()), Data([32]) + bytes] {
        #expect(throws: UIAppearanceErrorV2.self) { _ = try UIAppearanceDescriptorCodecV2.decode(altered) }
    }
    #expect(try UIAppearanceDescriptorCodecV2.canonicalData(UIAppearanceDescriptorCodecV2.decode(bytes)) == bytes)
}

@Test func independentCopiedDefaultIsDeterministicAcrossProductions() throws {
    let expected = try exportedDescriptor()
    for _ in 0..<4 {
        let first = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
        let second = try UIAppearanceDescriptorCodecV2.decode(UIAppearanceDescriptorCodecV2.canonicalData(first))
        #expect(try UIAppearanceDescriptorCodecV2.canonicalData(second) == expected)
    }
}
