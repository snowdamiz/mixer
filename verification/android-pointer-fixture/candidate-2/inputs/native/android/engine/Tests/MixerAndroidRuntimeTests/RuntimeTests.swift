import Foundation
import MixerUI
import Testing
@testable import MixerAndroidRuntime

struct RuntimeTests {
    struct State: Equatable, Sendable { var value = "Initial" }
    func document(_ state: State, _ revision: UInt64) -> UIDocument {
        MixerUI.TextField("field", "Title", value: state.value, action: "edit").document(revision: revision)
    }
    func session() throws -> AndroidDocumentSession<State> {
        try AndroidDocumentSession(state: State(), document: { state, revision in
            MixerUI.TextField("field", "Title", value: state.value, action: "edit").document(revision: revision)
        }, reduce: { state, action in
            guard action.actionID == "edit", case .string(let value) = action.value else { throw AndroidDocumentError.invalidEvent }
            state.value = value
            if value == "reject" { throw AndroidDocumentError.invalidEvent }
        })
    }
    func event(_ bytes: Data, value: String) throws -> Data {
        let packet = try #require(JSONSerialization.jsonObject(with: bytes) as? [String: Any])
        let doc = try UIDocument.decode(JSONSerialization.data(withJSONObject: packet["document"]!))
        let identities = try JSONDecoder().decode([UINodeIdentity].self, from: JSONSerialization.data(withJSONObject: packet["identities"]!))
        return try JSONEncoder().encode(UIEventEnvelope(revision: doc.revision, identity: #require(identities.first), event: .textChange, value: .string(value)))
    }
    @Test func candidateReductionAndRoutingAreAtomic() throws {
        var engine = try session()
        let first = try engine.render()
        #expect(throws: (any Error).self) { try engine.dispatch(event(first, value: "reject")) }
        #expect(try engine.render() == first)
        let edit = try event(first, value: "Café 東京 🧪")
        _ = try engine.dispatch(edit)
        #expect(engine.state.value == "Café 東京 🧪"); #expect(engine.revision == 2)
        let last = try engine.render()
        #expect(throws: (any Error).self) { try engine.dispatch(edit) }
        for bytes in [Data("{}".utf8), Data("{\"event\":null,\"\\u0065vent\":null}".utf8), Data(repeating: 32, count: 131_073)] {
            #expect(throws: (any Error).self) { try engine.dispatch(bytes) }
            #expect(try engine.render() == last)
        }
    }
    @Test func unsupportedAndroidSubsetFailsBeforePublishingPacket() {
        #expect(throws: (any Error).self) {
            try AndroidDocumentSession(state: State(), document: { _, revision in
                MixerUI.List("outer") { MixerUI.List("inner") {} }.document(revision: revision)
            }, reduce: { _, _ in })
        }
        #expect(throws: (any Error).self) {
            try AndroidDocumentSession(state: State(), document: { _, revision in
                UIDocument(schemaVersion: 1, revision: revision, root: UINode(id: "root", kind: .hStack, properties: ["alignment": .string("firstTextBaseline")]))
            }, reduce: { _, _ in })
        }
    }
    @Test func registryRejectsUnknownOversizedAndSmallBuffersWithoutCommitting() throws {
        let registry = AndroidSessionRegistry { try self.session() }
        let handle = registry.create(); #expect(handle != 0)
        defer { #expect(registry.destroy(handle) == 0) }
        var required = 0
        #expect(registry.exchange(handle, 0, nil, 0, nil, 0, &required) == 3)
        #expect(required > 0)
        #expect(registry.exchange(handle, 9, nil, 0, nil, 0, &required) == 1)
        #expect(required == 0)
        #expect(registry.exchange(handle, 1, nil, 131_073, nil, 0, &required) == 1)
        #expect(registry.exchange(handle, 0, nil, 0, nil, 0, nil) == 1)
        #expect(registry.exchange(0, 0, nil, 0, nil, 0, &required) == 2)
    }

    @Test func escapedPacketLimitPreservesStateRevisionAndIdentityUntilAValidUpdate() throws {
        let makeDocument: @Sendable (State, UInt64) -> UIDocument = { state, revision in
            VStack("root") {
                TextField("field", "Title", value: state.value, action: "edit")
                for index in 0..<11 {
                    Text("text.\(index)", state.value == "overflow" ? String(repeating: "\0", count: 16_384) : "")
                }
            }.document(revision: revision)
        }
        let reduce: @Sendable (inout State, RoutedUIAction) throws -> Void = { state, action in
            guard case .string(let value) = action.value else { throw AndroidDocumentError.invalidEvent }
            state.value = value
        }
        do {
            _ = try AndroidDocumentSession(state: State(value: "overflow"), document: makeDocument, reduce: reduce)
            Issue.record("Oversized initial escaped packet was accepted")
        } catch AndroidDocumentError.outputLimit { }

        var engine = try AndroidDocumentSession(state: State(), document: makeDocument, reduce: reduce)
        let first = try engine.render()
        let object = try #require(JSONSerialization.jsonObject(with: first) as? [String: Any])
        let identities = try JSONDecoder().decode([UINodeIdentity].self,
            from: JSONSerialization.data(withJSONObject: #require(object["identities"])))
        let identity = try #require(identities.first { $0.id == "field" })
        let rejected = try JSONEncoder().encode(UIEventEnvelope(revision: 1, identity: identity,
            event: .textChange, value: .string("overflow")))
        do {
            _ = try engine.dispatch(rejected)
            Issue.record("Oversized update escaped packet was accepted")
        } catch AndroidDocumentError.outputLimit { }
        #expect(engine.state == State())
        #expect(engine.revision == 1)
        #expect(try engine.render() == first)
        let accepted = try JSONEncoder().encode(UIEventEnvelope(revision: 1, identity: identity,
            event: .textChange, value: .string("é\0漢字🏗️")))
        let second = try engine.dispatch(accepted)
        #expect(engine.state.value == "é\0漢字🏗️" && engine.revision == 2)
        let secondObject = try #require(JSONSerialization.jsonObject(with: second) as? [String: Any])
        let secondIdentities = try JSONDecoder().decode([UINodeIdentity].self,
            from: JSONSerialization.data(withJSONObject: #require(secondObject["identities"])))
        #expect(secondIdentities.first { $0.id == "field" } == identity)
    }
}
