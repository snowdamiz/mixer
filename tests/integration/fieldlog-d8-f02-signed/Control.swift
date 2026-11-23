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
            try TaskStorage.seed(workspace)
            return
        }

        let phase = args[1]
        let identity = try read(work, "identity.json")
        let roots = try read(work, "roots.json")
        let host = try CapabilityRuntimeIdentity(json: identity).installedRuntime
        let repository = try WorkspaceRepository(directory: workspace)
        let storage = TaskStorage(repository)
        let before = await repository.snapshot()
        let beforeBytes = try read(workspace, "workspace.json")
        let initialOrder = phase == "up" ? TaskStorage.swappedOrder : TaskStorage.initialOrder
        let initialRevision: UInt64 = phase == "up" ? 4 : (["rollback", "offline"].contains(phase) ? 5 : 3)
        try check(before.id == TaskStorage.workspaceID && before.revision == initialRevision
                  && before.tasks(for: TaskStorage.project).map(\.id) == initialOrder, "Cold starting state")
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
        let afterBytes = try read(workspace, "workspace.json")
        let cold = try WorkspaceRepository(directory: workspace)
        let after = await cold.snapshot()
        await cold.close()

        let writes = await storage.writes
        if phase == "down" || phase == "up" {
            let order = phase == "down" ? TaskStorage.swappedOrder : TaskStorage.initialOrder
            let entry = try need(after.outbox.last, "Missing taskOrderChanged")
            try check(entry.kind == .taskOrderChanged && entry.recordID == TaskStorage.project
                      && entry.revision == before.revision + 1 && !before.outbox.contains { $0.id == entry.id },
                      "Outbox identity, kind or revision")
            var expected = before
            expected.revision += 1
            expected.outbox.append(entry)
            for index in expected.tasks.indices {
                expected.tasks[index].position = try need(order.firstIndex(of: expected.tasks[index].id), "Task identity")
                expected.tasks[index].updatedAt = entry.createdAt
            }
            try check(after == expected && writes == ["move-\(phase)-" + TaskStorage.target.uuidString],
                      "Workspace changed outside one reorder transaction")
        } else {
            try check(before == after && beforeBytes == afterBytes && writes.isEmpty,
                      "Read-only launch modified the workspace")
        }
        report["outboxMoves"] = after.outbox.filter { $0.kind == .taskOrderChanged }.map {
            ["recordID": $0.recordID.uuidString, "revision": $0.revision, "id": $0.id.uuidString] as [String: Any]
        }
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
                                           host: InstalledRuntime, port: Int) async throws -> [String: Any] {
        let model = owner.presentation
        let attachment = try need(model.claimNativeAttachment(), "Host display attachment")
        defer { model.detachNativeAttachment(attachment) }
        let online = ["prior", "down", "rollback"].contains(phase)
        let sequence: UInt64 = phase == "prior" ? 1 : (["down", "up"].contains(phase) ? 2 : 3)
        let release = phase == "down" || phase == "up" ? "exact" : (phase == "prior" ? "prior" : "rollback")
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
        let initialOrder = phase == "up" ? TaskStorage.swappedOrder : TaskStorage.initialOrder
        let reviewed = release == "exact"
        try inspect(renderer.snapshot.document, initialOrder, reviewed)
        let ticket = try need(model.nativeDisplayTicket(attachment: attachment), "Host display ticket")
        try check(model.observeNativeDisplay(ticket), "Display witness refused")
        try await until("Healthy candidate") {
            let health = await owner.recoverySnapshot()
            return health.activation.phase == .healthyGuest && health.healthy == candidate && model.inputEnabled
        }
        let health = await owner.recoverySnapshot()
        try check(health.acceptedSequence == sequence, "Durable signed assignment high-water")
        var delivered: String? = nil
        if reviewed {
            let id = "move-\(phase)-" + TaskStorage.target.uuidString
            let identity = try need(renderer.snapshot.identity(for: id), "Absent authorized action \(id)")
            let action = try renderer.route(.init(revision: 1, identity: identity, event: .activate))
            try check(action.actionID == id && action.nodeID == id, "Incorrect route")
            let fire = model.actionHandler(host: renderer, attachment: attachment)
            fire(action)
            try await until("Guest frame after durable write") {
                model.state == .displaying(revision: 2) && model.inputEnabled
            }
            try inspect(try need(model.renderHost, "Updated renderer").snapshot.document,
                        phase == "down" ? TaskStorage.swappedOrder : TaskStorage.initialOrder, true)
            fire(action)
            try check(model.lifecycleObservation?.counters.acceptedEvents == 1
                      && model.lifecycleObservation?.counters.deliveredEvents == 1
                      && model.lastEventResult?.outcome == .delivered, "Guest delivery or stale callback fence")
            delivered = id
        }
        return ["phase": phase, "artifact": artifact, "sequence": sequence, "candidate": candidate,
                "previous": health.previousHealthy as Any? ?? NSNull(), "launch": started.launchID as Any? ?? NSNull(),
                "action": delivered as Any? ?? NSNull()]
    }

    private static func inspect(_ document: UIDocument, _ order: [UUID], _ reviewed: Bool) throws {
        let rows = document.root.children.filter { $0.id.hasPrefix("row-") }
        try check(rows.map(\.id) == order.map { "row-" + $0.uuidString }, "Wrong guest row IDs/order")
        for (position, row) in rows.enumerated() {
            let id = order[position]
            let title = id == TaskStorage.target ? "Measure opening" : "Take field notes"
            try check(row.children.first?.properties["text"]?.string == title, "Wrong guest row title")
            let direction = position == 0 ? "down" : "up"
            let expected = "move-\(direction)-" + id.uuidString
            let buttons = row.children.filter { $0.kind == .button }
            try check(buttons.map(\.id) == (reviewed ? [expected] : []), "Wrong signed action set")
            if let button = buttons.first {
                try check(button.actions == [.init(id: expected, event: .activate)], "Wrong guest action binding")
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
