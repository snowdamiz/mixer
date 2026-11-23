import FieldLogFeatures
import FieldLogModels
import FieldLogStorage
import Foundation
@testable @_spi(PrivateFieldLogEditor) import MixerCapabilityActivation
@testable @_spi(GuestUIV2) import MixerGuest
import MixerCapabilities
import MixerRuntimeIdentity
import MixerUI
import MixerUpdates

actor NoteStorage: InstalledApplicationStorageServing {
    static let namespace = "fieldlog-d8-f11-note"
    static let target = UUID(uuidString: "F1100000-0000-4000-8000-000000000001")!
    static let originalHash = "c19cbfb3593e93e8a717c23046286e5c6c178166259d2a06d2203a17e81a387d"
    static let seedHash = "334f3dbcf08b6b1e363da63fad7388fcf7496c9573c3ac0315fd4e0c87a3876d"

    let repository: WorkspaceRepository
    private(set) var reads = 0
    private(set) var writes = 0

    init(_ repository: WorkspaceRepository) { self.repository = repository }

    func get(_ request: KVGetArguments) async throws -> KVGetResponse {
        reads += 1
        let workspace = await repository.snapshot()
        guard request.namespace == Self.namespace, request.key == "note",
              workspace.restoration.openDraftID == Self.target,
              let draft = workspace.drafts.first(where: { $0.id == Self.target }),
              ReleaseVerifier.sha256(Data(draft.note.utf8)) == Self.originalHash else {
            throw CapabilityFailure.unavailable
        }
        return .init(found: true, valueBase64: Data(draft.note.utf8).base64EncodedString())
    }

    func put(_ request: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        writes += 1
        throw CapabilityFailure.permissionDenied
    }

    func delete(_ request: KVDeleteArguments) async throws -> KVMutationResponse {
        writes += 1
        throw CapabilityFailure.permissionDenied
    }
}

