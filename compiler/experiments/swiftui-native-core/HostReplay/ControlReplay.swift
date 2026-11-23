import Foundation
import MixerSwiftUI
import MixerUI
import ReplayFeature

func layoutRefusals() throws {
    let session = FeatureSession(executor: replayExecutor)
    let initial = try session.prepare { HStack { Text("Original") } }
    accept(initial, in: session)

    for spacing: CGFloat in [-1, 257, .infinity, .nan] {
        let candidate = try session.prepare { HStack { Text("Pending") } }
        do {
            _ = try session.prepare { HStack(spacing: spacing) { Text("Refused") } }
            preconditionFailure("Unrepresentable spacing was accepted: \(spacing)")
        } catch UIValidationError.invalidProperty(_, let key) {
            expect(key == "spacing", "Spacing must fail through the existing validator")
        }
        expect(!session.finish(candidate.presentation.token, outcome: .drawnAndInputReady),
               "The refused build must supersede the previous candidate")
        expect(session.acceptedPresentation?.snapshot.document == initial.presentation.snapshot.document,
               "The refused build must preserve the accepted document")
    }

    let withoutList = FeatureSession(executor: replayExecutor, validator: UIValidator(supportedKinds: [.text]))
    try expectError(UIValidationError.unsupportedNode(.list)) {
        _ = try withoutList.prepare { List { Text("Unsupported") } }
    }
    print("PASS unsupported spacing and node kinds fail through SDK validation")
}

