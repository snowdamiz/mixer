import Foundation
import Testing
import MixerUI
@_spi(MixerNativeAppearanceV2) @testable import AppAndroid

@Suite(.serialized) struct IndependentReviewTests {
    func exchange(_ handle: UInt64, _ input: Data? = nil) -> (Int32, Data) {
        var bytes = [UInt8](repeating: 0, count: 1_048_576), written = 0
        let status = bytes.withUnsafeMutableBufferPointer { out in
            if let input { return input.withUnsafeBytes { value in
                mixerAndroidExchange(handle, 1, value.bindMemory(to: UInt8.self).baseAddress, value.count, out.baseAddress, out.count, &written)
            } }
            return mixerAndroidExchange(handle, 0, nil, 0, out.baseAddress, out.count, &written)
        }
        return (status, Data(bytes.prefix(written)))
    }
    func decoded(_ packet: Data) throws -> (UIDocument, [UINodeIdentity]) {
        let object = try #require(JSONSerialization.jsonObject(with: packet) as? [String: Any])
        return (try UIDocument.decode(JSONSerialization.data(withJSONObject: object["document"]!)),
                try JSONDecoder().decode([UINodeIdentity].self, from: JSONSerialization.data(withJSONObject: object["identities"]!)))
    }
    func draft(_ packet: Data) throws -> UIValue? {
        func find(_ node: UINode) -> UINode? {
            if node.id == "draft" { return node }
            return node.children.compactMap(find).first
        }
        return try find(decoded(packet).0.root)?.properties["value"]
    }
    func edit(_ packet: Data, _ value: String) throws -> Data {
        let (doc, identities) = try decoded(packet)
        return try JSONEncoder().encode(UIEventEnvelope(revision: doc.revision,
            identity: #require(identities.first { $0.id == "draft" }), event: .textChange, value: .string(value)))
    }
    @Test func appOwnedFactorySeedsTypedDocument() throws {
        let handle = mixerAndroidCreate(); #expect(handle != 0)
        defer { #expect(mixerAndroidDestroy(handle) == 0) }
        let initial = exchange(handle)
        #expect(initial.0 == 0)
        #expect(try decoded(initial.1).0.revision == 1)
        #expect(try draft(initial.1) == .string("Independent factory seed"))
    }
    @Test func copiedReducerCommitsAndStaleReplayPreservesState() throws {
        let handle = mixerAndroidCreate(); #expect(handle != 0)
        defer { #expect(mixerAndroidDestroy(handle) == 0) }
        let initial = exchange(handle)
        let event = try edit(initial.1, "Café 東京")
        let updated = exchange(handle, event)
        #expect(updated.0 == 0)
        #expect(try decoded(updated.1).0.revision == 2)
        #expect(try draft(updated.1) == .string("review:Café 東京"))
        #expect(exchange(handle, event).0 == 4)
        #expect(exchange(handle).1 == updated.1)
    }
    @Test func separateHandlesOwnSeparateFactoryState() throws {
        let one = mixerAndroidCreate(), two = mixerAndroidCreate()
        #expect(one != 0 && two != 0 && one != two)
        defer { #expect(mixerAndroidDestroy(one) == 0); #expect(mixerAndroidDestroy(two) == 0) }
        let first = exchange(one), second = exchange(two)
        #expect(exchange(one, try edit(first.1, "only first")).0 == 0)
        #expect(exchange(two).1 == second.1)
        #expect(try draft(exchange(two).1) == .string("Independent factory seed"))
    }
}
