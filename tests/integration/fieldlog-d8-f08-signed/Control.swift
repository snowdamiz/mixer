import FieldLogModels
import FieldLogStorage
import Foundation
@testable import MixerCapabilityActivation
import MixerRuntimeIdentity
@_spi(GuestUIV1) import MixerGuest
import MixerUI
import MixerUpdates

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
        let work = URL(fileURLWithPath: args[2], isDirectory: true)
        let workspace = work.appendingPathComponent("workspace")
        if args[1] == "prepare" {
            try Release.prepare(work, fixtures: URL(fileURLWithPath: args[3]), guests: URL(fileURLWithPath: args[4]),
                                vm: URL(fileURLWithPath: args[5]))
            try TaskStorage.seed(URL(fileURLWithPath: args[6]), into: workspace)
            return
        }

        let phase = args[1]
        let identity = try read(work, "identity.json")
        let roots = try read(work, "roots.json")
        let descriptor = try CapabilityRuntimeIdentity(json: identity)
        try check(descriptor.capabilityExecution.turnMilliseconds == 50, "Strict VM turn budget")
        let host = descriptor.installedRuntime
        let repository = try WorkspaceRepository(directory: workspace)
        let storage = TaskStorage(repository)
        let before = await repository.snapshot()
        let beforeBytes = try read(workspace, "workspace.json")
        let initialRevision: UInt64 = phase == "reorder" ? 4 : (["rollback", "offline"].contains(phase) ? 5 : 3)
        try check(before.id == TaskStorage.workspaceID && before.revision == initialRevision
                  && beforeBytes == encode(before), "Cold starting state and canonical disk bytes")
        let materials = try Release.materials.map { name, role in
            CapabilityMaterialFile(role: role, bytes: try read(work, name))
        }
        let execution = try InstalledCapabilityExecution(identityJSON: identity, materials: materials,
            trustRootsJSON: roots, privateContainer: work,
            applicationStorage: .init(runtimeFingerprint: host.runtime, namespace: TaskStorage.namespace,
                                      service: storage, allowsDeferredGuestUIStartup: true))
        let owner = try await CapabilityGuestUIRuntime.open(configuration: .init(
            directory: work.appendingPathComponent("recovery"), channel: "beta",
            installation: Release.installation, observationSeconds: 1), execution: execution)
        let result: Result<[String: Any], Error>
        do {
            let port = try need(Int(args[3]), "Loopback port")
            result = .success(try await observe(owner, work: work, phase: phase, host: host, port: port, storage: storage, before: before))
        } catch {
            result = .failure(error)
        }
        await owner.close()
        await repository.close()
        let recovery = await owner.recoverySnapshot()
        let retired = owner.ownerRetired && recovery.closed && !recovery.incompleteAttempt
            && !recovery.activation.cleanupPending
        if !retired {
            let state = "retired=\(owner.ownerRetired), closed=\(recovery.closed), incomplete=\(recovery.incompleteAttempt), cleanup=\(recovery.activation.cleanupPending)"
            if case .failure(let error) = result { throw UpdateError("f08.retirement", "\(error) (\(state))") }
            throw UpdateError("f08.retirement", state)
        }
        var report = try result.get()
        let afterBytes = try read(workspace, "workspace.json")
        let cold = try WorkspaceRepository(directory: workspace)
        let after = await cold.snapshot()
        await cold.close()

        let writes = await storage.writes
        if phase == "complete" || phase == "reorder" {
            let completing = phase == "complete"
            let entry = try need(after.outbox.last, "Missing linked event")
            try check(entry.kind == (completing ? .taskSaved : .taskOrderChanged)
                      && entry.recordID == (completing ? TaskStorage.roof : TaskStorage.project)
                      && entry.revision == before.revision + 1 && !before.outbox.contains { $0.id == entry.id },
                      "Outbox identity, kind and revision")
            var expected = before
            expected.revision += 1
            expected.outbox.append(entry)
            for index in expected.tasks.indices {
                switch expected.tasks[index].id {
                case TaskStorage.roof:
                    if completing { expected.tasks[index].completed = true }
                    else { expected.tasks[index].position = 1 }
                    expected.tasks[index].updatedAt = entry.createdAt
                case TaskStorage.delivery where !completing:
                    expected.tasks[index].position = 0
                    expected.tasks[index].updatedAt = entry.createdAt
                default: break
                }
            }
            try check(after == expected && afterBytes == encode(expected)
                      && writes == [completing ? TaskStorage.completion : TaskStorage.reorder],
                      "Unexpected workspace bytes or extra write")
        } else {
            try check(before == after && beforeBytes == afterBytes && writes.isEmpty,
                      "Read-only launch modified the workspace")
        }
        report["outbox"] = after.outbox.map {
            ["recordID": $0.recordID.uuidString, "revision": $0.revision, "id": $0.id.uuidString,
             "kind": $0.kind.rawValue, "createdAt": $0.createdAt.timeIntervalSinceReferenceDate] as [String: Any]
        }
        report["completed"] = after.tasks(for: TaskStorage.project).filter(\.completed).map { $0.id.uuidString }
        report["coldOrder"] = after.tasks(for: TaskStorage.project).map { $0.id.uuidString }
        report["revision"] = after.revision
        report["writes"] = writes
        report["workspaceSHA256"] = ReleaseVerifier.sha256(afterBytes)
        report["retired"] = true
        report["pid"] = Int(getpid())
        let data = try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
        print(String(decoding: data, as: UTF8.self))
    }

    @MainActor private static func observe(_ owner: CapabilityGuestUIRuntime, work: URL, phase: String,
                                           host: InstalledRuntime, port: Int, storage: TaskStorage,
                                           before: Workspace) async throws -> [String: Any] {
        let model = owner.presentation
        let attachment = try need(model.claimNativeAttachment(), "Host display attachment")
        defer { model.detachNativeAttachment(attachment) }
        let online = ["prior", "complete", "rollback"].contains(phase)
        let sequence: UInt64 = phase == "prior" ? 1 : (["complete", "reorder"].contains(phase) ? 2 : 3)
        let release = phase == "complete" || phase == "reorder" ? "exact" : (phase == "prior" ? "prior" : "rollback")
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
        let reviewed = release == "exact"
        try inspect(renderer.snapshot.document, revision: before.revision, successor: reviewed)
        let ticket = try need(model.nativeDisplayTicket(attachment: attachment), "Host display ticket")
        try check(model.observeNativeDisplay(ticket), "Display witness refused")
        try await until("Healthy candidate") {
            let health = await owner.recoverySnapshot()
            return health.activation.phase == .healthyGuest && health.healthy == candidate && model.inputEnabled
        }
        let health = await owner.recoverySnapshot()
        try check(health.acceptedSequence == sequence, "Durable signed assignment high-water")
        var revision: UInt64 = 1
        func fire(_ id: String) async throws {
            let frame = try need(model.renderHost, "Current Guest UI frame")
            let identity = try need(frame.snapshot.identity(for: id), "Missing visible action \(id)")
            let action = try frame.route(.init(revision: revision, identity: identity, event: .activate))
            try check(action.actionID == id && action.nodeID == id, "Exact Guest UI action binding")
            let handler = model.actionHandler(host: frame, attachment: attachment)
            handler(action)
            revision += 1
            try await until("Guest frame following \(id)") {
                model.state == .displaying(revision: revision) && model.inputEnabled
            }
            handler(action)
            try check(model.lifecycleObservation?.counters.acceptedEvents == revision - 1
                      && model.lifecycleObservation?.counters.deliveredEvents == revision - 1
                      && model.lastEventResult?.outcome == .delivered, "Action delivery or stale callback fence")
        }

        var workspaceRevision = before.revision
        var delivered: String? = nil
        if reviewed {
            let id = phase == "complete" ? TaskStorage.completion : TaskStorage.reorder
            try await fire(id)
            workspaceRevision += 1
            try inspect(try need(model.renderHost, "Updated frame").snapshot.document,
                        revision: workspaceRevision, successor: true)
            delivered = id
        }

        let url = work.appendingPathComponent("workspace/workspace.json")
        let beforeBrowse = try Data(contentsOf: url)
        let fileBeforeBrowse = try fileIdentity(url)
        let writesBeforeBrowse = await storage.writes
        try await fire("queue")
        let queue = try need(model.renderHost, "Queue frame").snapshot.document
        let labels = queue.root.children.filter { $0.id.hasPrefix("change-") }.map { $0.properties["text"]?.string }
        let expected = Array([
            "Project created", "Task updated: Record delivery", "Entry saved",
            "Task updated: Inspect roof", "Checklist reordered",
        ].prefix(Int(workspaceRevision)).reversed()).map { $0 + " — Saved on device" }
        try check(labels == expected && queue.root.children.map(\.id).last == "back"
                  && queue.root.children.flatMap(\.actions) == [.init(id: "back", event: .activate)],
                  "Queue order and read-only controls")
        try check(beforeBrowse == Data(contentsOf: url) && fileBeforeBrowse == fileIdentity(url),
                  "Opening the queue changed workspace bytes or file identity")
        try await fire("back")
        try inspect(try need(model.renderHost, "Checklist after browsing").snapshot.document,
                    revision: workspaceRevision, successor: reviewed)
        let writesAfterBrowse = await storage.writes
        try check(beforeBrowse == Data(contentsOf: url) && fileBeforeBrowse == fileIdentity(url)
                  && writesBeforeBrowse == writesAfterBrowse, "Browsing changed the workspace")

        return ["phase": phase, "artifact": artifact, "sequence": sequence, "candidate": candidate,
                "previous": health.previousHealthy as Any? ?? NSNull(), "launch": started.launchID as Any? ?? NSNull(),
                "action": delivered as Any? ?? NSNull(), "queue": expected, "browseWorkspaceUnchanged": true]
    }

    private static func fileIdentity(_ url: URL) throws -> [String] {
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        return try [FileAttributeKey.systemFileNumber, .size, .modificationDate].map {
            String(describing: try need(attributes[$0], "Missing workspace file attribute"))
        }
    }

    private static func inspect(_ document: UIDocument, revision: UInt64, successor: Bool) throws {
        let order = revision == 5 ? Array(TaskStorage.initialOrder.reversed()) : TaskStorage.initialOrder
        let rows = document.root.children.filter { $0.id.hasPrefix("row-") }
        try check(rows.map(\.id) == order.map { "row-" + $0.uuidString }, "Wrong guest row IDs/order")
        let summary = try need(document.root.children.first { $0.id == "progress" }, "Progress label")
        let count = revision == 3 ? 0 : 1
        try check(summary.properties["text"]?.string == "\(count) of 2 tasks completed", "Visible completion progress")
        for (position, row) in rows.enumerated() {
            let roof = order[position] == TaskStorage.roof
            let title = roof ? "Inspect roof" : "Record delivery"
            let status = roof && revision >= 4 ? "Completed" : "Not completed"
            try check(row.children.first?.properties["text"]?.string == "\(title) · \(status)", "Visible task status")
            let buttons = row.children.filter { $0.kind == .button }
            let expected: (id: String, label: String)?
            if successor && roof && revision == 3 { expected = (TaskStorage.completion, "Complete: Inspect roof") }
            else if successor && !roof && revision < 5 { expected = (TaskStorage.reorder, "Move up: Record delivery") }
            else { expected = nil }
            try check(buttons.map(\.id) == (expected.map { [$0.id] } ?? []), "Unexpected signed action set")
            if let expected, let button = buttons.first {
                try check(button.actions == [.init(id: expected.id, event: .activate)]
                          && button.properties["label"]?.string == expected.label, "Visible action label and binding")
            }
        }
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
