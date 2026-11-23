import FieldLogModels
import FieldLogStorage
import Foundation
@testable @_spi(PrivateFieldLogEditor) import MixerCapabilityActivation
@testable @_spi(GuestUIV1) import MixerGuest
import MixerCapabilities
@_spi(PrivateFieldLogEditor) import MixerRuntimeIdentity
import MixerUI
import MixerUpdates

actor NoteStorage: InstalledApplicationStorageServing {
    static let namespace = "fieldlog-d8-f11-note"
    static let draftID = UUID(uuidString: "F1100000-0000-4000-8000-000000000001")!
    static let projectID = UUID(uuidString: "F1100000-0000-4000-8000-000000000003")!
    static let workspaceID = UUID(uuidString: "F1100000-0000-4000-8000-000000000004")!
    static let originalHash = "c19cbfb3593e93e8a717c23046286e5c6c178166259d2a06d2203a17e81a387d"
    static let editedHash = "c2df9d0971930a3b76c1471bc3de882c603f23c5d9240f6d265b4ab03e9d53d1"
    static let seedHash = "334f3dbcf08b6b1e363da63fad7388fcf7496c9573c3ac0315fd4e0c87a3876d"

    let repository: WorkspaceRepository
    private(set) var reads = 0
    private(set) var writeCalls = 0

    init(_ repository: WorkspaceRepository) { self.repository = repository }

    func get(_ request: KVGetArguments) async throws -> KVGetResponse {
        reads += 1
        let value = await repository.snapshot()
        guard request.namespace == Self.namespace, request.key == "note", value.id == Self.workspaceID,
              value.revision == 1, value.restoration.openDraftID == Self.draftID,
              value.restoration.selectedProjectID == Self.projectID,
              let draft = value.drafts.first(where: { $0.id == Self.draftID }), draft.projectID == Self.projectID,
              ReleaseVerifier.sha256(Data(draft.note.utf8)) == Self.originalHash else {
            throw CapabilityFailure.unavailable
        }
        return .init(found: true, valueBase64: Data(draft.note.utf8).base64EncodedString())
    }

    func put(_ request: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        writeCalls += 1
        throw CapabilityFailure.permissionDenied
    }

    func delete(_ request: KVDeleteArguments) async throws -> KVMutationResponse {
        writeCalls += 1
        throw CapabilityFailure.permissionDenied
    }
}

