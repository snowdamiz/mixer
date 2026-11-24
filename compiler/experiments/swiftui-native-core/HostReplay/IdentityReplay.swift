import MixerSwiftUI
import MixerUI
import ReplayFeature

private func increment(_ title: String, in frame: PreparedFrame, session: FeatureSession) {
    expect(session.dispatch(frame.presentation.token, event(frame, button: "Increment \(title)")) ==
           .handled(superseded: nil), "Accepted callback must increment \(title)")
}

private struct UnsupportedIdentityKey: Hashable {
    static func == (lhs: Self, rhs: Self) -> Bool { preconditionFailure("Called unsupported key equality") }
    func hash(into hasher: inout Hasher) { preconditionFailure("Called unsupported key hashing") }
}

private func siblingMovesAndAuthority() throws {
    let session = FeatureSession(executor: replayExecutor)
    func stage(swapped: Bool = false, firstKey: Int = 1) throws -> PreparedFrame {
        try session.prepare { ExplicitSiblings(swapped: swapped, firstKey: firstKey) }
    }

    let initial = try stage()
    expect(text(initial) == ["A 0", "Between", "B 0", "String 0", "Nested 0"], "Expected plain rendered siblings")
    accept(initial, in: session)
    increment("A", in: initial, session: session)
    increment("String", in: initial, session: session)

    let moved = try stage(swapped: true)
    let oldA = event(moved, button: "Increment A")
    let movedNode = moved.presentation.snapshot.document.root.children[2]
    expect(text(moved) == ["B 0", "Between", "A 1", "String 1", "Nested 0"],
           "Parent plus key must preserve the moved counter and distinguish Int from String")
    expect(oldA.identity == event(initial, button: "Increment A").identity &&
           moved.changes.moved.contains { $0.id == movedNode.id && $0.fromIndex == 0 && $0.toIndex == 2 },
           "The accepted reconciler must see a move, with the descendant identity intact")
    accept(moved, in: session)

    for outcome: PresentationOutcome in [.canceled, .failed] {
        let candidate = try stage(swapped: true, firstKey: 99)
        let candidateInput = event(candidate, button: "Increment A")
        expect(text(candidate)[2] == "A 0" && candidateInput.identity != oldA.identity,
               "Changing a key must stage fresh state and a new SDK identity")
        expect(session.dispatch(candidate.presentation.token, candidateInput) == .rejected,
               "Speculative identity must have no callback authority")
        expect(session.finish(candidate.presentation.token, outcome: outcome), "Discard must consume the candidate")
        expect(!session.finish(candidate.presentation.token, outcome: .drawnAndInputReady),
               "A discarded reset cannot be promoted")
    }
    let pending = try stage(swapped: true, firstKey: 99)
    try expectError(ExplicitIdentityError.duplicateKey) {
        _ = try session.prepare {
            VStack {
                ExplicitCounter("Duplicate").id(1)
                Text("Different concrete type").id(1)
            }
        }
    }
    expect(!session.finish(pending.presentation.token, outcome: .drawnAndInputReady),
           "A key collision must supersede an older pending draw")

    try expectError(ExplicitIdentityError.unsupportedKey) {
        _ = try session.prepare { Text("Custom").id(UnsupportedIdentityKey()) }
    }
    try expectError(ExplicitIdentityError.unsupportedKey) {
        _ = try session.prepare { Text("Boxed").id(AnyHashable(1)) }
    }
    try expectError(FeatureError.limitExceeded("explicit key bytes")) {
        _ = try session.prepare { Text("Oversized").id(String(repeating: "é", count: 129)) }
    }
    expect(session.acceptedPresentation?.token == moved.presentation.token &&
           session.acceptedPresentation?.snapshot.document == moved.presentation.snapshot.document,
           "Every rejected or discarded build must preserve the accepted token and document")
    increment("A", in: moved, session: session)
    expect(text(try stage(swapped: true))[2] == "A 2", "Accepted state and callback must survive all refusals")

    let replacement = try stage(swapped: true, firstKey: 99)
    let replacementInput = event(replacement, button: "Increment A")
    expect(text(replacement)[2] == "A 0" && replacement.changes.removed.contains(movedNode.id) &&
           replacementInput.identity != oldA.identity, "Accepting a new key must replace the previous subtree")
    accept(replacement, in: session)
    expect(session.dispatch(moved.presentation.token, oldA) == .rejected, "The prior frame must lose authority")
    increment("A", in: replacement, session: session)
    let returned = try stage(swapped: true)
    expect(text(returned)[2] == "A 0" && event(returned, button: "Increment A").identity != oldA.identity,
           "Returning to a retired key must not resurrect its state or its node identity")
    print("PASS explicit sibling moves, typed keys, key reset and retirement, duplicate and invalid key authority")
}

