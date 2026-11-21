#if os(macOS) && MIXER_PRIVATE_FIELDLOG_EDITOR && FIELDLOG_EDITOR_REPLAY
import Crypto
import FieldLogModels
import FieldLogStorage
import Foundation
@_spi(InstalledApplicationStorage) import MixerCapabilities
#if MIXER_PRIVATE_F10
@_spi(PrivateFieldLogF10) import MixerExperimentalCapabilityRuntime
#endif
@_spi(GuestUIV1) import MixerGuest
@_spi(PrivateFieldLogEditor) import MixerRuntimeIdentity
#if MIXER_PRIVATE_F10
@_spi(PrivateFieldLogF10) import MixerRuntimeIdentity
#endif
import MixerUI
@_spi(PrivateFieldLogEditor) import MixerUpdates
import XCTest
@_spi(PrivateFieldLogEditor) @testable import MixerCapabilityActivation

final class FieldLogInstalledEditorTests: XCTestCase {
    private struct Pin {
        let name: String
        let revision: String
        let axis: String?
    }
    private static let pins = [
        Pin(name: "F05", revision: "70f3aa1d28f29e7c327a17fd46199480d41ca749", axis: nil),
        Pin(name: "F06", revision: "4d17c92656d3a7574506f06414bc2f08af469122", axis: "vertical"),
    ]
    private enum Scenario: String { case editCancel, save, uncertainSave }
    private static let title = "Inspect pump P-17"
    private static let now = Date(timeIntervalSince1970: 1_800_000_000)
    private static let project = UUID(uuidString: "4c589bde-5f6c-41f4-8acb-e6099d0a1877")!

    /// Fault hook inside the pinned repository's fsynced write, just before rename.
    private final class WriteGate: @unchecked Sendable {
        private let lock = NSLock()
        private let semaphore = DispatchSemaphore(value: 0)
        private var armed = false
        private var arrived = false
        private let failAfterRename: Bool

        init(failAfterRename: Bool) { self.failAfterRename = failAfterRename }
        var entered: Bool { lock.withLock { arrived } }
        func arm() { lock.withLock { armed = true } }
        func release() { semaphore.signal() }

        func fault(_ stage: String) throws {
            if stage == "after_rename", failAfterRename, entered {
                throw FieldLogError.storage("Test uncertainty after rename")
            }
            guard stage == "before_rename" else { return }
            let block = lock.withLock {
                guard armed else { return false }
                armed = false
                arrived = true
                return true
            }
            if block, semaphore.wait(timeout: .now() + 8) != .success {
                throw FieldLogError.storage("Test did not unblock the repository")
            }
        }
    }

    private actor OwnerCount {
        private(set) var writes = 0
        func begin() { writes += 1 }
    }

    private struct ReplayInputs {
        let input: URL
        let root: URL
        let archive: String
        let vmSource: String

        init() throws {
            let environment = ProcessInfo.processInfo.environment
            input = URL(fileURLWithPath: try XCTUnwrap(environment["MIXER_FIELDLOG_EDITOR_INPUT"]), isDirectory: true)
            root = URL(fileURLWithPath: try XCTUnwrap(environment["MIXER_FIELDLOG_EDITOR_TEST_ROOT"]), isDirectory: true)
            archive = try XCTUnwrap(environment["MIXER_FIELDLOG_EDITOR_VM_SHA256"])
            vmSource = try XCTUnwrap(environment["MIXER_FIELDLOG_EDITOR_VM_SOURCE_SHA256"])
        }
    }

