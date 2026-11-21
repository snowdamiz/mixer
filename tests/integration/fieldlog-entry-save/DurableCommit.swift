import Crypto
import FieldLogFeatures
import FieldLogHostTest
import FieldLogInstalledGuest
import FieldLogModels
import FieldLogStorage
import Foundation
@_spi(AndroidGuestUIV1) import MixerCapabilityActivation
@_spi(InstalledApplicationStorage) import MixerCapabilities
import MixerRuntimeIdentity
import MixerUpdates

private actor CommitStore: InstalledApplicationStorageServing {
    enum Refusal: String { case staleBeforeFacts, staleRevision, permitDenied, declined }
    private struct DeclinedWrite: Error {}
    static let read = KVGetArguments(namespace: FieldLogDraftStorage.namespace, key: "entry-save-decision-v1")
    static let command = KVPutArguments(namespace: FieldLogDraftStorage.namespace, key: "entry-commit-v1", valueBase64: "AQ==")

    private let repository: WorkspaceRepository
    private let selectedDraft: EntryDraft
    private let stagedRevision: UInt64
    private var blocked: Bool
    private let declineWrite: Bool
    private var resumeWrite: CheckedContinuation<Void, Never>?
    private(set) var originatingEvent: InstalledGuestUICommitEvent?
    private(set) var reads = 0
    private(set) var writeAttempts = 0
    private(set) var writes = 0
    private(set) var fallbackCalls = 0
    private(set) var refusal: Refusal?

    init(repository: WorkspaceRepository, draft: EntryDraft, stagedRevision: UInt64, blockWrite: Bool, declineWrite: Bool = false) {
        self.repository = repository; selectedDraft = draft; self.stagedRevision = stagedRevision; blocked = blockWrite
        self.declineWrite = declineWrite
    }

    func facts(for event: InstalledGuestUICommitEvent) async throws -> InstalledGuestUICommitRead {
        reads += 1
        originatingEvent = event
        let snapshot = try await repository.readCommittedSnapshot()
        guard snapshot.revision == stagedRevision else {
            refusal = .staleBeforeFacts
            throw CapabilityFailure.permissionDenied
        }
        let project = selectedDraft.projectID, draftID = selectedDraft.id
        guard snapshot.restoration.selectedProjectID == project, snapshot.restoration.openDraftID == draftID,
              snapshot.drafts.contains(where: { $0.id == draftID && $0.projectID == project }) else {
            throw CapabilityFailure.permissionDenied
        }
        let intent = EntrySaveIntent(projectID: project, draft: selectedDraft, kind: .commit)
        let facts = intent.decisionFacts()
        var bytes = withUnsafeBytes(of: facts.counts.bigEndian) { Data($0) }
        bytes.append(facts.flags)
        let response = KVGetResponse(found: true, valueBase64: bytes.base64EncodedString())
        do { try intent.validate() }
        catch FieldLogError.validation { return .init(response: response) }
        return .init(response: response) { permit in
            try await self.commit(intent, permit: permit)
        }
    }

    private func commit(_ intent: EntrySaveIntent, permit: InstalledGuestUICommitPermit) async throws -> KVMutationResponse {
        writeAttempts += 1
        if blocked { await withCheckedContinuation { resumeWrite = $0 } }
        let saved: Workspace
        do {
            saved = try await repository.transact(expectedRevision: stagedRevision) { workspace in
                guard workspace.restoration.selectedProjectID == intent.projectID,
                      workspace.restoration.openDraftID == intent.draft.id,
                      workspace.drafts.contains(where: { $0.id == intent.draft.id && $0.projectID == intent.projectID }) else {
                    throw CapabilityFailure.permissionDenied
                }
                try permit.consume()
                if declineWrite { throw DeclinedWrite() }
                try intent.apply(to: &workspace)
            }
        } catch is DeclinedWrite {
            refusal = .declined
            return .init(committed: false)
        } catch FieldLogError.staleRevision {
            refusal = .staleRevision
            throw CapabilityFailure.permissionDenied
        } catch CapabilityFailure.permissionDenied {
            refusal = .permitDenied
            throw CapabilityFailure.permissionDenied
        }
        guard case .committed = try intent.result(in: saved) else { throw TrialError("Wrong save result") }
        writes += 1
        return .init(committed: true)
    }

    func release() {
        blocked = false
        resumeWrite?.resume()
        resumeWrite = nil
    }

    func get(_ arguments: KVGetArguments) throws -> KVGetResponse {
        fallbackCalls += 1; throw CapabilityFailure.permissionDenied
    }
    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) throws -> KVMutationResponse {
        fallbackCalls += 1; throw CapabilityFailure.permissionDenied
    }
    func delete(_ arguments: KVDeleteArguments) throws -> KVMutationResponse {
        fallbackCalls += 1; throw CapabilityFailure.permissionDenied
    }
}

