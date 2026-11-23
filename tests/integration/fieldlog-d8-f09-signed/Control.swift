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
            let pages = try Data(contentsOf: URL(fileURLWithPath: args[7]))
            _ = try ArchivedPages.load(pages)
            try pages.write(to: work.appendingPathComponent("expected-pages.json"), options: .withoutOverwriting)
            return
        }

        let phase = args[1]
        let identity = try read(work, "identity.json")
        let roots = try read(work, "roots.json")
        let descriptor = try CapabilityRuntimeIdentity(json: identity)
        try check(descriptor.capabilityExecution.turnMilliseconds == 50, "Strict VM turn budget")
        let host = descriptor.installedRuntime
        let repository = try WorkspaceRepository(directory: workspace)
        let pages = try ArchivedPages.load(read(work, "expected-pages.json"))
        try check(pages.projectID == TaskStorage.project && pages.before.map { $0.rows.count } == [20, 3]
                  && pages.after.map { $0.rows.count } == [20, 3], "Archived checklist identity and page sizes")
        let storage = TaskStorage(repository, pages: pages)
        let workspaceFiles = try siblings(workspace)
        let before = await repository.snapshot()
        let beforeBytes = try read(workspace, "workspace.json")
        let initialRevision: UInt64 = ["successor-cold", "rollback", "offline"].contains(phase) ? 2 : 1
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
            result = .success(try await observe(owner, work: work, phase: phase, host: host, port: port, storage: storage, before: before, pages: pages))
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
            if case .failure(let error) = result { throw UpdateError("f09.retirement", "\(error) (\(state))") }
            throw UpdateError("f09.retirement", state)
        }
        var report = try result.get()
        let afterBytes = try read(workspace, "workspace.json")
        let cold = try WorkspaceRepository(directory: workspace)
        let after = await cold.snapshot()
        await cold.close()

        let writes = await storage.writes
        if phase == "move" {
            let event = try need(after.outbox.last, "Missing linked event")
            try check(event.kind == .taskOrderChanged && event.recordID == TaskStorage.project
                      && event.revision == 2 && !before.outbox.contains { $0.id == event.id },
                      "Outbox identity, kind and revision")
            var expected = before
            expected.revision += 1
            expected.outbox.append(event)
            for index in expected.tasks.indices where expected.tasks[index].projectID == TaskStorage.project {
                expected.tasks[index].updatedAt = event.createdAt
                switch expected.tasks[index].id {
                case TaskStorage.target: expected.tasks[index].position = 19
                case TaskStorage.neighbor: expected.tasks[index].position = 20
                default: break
                }
            }
            try check(after == expected && afterBytes == encode(expected) && writes == [TaskStorage.reorder],
                      "Unexpected workspace bytes or extra write")
            // Project both executions onto the installed event identity and time.
            var archived = event
            archived.id = UUID(uuidString: "C65BFFFD-024D-40E9-8555-16BC552E95F4")!
            archived.createdAt = Date(timeIntervalSinceReferenceDate: 817040609.4876717)
            expected.outbox[expected.outbox.count - 1] = archived
            for index in expected.tasks.indices where expected.tasks[index].projectID == TaskStorage.project {
                expected.tasks[index].updatedAt = archived.createdAt
            }
            let archivedHash = ReleaseVerifier.sha256(try encode(expected))
            try check(archivedHash == TaskStorage.archivedMoveSHA256, "Archived installed post-move bytes")
            report["normalizedInstalledWorkspaceSHA256"] = archivedHash
            report["event"] = ["recordID": event.recordID.uuidString, "revision": event.revision,
                "id": event.id.uuidString, "kind": event.kind.rawValue, "createdAt": event.createdAt.timeIntervalSinceReferenceDate]
        } else {
            try check(before == after && beforeBytes == afterBytes && writes.isEmpty,
                      "Read-only launch modified the workspace")
        }
        let order = after.tasks(for: TaskStorage.project).map(\.id)
        let archive = after.revision == 1 ? pages.before : pages.after
        try check(order == archive.flatMap(\.rows).map(\.id), "Cold checklist order")
        let finalFiles = try siblings(workspace)
        try check(finalFiles == workspaceFiles && finalFiles.keys.sorted() == ["workspace.lock"],
                  "Unrelated workspace files changed or new files were left behind")
        report["unaffectedWorkspaceFiles"] = finalFiles
        report["coldOrder"] = order.map(\.uuidString)
        report["outboxCount"] = after.outbox.count
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
                                           before: Workspace, pages: ArchivedPages) async throws -> [String: Any] {
        let model = owner.presentation
        let attachment = try need(model.claimNativeAttachment(), "Host display attachment")
        defer { model.detachNativeAttachment(attachment) }
        let online = ["prior", "move", "rollback"].contains(phase)
        let sequence: UInt64 = phase == "prior" ? 1 : (["move", "successor-cold"].contains(phase) ? 2 : 3)
        let release = ["move", "successor-cold"].contains(phase) ? "exact" : (phase == "prior" ? "prior" : "rollback")
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
        _ = try inspect(renderer.snapshot.document, pages: pages, revision: before.revision, page: 0, successor: reviewed)
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

        let url = work.appendingPathComponent("workspace/workspace.json")
        func frame() throws -> UIDocument {
            try need(model.renderHost, "Checklist frame").snapshot.document
        }
        func checkDisabled(_ id: String) throws {
            let renderer = try need(model.renderHost, "Checklist frame for disabled control")
            let identity = try need(renderer.snapshot.identity(for: id), "Disabled control identity")
            do {
                _ = try renderer.route(.init(revision: revision, identity: identity, event: .activate))
                throw UpdateError("f09.route", "Disabled pagination control accepted")
            } catch UIRoutingError.disabledNode {}
        }
        var visits = [try inspect(frame(), pages: pages, revision: before.revision, page: 0, successor: reviewed)]
        if reviewed {
            try checkDisabled("tasks.previous")
            let original = try fingerprint(url)
            try await fire("tasks.next")
            try checkDisabled("tasks.next")
            visits.append(try inspect(frame(), pages: pages, revision: before.revision, page: 1, successor: true))
            try await fire("tasks.previous")
            visits.append(try inspect(frame(), pages: pages, revision: before.revision, page: 0, successor: true))
            try await fire("tasks.next")
            try checkDisabled("tasks.next")
            visits.append(try inspect(frame(), pages: pages, revision: before.revision, page: 1, successor: true))
            let beforeWrite = await storage.writes
            try check(try original == fingerprint(url) && beforeWrite.isEmpty, "Pre-move browsing wrote workspace data")
            if phase == "move" {
                try await fire(TaskStorage.reorder)
                visits.append(try inspect(frame(), pages: pages, revision: 2, page: 0, successor: true))
                let committed = try fingerprint(url)
                try check(committed != original, "Move did not persist")
                try await fire("tasks.next")
                visits.append(try inspect(frame(), pages: pages, revision: 2, page: 1, successor: true))
                try await fire("tasks.previous")
                visits.append(try inspect(frame(), pages: pages, revision: 2, page: 0, successor: true))
                try check(try committed == fingerprint(url), "Post-move browsing wrote workspace data")
            }
        }
        return ["phase": phase, "artifact": artifact, "sequence": sequence, "candidate": candidate,
                "previous": health.previousHealthy as Any? ?? NSNull(), "launch": started.launchID as Any? ?? NSNull(),
                "visits": visits, "browseWorkspaceUnchanged": true]
    }

    private static func fingerprint(_ url: URL) throws -> [String] {
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        let identity = try [FileAttributeKey.systemFileNumber, .size, .modificationDate].map {
            String(describing: try need(attributes[$0], "Missing workspace file attribute"))
        }
        return try identity + [ReleaseVerifier.sha256(Data(contentsOf: url))]
    }

    private static func siblings(_ workspace: URL) throws -> [String: [String]] {
        let files = try FileManager.default.contentsOfDirectory(atPath: workspace.path)
        return try Dictionary(uniqueKeysWithValues: files.filter { $0 != "workspace.json" }.map {
            ($0, try fingerprint(workspace.appendingPathComponent($0)))
        })
    }

    private static func inspect(_ document: UIDocument, pages: ArchivedPages, revision: UInt64,
                                page: Int, successor: Bool) throws -> [String: Any] {
        let archive = revision == 1 ? pages.before : pages.after
        let expected = successor ? archive[page].rows : archive.flatMap(\.rows)
        let position = successor ? archive[page].position : "Checklist"
        let children = document.root.children
        let caption = children.first?.properties["text"]?.string
        try check(children.first?.id == "tasks.position" && caption == position,
                  "Checklist page caption at workspace revision \(revision): expected '\(position)', observed '\(caption ?? "missing")'")
        let rows = children.filter { $0.id.hasPrefix("task.") && $0.id.hasSuffix(".title") }
        try check(rows.map(\.id) == expected.map { "task." + $0.id.uuidString.lowercased() + ".title" }
                  && rows.compactMap { $0.properties["text"]?.string } == expected.map(\.text),
                  "Archived checklist identities and Unicode row labels")
        let move = successor && revision == 1 && page == 1
        let actions = successor ? [page == 0 ? "tasks.next" : "tasks.previous"] + (move ? [TaskStorage.reorder] : []) : []
        try check(children.filter { $0.properties["disabled"]?.bool != true }.flatMap(\.actions).map(\.id).sorted() == actions.sorted(), "Exact visible page actions")
        if successor {
            for (id, label, enabled) in [("tasks.next", "Next", page == 0), ("tasks.previous", "Previous", page == 1)] {
                let node = try need(children.first { $0.id == id }, "Missing pagination button \(id)")
                try check(node.properties["label"]?.string == label
                          && node.properties["disabled"]?.bool == !enabled
                          && node.actions == [.init(id: id, event: .activate)],
                          "Pagination control label and availability")
            }
        }
        if move {
            let button = try need(children.first { $0.id == TaskStorage.reorder }, "Missing exact boundary move control")
            try check(button.properties["label"]?.string == "Move up: Verify café drain"
                      && button.actions == [.init(id: TaskStorage.reorder, event: .activate)], "Exact boundary action label")
        }
        return ["position": position, "rows": rows.count, "first": expected.first!.id.uuidString,
                "last": expected.last!.id.uuidString, "actions": actions]
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
