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
            try PagerStorage.seed(URL(fileURLWithPath: args[6]), into: workspace)
            return
        }

        let phase = args[1]
        let identity = try read(work, "identity.json")
        let roots = try read(work, "roots.json")
        let descriptor = try CapabilityRuntimeIdentity(json: identity)
        try check(descriptor.capabilityExecution.turnMilliseconds == 50, "Strict VM turn budget")
        let host = descriptor.installedRuntime
        let repository = try WorkspaceRepository(directory: workspace)
        let storage = PagerStorage(repository)
        let before = await repository.snapshot()
        let beforeBytes = try read(workspace, "workspace.json")
        try check(before.id == PagerStorage.workspaceID && before.revision == 1
                  && before.outbox.count == 46 && beforeBytes == encode(before), "Exact cold workspace")
        let fileBefore = try fileIdentity(workspace.appendingPathComponent("workspace.json"))
        let materials = try Release.materials.map { name, role in
            CapabilityMaterialFile(role: role, bytes: try read(work, name))
        }
        let execution = try InstalledCapabilityExecution(identityJSON: identity, materials: materials,
            trustRootsJSON: roots, privateContainer: work,
            applicationStorage: .init(runtimeFingerprint: host.runtime, namespace: PagerStorage.namespace,
                                      service: storage, allowsDeferredGuestUIStartup: true))
        let owner = try await CapabilityGuestUIRuntime.open(configuration: .init(
            directory: work.appendingPathComponent("recovery"), channel: "beta",
            installation: Release.installation, observationSeconds: 1), execution: execution)
        let result: Result<[String: Any], Error>
        do {
            let port = try need(Int(args[3]), "Loopback port")
            result = .success(try await observe(owner, work: work, phase: phase, host: host, port: port))
        } catch {
            result = .failure(UpdateError("f20.observe", "\(error) (reads: \(await storage.reads))"))
        }
        await owner.close()
        await repository.close()
        let recovery = await owner.recoverySnapshot()
        let retired = owner.ownerRetired && recovery.closed && !recovery.incompleteAttempt
            && !recovery.activation.cleanupPending
        if !retired {
            let state = "retired=\(owner.ownerRetired), closed=\(recovery.closed), incomplete=\(recovery.incompleteAttempt), cleanup=\(recovery.activation.cleanupPending)"
            if case .failure(let error) = result { throw UpdateError("f20.retirement", "\(error) (\(state))") }
            throw UpdateError("f20.retirement", state)
        }
        var report = try result.get()
        let afterBytes = try read(workspace, "workspace.json")
        let cold = try WorkspaceRepository(directory: workspace)
        let after = await cold.snapshot()
        await cold.close()

        let refusedWrites = await storage.refusedWrites
        let reads = await storage.reads
        let fileAfter = try fileIdentity(workspace.appendingPathComponent("workspace.json"))
        try check(before == after && beforeBytes == afterBytes && fileBefore == fileAfter
                  && refusedWrites == 0, "Browse/open changed workspace or attempted a write")
        report["outboxSHA256"] = ReleaseVerifier.sha256(try encode(after.outbox))
        report["outboxCount"] = after.outbox.count
        report["revision"] = after.revision
        report["reads"] = reads
        report["writeAttempts"] = refusedWrites
        report["fileIdentity"] = fileAfter
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
        let online = ["prior", "exact", "rollback"].contains(phase)
        let sequence: UInt64 = phase == "prior" ? 1 : (["exact", "exact-cold"].contains(phase) ? 2 : 3)
        let release = sequence == 2 ? "exact" : (sequence == 1 ? "prior" : "rollback")
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
        let initial = renderer.snapshot.document.root.children
        try check(initial.map(\.id) == [reviewed ? "workspace.entries" : "workspace.home"],
                  "Historical Android route admission changed")
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

        let draftID = "F2000000-0000-4000-8000-000000000220"
        var pages: [[String: Any]] = []
        var opened: [String: String] = [:]

        func capture(_ family: String) throws {
            let frame = try need(model.renderHost, "Page frame")
            let document = frame.snapshot.document
            let prefix = family == "drafts" ? "draft." : "entry."
            let label = family == "drafts" ? "label" : "text"
            let rows = document.root.children.filter { $0.id.hasPrefix(prefix) }
            try check(rows.allSatisfy { node in
                if family == "drafts" {
                    return node.kind == .button && node.actions == [.init(id: node.id, event: .activate)]
                }
                return node.kind == .text && node.actions.isEmpty
            }, "Draft action or committed-row read-only contract")
            var evidence: [String: Any] = [
                "family": family,
                "ids": rows.map { String($0.id.dropFirst(prefix.count)) },
                "labels": try rows.map { try need($0.properties[label]?.string, "Archived row label") },
            ]
            evidence["position"] = try need(document.root.children.first { $0.id == family + ".position" }?
                .properties["text"]?.string, "Page position")
            for direction in ["previous", "next"] {
                let id = family + "." + direction
                let node = try need(document.root.children.first { $0.id == id }, "Pager button")
                let disabled = try need(node.properties["disabled"]?.bool, "Pager button enabled state")
                if disabled {
                    let identity = try need(frame.snapshot.identity(for: id), "Disabled pager identity")
                    do {
                        _ = try frame.route(.init(revision: revision, identity: identity, event: .activate))
                        throw UpdateError("f20.pager", "Disabled pager routed an action")
                    } catch UIRoutingError.disabledNode {}
                }
                evidence[direction + "Enabled"] = !disabled
            }
            pages.append(evidence)
        }

        if reviewed {
            try await fire("workspace.entries")
            try capture("drafts")
            try await fire("drafts.next")
            try capture("drafts")
            try await fire("draft." + draftID)
            let detail = try need(model.renderHost, "Saved draft detail").snapshot.document.root.children
            try check(detail.map(\.id) == ["detail.back", "draft.title", "draft.note"]
                      && detail.flatMap(\.actions) == [.init(id: "detail.back", event: .activate)],
                      "No-edit detail unexpectedly exposes a mutation")
            opened = ["id": draftID,
                      "title": try need(detail[1].properties["text"]?.string, "Draft title"),
                      "note": try need(detail[2].properties["text"]?.string, "Draft note")]
            try await fire("detail.back")
            try capture("drafts")
            try await fire("show.entries")
            try capture("entries")
            try await fire("entries.next")
            try capture("entries")
            try await fire("show.drafts")
            try capture("drafts")
            try await fire("drafts.previous")
            try capture("drafts")
            try await fire("show.entries")
            try capture("entries")
            try await fire("entries.next")
            try capture("entries")
            try await fire("entries.previous")
            try capture("entries")
            try await fire("entries.previous")
            try capture("entries")
            try await fire("workspace.tasks")
        }
        let final = try need(model.renderHost, "Home frame").snapshot.document.root.children
        try check(final.map(\.id) == initial.map(\.id), "Return to the assigned workspace route")

        return ["phase": phase, "artifact": artifact, "sequence": sequence, "candidate": candidate,
                "previous": health.previousHealthy as Any? ?? NSNull(), "launch": started.launchID as Any? ?? NSNull(),
                "initialNodes": initial.map(\.id), "pages": pages, "openedDraft": opened, "deliveredEvents": revision - 1]
    }

    private static func fileIdentity(_ url: URL) throws -> [String] {
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        return try [FileAttributeKey.systemFileNumber, .size, .modificationDate].map {
            String(describing: try need(attributes[$0], "Missing workspace file attribute"))
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