@MainActor enum DurableCommit {
    private enum Material: String, CaseIterable {
        case minimum, multiple = "multiple-puts", oneSlot = "one-slot"

        var requests: UInt32 {
            switch self {
            case .minimum: 2
            case .multiple: 4
            case .oneSlot: 1
            }
        }
        var reservationBytes: UInt64 { self == .multiple ? 4_194_304 : 2_097_152 }
        var variants: [String] { self == .multiple ? ["multiple", "unconsumed"] : ["commit"] }

        func directory(in root: URL) -> URL {
            self == .minimum ? root : root.appendingPathComponent(rawValue, isDirectory: true)
        }

        func validate(in directory: URL) throws {
            let identity = try CapabilityRuntimeIdentity(json: Trial.read(directory, "identity.json"))
            guard identity.capabilityExecution.maximumRequests == requests,
                  identity.capabilityExecution.reservationBytes == reservationBytes else {
                throw TrialError("Wrong installed capability limits for \(rawValue)")
            }
        }
    }

    private enum Scenario: String, CaseIterable {
        case blank, valid, declined, multiplePuts, staleBeforeFacts, stale, retired, unconsumed

        var commits: Bool { self == .valid || self == .multiplePuts }
        var blocksWrite: Bool { self == .stale || self == .retired }
        var expectAttempt: Int { commits || blocksWrite || self == .declined ? 1 : 0 }
        var material: Material { self == .multiplePuts || self == .unconsumed ? .multiple : .minimum }
        var expectedRefusal: CommitStore.Refusal? {
            switch self {
            case .staleBeforeFacts: .staleBeforeFacts
            case .stale: .staleRevision
            case .retired: .permitDenied
            case .declined: .declined
            default: nil
            }
        }
        var assignment: Int { self == .unconsumed ? 2 : 1 }
        var expectedFrame: String {
            switch self {
            case .blank: "Entry title can't be empty."
            case .valid, .multiplePuts: "Committed once"
            case .staleBeforeFacts: "Selected draft unavailable."
            case .declined, .stale, .unconsumed: "Commit refused"
            case .retired: ""
            }
        }
    }

    static func sign(fixtures: URL, guests: URL, output: URL, archive: String, binary: String) throws {
        for material in Material.allCases {
            let directory = material.directory(in: output)
            if material != .minimum {
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
            }
            try signReleases(fixtures: fixtures, guests: guests, output: directory, archive: archive, binary: binary,
                             variants: material.variants, deferredStartup: false,
                             limits: (UInt64(material.requests), material.reservationBytes))
        }
    }

    static func replay(assets: URL, directory: URL) async throws {
        try Host.check(mxish_start() == 0, "Host witness transport failed")
        for material in Material.allCases { try material.validate(in: material.directory(in: assets)) }
        for scenario in Scenario.allCases { try await replay(scenario, assets: assets, directory: directory) }
        let closedOwners = Scenario.allCases.count + 1 // Includes a new owner attempting the cold replay.
        try Host.check(mxish_destructors() == closedOwners && mxish_live_allocations() == 0,
                       "Transport destructor count differs from the owned runtime count")
        print("closedOwners=\(closedOwners) liveTransportAllocations=0")
    }

