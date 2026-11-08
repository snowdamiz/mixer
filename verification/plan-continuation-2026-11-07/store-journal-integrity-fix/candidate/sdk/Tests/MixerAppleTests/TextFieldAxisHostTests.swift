import Testing
import MixerUI
import MixerApple

@MainActor
@Test func appleHostAdmitsVerticalFieldsAndKeepsCurrentEventBindings() throws {
    let document = MixerUI.TextField("title", "Title", value: "First line\nCafé 🏗️", action: "changed",
                                     onSubmit: "save", axis: .vertical).document(revision: 1)
    let host = try MixerUIHost(document: document)
    let identity = try #require(host.snapshot.identity(for: "title"))
    #expect(host.snapshot.document == document)
    let envelope = UIEventEnvelope(revision: 1, identity: identity, event: .textChange, value: .string("Edited\n漢字"))
    #expect(try host.route(envelope).value == .string("Edited\n漢字"))
    let updated = MixerUI.TextField("title", "Title", value: "Edited\n漢字", action: "new.changed",
                                    onSubmit: "new.save", axis: .vertical).document(revision: 2)
    try host.update(updated)
    #expect(host.snapshot.document == updated && host.snapshot.identity(for: "title") == identity)
    #expect(throws: UIRoutingError.staleRevision) { try host.route(envelope) }
    #expect(try host.route(UIEventEnvelope(revision: 2, identity: identity, event: .submit)).actionID == "new.save")
}

@MainActor
@Test func appleHostPreservesExplicitNarrowerAxisCapabilities() throws {
    let vertical = MixerUI.TextField("title", "Title", value: "First\nSecond", action: "changed", axis: .vertical)
        .document(revision: 1)
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) {
        try MixerUIHost(document: vertical, validator: UIValidator())
    }
    let horizontal = MixerUI.TextField("title", "Title", value: "Saved", action: "changed").document(revision: 1)
    let host = try MixerUIHost(document: horizontal, validator: UIValidator())
    let identity = try #require(host.snapshot.identity(for: "title"))
    let candidate = MixerUI.TextField("title", "Title", value: "First\nSecond", action: "changed", axis: .vertical)
        .document(revision: 2)
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) { try host.update(candidate) }
    #expect(host.snapshot.document == horizontal && host.snapshot.identity(for: "title") == identity)
    let envelope = UIEventEnvelope(revision: 1, identity: identity, event: .textChange, value: .string("Still editable"))
    #expect(try host.route(envelope).actionID == "changed")
}