@main struct Control {
    @MainActor static func main() async {
        do { try await run() }
        catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(1)
        }
    }

    @MainActor private static func run() async throws {
        let args = CommandLine.arguments
        let phase = args[1]
        let work = URL(fileURLWithPath: args[2], isDirectory: true)
        let workspace = work.appendingPathComponent("workspace")
        let privateRetry = args.contains("--private-retry")
        if phase == "prepare" {
            try Release.prepare(work, fixtures: URL(fileURLWithPath: args[3]), guests: URL(fileURLWithPath: args[4]),
                                vm: URL(fileURLWithPath: args[5]), privateRetry: privateRetry)
            let seed = try Data(contentsOf: URL(fileURLWithPath: args[6]))
            try check(ReleaseVerifier.sha256(seed) == NoteStorage.seedHash, "Archived installed F11 seed")
            try FileManager.default.createDirectory(at: workspace, withIntermediateDirectories: false)
            try seed.write(to: workspace.appendingPathComponent("workspace.json"), options: .withoutOverwriting)
            return
        }
        if phase == "contract" {
            let bytes = try Data(contentsOf: work)
            let noteHost = GuestUICodec(validator: UIValidator(supportedTextFieldAxes: [.horizontal, .vertical]))
            let field = try need(noteHost.decode(bytes).document.root.children.first, "Projected F11 field")
            let note = try need(field.properties["value"]?.string, "Projected F11 note bytes")
            try check(field.actions.first?.id == "entry.note.change"
                      && ReleaseVerifier.sha256(Data(note.utf8)) == NoteStorage.originalHash, "Exact F11 action and note")
            do {
                _ = try GuestUIExchangeCodec.legacy.decode(bytes)
                throw UpdateError("f11.contract", "Stock codec allowed the restored note")
            } catch UIValidationError.unsupportedNode(.textField) {}
            do {
                _ = try GuestUIFieldLogTaskRetry.codec.decode(bytes)
                throw UpdateError("f11.contract", "Private retry codec allowed the vertical note")
            } catch UIValidationError.unsupportedTextFieldAxis(.vertical) {}
            var document = try object(bytes)
            var root = try need(document["root"] as? [String: Any], "Root")
            var children = try need(root["children"] as? [[String: Any]], "Children")
            var properties = try need(children[0]["properties"] as? [String: Any], "Field properties")
            properties.removeValue(forKey: "axis")
            children[0]["properties"] = properties
            root["children"] = children
            document["root"] = root
            do {
                _ = try GuestUIFieldLogTaskRetry.codec.decode(JSONSerialization.data(withJSONObject: document))
                throw UpdateError("f11.contract", "Private retry codec allowed the note with a horizontal field")
            } catch GuestUIEditorErrorV2.routing {}
            print(#"{"stock":"unsupportedNode(textField)","private":"unsupportedTextFieldAxis(vertical)","privateHorizontalDiscriminator":"routing"}"#)
            return
        }
        if phase.hasPrefix("ordinary-") {
            try await ordinary(phase, workspace: work)
            return
        }
        let before = try read(workspace, "workspace.json")
        try check(ReleaseVerifier.sha256(before) == NoteStorage.seedHash, "Cold exact installed seed")
        let repository = try WorkspaceRepository(directory: workspace)
        let storage = NoteStorage(repository)
        let identity = try read(work, "identity.json")
        let host = try Release.installedHost(identity, privateRetry: privateRetry)
        if !privateRetry {
            let descriptor = try CapabilityRuntimeIdentity(json: identity)
            try check(descriptor.capabilityExecution.turnMilliseconds == 50, "Strict 50 ms VM turn budget")
        }
        let materials = try Release.materials.filter { !privateRetry || !$0.0.hasPrefix("http") }.map { name, role in
            CapabilityMaterialFile(role: role, bytes: try read(work, name))
        }
        let configuration = CapabilityColdStartConfiguration(directory: work.appendingPathComponent("recovery"),
            channel: "beta", installation: Release.installation, observationSeconds: 1)
        let roots = try read(work, "roots.json")
        let owner: CapabilityGuestUIRuntime
        if privateRetry {
            let execution = try InstalledCapabilityExecution(privateDevelopmentFieldLogTaskRetryJSON: identity,
                materials: materials, trustRootsJSON: roots, privateContainer: work, repository: storage)
            owner = try await CapabilityGuestUIRuntime.open(privateDevelopmentFieldLogTaskRetry: execution, configuration: configuration)
        } else {
            let execution = try InstalledCapabilityExecution(identityJSON: identity,
                materials: materials, trustRootsJSON: roots, privateContainer: work,
                applicationStorage: .init(runtimeFingerprint: host.runtime, namespace: NoteStorage.namespace,
                                          service: storage, allowsDeferredGuestUIStartup: true))
            owner = try await CapabilityGuestUIRuntime.open(configuration: configuration, execution: execution)
        }
        let result: Result<[String: Any], Error>
        do {
            let port = privateRetry ? nil : try need(Int(args[3]), "Loopback port")
            result = .success(try await observe(owner, work: work, phase: phase, host: host, port: port))
        } catch {
            result = .failure(error)
        }
        await owner.close()
        await repository.close()
        let recovery = await owner.recoverySnapshot()
        try check(owner.ownerRetired && recovery.closed && !recovery.incompleteAttempt
                  && !recovery.activation.cleanupPending, "Complete installed attempt retirement")
        var report = try result.get()
        let reads = await storage.reads
        let writes = await storage.writes
        try check(reads == (privateRetry ? 0 : 1) && writes == 0
                  && before == read(workspace, "workspace.json"), "Observed storage boundary and untouched seed")
        report["workspaceReads"] = reads
        report["workspaceWrites"] = writes
        report["workspaceSHA256"] = ReleaseVerifier.sha256(before)
        report["pid"] = Int(getpid())
        report["retired"] = true
        print(String(decoding: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]), as: UTF8.self))
    }

    @MainActor private static func ordinary(_ phase: String, workspace: URL) async throws {
        let repository = try WorkspaceRepository(directory: workspace)
        let state = await repository.snapshot()
        let original = "Café e\u{0301} 👩🏽‍🔬\n東京\n\nLast line\n"
        let edited = original + "Edited"
        let input = try read(workspace, "workspace.json")
        var note: String
        if phase == "ordinary-read" {
            let entry = try need(state.entries.first { $0.id == NoteStorage.target }, "Missing committed row")
            try check(state.revision == 3 && state.outbox.last?.kind == .entrySaved
                      && state.outbox.last?.recordID == entry.id && state.outbox.last?.revision == 3
                      && state.restoration.openDraftID == nil, "Cold linked F11 record and restoration")
            note = entry.note
        } else {
            let draft = try need(state.drafts.first { $0.id == state.restoration.openDraftID }, "Restored draft")
            let edit = phase == "ordinary-save"
            try check(draft.id == NoteStorage.target && state.revision == (edit ? 1 : 2)
                      && draft.note.utf8.elementsEqual((edit ? original : edited).utf8), "Exact cold restored note")
            let editor = try EntryEditor(projectID: draft.projectID, draft: draft) { intent in
                do {
                    let saved = try await repository.transact(expectedRevision: state.revision) { try intent.apply(to: &$0) }
                    return try intent.result(in: saved)
                } catch { return .failed(String(describing: error)) }
            }
            if edit {
                try editor.changeNote(edited)
                try check(input == read(workspace, "workspace.json"), "Edit alone wrote the workspace")
                try editor.saveDraft()
                await editor.waitForSave()
                note = try need(editor.state.savedDraft, "Draft save failed").note
            } else {
                try editor.commitDraft()
                await editor.waitForSave()
                note = try need(editor.state.committed, "Commit failed").note
                let committed = try read(workspace, "workspace.json")
                try editor.commitDraft()
                await editor.waitForSave()
                try check(committed == read(workspace, "workspace.json"), "Repeat commit wrote again")
            }
            try editor.close()
        }
        try check(note.utf8.elementsEqual(edited.utf8), "Unicode or line-feed bytes changed")
        await repository.close()
        print(ReleaseVerifier.sha256(try read(workspace, "workspace.json")))
    }

    @MainActor private static func observe(_ owner: CapabilityGuestUIRuntime, work: URL, phase: String,
                                           host: InstalledRuntime, port: Int?) async throws -> [String: Any] {
        let model = owner.presentation
        let attachment = try need(model.claimNativeAttachment(), "Host display attachment")
        defer { model.detachNativeAttachment(attachment) }
        let online = phase != "offline"
        let sequence: UInt64 = phase == "prior" ? 1 : (phase == "successor" ? 2 : 3)
        let release = online ? phase : "rollback"
        let packet = work.appendingPathComponent(release)
        let expectedAssignment = try object(read(packet, "assignment.json"))
        let assignment = try need(expectedAssignment["assignment"] as? [String: Any], "Assignment body")
        let artifact = try need(assignment["artifact_sha256"] as? String, "Assigned artifact")
        if online, let port {
            let base = try need(URL(string: "http://127.0.0.1:\(port)"), "Loopback URL")
            let scope = host.scope
            let query = "/v3/updates?organization=\(scope.organization)&project=\(scope.project)&app=\(scope.app)"
                + "&environment=\(scope.environment)&platform=\(scope.platform)&runtime=\(host.runtime)"
                + "&channel=beta&installation=\(Release.installation)"
            let session = URLSession(configuration: .ephemeral)
            defer { session.invalidateAndCancel() }
            let offer = try object(await fetch(session, base, query))
            let artifactPath = "/v3/artifacts/\(artifact)?organization=\(scope.organization)&project=\(scope.project)"
            try check(offer["artifact_url"] as? String == artifactPath
                      && (offer["signed_assignment"] as? NSDictionary) == (expectedAssignment as NSDictionary),
                      "Stock origin offer differs from signed assignment")
            let envelope = try object(await fetch(session, base, artifactPath))
            let manifest = try need(envelope["signed_manifest"] as? [String: Any], "Delivered signed manifest")
            let payload = try need((envelope["payload"] as? String).flatMap { Data(base64Encoded: $0) }, "Delivered payload")
            let expectedManifest = try object(read(packet, "signed-manifest.json"))
            let expectedPayload = try read(packet, "payload.wasm")
            try check(manifest as NSDictionary == expectedManifest as NSDictionary && payload == expectedPayload,
                      "Stock origin envelope differs from signed packet")
            try await owner.beginDownload(signedManifest: JSONSerialization.data(withJSONObject: manifest),
                signedAssignment: JSONSerialization.data(withJSONObject: try need(offer["signed_assignment"], "Delivered assignment")))
            try await owner.appendDownload(payload, atOffset: 0)
            try await owner.finishDownload()
        } else if online {
            let payload = try read(packet, "payload.wasm")
            try await owner.beginDownload(signedManifest: read(packet, "signed-manifest.json"),
                                          signedAssignment: read(packet, "assignment.json"))
            try await owner.appendDownload(payload, atOffset: 0)
            try await owner.finishDownload()
        }
        let staged = await owner.recoverySnapshot()
        let candidate = try need(online ? staged.staged : staged.healthy, "Assigned or cached candidate")
        let started = try await owner.start()
        try check(started.phase == .provisionalGuest && started.candidateID == candidate, "Selected candidate")
        if phase == "successor" {
            try await until("Successor did not reach the first-document refusal") {
                let recovery = await owner.recoverySnapshot()
                return recovery.activation.phase == .recoveryRequired && model.state == .stopped
            }
            let recovery = await owner.recoverySnapshot()
            let state = try object(read(work.appendingPathComponent("recovery"), "state.json"))
            try check(recovery.acceptedSequence == 2 && recovery.healthy == staged.healthy
                      && model.renderHost == nil && !model.inputEnabled
                      && state["lastRecovery"] as? String == "ui_protocol_after_effects",
                      "Refusal reason, prior health or presentation boundary")
            return ["phase": phase, "artifact": artifact, "sequence": sequence, "candidate": candidate,
                    "refusal": "ui_protocol_after_effects", "presentationAdmitted": false,
                    "previousHealthy": recovery.healthy as Any? ?? NSNull(),
                    "launch": started.launchID as Any? ?? NSNull()]
        }
        try await until("Initial prior frame") { model.state == .displaying(revision: 1) }
        let displayed = try need(model.renderHost, "Read-only renderer").snapshot.document
        let note = try need(displayed.root.children.first?.properties["text"]?.string, "Read-only note")
        try check(displayed.root.children.count == 1
                  && ReleaseVerifier.sha256(Data(note.utf8)) == NoteStorage.originalHash,
                  "Baseline, rollback or offline note bytes")
        let ticket = try need(model.nativeDisplayTicket(attachment: attachment), "Display ticket")
        try check(model.observeNativeDisplay(ticket), "Display witness refused")
        try await until("Healthy prior candidate") {
            let health = await owner.recoverySnapshot()
            return health.activation.phase == .healthyGuest && health.healthy == candidate && model.inputEnabled
        }
        let health = await owner.recoverySnapshot()
        try check(health.acceptedSequence == sequence, "Durable assignment high-water")
        return ["phase": phase, "artifact": artifact, "sequence": sequence, "candidate": candidate,
                "noteSHA256": NoteStorage.originalHash, "launch": started.launchID as Any? ?? NSNull()]
    }

    private static func fetch(_ session: URLSession, _ base: URL, _ path: String) async throws -> Data {
        let url = try need(URL(string: path, relativeTo: base)?.absoluteURL, "Loopback request URL")
        let (bytes, response) = try await session.data(from: url)
        try check((response as? HTTPURLResponse)?.statusCode == 200 && response.url == url
                  && bytes.count < 65_537, "Stock loopback GET \(url.path)")
        return bytes
    }

    @MainActor private static func until(_ reason: String, _ predicate: () async -> Bool) async throws {
        let deadline = ContinuousClock.now + .seconds(8)
        while !(await predicate()) {
            try check(ContinuousClock.now < deadline, reason)
            try await Task.sleep(for: .milliseconds(15))
        }
    }
}