    private static func replay(_ scenario: Scenario, assets: URL, directory: URL) async throws {
        let root = directory.appendingPathComponent(scenario.rawValue, isDirectory: true)
        let workspaceDir = root.appendingPathComponent("workspace", isDirectory: true)
        let file = workspaceDir.appendingPathComponent("workspace.json")
        let projectID = UUID(uuidString: "0576B7F3-9350-4AE6-8F1C-F219CE5CF4E3")!
        let original = EntryDraft(id: UUID(uuidString: "D8E808D4-ACBE-4558-91C6-FAAB517C8DF3")!, projectID: projectID,
            title: "Draft before editing", note: "Saved note", occurredAt: Date(timeIntervalSince1970: 1_700_000_000))
        let seed = try WorkspaceRepository(directory: workspaceDir)
        do {
            _ = try await seed.transact(expectedRevision: 0) { workspace in
                try workspace.createProject(id: original.projectID, title: "North plant", site: "Pump 4")
                try workspace.saveDraft(original)
                workspace.restoration.selectedProjectID = original.projectID
                workspace.restoration.openDraftID = original.id
            }
        } catch { await seed.close(); throw error }
        await seed.close()
        let repository = try WorkspaceRepository(directory: workspaceDir)
        do {
            let before = try await repository.readCommittedSnapshot()
            try Host.check(before.entries.isEmpty && before.drafts == [original], "Cold open did not recover the seeded draft")
            var draft = before.drafts[0]
            draft.title = scenario == .blank ? " \t " : "Inspect e\u{301} valve"
            draft.note = "Keep e\u{301}\r\nexactly. 🛠"
            draft.occurredAt = Date(timeIntervalSince1970: 1_700_000_061)
            let store = CommitStore(repository: repository, draft: draft, stagedRevision: before.revision,
                                    blockWrite: scenario.blocksWrite, declineWrite: scenario == .declined)
            if scenario == .staleBeforeFacts {
                _ = try await repository.transact(expectedRevision: before.revision) { workspace in
                    workspace.projects[0].site = "Updated after staging the edit"
                }
            }
            let baseline = try Data(contentsOf: file)
            if scenario == .valid {
                try await checkOneSlotRefusal(assets: assets, root: root, store: store)
                let reads = await store.reads, attempts = await store.writeAttempts, fallbacks = await store.fallbackCalls
                try Host.check(reads == 0 && attempts == 0 && fallbacks == 0 && Data(contentsOf: file) == baseline,
                               "Refused configuration touched the repository")
            }
            let scenarioAssets = scenario.material.directory(in: assets)
            let committed = try await runOwner(scenario, assets: scenarioAssets, root: root, repository: repository,
                                               store: store, original: original, file: file, baseline: baseline)
            let committedBytes = try Data(contentsOf: file)
            await repository.close()
            let cold = try WorkspaceRepository(directory: workspaceDir)
            let reopened: Workspace
            do {
                reopened = try await cold.readCommittedSnapshot()
                try Host.check(reopened == committed && Data(contentsOf: file) == committedBytes,
                               "Cold reopen changed the committed snapshot or its bytes")
                if scenario.commits {
                    let entrySaved = reopened.outbox.filter { $0.kind == .entrySaved }
                    try Host.check(reopened.revision == 2 && reopened.entries.count == 1 && reopened.drafts.isEmpty
                        && reopened.outbox.count == before.outbox.count + 1
                        && entrySaved.count == 1 && entrySaved[0].recordID == draft.id,
                        "Cold reopen did not recover exactly one added entry and matching outbox record")
                    let entry = reopened.entries[0]
                    try Host.check(entry.id == draft.id && entry.projectID == draft.projectID
                        && entry.title.utf8.elementsEqual(draft.title.utf8) && entry.note.utf8.elementsEqual(draft.note.utf8)
                        && entry.occurredAt == draft.occurredAt, "Cold entry content or identity differed")
                }
                if scenario == .valid {
                    try await replayCommitted(assets: scenarioAssets, root: root, repository: cold, draft: draft)
                }
            } catch { await cold.close(); throw error }
            await cold.close()
            let onDisk = try Data(contentsOf: file)
            try Host.check(onDisk == committedBytes, "Cold replay changed exact workspace bytes")
            print("case=\(scenario.rawValue) maximumRequests=\(scenario.material.requests) "
                + "reservationBytes=\(scenario.material.reservationBytes) "
                + "draft=\(draft.id) revision=\(before.revision)->\(reopened.revision) "
                + "reads=\(await store.reads) writeAttempts=\(await store.writeAttempts) puts=\(await store.writes) "
                + "entries=\(reopened.entries.count) entrySaved=\(reopened.outbox.filter { $0.kind == .entrySaved }.count) "
                + "coldReopen=true "
                + "refusal=\(await store.refusal?.rawValue ?? "none") "
                + "before=\(hash(baseline)) after=\(hash(onDisk))")
        } catch {
            await repository.close()
            throw TrialError("\(scenario.rawValue): \(error)")
        }
    }

