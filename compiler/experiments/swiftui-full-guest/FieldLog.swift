#if os(WASI) && !ICU_CONTROL
import FoundationEssentials
#else
import Foundation
#endif
import Observation

struct TaskRecord: Codable, Equatable, Identifiable {
    let id: UUID
    let created: Date
    var title: String
    let site: String
}

@MainActor
final class Workspace: Observable {
    private let registrar = ObservationRegistrar()
    private var storage: [TaskRecord] = []

    var records: [TaskRecord] {
        get {
            registrar.access(self, keyPath: \.records)
            return storage
        }
        set {
            registrar.withMutation(of: self, keyPath: \.records) {
                storage = newValue
            }
        }
    }

    var selected: UUID?
    var draft = ""
    private var saved: Data?

    func load() async {
        await Task.yield()
        records = (0..<1_000).map { index in
            let id = UUID(uuid: (0, 0, 0, 0, 0, 0, 0x40, 0, 0x80, 0, 0, 0, 0, 0,
                                 UInt8(index >> 8), UInt8(truncatingIfNeeded: index)))
            return TaskRecord(
                id: id,
                created: Date(timeIntervalSince1970: 1_790_000_000 + Double(index) * 60),
                title: "Inspection \(index)",
                site: ["North yard", "Pump station", "Loading bay"][index % 3]
            )
        }
    }

    func open(_ id: UUID) {
        guard let record = records.first(where: { $0.id == id }) else { return }
        selected = id
        draft = record.title
    }

    func save() {
        guard let position = records.firstIndex(where: { $0.id == selected }),
              Self.accepts(draft)
        else { return }

        var record = records[position]
        record.title = draft
        do {
            let bytes = try JSONEncoder().encode(record)
            records[position] = try JSONDecoder().decode(TaskRecord.self, from: bytes)
            saved = bytes
            selected = nil
        } catch {
            preconditionFailure("Task record must round-trip through FoundationEssentials")
        }
    }

    func reopenSaved() throws -> TaskRecord {
        guard let saved else { preconditionFailure("A record must be saved before reopening") }
        let record = try JSONDecoder().decode(TaskRecord.self, from: saved)
        open(record.id)
        return record
    }

    private static func accepts(_ title: String) -> Bool {
        #if UPDATE
        return title.utf8.count <= 100 && title.contains { !$0.isWhitespace }
        #else
        return !title.isEmpty
        #endif
    }
}

// The spike renders these values offscreen. The product SwiftUI subset and
// document wire have separate owners.
@MainActor
protocol View {}

struct TaskView<Content: View>: View {
    let content: Content
    let action: @MainActor () async -> Void

    func appear() async {
        await Task { await action() }.value
    }
}

extension View {
    func task(_ action: @escaping @MainActor () async -> Void) -> TaskView<Self> {
        TaskView(content: self, action: action)
    }
}

struct Binding<Value> {
    let get: @MainActor () -> Value
    let set: @MainActor (Value) -> Void
}

struct TextField: View {
    let title: String
    let text: Binding<String>
}

struct Button: View {
    let title: String
    let action: @MainActor () -> Void
}

struct List: View {
    let rows: [Button]
}

struct FieldLogList: View {
    let workspace: Workspace

    var body: TaskView<FieldLogList> {
        task { await workspace.load() }
    }

    func frame() -> List {
        List(rows: workspace.records.map { record in
            Button(title: "\(record.title) · \(record.site)") {
                workspace.open(record.id)
            }
        })
    }
}

struct FieldLogEditor: View {
    let workspace: Workspace

    var title: TextField {
        TextField(title: "Title", text: Binding(get: { workspace.draft }, set: { workspace.draft = $0 }))
    }

    var save: Button {
        #if UPDATE
        Button(title: "Save inspection", action: workspace.save)
        #else
        Button(title: "Save", action: workspace.save)
        #endif
    }
}

@MainActor
final class Journey {
    struct Result: Codable {
        var initialCount = 0
        var loadedCount = 0
        var firstRow = ""
        var lastRow = ""
        var initialTitle = ""
        var saveLabel = ""
        var blankRejected = false
        var editedTitle = ""
        var reopenedTitle = ""
        var observedSave = false
        var id = ""
        var created: Double = 0
    }

    private let workspace: Workspace
    private let list: TaskView<FieldLogList>
    private let editor: FieldLogEditor
    private(set) var result: Result

    init() {
        let workspace = Workspace()
        self.workspace = workspace
        list = FieldLogList(workspace: workspace).body
        editor = FieldLogEditor(workspace: workspace)
        result = Result(initialCount: list.content.frame().rows.count)
    }

    func load() async {
        await list.appear()
        let rows = list.content.frame().rows
        precondition(rows.count == 1_000)
        result.loadedCount = rows.count
        result.firstRow = rows[0].title
        result.lastRow = rows[999].title
    }

    func openRecord() {
        list.content.frame().rows[527].action()

        result.initialTitle = editor.title.text.get()
        result.saveLabel = editor.save.title
    }

    func tryBlankSave() {
        #if UPDATE
        editor.title.text.set("  ")
        #else
        editor.title.text.set("")
        #endif
        editor.save.action()
        result.blankRejected = workspace.selected != nil
    }

    func saveEdit() {
        let edited = "Pompé inspection 東京"
        editor.title.text.set(edited)
        result.editedTitle = editor.title.text.get()
        let observation = SaveObservation()
        withObservationTracking {
            _ = list.content.frame()
        } onChange: {
            MainActor.assumeIsolated { observation.wasCalled = true }
        }
        editor.save.action()
        result.observedSave = observation.wasCalled
    }

    func reopen() throws {
        let reopened = try workspace.reopenSaved()
        precondition(workspace.selected == reopened.id)
        result.reopenedTitle = editor.title.text.get()
        result.id = reopened.id.uuidString
        result.created = reopened.created.timeIntervalSince1970
    }
}

@MainActor
private final class SaveObservation {
    var wasCalled = false
}
