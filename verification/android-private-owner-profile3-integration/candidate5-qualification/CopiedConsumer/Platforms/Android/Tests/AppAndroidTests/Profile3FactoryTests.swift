import Foundation
import Testing
import MixerUI
@_spi(MixerNativeAppearanceV2) @testable import AppAndroid
@Test func profile3CopiedFactoryReducer() throws {
    let helper = ApplicationSessionTests()
    let handle = mixerAndroidCreate(); #expect(handle != 0)
    defer { #expect(mixerAndroidDestroy(handle) == 0) }
    let initial = helper.exchange(handle); #expect(initial.0 == 0)
    #expect(String(decoding: initial.1, as: UTF8.self).contains("Selected owner factory seed"))
    let event = try helper.event(initial.1, id: "draft", kind: .textChange, value: .string("selected lower"))
    let changed = helper.exchange(handle, event); #expect(changed.0 == 0)
    #expect(String(decoding: changed.1, as: UTF8.self).contains("SELECTED LOWER"))
    func revision(_ data: Data) throws -> UInt64 {
        let object = try #require(JSONSerialization.jsonObject(with: data) as? [String: Any])
        return try UIDocument.decode(JSONSerialization.data(withJSONObject: object["document"]!)).revision
    }
    #expect(try revision(initial.1) == 1); #expect(try revision(changed.1) == 2)
}
