import FieldLogModels
import FieldLogStorage
import Foundation
import MixerCapabilityActivation
import MixerRuntimeIdentity
import MixerUpdates
import SwiftUI

struct SignedTaskLaunch {
    enum Delivery {
        case loopback(UInt16, expectedSequence: UInt64)
        case offline
        case invalid
    }
    let workspace: UUID
    let delivery: Delivery

    static var current: Self? {
        let args = ProcessInfo.processInfo.arguments
        guard let mode = args.firstIndex(of: "--fieldlog-signed-ota"),
              args.indices.contains(mode + 1), let workspace = UUID(uuidString: args[mode + 1]) else { return nil }
        let values = Array(args.dropFirst(mode + 2))
        if values == ["offline"] { return Self(workspace: workspace, delivery: .offline) }
        if values.count == 2, let port = UInt16(values[0]), port > 0,
           let sequence = UInt64(values[1]), (1...3).contains(sequence) {
            return Self(workspace: workspace, delivery: .loopback(port, expectedSequence: sequence))
        }
        return Self(workspace: workspace, delivery: .invalid)
    }
}

struct SignedTaskView: View {
    let launch: SignedTaskLaunch
    @State private var model = SignedTaskModel()

    var body: some View {
        VStack(spacing: 12) {
            Text("FieldLog Signed OTA").font(.headline)
            Text(model.release).accessibilityIdentifier("ota-release")
            if let owner = model.owner {
                MixerGuestScreen(presentation: owner.presentation)
                    .allowsHitTesting(model.healthy && !model.needsReopen && !model.saving && !model.closeRequested)
                    .accessibilityHidden(model.needsReopen)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            Text(model.savedTask).accessibilityIdentifier("ota-saved-task")
            Text(model.evidence).accessibilityIdentifier("ota-evidence")
                .font(.caption2).lineLimit(2)
            if model.needsReopen {
                Button("Reopen saved task") { Task { await model.reopenTask() } }
                    .disabled(!model.healthy || model.saving || model.closeRequested)
            }
            if let error = model.error {
                Text(error).accessibilityIdentifier("ota-error")
            }
            Button("Close signed task") { model.closeRequested = true }
                .disabled(!model.healthy || model.saving || model.closeRequested)
        }
        .padding()
        .task { await model.run(launch) }
    }
}

@MainActor
@Observable final class SignedTaskModel {
    var owner: CapabilityGuestUIRuntime?
    var release = "Opening signed task"
    var savedTask = "Reading workspace"
    var evidence = "Waiting for native first screen"
    var error: String?
    var healthy = false
    var needsReopen = false
    var saving = false
    var closeRequested = false
    private var repository: WorkspaceRepository?
    private var workspace = Workspace()
    private var taskID: UUID?
    private var frameRevision: UInt64 = 1

    func run(_ launch: SignedTaskLaunch) async {
        var failure: String?
        do {
            try await openAndObserve(launch)
            release = "Closing signed task"
        } catch {
            failure = String(describing: error)
        }
        do {
            try await retire()
            if failure == nil { release = "Signed task closed" }
        } catch {
            failure = failure.map { "\($0) | retirement: \(error)" } ?? String(describing: error)
        }
        self.error = failure
    }

