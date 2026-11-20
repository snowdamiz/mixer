import FieldLogInstalledGuest
import FieldLogStorage
import Foundation
import MixerCapabilities
@_spi(FieldLogStartupDiagnostics) @testable import MixerCapabilityActivation
import MixerRuntimeIdentity
import MixerUI
import MixerUpdates

func check(_ condition: Bool, _ message: String) throws {
    if !condition { throw UpdateError("fixture.assertion", message) }
}

guard CommandLine.arguments.count == 3 else {
    throw UpdateError("fixture.arguments", "Pass a signed fixture and a new work directory")
}
let fixture = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let work = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
let container = work.appending(path: "recovery", directoryHint: .isDirectory)
let state = container.appending(path: "state.json")
let installation = "885d11ae-0000-4000-8000-000000000004"
try FileManager.default.createDirectory(at: work, withIntermediateDirectories: false)
let workspaceDirectory = work.appending(path: "workspace", directoryHint: .isDirectory)
let workspaceFile = workspaceDirectory.appending(path: "workspace.json")
let repository = try WorkspaceRepository(directory: workspaceDirectory)
let title = "Inspect pump"
let project = try await repository.transact { state in
    try state.createProject(title: "Checklist workshop", site: "Yard")
}
let projectID = project.projects[0].id
let saved = try await repository.transact { state in
    try state.saveTask(projectID: projectID, title: title, responsible: "Night shift")
}
let savedBytes = try Data(contentsOf: workspaceFile)
let task = saved.tasks[0]
try check(saved.revision == 2 && saved.outbox.count == 2 && !task.completed, "Unexpected saved workspace seed")

func read(_ path: String) throws -> Data {
    try Data(contentsOf: fixture.appending(path: path))
}

let identityBytes = try read("Installed/identity.json")
let identity = try CapabilityRuntimeIdentity(json: identityBytes)
let storage = InstalledApplicationStorage(runtimeFingerprint: identity.fingerprint, namespace: FieldLogTaskStorage.namespace,
    service: FieldLogTaskStorage(repository: repository, projectID: projectID, taskID: task.id),
    allowsDeferredGuestUIStartup: true)
let storageID = CapabilitySchemas.storageID
let materials: [CapabilityMaterialFile] = try [
    .init(role: .bridgePolicy, bytes: read("Installed/bridge.json")),
    .init(role: .configuration(capabilityID: storageID), bytes: read("Installed/storage.json")),
    .init(role: .installedGrant(capabilityID: storageID), bytes: read("Installed/storage-grant.json")),
]
let execution = try InstalledCapabilityExecution(identityJSON: identityBytes, materials: materials,
    trustRootsJSON: read("Installed/roots.json"), privateContainer: work, applicationStorage: storage)
try check(execution.runtimeFingerprint == identity.fingerprint, "Installed material runtime changed")
let configuration = CapabilityColdStartConfiguration(directory: container, channel: "beta",
    installation: installation, observationSeconds: 1)

func begin(_ owner: CapabilityGuestUIRuntime, _ name: String) async throws {
    try await owner.beginDownload(signedManifest: read(name + "/signed-manifest.json"),
                                  signedAssignment: read(name + "/assignment.json"))
}

func stage(_ owner: CapabilityGuestUIRuntime, _ name: String, sequence: UInt64) async throws -> String {
    try await begin(owner, name)
    try await owner.appendDownload(read(name + "/payload.wasm"), atOffset: 0)
    try await owner.finishDownload()
    let snapshot = await owner.recoverySnapshot()
    guard let staged = snapshot.staged, snapshot.acceptedSequence == sequence, snapshot.downloading == nil else {
        throw UpdateError("fixture.assertion", "\(name) did not stage at sequence \(sequence)")
    }
    return staged
}

func checkWorkspace() async throws {
    let actual = try await repository.readCommittedSnapshot()
    try check(actual == saved && Data(contentsOf: workspaceFile) == savedBytes, "Saved workspace changed")
}

func inventory() throws -> [String] {
    try FileManager.default.contentsOfDirectory(atPath: container.path).sorted()
}

struct StartupDiagnostic: Decodable {
    struct Startup: Decodable {
        let acceptedStoreMilestones: [String]
        let sameLaunchHealthCommitted: Bool
    }
    let startup: Startup
}

