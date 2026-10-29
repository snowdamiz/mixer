import Foundation
import MixerUI
import XCTest
@testable import MixerAndroidRuntime

/// Source-only obligations for the isolated DocumentSession candidate.
/// Compile this file in MixerAndroidRuntimeTests with the exact candidate replacing
/// DocumentSession.swift. No test in this file has been executed in this lane.
final class AndroidTextFieldAxisRefusalTests: XCTestCase {
    private struct State: Equatable, Sendable {
        var value = "Initial"
        var emitRawHorizontal = false
    }

    private static func typedDocument(_ state: State, revision: UInt64,
                                      explicitHorizontal: Bool) -> UIDocument {
        if explicitHorizontal {
            return TextField("field", "Title", value: state.value, action: "edit",
                             onSubmit: "save", axis: .horizontal).document(revision: revision)
        }
        return TextField("field", "Title", value: state.value, action: "edit",
                         onSubmit: "save").document(revision: revision)
    }

    private static func rawField(axis: UIValue, value: String = "Initial") -> UINode {
        UINode(id: "field", kind: .textField,
               properties: ["label": .string("Title"), "value": .string(value), "axis": axis],
               actions: [UIActionBinding(id: "edit", event: .textChange)])
    }

    private static func typedSession(explicitHorizontal: Bool) throws -> AndroidDocumentSession<State> {
        try AndroidDocumentSession(state: State(), document: { state, revision in
            Self.typedDocument(state, revision: revision, explicitHorizontal: explicitHorizontal)
        }, reduce: { state, action in
            guard action.actionID == "edit", case .string(let value) = action.value else {
                throw AndroidDocumentError.invalidEvent
            }
            state.value = value
        })
    }

    private static func initialSession(root: UINode) throws -> AndroidDocumentSession<State> {
        try AndroidDocumentSession(state: State(), document: { _, revision in
            UIDocument(revision: revision, root: root)
        }, reduce: { _, _ in })
    }

