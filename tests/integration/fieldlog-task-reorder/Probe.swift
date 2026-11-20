import FieldLogInstalledGuest
import FieldLogModels
import FieldLogStorage
import Foundation
@testable import MixerCapabilityActivation
@_spi(GuestUIV1) import MixerGuest
import MixerUI
import MixerUpdates

@main struct RowProbe {
    @MainActor static func main() async throws {
        let args = CommandLine.arguments
        guard args.count == 6, let installation = UUID(uuidString: args[3]),
              let sequence = Int(args[4]), (1...3).contains(sequence) else {
            throw failure("Invalid probe arguments")
        }
        let material = URL(fileURLWithPath: args[1], isDirectory: true)
        let work = URL(fileURLWithPath: args[2], isDirectory: true)
        let store = work.appendingPathComponent("FieldLog")
        let file = store.appendingPathComponent("workspace.json")
        let seed = try CalculationFixture.readSeed(material.appendingPathComponent("calculation-seed.json"))
        let original = try JSONDecoder().decode(Workspace.self, from: seed)
        let originalRows = original.tasks(for: CalculationFixture.projectID)
        let originalOrder = originalRows.map(\.id)
        let movedOrder = [originalOrder[0], CalculationFixture.taskID, CalculationFixture.predecessor]
        let offline = args[5] == "offline"
        let repository = try WorkspaceRepository(directory: store, expectedSeed: seed, requireExistingSeed: false)
        let before = try await repository.readCommittedSnapshot()
        let beforeBytes = try Data(contentsOf: file)
        try check(before, original: original, order: sequence == 3 ? movedOrder : originalOrder, moved: sequence == 3)
        guard sequence == 3 || beforeBytes == seed,
              let target = originalRows.last, target.id == CalculationFixture.taskID,
              originalOrder[1] == CalculationFixture.predecessor else { throw failure("Wrong fixture task or seed") }

        let storage = try CalculationFixture.storage(repository: repository, task: target)
        let checklist = try await FieldLogSignedTask.open(storage: storage, material: material,
            directory: work.appendingPathComponent("signed-checklist"),
            bundleID: CalculationFixture.bundleID, installation: installation)
        let result: Result<[String: Any], Error>
        do {
            let model = checklist.owner.presentation
            guard let attachment = model.claimNativeAttachment() else { throw failure("No display attachment") }
            defer { model.detachNativeAttachment(attachment) }
            let label = try await checklist.start()
            guard label == (offline ? "Using saved checklist release" : "Signed checklist") else {
                throw failure("Unexpected origin outcome: \(label)")
            }
            try await until("No first frame") { model.state == .displaying(revision: 1) }
            let phaseOrder = sequence == 3 ? movedOrder : originalOrder
            let action = try inspect(model, order: phaseOrder, rows: originalRows, actionExpected: sequence == 2)
            guard let ticket = model.nativeDisplayTicket(attachment: attachment), model.observeNativeDisplay(ticket) else {
                throw failure("First frame witness was refused")
            }
            try await until("Candidate did not become healthy") {
                let state = await checklist.recovery()
                return state.acceptedSequence == sequence && state.healthy == state.activation.candidateID
                    && state.activation.phase == .healthyGuest
            }
            if let action, let host = model.renderHost {
                try await until("Action readiness") { model.inputEnabled }
                let fire = model.actionHandler(host: host, attachment: attachment)
                fire(action)
                try await until("No refreshed frame after Move up") { model.state == .displaying(revision: 2) }
                _ = try inspect(model, order: movedOrder, rows: originalRows, actionExpected: false)
                guard model.lastEventResult?.sequence == 1, model.lastEventResult?.outcome == .delivered else {
                    throw failure("Expected one delivered native action")
                }
                // A retained renderer callback cannot act on its previous frame.
                fire(action)
                // The exact previous command and a command with a fresh revision
                // after the move are both denied by transaction preconditions.
                for revision in [before.revision, before.revision + 1] {
                    let command = Data(String(revision).utf8).base64EncodedString()
                    let result = try await storage.put(.init(namespace: "fieldlog-task-v1",
                        key: "move-" + target.id.uuidString, valueBase64: command),
                        maximumTotalBytes: 20, maximumEntries: 1)
                    guard !result.committed else { throw failure("Repeated Move up committed") }
                }
            }
            let after = try await repository.readCommittedSnapshot()
            let moved = sequence != 1
            let afterOrder = moved ? movedOrder : originalOrder
            try check(after, original: original, order: afterOrder, moved: moved)
            let afterBytes = try Data(contentsOf: file)
            guard sequence == 2 || beforeBytes == afterBytes else { throw failure("Launch rewrote the workspace") }
            let health = await checklist.recovery()
            guard let candidate = health.healthy, let launch = health.activation.launchID else {
                throw failure("Missing healthy activation identity")
            }
            result = .success(["pid": Int(getpid()), "sequence": sequence, "label": label, "candidate": candidate,
                "previous": health.previousHealthy as Any? ?? NSNull(), "launchID": launch,
                "order": afterOrder.map(\.uuidString), "revision": after.revision, "outbox": after.outbox.count,
                "openDraft": after.restoration.openDraftID!.uuidString,
                "workspaceSHA256": ReleaseVerifier.sha256(afterBytes), "guestActions": action == nil ? 0 : 1])
        } catch { result = .failure(error) }
        let retired = await checklist.close()
        let committedBytes = try Data(contentsOf: file)
        await repository.close()
        let closed = await checklist.recovery()
        guard retired, closed.closed, !closed.incompleteAttempt, !closed.activation.cleanupPending,
              try Data(contentsOf: file) == committedBytes else { throw failure("Retirement changed durable state") }
        let observation = try result.get()
        guard observation["workspaceSHA256"] as? String == ReleaseVerifier.sha256(committedBytes) else {
            throw failure("Workspace changed after the verified checkpoint")
        }
        let bytes = try JSONSerialization.data(withJSONObject: observation, options: [.sortedKeys])
        print(String(decoding: bytes, as: UTF8.self))
    }