    private static func openOwner(assets: URL, root: URL, store: CommitStore) async throws -> CapabilityGuestUIAndroidRuntime {
        let facts = InstalledGuestUICommitFacts(arguments: CommitStore.read, nodeID: "toggle", actionID: "entry.commit",
            commitArguments: CommitStore.command) { try await store.facts(for: $0) }
        return try await Trial.open(directory: root, assets: assets, storage: store, commitFacts: facts)
    }

    private static func checkOneSlotRefusal(assets: URL, root: URL, store: CommitStore) async throws {
        do {
            let owner = try await openOwner(assets: Material.oneSlot.directory(in: assets), root: root, store: store)
            let closed = await owner.close()
            throw TrialError("One-slot Commit configuration admitted, closed=\(closed)")
        } catch let error as UpdateError {
            try Host.check(error.code == "installed.capability.application_storage_commit_limits",
                           "Unexpected one-slot admission refusal: \(error)")
            try Host.check(mxish_live_allocations() == 0, "Refused configuration allocated a presentation")
            print("maximumRequests=1 reservationBytes=\(Material.oneSlot.reservationBytes) refused=\(error.code)")
        }
    }

    private static func start(_ owner: CapabilityGuestUIAndroidRuntime, assets: URL, material: Material,
                              assignment: Int) async throws {
        let variant = material.variants[assignment - 1]
        try await owner.stage(manifest: Trial.read(assets, variant + ".manifest.json"),
                              assignment: Trial.read(assets, "sequence-\(assignment).assignment.json"),
                              bytes: Trial.read(assets, variant + ".wasm"))
        _ = try await owner.start()
        try await Host.eventually("No signed startup frame") { mxfield_recorded_probe(owner.facade) > 0 }
        try Host.check(try Host.frame(owner.facade) == ["Ready to commit", "Commit"], "Wrong Commit startup frame")
        try await Host.witness(owner.facade, command: 10)
        try await Host.eventually("Signed owner did not become healthy") { owner.recoverySnapshot().activation.phase == .healthyGuest }
    }