@main struct Control {
    @MainActor static func main() async {
        do { try await run(CommandLine.arguments) }
        catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(1)
        }
    }

    @MainActor private static func run(_ args: [String]) async throws {
        let phase = args[1]
        let work = URL(fileURLWithPath: args[2])
        if phase == "stock" {
            try stock(work, frame: URL(fileURLWithPath: args[3]))
            return
        }
        let workspace = work.appendingPathComponent("workspace")
        if phase == "prepare" {
            try Release.prepare(work, fixtures: URL(fileURLWithPath: args[3]), guests: URL(fileURLWithPath: args[4]),
                vm: URL(fileURLWithPath: args[5]), privateRetry: true)
            let seed = try Data(contentsOf: URL(fileURLWithPath: args[6]))
            try check(ReleaseVerifier.sha256(seed) == NoteStorage.seedHash, "Seed mismatch")
            try FileManager.default.createDirectory(at: workspace, withIntermediateDirectories: false)
            try seed.write(to: workspace.appendingPathComponent("workspace.json"), options: .withoutOverwriting)
            return
        }

        let before = try read(workspace, "workspace.json")
        let identity = try read(work, "identity.json")
        try check(ReleaseVerifier.sha256(before) == NoteStorage.seedHash, "Archived workspace bytes")
        let descriptor = try CapabilityRuntimeIdentity(privateDevelopmentFieldLogNoteFixtureJSON: identity)
        try check(descriptor.capabilityExecution.turnMilliseconds == 50, "VM turn budget changed")
        do {
            _ = try CapabilityRuntimeIdentity(json: identity)
            throw UpdateError("f11.unexpected", "Stock identity parsed a private fixture")
        } catch let error as UpdateError where error.code != "f11.unexpected" {}
        let repository = try WorkspaceRepository(directory: workspace)
        let storage = NoteStorage(repository)
        let materials = try Release.materials.filter { !$0.0.hasPrefix("http") }.map { name, role in
            CapabilityMaterialFile(role: role, bytes: try read(work, name))
        }
        let execution = try InstalledCapabilityExecution(privateDevelopmentFieldLogNoteFixtureJSON: identity,
            materials: materials, trustRootsJSON: read(work, "roots.json"), privateContainer: work, repository: storage)
        let configuration = CapabilityColdStartConfiguration(directory: work.appendingPathComponent("recovery"),
            channel: "beta", installation: Release.installation, observationSeconds: 1)
        let owner = try await CapabilityGuestUIRuntime.open(privateDevelopmentFieldLogNoteFixture: execution,
            configuration: configuration)

        let trial: Result<[String: Any], Error>
        do { trial = .success(try await observe(owner, work, valid: phase == "valid")) }
        catch { trial = .failure(error) }
        await owner.close()
        await repository.close()
        let recovery = await owner.recoverySnapshot()
        let durableState = try object(read(work.appendingPathComponent("recovery"), "state.json"))
        let retired = owner.ownerRetired && recovery.closed && !recovery.incompleteAttempt && !recovery.activation.cleanupPending
        guard case .success(var report) = trial else {
            FileHandle.standardError.write(Data("post-close retired=\(retired) lastRecovery=\(durableState["lastRecovery"] ?? "none")\n".utf8))
            _ = try trial.get()
            return
        }
        let reads = await storage.reads
        let writes = await storage.writeCalls
        try check(reads == 1 && writes == 0 && before == read(workspace, "workspace.json"),
            "Repository read/write boundary or seed changed")
        try check(retired, "Runtime retirement incomplete after \(phase), lastRecovery=\(durableState["lastRecovery"] ?? "none")")
        report["turnMilliseconds"] = descriptor.capabilityExecution.turnMilliseconds
        report["runtimeFingerprint"] = descriptor.fingerprint
        report["workspaceSHA256"] = ReleaseVerifier.sha256(before)
        report["workspaceReads"] = reads
        report["repositoryWriteCalls"] = writes
        report["workspaceRevision"] = 1
        report["retired"] = retired
        report["stockIdentityRefused"] = true
        print(String(decoding: try JSONSerialization.data(withJSONObject: report, options: .sortedKeys), as: UTF8.self))
    }

    @MainActor private static func observe(_ owner: CapabilityGuestUIRuntime, _ work: URL, valid: Bool) async throws -> [String: Any] {
        let model = owner.presentation
        let attachment = try need(model.claimNativeAttachment(), "Host view attachment")
        defer { model.detachNativeAttachment(attachment) }
        let packet = work.appendingPathComponent("successor")
        let wasm = try read(packet, "payload.wasm")
        try await owner.beginDownload(signedManifest: read(packet, "signed-manifest.json"),
            signedAssignment: read(packet, "assignment.json"))
        try await owner.appendDownload(wasm, atOffset: 0)
        try await owner.finishDownload()
        let staged = await owner.recoverySnapshot()
        let started = try await owner.start()
        let launch = try need(started.launchID, "Launch ID")
        let candidate = try need(staged.staged, "Signed staged candidate")
        try check(started.candidateID == candidate, "Selected wrong signed artifact")
        var report: [String: Any] = ["launch": launch, "candidate": candidate,
            "wasmSHA256": ReleaseVerifier.sha256(wasm)]
        if !valid {
            try await until("signed malformed frame terminal") {
                let snapshot = await owner.recoverySnapshot()
                return snapshot.activation.phase == .recoveryRequired && model.state == .stopped
            }
            let state = try object(read(work.appendingPathComponent("recovery"), "state.json"))
            let recovery = await owner.recoverySnapshot()
            try check(model.renderHost == nil && !model.inputEnabled
                && state["lastRecovery"] as? String == "ui_protocol_after_effects"
                && recovery.healthy == nil, "Wrong frame reached current host presentation")
            report["presentationAdmitted"] = false
            report["reason"] = "ui_protocol_after_effects"
            return report
        }

        try await until("original vertical frame displayed") { model.state == .displaying(revision: 1) }
        let host = try need(model.renderHost, "Actual MixerUIHost")
        let spec = GuestUIFieldLogNoteFixture.self
        try checkField(host.snapshot.document, revision: 1, hash: NoteStorage.originalHash)
        let display = try need(model.nativeDisplayTicket(attachment: attachment), "Host display ticket")
        try check(display.ticket.revision == 1 && model.observeNativeDisplay(display), "Initial display observation")
        try await until("healthy signed host and current input") {
            let snapshot = await owner.recoverySnapshot()
            return snapshot.healthy == candidate && snapshot.activation.phase == .healthyGuest && model.inputEnabled
        }
        let current = try need(host.snapshot.identity(for: spec.field), "Current field owner")
        let envelope = UIEventEnvelope(revision: 1, identity: current, event: .textChange, value: .string(spec.edited))
        let approved = try host.route(envelope)
        try check(approved.nodeID == spec.field && approved.actionID == spec.action, "Wrong action routed")
        let submit = model.actionHandler(host: host, attachment: attachment)
        let other = CapabilityGuestUIAttachmentIdentity()
        model.actionHandler(host: host, attachment: other)(approved)
        try submit(alter(approved, "nodeID", "entry.other.note"))
        try submit(alter(approved, "actionID", "entry.saveDraft"))
        try submit(alter(approved, "revision", 2))
        try check(model.lifecycleObservation?.counters.acceptedEvents == 0 && model.lastEventResult == nil,
            "Wrong owner, field, action or revision entered the guest")
        submit(approved)
        try await until("edited view after denied guest put and delete") {
            model.state == .displaying(revision: 2) && model.lastEventResult?.outcome == .delivered
        }
        let delivery = try need(model.lastEventResult, "Edit delivery receipt")
        let newView = try need(model.renderHost, "Edited MixerUIHost")
        try check(newView === host, "Accidental owner replacement")
        try checkField(newView.snapshot.document, revision: 2, hash: NoteStorage.editedHash)
        submit(approved)
        let counts = try need(model.lifecycleObservation?.counters, "Live exchange counters")
        try check(delivery.generation == display.ticket.generation && delivery.sequence == 1
            && counts.acceptedEvents == 1 && counts.deliveredEvents == 1, "Unexpected edit receipt or stale replay")
        report["field"] = spec.field
        report["action"] = spec.action
        report["initialRevision"] = 1
        report["editedRevision"] = 2
        report["originalNoteSHA256"] = NoteStorage.originalHash
        report["editedNoteSHA256"] = NoteStorage.editedHash
        report["lineFeedsPerView"] = 4
        report["acceptedAndDeliveredSequence"] = delivery.sequence
        report["generation"] = delivery.generation
        report["rejectedInput"] = ["wrong attachment", "wrong field", "wrong action", "wrong revision", "stale replay"]
        report["guestMutations"] = ["put": "permissionDenied", "delete": "permissionDenied"]
        return report
    }

    private static func alter(_ action: RoutedUIAction, _ key: String, _ value: Any) throws -> RoutedUIAction {
        var fields = try object(encode(action))
        fields[key] = value
        return try JSONDecoder().decode(RoutedUIAction.self, from: JSONSerialization.data(withJSONObject: fields))
    }

    private static func checkField(_ frame: UIDocument, revision: UInt64, hash: String) throws {
        let spec = GuestUIFieldLogNoteFixture.self
        let field = try need(frame.root.children.first, "Restored note field")
        let value = try need(field.properties["value"]?.string, "Restored note text")
        try check(frame.revision == revision && frame.root.children.count == 1 && field.id == spec.field
            && field.kind == .textField && field.properties["axis"] == .string("vertical")
            && field.actions == [.init(id: spec.action, event: .textChange)]
            && value.utf8.filter { $0 == 10 }.count == 4 && ReleaseVerifier.sha256(Data(value.utf8)) == hash,
            "Frame identity, revision, binding or UTF-8 bytes")
    }

    @MainActor private static func until(_ message: String, _ done: () async -> Bool) async throws {
        let deadline = ContinuousClock.now + .seconds(4)
        while !(await done()) {
            try check(ContinuousClock.now < deadline, message)
            try await Task.sleep(for: .milliseconds(5))
        }
    }

    private static func stock(_ vectorsPath: URL, frame: URL) throws {
        let vectors = try need(JSONSerialization.jsonObject(with: Data(contentsOf: vectorsPath)) as? [[String: Any]], "Stock vectors")
        try check(vectors.count == 11, "Unexpected stock vector count")
        for vector in vectors {
            let bytes = try JSONSerialization.data(withJSONObject: need(vector["descriptor"], "Stock descriptor"))
            let runtime = try CapabilityRuntimeIdentity(json: bytes)
            try check(runtime.fingerprint == vector["fingerprint"] as? String
                && runtime.canonicalCBOR.map { String(format: "%02x", $0) }.joined() == vector["canonicalCBOR"] as? String,
                "Stock identity bytes or fingerprint changed")
        }
        let bytes = try Data(contentsOf: frame)
        do {
            _ = try GuestUIExchangeCodec.legacy.decode(bytes)
            throw UpdateError("f11.unexpected", "Stock V1 accepted a text field")
        } catch UIValidationError.unsupportedNode(.textField) {}
        do {
            _ = try GuestUIFieldLogTaskRetry.codec.decode(bytes)
            throw UpdateError("f11.unexpected", "F04 codec accepted vertical note")
        } catch UIValidationError.unsupportedTextFieldAxis(.vertical) {}
        print(#"{"canonicalCBORAndFingerprints":11,"stockV1":"unsupportedNode(textField)","f04Codec":"unsupportedTextFieldAxis(vertical)"}"#)
    }
}
