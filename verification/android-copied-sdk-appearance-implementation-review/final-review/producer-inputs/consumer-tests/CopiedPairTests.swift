import Foundation
import Testing
@testable import MixerUI
@_spi(MixerNativeAppearanceV2) @testable import AppAndroid

private let output = URL(fileURLWithPath: "/tmp/mixer-source-pair-consumer-20261026/qualification-output")
private func fullSnapshot() throws -> UIRenderSnapshot {
    let document = MixerUI.VStack("root") {
        MixerUI.Text("caption", "Café 東京 🧪")
        MixerUI.TextField("draft", "Draft", value: "", action: "draft.change")
    }.document(revision: UInt64.max)
    var reconciler = UIReconciler(); try reconciler.apply(document)
    let ordinary = try reconciler.currentSnapshot()
    var records: [String: ReconciledNode] = [:]
    for (index, id) in ordinary.nodes.keys.sorted().enumerated() {
        let node = ordinary.nodes[id]!
        records[id] = ReconciledNode(node: node.node, identity: UINodeIdentity(id: id, generation: UInt64.max - UInt64(index)), parent: node.parent, index: node.index, disabled: node.disabled)
    }
    // Internal construction supplies otherwise unreachable exhaustion-edge values
    // to the actual production writer. This is not a public snapshot constructor.
    return UIRenderSnapshot(document: document, nodes: records, maximumStringBytes: 16_384)
}
@Test func copiedPairProducesActualDefaultAndPacketOutputsAndRejectsSchemas() throws {
    try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
    let asset = try Data(contentsOf: output.deletingLastPathComponent().appendingPathComponent("Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json"))
    let value = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
    let canonical = try UIAppearanceDescriptorCodecV2.canonicalData(value)
    #expect(asset == canonical); #expect(try UIAppearanceDescriptorCodecV2.decode(asset) == value)
    try canonical.write(to: output.appendingPathComponent("swift-descriptor.json"))
    for bytes in [Data("{}".utf8), Data(String(decoding: asset, as: UTF8.self).replacingOccurrences(of: "mixer.native-appearance.2", with: "mixer.native-appearance.9").utf8), Data("{\"format\":1,\"format\":1}\n".utf8)] {
        #expect(throws: (any Error).self) { try UIAppearanceDescriptorCodecV2.decode(bytes) }
    }
    var reconciler = UIReconciler()
    let document = MixerUI.VStack("root") { MixerUI.Text("caption", "Café 東京 🧪"); MixerUI.TextField("draft", "Draft", value: "", action: "draft.change") }.document(revision: 1)
    try reconciler.apply(document)
    let initial = try reconciler.currentSnapshot()
    try initial.encodeNativePacketV1().write(to: output.appendingPathComponent("swift-packet-1.json"))
    let id = try #require(initial.identity(for: "draft"))
    #expect(try initial.route(UIEventEnvelope(revision: 1, identity: id, event: .textChange, value: .string("text"))).actionID == "draft.change")
    #expect(throws: UIRoutingError.self) { try initial.route(UIEventEnvelope(revision: 0, identity: id, event: .textChange, value: .string("text"))) }
    #expect(throws: UIRoutingError.self) { try initial.route(UIEventEnvelope(revision: 1, identity: UINodeIdentity(id: "draft", generation: UInt64.max), event: .textChange, value: .string("text"))) }
    #expect(throws: UIReconciliationError.self) { try reconciler.apply(document) }
    let next = UIDocument(revision: 2, root: document.root); try reconciler.apply(next)
    let second = try reconciler.currentSnapshot()
    #expect(second.identity(for: "draft") == id)
    try second.encodeNativePacketV1().write(to: output.appendingPathComponent("swift-packet-2.json"))
    for bytes in [Data("{}".utf8), Data("{\"schemaVersion\":1,\"schemaVersion\":1}".utf8), Data(String(decoding: try UIValidator().encode(document), as: UTF8.self).replacingOccurrences(of: "\"schemaVersion\":1", with: "\"schemaVersion\":9").utf8)] {
        #expect(throws: (any Error).self) { try UIDocument.decode(bytes) }
    }
    let full = try fullSnapshot()
    let fullBytes = try full.encodeNativePacketV1()
    #expect(String(decoding: fullBytes, as: UTF8.self).contains("18446744073709551615"))
    #expect(try UIDocument.decode(UIValidator().encode(full.document)).revision == UInt64.max)
    try fullBytes.write(to: output.appendingPathComponent("swift-packet-uint64.json"))
    let handle = mixerAndroidCreate(); #expect(handle != 0)
    defer { #expect(mixerAndroidDestroy(handle) == 0) }
    var buffer = [UInt8](repeating: 0, count: 1_048_576), written = 0
    let status = buffer.withUnsafeMutableBufferPointer { mixerAndroidExchange(handle, 0, nil, 0, $0.baseAddress, $0.count, &written) }
    #expect(status == 0)
    try Data(buffer.prefix(written)).write(to: output.appendingPathComponent("swift-app-session-packet.json"))
}

@Test func copiedPairConsumesActualJavaFullUInt64Event() throws {
    let bytes = try Data(contentsOf: output.appendingPathComponent("java-event-uint64.json"))
    let event = try JSONDecoder().decode(UIEventEnvelope.self, from: bytes)
    let snapshot = try fullSnapshot()
    #expect(event.revision == UInt64.max)
    #expect(event.identity.generation == snapshot.identity(for: "draft")?.generation)
    let action = try snapshot.route(event)
    #expect(action.actionID == "draft.change"); #expect(action.value == .string("Java café 東京"))
    try Data("Swift consumed Java full UInt64 event\n".utf8).write(to: output.appendingPathComponent("swift-java-event-pass.txt"))
}
