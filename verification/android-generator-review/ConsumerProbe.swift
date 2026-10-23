import Foundation
import MixerUI
import Testing
@testable import AppAndroid

@Suite(.serialized) struct IndependentConsumerProbe {
    func exchange(_ handle: UInt64, _ input: Data? = nil, capacity: Int = 1_048_576) -> (Int32, Data) {
        var buffer = [UInt8](repeating: 0, count: capacity), written = 0
        let status = buffer.withUnsafeMutableBufferPointer { output in
            if let input { return input.withUnsafeBytes { bytes in
                mixerAndroidExchange(handle, 1, bytes.bindMemory(to: UInt8.self).baseAddress, input.count, output.baseAddress, capacity, &written)
            } }
            return mixerAndroidExchange(handle, 0, nil, 0, output.baseAddress, capacity, &written)
        }
        return (status, Data(buffer.prefix(min(written, capacity))))
    }
    func event(_ packet: Data, _ id: String, _ kind: UIEventKind, _ value: UIValue) throws -> Data {
        let object = try #require(JSONSerialization.jsonObject(with: packet) as? [String: Any])
        let document = try UIDocument.decode(JSONSerialization.data(withJSONObject: object["document"]!))
        let identities = try JSONDecoder().decode([UINodeIdentity].self, from: JSONSerialization.data(withJSONObject: object["identities"]!))
        return try JSONEncoder().encode(UIEventEnvelope(revision: document.revision, identity: #require(identities.first { $0.id == id }), event: kind, value: value))
    }
    @Test func actualSharedReducerRejectsDisabledAddAndRollsBackSmallBufferAndEntryLimit() throws {
        let handle = mixerAndroidCreate(); #expect(handle != 0)
        defer { #expect(mixerAndroidDestroy(handle) == 0) }
        var current = exchange(handle).1
        let disabled = try event(current, "add", .activate, .null)
        #expect(exchange(handle, disabled).0 == 4); #expect(exchange(handle).1 == current)
        current = exchange(handle, try event(current, "draft", .textChange, .string("  Café 東京 🧪  "))).1
        let add = try event(current, "add", .activate, .null)
        #expect(exchange(handle, add, capacity: 1).0 == 3); #expect(exchange(handle).1 == current)
        current = exchange(handle, add).1
        #expect(String(decoding: current, as: UTF8.self).contains("Café 東京 🧪"))
        #expect(String(decoding: current, as: UTF8.self).contains("0 of 1 completed"))
        for index in 1..<100 {
            current = exchange(handle, try event(current, "draft", .textChange, .string("Entry \(index)"))).1
            let result = exchange(handle, try event(current, "add", .activate, .null)); #expect(result.0 == 0)
            current = result.1
        }
        #expect(String(decoding: current, as: UTF8.self).contains("0 of 100 completed"))
        current = exchange(handle, try event(current, "draft", .textChange, .string("Entry beyond supported budget"))).1
        #expect(exchange(handle, try event(current, "add", .activate, .null)).0 == 4)
        #expect(exchange(handle).1 == current)
    }
}
