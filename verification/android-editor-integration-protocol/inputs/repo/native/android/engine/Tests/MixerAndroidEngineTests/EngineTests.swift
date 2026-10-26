import Foundation
import MixerUI
import Testing

@testable import MixerAndroidEngine

@Suite(.serialized) struct AndroidEngineTests {
  func packet(_ data: Data) throws -> RenderPacket {
    let object = try #require(try JSONSerialization.jsonObject(with: data) as? [String: Any])
    let document = try UIValidator().decode(
      JSONSerialization.data(withJSONObject: object["document"]!)
    ).document
    let identities = try JSONDecoder().decode(
      [UINodeIdentity].self, from: JSONSerialization.data(withJSONObject: object["identities"]!))
    return RenderPacket(schemaVersion: 1, document: document, identities: identities)
  }
  func event(_ packet: RenderPacket, id: String, kind: UIEventKind, value: UIValue) throws -> Data {
    let identity = try #require(packet.identities.first { $0.id == id })
    return try JSONEncoder().encode(
      UIEventEnvelope(
        revision: packet.document.revision, identity: identity, event: kind, value: value))
  }
  @Test func modelOwnsEditsInsertionAndStableIdentity() throws {
    var engine = try ChecklistEngine()
    let initial = try packet(engine.render())
    let changed = try packet(
      engine.dispatch(event(initial, id: "title", kind: .textChange, value: .string("Café 東京 🧪"))))
    #expect(engine.state.title == "Café 東京 🧪")
    #expect(changed.document.revision == 2)
    let draft = try packet(
      engine.dispatch(event(changed, id: "draft", kind: .textChange, value: .string("New task"))))
    let added = try packet(engine.dispatch(event(draft, id: "add", kind: .activate, value: .null)))
    #expect(engine.state.tasks.count == 3)
    #expect(engine.state.draft.isEmpty)
    let toggled = try packet(
      engine.dispatch(event(added, id: "task.1", kind: .valueChange, value: .bool(true))))
    let reversed = try packet(
      engine.dispatch(event(toggled, id: "reverse", kind: .activate, value: .null)))
    #expect(engine.state.tasks.first?.id == 3)
    #expect(engine.state.tasks.last?.done == true)
    #expect(
      initial.identities.first { $0.id == "task.1" }
        == reversed.identities.first { $0.id == "task.1" })
  }
  @Test func staleAndMismatchedEventsLeaveStateUntouched() throws {
    var engine = try ChecklistEngine()
    let first = try packet(engine.render())
    _ = try engine.dispatch(event(first, id: "title", kind: .textChange, value: .string("Updated")))
    let state = engine.state
    let rendered = try engine.render()
    #expect(throws: (any Error).self) {
      try engine.dispatch(event(first, id: "title", kind: .textChange, value: .string("stale")))
    }
    let current = try packet(rendered)
    #expect(throws: (any Error).self) {
      try engine.dispatch(event(current, id: "task.1", kind: .valueChange, value: .string("wrong")))
    }
    #expect(throws: (any Error).self) {
      try engine.dispatch(event(current, id: "add", kind: .activate, value: .null))
    }
    #expect(engine.state == state)
    #expect(try engine.render() == rendered)
  }
  @Test func strictWireBoundsAndDuplicateKeys() throws {
    var engine = try ChecklistEngine()
    for wire in [
      "{}", "{\"event\":\"activate\",\"event\":\"activate\"}",
      "{\"event\":null,\"\\u0065vent\":null}", "{\"unknown\":true}",
      String(repeating: "[", count: 200),
    ] {
      #expect(throws: (any Error).self) { try engine.dispatch(Data(wire.utf8)) }
    }
    #expect(throws: (any Error).self) { try engine.dispatch(Data(repeating: 32, count: 131_073)) }
    #expect(engine.revision == 1)
  }
  @Test func cAbiOutputOwnershipAndTransactionalCapacity() throws {
    let handle = mixerAndroidCreate()
    #expect(handle != 0)
    defer { _ = mixerAndroidDestroy(handle) }
    var required = 0
    #expect(mixerAndroidExchange(handle, 0, nil, 0, nil, 0, &required) == 3)
    #expect(required > 0)
    var output = [UInt8](repeating: 0, count: 1_048_576)
    var written = 0
    let status = output.withUnsafeMutableBufferPointer {
      mixerAndroidExchange(handle, 0, nil, 0, $0.baseAddress, $0.count, &written)
    }
    #expect(status == 0)
    let first = try packet(Data(output.prefix(written)))
    let edit = try event(first, id: "title", kind: .textChange, value: .string("Should not commit"))
    let tooSmall = edit.withUnsafeBytes { bytes in
      mixerAndroidExchange(
        handle, 1, bytes.bindMemory(to: UInt8.self).baseAddress, bytes.count, nil, 0, &required)
    }
    #expect(tooSmall == 3)
    _ = output.withUnsafeMutableBufferPointer {
      mixerAndroidExchange(handle, 0, nil, 0, $0.baseAddress, $0.count, &written)
    }
    #expect(try packet(Data(output.prefix(written))).document.revision == 1)
    #expect(mixerAndroidExchange(handle, 0, nil, 1, nil, 0, &required) == 1)
    #expect(mixerAndroidExchange(handle, 0, nil, 0, nil, 0, nil) == 1)
  }
  @Test func sessionBoundAndClosedHandles() {
    let handles = (0..<16).map { _ in mixerAndroidCreate() }
    #expect(handles.allSatisfy { $0 != 0 })
    #expect(Set(handles).count == 16)
    #expect(mixerAndroidCreate() == 0)
    for handle in handles {
      #expect(mixerAndroidDestroy(handle) == 0)
      #expect(mixerAndroidDestroy(handle) == 2)
    }
    var written = 99
    #expect(mixerAndroidExchange(handles[0], 0, nil, 0, nil, 0, &written) == 2)
    #expect(written == 0)
    let fresh = mixerAndroidCreate()
    #expect(!handles.contains(fresh))
    #expect(mixerAndroidDestroy(fresh) == 0)
  }
}
