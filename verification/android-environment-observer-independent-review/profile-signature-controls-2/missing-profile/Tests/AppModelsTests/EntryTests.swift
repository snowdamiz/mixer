import Testing
import Foundation
@testable import AppModels
@testable import AppFeatures
import MixerUI
@Test func progressPreservesFraction() {
    #expect(ProjectProgress.fraction([Entry(title: "A", completed: true), Entry(title: "B")]) == 0.5)
    #expect(ProjectProgress.fraction([]) == 0)
}
@Test func draftRoundTrip() throws {
    let entry = Entry(title: "Inspect site", note: "Offline draft")
    #expect(try JSONDecoder().decode(Entry.self, from: JSONEncoder().encode(entry)) == entry)
    #expect(!Entry(title: "  ").isValid)
}
@Test func featureBuilds() { #expect(ProjectFeature.document(entries: []).root.id == "project") }
@Test func sharedDraftAddToggle() throws {
    var state = ProjectFeatureState()
    var reconciler = UIReconciler()
    func action(_ id: String, _ event: UIEventKind, _ value: UIValue) throws -> RoutedUIAction {
        let snapshot = try reconciler.currentSnapshot()
        return try snapshot.route(UIEventEnvelope(revision: snapshot.document.revision,
            identity: #require(snapshot.identity(for: id)), event: event, value: value))
    }
    try reconciler.apply(ProjectFeature.document(state: state, revision: 1))
    try ProjectFeature.handle(action("draft", .textChange, .string(" Café 東京 ")), state: &state)
    try reconciler.apply(ProjectFeature.document(state: state, revision: 2))
    try ProjectFeature.handle(action("add", .activate, .null), state: &state)
    #expect(state.entries.count == 1); #expect(state.entries[0].title == "Café 東京"); #expect(state.draft.isEmpty)
    try reconciler.apply(ProjectFeature.document(state: state, revision: 3))
    try ProjectFeature.handle(action("entry.\(state.entries[0].id.uuidString)", .valueChange, .bool(true)), state: &state)
    #expect(state.entries[0].completed)
}
