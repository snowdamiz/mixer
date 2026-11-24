import MixerSwiftUI
import MixerUI
import ReplayFeature

private func modifierInputs(
    _ frame: PreparedFrame, forRowAt index: Int, name: String = "Zoë 🪴", flag: Bool = true
) -> [UIEventEnvelope] {
    let snapshot = frame.presentation.snapshot
    let children = snapshot.document.root.children[index].children
    let events: [(UIEventKind, UIValue)] = [(.activate, .null), (.textChange, .string(name)), (.valueChange, .bool(flag))]
    return zip(children.dropFirst(), events).map { node, input in
        UIEventEnvelope(revision: snapshot.document.revision, identity: snapshot.identity(for: node.id)!,
                        event: input.0, value: input.1)
    }
}

private func modifierAuthority() throws {
    let session = FeatureSession(executor: replayExecutor)
    let rows = [Row(1, "A"), Row(2, "B")]
    func stage(locked: Bool, reversed: Bool = false, label: String = "Enregistrer 🪴") throws -> PreparedFrame {
        try session.prepare { ModifierScreen(rows: reversed ? Array(rows.reversed()) : rows, locked: locked, saveLabel: label) }
    }

    let first = try stage(locked: false)
    let firstToken = first.presentation.token
    let doc = first.presentation.snapshot.document
    let firstRow = doc.root.children[0]
    let nodes = firstRow.children
    expect(nodes.map(\.kind) == [.text, .button, .textField, .toggle], "Modifiers must preserve the underlying nodes")
    expect(nodes[0].properties["accessibilityLabel"] == .string("Save count"), "Text must carry the authored label")
    expect(nodes[1].properties["accessibilityLabel"] == .string("Enregistrer 🪴") &&
           nodes[1].properties["accessibilityHint"] == .string("Records the current edit") &&
           nodes[1].properties["label"] == .string("Save A"), "Button metadata must preserve its visible label")
    expect(nodes[2].properties["accessibilityHint"] == .string("Enter the full name") &&
           nodes[3].properties["accessibilityLabel"] == .string("Flag for review"), "Editable controls must carry metadata")
    let validator = UIValidator()
    expect(try validator.decode(validator.encode(doc)).document == doc, "Modifiers must round-trip through the existing wire")
    let firstInputs = modifierInputs(first, forRowAt: 0)
    expect(firstInputs.count == 3, "The fixture must exercise all three typed inputs")
    for input in firstInputs {
        expect(session.dispatch(firstToken, input) == .rejected, "A prepared frame has no input authority")
    }
    accept(first, in: session)
    for input in firstInputs {
        expect(session.dispatch(firstToken, input) == .handled(superseded: nil), "Accepted enabled inputs must update state")
    }

    let locked = try stage(locked: true, reversed: true, label: "Save edit")
    let lockedToken = locked.presentation.token
    let lockedSnapshot = locked.presentation.snapshot
    let movedRow = lockedSnapshot.document.root.children[1]
    let lockedInputs = modifierInputs(locked, forRowAt: 1, name: "Rejected edit", flag: false)
    expect(lockedSnapshot.document.root.properties["disabled"] == .bool(true), "The disabled scope belongs to the container")
    expect(movedRow.id == firstRow.id && movedRow.children.map(\.id) == nodes.map(\.id) &&
           lockedInputs.map(\.identity) == firstInputs.map(\.identity) &&
           locked.changes.moved.contains { $0.id == firstRow.id } &&
           locked.changes.updated.contains(nodes[1].id) &&
           locked.changes.inserted.isEmpty && locked.changes.removed.isEmpty,
           "Row moves and modifier updates must retain every node and action identity")
    expect(text(locked) == ["B 0", "A 1"] && movedRow.children[2].properties["value"] == .string("Zoë 🪴") &&
           movedRow.children[3].properties["value"] == .bool(true), "A moved, disabled row must keep its accepted state")
    for input in lockedInputs {
        try expectError(UIRoutingError.disabledNode) { _ = try lockedSnapshot.route(input) }
        expect(session.dispatch(lockedToken, input) == .rejected, "The pending disabled inputs must be refused")
        expect(session.dispatch(firstToken, input) == .rejected, "The pending revision cannot use the accepted token")
    }
    accept(locked, in: session)
    for (old, current) in zip(firstInputs, lockedInputs) {
        expect(session.dispatch(firstToken, old) == .rejected && session.dispatch(lockedToken, old) == .rejected,
               "A stale token or revision must lose input authority after promotion")
        expect(session.dispatch(lockedToken, current) == .rejected,
               "A child disabled(false) must leave its accepted ancestor's disabled state in force")
    }

    let enabled = try stage(locked: false, reversed: true)
    let enabledInputs = modifierInputs(enabled, forRowAt: 1, name: "New edit", flag: false)
    let enabledRow = enabled.presentation.snapshot.document.root.children[1]
    expect(text(enabled) == ["B 0", "A 1"] && enabledRow.children[2].properties["value"] == .string("Zoë 🪴") &&
           enabledRow.children[3].properties["value"] == .bool(true), "Rejected inputs must leave all three state values unchanged")
    for input in enabledInputs {
        expect(session.dispatch(enabled.presentation.token, input) == .rejected, "Pending reenablement must not grant input")
    }
    accept(enabled, in: session)
    let enabledToken = enabled.presentation.token
    for input in lockedInputs {
        expect(session.dispatch(enabledToken, input) == .rejected, "Reenablement must not revive an older envelope")
    }
    let malformed = zip(enabledInputs, [UIValue.bool(true), .bool(false), .string("false")]).map { input, value in
        UIEventEnvelope(revision: input.revision, identity: input.identity, event: input.event, value: value)
    }
    for input in malformed {
        try expectError(UIRoutingError.invalidValue) { _ = try enabled.presentation.snapshot.route(input) }
        expect(session.dispatch(enabledToken, input) == .rejected, "Reenablement must still require a typed payload")
    }
    for input in enabledInputs {
        expect(session.dispatch(enabledToken, input) == .handled(superseded: nil), "Only current enabled input must dispatch")
    }
    let updated = try stage(locked: false, reversed: true)
    let updatedRow = updated.presentation.snapshot.document.root.children[1]
    expect(text(updated) == ["B 0", "A 2"] && updatedRow.children[2].properties["value"] == .string("New edit") &&
           updatedRow.children[3].properties["value"] == .bool(false), "Current inputs must update their own keyed state")
    print("PASS disabled ancestry, typed cross-frame refusal, and keyed modifier updates")
}