    private func packet(_ bytes: Data) throws -> (document: UIDocument, identities: [UINodeIdentity]) {
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: bytes) as? [String: Any])
        let document = try UIDocument.decode(JSONSerialization.data(withJSONObject: XCTUnwrap(object["document"])))
        let identities = try JSONDecoder().decode([UINodeIdentity].self,
            from: JSONSerialization.data(withJSONObject: XCTUnwrap(object["identities"])))
        return (document, identities)
    }

    private func event(_ bytes: Data, value: String) throws -> Data {
        let current = try packet(bytes)
        let identity = try XCTUnwrap(current.identities.first { $0.id == "field" })
        return try JSONEncoder().encode(UIEventEnvelope(revision: current.document.revision,
            identity: identity, event: .textChange, value: .string(value)))
    }

    private func assertUnsupportedUI<T>(_ expression: @autoclosure () throws -> T,
                                        file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertThrowsError(try expression(), file: file, line: line) { error in
            guard case AndroidDocumentError.unsupportedUI = error else {
                XCTFail("Expected AndroidDocumentError.unsupportedUI, got \(error)", file: file, line: line)
                return
            }
        }
    }

    private func assertValidationError<T>(_ expected: UIValidationError,
                                          _ expression: @autoclosure () throws -> T,
                                          file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertThrowsError(try expression(), file: file, line: line) { error in
            XCTAssertEqual(error as? UIValidationError, expected, file: file, line: line)
        }
    }

    func testTypedDefaultAndExplicitHorizontalKeepEqualPacketsAndSuccessfulUpdates() throws {
        let implicit = Self.typedDocument(State(), revision: 1, explicitHorizontal: false)
        let explicit = Self.typedDocument(State(), revision: 1, explicitHorizontal: true)
        XCTAssertEqual(implicit, explicit)
        XCTAssertNil(implicit.root.properties["axis"])
        XCTAssertNil(explicit.root.properties["axis"])
        XCTAssertEqual(try UIValidator().encode(implicit), try UIValidator().encode(explicit))
        var reconciler = UIReconciler()
        try reconciler.apply(implicit)
        let expected = try reconciler.currentSnapshot().encodeNativePacketV1()
        var implicitSession = try Self.typedSession(explicitHorizontal: false)
        var explicitSession = try Self.typedSession(explicitHorizontal: true)
        let first = try implicitSession.render()
        XCTAssertEqual(first, expected)
        XCTAssertEqual(try explicitSession.render(), first)
        let edit = try event(first, value: "Café 東京 🧪")
        let implicitNext = try implicitSession.dispatch(edit)
        let explicitNext = try explicitSession.dispatch(edit)
        XCTAssertEqual(implicitNext, explicitNext)
        XCTAssertEqual(implicitSession.state, State(value: "Café 東京 🧪"))
        XCTAssertEqual(explicitSession.state, implicitSession.state)
        XCTAssertEqual(implicitSession.revision, 2)
        XCTAssertEqual(explicitSession.revision, 2)
        let next = try packet(implicitNext)
        XCTAssertEqual(next.document.revision, 2)
        XCTAssertEqual(next.document.root.properties["value"], .string("Café 東京 🧪"))
        XCTAssertNil(next.document.root.properties["axis"])
        XCTAssertEqual(next.identities, try packet(first).identities)
    }

    func testRawHorizontalIsPreservedBySDKButRejectedAtAndroidInitialization() throws {
        let raw = Data(#"{"schemaVersion":1,"revision":1,"root":{"id":"field","kind":"textField","properties":{"label":"Title","value":"Initial","axis":"horizontal"},"children":[],"actions":[{"id":"edit","event":"textChange"}]}}"#.utf8)
        let decoded = try UIValidator().decode(raw).document
        XCTAssertEqual(decoded.root.properties["axis"], .string("horizontal"))
        let encoded = try UIValidator().encode(decoded)
        XCTAssertEqual(try UIDocument.decode(encoded), decoded)
        var reconciler = UIReconciler()
        try reconciler.apply(decoded)
        let snapshot = try reconciler.currentSnapshot()
        let nativePacket = try packet(snapshot.encodeNativePacketV1())
        XCTAssertEqual(nativePacket.document, decoded)
        XCTAssertEqual(nativePacket.document.root.properties["axis"], .string("horizontal"))
        XCTAssertEqual(nativePacket.identities, [try XCTUnwrap(snapshot.identity(for: "field"))])
        assertUnsupportedUI(try Self.initialSession(root: decoded.root))
        XCTAssertEqual(decoded.root.properties["axis"], .string("horizontal"))
    }

    func testRawHorizontalReducerCandidateRollsBackAndOriginalEventIdentityCanRecover() throws {
        var session = try AndroidDocumentSession(state: State(), document: { state, revision in
            var root = Self.typedDocument(state, revision: revision, explicitHorizontal: false).root
            if state.emitRawHorizontal { root.properties["axis"] = .string("horizontal") }
            return UIDocument(revision: revision, root: root)
        }, reduce: { state, action in
            guard action.actionID == "edit", case .string(let value) = action.value else {
                throw AndroidDocumentError.invalidEvent
            }
            state.value = value
            state.emitRawHorizontal = value == "reject-axis"
        })
        let first = try session.render()
        let rejected = try event(first, value: "reject-axis")
        for _ in 0..<2 {
            assertUnsupportedUI(try session.dispatch(rejected))
            XCTAssertEqual(session.state, State())
            XCTAssertEqual(session.revision, 1)
            XCTAssertEqual(try session.render(), first)
        }
        let accepted = try session.dispatch(event(first, value: "Accepted"))
        XCTAssertEqual(session.state, State(value: "Accepted"))
        XCTAssertEqual(session.revision, 2)
        let next = try packet(accepted)
        XCTAssertEqual(next.document.revision, 2)
        XCTAssertEqual(next.document.root.properties["value"], .string("Accepted"))
        XCTAssertNil(next.document.root.properties["axis"])
        XCTAssertEqual(next.identities, try packet(first).identities)
        XCTAssertThrowsError(try session.dispatch(rejected)) { error in
            XCTAssertEqual(error as? UIRoutingError, .staleRevision)
        }
        XCTAssertEqual(session.state, State(value: "Accepted"))
        XCTAssertEqual(session.revision, 2)
        XCTAssertEqual(try session.render(), accepted)
    }

    func testNestedExplicitHorizontalIsRefused() throws {
        let field = Self.rawField(axis: .string("horizontal"))
        let root = UINode(id: "outer", kind: .vStack, children: [
            Text("sibling", "Heading").uiNode,
            UINode(id: "section", kind: .section, children: [
                UINode(id: "row", kind: .hStack, children: [field])
            ])
        ])
        _ = try UIValidator().validate(UIDocument(revision: 1, root: root))
        assertUnsupportedUI(try Self.initialSession(root: root))
        XCTAssertEqual(field.properties["axis"], .string("horizontal"))
    }

    func testMalformedAxisKeepsGenericValidationErrorPriority() {
        let malformed: [UIValue] = [.null, .bool(true), .number(1), .string("diagonal"), .string("")]
        for axis in malformed {
            let field = Self.rawField(axis: axis)
            let expected = UIValidationError.invalidProperty(node: "field", key: "axis")
            assertValidationError(expected, try UIValidator().validate(UIDocument(revision: 1, root: field)))
            assertValidationError(expected, try Self.initialSession(root: field))
        }
    }

    func testWholeDocumentMalformedValidationPrecedesAndroidAxisRefusal() {
        let root = UINode(id: "root", kind: .vStack, children: [
            Self.rawField(axis: .string("horizontal")),
            UINode(id: "broken", kind: .text)
        ])
        let expected = UIValidationError.invalidProperty(node: "broken", key: "text")
        assertValidationError(expected, try UIValidator().validate(UIDocument(revision: 1, root: root)))
        assertValidationError(expected, try Self.initialSession(root: root))
    }

    func testTypedAndRawVerticalKeepPortableDefaultRefusal() {
        let typed = TextField("field", "Title", value: "Initial", action: "edit", axis: .vertical).uiNode
        let raw = Self.rawField(axis: .string("vertical"))
        for field in [typed, raw] {
            assertValidationError(.unsupportedTextFieldAxis(.vertical),
                                  try UIValidator().validate(UIDocument(revision: 1, root: field)))
            assertValidationError(.unsupportedTextFieldAxis(.vertical), try Self.initialSession(root: field))
        }
    }

    func testWholeDocumentVerticalValidationPrecedesAndroidAxisRefusal() {
        let vertical = UINode(id: "vertical", kind: .textField,
            properties: ["label": .string("Title"), "value": .string("Initial"), "axis": .string("vertical")],
            actions: [UIActionBinding(id: "edit.vertical", event: .textChange)])
        let root = UINode(id: "root", kind: .vStack, children: [Self.rawField(axis: .string("horizontal")), vertical])
        assertValidationError(.unsupportedTextFieldAxis(.vertical),
                              try UIValidator().validate(UIDocument(revision: 1, root: root)))
        assertValidationError(.unsupportedTextFieldAxis(.vertical), try Self.initialSession(root: root))
    }
}
