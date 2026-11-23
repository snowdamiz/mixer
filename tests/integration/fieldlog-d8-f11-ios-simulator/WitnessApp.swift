import FieldLogModels
import FieldLogStorage
@testable @_spi(PrivateFieldLogEditor) import MixerCapabilityActivation
@testable @_spi(GuestUIV1) import MixerGuest
import MixerUpdates
import SwiftUI
import UIKit
import UniformTypeIdentifiers

#if os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE
@main struct F11WitnessApp: App {
    var body: some Scene { WindowGroup { WitnessRoot() } }
}

@MainActor
private struct WitnessRoot: View {
    @State private var session: WitnessSession?

    var body: some View {
        Group {
            if let session {
                if let owner = session.owner {
                    JourneyView(model: owner.presentation, session: session)
                } else {
                    Text(session.status).accessibilityIdentifier("f11.status")
                }
            }
        }
        .task {
            guard session == nil else { return }
            let started = WitnessSession()
            session = started
            await started.start()
        }
    }
}

@MainActor
private struct JourneyView: View {
    @ObservedObject var model: GuestUIPresentation
    let session: WitnessSession

    var body: some View {
        VStack {
            MixerGuestScreen(presentation: model)
            Text(session.status).accessibilityIdentifier("f11.status")
            Button("Save draft") { request(.save) }
                .accessibilityIdentifier("f11.save")
                .disabled(!session.canPerform(.save) || model.f11ActionDisplay() == nil)
            Button("Commit entry") { request(.commit) }
                .accessibilityIdentifier("f11.commit")
                .disabled(!session.canPerform(.commit) || model.f11ActionDisplay() == nil)
        }
        .padding()
    }

    private func request(_ action: F11HostActions.Action) {
        guard let display = model.f11ActionDisplay(),
              let rendered = model.renderHost?.snapshot.document.root.children.first?.properties["value"]?.string
        else { return }
        let bytes = Data(rendered.utf8)
        Task { await session.perform(action, presentation: model, display: display, note: bytes) }
    }
}

@Observable @MainActor
private final class WitnessSession {
    private(set) var owner: CapabilityGuestUIRuntime?
    private(set) var status = "Restoring"
    private var input: WitnessInput?
    private var repository: WorkspaceRepository?
    private var storage: NoteStorage?
    private var revision: UInt64 = 1
    private var busy = false

    func start() async {
        do {
            let args = ProcessInfo.processInfo.arguments
            let run = try need(args.dropFirst().compactMap(UUID.init(uuidString:)).first, "Supply a test run UUID")
            let input = try WitnessInput(run: run)
            if args.contains("--readback") {
                status = "Cold commit " + (try await input.coldCommit())
                return
            }
            let (owner, repository, storage) = try await input.open()
            self.input = input
            self.repository = repository
            self.storage = storage
            UIPasteboard.general.setItems([[UTType.utf8PlainText.identifier: Data("Edited".utf8)]],
                                         options: [.localOnly: true, .expirationDate: Date().addingTimeInterval(90)])
            self.owner = owner
            status = "Ready"
        } catch { status = "Failed: \(error)" }
    }

    func canPerform(_ action: F11HostActions.Action) -> Bool {
        !busy && revision == action.expectedRevision && owner != nil
    }

    func perform(_ action: F11HostActions.Action, presentation: GuestUIPresentation,
                 display: CapabilityGuestUIDisplayTicket, note: Data) async {
        guard canPerform(action), let input, let repository, let storage, let owner,
              owner.presentation === presentation else { return }
        busy = true
        defer { busy = false }
        do {
            let reads = await storage.reads
            let writes = await storage.writeCalls
            try check(note.filter { $0 == 10 }.count == 4 && reads == 1 && writes == 0
                && presentation.lifecycleObservation?.counters.acceptedEvents == 1
                && presentation.lifecycleObservation?.counters.deliveredEvents == 1, "Guest event or storage boundary")
            let permit = F11HostActions(model: presentation, display: display, repository: repository, action: action)
            let updated = try await permit.perform(action, from: presentation, frame: display,
                workspace: NoteStorage.workspaceID, expectedRevision: revision, note: note)
            let result = try need(updated, "Action permit refused")
            let persisted = try read(input.workspace, "workspace.json")
            let duplicate = try await permit.perform(action, from: presentation, frame: display,
                workspace: NoteStorage.workspaceID, expectedRevision: revision, note: note)
            try check(duplicate == nil && permit.transactionAttempts == 1
                && read(input.workspace, "workspace.json") == persisted, "Duplicate action touched the repository")
            try check(result.revision == revision + 1, "Workspace advanced by more than one revision")
            revision = result.revision
            await repository.close()
            self.repository = nil

            if action == .save {
                let reopened = try WorkspaceRepository(directory: input.workspace)
                self.repository = reopened
                try input.verify(await reopened.snapshot(), revision: revision)
                do {
                    _ = try await reopened.transact(expectedRevision: 1) { _ in
                        throw UpdateError("f11.witness", "Stale revision reached mutation")
                    }
                    throw UpdateError("f11.witness", "Stale revision was accepted")
                } catch FieldLogError.staleRevision {}
                try check(read(input.workspace, "workspace.json") == persisted, "Cold draft bytes differed")
                status = "Cold draft revision 2"
            } else {
                try input.verify(result, revision: revision)
                let receipt = CommitReceipt(pid: ProcessInfo.processInfo.processIdentifier,
                                            workspaceHash: ReleaseVerifier.sha256(persisted))
                try JSONEncoder().encode(receipt).write(to: input.root.appendingPathComponent("commit.json"),
                                                        options: .withoutOverwriting)
                await owner.close()
                let deadline = ContinuousClock.now + .seconds(4)
                while !owner.ownerRetired && ContinuousClock.now < deadline {
                    try await Task.sleep(for: .milliseconds(5))
                }
                try check(owner.ownerRetired, "Owner retirement incomplete")
                self.owner = nil
                status = "Committed " + receipt.workspaceHash
            }
        } catch {
            await owner.close()
            await self.repository?.close()
            self.owner = nil
            self.repository = nil
            status = "Failed: \(error)"
        }
    }
}
#endif
