import FieldLogModels
import FieldLogStorage
import Foundation
@testable import MixerCapabilityActivation
import MixerRuntimeIdentity
@_spi(GuestUIV1) import MixerGuest
import MixerUI
import MixerUpdates

@main struct Control {
    @MainActor static func main() async throws {
        let args = CommandLine.arguments
        let work = URL(fileURLWithPath: args[2], isDirectory: true)
        let workspace = work.appendingPathComponent("workspace")
        if args[1] == "prepare" {
            try Release.prepare(work, fixtures: URL(fileURLWithPath: args[3]), guests: URL(fileURLWithPath: args[4]),
                                vm: URL(fileURLWithPath: args[5]))
            try await TaskStorage.seed(workspace)
            return
        }

        let phase = args[1]
        let successor = phase == "successor"
        let boundary = successor ? SaveBoundary() : nil
        let fault: WorkspaceRepository.Fault?
        if let boundary {
            fault = { try boundary.writePhase($0) }
        } else {
            fault = nil
        }
        let repository = try WorkspaceRepository(directory: workspace, fault: fault)
        let before = await repository.snapshot()
        let beforeBytes = try read(workspace, "workspace.json")
        try check(before.revision == TaskStorage.baseRevision,
                  "Unexpected cold starting revision")
        let storage = TaskStorage(repository, workspace: workspace, initial: beforeBytes, boundary: boundary)
        let identity = try read(work, "identity.json")
        let host = try CapabilityRuntimeIdentity(json: identity).installedRuntime
        let materials = try Release.materials.map { name, role in
            CapabilityMaterialFile(role: role, bytes: try read(work, name))
        }
        let execution = try InstalledCapabilityExecution(identityJSON: identity, materials: materials,
            trustRootsJSON: read(work, "roots.json"), privateContainer: work,
            applicationStorage: .init(runtimeFingerprint: host.runtime, namespace: TaskStorage.namespace,
                                      service: storage, allowsDeferredGuestUIStartup: true))
        let owner = try await CapabilityGuestUIRuntime.open(configuration: .init(
            directory: work.appendingPathComponent("recovery"), channel: "beta",
            installation: Release.installation, observationSeconds: 1), execution: execution)
        let result: Result<[String: Any], Error>
        do {
            let port = try need(Int(args[3]), "Loopback port")
            result = .success(try await observe(owner, work: work, phase: phase, host: host, port: port,
                                                workspace: workspace, beforeBytes: beforeBytes, boundary: boundary))
        } catch {
            result = .failure(error)
        }
        await owner.close()
        let recovery = await owner.recoverySnapshot()
        try check(owner.ownerRetired && recovery.closed && !recovery.incompleteAttempt
                  && !recovery.activation.cleanupPending, "Complete installed attempt retirement")
        await repository.close()
        var report = try result.get()

        let afterBytes = try read(workspace, "workspace.json")
        let cold = try WorkspaceRepository(directory: workspace)
        let after = await cold.snapshot()
        await cold.close()
        let writes = await storage.puts
        let refusals = await storage.confirmedRefusals
        if successor {
            let task = try need(after.tasks.last, "Missing saved task")
            let entry = try need(after.outbox.last, "Missing taskSaved")
            try check(task.projectID == TaskStorage.project && task.position == 1 && !task.completed
                      && task.title == TaskStorage.title.trimmingCharacters(in: .whitespacesAndNewlines)
                      && task.responsible == TaskStorage.responsible && task.updatedAt == TaskStorage.date,
                      "Task fields and owned project")
            try check(entry.kind == .taskSaved && entry.recordID == task.id
                      && entry.revision == before.revision + 1 && entry.createdAt == TaskStorage.date
                      && !before.outbox.contains { $0.id == entry.id }, "Outbox identity, kind or revision")
            var expected = before
            expected.revision += 1
            expected.tasks.append(task)
            expected.outbox.append(entry)
            try check(after == expected, "Unrelated workspace state changed")
            let observed = try need(boundary?.observation, "No writer observation")
            try check(writes.count == 2 && Set(writes).count == 1 && refusals == 1
                      && observed.attempts == 2 && observed.publications == 1,
                      "Exact retry, refusal, or publication counts")
            report["taskID"] = task.id.uuidString
            report["outboxID"] = entry.id.uuidString
            report["outboxKind"] = entry.kind.rawValue
            report["writerAttempts"] = observed.attempts
            report["publications"] = observed.publications
            report["unrelatedRecordsPreserved"] = true
        } else {
            try check(before == after && beforeBytes == afterBytes && writes.isEmpty && refusals == 0,
                      "Read-only launch modified the workspace")
        }
        report["puts"] = writes
        report["confirmedRefusals"] = refusals
        report["revision"] = after.revision
        report["tasks"] = after.tasks.count
        report["outbox"] = after.outbox.count
        report["workspaceSHA256"] = ReleaseVerifier.sha256(afterBytes)
        report["retired"] = true
        report["pid"] = Int(getpid())
        let data = try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
        print(String(decoding: data, as: UTF8.self))
    }