private func nestedModifiersAndRows() throws {
    let session = FeatureSession(executor: replayExecutor)
    let initial = try session.prepare { ExplicitSiblings() }
    accept(initial, in: session)
    increment("Nested", in: initial, session: session)
    let moved = try session.prepare { ExplicitSiblings(swapped: true) }
    expect(text(moved).last == "Nested 1", "Both surviving nested keys must keep state")
    let originalID = event(initial, button: "Increment Nested").identity
    for (inner, outer) in [(8, "outer"), (7, "other")] {
        let changed = try session.prepare { ExplicitSiblings(inner: inner, outer: outer) }
        expect(text(changed).last == "Nested 0" && event(changed, button: "Increment Nested").identity != originalID,
               "Each nested explicit modifier must independently reset the subtree")
    }

    let one = Row(1, "R1")
    let two = Row(2, "R2")
    func stage(_ rows: [Row], firstKey: Int = 1, loopKey: Int = 1) throws -> PreparedFrame {
        try session.prepare { ExplicitRows(rows, firstKey: firstKey, loopKey: loopKey) }
    }
    let first = try stage([one, two])
    accept(first, in: session)
    increment("R1", in: first, session: session)
    increment("R2", in: first, session: session)
    let reordered = try stage([two, one])
    for title in ["R1", "R2"] {
        expect(event(reordered, button: "Increment \(title)").identity == event(first, button: "Increment \(title)").identity,
               "ForEach must scope the same inner key to each moving row")
    }
    let rowNode = first.presentation.snapshot.document.root.children[0]
    expect(text(reordered) == ["R2 1", "R1 1"] && reordered.changes.moved.contains { $0.id == rowNode.id },
           "The ForEach reorder must reconcile as a move even with explicit modifiers inside and outside it")
    accept(reordered, in: session)
    let inside = try stage([two, one], firstKey: 2)
    expect(text(inside) == ["R2 1", "R1 0"], "An explicit key inside a loop resets only that row subtree")
    let outside = try stage([two, one], loopKey: 2)
    expect(text(outside) == ["R2 0", "R1 0"], "Changing the explicit key outside a loop resets all row subtrees")
    let replacedRow = try stage([two, Row(3, "R1")])
    expect(text(replacedRow) == ["R2 1", "R1 0"], "An inner explicit key cannot bypass a changed ForEach row key")
    print("PASS nested explicit modifiers and independent ForEach row and loop scopes")
}

