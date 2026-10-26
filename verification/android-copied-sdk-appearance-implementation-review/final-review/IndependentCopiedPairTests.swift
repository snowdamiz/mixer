import Foundation
import Testing
@testable import MixerUI
@_spi(MixerNativeAppearanceV2) import MixerAndroidRuntime
@_spi(MixerNativeAppearanceV2) @testable import AppAndroid

@Suite(.serialized) struct IndependentCopiedPairTests {
    let output = URL(fileURLWithPath: ProcessInfo.processInfo.environment["MIXER_REVIEW_OUTPUT"]!)
    func write(_ name: String, _ bytes: Data) throws { try bytes.write(to: output.appendingPathComponent(name)) }
    func reject(_ body: () throws -> Void) {
        do { try body(); Issue.record("Expected actual copied API refusal") } catch {}
    }
    func exchange(_ handle: UInt64, _ input: Data? = nil) -> (Int32, Data) {
        var buffer = [UInt8](repeating: 0, count: 1_048_576), count = 0
        let status = buffer.withUnsafeMutableBufferPointer { target in
            if let input { return input.withUnsafeBytes { source in
                mixerAndroidExchange(handle, 1, source.bindMemory(to: UInt8.self).baseAddress,
                    source.count, target.baseAddress, target.count, &count)
            } }
            return mixerAndroidExchange(handle, 0, nil, 0, target.baseAddress, target.count, &count)
        }
        return (status, Data(buffer.prefix(min(count, buffer.count))))
    }
    func event(_ packet: Data, value: String) throws -> Data {
        let raw = try #require(JSONSerialization.jsonObject(with: packet) as? [String: Any])
        let document = try UIDocument.decode(JSONSerialization.data(withJSONObject: raw["document"]!))
        let identities = try JSONDecoder().decode([UINodeIdentity].self, from: JSONSerialization.data(withJSONObject: raw["identities"]!))
        return try JSONEncoder().encode(UIEventEnvelope(revision: document.revision,
            identity: #require(identities.first { $0.id == "draft" }), event: .textChange, value: .string(value)))
    }
    @Test func canonicalDefaultAndClosedDecode() throws {
        let value = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
        let bytes = try UIAppearanceDescriptorCodecV2.canonicalData(value)
        let asset = try Data(contentsOf: URL(fileURLWithPath: ProcessInfo.processInfo.environment["MIXER_REVIEW_ASSET"]!))
        #expect(bytes == asset)
        #expect(try UIAppearanceDescriptorCodecV2.canonicalData(UIAppearanceDescriptorCodecV2.decode(bytes)) == bytes)
        #expect(value.resources.isEmpty)
        try write("descriptor.json", bytes)
        for invalid in [Data("{}".utf8), bytes + Data([10]), Data(String(decoding: bytes, as: UTF8.self).replacingOccurrences(of: "mixer.native-appearance.2", with: "mixer.native-appearance.9").utf8)] {
            reject { _ = try UIAppearanceDescriptorCodecV2.decode(invalid) }
        }
    }
    @Test func actualApplicationWireAndStagedOutcomes() throws {
        let handle = mixerAndroidCreate(); #expect(handle != 0)
        let other = mixerAndroidCreate(); #expect(other != 0)
        defer { #expect(mixerAndroidDestroy(handle) == 0); #expect(mixerAndroidDestroy(other) == 0) }
        let initial = exchange(handle); #expect(initial.0 == 0); try write("app-initial.json", initial.1)
        let edit = try event(initial.1, value: "Independent café 東京 🧪")
        var buffer = [UInt8](repeating: 0, count: 1_048_576), written = 0, token: UInt64 = 0
        let prepared = buffer.withUnsafeMutableBufferPointer { out in edit.withUnsafeBytes { input in
            mixerAndroidPrepareV2(handle, 1, input.bindMemory(to: UInt8.self).baseAddress,
                input.count, out.baseAddress, out.count, &written, &token)
        } }
        #expect(prepared == 0); #expect(token != 0); #expect(exchange(handle).0 == 5)
        #expect(mixerAndroidCommitV2(other, token) == 6)
        #expect(mixerAndroidAbortV2(handle, token) == 0)
        #expect(mixerAndroidAbortV2(handle, token) == 0)
        #expect(exchange(handle).1 == initial.1)
        var nextToken: UInt64 = 0
        let second = buffer.withUnsafeMutableBufferPointer { out in edit.withUnsafeBytes { input in
            mixerAndroidPrepareV2(handle, 1, input.bindMemory(to: UInt8.self).baseAddress,
                input.count, out.baseAddress, out.count, &written, &nextToken)
        } }
        #expect(second == 0); #expect(nextToken != token)
        let candidate = Data(buffer.prefix(written));try write("app-successor.json", candidate)
        #expect(mixerAndroidCommitV2(handle, nextToken) == 0)
        #expect(mixerAndroidCommitV2(handle, nextToken) == 6)
        #expect(exchange(handle).1 == candidate)
        #expect(exchange(handle, edit).0 == 4)
        for bad in [Data("{}".utf8), Data("{\"revision\":1,\"revision\":2}".utf8)] {
            #expect(exchange(handle, bad).0 == 4); #expect(exchange(handle).1 == candidate)
        }
        #expect(exchange(handle, Data(repeating:32,count:131_073)).0 == 1)
        #expect(exchange(handle).1 == candidate)
    }
    @Test func fullUInt64WriterAndRouting() throws {
        let node = UINode(id:"full",kind:.button,properties:["label":.string("Wire café 東京")],actions:[UIActionBinding(id:"activate",event:.activate)])
        let identity = UINodeIdentity(id:"full",generation:UInt64.max)
        func snapshot(_ revision: UInt64) -> UIRenderSnapshot {
            UIRenderSnapshot(document:UIDocument(revision:revision,root:node),
                nodes:["full":ReconciledNode(node:node,identity:identity,parent:nil,index:0,disabled:false)],maximumStringBytes:16_384)
        }
        let previous=snapshot(UInt64.max-1),next=snapshot(UInt64.max)
        let a=try previous.encodeNativePacketV1(),b=try next.encodeNativePacketV1()
        #expect(String(decoding:b,as:UTF8.self).contains("18446744073709551615"))
        #expect(try next.route(UIEventEnvelope(revision:UInt64.max,identity:identity,event:.activate)).actionID == "activate")
        reject { _ = try next.route(UIEventEnvelope(revision:9_007_199_254_740_993,identity:identity,event:.activate)) }
        reject { _ = try next.route(UIEventEnvelope(revision:UInt64.max,identity:UINodeIdentity(id:"full",generation:UInt64.max-1),event:.activate)) }
        try write("full-previous.json",a);try write("full-next.json",b)
        let missing=UIRenderSnapshot(document:next.document,nodes:[:],maximumStringBytes:16_384)
        reject { _ = try missing.encodeNativePacketV1() }
        let unsupported=Data("{\"schemaVersion\":2,\"revision\":1,\"root\":{}}".utf8)
        reject { _ = try UIDocument.decode(unsupported) }
        reject { _ = try UIDocument.decode(Data("{\"schemaVersion\":1,\"schemaVersion\":1}".utf8)) }
    }
    @Test func reducerFailurePreservesActualSession() throws {
        enum Denied: Error { case no }
        var session = try AndroidDocumentSession(state:0,document:{ _, revision in
            UIDocument(revision:revision,root:UINode(id:"deny",kind:.button,properties:["label":.string("Reject")],actions:[UIActionBinding(id:"deny",event:.activate)]))
        },reduce:{ state,_ in state += 1;throw Denied.no })
        let initial=try session.render()
        let input=try JSONEncoder().encode(UIEventEnvelope(revision:1,identity:UINodeIdentity(id:"deny",generation:1),event:.activate))
        reject { _ = try session.dispatch(input) }
        #expect(session.state == 0);#expect(session.revision == 1);#expect(try session.render() == initial)
    }
}
