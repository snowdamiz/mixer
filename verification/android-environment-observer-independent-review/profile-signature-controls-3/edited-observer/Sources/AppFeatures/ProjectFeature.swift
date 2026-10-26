import Foundation
import AppModels
import MixerUI
public struct ProjectFeatureState: Equatable, Sendable {
    public var entries: [Entry]
    public var draft: String
    public init(entries: [Entry] = [], draft: String = "") { self.entries = entries; self.draft = draft }
}
public enum ProjectFeatureError: Error { case invalidAction, invalidDraft, entryLimit }
public enum ProjectFeature {
    // Compatible read-only surface retained for the iOS starter.
    public static func document(entries: [Entry], revision: UInt64 = 0) -> UIDocument {
        UIDocument(schemaVersion: 1, revision: revision, root: UINode(
            id: "project", kind: .vStack,
            properties: [:], children: [
                UINode(id: "title", kind: .text, properties: ["text": .string("Your project")]),
                UINode(id: "progress", kind: .text, properties: ["text": .string("\(entries.filter(\.completed).count) of \(entries.count) completed")])
            ]
        ))
    }
    public static func document(state: ProjectFeatureState, revision: UInt64 = 0) -> UIDocument {
        MixerUI.Navigation("project", title: "Your project") {
            MixerUI.List("entries") {
                MixerUI.Section("editor", title: "Entries") {
                    MixerUI.Text("progress", "\(state.entries.filter(\.completed).count) of \(state.entries.count) completed")
                    MixerUI.TextField("draft", "New entry", value: state.draft, action: "draft.change", onSubmit: "entry.add")
                    MixerUI.Button("add", "Add entry", action: "entry.add")
                        .disabled(state.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || state.entries.count >= 100)
                }
                MixerUI.Section("items", title: "Project entries") {
                    for entry in state.entries {
                        MixerUI.Toggle("entry.\(entry.id.uuidString)", entry.title, value: entry.completed, action: "entry.toggle")
                    }
                }
            }
        }.document(revision: revision)
    }
    public static func handle(_ action: RoutedUIAction, state: inout ProjectFeatureState) throws {
        switch (action.actionID, action.value) {
        case ("draft.change", .string(let value)):
            guard action.nodeID == "draft", value.utf8.count <= 16_384 else { throw ProjectFeatureError.invalidAction }
            state.draft = value.uppercased()
        case ("entry.add", .null):
            guard action.nodeID == "add" || action.nodeID == "draft" else { throw ProjectFeatureError.invalidAction }
            let title = state.draft.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !title.isEmpty else { throw ProjectFeatureError.invalidDraft }
            guard state.entries.count < 100 else { throw ProjectFeatureError.entryLimit }
            state.entries.append(Entry(title: title)); state.draft = ""
        case ("entry.toggle", .bool(let completed)):
            guard let index = state.entries.firstIndex(where: { "entry.\($0.id.uuidString)" == action.nodeID }) else { throw ProjectFeatureError.invalidAction }
            state.entries[index].completed = completed
        default: throw ProjectFeatureError.invalidAction
        }
    }
}