    @MainActor private static func observe(_ owner: CapabilityGuestUIRuntime, work: URL, phase: String,
                                           host: InstalledRuntime, port: Int, workspace: URL, beforeBytes: Data,
                                           boundary: SaveBoundary?) async throws -> [String: Any] {
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
        if online {
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
        }
        let staged = await owner.recoverySnapshot()
        let candidate = try need(online ? staged.staged : staged.healthy, "Assigned or cached candidate")
        let started = try await owner.start()
        try check(started.phase == .provisionalGuest && started.candidateID == candidate, "Selected candidate")
        try await until("Initial guest frame") { model.state == .displaying(revision: 1) }
        let renderer = try need(model.renderHost, "Guest renderer")
        let expectedStatus = "New task"
        try check(node(renderer.snapshot.document, "status")?.properties["text"]?.string == expectedStatus,
                  "Wrong cold initial status")
        let ticket = try need(model.nativeDisplayTicket(attachment: attachment), "Host display ticket")
        try check(model.observeNativeDisplay(ticket), "Display witness refused")
        try await until("Healthy candidate") {
            let health = await owner.recoverySnapshot()
            return health.activation.phase == .healthyGuest && health.healthy == candidate && model.inputEnabled
        }
        let health = await owner.recoverySnapshot()
        try check(health.acceptedSequence == sequence, "Durable signed assignment high-water")
        var evidence: [String: Any] = [:]
        if let boundary {
            defer { boundary.release() }
            func action(_ id: String, _ event: UIEventKind, _ value: UIValue = .null) throws -> RoutedUIAction {
                let current = try need(model.renderHost, "Current editor renderer")
                let identity = try need(current.snapshot.identity(for: id), "Current identity for \(id)")
                return try current.route(.init(revision: current.snapshot.document.revision, identity: identity,
                                               event: event, value: value))
            }
            func revision(_ number: UInt64) async throws {
                try await until("Expected editor frame \(number)") {
                    model.state == .displaying(revision: number) && model.inputEnabled
                }
            }
            func inspect(_ status: String, disabled: Bool) throws {
                let document = try need(model.renderHost, "Editor renderer").snapshot.document
                try check(document.root.id == "task-editor"
                          && node(document, "title")?.properties["value"]?.string == TaskStorage.title
                          && node(document, "responsible")?.properties["value"]?.string == TaskStorage.responsible
                          && node(document, "title")?.properties["disabled"]?.bool == disabled
                          && node(document, "responsible")?.properties["disabled"]?.bool == disabled
                          && node(document, "save")?.properties["disabled"]?.bool == disabled
                          && node(document, "status")?.properties["text"]?.string == status, "Editor inputs or state")
            }

            let fire = model.actionHandler(host: renderer, attachment: attachment)
            fire(try action("title", .textChange, .string(TaskStorage.title)))
            try await revision(2)
            fire(try action("responsible", .textChange, .string(TaskStorage.responsible)))
            try await revision(3)
            try inspect("New task", disabled: false)
            let first = try action("save", .activate)
            fire(first)
            try await revision(4)
            try await until("Real temp-file write at before_rename") { boundary.observation.staged }
            try inspect("Saving", disabled: true)
            fire(first)
            let pendingNames = try FileManager.default.contentsOfDirectory(atPath: workspace.path)
            let tempName = try need(pendingNames.first { $0.hasPrefix(".saving-") }, "Synced staging file")
            let pending = try JSONDecoder().decode(Workspace.self, from: read(workspace, tempName))
            try check(pending.revision == TaskStorage.baseRevision + 1 && pending.tasks.count == 3
                      && pending.outbox.count == 5 && pending.tasks.last?.responsible == TaskStorage.responsible,
                      "Staging file lacks the actual task and outbox mutation")
            try check(try read(workspace, "workspace.json") == beforeBytes, "Published during refused attempt")
            boundary.release()
            try await revision(5)
            try inspect("Save refused before publication", disabled: false)
            let refused = try read(workspace, "workspace.json")
            let namesAfterRefusal = try FileManager.default.contentsOfDirectory(atPath: workspace.path)
            try check(refused == beforeBytes && !namesAfterRefusal.contains { $0.hasPrefix(".saving-") },
                      "Failed save changed published bytes or left the temporary file")
            let retry = try action("save", .activate)
            fire(retry)
            // The real write may finish before the saving frame is observed.
            try await revision(7)
            fire(retry)
            let saved = try need(model.renderHost, "Saved renderer").snapshot.document
            try check(node(saved, "status")?.properties["text"]?.string == "Task saved"
                      && node(saved, "save") == nil && model.renderHost === renderer
                      && model.lifecycleObservation?.counters.acceptedEvents == 4
                      && model.lifecycleObservation?.counters.deliveredEvents == 4,
                      "Same editor, saved frame, or duplicate control")
            evidence = ["editorStayedAttached": true, "exactInputsRetained": true,
                        "acceptedAndDeliveredEvents": 4, "staleSaveReplays": 2,
                        "stagedRevision": pending.revision,
                        "prePublicationSHA256": ReleaseVerifier.sha256(beforeBytes),
                        "failedSHA256": ReleaseVerifier.sha256(refused), "remainingTemporaryFiles": 0]
        } else {
            try check(node(renderer.snapshot.document, "save") == nil, "Prior payload exposed the successor action")
        }
        evidence["phase"] = phase
        evidence["artifact"] = artifact
        evidence["sequence"] = sequence
        evidence["candidate"] = candidate
        evidence["previous"] = health.previousHealthy as Any? ?? NSNull()
        evidence["launch"] = started.launchID as Any? ?? NSNull()
        return evidence
    }

    private static func node(_ document: UIDocument, _ id: String) -> UINode? {
        document.root.children.first { $0.id == id }
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