func typedControls() throws {
    let session = FeatureSession(executor: replayExecutor)
    let rows = [Row(1, "A"), Row(2, "B")]
    var bindings: [Int: (Binding<String>, Binding<Bool>)] = [:]
    func stage(_ rows: [Row]) throws -> PreparedFrame {
        try session.prepare { EditorScreen(rows: rows, retain: { bindings[$0] = ($1, $2) }) }
    }
    func envelope(_ frame: PreparedFrame, _ node: UINode, _ event: UIEventKind, _ value: UIValue) -> UIEventEnvelope {
        let snapshot = frame.presentation.snapshot
        return UIEventEnvelope(revision: snapshot.document.revision, identity: snapshot.identity(for: node.id)!,
                               event: event, value: value)
    }

    let first = try stage(rows)
    let token = first.presentation.token
    let snapshot = first.presentation.snapshot
    let root = snapshot.document.root
    expect(root.kind == .list && root.properties.isEmpty, "List must emit the plain SDK list")
    let sections = root.children
    expect(sections.map(\.kind) == [.section, .section, .section], "Sections must remain distinct SDK nodes")
    expect(sections.map { $0.properties["title"] } == [.string("Editors"), nil, .string("Details")],
           "Only titled sections must emit a title")
    let rowA = sections[0].children[0]
    expect(rowA.kind == .hStack && rowA.properties == ["alignment": .string("top"), "spacing": .number(12.5)],
           "HStack must preserve the supported layout values")
    expect(sections[1].children[0].properties == ["alignment": .string("center")],
           "Default spacing must stay unspecified")
    expect(sections[2].children[0].properties == ["alignment": .string("bottom"), "spacing": .number(0)],
           "Explicit zero spacing must stay explicit")
    let field = rowA.children[0]
    let toggle = rowA.children[1]
    expect(field.kind == .textField && field.properties == ["label": .string("Name A"), "value": .string("")],
           "The editor must emit a single-line string field with its initial state")
    expect(toggle.kind == .toggle && toggle.properties == ["label": .string("Enable A"), "value": .bool(false)],
           "The toggle must emit its initial Boolean state")
    expect(field.actions.map(\.event) == [.textChange] && toggle.actions.map(\.event) == [.valueChange],
           "Each control must bind only its corresponding event")
    let validator = UIValidator()
    expect(try validator.decode(validator.encode(snapshot.document)).document == snapshot.document,
           "The controls must round-trip through the existing document wire")

    let editedText = "Cafe\u{301} 🪴"
    let edit = envelope(first, field, .textChange, .string(editedText))
    let enable = envelope(first, toggle, .valueChange, .bool(true))
    let disable = envelope(first, toggle, .valueChange, .bool(false))
    let initialA = bindings[1]!
    let initialB = bindings[2]!
    expect(session.dispatch(token, edit) == .rejected && session.dispatch(token, enable) == .rejected,
           "Candidate control input must stay gated")
    accept(first, in: session)
    for (event, node) in [(edit, field), (enable, toggle)] {
        let routed = try snapshot.route(event)
        expect(routed.actionID == node.actions[0].id && routed.value == event.value,
               "The SDK must resolve the control's typed payload and action ID")
        expect(session.dispatch(token, event) == .handled(superseded: nil), "Accepted control input must run")
    }
    expect(initialA.0.wrappedValue.utf8.elementsEqual(editedText.utf8) && initialA.1.wrappedValue,
           "Accepted input must publish the exact text and Boolean values")
    expect(initialB.0.wrappedValue.isEmpty && !initialB.1.wrappedValue, "Input must target only the edited row")

    let canceled = try stage([rows[1]])
    let invalid: [(UIEventEnvelope, UIRoutingError)] = [
        (envelope(first, field, .textChange, .bool(false)), .invalidValue),
        (envelope(first, toggle, .valueChange, .string("false")), .invalidValue),
        (envelope(first, field, .textChange, .string(String(repeating: "x", count: 16_385))), .invalidValue),
        (envelope(first, field, .submit, .null), .unboundEvent),
        (UIEventEnvelope(revision: edit.revision + 1, identity: edit.identity, event: edit.event, value: edit.value),
         .staleRevision),
        (UIEventEnvelope(revision: enable.revision,
                         identity: UINodeIdentity(id: enable.identity.id, generation: enable.identity.generation + 1),
                         event: enable.event, value: enable.value), .staleIdentity),
    ]
    for (event, error) in invalid {
        try expectError(error) { _ = try snapshot.route(event) }
        expect(session.dispatch(token, event) == .rejected, "Invalid routing must refuse dispatch")
    }
    expect(session.finish(canceled.presentation.token, outcome: .canceled),
           "Invalid input must leave the candidate available for its own cancel receipt")
    expect(!session.finish(canceled.presentation.token, outcome: .drawnAndInputReady), "Canceled receipt must be stale")
    expect(session.acceptedPresentation?.snapshot.document == snapshot.document && initialA.1.wrappedValue,
           "Cancellation must preserve the accepted snapshot and edits")

    let oversized = envelope(first, field, .textChange, .string(String(repeating: "é", count: 513)))
    let pending = try stage(rows)
    _ = try snapshot.route(oversized)
    expect(session.dispatch(token, oversized) ==
           .invalidState(.limitExceeded("state value bytes"), superseded: pending.presentation.token),
           "SDK-admitted edits must still enforce the authored state bound")
    expect(!session.finish(pending.presentation.token, outcome: .drawnAndInputReady),
           "A routed event must invalidate a previously staged frame")
    expect(initialA.0.wrappedValue.utf8.elementsEqual(editedText.utf8), "An invalid state write must preserve the edit")
    expect(session.dispatch(token, disable) == .handled(superseded: nil) && !initialA.1.wrappedValue,
           "A current toggle must assign the incoming false value after cancellation")

    for staleBinding in [initialA.0, State(wrappedValue: "").projectedValue] {
        try expectError(FeatureError.unboundControl) {
            _ = try session.prepare { TextField("Unbound", text: staleBinding) }
        }
    }
    expect(session.acceptedPresentation?.token == token, "A refused authored binding must preserve the accepted frame")

    let moved = try stage(Array(rows.reversed()))
    let movedA = moved.presentation.snapshot.document.root.children[0].children[1]
    let movedField = movedA.children[0]
    let movedToggle = movedA.children[1]
    let clear = envelope(moved, movedField, .textChange, .string(""))
    let reenable = envelope(moved, movedToggle, .valueChange, .bool(true))
    expect(movedA.id == rowA.id && clear.identity == edit.identity && reenable.identity == enable.identity,
           "Moving a keyed row must preserve both control identities")
    expect(movedField.properties["value"]?.string?.utf8.elementsEqual(editedText.utf8) == true
           && movedToggle.properties["value"] == .bool(false), "The rebuilt row must keep its committed state")
    expect(moved.changes.moved.contains { $0.id == rowA.id } &&
           moved.changes.updated.contains(field.id), "The existing reconciler must report the row move and field edit")
    accept(moved, in: session)
    let current = moved.presentation.token
    expect(session.dispatch(token, enable) == .rejected && session.dispatch(current, edit) == .rejected,
           "Neither a stale token nor a stale SDK revision may revive a callback")
    expect(session.dispatch(current, clear) == .handled(superseded: nil)
           && session.dispatch(current, reenable) == .handled(superseded: nil), "The promoted controls must accept input")
    expect(bindings[1]!.0.wrappedValue.isEmpty && bindings[1]!.1.wrappedValue,
           "The promoted controls must write their own cells")
    print("PASS typed control envelopes, canceled and invalid candidates, keyed edit state, and stale authority")
}
