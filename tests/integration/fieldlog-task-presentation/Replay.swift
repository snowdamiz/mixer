import FieldLogAndroid
import FieldLogFeatures
import FieldLogModels
import FieldLogStorage
import Foundation
import MixerAndroid
import MixerUI

private struct ReplayFailure: Error, CustomStringConvertible {
    let description: String
}

private func check(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
    if try !condition() { throw ReplayFailure(description: message) }
}

private func expectRefusal<E: Error & Equatable>(_ expected: E, _ action: () throws -> Void) throws {
    do {
        try action()
    } catch let received as E where received == expected {
        return
    }
    throw ReplayFailure(description: "Expected refusal: \(expected)")
}

@MainActor private final class Surface: AndroidUINativeSurface {
    let profile = AndroidUIProfile.measuredMultilineLongNotesV4
    var capabilities: AndroidUICapabilities { profile.capabilities }
    private(set) var owner: UUID?
    private(set) var frame: AndroidUIFrame?

    func activate(owner: UUID) throws {
        try check(self.owner == nil, "Surface activated twice")
        self.owner = owner
    }

    func install(_ frame: AndroidUIFrame) throws {
        try check(owner == frame.owner, "Frame delivered for a different owner")
        self.frame = frame
    }

    func revoke(owner: UUID) {
        if self.owner == owner {
            self.owner = nil
            frame = nil
        }
    }

    func event(_ nodeID: String, _ kind: UIEventKind = .activate, _ value: UIValue = .null) throws -> UIEventEnvelope {
        guard let snapshot = frame?.snapshot, let identity = snapshot.identity(for: nodeID) else {
            throw ReplayFailure(description: "Missing installed control \(nodeID)")
        }
        return UIEventEnvelope(revision: snapshot.document.revision, identity: identity, event: kind, value: value)
    }

    func node(_ id: String) throws -> UINode {
        guard let root = frame?.snapshot.document.root else {
            throw ReplayFailure(description: "No installed frame")
        }
        var pending = [root]
        while let node = pending.popLast() {
            if node.id == id { return node }
            pending.append(contentsOf: node.children)
        }
        throw ReplayFailure(description: "No installed node \(id)")
    }
}

