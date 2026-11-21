import Foundation
import MixerUI

/// Executed against the two historical SDK and FieldLog source pairs.
@main struct EditorOracle {
    @MainActor static func main() async throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let output = URL(fileURLWithPath: CommandLine.arguments[1])
        var documents: [UIDocument] = []
        let accent = "Line one\ne\u{301} 🧑🏽‍🔧"
        let composed = "Line one\n\u{e9} 🧑🏽‍🔧"
        let edits = try TaskEditorPresentation { _, _ in fatalError("Unexpected Save") }
        documents.append(edits.snapshot.render.document)
        for title in ["Inspect pump P-17", accent, composed] {
            try edits.send(nodeID: "task.title", event: .textChange, value: .string(title))
            documents.append(edits.snapshot.render.document)
        }
        try edits.send(nodeID: "task.cancel", event: .activate)
        precondition(edits.snapshot.outcome == .cancelled && edits.snapshot.navigation.routes.isEmpty)
        documents.append(edits.snapshot.render.document)
        try edits.close()

        let save = try TaskEditorPresentation { title, responsible in
            precondition(title == "Inspect pump P-17" && responsible.isEmpty)
            return .saved
        }
        documents.append(save.snapshot.render.document)
        try save.send(nodeID: "task.title", event: .textChange, value: .string("Inspect pump P-17"))
        documents.append(save.snapshot.render.document)
        try save.send(nodeID: "task.save", event: .activate)
        precondition(save.snapshot.state.saving && save.snapshot.navigation.routes.count == 1)
        documents.append(save.snapshot.render.document)
        await save.waitForSave()
        precondition(save.snapshot.outcome == .saved && save.snapshot.navigation.routes.isEmpty)
        documents.append(save.snapshot.render.document)
        try save.close()
        try encoder.encode(documents.map(encoder.encode)).write(to: output, options: .withoutOverwriting)
    }
}
