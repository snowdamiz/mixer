import Foundation
@_spi(S5SignedCompose) import MixerCapabilityActivation
import MixerUI

@main enum Replay {
    static func main() async throws {
        let args = CommandLine.arguments
        guard args.count == 3 else { throw JourneyError("Expected signed assets and private state directory") }
        let directory = URL(fileURLWithPath: args[2], isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o700])
        let journey = SignedJourney(assets: URL(fileURLWithPath: args[1], isDirectory: true), directory: directory)
        do {
            try await run(journey)
        } catch {
            await journey.abort()
            throw error
        }
    }

    private static func run(_ journey: SignedJourney) async throws {
        let prior = S5SignedPresentation()
        async let first = journey.activate(.prior, presentation: prior, provisional: {})
        let initial = try await frame(prior, revision: 1)
        let draft = "Café e\u{301} \"東京\" 🧰"
        try require(!submit(prior, initial, draft), "Input accepted before queued acknowledgment")
        try require(!prior.present(UUID()), "Foreign frame receipt accepted")
        try require(prior.present(initial.id), "Exact prior frame refused")
        let priorID = try await first
        print("PASS signed prior after exact frame receipt")

        let candidate = S5SignedPresentation()
        async let second = journey.activate(.candidate, presentation: candidate, provisional: {})
        let editor = try await frame(candidate, revision: 1)
        try require(!prior.present(initial.id) && !submit(prior, initial, draft), "Retired owner accepted input or receipt")
        try require(candidate.present(editor.id), "Exact editor frame refused")
        let candidateID = try await second
        try require(candidateID != priorID, "Candidate did not replace prior owner")
        try require(submit(candidate, editor, draft), "Typed Save refused")
        try require(!submit(candidate, editor, draft), "Duplicate Save accepted")
        let saved = try await frame(candidate, revision: 2)
        try require(candidate.deliveredEvents == 2, "Expected exactly one draft and one Save delivery")
        try require(saved.snapshot.document.root.children[0].properties["value"]?.string?.utf8.elementsEqual(draft.utf8) == true &&
                    saved.snapshot.document.root.children[2].properties["text"]?.string?.utf8.elementsEqual("1: \(draft)".utf8) == true,
                    "Guest readback did not carry exact typed bytes")
        try require(candidate.present(saved.id), "Saved frame refused")
        print("PASS one draft, one Save, and exact Unicode document readback")

        let rollback = S5SignedPresentation()
        async let third = journey.activate(.rollback, presentation: rollback, provisional: {})
        let restored = try await frame(rollback, revision: 1)
        try require(!rollback.present(saved.id) && !submit(candidate, saved, draft), "Rollback accepted retired input or receipt")
        try require(rollback.present(restored.id), "Exact rollback frame refused")
        let restoredID = try await third
        try require(restoredID != priorID && restoredID != candidateID &&
                    restored.snapshot.document.root.children[0].properties["value"] == .string("Prior editor"),
                    "Wrong restored owner")
        print("PASS damaged signature refusal and rollback of the original signed artifact")
        try require(try await journey.finish() == Data(draft.utf8), "Persisted UTF-8 changed")
        print("PASS exact persisted bytes after owner retirement and store reopen")
    }

    private static func frame(_ presenter: S5SignedPresentation, revision: UInt64) async throws -> S5SignedPresentation.Frame {
        let deadline = ContinuousClock.now + .seconds(7)
        while ContinuousClock.now < deadline {
            presenter.pump()
            if let frame = presenter.frame(), frame.snapshot.document.revision == revision { return frame }
            try await Task.sleep(for: .milliseconds(10))
        }
        throw JourneyError("No revision \(revision) frame")
    }

    private static func submit(_ presenter: S5SignedPresentation, _ frame: S5SignedPresentation.Frame, _ title: String) -> Bool {
        guard let editor = frame.snapshot.identity(for: "title"), let save = frame.snapshot.identity(for: "save") else { return false }
        let revision = frame.snapshot.document.revision
        return presenter.submit(.init(revision: revision, identity: editor, event: .textChange, value: .string(title)),
                                save: .init(revision: revision, identity: save, event: .activate), from: frame.id)
    }

    private static func require(_ condition: Bool, _ failure: String) throws {
        guard condition else { throw JourneyError(failure) }
    }
}