    @MainActor private static func inspect(_ model: GuestUIPresentation, order: [UUID],
                                          rows: [WorkTask], actionExpected: Bool) throws -> RoutedUIAction? {
        guard let snapshot = model.renderHost?.snapshot else { throw failure("No guest document") }
        let root = snapshot.document.root
        let actual = root.children.filter { $0.id.hasPrefix("row-") }
        guard root.id == "fieldlog-rows", root.kind == .vStack,
              actual.map(\.id) == order.map({ "row-" + $0.uuidString }),
              actual.map({ $0.children.first?.properties["text"]?.string }) ==
                order.map({ id in rows.first(where: { $0.id == id })?.title }) else {
            throw failure("Stable row identity, order or title differs")
        }
        let buttons = actual.flatMap { $0.children.filter { $0.kind == .button } }
        guard buttons.count == (actionExpected ? 1 : 0) else { throw failure("Unexpected button count") }
        guard let button = buttons.first else { return nil }
        let input = CalculationFixture.actionNode
        guard actual.last?.children.last?.id == input,
              button.properties["accessibilityIdentifier"]?.string == "move-" + CalculationFixture.taskID.uuidString,
              button.properties["label"]?.string == "Move up: File report",
              let identity = snapshot.identity(for: input) else { throw failure("Android input node differs") }
        let action = try snapshot.route(.init(revision: snapshot.document.revision, identity: identity, event: .activate))
        guard action.actionID == CalculationFixture.actionID else { throw failure("Android action route differs") }
        return action
    }

    private static func check(_ state: Workspace, original: Workspace, order: [UUID], moved: Bool) throws {
        let project = CalculationFixture.projectID
        guard state.tasks(for: project).map(\.id) == order,
              state.revision == original.revision + (moved ? 1 : 0),
              state.outbox.count == original.outbox.count + (moved ? 1 : 0),
              Array(state.outbox.prefix(original.outbox.count)) == original.outbox,
              state.restoration == original.restoration, state.restoration.openDraftID != nil,
              state.drafts == original.drafts, state.entries == original.entries,
              state.attachments == original.attachments, state.projects == original.projects,
              state.tasks.filter({ $0.projectID != project }) == original.tasks.filter({ $0.projectID != project }) else {
            throw failure("Workspace order, outbox, draft or unrelated state differs")
        }
        if moved {
            guard let last = state.outbox.last, last.kind == .taskOrderChanged,
                  last.recordID == project, last.revision == state.revision else { throw failure("Incorrect outbox event") }
        }
    }

    private static func failure(_ message: String) -> UpdateError { UpdateError("fieldlog.row.probe", message) }

    @MainActor private static func until(_ message: String, _ condition: () async -> Bool) async throws {
        let deadline = ContinuousClock.now + .seconds(8)
        while !(await condition()) {
            guard ContinuousClock.now < deadline else { throw failure(message) }
            try await Task.sleep(for: .milliseconds(15))
        }
    }
}
