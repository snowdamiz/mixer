import Foundation
import MixerAndroid
import MixerUI
import XCTest
@_spi(MixerNativeAppearanceV2) import MixerAndroidRuntime

final class AndroidDocumentProfileTests: XCTestCase {
    private struct State: Equatable, Sendable {
        var first = "Zoë\n  café"
        var second = "  café\nZoë  "
    }
    private enum Rejected: Error { case reducer }
    private static let measured: [AndroidUIProfile] = [.measuredMultilineV2, .measuredMultilineRetirementV3]

    private static func document(_ state: State, _ revision: UInt64,
                                 axes: [UIValue?], reversed: Bool = false) -> UIDocument {
        var children = zip(["first", "second"], [state.first, state.second]).enumerated().map { index, pair in
            var field = TextField(pair.0, pair.0, value: pair.1, action: pair.0 + ".edit",
                                  axis: axes[index] == .string("vertical") ? .vertical : .horizontal).uiNode
            if let axis = axes[index] { field.properties["axis"] = axis }
            return field
        }
        if state.first == "vertical" { children[0].properties["axis"] = .string("vertical") }
        if reversed { children.reverse() }
        var root = UINode(id: "root", kind: .vStack, children: children)
        switch state.first {
        case "nested": root = UINode(id: "outer", kind: .list, children: [UINode(id: "inner", kind: .list)])
        case "firstTextBaseline", "lastTextBaseline":
            root = UINode(id: "root", kind: .hStack, properties: ["alignment": .string(state.first)], children: children)
        case "invalid":
            children[0].properties["axis"] = .string("diagonal")
            root = UINode(id: "root", kind: .vStack, children: children)
        case "overflow":
            children += (0..<11).map { Text("large.\($0)", String(repeating: "\0", count: 16_384)).uiNode }
            root = UINode(id: "root", kind: .vStack, children: children)
        default: break
        }
        return UIDocument(revision: state.first == "bad-revision" ? revision + 1 : revision, root: root)
    }
    private static func reduce(_ state: inout State, _ action: RoutedUIAction) throws {
        guard case .string(let value) = action.value else { throw AndroidDocumentError.invalidEvent }
        switch action.actionID {
        case "first.edit": state.first = value
        case "second.edit": state.second = value
        default: throw AndroidDocumentError.invalidEvent
        }
        if value == "throw" { throw Rejected.reducer }
    }
    private static func session(_ profile: AndroidUIProfile, axes: [UIValue?] = [.string("vertical"), .string("vertical")],
                                reversed: Bool = false, state: State = State()) throws -> AndroidDocumentSession<State> {
        try AndroidDocumentSession(state: state, profile: profile,
            document: { Self.document($0, $1, axes: axes, reversed: reversed) }, reduce: Self.reduce)
    }
    private static func legacy(axes: [UIValue?]) throws -> AndroidDocumentSession<State> {
        try AndroidDocumentSession(state: State(), document: { Self.document($0, $1, axes: axes) }, reduce: Self.reduce)
    }
    private func packet(_ bytes: Data) throws -> (UIDocument, [UINodeIdentity]) {
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: bytes) as? [String: Any])
        XCTAssertEqual(Set(object.keys), ["schemaVersion", "document", "identities"])
        XCTAssertEqual(object["schemaVersion"] as? Int, 1)
        let document = try UIValidator(supportedTextFieldAxes: [.horizontal, .vertical]).decode(
            JSONSerialization.data(withJSONObject: XCTUnwrap(object["document"]))).document
        let identities = try JSONDecoder().decode([UINodeIdentity].self,
            from: JSONSerialization.data(withJSONObject: XCTUnwrap(object["identities"])))
        return (document, identities)
    }
    private func event(_ bytes: Data, id: String = "first", value: String) throws -> Data {
        let (document, identities) = try packet(bytes)
        return try JSONEncoder().encode(UIEventEnvelope(revision: document.revision,
            identity: XCTUnwrap(identities.first { $0.id == id }), event: .textChange, value: .string(value)))
    }
    private func assertValues(_ bytes: Data, _ state: State, revision: UInt64,
                              file: StaticString = #filePath, line: UInt = #line) throws {
        let (document, _) = try packet(bytes)
        XCTAssertEqual(document.revision, revision, file: file, line: line)
        for (id, value) in [("first", state.first), ("second", state.second)] {
            let node = try XCTUnwrap(document.root.children.first { $0.id == id }, file: file, line: line)
            XCTAssertEqual(node.properties["value"], .string(value), file: file, line: line)
            XCTAssertEqual(Array(try XCTUnwrap(node.properties["value"]?.string).utf8), Array(value.utf8), file: file, line: line)
        }
    }
    private func assertDocumentError<T>(_ expected: AndroidDocumentError, _ body: @autoclosure () throws -> T,
                                        file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertThrowsError(try body(), file: file, line: line) { error in
            switch (expected, error) {
            case (.unsupportedUI, AndroidDocumentError.unsupportedUI),
                 (.invalidEvent, AndroidDocumentError.invalidEvent),
                 (.outputLimit, AndroidDocumentError.outputLimit): break
            default: XCTFail("Unexpected error: \(error)", file: file, line: line)
            }
        }
    }

    func testLegacyOverloadPreservesEveryExplicitAxisRefusal() {
        for profile in [AndroidUIProfile.legacyHorizontal] {
            assertDocumentError(.unsupportedUI, try Self.session(profile, axes: [.string("horizontal"), nil]))
            XCTAssertThrowsError(try Self.session(profile)) { error in
                XCTAssertEqual(error as? UIValidationError, .unsupportedTextFieldAxis(.vertical))
            }
        }
        assertDocumentError(.unsupportedUI, try Self.legacy(axes: [.string("horizontal"), nil]))
        XCTAssertThrowsError(try Self.legacy(axes: [.string("vertical"), nil])) { error in
            XCTAssertEqual(error as? UIValidationError, .unsupportedTextFieldAxis(.vertical))
        }
    }

    func testNoAxisDefaultsKeepExactLegacyPacketsAcrossProfilesAndDispatch() throws {
        var legacy = try Self.legacy(axes: [nil, nil])
        let first = try legacy.render()
        let edit = try event(first, value: "Zoë  café\n  unchanged")
        let expected = try legacy.dispatch(edit)
        for profile in AndroidUIProfile.allCases {
            var selected = try Self.session(profile, axes: [nil, nil])
            XCTAssertEqual(try selected.render(), first)
            XCTAssertEqual(try selected.dispatch(edit), expected)
            XCTAssertEqual(selected.state, legacy.state)
            XCTAssertEqual(selected.revision, 2)
        }
    }

    func testV3TwoVerticalFieldsHaveExactPacketJSON() throws {
        let session = try Self.session(.measuredMultilineRetirementV3)
        let bytes = try session.render()
        let expected = #"{"document":{"revision":1,"root":{"actions":[],"children":[{"actions":[{"event":"textChange","id":"first.edit"}],"children":[],"id":"first","kind":"textField","properties":{"axis":"vertical","label":"first","value":"Zoë\u000a  café"}},{"actions":[{"event":"textChange","id":"second.edit"}],"children":[],"id":"second","kind":"textField","properties":{"axis":"vertical","label":"second","value":"  café\u000aZoë  "}}],"id":"root","kind":"vStack","properties":{}},"schemaVersion":1},"identities":[{"generation":1,"id":"root"},{"generation":2,"id":"first"},{"generation":3,"id":"second"}],"schemaVersion":1}"#
        XCTAssertEqual(bytes, Data(expected.utf8))
        try assertValues(bytes, State(), revision: 1)
        XCTAssertEqual(try session.render(), bytes)
    }

    func testMeasuredProfilesAdmitBothAxesInBothOrdersWithTypedInput() throws {
        for profile in Self.measured {
            for reversed in [false, true] {
                let combinations: [[UIValue?]] = [[.string("horizontal"), .string("vertical")], [.string("vertical"), .string("horizontal")]]
                for axes in combinations {
                    var session = try Self.session(profile, axes: axes, reversed: reversed)
                    let first = try session.render()
                    let identities = Dictionary(uniqueKeysWithValues: try packet(first).1.map { ($0.id, $0) })
                    try assertValues(first, State(), revision: 1)
                    let second = try session.dispatch(event(first, id: "second", value: "café\n  Zoë  "))
                    let third = try session.dispatch(event(second, value: "  Zoë\n\ncafé  "))
                    try assertValues(third, State(first: "  Zoë\n\ncafé  ", second: "café\n  Zoë  "), revision: 3)
                    XCTAssertEqual(try session.render(), third)
                    let (document, updated) = try packet(third)
                    XCTAssertEqual(document.root.children.map(\.id), reversed ? ["second", "first"] : ["first", "second"])
                    for (index, id) in ["first", "second"].enumerated() {
                        XCTAssertEqual(document.root.children.first { $0.id == id }?.properties["axis"], axes[index])
                    }
                    XCTAssertEqual(Dictionary(uniqueKeysWithValues: updated.map { ($0.id, $0) }), identities)
                }
            }
        }
    }

    func testSessionSelectionDoesNotFollowSuccessfulInitialRenderOrOtherSessions() throws {
        for profile in Self.measured {
            var selected = try Self.session(profile, axes: [nil, nil])
            var legacy = try Self.legacy(axes: [nil, nil])
            let initial = try selected.render()
            let copy = selected
            XCTAssertEqual(try legacy.render(), initial)
            let input = try event(initial, value: "vertical")
            let vertical = try selected.dispatch(input)
            XCTAssertEqual(try packet(vertical).0.root.children[0].properties["axis"], .string("vertical"))
            XCTAssertEqual(try selected.render(), vertical)
            XCTAssertEqual(try copy.render(), initial)
            XCTAssertThrowsError(try legacy.dispatch(input)) { error in
                XCTAssertEqual(error as? UIValidationError, .unsupportedTextFieldAxis(.vertical))
            }
            XCTAssertEqual(legacy.state, State())
            XCTAssertEqual(legacy.revision, 1)
            XCTAssertEqual(try legacy.render(), initial)
            let next = try selected.dispatch(event(vertical, id: "second", value: "Zoë  café\n"))
            XCTAssertEqual(try packet(next).0.root.children[0].properties["axis"], .string("vertical"))
            XCTAssertEqual(try selected.render(), next)
        }
    }

    func testMalformedAxesRemainValidatorFailuresForEveryProfile() {
        for profile in AndroidUIProfile.allCases {
            let invalidAxes: [UIValue] = [.null, .bool(true), .number(1), .string("diagonal"), .string("")]
            for axis in invalidAxes {
                XCTAssertThrowsError(try Self.session(profile, axes: [axis, nil])) { error in
                    XCTAssertEqual(error as? UIValidationError, .invalidProperty(node: "first", key: "axis"))
                }
            }
        }
    }

    func testUnsupportedStructureRevisionAndReducerFailuresRollBackMeasuredSessions() throws {
        for profile in Self.measured {
            for value in ["nested", "firstTextBaseline", "lastTextBaseline", "bad-revision", "throw", "invalid", "overflow"] {
                var session = try Self.session(profile)
                let first = try session.render()
                let rejected = try event(first, value: value)
                XCTAssertThrowsError(try session.dispatch(rejected)) { error in
                    switch value {
                    case "nested", "firstTextBaseline", "lastTextBaseline":
                        guard case AndroidDocumentError.unsupportedUI = error else { return XCTFail("\(error)") }
                    case "bad-revision":
                        guard case AndroidDocumentError.invalidEvent = error else { return XCTFail("\(error)") }
                    case "throw":
                        guard case Rejected.reducer = error else { return XCTFail("\(error)") }
                    case "invalid": XCTAssertEqual(error as? UIValidationError, .invalidProperty(node: "first", key: "axis"))
                    case "overflow":
                        guard case AndroidDocumentError.outputLimit = error else { return XCTFail("\(error)") }
                    default: XCTFail("uncovered case")
                    }
                }
                XCTAssertEqual(session.state, State())
                XCTAssertEqual(session.revision, 1)
                XCTAssertEqual(try session.render(), first)
                let recovered = try session.dispatch(event(first, value: "Zoë\n  café  recovered"))
                try assertValues(recovered, State(first: "Zoë\n  café  recovered"), revision: 2)
                XCTAssertEqual(try packet(recovered).1, try packet(first).1)
                XCTAssertThrowsError(try session.dispatch(rejected)) { error in
                    XCTAssertEqual(error as? UIRoutingError, .staleRevision)
                }
                XCTAssertEqual(try session.render(), recovered)
            }
        }
    }

    func testMeasuredInitialRestrictionsAndInputBoundsRemainClosed() throws {
        for profile in Self.measured {
            for value in ["nested", "firstTextBaseline", "lastTextBaseline"] {
                assertDocumentError(.unsupportedUI, try Self.session(profile, state: State(first: value)))
            }
            assertDocumentError(.invalidEvent, try Self.session(profile, state: State(first: "bad-revision")))
            assertDocumentError(.outputLimit, try Self.session(profile, state: State(first: "overflow")))
            var session = try Self.session(profile)
            let first = try session.render()
            for input in [Data("{}".utf8), Data(repeating: 32, count: 131_073)] {
                assertDocumentError(.invalidEvent, try session.dispatch(input))
                XCTAssertEqual(session.state, State())
                XCTAssertEqual(session.revision, 1)
                XCTAssertEqual(try session.render(), first)
            }
            var stale = try JSONDecoder().decode(UIEventEnvelope.self, from: event(first, value: "stale"))
            stale = UIEventEnvelope(revision: 0, identity: stale.identity, event: stale.event, value: stale.value)
            XCTAssertThrowsError(try session.dispatch(JSONEncoder().encode(stale))) { error in
                XCTAssertEqual(error as? UIRoutingError, .staleRevision)
            }
            XCTAssertEqual(try session.render(), first)
        }
    }

    func testStagedRegistryUsesProductionProfileFactoryThroughAbortAndCommit() throws {
        let transport = TransactionTests()
        for profile in Self.measured {
            let registry = AndroidSessionRegistry { try Self.session(profile) }
            let handle = registry.create()
            XCTAssertNotEqual(handle, 0)
            defer { XCTAssertEqual(registry.destroy(handle), 0) }
            let initial = transport.render(registry, handle)
            XCTAssertEqual(initial.status, 0)
            try assertValues(initial.bytes, State(), revision: 1)
            let opening = transport.call(registry, handle, staged: true, operation: 0)
            XCTAssertEqual(opening.status, 0)
            XCTAssertGreaterThan(opening.token, 0)
            XCTAssertEqual(opening.bytes, initial.bytes)
            XCTAssertEqual(registry.commitV2(handle, opening.token), 0)
            let input = try event(initial.bytes, value: "Zoë\n  café  staged")
            let small = transport.call(registry, handle, staged: true, input: input, capacity: 0)
            XCTAssertEqual(small.status, 3)
            XCTAssertEqual(small.token, 0)
            XCTAssertGreaterThan(small.written, 0)
            XCTAssertEqual(transport.render(registry, handle).bytes, initial.bytes)
            let aborted = transport.call(registry, handle, staged: true, input: input)
            XCTAssertEqual(aborted.status, 0)
            try assertValues(aborted.bytes, State(first: "Zoë\n  café  staged"), revision: 2)
            XCTAssertEqual(transport.render(registry, handle).status, 5)
            XCTAssertEqual(registry.abortV2(handle, aborted.token), 0)
            XCTAssertEqual(transport.render(registry, handle).bytes, initial.bytes)
            let accepted = transport.call(registry, handle, staged: true, input: input)
            XCTAssertEqual(accepted.status, 0)
            XCTAssertEqual(accepted.bytes, aborted.bytes)
            XCTAssertEqual(registry.commitV2(handle, accepted.token), 0)
            XCTAssertEqual(registry.commitV2(handle, accepted.token), 6)
            XCTAssertEqual(transport.render(registry, handle).bytes, accepted.bytes)
            let secondInput = try event(accepted.bytes, id: "second", value: "  café\nZoë")
            let second = transport.call(registry, handle, staged: true, input: secondInput)
            XCTAssertEqual(second.status, 0)
            XCTAssertEqual(registry.commitV2(handle, second.token), 0)
            try assertValues(transport.render(registry, handle).bytes,
                             State(first: "Zoë\n  café  staged", second: "  café\nZoë"), revision: 3)
            let rejected = transport.call(registry, handle, staged: true, input: input)
            XCTAssertEqual(rejected.status, 4)
            XCTAssertEqual(rejected.token, 0)
            XCTAssertEqual(rejected.written, 0)
            XCTAssertEqual(transport.render(registry, handle).bytes, second.bytes)
        }
    }
}
