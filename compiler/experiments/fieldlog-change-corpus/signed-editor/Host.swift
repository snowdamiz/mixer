import Crypto
import FieldLogModels
import FieldLogStorage
import Foundation
import MixerUI
import MixerUpdates
@_spi(InstalledApplicationStorage) import MixerCapabilities
@_spi(GuestUIV1) @_spi(FeatureUIV3) @_spi(FieldLogSignedEditorHost) import MixerGuest
@_spi(GuestUIV1) @_spi(CapabilityLifecycle) import MixerExperimentalCapabilityRuntime

private struct CheckFailure: Error { let message: String }
private func check(_ test: Bool, _ message: String) throws {
    guard test else { throw CheckFailure(message: message) }
}
private func refuse(_ code: String, _ body: () throws -> Void) throws {
    do { try body() } catch let error as UpdateError where error.code == code { return }
    throw CheckFailure(message: "Expected signed admission refusal \(code)")
}

private let namespace = "fieldlog-editor"
private let storageGrant = CapabilityGrant(capabilityID: CapabilitySchemas.storageID,
    schemaSHA256: CapabilitySchemas.storageSHA256, permissions: ["storage.appPrivate"], namespaces: [namespace])

// This scope has no read/delete authority or generic key-value interface.
// The project and repository come from the host, never from guest arguments.
private actor TaskSave: InstalledApplicationStorageServing {
    let repository: WorkspaceRepository
    let project: UUID
    var attempted = false

    init(repository: WorkspaceRepository, project: UUID) {
        self.repository = repository
        self.project = project
    }
    func get(_ arguments: KVGetArguments) throws -> KVGetResponse { throw CapabilityFailure.permissionDenied }
    func delete(_ arguments: KVDeleteArguments) throws -> KVMutationResponse { throw CapabilityFailure.permissionDenied }
    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse {
        guard !attempted, arguments.namespace == namespace, arguments.key == "new-task",
              let bytes = Data(base64Encoded: arguments.valueBase64), bytes.count <= min(maximumTotalBytes, 3072),
              maximumEntries >= 1, let fields = try StrictJSON.decode(CanonicalValue.self, from: bytes).object,
              Set(fields.keys) == ["title", "responsible"],
              let title = fields["title"]?.text, let responsible = fields["responsible"]?.text else {
            throw CapabilityWireError.invalid("FieldLog task request")
        }
        try Workspace.text(title, label: "Task", maximum: 240, required: true)
        try Workspace.text(responsible, label: "Responsible person", maximum: 160)
        try Task.checkCancellation()
        attempted = true // A failed/ambiguous disk commit cannot cause another write in this session.
        _ = try await repository.transact { try $0.saveTask(projectID: self.project, title: title, responsible: responsible) }
        return KVMutationResponse(committed: true)
    }
}

private final class Retirement: CapabilityBridgeTerminalObserver, CapabilityBridgeRetirementObserver, @unchecked Sendable {
    private let lock = NSLock()
    private var terminal: ExperimentalCapabilityFailure?
    private var retired = false
    func recordTerminalFailure(_ failure: ExperimentalCapabilityFailure) { lock.withLock { terminal = failure } }
    func recordRetired() { lock.withLock { retired = true } }
    var clean: Bool { lock.withLock { retired && terminal == nil } }
    var didRetire: Bool { lock.withLock { retired } }
    var failure: ExperimentalCapabilityFailure? { lock.withLock { terminal } }
}

private struct SigningAuthority {
    let scope = UpdateScope(organization: "mixer-local", project: "fieldlog", app: "fieldlog",
                            environment: "development", platform: "ios")
    let key = Curve25519.Signing.PrivateKey()
    let keyID = "f05-ephemeral"
    let runtime: String
    let memoryBytes: UInt64 = 65_536
    let fuel: UInt64 = 1_000_000
    let revision: String
    let now = UInt64(Date().timeIntervalSince1970)

