import Foundation
@_spi(S5SignedCompose) import MixerCapabilityActivation
import MixerUI
import MixerUpdates

@main enum Replay {
    static func main() async throws {
        let args = CommandLine.arguments
        guard args.count == 3 else { throw JourneyError("Expected signed assets and private state directory") }
        let directory = URL(fileURLWithPath: args[2], isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o700])
        let assets = URL(fileURLWithPath: args[1], isDirectory: true)
        let checks: [(String, @Sendable (SignedJourney) async throws -> Void)] = [
            ("provisional", refuseFirstFrame), ("committed", preserveCommittedSave), ("replacement", run),
        ]
        for (name, check) in checks {
            let state = directory.appendingPathComponent(name, isDirectory: true)
            try FileManager.default.createDirectory(at: state, withIntermediateDirectories: false,
                                                    attributes: [.posixPermissions: 0o700])
            let journey = SignedJourney(assets: assets, directory: state)
            do {
                try await check(journey)
            } catch {
                await journey.abort()
                throw error
            }
        }
    }

    private static func refuseFirstFrame(_ journey: SignedJourney) async throws {
        let prior = S5SignedPresentation()
        async let activation = journey.activate(.prior, presentation: prior, provisional: {})
        let initial = try await frame(prior, revision: 1)
        try require(prior.discard(initial.id), "Provisional frame cancellation refused")
        try require((try? await activation) == nil, "Canceled first frame earned health")
        try await journey.verifyProvisionalFailure()
        try require(!prior.present(initial.id) && !submit(prior, initial, "refused"),
                    "Provisional failure admitted stale receipt or input")
        await journey.abort()
        print("PASS first-frame cancellation fails closed with stale input and receipts refused")
    }

    private static func preserveCommittedSave(_ journey: SignedJourney) async throws {
        let prior = S5SignedPresentation()
        async let activation = journey.activate(.prior, presentation: prior, provisional: {})
        let initial = try await frame(prior, revision: 1)
        try require(prior.present(initial.id), "Initial frame refused")
        _ = try await activation
        let title = "Café e\u{301} \"東京\" 🧰"
        try require(submit(prior, initial, title), "Commit control refused")
        let saved = try await frame(prior, revision: 2)
        try require(prior.discard(saved.id), "Committed frame cancellation refused")
        try require(prior.deliveredEvents == 2, "Cancellation duplicated or lost guest events")
        try require(try await journey.finish() == Data(title.utf8), "Canceled draw changed committed bytes")
        print("PASS canceled post-Save draw retained actual committed UTF-8 after store reopen")
    }

    private static func run(_ journey: SignedJourney) async throws {
        let prior = S5SignedPresentation()
        async let first = journey.activate(.prior, presentation: prior, provisional: {})
        let initial = try await frame(prior, revision: 1)
        let draft = "Unpresented Café e\u{301} \"東京\" 🧰"
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
        let canceled = try await frame(candidate, revision: 2)
        try require(candidate.deliveredEvents == 2, "Expected exactly one draft and one Save delivery")
        try assertReadback(canceled, count: 1, title: draft)
        try require(!candidate.discard(UUID()) && candidate.discard(canceled.id), "Exact pending cancellation was not required")
        try await journey.verifyHealthy(.candidate)
        try require(!candidate.present(canceled.id) && !candidate.discard(canceled.id) && !submit(candidate, canceled, draft),
                    "Canceled frame retained authority")

        let secondCanceled = try await save(candidate, from: editor, count: 2, title: "Second unpresented 点検")
        try require(candidate.discard(secondCanceled.id), "Second cancellation refused")
        try await journey.verifyHealthy(.candidate)
        var shown = editor
        var finalTitle = ""
        for count in UInt64(3)...5 {
            finalTitle = "Inspection \(count) — e\u{301} \"点検\" 🔍"
            let next = try await save(candidate, from: shown, count: count, title: finalTitle)
            try require(candidate.present(next.id), "Saved frame \(count) refused")
            try require(!submit(candidate, shown, draft), "Superseded accepted ticket retained input")
            shown = next
        }
        print("PASS two canceled revisions preserved accepted input and three subsequent signed Unicode saves advanced exactly once")

        let refusedOwner = try await journey.refuseRollback()
        try require(refusedOwner == candidateID && candidate.deliveredEvents == 10,
                    "Refusal changed the accepted owner or delivered input")
        try require(!candidate.present(shown.id) && !candidate.discard(shown.id),
                    "Refusal changed the exact presentation receipt authority")
        finalTitle = "After refusal — e\u{301} \"点検\" 🔍"
        let savedAfterRefusal = try await save(candidate, from: shown, count: 6, title: finalTitle)
        try require(candidate.present(savedAfterRefusal.id), "Post-refusal Save frame refused")
        try await journey.verifyHealthy(.candidate)
        shown = savedAfterRefusal
        print("PASS invalid signature refused by the live store, same editor delivered a later Save to the signed guest")
        print("POST_REFUSAL_UTF8_SHA256 \(ReleaseVerifier.sha256(Data(finalTitle.utf8)))")

        let rollback = S5SignedPresentation()
        async let third = journey.activate(.rollback, presentation: rollback, provisional: {})
        let restored = try await frame(rollback, revision: 1)
        try require(!rollback.present(shown.id) && !candidate.present(secondCanceled.id) &&
                    !submit(candidate, shown, draft), "Rollback accepted retired input or receipt")
        try require(rollback.present(restored.id), "Exact rollback frame refused")
        let restoredID = try await third
        try require(restoredID != priorID && restoredID != candidateID &&
                    restored.snapshot.document.root.children[0].properties["value"] == .string("Prior editor"),
                    "Wrong restored owner")
        print("PASS rollback of the original signed artifact")
        try require(try await journey.finish() == Data(finalTitle.utf8), "Persisted UTF-8 changed")
        try require(!rollback.present(restored.id) && !submit(rollback, restored, draft),
                    "Retired rollback owner retained input or receipts")
        print("PASS exact persisted bytes after owner retirement and store reopen")
    }

    private static func save(_ presentation: S5SignedPresentation, from shown: S5SignedPresentation.Frame,
                             count: UInt64, title: String) async throws -> S5SignedPresentation.Frame {
        try require(submit(presentation, shown, title), "Accepted Save \(count) refused")
        let next = try await frame(presentation, revision: count + 1)
        try require(presentation.deliveredEvents == count * 2, "Save \(count) delivered extra or missing events")
        try assertReadback(next, count: count, title: title)
        return next
    }

    private static func assertReadback(_ frame: S5SignedPresentation.Frame, count: UInt64, title: String) throws {
        let nodes = frame.snapshot.document.root.children
        try require(nodes[0].properties["value"]?.string?.utf8.elementsEqual(title.utf8) == true &&
                    nodes[2].properties["text"]?.string?.utf8.elementsEqual("\(count): \(title)".utf8) == true,
                    "Guest readback did not carry exact typed bytes")
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
