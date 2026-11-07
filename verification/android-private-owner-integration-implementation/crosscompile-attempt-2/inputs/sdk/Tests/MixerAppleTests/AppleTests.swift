import Testing
import MixerUI
import MixerApple
import SwiftUI

@MainActor
@Test func appleHostPreservesDisplayAndRejectsStaleCallbacks() throws {
    let document = MixerUI.Button("save", "Save", action: "entry.save").document(revision: 1)
    let host = try MixerUIHost(document: document)
    let identity = try #require(host.snapshot.identity(for: "save"))
    let envelope = UIEventEnvelope(revision: 1, identity: identity, event: .activate)
    #expect(try host.route(envelope).actionID == "entry.save")
    let invalid = MixerUI.VStack("root") { MixerUI.Text("duplicate", "A"); MixerUI.Text("duplicate", "B") }.document(revision: 2)
    #expect(throws: UIValidationError.duplicateIdentity("duplicate")) { try host.update(invalid) }
    #expect(host.snapshot.document == document)
    try host.update(MixerUI.Button("save", "Delete", action: "entry.delete").document(revision: 2))
    #expect(host.snapshot.identity(for: "save") == identity)
    #expect(throws: UIRoutingError.staleRevision) { try host.route(envelope) }
    #expect(try host.route(UIEventEnvelope(revision: 2, identity: identity, event: .activate)).actionID == "entry.delete")
}

@MainActor
@Test func macOSNativeRendererCreatesNonemptyImage() throws {
    let document = MixerUI.VStack("editor", alignment: .leading) {
        MixerUI.Text("title", "Inspection", style: .headline)
        MixerUI.TextField("notes", "Notes", value: "Roof access clear", action: "notes.changed")
        MixerUI.Toggle("done", "Complete", value: true, action: "done.changed")
        MixerUI.Button("save", "Save draft", action: "entry.save")
    }.document(revision: 1)
    let host = try MixerUIHost(document: document)
    let renderer = ImageRenderer(content: MixerNativeView(host: host, onAction: { _ in }).frame(width: 400, height: 240))
    #expect(renderer.nsImage != nil)
}