    init(identity: String, revision: String) {
        self.revision = revision
        runtime = ReleaseVerifier.sha256(Data("fieldlog.editor.host.v1\0\(identity)".utf8) + key.publicKey.rawRepresentation)
    }
    func verifier(runtime: String, grants: Bool) throws -> ReleaseVerifierV3 {
        let hashes = grants ? [storageGrant.capabilityID: storageGrant.schemaSHA256] : [:]
        return try ReleaseVerifierV3(host: InstalledRuntime(scope: scope, runtime: runtime,
            protocolVersion: 3, guestABI: 2, uiSchema: 1, capabilityHashes: hashes, stateVersion: 0,
            maxPayloadBytes: 4_194_304, limits: ResourceLimits(memoryBytes: memoryBytes,
                fuel: fuel, startupMilliseconds: 5_000)),
            roots: [TrustRoot(keyID: keyID, publicKey: key.publicKey.rawRepresentation,
                              scope: scope, artifact: true, assignment: true)])
    }
    func envelope(_ value: CanonicalValue, _ field: String, _ domain: String) throws -> Data {
        let signature = try key.signature(for: Data("mixer.\(domain).v3\0".utf8) + value.canonicalCBOR())
        return try JSONEncoder().encode(CanonicalValue.object([field: value, "signature": .text(signature.base64EncodedString())]))
    }
    func authorize(_ bytes: Data, grant: Bool, legacyRuntime: String, checkRefusals: Bool) throws -> CapabilityPolicy {
        let verifier = try verifier(runtime: runtime, grants: true)
        let scopeValue = try StrictJSON.decode(CanonicalValue.self, from: JSONEncoder().encode(scope))
        let name = "fieldlog-f05"
        let entry = CanonicalValue.object([
            "capability_id": .text(storageGrant.capabilityID), "schema_sha256": .text(storageGrant.schemaSHA256),
            "permissions": .array([.text("storage.appPrivate")]), "namespaces": .array([.text(namespace)]),
            "origins": .array([]), "methods": .array([]),
        ])
        let manifest = CanonicalValue.object([
            "schema": .uint(3), "scope": scopeValue, "release_id": .text(name),
            "source_commit": .text(revision), "provenance_id": .text("fieldlog-corpus-private"),
            "runtime": .text(runtime), "protocol": .uint(3), "guest_abi": .uint(2), "ui_schema": .uint(1),
            "capability_hashes": .object(verifier.host.capabilityHashes.mapValues(CanonicalValue.text)),
            "state_min": .uint(0), "state_max": .uint(0), "payload_sha256": .text(ReleaseVerifier.sha256(bytes)),
            "compressed_bytes": .uint(UInt64(bytes.count)), "expanded_bytes": .uint(UInt64(bytes.count)),
            "compression": .text("none"), "asset_hashes": .object([:]),
            "source_map_sha256": .text(ReleaseVerifier.sha256(Data("{}".utf8))),
            "limits": .object(["memory_bytes": .uint(memoryBytes), "fuel": .uint(fuel), "startup_milliseconds": .uint(5_000)]),
            "key_id": .text(keyID), "created_at_unix": .uint(now),
            "capability_grants": .object(["schema": .uint(1),
                "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256), "entries": .array(grant ? [entry] : [])]),
        ])
        let signedManifest = try envelope(manifest, "manifest", "artifact")
        let artifact = try verifier.verifyArtifact(signedManifest: signedManifest, payload: bytes, now: now)
        let assignment = try envelope(.object([
            "schema": .uint(3), "scope": scopeValue, "channel": .text("local"), "cohort": .text("sha256-v1"),
            "rollout_basis_points": .uint(10_000), "sequence": .uint(1), "release_id": .text(name),
            "artifact_sha256": .text(artifact.artifactSHA256), "runtime": .text(runtime),
            "key_id": .text(keyID), "created_at_unix": .uint(now),
        ]), "assignment", "assignment")
        _ = try verifier.verifyAssignment(signedAssignment: assignment, artifact: artifact, channel: "local",
            installation: "f05-host", lastSequence: 0, now: now)
        if checkRefusals {
            var tampered = bytes
            tampered[tampered.startIndex] ^= 1
            try refuse("v3.payload.integrity") {
                _ = try verifier.verifyArtifact(signedManifest: signedManifest, payload: tampered, now: now)
            }
            let legacy = try self.verifier(runtime: legacyRuntime, grants: true)
            try refuse("v3.manifest.compatibility") {
                _ = try legacy.verifyArtifact(signedManifest: signedManifest, payload: bytes, now: now)
            }
            try refuse("v3.assignment.replay") {
                _ = try verifier.verifyAssignment(signedAssignment: assignment, artifact: artifact, channel: "local",
                    installation: "f05-host", lastSequence: 1, now: now)
            }
            print("signed controls: tampered payload, legacy runtime and replayed assignment refused")
        }
        let grants = artifact.capabilityGrants.entries.map {
            CapabilityGrant(capabilityID: $0.capabilityID, schemaSHA256: $0.schemaSHA256,
                permissions: Set($0.permissions), namespaces: Set($0.namespaces))
        }
        return try CapabilityPolicy(installed: [storageGrant], manifest: grants)
    }
}

private func wait<T>(_ what: String, _ poll: () throws -> T?) async throws -> T {
    let deadline = ContinuousClock.now + .seconds(5)
    repeat {
        if let value = try poll() { return value }
        try await Task.sleep(for: .milliseconds(2))
    } while ContinuousClock.now < deadline
    throw CheckFailure(message: "Timed out waiting for \(what)")
}

private struct Presentation {
    let exchange: GuestUIExchangeV1
    var reconciler = UIReconciler(validator: FeatureDocumentV3(textValuePolicy: .standard).validator)

    mutating func next(after revision: UInt64, outcome: UInt64? = nil) async throws -> UIRenderSnapshot {
        let claim: GuestUIPresentationClaimV1 = try await wait("frame after \(revision)") {
            try check(exchange.snapshot().stop == nil, "Guest stopped: \(String(describing: exchange.snapshot().stop))")
            guard let claim = exchange.claimPresentation(generation: 1) else { return nil }
            if claim.frame == nil {
                _ = exchange.completePresentation(claim, snapshot: nil)
                return nil
            }
            return claim
        }
        guard let document = claim.frame?.document.document else { throw CheckFailure(message: "Missing frame") }
        try check(document.revision > revision, "Stale new frame")
        if let outcome {
            try check(claim.eventResult?.sequence == outcome && claim.eventResult?.outcome == .delivered,
                "Accepted input did not settle exactly once")
        }
        try reconciler.apply(document)
        let snapshot = try reconciler.currentSnapshot()
        try check(exchange.completePresentation(claim, snapshot: snapshot) != nil, "Frame refused by exchange")
        return snapshot
    }
    func event(_ snapshot: UIRenderSnapshot, _ id: String, _ event: UIEventKind, _ value: UIValue = .null) throws -> UIEventEnvelope {
        guard let identity = snapshot.identity(for: id) else { throw CheckFailure(message: "Missing " + id) }
        return UIEventEnvelope(revision: snapshot.document.revision, identity: identity, event: event, value: value)
    }
    func send(_ event: UIEventEnvelope) async throws -> UInt64 {
        try await wait("input admission") {
            switch exchange.offer(event, generation: 1) {
            case .busy: return nil
            case .accepted(let sequence): return sequence
            case let failure: throw CheckFailure(message: "Input refused: \(failure)")
            }
        }
    }
    func reject(_ event: UIEventEnvelope, because want: GuestUIEventAdmissionV1) async throws {
        let actual: GuestUIEventAdmissionV1 = try await wait("refusal") {
            let result = exchange.offer(event, generation: 1)
            return result == .busy ? nil : result
        }
        try check(actual == want, "Expected \(want), got \(actual)")
    }
}

private func node(_ root: UINode, _ id: String) -> UINode? {
    if root.id == id { return root }
    return root.children.lazy.compactMap { node($0, id) }.first
}

private func run(_ module: Data, expected: UIDocument, mode: String, directory: URL,
                 policy: CapabilityPolicy) async throws {
    let repository = try WorkspaceRepository(directory: directory)
    let initial = try await repository.transact { _ = try $0.createProject(title: "Inspection", site: "Site") }
    guard let project = initial.projects.first?.id else { throw CheckFailure(message: "Missing project") }
    let storage = TaskSave(repository: repository, project: project)
    let report = Retirement()
    let adapter = InstalledApplicationStorageAdapter(service: storage, maximumTotalBytes: 3072, maximumEntries: 1)
    let group = OwnedCapabilityAdapterGroup(http: nil, applicationStorage: adapter, terminal: report, retirement: report)
    defer { group.closeIfUntransferred() }
    let configuration = ExperimentalCapabilityConfiguration(memoryPages: 1)
    try await ExperimentalCapabilityValidator.prepareGuestUIV1(module: module, configuration: configuration).validate()
    let exchange = try GuestUIExchangeV1(fieldLogEditorGeneration: 1)
    let construction = try ExperimentalCapabilitySession.prepareOwnedGuestUIV1(module: module,
        configuration: configuration, policy: policy, adapterGroup: group, exchange: exchange)
    let session = try await construction.create()
    do {
        try await session.startupGuestUIV1()
        try check(exchange.snapshot().latestRevision == 1 && !exchange.snapshot().effectsMayHaveOpened,
            "Initial document was not validated before effects intent")
        try exchange.enterEffectsIntent(generation: 1)
        try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: DispatchTime.now().uptimeNanoseconds + 5_000_000_000)
        try exchange.confirmEffectsEnabled(generation: 1)
        var ui = Presentation(exchange: exchange)
        let startup = try await ui.next(after: 0)
        try check(startup.document == expected && startup.document.root.kind == .navigation, "Initial frame differs from real input")
        let title = mode == "multiline" ? "  Valve \"α\"\nSecond 🧰 line  " : "  Inspect \"α\" \\ pump  "
        let responsible = "  Réa 🧰  "
        let initialTitle = try ui.event(startup, "task.title", .textChange, .string(title))
        try await ui.reject(ui.event(startup, "task.save", .activate), because: .invalid(.disabledNode))
        try await ui.reject(ui.event(startup, "task.title", .submit), because: .invalid(.unboundEvent))
        try await ui.reject(ui.event(startup, "task.title", .textChange, .string("x\0y")), because: .invalid(.invalidValue))
        try await ui.reject(ui.event(startup, "task.title", .textChange, .string(String(repeating: "a", count: 241))),
                            because: .invalid(.invalidValue))
        try await ui.reject(ui.event(startup, "task.responsible", .textChange, .string("a\nb")),
                            because: .invalid(.invalidValue))
        if mode != "multiline" {
            try await ui.reject(ui.event(startup, "task.title", .textChange, .string("a\nb")),
                                because: .invalid(.invalidValue))
        }
        let titleSequence = try await ui.send(initialTitle)
        let edited = try await ui.next(after: 1, outcome: titleSequence)
        try check(node(edited.document.root, "task.title")?.properties["value"]?.string?.utf8.elementsEqual(title.utf8) == true,
            "Guest changed the title bytes")
        try await ui.reject(initialTitle, because: .stale)
        let responsibleSequence = try await ui.send(ui.event(edited, "task.responsible", .textChange, .string(responsible)))
        let complete = try await ui.next(after: edited.document.revision, outcome: responsibleSequence)
        try check(node(complete.document.root, "task.responsible")?.properties["value"]?.string?.utf8.elementsEqual(responsible.utf8) == true,
            "Guest changed the responsible bytes")
        let before = await repository.snapshot()
        try check(before == initial, "Editing wrote to the repository")
        let finish = try ui.event(complete, mode == "cancel" ? "task.cancel" : "task.save", .activate)
        let terminalSequence = try await ui.send(finish)
        var end = try await ui.next(after: complete.document.revision, outcome: terminalSequence)
        if mode != "cancel" && end.document.root.id != "task.result" && node(end.document.root, "task.failure") == nil {
            end = try await ui.next(after: end.document.revision)
        }
        switch mode {
        case "denied":
            try check(node(end.document.root, "task.failure") != nil, "No refusal frame for missing signed grant")
            try check(node(end.document.root, "task.title")?.properties["value"]?.string == title,
                "Denied save cleared the editable value")
            try check(await repository.snapshot() == initial, "Denied save changed disk state")
            try check(await !storage.attempted, "Denied operation reached application storage")
        case "cancel":
            try check(end.document.root.id == "task.result" && end.document.root.properties["text"]?.string == "Task cancelled",
                "Cancel retained the editor route")
            try check(await repository.snapshot() == initial, "Cancel changed disk state")
        default:
            try check(end.document.root.id == "task.result" && end.document.root.properties["text"]?.string == "Task added",
                "Save did not close the editor after its repository acknowledgement")
            try await ui.reject(finish, because: .stale)
            await repository.close()
            let reopened = try WorkspaceRepository(directory: directory)
            let disk = await reopened.snapshot()
            await reopened.close()
            try check(disk.revision == initial.revision + 1 && disk.tasks.count == 1 &&
                disk.tasks[0].projectID == project &&
                disk.tasks[0].title.utf8.elementsEqual(title.trimmingCharacters(in: .whitespacesAndNewlines).utf8) &&
                disk.tasks[0].responsible.utf8.elementsEqual(responsible.utf8) &&
                disk.outbox.count == initial.outbox.count + 1 && disk.outbox.last?.kind == .taskSaved &&
                disk.outbox.last?.recordID == disk.tasks[0].id, "Reopened workspace differs from the guest save")
        }
    } catch {
        FileHandle.standardError.write(Data("\(mode) failed: \(error); session: \(session.status); terminal: \(String(describing: report.failure))\n".utf8))
        session.close()
        await repository.close()
        _ = try await wait("error retirement") { session.status.drained && report.didRetire ? true : nil }
        FileHandle.standardError.write(Data("Failure retired. Revision \(String(describing: exchange.snapshot().latestRevision)); native status \(session.status)\n".utf8))
        throw error
    }
    session.close()
    await repository.close()
    _ = try await wait("retirement") { session.status.drained && report.clean ? true : nil }
    let status = session.status
    let calls: UInt64 = mode == "cancel" ? 0 : 1
    try check(status.closed && status.acceptedCalls == calls && status.acknowledgements == calls &&
        status.retainedExits == 0 && status.retainedPayloadBytes == 0,
        "Unexpected call, acknowledgement or retained ownership count: \(status)")
    print("\(mode): exact startup, edits and event acknowledgements; terminal revision \(exchange.snapshot().latestRevision ?? 0); clean retirement")
}

private func verifyLegacyGuest(_ module: Data) async throws {
    let observer = Retirement()
    let group = OwnedCapabilityAdapterGroup(terminal: observer, retirement: observer)
    defer { group.closeIfUntransferred() }
    let configuration = ExperimentalCapabilityConfiguration(memoryPages: 1)
    try await ExperimentalCapabilityValidator.prepareGuestUIV1(module: module, configuration: configuration).validate()
    let exchange = try GuestUIExchangeV1(generation: 1)
    let construction = try ExperimentalCapabilitySession.prepareOwnedGuestUIV1(module: module,
        configuration: configuration, policy: CapabilityPolicy(installed: [], manifest: []),
        adapterGroup: group, exchange: exchange)
    let session = try await construction.create()
    do {
        try await session.startupGuestUIV1()
        try exchange.enterEffectsIntent(generation: 1)
        try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: DispatchTime.now().uptimeNanoseconds + 5_000_000_000)
        try exchange.confirmEffectsEnabled(generation: 1)
        var ui = Presentation(exchange: exchange)
        let before = try await ui.next(after: 0)
        try check(node(before.document.root, "toggle")?.properties["label"]?.string == "Complete task",
                  "Unexpected legacy startup")
        let sequence = try await ui.send(ui.event(before, "toggle", .activate))
        let after = try await ui.next(after: before.document.revision, outcome: sequence)
        try check(node(after.document.root, "toggle")?.properties["label"]?.string == "Reopen task",
                  "Legacy activation did not reach the owned VM")
    } catch {
        session.close()
        _ = try await wait("legacy error retirement") { session.status.drained && observer.clean ? true : nil }
        throw error
    }
    session.close()
    _ = try await wait("legacy retirement") { session.status.drained && observer.clean ? true : nil }
    print("legacy compact guest: Complete task → Reopen task through unchanged ABI and event codec")
}