    private static func replayCommitted(assets: URL, root: URL, repository: WorkspaceRepository, draft: EntryDraft) async throws {
        let directory = root.appendingPathComponent("cold-replay", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
        let revision = try await repository.readCommittedSnapshot().revision
        let store = CommitStore(repository: repository, draft: draft, stagedRevision: revision, blockWrite: false)
        let owner = try await openOwner(assets: assets, root: directory, store: store)
        do {
            try await start(owner, assets: assets, material: .minimum, assignment: 1)
            try await Host.tap(owner.facade, expected: ["Selected draft unavailable."])
            let reads = await store.reads, attempts = await store.writeAttempts
            try Host.check(reads == 1 && attempts == 0, "Cold replay recovered write authority")
            try Host.check(await owner.close(), "Cold replay owner could not retire")
            print("coldReplay=refused reads=1 puts=0")
        } catch {
            let closed = await owner.close()
            throw TrialError("cold replay closed=\(closed): \(error)")
        }
    }

    private static func runOwner(_ scenario: Scenario, assets: URL, root: URL, repository: WorkspaceRepository,
                                 store: CommitStore, original: EntryDraft,
                                 file: URL, baseline: Data) async throws -> Workspace {
        let owner = try await openOwner(assets: assets, root: root, store: store)
        let facade = owner.facade
        var refusedBaseline = baseline
        do {
            try await start(owner, assets: assets, material: scenario.material, assignment: scenario.assignment)

            let oldInput = mxish_last_id(facade, 2)
            if scenario.blocksWrite {
                let previous = mxfield_recorded_probe(facade)
                try await Host.witness(facade, command: 11)
                let cutoff = ContinuousClock.now + .seconds(5)
                while await store.writeAttempts == 0 {
                    try Host.check(ContinuousClock.now < cutoff, "Write did not reach the pre-admission barrier")
                    try await Task.sleep(for: .milliseconds(10))
                }
                guard let event = await store.originatingEvent else { throw TrialError("Missing originating event") }
                if scenario == .stale {
                    _ = try await repository.transact(expectedRevision: 1) { workspace in
                        workspace.projects[0].site = "Updated after facts"
                    }
                    refusedBaseline = try Data(contentsOf: file)
                    await store.release()
                    try await Host.eventually("Stale write never returned") { mxfield_recorded_probe(facade) > previous }
                    try Host.check(try Host.frame(facade) == [scenario.expectedFrame], "The stale write was accepted")
                } else {
                    let closing = Task { await owner.close() }
                    do { try await Host.eventually("Owner did not revoke before admission") { !event.isLive } }
                    catch { await store.release(); _ = await closing.value; throw error }
                    await store.release()
                    try Host.check(await closing.value, "Owner could not retire after refused write")
                }
            } else {
                try await Host.tap(facade, expected: [scenario.expectedFrame])
            }

            guard let event = await store.originatingEvent else { throw TrialError("Missing facts provenance") }
            try Host.check(event.generation > 0 && event.sequence == 1 && event.turnSerial > 1 && event.displayedRevision == 1
                && event.nodeID == "toggle" && event.actionID == "entry.commit", "Unexpected host-originated event")
            if scenario != .retired { try Host.check(await owner.close(), "Owner could not retire") }
            try Host.check(!event.isLive && mxish_live_allocations() == 0, "Retired owner or presentation retained authority")
            try Host.check(oldInput > 0 && mxish_call_entry(facade, 11) != 0, "Retired action replay was accepted")
            let reads = await store.reads, attempts = await store.writeAttempts, fallbacks = await store.fallbackCalls
            try Host.check(reads == 1 && attempts == scenario.expectAttempt && fallbacks == 0,
                           "Unexpected capability dispatch accounting")
            try Host.check(await store.refusal == scenario.expectedRefusal, "Write was refused at the wrong boundary")
            let saved = try await repository.readCommittedSnapshot()
            let entrySaved = saved.outbox.filter { $0.kind == .entrySaved }
            if scenario.commits {
                try Host.check(await store.writes == 1, "Expected exactly one successful Commit")
                if scenario == .multiplePuts { print("duplicatePut=permissionDenied changedPut=permissionDenied") }
            } else {
                try Host.check(await store.writes == 0 && saved.entries.isEmpty && entrySaved.isEmpty && saved.drafts == [original]
                    && Data(contentsOf: file) == refusedBaseline, "Refused Commit changed workspace bytes")
                if scenario == .stale { print("staleRevision2UnchangedSHA256=\(hash(refusedBaseline))") }
            }
            return saved
        } catch {
            await store.release()
            let closed = await owner.close()
            throw TrialError("signed runtime closed=\(closed) liveTransport=\(mxish_live_allocations()): \(error)")
        }
    }

    private static func hash(_ bytes: Data) -> String {
        SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }
}
