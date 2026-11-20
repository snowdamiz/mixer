import FieldLogInstalledGuest
import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilities
@testable import MixerCapabilityActivation
@_spi(GuestUIV1) import MixerGuest
import MixerUI
import MixerUpdates

@main struct CalculationProbe {
    @MainActor
    static func main() async throws {
        let args = CommandLine.arguments
        let installed = URL(fileURLWithPath: args[1], isDirectory: true)
        let directory = URL(fileURLWithPath: args[2], isDirectory: true)
        guard let installation = UUID(uuidString: args[3]), let sequence = UInt64(args[4]),
              (1...3).contains(sequence) else { throw failure("Invalid run arguments") }
        let offline = args[5] == "offline"
        let seed = try CalculationFixture.readSeed(installed.appendingPathComponent("calculation-seed.json"))
        let store = directory.appendingPathComponent("workspace")
        let workspaceFile = store.appendingPathComponent("workspace.json")
        if sequence == 1 {
            try FileManager.default.createDirectory(at: store, withIntermediateDirectories: true)
            try seed.write(to: workspaceFile, options: .withoutOverwriting)
        }
        let repository = try WorkspaceRepository(directory: store)
        let snapshot = try await repository.readCommittedSnapshot()
        let native = CalculationFixture.projects.map { Int(snapshot.progress(for: $0) * 100) }
        let tasks = snapshot.tasks(for: CalculationFixture.projectID)
        guard native == [33, 100, 0], tasks.count == 3, snapshot.revision == 9,
              snapshot.outbox.count == 11, try Data(contentsOf: workspaceFile) == seed else {
            throw failure("The reopened committed workspace differs from the seed")
        }
        let storage = try CalculationFixture.storage(repository: repository, task: tasks[1])
        try await expectDenied { try await storage.get(.init(namespace: "other", key: "completion-rows")) }
        try await expectDenied { try await storage.get(.init(namespace: FieldLogDraftStorage.namespace, key: "other")) }
        try await expectDenied {
            try await storage.put(.init(namespace: FieldLogDraftStorage.namespace, key: "completion-rows", valueBase64: ""),
                                  maximumTotalBytes: 1024, maximumEntries: 1)
        }
        try await expectDenied { try await storage.delete(.init(namespace: FieldLogDraftStorage.namespace, key: "completion-rows")) }
        let checklist = try await FieldLogSignedTask.open(storage: storage, material: installed,
            directory: directory.appendingPathComponent("signed-checklist"), bundleID: CalculationFixture.bundleID,
            installation: installation)
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
            guard let document = model.renderHost?.snapshot.document else { throw failure("No guest document") }
            let counts = document.root.children.filter { $0.id.hasPrefix("completion-") }
            let percentages = counts.compactMap { $0.properties["text"]?.string }
            let rows = document.root.children.filter { $0.id.hasPrefix("row-") }
            let actual = await checklist.recovery()
            guard actual.acceptedSequence == sequence, let candidate = actual.activation.candidateID,
                  let launch = actual.activation.launchID,
                  (offline || actual.healthy != candidate),
                  counts.map(\.id) == ["completion-0", "completion-1", "completion-2"],
                  percentages == (sequence == 2 ? ["33%", "100%", "0%"] : ["0%", "100%", "0%"]),
                  rows.map(\.id) == tasks.map({ "row-" + $0.id.uuidString }),
                  rows.compactMap({ $0.children.first?.properties["text"]?.string }) == tasks.map(\.title),
                  let ticket = model.nativeDisplayTicket(attachment: attachment),
                  model.observeNativeDisplay(ticket) else { throw failure("Unexpected frame or display witness") }
            try await until("Candidate did not become healthy") {
                let recovery = await checklist.recovery()
                return recovery.healthy == candidate && recovery.activation.phase == .healthyGuest
            }
            let health = await checklist.recovery()
            result = .success(["pid": Int(getpid()), "sequence": sequence, "label": label, "candidate": candidate,
                "previous": health.previousHealthy as Any? ?? NSNull(), "launchID": launch, "percentages": percentages,
                "native": native, "workspaceSHA256": ReleaseVerifier.sha256(seed), "storageRefusals": 4])
        } catch { result = .failure(error) }

        let retired = await checklist.close()
        await repository.close()
        let closed = await checklist.recovery()
        guard retired, closed.closed, !closed.incompleteAttempt, !closed.activation.cleanupPending,
              try Data(contentsOf: workspaceFile) == seed else { throw failure("Cleanup or workspace bytes differed") }
        let outcome = try result.get().merging(["retired": true]) { _, new in new }
        let bytes = try JSONSerialization.data(withJSONObject: outcome, options: [.sortedKeys])
        print(String(decoding: bytes, as: UTF8.self))
    }

    static func failure(_ message: String) -> UpdateError { UpdateError("fieldlog.calculation.probe", message) }

    @MainActor
    static func expectDenied<T: Sendable>(_ operation: @MainActor () async throws -> T) async throws {
        do {
            _ = try await operation()
            throw failure("The storage capability accepted an unauthorized operation")
        } catch CapabilityFailure.permissionDenied {}
    }

    @MainActor
    static func until(_ message: String, _ condition: () async -> Bool) async throws {
        let deadline = ContinuousClock.now + .seconds(6)
        while !(await condition()) {
            guard ContinuousClock.now < deadline else { throw failure(message) }
            try await Task.sleep(for: .milliseconds(15))
        }
    }
}
