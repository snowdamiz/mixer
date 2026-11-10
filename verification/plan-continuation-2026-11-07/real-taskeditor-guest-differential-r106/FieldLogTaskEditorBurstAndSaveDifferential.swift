import Foundation
import FieldLogFeatures
import MixerCore

private struct Save: Codable, Equatable, Sendable {
    let title: String
    let responsible: String
}

private actor AppSaveRecorder {
    private var saves: [Save] = []

    func save(_ title: String, _ responsible: String) async -> TaskSaveResult {
        await Task.yield()
        saves.append(Save(title: title, responsible: responsible))
        return .saved
    }

    func snapshot() -> [Save] { saves }
}

@MainActor private final class Observations {
    var states: [TaskEditorState] = []
}

private enum FixtureFailure: Error { case mismatch(String) }

private func require(_ condition: Bool, _ message: String) throws {
    if !condition { throw FixtureFailure.mismatch(message) }
}

private struct State: Codable {
    let title: String
    let responsible: String
    let saving: Bool
    let saved: Bool
    let failure: String?
    let canSubmit: Bool
}

private struct Receipt: Codable {
    let test: String
    let status: String
    let finalState: State
    let saves: [Save]
    let saveCount: Int
    let completionTransitions: Int
    let observerDeliveries: Int
    let closedSubmitRejected: Bool
}

@main struct FieldLogTaskEditorBurstAndSaveDifferential {
    @MainActor static func main() async throws {
        let recorder = AppSaveRecorder()
        let editor = try TaskEditor { title, responsible in
            await recorder.save(title, responsible)
        }
        let observations = Observations()
        let token = editor.observe { observations.states.append($0) }
        try require(!editor.state.canSubmit, "empty editor can submit")
        try editor.submit()
        try require(!editor.state.saving, "empty submit launched a save")

        let finalTitle = " \nInspect 🛠️ gate\nبوابة · cafe\u{301}\n "
        let finalResponsible = " Zoë\n李 · مسؤول "
        for (title, responsible) in [
            ("I", "Z"), ("Inspect 🛠️", "Zoë"),
            ("Inspect 🛠️ gate\nبوابة", "Zoë\n李"),
            (finalTitle, finalResponsible)
        ] {
            try editor.changeTitle(title)
            try editor.changeResponsible(responsible)
        }
        try require(editor.state.canSubmit, "valid burst cannot submit")
        try editor.submit()
        try require(editor.state.saving && !editor.state.saved, "submit did not enter saving")
        try editor.changeTitle("must be ignored while saving")
        try editor.changeResponsible("must also be ignored")
        try editor.submit()
        try require(editor.state.title == finalTitle && editor.state.responsible == finalResponsible,
                    "in-flight edit changed the submitted state")

        await editor.waitForSave()
        let saves = await recorder.snapshot()
        try require(saves == [Save(title: finalTitle, responsible: finalResponsible)],
                    "save payload/count differs from the last burst")
        let saved = editor.state
        try require(saved.title == finalTitle && saved.responsible == finalResponsible &&
                    saved.saved && !saved.saving && saved.failure == nil && !saved.canSubmit,
                    "durable closure completion did not reach final feature state")
        let completionTransitions = zip(observations.states, observations.states.dropFirst())
            .filter { $0.0.saving && !$0.1.saving && $0.1.saved }.count
        try require(completionTransitions == 1, "effect did not complete exactly once")
        try editor.changeTitle("must be ignored after save")
        try editor.submit()
        await editor.waitForSave()
        let finalSaves = await recorder.snapshot()
        try require(editor.state == saved && finalSaves == saves, "saved editor resubmitted or mutated")
        editor.removeObserver(token)
        try editor.close()
        var closedSubmitRejected = false
        do { try editor.submit() }
        catch LifecycleError.featureNotRunning { closedSubmitRejected = true }
        try require(closedSubmitRejected, "closed editor accepted submit")

        let receipt = Receipt(test: "FieldLogTaskEditorBurstAndSaveDifferential", status: "passed",
            finalState: State(title: saved.title, responsible: saved.responsible,
                saving: saved.saving, saved: saved.saved, failure: saved.failure, canSubmit: saved.canSubmit),
            saves: finalSaves, saveCount: finalSaves.count, completionTransitions: completionTransitions,
            observerDeliveries: observations.states.count, closedSubmitRejected: closedSubmitRejected)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        print(String(decoding: try encoder.encode(receipt), as: UTF8.self))
    }
}
