import Foundation
import MixerAndroidRuntime
import MixerUI
import Testing

private struct Counter: AndroidApplicationEngine {
    var value = 0
    func render() throws -> Data { Data(String(value).utf8) }
    mutating func dispatch(_ input: Data) throws -> Data { value += 1; return try render() }
}
private struct HugeOutput: AndroidApplicationEngine {
    func render() throws -> Data { Data(repeating: 0, count: 1_048_577) }
    mutating func dispatch(_ input: Data) throws -> Data { try render() }
}
private struct State: Sendable, Equatable { var value = "Initial"; var mode = 0 }
private struct Packet { let document: UIDocument; let identities: [UINodeIdentity] }

@Suite(.serialized) struct IndependentRuntimeProbe {
    private func exchange<E>(_ registry: AndroidSessionRegistry<E>, _ handle: UInt64, operation: UInt32 = 0,
                             input: Data? = nil, capacity: Int = 1_048_576) -> (Int32, Data, Int) {
        var buffer = [UInt8](repeating: 0, count: capacity), written = -1
        let status = buffer.withUnsafeMutableBufferPointer { out in
            if let input { return input.withUnsafeBytes { bytes in
                registry.exchange(handle, operation, bytes.bindMemory(to: UInt8.self).baseAddress,
                                  input.count, out.baseAddress, capacity, &written)
            } }
            return registry.exchange(handle, operation, nil, 0, out.baseAddress, capacity, &written)
        }
        return (status, Data(buffer.prefix(max(0, min(written, capacity)))), written)
    }
    private func packet(_ data: Data) throws -> Packet {
        let object = try #require(JSONSerialization.jsonObject(with: data) as? [String: Any])
        return try Packet(document: UIDocument.decode(JSONSerialization.data(withJSONObject: object["document"]!)),
                          identities: JSONDecoder().decode([UINodeIdentity].self, from: JSONSerialization.data(withJSONObject: object["identities"]!)))
    }
    private func event(_ data: Data, id: String, event: UIEventKind, value: UIValue = .null,
                       identity: UINodeIdentity? = nil) throws -> Data {
        let packet = try packet(data)
        return try JSONEncoder().encode(UIEventEnvelope(revision: packet.document.revision,
            identity: try identity ?? #require(packet.identities.first { $0.id == id }), event: event, value: value))
    }
    private func session() throws -> AndroidDocumentSession<State> {
        try AndroidDocumentSession(state: State(), document: { state, revision in
            var children = [UINode(id: "mode", kind: .button, properties: ["label": .string("Mode")],
                                  actions: [UIActionBinding(id: "mode.change", event: .activate)])]
            if state.mode != 2 {
                children.append(state.mode == 1
                    ? UINode(id: "field", kind: .toggle, properties: ["label": .string("Toggle"), "value": .bool(false)], actions: [UIActionBinding(id: "field.toggle", event: .valueChange)])
                    : UINode(id: "field", kind: .textField, properties: ["label": .string("Title"), "value": .string(state.value)], actions: [UIActionBinding(id: "field.edit", event: .textChange)]))
            }
            return UIDocument(schemaVersion: 1, revision: revision, root: UINode(id: "root", kind: .vStack, children: children))
        }, reduce: { state, action in
            if action.actionID == "mode.change" { state.mode = (state.mode + 1) % 4 }
            else if case .string(let value) = action.value {
                state.value = value
                if value == "reject after mutation" { throw AndroidDocumentError.invalidEvent }
            }
        })
    }
    @Test func smallOutputRollsBackMutatedValueEngineAndRetryCommitsOnce() throws {
        let registry = AndroidSessionRegistry { Counter() }, handle = registry.create()
        #expect(handle != 0)
        #expect(exchange(registry, handle).1 == Data("0".utf8))
        let rejected = exchange(registry, handle, operation: 1, capacity: 0)
        #expect(rejected.0 == 3); #expect(rejected.2 == 1)
        #expect(exchange(registry, handle).1 == Data("0".utf8))
        #expect(exchange(registry, handle, operation: 1).1 == Data("1".utf8))
        #expect(exchange(registry, handle).1 == Data("1".utf8))
        #expect(registry.destroy(handle) == 0)
    }
    @Test func handleBudgetStaleDestructionAndArgumentValidation() {
        let registry = AndroidSessionRegistry { Counter() }
        let handles = (0..<16).map { _ in registry.create() }
        #expect(Set(handles).count == 16); #expect(!handles.contains(0)); #expect(registry.create() == 0)
        var written = -1
        #expect(registry.exchange(handles[0], 0, nil, 1, nil, 0, &written) == 1); #expect(written == 0)
        #expect(registry.exchange(handles[0], 0, nil, -1, nil, 0, &written) == 1)
        #expect(registry.exchange(handles[0], 0, nil, 0, nil, -1, &written) == 1)
        #expect(registry.exchange(handles[0], 0, nil, 0, nil, 1_048_577, &written) == 1)
        #expect(registry.exchange(handles[0], 1, nil, 131_073, nil, 0, &written) == 1)
        #expect(registry.exchange(handles[0], 2, nil, 0, nil, 0, &written) == 1)
        #expect(registry.exchange(handles[0], 0, nil, 0, nil, 0, nil) == 1)
        #expect(registry.destroy(handles[0]) == 0); #expect(registry.destroy(handles[0]) == 2)
        #expect(exchange(registry, handles[0]).0 == 2)
        let replacement = registry.create(); #expect(replacement != 0); #expect(!handles.contains(replacement))
        for handle in handles.dropFirst() { #expect(registry.destroy(handle) == 0) }
        #expect(registry.destroy(replacement) == 0)
    }
    @Test func oversizedEngineOutputIsRejectedAtNativeBoundary() {
        let registry = AndroidSessionRegistry { HugeOutput() }, handle = registry.create()
        let result = exchange(registry, handle)
        #expect(result.0 == 4); #expect(result.2 == 0); #expect(result.1.isEmpty)
        #expect(registry.destroy(handle) == 0)
    }
    @Test func reducerFailureIdentityReplacementReinsertionAndStaleEventsAreAtomic() throws {
        var engine = try session()
        let initial = try engine.render(), original = try #require(packet(initial).identities.first { $0.id == "field" })
        #expect(throws: (any Error).self) { try engine.dispatch(event(initial, id: "field", event: .textChange, value: .string("reject after mutation"))) }
        #expect(engine.state == State()); #expect(try engine.render() == initial)
        let changed = try engine.dispatch(event(initial, id: "field", event: .textChange, value: .string("Café 東京 🧪")))
        #expect(try packet(changed).identities.first { $0.id == "field" } == original)
        let replaced = try engine.dispatch(event(changed, id: "mode", event: .activate))
        let replacement = try #require(packet(replaced).identities.first { $0.id == "field" })
        #expect(replacement.generation > original.generation)
        #expect(throws: (any Error).self) { try engine.dispatch(event(replaced, id: "field", event: .valueChange, value: .bool(true), identity: original)) }
        #expect(try engine.render() == replaced)
        #expect(throws: (any Error).self) { try engine.dispatch(event(initial, id: "field", event: .textChange, value: .string("stale"))) }
        #expect(try engine.render() == replaced)
        let removed = try engine.dispatch(event(replaced, id: "mode", event: .activate))
        #expect(try packet(removed).identities.first { $0.id == "field" } == nil)
        let reinserted = try engine.dispatch(event(removed, id: "mode", event: .activate))
        #expect(try #require(packet(reinserted).identities.first { $0.id == "field" }).generation > replacement.generation)
    }
    @Test func encodedOutputLimitRollsBackValidValueStateAndRevision() throws {
        var engine = try AndroidDocumentSession(state: 0, document: { state, revision in
            if state == 0 { return MixerUI.Button("grow", "Grow", action: "grow").document(revision: revision) }
            let text = String(repeating: "\n", count: 16_000)
            return UIDocument(schemaVersion: 1, revision: revision, root: UINode(id: "root", kind: .vStack,
                children: (0..<60).map { UINode(id: "text.\($0)", kind: .text, properties: ["text": .string(text)]) }))
        }, reduce: { state, _ in state += 1 })
        let original = try engine.render()
        do { _ = try engine.dispatch(event(original, id: "grow", event: .activate)); Issue.record("Expected encoded packet limit") }
        catch AndroidDocumentError.outputLimit { }
        catch { Issue.record("Unexpected rejection: \(error)") }
        #expect(engine.state == 0); #expect(engine.revision == 1); #expect(try engine.render() == original)
    }
    @Test func malformedJSONFieldsAndEventValuesLeaveCurrentSnapshotIntact() throws {
        var engine = try session(); let original = try engine.render()
        let good = try event(original, id: "field", event: .textChange, value: .string("safe"))
        var dictionary = try #require(JSONSerialization.jsonObject(with: good) as? [String: Any])
        dictionary["extra"] = true
        let extras = try JSONSerialization.data(withJSONObject: dictionary)
        for bad in [Data(), Data("{}".utf8), extras, Data("{\"revision\":1,\"\\u0072evision\":1}".utf8), Data(repeating: 32, count: 131_073), try event(original, id: "field", event: .textChange, value: .bool(true))] {
            #expect(throws: (any Error).self) { try engine.dispatch(bad) }
            #expect(engine.revision == 1); #expect(try engine.render() == original)
        }
    }
}