private func modifierTargets() throws {
    let session = FeatureSession(executor: replayExecutor)
    let group = try session.prepare {
        VStack {
            ForEach([1, 2], id: \.self) { key in
                Button("Blocked \(key)") {}.disabled(false)
            }
            .disabled(true)
            .disabled(false)
            Button("Also blocked") {}.disabled(false).disabled(true)
            Button("Ready") {}
        }
    }
    accept(group, in: session)
    let groupToken = group.presentation.token
    expect(group.presentation.snapshot.document.root.children.count == 4, "Disabled groups need no synthetic node")
    for label in ["Blocked 1", "Blocked 2", "Also blocked"] {
        let input = event(group, button: label)
        try expectError(UIRoutingError.disabledNode) { _ = try group.presentation.snapshot.route(input) }
        expect(session.dispatch(groupToken, input) == .rejected, "Any disabled modifier must prevent activation")
    }
    expect(session.dispatch(groupToken, event(group, button: "Ready")) == .handled(superseded: nil),
           "A disabled group must leave its sibling interactive")

    let plain = try session.prepare { ExplicitCounter("Counter").id(1) }
    accept(plain, in: session)
    let input = event(plain, button: "Increment Counter")
    expect(session.dispatch(plain.presentation.token, input) == .handled(superseded: nil),
           "The plain keyed view must accept input")
    let decorated = try session.prepare { ExplicitCounter("Counter").disabled(false).id(1).disabled(true) }
    expect(text(decorated) == ["Counter 1"] && event(decorated, button: "Increment Counter").identity == input.identity &&
           decorated.changes.inserted.isEmpty && decorated.changes.removed.isEmpty,
           "Adding modifiers on both sides of a key must keep the exact subtree and state")
    try expectError(ExplicitIdentityError.duplicateKey) {
        _ = try session.prepare {
            VStack {
                Text("First").id(1).accessibilityLabel("First label")
                Text("Second").accessibilityHint("Second hint").id(1).disabled(false)
            }
        }
    }
    expect(!session.finish(decorated.presentation.token, outcome: .drawnAndInputReady),
           "A modifier must never hide a duplicate key or leave its superseded candidate promotable")

    let single = try session.prepare {
        ForEach([1], id: \.self) { _ in Text("Single") }
            .accessibilityLabel("Single child")
            .accessibilityHint("")
    }
    expect(single.presentation.snapshot.document.root.properties ==
           ["text": .string("Single"), "accessibilityLabel": .string("Single child"), "accessibilityHint": .string("")],
           "A transparent single-leaf target must retain the exact assigned strings")
    try expectError(FeatureError.unsupportedAccessibilityTarget) {
        _ = try session.prepare {
            VStack {
                Text("Sibling")
                ForEach([1, 2], id: \.self) { _ in Text("Child") }.accessibilityLabel("Ambiguous")
            }
        }
    }
    expect(!session.finish(single.presentation.token, outcome: .drawnAndInputReady),
           "An ambiguous target must supersede the candidate before promotion")
    try expectError(FeatureError.unsupportedAccessibilityTarget) {
        _ = try session.prepare {
            VStack {
                Text("Sibling")
                ForEach([Int](), id: \.self) { _ in Text("Child") }.accessibilityHint("No target")
            }
        }
    }
    try expectError(FeatureError.unsupportedAccessibilityTarget) {
        _ = try session.prepare { Section("Header") { Text("Child") }.accessibilityLabel("Ambiguous scope") }
    }
    try expectError(FeatureError.duplicateAccessibilityProperty("accessibilityLabel")) {
        _ = try session.prepare { Text("Duplicate").accessibilityLabel("First").accessibilityLabel("Second") }
    }
    try expectError(FeatureError.duplicateAccessibilityProperty("accessibilityHint")) {
        _ = try session.prepare { Text("Duplicate").accessibilityHint("First").id(1).accessibilityHint("Second") }
    }
    try expectError(UIValidationError.limitExceeded("stringBytes")) {
        _ = try session.prepare { Text("Oversized").accessibilityLabel(String(repeating: "é", count: 8_193)) }
    }
    expect(session.acceptedPresentation?.token == plain.presentation.token &&
           session.dispatch(plain.presentation.token, input) == .handled(superseded: nil),
           "Invalid accessibility authoring must preserve accepted input authority")
    print("PASS transparent modifier targets and pre-promotion accessibility refusals")
}

func ordinaryModifiers() throws {
    try modifierAuthority()
    try modifierTargets()
}