    @MainActor
    func testPresenterOwnerSpansUnboundOpenPresentationAndClose() async throws {
        let inputs = try ReplayInputs()
        let baseline = CapabilityAttemptReservation.occupiedSlots
        let directory = inputs.root.appendingPathComponent("presenter-ownership")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
        let presenter = FieldLogEditorPresenter { _ in throw CapabilityFailure.permissionDenied }
        let signed = try makeFixture(directory: directory, presenter: presenter, archive: inputs.archive,
                                     vmSource: inputs.vmSource, checkDefault: true)
        await refuses("invalid configuration before reservation") {
            let unexpected = try await CapabilityColdStartRuntime.openFieldLogEditor(
                configuration: .init(directory: signed.configuration.directory, channel: "", installation: "owner-test"),
                execution: signed.execution, presenter: presenter)
            await unexpected.close()
        }
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, baseline)
        let blocked = directory.appendingPathComponent("blocked-directory")
        try Data().write(to: blocked)
        await refuses("recovery directory is a plain file") {
            let unexpected = try await CapabilityColdStartRuntime.openFieldLogEditor(
                configuration: .init(directory: blocked, channel: "beta", installation: "owner-test"),
                execution: signed.execution, presenter: presenter)
            await unexpected.close()
        }
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, baseline)

        let first = try await CapabilityColdStartRuntime.openFieldLogEditor(configuration: signed.configuration,
            execution: signed.execution, presenter: presenter)
        let duplicate = directory.appendingPathComponent("duplicate")
        func assertDuplicateRefused() async {
            do {
                let runtime = try await CapabilityColdStartRuntime.openFieldLogEditor(
                    configuration: .init(directory: duplicate, channel: "beta", installation: "owner-test"),
                    execution: signed.execution, presenter: presenter)
                await runtime.close()
                XCTFail("A second runtime claimed the live presenter")
            } catch {
                XCTAssertEqual((error as? UpdateError)?.code, "capability.runtime.fieldlog_editor_presenter_owned")
            }
            XCTAssertFalse(FileManager.default.fileExists(atPath: duplicate.path))
            XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, baseline + 1)
        }
        do {
            await assertDuplicateRefused()
            let pin = Self.pins[0]
            let wasm = try Data(contentsOf: inputs.input.appendingPathComponent(pin.name + "/editor.wasm"))
            try await stage(wasm, pin: pin, signed: signed, runtime: first)
            try await wait("owner's initial frame", runtime: first) { presenter.snapshot?.document.revision == 1 }
            let edit = try issue(presenter, node: "task.title", event: .textChange, value: .string(Self.title))
            await assertDuplicateRefused()

            let otherDirectory = directory.appendingPathComponent("other")
            try FileManager.default.createDirectory(at: otherDirectory, withIntermediateDirectories: false)
            let otherPresenter = FieldLogEditorPresenter { _ in throw CapabilityFailure.permissionDenied }
            let otherSigned = try makeFixture(directory: otherDirectory, presenter: otherPresenter, archive: inputs.archive,
                                              vmSource: inputs.vmSource, checkDefault: false)
            let unbound = try await CapabilityColdStartRuntime.openFieldLogEditor(configuration: otherSigned.configuration,
                execution: otherSigned.execution, presenter: otherPresenter)
            XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, baseline + 2)
            await unbound.close()
            XCTAssertNil(otherPresenter.snapshot)
            XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, baseline + 1)
            XCTAssertEqual(presenter.snapshot?.document.revision, 1)
            try await delivered(edit, presenter: presenter, runtime: first)
            XCTAssertEqual(presenter.snapshot?.document.revision, 2)
        } catch {
            await first.close()
            throw error
        }
        await first.close()
        try await waitForReservationCount(baseline)
        XCTAssertNil(presenter.snapshot)

        let reused = try await CapabilityColdStartRuntime.openFieldLogEditor(configuration: signed.configuration,
            execution: signed.execution, presenter: presenter)
        await first.close()
        await assertDuplicateRefused()
        await reused.close()
        try await waitForReservationCount(baseline)
    }

    @MainActor
    func testSignedAbsentAndRejectedSavingFramesRetireWithoutWrite() async throws {
        let inputs = try ReplayInputs()
        let baseline = CapabilityAttemptReservation.occupiedSlots
        let pin = Self.pins[1]
        for control in ["absent-saving", "rejected-saving"] {
            let directory = inputs.root.appendingPathComponent(control)
            let workspace = directory.appendingPathComponent("app")
            let repository = try WorkspaceRepository(directory: workspace)
            let seed = try await repository.transact {
                try $0.createProject(id: Self.project, title: "Pump station", site: "", now: Self.now)
            }
            let file = workspace.appendingPathComponent("workspace.json")
            let seedDisk = try Data(contentsOf: file)
            let count = OwnerCount()
            let presenter = FieldLogEditorPresenter { title in
                return { permit in
                    await count.begin()
                    try await repository.transact(expectedRevision: seed.revision) { next in
                        try permit.consume()
                        try next.saveTask(projectID: Self.project, title: title, responsible: "", now: Self.now)
                    }
                    return KVMutationResponse(committed: true)
                }
            }
            let signed = try makeFixture(directory: directory, presenter: presenter, archive: inputs.archive,
                                         vmSource: inputs.vmSource, checkDefault: false)
            let runtime = try await CapabilityColdStartRuntime.openFieldLogEditor(configuration: signed.configuration,
                execution: signed.execution, presenter: presenter)
            do {
                let wasm = try Data(contentsOf: inputs.input.appendingPathComponent(pin.name + "/" + control + ".wasm"))
                try await stage(wasm, pin: pin, signed: signed, runtime: runtime)
                try await wait("first frame", runtime: runtime) { presenter.snapshot?.document.revision == 1 }
                try await delivered(issue(presenter, node: "task.title", event: .textChange, value: .string(Self.title)),
                                    presenter: presenter, runtime: runtime)
                let save = try issue(presenter, node: "task.save", event: .activate)
                XCTAssertEqual(presenter.submit(save), .accepted(sequence: 2))
                let deadline = ContinuousClock.now.advanced(by: .seconds(5))
                while presenter.eventResult?.outcome != .terminal(turnBegan: true) {
                    guard ContinuousClock.now < deadline else { throw coldStartError("saving_terminal_result") }
                    try await Task.sleep(for: .milliseconds(2))
                }
                XCTAssertEqual(presenter.eventResult?.sequence, 2)
                XCTAssertNotEqual(presenter.snapshot?.document.revision, 4)
            } catch {
                await runtime.close()
                await repository.close()
                throw error
            }
            await runtime.close()
            try await waitForReservationCount(baseline)
            let result = await runtime.recoverySnapshot()
            XCTAssertTrue(result.closed)
            XCTAssertFalse(result.activation.cleanupPending)
            XCTAssertNil(presenter.snapshot)
            let writes = await count.writes
            XCTAssertEqual(writes, 0)
            await repository.close()
            XCTAssertEqual(try Data(contentsOf: file), seedDisk)
            let reopened = try WorkspaceRepository(directory: workspace)
            let cold = await reopened.snapshot()
            await reopened.close()
            XCTAssertEqual(cold, seed)
            print("FIELDLOG EDITOR \(control) terminal-sequence=2 writes=\(writes) reserved=\(CapabilityAttemptReservation.occupiedSlots - baseline)")
        }
    }

    @MainActor
    private func stage(_ wasm: Data, pin: Pin, signed: GuestUISignedFixture, runtime: CapabilityColdStartRuntime) async throws {
        let documents = try signed.documents(wasm, storage: true, memoryBytes: 4_194_304, fuel: 1_000_000,
            sourceCommit: pin.revision, storageNamespace: FieldLogEditorStorage.namespace)
        try await runtime.beginDownload(signedManifest: documents.0, signedAssignment: documents.1)
        try await runtime.appendDownload(wasm, atOffset: 0)
        try await runtime.finishDownload()
        _ = try await runtime.start()
    }

    @MainActor
    private func waitForReservationCount(_ count: Int) async throws {
        let deadline = ContinuousClock.now.advanced(by: .seconds(5))
        while CapabilityAttemptReservation.occupiedSlots != count {
            guard ContinuousClock.now < deadline else { throw coldStartError("editor_reservation_not_retired") }
            try await Task.sleep(for: .milliseconds(2))
        }
    }

    @MainActor
    func testSignedHistoricalEditors() async throws {
        let inputs = try ReplayInputs()
        for pin in Self.pins {
            let variant = inputs.input.appendingPathComponent(pin.name)
            let wasm = try Data(contentsOf: variant.appendingPathComponent("editor.wasm"))
            let oracle = try JSONDecoder().decode([Data].self,
                from: Data(contentsOf: variant.appendingPathComponent("trace.json")))
            XCTAssertEqual(oracle.count, 9)
#if MIXER_PRIVATE_F10
            await refuses("MUI1 editor in the F10 native selector") {
                try await ExperimentalCapabilityValidator.prepareF10(module: wasm, configuration: .init()).validate()
            }
#endif
            var scenarios: [Scenario] = [.editCancel, .save]
            if pin.name == "F06" { scenarios.append(.uncertainSave) }
            for scenario in scenarios {
                let directory = inputs.root.appendingPathComponent(pin.name + "-" + scenario.rawValue)
                try await exercise(pin, wasm: wasm, oracle: oracle, directory: directory,
                                   archive: inputs.archive, vmSource: inputs.vmSource, scenario: scenario)
            }
        }
    }

    @MainActor
    private func exercise(_ pin: Pin, wasm: Data, oracle: [Data], directory: URL,
                          archive: String, vmSource: String, scenario: Scenario) async throws {
        let save = scenario != .editCancel
        let uncertain = scenario == .uncertainSave
        let gate = WriteGate(failAfterRename: uncertain)
        let workspace = directory.appendingPathComponent("app")
        let repository = try WorkspaceRepository(directory: workspace, fault: gate.fault)
        let seed = try await repository.transact {
            try $0.createProject(id: Self.project, title: "Pump station", site: "", now: Self.now)
        }
        let seedDisk = try Data(contentsOf: workspace.appendingPathComponent("workspace.json"))
        let count = OwnerCount()
        let presenter = FieldLogEditorPresenter { title in
            let project = try XCTUnwrap(seed.restoration.selectedProjectID)
            let revision = seed.revision
            return { permit in
                await count.begin()
                try await repository.transact(expectedRevision: revision) { next in
                    guard next.restoration.selectedProjectID == project else { throw FieldLogError.staleRevision }
                    try permit.consume()
                    try next.saveTask(projectID: project, title: title, responsible: "", now: Self.now)
                }
                return KVMutationResponse(committed: true)
            }
        }
        let signed = try makeFixture(directory: directory, presenter: presenter, archive: archive, vmSource: vmSource,
                                     checkDefault: !save)
        let runtime = try await CapabilityColdStartRuntime.openFieldLogEditor(configuration: signed.configuration,
            execution: signed.execution, presenter: presenter)
        do {
            if !save {
                let wrong = try signed.documents(wasm, storage: true, memoryBytes: 4_194_304, fuel: 1_000_000,
                    sourceCommit: pin.revision, storageNamespace: FieldLogEditorStorage.namespace,
                    runtimeFingerprint: String(repeating: "f", count: 64))
                await refuses("wrong fingerprint") {
                    try await runtime.beginDownload(signedManifest: wrong.0, signedAssignment: wrong.1)
                }
            }
            let good = try signed.documents(wasm, sequence: 2, storage: true, memoryBytes: 4_194_304, fuel: 1_000_000,
                sourceCommit: pin.revision, storageNamespace: FieldLogEditorStorage.namespace)
            try await runtime.beginDownload(signedManifest: good.0, signedAssignment: good.1)
            try await runtime.appendDownload(wasm, atOffset: 0)
            try await runtime.finishDownload()
            await refuses("replayed assignment") {
                try await runtime.beginDownload(signedManifest: good.0, signedAssignment: good.1)
            }
            let start = try await runtime.start()
            XCTAssertTrue(start.effectsMayHaveOpened)
            await refuses("caller-reported first screen") {
                try await runtime.reportMilestone("first_screen")
            }
            try await wait("first render", runtime: runtime) { presenter.snapshot != nil }
            try assertDocument(presenter, oracle[0])
            let initial = try XCTUnwrap(presenter.snapshot)
            let titleNode = initial.document.root.children[0].children[0].children[0]
            XCTAssertEqual(titleNode.properties["axis"]?.string, pin.axis)
            XCTAssertEqual(initial.document.root.kind, .navigation)

            let oversized = try issue(presenter, node: "task.title", event: .textChange,
                                      value: .string(String(repeating: "\n", count: 2200)))
            XCTAssertEqual(presenter.submit(oversized), .invalid(.invalidValue))
            XCTAssertEqual(presenter.exchangeSnapshot?.counters.maximumEventSlots, 0)
            XCTAssertEqual(presenter.exchangeSnapshot?.counters.acceptedEvents, 0)
            XCTAssertEqual(presenter.exchangeSnapshot?.eventOutstanding, false)
            let cr = try issue(presenter, node: "task.title", event: .textChange, value: .string("a\rb"))
            XCTAssertEqual(presenter.submit(cr), .invalid(.invalidValue))
            let foreign = try UINativeActionRouter(document: initial.document,
                validator: UIValidator(supportedTextFieldAxes: [.horizontal, .vertical]))
            let foreignIssued = try foreign.route(oversized.envelope)
            XCTAssertEqual(presenter.submit(foreignIssued), .stale)

            let title = try issue(presenter, node: "task.title", event: .textChange, value: .string(Self.title))
            try await delivered(title, presenter: presenter, runtime: runtime)
            try assertDocument(presenter, oracle[1])
            let saveAction = try issue(presenter, node: "task.save", event: .activate)
            if save {
                gate.arm()
                try await delivered(saveAction, presenter: presenter, runtime: runtime)
                try assertDocument(presenter, oracle[7])
                try await wait("repository blocked before rename", runtime: runtime) { gate.entered }
                XCTAssertEqual(try Data(contentsOf: workspace.appendingPathComponent("workspace.json")), seedDisk)
                XCTAssertEqual(presenter.submit(saveAction), .stale)
                gate.release()
                if uncertain {
                    let deadline = ContinuousClock.now.advanced(by: .seconds(5))
                    while await runtime.recoverySnapshot().activation.terminalCause == nil {
                        guard ContinuousClock.now < deadline else { throw coldStartError("editor_uncertain_completion") }
                        try await Task.sleep(for: .milliseconds(2))
                    }
                    XCTAssertNotEqual(presenter.snapshot?.document.revision, 4)
                    if case .accepted = presenter.submit(saveAction) { XCTFail("Accepted the uncertain Save again") }
                } else {
                    try await wait("Saved frame", runtime: runtime) { presenter.snapshot?.document.revision == 4 }
                    try assertDocument(presenter, oracle[8])
                }
            } else {
                for (index, draft) in ["Line one\ne\u{301} 🧑🏽‍🔧", "Line one\n\u{e9} 🧑🏽‍🔧"].enumerated() {
                    let input = try issue(presenter, node: "task.title", event: .textChange, value: .string(draft))
                    try await delivered(input, presenter: presenter, runtime: runtime)
                    try assertDocument(presenter, oracle[2 + index])
                }
                XCTAssertEqual(presenter.submit(saveAction), .stale)
                let cancel = try issue(presenter, node: "task.cancel", event: .activate)
                try await delivered(cancel, presenter: presenter, runtime: runtime)
                try assertDocument(presenter, oracle[4])
                XCTAssertEqual(presenter.submit(cancel), .stale)
            }
            if !uncertain {
                let healthDeadline = ContinuousClock.now.advanced(by: .seconds(5))
                while await runtime.recoverySnapshot().activation.phase != .healthyGuest {
                    guard ContinuousClock.now < healthDeadline else { throw coldStartError("editor_health") }
                    try await Task.sleep(for: .milliseconds(10))
                }
            }
        } catch {
            gate.release()
            await runtime.close()
            await repository.close()
            throw error
        }
        await runtime.close()
        let terminal = await runtime.recoverySnapshot()
        XCTAssertFalse(terminal.activation.cleanupPending)
        XCTAssertTrue(terminal.closed)
        XCTAssertNil(presenter.snapshot)
        let committed = await repository.snapshot()
        await repository.close()
        let reopened = try WorkspaceRepository(directory: workspace)
        let cold = await reopened.snapshot()
        await reopened.close()
        let writes = await count.writes
        if uncertain { XCTAssertEqual(committed, seed) }
        else { XCTAssertEqual(cold, committed) }
        if save {
            XCTAssertEqual(writes, 1)
            let task = try XCTUnwrap(cold.tasks.last)
            let change = try XCTUnwrap(cold.outbox.last)
            XCTAssertEqual(task.projectID, Self.project)
            XCTAssertEqual(Array(task.title.utf8), Array(Self.title.utf8))
            XCTAssertEqual(task.responsible, "")
            XCTAssertFalse(task.completed)
            XCTAssertEqual(task.updatedAt, Self.now)
            XCTAssertEqual(task.position, seed.tasks(for: Self.project).count)
            XCTAssertEqual(change.kind, .taskSaved)
            XCTAssertEqual(change.recordID, task.id)
            XCTAssertEqual(change.revision, seed.revision + 1)
            XCTAssertEqual(change.createdAt, Self.now)
            XCTAssertEqual(change.idempotencyKey, change.id.uuidString.lowercased())
            var expected = seed
            expected.revision += 1
            expected.tasks.append(task)
            expected.outbox.append(change)
            XCTAssertEqual(cold, expected)
        } else {
            XCTAssertEqual(writes, 0)
            XCTAssertEqual(cold, seed)
            let wrongGrantDirectory = directory.appendingPathComponent("wrong-grant")
            try FileManager.default.createDirectory(at: wrongGrantDirectory, withIntermediateDirectories: false)
            let wrong = GuestUISignedFixture(root: wrongGrantDirectory, execution: signed.execution, key: signed.key)
            let blocked = try await CapabilityColdStartRuntime.openFieldLogEditor(configuration: wrong.configuration,
                execution: wrong.execution, presenter: presenter)
            do {
                let documents = try wrong.documents(wasm, storage: true, memoryBytes: 4_194_304, fuel: 1_000_000,
                    sourceCommit: pin.revision, storageNamespace: "material_test")
                try await blocked.beginDownload(signedManifest: documents.0, signedAssignment: documents.1)
                try await blocked.appendDownload(wasm, atOffset: 0)
                try await blocked.finishDownload()
                let result = try await blocked.start()
                XCTAssertEqual(result.phase, .nativeFallback)
                XCTAssertFalse(result.effectsMayHaveOpened)
                XCTAssertNil(presenter.snapshot)
            } catch {
                await blocked.close()
                throw error
            }
            await blocked.close()
        }
        print("FIELDLOG EDITOR \(pin.name) \(scenario.rawValue) writes=\(writes) closed=\(terminal.closed) retired=\(!terminal.activation.cleanupPending)")
    }

    @MainActor
    private func issue(_ presenter: FieldLogEditorPresenter, node: String, event: UIEventKind, value: UIValue = .null) throws -> IssuedUIAction {
        let frame = try XCTUnwrap(presenter.snapshot)
        let identity = try XCTUnwrap(frame.identity(for: node))
        return try presenter.issue(.init(revision: frame.document.revision, identity: identity, event: event, value: value))
    }

    @MainActor
    private func delivered(_ issued: IssuedUIAction, presenter: FieldLogEditorPresenter, runtime: CapabilityColdStartRuntime) async throws {
        guard case .accepted(let sequence) = presenter.submit(issued) else { throw coldStartError("editor_event_admission") }
        try await wait("event \(sequence) delivery", runtime: runtime) { presenter.eventResult?.sequence == sequence }
        XCTAssertEqual(presenter.eventResult?.outcome, .delivered)
    }

    @MainActor
    private func assertDocument(_ presenter: FieldLogEditorPresenter, _ expected: Data) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let actual = try encoder.encode(presenter.snapshot?.document)
        XCTAssertTrue(actual == expected, "\(String(decoding: actual, as: UTF8.self)) != \(String(decoding: expected, as: UTF8.self))")
    }

    @MainActor
    private func wait(_ stage: String, runtime: CapabilityColdStartRuntime, condition: () -> Bool) async throws {
        let end = ContinuousClock.now.advanced(by: .seconds(5))
        while !condition() {
            let state = await runtime.recoverySnapshot()
            guard ContinuousClock.now < end, state.activation.terminalCause == nil,
                  state.activation.phase != .nativeFallback else {
                XCTFail("\(stage): \(state.activation.phase), \(String(describing: state.activation.terminalCause))")
                throw coldStartError("editor_test_timeout")
            }
            try await Task.sleep(for: .milliseconds(2))
        }
    }

    @MainActor
    private func refuses(_ detail: String, _ operation: () async throws -> Void) async {
        do {
            try await operation()
            XCTFail("Accepted \(detail)")
        } catch {}
    }

    private func makeFixture(directory: URL, presenter: FieldLogEditorPresenter, archive: String, vmSource: String,
                             checkDefault: Bool) throws -> GuestUISignedFixture {
        func resource(_ name: String) throws -> Data {
            try Data(contentsOf: XCTUnwrap(Bundle.module.url(forResource: name, withExtension: nil, subdirectory: "Fixtures")))
        }
        let scope = FieldLogEditorDevelopment.scope
        let key = Curve25519.Signing.PrivateKey()
        let roots = try JSONEncoder().encode([TrustRoot(keyID: "guest-ui-signed-test",
            publicKey: key.publicKey.rawRepresentation, scope: scope, artifact: true, assignment: true,
            notBeforeUnix: 1, notAfterUnix: UInt64.max)])
        func json(_ value: [String: Any]) throws -> Data {
            try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes])
        }
        var grant = try XCTUnwrap(MaterialJSON.decode(resource("storage-grant.json")).object)
        grant["namespaces"] = .array([.text(FieldLogEditorStorage.namespace)])
        let grantBytes = MaterialJSON.canonical(.object(grant))
        var identity = try XCTUnwrap(JSONSerialization.jsonObject(with: resource("identity.json")) as? [String: Any])
        if checkDefault {
            var marked = identity
            marked["dependencies"] = [["id": FieldLogEditorDevelopment.dependency, "version": "1",
                                      "artifact_sha256": FieldLogEditorDevelopment.contractSHA256]]
            XCTAssertThrowsError(try CapabilityRuntimeIdentity(json: json(marked)))
        }
        var storage = try XCTUnwrap((identity["capabilities"] as? [[String: Any]])?.last)
        storage["grants_sha256"] = ReleaseVerifier.sha256(grantBytes)
        identity["capabilities"] = [storage]
        identity["application"] = ["app": scope.app, "organization": scope.organization, "project": scope.project,
                                   "environment": scope.environment, "bundle_id": FieldLogEditorDevelopment.bundleID]
        #if arch(arm64)
        let arch = "arm64"
        #else
        let arch = "x86_64"
        #endif
        identity["platform"] = ["os": "macos", "architecture": arch, "environment": "device",
                                "minimum_os": "14.0", "target": "\(arch)-apple-macosx14.0"]
        var build = try XCTUnwrap(identity["build"] as? [String: Any])
        build["trust_roots_sha256"] = ReleaseVerifier.sha256(roots)
        identity["build"] = build
        var engine = try XCTUnwrap(identity["engine"] as? [String: Any])
        engine["ui_contract_sha256"] = FieldLogEditorDevelopment.contractSHA256
        engine["artifact_sha256"] = archive
        engine["source_sha256"] = vmSource
        identity["engine"] = engine
        var mode = try XCTUnwrap(identity["execution"] as? [String: Any])
        mode["startup_export"] = CapabilityInstalledExecutionMode.startup
        if checkDefault { mode["host_calls"] = 0 }
        identity["execution"] = mode
        identity["dependencies"] = [
            ["id": FieldLogEditorDevelopment.dependency, "version": "1", "artifact_sha256": FieldLogEditorDevelopment.contractSHA256],
            ["id": CapabilityInstalledExecutionMode.headerID, "version": "1", "artifact_sha256": CapabilityInstalledExecutionMode.headerSHA256],
        ]
        let bytes = try json(identity)
        let materials: [CapabilityMaterialFile] = [
            .init(role: .bridgePolicy, bytes: try resource("bridge.json")),
            .init(role: .configuration(capabilityID: CapabilitySchemas.storageID), bytes: try resource("storage.json")),
            .init(role: .installedGrant(capabilityID: CapabilitySchemas.storageID), bytes: grantBytes),
        ]
        let execution = try InstalledCapabilityExecution(privateDevelopmentFieldLogEditorJSON: bytes,
            materials: materials, trustRootsJSON: roots, privateContainer: directory, presenter: presenter)
        if checkDefault {
            let wrongScope = UpdateScope(organization: scope.organization, project: scope.project, app: "different-app",
                                         environment: scope.environment, platform: scope.platform)
            let wrongRoot = TrustRoot(keyID: "guest-ui-signed-test", publicKey: key.publicKey.rawRepresentation,
                scope: wrongScope, artifact: true, assignment: true, notBeforeUnix: 1)
            XCTAssertThrowsError(try ReleaseVerifierV3(privateDevelopmentFieldLogEditor: execution.installed.identity.installedRuntime,
                roots: [wrongRoot]))
            var anotherApp = identity
            anotherApp["application"] = ["app": wrongScope.app, "organization": scope.organization, "project": scope.project,
                                         "environment": scope.environment, "bundle_id": FieldLogEditorDevelopment.bundleID]
            XCTAssertThrowsError(try CapabilityRuntimeIdentity(privateDevelopmentFieldLogEditorJSON: json(anotherApp)))
            XCTAssertThrowsError(try InstalledCapabilityExecution(identityJSON: bytes, materials: materials,
                trustRootsJSON: roots, privateContainer: directory))
            XCTAssertThrowsError(try CapabilityInstalledExecutionMode.requireGuestUI(execution.installed.identity,
                milestones: ["feature_started", "first_screen"]))
            XCTAssertThrowsError(try CapabilityInstalledExecutionMode.requireCapabilityOnly(execution.installed.identity))
#if MIXER_PRIVATE_F10
            let milestones: Set<String> = ["feature_started", "first_screen"]
            XCTAssertThrowsError(try CapabilityInstalledExecutionMode.requirePrivateF10(execution.installed.identity,
                milestones: milestones))
            var f10 = identity
            engine["ui_schema"] = 3
            engine["ui_contract_sha256"] = CapabilityInstalledExecutionMode.f10WireSHA256
            f10["engine"] = engine
            mode["startup_export"] = CapabilityInstalledExecutionMode.f10Startup
            f10["execution"] = mode
            let dependencies = [
                ["id": CapabilityInstalledExecutionMode.f10WireID, "version": "3",
                 "artifact_sha256": CapabilityInstalledExecutionMode.f10WireSHA256],
                ["id": CapabilityInstalledExecutionMode.f10HeaderID, "version": "3",
                 "artifact_sha256": CapabilityInstalledExecutionMode.f10HeaderSHA256],
            ]
            f10["dependencies"] = dependencies
            let f10Identity = try CapabilityRuntimeIdentity(privateDevelopmentF10JSON: json(f10))
            XCTAssertNoThrow(try CapabilityInstalledExecutionMode.requirePrivateF10(f10Identity, milestones: milestones))
            XCTAssertThrowsError(try CapabilityInstalledExecutionMode.requireFieldLogEditor(f10Identity, milestones: milestones))
            f10["dependencies"] = [["id": FieldLogEditorDevelopment.dependency, "version": "1",
                                   "artifact_sha256": FieldLogEditorDevelopment.contractSHA256]] + dependencies
            XCTAssertThrowsError(try CapabilityRuntimeIdentity(privateDevelopmentF10JSON: json(f10)))
#endif
        }
        return GuestUISignedFixture(root: directory, execution: execution, key: key)
    }
}
#endif