    private func openAndObserve(_ launch: SignedTaskLaunch) async throws {
        let material = Bundle.main.resourceURL!.appendingPathComponent("Installed")
        let identityBytes = try Data(contentsOf: material.appendingPathComponent("identity.json"))
        let identity = try CapabilityRuntimeIdentity(json: identityBytes)
        guard identity.descriptor.object?["application"]?.object?["bundle_id"]?.text == Bundle.main.bundleIdentifier else {
            throw UpdateError("fixture.identity", "Bundle identifier differs from embedded installed identity")
        }
        let applicationSupport = try FileManager.default.url(
            for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
        let container = applicationSupport.appendingPathComponent("FieldLogSignedOTA-" + launch.workspace.uuidString)
        try FileManager.default.createDirectory(at: container, withIntermediateDirectories: true)
        let execution = try InstalledCapabilityExecution(identityJSON: identityBytes, materials: [
            .init(role: .bridgePolicy, bytes: Data(contentsOf: material.appendingPathComponent("bridge.json"))),
        ], trustRootsJSON: Data(contentsOf: material.appendingPathComponent("roots.json")), privateContainer: container)
        let configuration = CapabilityColdStartConfiguration(directory: container.appendingPathComponent("recovery"),
            channel: "beta", installation: "fieldlog-ios-local", observationSeconds: 1)
        let repository = try WorkspaceRepository(directory: container.appendingPathComponent("workspace"))
        self.repository = repository
        workspace = await repository.snapshot()
        if workspace.tasks.isEmpty, case .loopback(_, 1) = launch.delivery {
            workspace = try await repository.transact(expectedRevision: 0) { state in
                let project = try state.createProject(title: "FieldLog inspection", site: "Local OTA verification")
                try state.saveTask(projectID: project, title: "Inspect pump", responsible: "FieldLog")
            }
        }
        guard workspace.tasks.count == 1, let task = workspace.tasks.first else {
            throw UpdateError("fixture.workspace", "Expected the same isolated FieldLog task")
        }
        taskID = task.id
        needsReopen = task.completed
        showSavedTask()
        let owner = try await CapabilityGuestUIRuntime.open(configuration: configuration, execution: execution)
        self.owner = owner
        let before = await owner.recoverySnapshot()
        let sequence: UInt64
        let candidate: String
        let label: String
        switch launch.delivery {
        case let .loopback(port, expected):
            guard before.acceptedSequence == expected - 1 else {
                throw UpdateError("fixture.sequence", "Unexpected starting high-water mark")
            }
            try await stage(owner, scope: identity.installedRuntime.scope, fingerprint: execution.runtimeFingerprint,
                            port: port, sequence: expected, installation: configuration.installation)
            let staged = await owner.recoverySnapshot()
            guard staged.acceptedSequence == expected, let id = staged.staged else {
                throw UpdateError("fixture.stage", "Expected a staged assignment")
            }
            sequence = expected
            candidate = id
            label = ["Baseline", "Reviewed", "Rollback"][Int(expected - 1)]
        case .offline:
            guard before.acceptedSequence == 3, let id = before.healthy else {
                throw UpdateError("fixture.offline", "Expected rollback retained in the app-private store")
            }
            sequence = before.acceptedSequence
            candidate = id
            label = "Offline rollback"
        case .invalid:
            throw UpdateError("fixture.arguments", "Invalid signed OTA launch")
        }
        let startup = try await owner.start()
        guard startup.candidateID == candidate, let launchID = startup.launchID else {
            throw UpdateError("fixture.start", "Selected candidate differs from the staged or retained candidate")
        }
        let deadline = ContinuousClock.now + .seconds(25)
        while !closeRequested {
            let current = await owner.recoverySnapshot()
            guard current.activation.candidateID == candidate, current.activation.terminalCause == nil,
                  current.activation.firstBridgeFailure == nil, current.activation.firstUIProtocolFailure == nil else {
                throw UpdateError("fixture.activation", String(describing: current.activation))
            }
            if !healthy {
                guard ContinuousClock.now < deadline else {
                    throw UpdateError("fixture.health", "Native first-screen health did not commit")
                }
                if current.activation.phase == .healthyGuest, current.healthy == candidate {
                    guard let initial = owner.presentation.fieldLogTaskFrame,
                          initial.revision == 1, initial.status == "Open", initial.title == task.title else {
                        throw UpdateError("fixture.task_binding", "Signed first screen did not match the saved inspection task")
                    }
                    if sequence > 1, current.previousHealthy == nil {
                        throw UpdateError("fixture.previous_health", "Previous healthy candidate was lost")
                    }
                    healthy = true
                    release = "\(label) healthy · sequence \(sequence)"
                    evidence = "candidate=\(candidate) launch=\(launchID)"
                }
            }
            if healthy, let frame = owner.presentation.fieldLogTaskFrame, frame.revision > frameRevision {
                guard frame.title == task.title, frame.revision == frameRevision + 1,
                      frame.deliveredSequence == frame.revision - 1 else {
                    throw UpdateError("fixture.event", "Displayed task change lacks its matching delivered native event")
                }
                switch frame.status {
                case "Review required":
                    guard sequence == 2, frame.revision == 2, workspace.tasks.first?.completed == false else {
                        throw UpdateError("fixture.review", "Review must preserve the open task")
                    }
                case "Completed": try await setCompletion(true)
                case "Open": try await setCompletion(false)
                default: throw UpdateError("fixture.frame", "Unexpected signed task status")
                }
                frameRevision = frame.revision
            }
            try await Task.sleep(for: .milliseconds(20))
        }
    }

    func reopenTask() async {
        guard needsReopen, !saving, healthy, !closeRequested else { return }
        do {
            try await setCompletion(false)
            needsReopen = false
        } catch { self.error = String(describing: error) }
    }

    private func showSavedTask() {
        let completion = workspace.tasks.first?.completed == true ? "completed" : "open"
        savedTask = "Saved task \(completion) · revision \(workspace.revision) · outbox \(workspace.outbox.count)"
    }

    private func setCompletion(_ completed: Bool) async throws {
        guard let repository, let taskID else { throw FieldLogError.missingRecord }
        saving = true
        defer { saving = false }
        workspace = try await repository.transact(expectedRevision: workspace.revision) { state in
            guard let task = state.tasks.first(where: { $0.id == taskID }), task.completed != completed else {
                throw FieldLogError.staleRevision
            }
            try state.toggleTask(taskID)
        }
        showSavedTask()
    }

    private func retire() async throws {
        if let owner {
            try await owner.closeFieldLogSignedTask()
            self.owner = nil
        }
        await repository?.close()
        repository = nil
    }

    private func stage(_ owner: CapabilityGuestUIRuntime, scope: UpdateScope, fingerprint: String,
                       port: UInt16, sequence: UInt64, installation: String) async throws {
        let origin = "http://127.0.0.1:\(port)"
        let route = "/v3/updates?organization=\(scope.organization)&project=\(scope.project)&app=\(scope.app)" +
            "&environment=\(scope.environment)&platform=\(scope.platform)&runtime=\(fingerprint)" +
            "&channel=beta&installation=\(installation)"
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 4
        configuration.timeoutIntervalForResource = 6
        let session = URLSession(configuration: configuration)
        defer { session.invalidateAndCancel() }

        func fetch(_ path: String) async throws -> [String: CanonicalValue] {
            let url = URL(string: origin + path)!
            let (data, response) = try await session.data(from: url)
            guard response.url == url, (response as? HTTPURLResponse)?.statusCode == 200,
                  let fields = try StrictJSON.decode(CanonicalValue.self, from: data, maximumBytes: 65_536).object else {
                throw UpdateError("fixture.download", "Unexpected loopback response")
            }
            return fields
        }
        let offer = try await fetch(route)
        guard let assignment = offer["signed_assignment"],
              let fields = assignment.object?["assignment"]?.object,
              fields["sequence"]?.uint == sequence, let digest = fields["artifact_sha256"]?.text,
              digest.utf8.count == 64, digest.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
            throw UpdateError("fixture.assignment", "Unexpected release assignment")
        }
        let expected = "/v3/artifacts/\(digest)?organization=\(scope.organization)&project=\(scope.project)"
        guard offer["artifact_url"]?.text == expected else {
            throw UpdateError("fixture.artifact_url", "Unexpected scoped artifact route")
        }
        let artifact = try await fetch(expected)
        guard let manifest = artifact["signed_manifest"], let encoded = artifact["payload"]?.text,
              let payload = Data(base64Encoded: encoded), payload.count <= 4096 else {
            throw UpdateError("fixture.artifact", "Missing signed compact FieldLog artifact")
        }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        try await owner.beginDownload(signedManifest: encoder.encode(manifest), signedAssignment: encoder.encode(assignment))
        try await owner.appendDownload(payload, atOffset: 0)
        try await owner.finishDownload()
    }
}