@MainActor
func checkFirstFrame(_ owner: CapabilityGuestUIRuntime, candidate: String) async throws {
    let started = try await owner.start()
    guard let launch = started.launchID, started.candidateID == candidate,
          started.phase == .provisionalGuest, started.effectsMayHaveOpened else {
        throw UpdateError("fixture.first_frame", "Signed guest did not start provisionally")
    }
    let deadline = ContinuousClock.now + .milliseconds(900)
    while ContinuousClock.now < deadline {
        if let document = owner.presentation.renderHost?.snapshot.document {
            let children = document.root.children
            let status = children.first { $0.id == "status" }?.properties["text"]?.string
            let action = children.first { $0.id == "toggle" }?.properties["label"]?.string
            try check(document.revision == 1 && status == "Open" && action == "Complete task",
                      "Wrong first frame from the saved workspace")
            guard let bytes = owner.startupDiagnostic(launchID: launch) else {
                throw UpdateError("fixture.first_frame", "Missing diagnostics for the same launch")
            }
            let startup = try JSONDecoder().decode(StartupDiagnostic.self, from: bytes).startup
            try check(startup.acceptedStoreMilestones == ["feature_started"] && !startup.sameLaunchHealthCommitted,
                      "Unexpected headless milestone state")
            try await checkWorkspace()
            return
        }
        try await Task.sleep(for: .milliseconds(10))
    }
    throw UpdateError("fixture.first_frame", "Signed guest did not produce a first frame")
}

func retire(_ owner: CapabilityGuestUIRuntime) async throws {
    // Match the bounded owner retirement in FieldLogSignedTask.close().
    await owner.close()
    let deadline = ContinuousClock.now + .seconds(8)
    repeat {
        let terminal = await owner.recoverySnapshot()
        try check(terminal.closed && !terminal.incompleteAttempt, "Owner retained an active attempt")
        if !terminal.activation.cleanupPending { return }
        try await Task.sleep(for: .milliseconds(20))
    } while ContinuousClock.now < deadline
    throw UpdateError("fixture.cleanup", "Host guest retirement is still pending")
}

@MainActor
func withOwner<T>(_ body: (CapabilityGuestUIRuntime) async throws -> T) async throws -> T {
    let owner = try await CapabilityGuestUIRuntime.open(configuration: configuration, execution: execution)
    let result: Result<T, Error>
    do { result = .success(try await body(owner)) }
    catch { result = .failure(error) }
    try await retire(owner)
    return try result.get()
}

do {
    let baseline = try await withOwner { owner in
        let candidate = try await stage(owner, "baseline", sequence: 1)
        let seededBytes = try Data(contentsOf: state)
        let seededFiles = try inventory()
        for (name, expected) in [
            ("revoked-artifact", "v3.signature.authority"),
            ("revoked-assignment", "v3.signature.authority"),
            ("wrong-runtime", "v3.manifest.compatibility"),
        ] {
            do {
                try await begin(owner, name)
                throw UpdateError("fixture.unexpected_admission", name)
            } catch let error as UpdateError {
                try check(error.code == expected, "\(name): \(error.code)")
            }
            let snapshot = await owner.recoverySnapshot()
            try check(snapshot.acceptedSequence == 1 && snapshot.staged == candidate && snapshot.downloading == nil,
                      "Rejected offer modified staging for \(name)")
            try check(Data(contentsOf: state) == seededBytes && inventory() == seededFiles,
                      "Rejected offer modified durable recovery for \(name)")
            try await checkWorkspace()
            print("\(name): \(expected), recovery and workspace byte-identical")
        }
        try await checkFirstFrame(owner, candidate: candidate)
        print("baseline: sequence 1, feature_started, saved Open task in validated first frame")
        return candidate
    }
    try await withOwner { owner in
        let reopened = await owner.recoverySnapshot()
        try check(reopened.acceptedSequence == 1, "Accepted sequence was lost across owner reopen")
        let replacement = try await stage(owner, "replacement", sequence: 2)
        try check(replacement != baseline, "Replacement reuses the baseline candidate")
        let durable = try JSONSerialization.jsonObject(with: Data(contentsOf: state)) as? [String: Any]
        try check(durable?["installation"] as? String == installation, "Durable installation identifier changed")
        try await checkFirstFrame(owner, candidate: replacement)
        print("replacement: sequence 2, same installation, feature_started, saved Open task in validated first frame")
    }
    try await checkWorkspace()
    print("retired both host owners, workspace SHA-256 \(ReleaseVerifier.sha256(savedBytes))")
} catch {
    await repository.close()
    throw error
}
await repository.close()