private func verifyUnsupportedDocuments() throws {
    let toggle = MixerUI.Toggle("unsupported", "Toggle", value: false, action: "toggle").document(revision: 1)
    let submit = MixerUI.TextField("task.title", "Title", value: "", action: "task.title.change",
                                   onSubmit: "task.save").document(revision: 1)
    for document in [toggle, submit] {
        var wrapped = Data(#"{"featureSchemaVersion":3,"document":"#.utf8)
        wrapped += try UIValidator().encode(document)
        wrapped.append(125)
        let exchange = try GuestUIExchangeV1(fieldLogEditorGeneration: 1)
        do {
            try exchange.finishTurn(exchange.claimStartup(), documentBytes: wrapped)
            throw CheckFailure(message: "Unsupported document admitted")
        } catch let failure as GuestUIProtocolFailureV1 {
            try check(failure.phase == .startup && failure.code == .document &&
                exchange.snapshot().latestRevision == nil && !exchange.snapshot().effectsMayHaveOpened,
                "Unsupported document was not refused before effects")
        }
    }
    print("editor document controls: toggle and submit binding refused before effects")
}

@main private enum EditorHost {
    static func main() async {
        do { try await runProbe() } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(1)
        }
    }

    private static func runProbe() async throws {
        let args = CommandLine.arguments
        try check(args.count == 5, "Expected input directory, identity digest, source revision and legacy runtime fingerprint")
        let dir = URL(fileURLWithPath: args[1])
        let signing = SigningAuthority(identity: args[2], revision: args[3])
        let codec = FeatureDocumentV3(textValuePolicy: .standard)
        try await verifyLegacyGuest(Data(contentsOf: dir.appendingPathComponent("legacy.wasm")))
        try verifyUnsupportedDocuments()
        for mode in ["single-line", "multiline", "cancel", "denied"] {
            let variant = mode == "multiline" ? "vertical" : "historical"
            let fixture = try Data(contentsOf: dir.appendingPathComponent("\(variant).json"))
            let document = try codec.validator.decode(fixture).document
            if mode == "single-line" {
                let legacy = try GuestUIExchangeV1(generation: 1)
                do {
                    try legacy.finishTurn(legacy.claimStartup(), documentBytes: fixture)
                    throw CheckFailure(message: "Legacy startup unexpectedly accepted F05")
                } catch let failure as GuestUIProtocolFailureV1 {
                    let snap = legacy.snapshot()
                    try check(failure.phase == .startup && failure.code == .document &&
                        snap.latestRevision == nil && !snap.effectsMayHaveOpened, "Legacy failure contract drifted")
                    print("legacy F05 startup/document, no admitted revision or effects intent")
                }
            }
            let bytes = try Data(contentsOf: dir.appendingPathComponent("\(variant).wasm"))
            let policy = try signing.authorize(bytes, grant: mode != "denied", legacyRuntime: args[4],
                checkRefusals: mode == "single-line")
            try await run(bytes, expected: document, mode: mode, directory: dir.appendingPathComponent(mode), policy: policy)
        }
    }
}
