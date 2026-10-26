import Foundation
import Testing
import MixerUI
@_spi(MixerNativeAppearanceV2) @testable import AppAndroid
@Suite(.serialized) struct ApplicationSessionTests {
    func exchange(_ handle: UInt64, _ input: Data? = nil, capacity: Int = 1_048_576) -> (Int32, Data) {
        var buffer = [UInt8](repeating: 0, count: capacity), written = 0
        let status = buffer.withUnsafeMutableBufferPointer { output in
            if let input { return input.withUnsafeBytes { bytes in
                mixerAndroidExchange(handle, 1, bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count, output.baseAddress, capacity, &written)
            } }
            return mixerAndroidExchange(handle, 0, nil, 0, output.baseAddress, capacity, &written)
        }
        return (status, Data(buffer.prefix(min(written, capacity))))
    }
    func event(_ packet: Data, id: String, kind: UIEventKind, value: UIValue) throws -> Data {
        let object = try #require(JSONSerialization.jsonObject(with: packet) as? [String: Any])
        let document = try UIDocument.decode(JSONSerialization.data(withJSONObject: object["document"]!))
        let identities = try JSONDecoder().decode([UINodeIdentity].self, from: JSONSerialization.data(withJSONObject: object["identities"]!))
        return try JSONEncoder().encode(UIEventEnvelope(revision: document.revision,
            identity: #require(identities.first { $0.id == id }), event: kind, value: value))
    }
    @Test func sharedDraftAddToggleAndRejectedTransactions() throws {
        let handle = mixerAndroidCreate(); #expect(handle != 0)
        defer { #expect(mixerAndroidDestroy(handle) == 0) }
        let initial = exchange(handle); #expect(initial.0 == 0)
        let edit = try event(initial.1, id: "draft", kind: .textChange, value: .string("Café 東京 🧪"))
        #expect(exchange(handle, edit, capacity: 1).0 == 3)
        #expect(exchange(handle).1 == initial.1)
        let draft = exchange(handle, edit); #expect(draft.0 == 0)
        #expect(exchange(handle, edit).0 == 4)
        let added = exchange(handle, try event(draft.1, id: "add", kind: .activate, value: .null))
        #expect(added.0 == 0)
        let object = try #require(JSONSerialization.jsonObject(with: added.1) as? [String: Any])
        let identities = try JSONDecoder().decode([UINodeIdentity].self, from: JSONSerialization.data(withJSONObject: object["identities"]!))
        let task = try #require(identities.first { $0.id.hasPrefix("entry.") })
        let toggled = exchange(handle, try event(added.1, id: task.id, kind: .valueChange, value: .bool(true)))
        #expect(toggled.0 == 0)
        #expect(String(decoding: toggled.1, as: UTF8.self).contains("1 of 1 completed"))
        for bad in [Data("{}".utf8), Data("{\"event\":null,\"\\u0065vent\":null}".utf8), Data(repeating: 32, count: 131_073)] {
            #expect(exchange(handle, bad).0 != 0)
            #expect(exchange(handle).1 == toggled.1)
        }
    }
    @Test func stagedDecisionsPreserveCommittedState() throws {
        let handle = mixerAndroidCreate(); #expect(handle != 0)
        defer { #expect(mixerAndroidDestroy(handle) == 0) }
        let initial = exchange(handle); #expect(initial.0 == 0)
        let edit = try event(initial.1, id: "draft", kind: .textChange, value: .string("Staged café 東京"))
        func prepare() -> (Int32, Data, UInt64) {
            var buffer = [UInt8](repeating: 0, count: 1_048_576), written = 0
            var token: UInt64 = 0
            let status = buffer.withUnsafeMutableBufferPointer { output in
                edit.withUnsafeBytes { input in
                    mixerAndroidPrepareV2(handle, 1, input.bindMemory(to: UInt8.self).baseAddress,
                        input.count, output.baseAddress, output.count, &written, &token)
                }
            }
            return (status, Data(buffer.prefix(min(written, buffer.count))), token)
        }
        let aborted = prepare(); #expect(aborted.0 == 0); #expect(aborted.2 != 0)
        #expect(exchange(handle).0 == 5)
        #expect(mixerAndroidAbortV2(handle, aborted.2) == 0)
        #expect(mixerAndroidAbortV2(handle, aborted.2) == 0)
        #expect(exchange(handle).1 == initial.1)
        let committed = prepare(); #expect(committed.0 == 0); #expect(committed.2 != aborted.2)
        #expect(mixerAndroidAbortV2(handle, aborted.2) == 0)
        #expect(exchange(handle).0 == 5)
        #expect(mixerAndroidCommitV2(handle, committed.2) == 0)
        #expect(mixerAndroidCommitV2(handle, committed.2) == 6)
        #expect(exchange(handle).1 == committed.1)
        #expect(String(decoding: committed.1, as: UTF8.self).contains("Staged café 東京"))
    }
    @Test func boundedHandlesAndDestruction() {
        let handles = (0..<16).map { _ in mixerAndroidCreate() }
        #expect(handles.allSatisfy { $0 != 0 }); #expect(Set(handles).count == 16)
        #expect(mixerAndroidCreate() == 0)
        for handle in handles { #expect(mixerAndroidDestroy(handle) == 0); #expect(mixerAndroidDestroy(handle) == 2) }
        #expect(exchange(handles[0]).0 == 2)
    }
}