@main @MainActor private enum Replay {
    static func main() async throws {
        let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
        let storage = directory.appendingPathComponent("FieldLog", isDirectory: true)
        let file = storage.appendingPathComponent("workspace.json")
        let title = "Café 東京 🧪\nInspect facade — e\u{301}"
        let composed = title.precomposedStringWithCanonicalMapping
        let responsible = "  Zoë  "
        let (oldOwner, discardedEvent, original) = try await withApplication(directory) { app, surface, owner in
            let original = try Data(contentsOf: file)
            try checkFieldContract(surface)
            let disabledSave = try surface.event("task.save")
            let stale = try surface.event("task.title", .textChange, .string("Obsolete"))
            let seed = try surface.event("task.title", .textChange, .string("Ready"))
            try expectRefusal(UIRoutingError.disabledNode) { try send(app, owner, [seed, disabledSave]) }
            try send(app, owner, seed)
            try expectRefusal(UIRoutingError.staleRevision) { try send(app, owner, stale) }

            let blank = try surface.event("task.title", .textChange, .string(" \n "))
            try send(app, owner, [blank, surface.event("task.save")])
            try await app.settle()
            try check(app.presentation.state.title == " \n " && !app.presentation.state.canSubmit,
                      "Clearing before an admitted Save should leave a blank, unsaved editor")
            try check(try Data(contentsOf: file) == original, "Blank batch changed durable state")

            try send(app, owner, surface.event("task.title", .textChange, .string(composed)))
            try send(app, owner, surface.event("task.title", .textChange, .string(title)))
            try send(app, owner, surface.event("task.responsible", .textChange, .string(responsible)))
            try check(try surface.node("task.title").properties["value"]?.string?.utf8.elementsEqual(title.utf8) == true,
                      "Reseeding a later edit changed the actual Unicode bytes")
            try send(app, owner, surface.event("workspace.queue"))
            try send(app, owner, surface.event("workspace.back"))
            try check(try surface.node("task.title").properties["value"]?.string?.utf8.elementsEqual(title.utf8) == true,
                      "Queue navigation discarded editor text")
            try check(try Data(contentsOf: file) == original, "Unsubmitted editor text reached disk")
            return (owner, try surface.event("task.save"), original)
        }
        try check(try Data(contentsOf: file) == original, "Closing an unsaved editor wrote to disk")
        print("discard: title selector, label, axis and binding preserved; blank batch, stale revision, queue return and owner close passed; zero durable writes")

        let saved = try await withApplication(directory) { app, surface, owner in
            try checkFieldContract(surface)
            try check(app.presentation.state.title.isEmpty && app.presentation.workspace.tasks.isEmpty,
                      "Discarded editor survived an owner reopen")
            try expectRefusal(AndroidUIHostError.staleOwner) { try send(app, oldOwner, discardedEvent) }
            try send(app, owner, surface.event("task.title", .textChange, .string("Seed for Save")))
            let before = app.presentation.snapshot.document.revision
            let edit = try surface.event("task.title", .textChange, .string("  " + title + "  "))
            let person = try surface.event("task.responsible", .textChange, .string(responsible))
            let save = try surface.event("task.save")
            try expectRefusal(PublicHostError.action) { try send(app, owner, [edit, save, person]) }
            try check(app.presentation.snapshot.document.revision == before, "Refused batch published a revision")
            try check(try Data(contentsOf: file) == original, "Refused batch wrote to disk")

            var publications = 0
            let unsubscribe = app.presentation.observe { _ in publications += 1 }
            defer { unsubscribe() }
            try send(app, owner, [edit, person, save])
            try check(publications == 1 && app.presentation.state.saving, "Expected one staged frame before the save effect")
            try check(try Data(contentsOf: file) == original, "Save wrote before the staged frame")
            try await app.settle()
            try check(publications == 2 && app.presentation.state.saved, "Expected one durable completion frame")
            let baseline = try JSONDecoder().decode(Workspace.self, from: original)
            let committed = try JSONDecoder().decode(Workspace.self, from: Data(contentsOf: file))
            guard let task = committed.tasks.first, let event = committed.outbox.last else {
                throw ReplayFailure(description: "Missing durable task or outbox event")
            }
            try check(committed == app.presentation.workspace && committed.revision == baseline.revision + 1
                && committed.tasks.count == 1 && task.title.utf8.elementsEqual(title.utf8)
                && task.responsible.utf8.elementsEqual(responsible.utf8)
                && committed.outbox.count == baseline.outbox.count + 1
                && Array(committed.outbox.dropLast()) == baseline.outbox
                && event.kind == .taskSaved && event.recordID == task.id,
                "Submit did not persist exactly one task and corresponding taskSaved")
            try send(app, owner, surface.event("task.new"))
            try checkFieldContract(surface)
            try check(app.presentation.state.title.isEmpty && app.presentation.state.responsible.isEmpty,
                      "New task did not reset the form")
            try expectRefusal(UIRoutingError.staleRevision) { try send(app, owner, save) }
            return committed
        }

        let bytes = try Data(contentsOf: file)
        let repository = try WorkspaceRepository(directory: storage)
        let cold = await repository.snapshot()
        await repository.close()
        try check(cold == saved, "Cold repository read differs from committed state")
        try await withApplication(directory) { app, surface, _ in
            try check(app.presentation.workspace == saved, "Cold checklist lost the task")
            let taskID = try saved.tasks.first.map { "task." + $0.id.uuidString.lowercased() + ".title" }
                .unwrap("Missing reopened task")
            try check(try surface.node(taskID).properties["text"]?.string?.contains(title) == true,
                      "Cold checklist did not render the saved title")
        }
        try check(try Data(contentsOf: file) == bytes, "Reopen or stale action changed disk bytes")
        print("submit: one staged frame, one completion frame, one repository revision, one task and one taskSaved; exact Unicode and responsible bytes; cold repository and checklist reopen passed")

        let shared = try TaskEditorPresentation { _, _ in .failed("Cancel admitted a save") }
        try shared.send(nodeID: "task.title", event: .textChange, value: .string("Cancel this title"))
        try shared.send(nodeID: "task.cancel", event: .activate)
        try check(shared.snapshot.outcome == .cancelled && shared.snapshot.navigation.routes.isEmpty,
                  "Shared presentation Cancel did not dismiss")
        try shared.close()
        print("shared form: explicit Cancel still dismisses")
    }

    private static func checkFieldContract(_ surface: Surface) throws {
        let title = try surface.node("task.title")
        let person = try surface.node("task.responsible")
        let save = try surface.node("task.save")
        try check(title.kind == .textField && title.properties["axis"] == .string("vertical")
            && title.properties["label"] == .string("What needs to happen?")
            && title.properties["accessibilityIdentifier"] == .string("task-title")
            && title.actions.count == 1 && title.actions[0].id == "task.title.change"
            && title.actions[0].event == .textChange
            && person.properties["accessibilityIdentifier"] == .string("task-responsible")
            && save.properties["accessibilityIdentifier"] == .string("task-save")
            && save.properties["label"] == .string("Save"), "Ordinary Android field contract changed")
    }

    private static func withApplication<Result>(
        _ directory: URL, _ body: @MainActor (PublicAndroidApplication, Surface, UUID) async throws -> Result
    ) async throws -> Result {
        let surface = Surface()
        let app = try await PublicAndroidApplication(surface: surface, selectedProfile: surface.profile.rawValue, directory: directory)
        let result: Result
        do {
            guard let owner = surface.owner else { throw ReplayFailure(description: "Owner was not installed") }
            result = try await body(app, surface, owner)
        } catch {
            await app.close()
            throw error
        }
        await app.close()
        try check(surface.owner == nil && surface.frame == nil, "Surface retained a closed owner")
        return result
    }

    private static func send(_ app: PublicAndroidApplication, _ owner: UUID, _ event: UIEventEnvelope) throws {
        try app.send(owner: owner, originalEnvelope: JSONEncoder().encode(event))
    }

    private static func send(_ app: PublicAndroidApplication, _ owner: UUID, _ events: [UIEventEnvelope]) throws {
        try app.sendBatch(owner: owner, originalEnvelopes: JSONEncoder().encode(events))
    }
}

private extension Optional {
    func unwrap(_ message: String) throws -> Wrapped {
        guard let value = self else { throw ReplayFailure(description: message) }
        return value
    }
}