private func structuralScopesAndStringKeys() throws {
    let session = FeatureSession(executor: replayExecutor)
    let initial = try session.prepare { ExplicitScopes() }
    accept(initial, in: session)
    for title in ["Branch", "Optional", "Left"] {
        increment(title, in: initial, session: session)
    }
    let same = try session.prepare { ExplicitScopes() }
    expect(text(same) == ["Parent 1", "Branch 1", "Optional 1", "Left 1", "Right 0"],
           "Same-key wrapper scopes must stay independent and the callback must still reach its containing state")
    let changed = try session.prepare { ExplicitScopes(firstBranch: false, showOptional: false) }
    expect(text(changed) == ["Parent 1", "Branch 0", "Left 1", "Right 0"],
           "A branch swap must reset its keyed subtree while preserving unrelated wrapper scopes")
    accept(changed, in: session)
    let reinserted = try session.prepare { ExplicitScopes() }
    expect(text(reinserted) == ["Parent 1", "Branch 0", "Optional 0", "Left 1", "Right 0"],
           "Accepted branch and optional removal must retire their descendant state")

    try expectError(ExplicitIdentityError.duplicateKey) {
        _ = try session.prepare {
            VStack {
                ViewBuilder.buildOptional(nil as MixerSwiftUI.Text?).id(1)
                ViewBuilder.buildOptional(nil as MixerSwiftUI.Text?).id(1)
            }
        }
    }
    let composed = "\u{e9}"
    let decomposed = "e\u{301}"
    try expectError(ExplicitIdentityError.duplicateKey) {
        _ = try session.prepare {
            VStack {
                Text("Composed").id(composed)
                Text("Decomposed").id(decomposed)
            }
        }
    }
    let string = try session.prepare { ExplicitCounter("Unicode").id(composed) }
    accept(string, in: session)
    increment("Unicode", in: string, session: session)
    let equivalent = try session.prepare { ExplicitCounter("Unicode").id(decomposed) }
    expect(text(equivalent) == ["Unicode 1"], "Equal Swift strings must preserve identity despite different UTF-8")
    let boundary = try session.prepare {
        VStack {
            Text("Empty").id("")
            Text("Limit").id(String(repeating: "é", count: 128))
            Text("Negative").id(Int.min)
        }
    }
    expect(text(boundary) == ["Empty", "Limit", "Negative"], "Empty, exactly 256 bytes, and signed keys must work")
    print("PASS wrapper and branch scopes, empty content collision, and UTF-8 key limits and equality")
}

func explicitIdentity() throws {
    try siblingMovesAndAuthority()
    try nestedModifiersAndRows()
    try structuralScopesAndStringKeys()
}

func erasedIdentity() throws {
    let session = FeatureSession(executor: replayExecutor)
    func stage(_ title: String, alternate: Bool = false) throws -> PreparedFrame {
        try session.prepare { erasedCounter(title, alternate: alternate) }
    }

    let first = try stage("First")
    accept(first, in: session)
    increment("First", in: first, session: session)
    let next = try stage("Updated")
    let acceptedEvent = event(next, button: "Increment Updated")
    expect(text(next) == ["Updated 1"] && acceptedEvent.identity == event(first, button: "Increment First").identity,
           "A new value of the same erased type must preserve state and node identity")
    accept(next, in: session)

    let candidate = try stage("Updated", alternate: true)
    let candidateEvent = event(candidate, button: "Increment Updated")
    expect(text(candidate) == ["Updated 0"] && candidateEvent.identity != acceptedEvent.identity,
           "Changing the erased type must stage a fresh subtree even with the same inner key")
    expect(session.dispatch(candidate.presentation.token, candidateEvent) == .rejected,
           "A pending erased subtree must have no input authority")
    expect(session.finish(candidate.presentation.token, outcome: .canceled),
           "Cancellation must consume the candidate")
    increment("Updated", in: next, session: session)
    expect(text(try stage("Updated")) == ["Updated 2"], "Cancellation must preserve the accepted erased subtree")

    let replacement = try stage("Updated", alternate: true)
    accept(replacement, in: session)
    expect(session.dispatch(next.presentation.token, acceptedEvent) == .rejected,
           "The old erased subtree must lose input authority after replacement")
    increment("Updated", in: replacement, session: session)
    expect(text(try stage("Updated", alternate: true)) == ["Updated 1"],
           "The replacement handler must update the new subtree")
    let returned = try stage("Updated")
    expect(text(returned) == ["Updated 0"] && event(returned, button: "Increment Updated").identity != acceptedEvent.identity,
           "Returning to a retired erased type must allocate fresh state and identity")
    print("PASS erased view lifetime, canceled type change, and retired callback refusal")
}
