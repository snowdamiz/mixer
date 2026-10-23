import Foundation
import MixerExperimentalCapabilityRuntime
@_spi(CapabilityDurableV3) import MixerUpdates

/// Store-local issuer identity. Only this source file can mint one.
final class CapabilityRecoverySelectionKey: Sendable { fileprivate init() {} }

/// Internal ingress owner. A future coordinator must transfer this to its one
/// counted closing owner and explicitly await close(). Deinit schedules no work
/// and performs no descriptor I/O; abandoning an open store pins its reservation.
final class CapabilityRecoveryStore: Sendable {
    private let worker: CapabilityRecoveryWorker
    private let control: CapabilityRecoveryControl
    private let obligation: CapabilityStoreObligation
    private let monotonic: @Sendable () -> UInt64
    private init(worker: CapabilityRecoveryWorker, control: CapabilityRecoveryControl, obligation: CapabilityStoreObligation, monotonic: @escaping @Sendable () -> UInt64) {
        self.worker = worker; self.control = control; self.obligation = obligation; self.monotonic = monotonic
    }
    static func open(admission: CapabilityRecoveryStoreAdmission, installed: InstalledMaterial,
                     configuration: CapabilityRecoveryConfiguration,
                     environment: CapabilityRecoveryEnvironment = .init()) async throws -> CapabilityRecoveryStore {
        let obligation = try admission.claimStore() // Before actor/configuration capture or any I/O.
        do {
            try validate(configuration)
            let control = CapabilityRecoveryControl(obligation: obligation)
            let worker = CapabilityRecoveryWorker(installed: installed, configuration: configuration,
                environment: environment, control: control, obligation: obligation)
            try obligation.retainOwner(worker) // Bounded cycle survives accidental façade drop.
            let store = CapabilityRecoveryStore(worker: worker, control: control, obligation: obligation, monotonic: environment.monotonic)
            let operation = try control.admit()
            do {
                try await withTaskCancellationHandler { try await worker.open(operation) } onCancel: { operation.cancel() }
                control.finish(operation); return store
            } catch {
                control.requestClose(); await worker.close(); control.finish(operation); throw error
            }
        } catch { obligation.retire(); throw error }
    }
    func beginDownload(signedManifest: Data, signedAssignment: Data) async throws {
        guard signedManifest.count <= 65_536, signedAssignment.count <= 65_536 else { throw capabilityRecoveryError("size") }
        let op = try control.admit(); defer { control.finish(op) }
        try await beginOwned(signedManifest, signedAssignment, op)
    }
    func downloadOffset() async throws -> UInt64 {
        let op = try control.admit(); defer { control.finish(op) }
        return try await withTaskCancellationHandler { try await worker.offset(op) } onCancel: { op.cancel() }
    }
    func appendDownload(_ bytes: Data, atOffset offset: UInt64) async throws {
        guard bytes.count <= 1_048_576 else { throw capabilityRecoveryError("size") }
        let op = try control.admit(); defer { control.finish(op) }
        try await appendOwned(bytes, offset, op)
    }
    func finishDownload() async throws {
        let op = try control.admit(); defer { control.finish(op) }
        do {
            try await withTaskCancellationHandler { try await worker.finish(op) } onCancel: { op.cancel() }
            await worker.finishRetired()
        } catch {
            await worker.finishRetired(); throw error
        }
    }
    func cancelDownload() async throws {
        let op = try control.admitCancellation(); defer { control.finishCancellation(op) }
        try await withTaskCancellationHandler { try await worker.cancelDownload(op) } onCancel: { op.cancel() }
    }
    func prepareStartupSelection() async throws -> CapabilityStartupSelection? {
        let op = try control.admit(); defer { control.finish(op) }
        let began = monotonic() // Before the worker hop, read and native validation.
        do {
            let selection = try await withTaskCancellationHandler { try await worker.prepareStartup(began: began, op) } onCancel: { op.cancel() }
            await worker.finishRetired(); return selection
        } catch { await worker.finishRetired(); throw error }
    }
    func consume(_ selection: CapabilityStartupSelection, signals: CapabilityAttemptSignals) async throws -> CapabilityConsumedStartup {
        let op = try control.admit(); defer { control.finish(op) }
        return try await withTaskCancellationHandler { try await worker.consume(selection, signals: signals, op) } onCancel: { op.cancel() }
    }
    func recordEffectsIntent(_ consumed: CapabilityConsumedStartup, signals: CapabilityAttemptSignals) async throws {
        let op = try control.admit(); defer { control.finish(op) }
        try await withTaskCancellationHandler { try await worker.recordEffectsIntent(consumed, signals: signals, op) } onCancel: { op.cancel() }
    }
    func confirmEffectsEnabled(_ consumed: CapabilityConsumedStartup, signals: CapabilityAttemptSignals) async throws {
        let op = try control.admit(); defer { control.finish(op) }
        try await withTaskCancellationHandler { try await worker.confirmEffectsEnabled(consumed, signals: signals, op) } onCancel: { op.cancel() }
    }
    func reportMilestone(_ consumed: CapabilityConsumedStartup, id: String) async throws {
        guard capabilityRecoveryIdentifier(id) else { throw capabilityRecoveryError("milestone") }
        let op = try control.admit(); defer { control.finish(op) }
        try await withTaskCancellationHandler { try await worker.reportMilestone(consumed, id: id, op) } onCancel: { op.cancel() }
    }
    func commitHealth(_ consumed: CapabilityConsumedStartup, signals: CapabilityAttemptSignals) async throws -> Bool {
        let op = try control.admit(); defer { control.finish(op) }
        return try await withTaskCancellationHandler { try await worker.commitHealth(consumed, signals: signals, op) } onCancel: { op.cancel() }
    }
    func failAndPrepareFallback(_ consumed: CapabilityConsumedStartup, signals: CapabilityAttemptSignals) async throws -> CapabilityRecoveryDisposition {
        let op = try control.admit(); defer { control.finish(op) }
        let began = monotonic() // Includes failure fsync and retained selection/validation.
        do {
            let result = try await withTaskCancellationHandler { try await worker.failAndPrepareFallback(consumed, signals: signals, began: began, op) } onCancel: { op.cancel() }
            await worker.finishRetired(); return result
        } catch { await worker.finishRetired(); throw error }
    }
    var snapshot: CapabilityRecoverySnapshot { control.snapshot }
    func close() async {
        if control.requestClose() { await worker.close() }
    }
    deinit {
        if !control.closeWasRequested {
            control.requestClose(); obligation.quarantine()
        }
    }
    // Owned snapshots live in these inner helpers, which return before the
    // outer operation-tail latch retires. This is a logical frame boundary, not
    // a claim about caller Task/runtime allocation destruction.
    private func beginOwned(_ manifest: Data, _ assignment: Data, _ op: CapabilityRecoveryOperation) async throws {
        try Task.checkCancellation()
        let m = Self.snapshot(manifest), a = Self.snapshot(assignment)
        try await withTaskCancellationHandler { try await worker.begin(m, a, op) } onCancel: { op.cancel() }
    }
    private func appendOwned(_ bytes: Data, _ offset: UInt64, _ op: CapabilityRecoveryOperation) async throws {
        try Task.checkCancellation()
        let snapshot = Self.snapshot(bytes)
        try await withTaskCancellationHandler { try await worker.append(snapshot, offset: offset, op) } onCancel: { op.cancel() }
    }
    private static func snapshot(_ bytes: Data) -> Data {
        bytes.withUnsafeBytes { $0.isEmpty ? Data() : Data(bytes: $0.baseAddress!, count: $0.count) }
    }
    private static func validate(_ c: CapabilityRecoveryConfiguration) throws {
        guard c.directory.isFileURL, c.directory.path.utf8.prefix(4097).count <= 4096,
              c.directory.path.hasPrefix("/"), !c.directory.path.utf8.contains(0),
              capabilityRecoveryIdentifier(c.channel), capabilityRecoveryIdentifier(c.installation),
              (1...10).contains(c.failureThreshold), (1...3600).contains(c.observationSeconds),
              (1...16).contains(c.requiredMilestones.count), c.requiredMilestones.allSatisfy(capabilityRecoveryIdentifier) else {
            throw capabilityRecoveryError("configuration")
        }
    }
}

/// One ordinary operation plus one coalesced cancellation/close path. All input
/// copies happen after admission. No Task/Task.detached or queue is created here.
private final class CapabilityRecoveryControl: @unchecked Sendable {
    private let lock = NSLock()
    private let obligation: CapabilityStoreObligation
    private var ioClosed = false
    private var retired = false
    init(obligation: CapabilityStoreObligation) { self.obligation = obligation }
    private var next: UInt64 = 0
    private var ordinary: CapabilityRecoveryOperation?
    private var cancellation: CapabilityRecoveryOperation?
    private var closed = false
    private var closeRequested = false
    private var report = CapabilityRecoverySnapshot()
    func admit() throws -> CapabilityRecoveryOperation {
        lock.lock(); defer { lock.unlock() }
        guard !closed, ordinary == nil, cancellation == nil else { throw capabilityRecoveryError(closed ? "closed" : "busy") }
        let op = try makeOperation(); ordinary = op; report.busy = true; return op
    }
    func admitCancellation() throws -> CapabilityRecoveryOperation {
        lock.lock()
        do {
            guard !closed, cancellation == nil else { throw capabilityRecoveryError(closed ? "closed" : "busy") }
            let op = try makeOperation(), old = ordinary; cancellation = op; report.busy = true
            lock.unlock(); old?.cancel(); return op
        } catch { lock.unlock(); throw error }
    }
    private func makeOperation() throws -> CapabilityRecoveryOperation {
        guard next < UInt64.max else { closed = true; report.closed = true; throw capabilityRecoveryError("generation") }
        next += 1; return CapabilityRecoveryOperation(generation: next)
    }
    func finish(_ op: CapabilityRecoveryOperation) {
        lock.lock()
        if ordinary === op { ordinary = nil }; report.busy = ordinary != nil || cancellation != nil
        let release = retireReady(); lock.unlock()
        if release { obligation.retire() }
    }
    func finishCancellation(_ op: CapabilityRecoveryOperation) {
        lock.lock()
        if cancellation === op { cancellation = nil }; report.busy = ordinary != nil || cancellation != nil
        let release = retireReady(); lock.unlock()
        if release { obligation.retire() }
    }
    func markIOClosed() {
        lock.lock(); ioClosed = true; let release = retireReady(); lock.unlock()
        if release { obligation.retire() }
    }
    private func retireReady() -> Bool {
        guard ioClosed, ordinary == nil, cancellation == nil, !retired else { return false }
        retired = true; return true
    }
    @discardableResult func requestClose() -> Bool {
        lock.lock(); let first = !closeRequested; closeRequested = true; closed = true; report.closed = true
        let old = ordinary, cancel = cancellation; lock.unlock()
        old?.cancel(); cancel?.cancel(); return first
    }
    var closeWasRequested: Bool { lock.lock(); defer { lock.unlock() }; return closeRequested }
    var snapshot: CapabilityRecoverySnapshot { lock.lock(); defer { lock.unlock() }; return report }
    func publish(_ state: CapabilityRecoveryState?, poisoned: Bool) {
        lock.lock(); defer { lock.unlock() }
        report.requiresReopen = poisoned
        if let state {
            report.acceptedSequence = state.acceptedSequence; report.downloading = state.pending?.candidateID
            report.staged = state.staged; report.healthy = state.healthy?.candidateID
            report.previousHealthy = state.previousHealthy?.candidateID; report.retainedCandidates = state.candidates.count
            report.incompleteAttempt = state.attempt != nil
        }
    }
}
private final class CapabilityRecoveryOperation: @unchecked Sendable {
    let generation: UInt64
    private let lock = NSLock()
    private var cancelled = false
    private var validator: ExperimentalCapabilityValidation?
    init(generation: UInt64) { self.generation = generation }
    func cancel() {
        lock.lock(); cancelled = true; let v = validator; lock.unlock(); v?.cancel()
    }
    func check() throws {
        lock.lock(); let stopped = cancelled; lock.unlock()
        if stopped { throw CancellationError() }
    }
    func attach(_ v: ExperimentalCapabilityValidation) {
        lock.lock(); validator = v; let stopped = cancelled; lock.unlock()
        if stopped { v.cancel() }
    }
    func detach() { lock.lock(); validator = nil; lock.unlock() }
    func enterCommit() throws {
        // The lock acquisition is the commit-entry linearization point. After
        // this check synchronous actor I/O is nonpreemptible; cancellation cannot
        // roll it back and all actual/uncertain outcomes must still be recorded.
        try check()
    }
}

private actor CapabilityRecoveryWorker {
    private let installed: InstalledMaterial
    private let configuration: CapabilityRecoveryConfiguration
    private let environment: CapabilityRecoveryEnvironment
    private let control: CapabilityRecoveryControl
    private let obligation: CapabilityStoreObligation
    private var directory: CapabilityDurableDirectory?
    private var state: CapabilityRecoveryState?
    private var poisoned = false
    private var closed = false
    private var validating = false
    private let selectionKey = CapabilityRecoverySelectionKey()
    private var selectionEpoch: UInt64 = 0
    private var selectionStarted = false
    private var retainedTried = false
    private var recoveryRequired = false
    private var prepared: CapabilityStartupSelection?
    private var active: CapabilityConsumedStartup?
    private var activeSignals: CapabilityAttemptSignals?
    private var effectsEnabledAt: UInt64?
    private var milestones: Set<String> = []
    init(installed: InstalledMaterial, configuration: CapabilityRecoveryConfiguration,
         environment: CapabilityRecoveryEnvironment, control: CapabilityRecoveryControl, obligation: CapabilityStoreObligation) {
        self.installed = installed; self.configuration = configuration; self.environment = environment
        self.control = control; self.obligation = obligation
    }
    func open(_ op: CapabilityRecoveryOperation) throws {
        try op.check()
        let d = try CapabilityDurableDirectory(url: configuration.directory, fault: environment.fault)
        directory = d
        do {
            if let bytes = try d.read("state.json", maximumBytes: 1_048_576) {
                let decoded = try StrictJSON.decode(CapabilityRecoveryState.self, from: bytes)
                try validate(decoded); state = decoded
            } else {
                guard d.wasCreated else { throw capabilityRecoveryError("state_missing") }
                let initial = CapabilityRecoveryState(installed: installed, configuration: configuration)
                try commit(initial, op)
            }
            if let interrupted = state?.attempt, var next = state {
                next.lastRecovery = interrupted.effectsMayHaveOpened ? "unknown_interruption_after_effects" : "unknown_interruption"
                next.attempt = nil
                try commit(next, op)
            }
            try op.check(); try cleanup(); publish()
        } catch { d.close(); directory = nil; closed = true; control.markIOClosed(); throw error }
    }
    func begin(_ manifest: Data, _ assignment: Data, _ op: CapabilityRecoveryOperation) throws {
        let (d, s) = try available(op)
        guard !selectionStarted else { throw capabilityRecoveryError("selection_started") }
        guard s.quarantine.count < 256, s.failures.count < 256 else { throw capabilityRecoveryError("history") }
        let offer = try installed.verifier._authorizeOfferV3(exactManifest: manifest, exactAssignment: assignment,
            channel: configuration.channel, installation: configuration.installation, lastSequence: s.acceptedSequence, now: environment.wall())
        guard s.quarantine[offer.artifactSHA256] == nil else { throw capabilityRecoveryError("quarantine") }
        try reserve(offer.payloadBytes, d)
        let pending = try CapabilityRecoveryCandidate(artifact: offer.artifactSHA256, payloadHash: offer.payloadSHA256,
            payloadBytes: offer.payloadBytes, sequence: offer.sequence, manifest: offer.signedManifest, assignment: offer.signedAssignment)
        var next = s; next.acceptedSequence = offer.sequence; next.pending = pending
        try commit(next, op); try cleanup(); try op.check()
    }
    func offset(_ op: CapabilityRecoveryOperation) throws -> UInt64 {
        let (d, s) = try available(op); let pending = try pending(s)
        try authorizePending(pending, s)
        if let size = try d.size(part(pending)) {
            guard size <= pending.payloadBytes else { throw capabilityRecoveryError("partial") }; return size
        }
        if let bytes = try d.read(payload(pending), maximumBytes: Int(pending.payloadBytes)) {
            guard UInt64(bytes.count) == pending.payloadBytes, ReleaseVerifier.sha256(bytes) == pending.payloadSHA256 else { throw capabilityRecoveryError("payload") }
            return pending.payloadBytes
        }
        return 0
    }
    func append(_ bytes: Data, offset: UInt64, _ op: CapabilityRecoveryOperation) throws {
        let (d, s) = try available(op); let pending = try pending(s)
        try authorizePending(pending, s)
        guard offset <= pending.payloadBytes, UInt64(bytes.count) <= pending.payloadBytes - offset else { throw capabilityRecoveryError("offset") }
        try reserve(pending.payloadBytes - offset, d); try op.enterCommit()
        do { try d.append(bytes, to: part(pending), offset: offset, maximumBytes: pending.payloadBytes) }
        catch { poison(); throw error }
        try op.check()
    }
    func finish(_ op: CapabilityRecoveryOperation) async throws {
        let began = environment.monotonic()
        let (d, s) = try available(op); let candidate = try pending(s)
        try authorizePending(candidate, s)
        let bytes: Data
        if let partial = try d.read(part(candidate), maximumBytes: Int(candidate.payloadBytes)) { bytes = partial }
        else if let existing = try d.read(payload(candidate), maximumBytes: Int(candidate.payloadBytes)) { bytes = existing }
        else { throw capabilityRecoveryError("payload_missing") }
        let artifact = try installed.verifier.verifyArtifact(signedManifest: candidate.signedManifest, payload: bytes, now: environment.wall())
        let assignment = try installed.verifier.verifyAssignment(signedAssignment: candidate.signedAssignment, artifact: artifact,
            channel: configuration.channel, installation: configuration.installation, lastSequence: 0, now: environment.wall())
        guard assignment.sequence == candidate.sequence else { throw capabilityRecoveryError("binding") }
        let interval = min(artifact.resourceLimits.startupMilliseconds, installed.identity.installedRuntime.limits.startupMilliseconds)
        let delta = interval.multipliedReportingOverflow(by: 1_000_000)
        let end = began.addingReportingOverflow(delta.partialValue)
        guard !delta.overflow, !end.overflow else { throw capabilityRecoveryError("deadline") }
        try current(op, candidate: candidate, began: began, cutoff: end.partialValue)
        let validation = try ExperimentalCapabilityValidator.prepare(module: bytes,
            startupExport: installed.identity.execution.startupExport, configuration: CapabilityExecutionPolicy.nativeConfiguration(installed: installed, signed: artifact.resourceLimits))
        op.attach(validation); validating = true
        defer { op.detach() }
        if let gate = environment.beforeValidation { await gate() }
        try current(op, candidate: candidate, began: began, cutoff: end.partialValue)
        try await validation.validate()
        if let gate = environment.afterValidation { await gate() }
        try current(op, candidate: candidate, began: began, cutoff: end.partialValue)
        _ = try installed.verifier.revalidateArtifact(artifact, payload: bytes, now: environment.wall())
        let fresh = try installed.verifier.verifyAssignment(signedAssignment: candidate.signedAssignment, artifact: artifact,
            channel: configuration.channel, installation: configuration.installation, lastSequence: 0, now: environment.wall())
        guard fresh.sequence == candidate.sequence else { throw capabilityRecoveryError("binding") }
        guard let latest = state else { throw capabilityRecoveryError("closed") }
        var next = latest; next.candidates[candidate.candidateID] = candidate
        next.staged = candidate.candidateID; next.pending = nil
        compact(&next)
        let encoded = try encode(next)
        try current(op, candidate: candidate, began: began, cutoff: end.partialValue); try op.enterCommit()
        do {
            if let existing = try d.read(payload(candidate), maximumBytes: Int(candidate.payloadBytes)) {
                guard UInt64(existing.count) == candidate.payloadBytes, ReleaseVerifier.sha256(existing) == candidate.payloadSHA256 else { throw capabilityRecoveryError("payload") }
                try d.remove(part(candidate))
            } else { try d.publishPayload(part(candidate), as: payload(candidate)) }
            state = next; try d.atomicState(encoded); publish(); try cleanup()
        } catch { poison(); throw error }
        try op.check()
    }
    func cancelDownload(_ op: CapabilityRecoveryOperation) throws {
        let (_, s) = try available(op)
        var next = s; next.pending = nil
        try commit(next, op); try cleanup(); try op.check()
    }
    func prepareStartup(began: UInt64, _ op: CapabilityRecoveryOperation) async throws -> CapabilityStartupSelection? {
        let (_, s) = try available(op)
        guard !selectionStarted, !recoveryRequired, s.attempt == nil else { throw capabilityRecoveryError("selection_started") }
        selectionStarted = true
        if let id = s.staged, let candidate = s.candidates[id], s.quarantine[candidate.artifactSHA256] == nil {
            do { return try await prepareOne(candidate, source: .fresh, began: began, op) }
            catch {
                try selectionFailureMayFallback(op)
                // A failed read/admission is never an executed deterministic trap.
                try recordSelectionRejection(op)
            }
        }
        return try await prepareRetained(excludingArtifact: nil, began: began, op)
    }
    private func prepareRetained(excludingArtifact: String?, began: UInt64, _ op: CapabilityRecoveryOperation) async throws -> CapabilityStartupSelection? {
        let (_, s) = try available(op)
        guard !retainedTried, !recoveryRequired else { return nil }
        // Select one eligible real committed record, not caller-supplied evidence.
        let eligible = [s.healthy, s.previousHealthy].compactMap { $0 }.first { health in
            guard let c = s.candidates[health.candidateID] else { return false }
            return c.artifactSHA256 != excludingArtifact && s.quarantine[c.artifactSHA256] == nil
        }
        guard let health = eligible, let candidate = s.candidates[health.candidateID] else { return nil }
        retainedTried = true
        do { return try await prepareOne(candidate, source: .retained, began: began, op) }
        catch { try selectionFailureMayFallback(op); try recordSelectionRejection(op); return nil }
    }
    private func selectionFailureMayFallback(_ op: CapabilityRecoveryOperation) throws {
        _ = try available(op) // Cancellation, close and uncertain I/O never recover in place.
        guard state?.attempt == nil else { throw capabilityRecoveryError("attempt_active") }
    }
    private func recordSelectionRejection(_ op: CapabilityRecoveryOperation) throws {
        let (_, s) = try available(op)
        guard s.lastRecovery != "selection_rejected" else { return }
        var next = s; next.lastRecovery = "selection_rejected"
        try commit(next, op)
    }
    private func prepareOne(_ candidate: CapabilityRecoveryCandidate, source: CapabilitySelectionSource,
                            began: UInt64, _ op: CapabilityRecoveryOperation) async throws -> CapabilityStartupSelection {
        let (d, s) = try available(op)
        guard s.attempt == nil, s.candidates[candidate.candidateID]?.candidateID == candidate.candidateID,
              s.quarantine[candidate.artifactSHA256] == nil else { throw capabilityRecoveryError("selection") }
        if source == .retained { try requireStoredHealth(candidate.candidateID, s) }
        guard let bytes = try d.read(payload(candidate), maximumBytes: Int(candidate.payloadBytes)),
              UInt64(bytes.count) == candidate.payloadBytes, ReleaseVerifier.sha256(bytes) == candidate.payloadSHA256 else {
            throw capabilityRecoveryError("payload")
        }
        let evidence: CapabilitySelectionEvidence
        let policy: CapabilityExecutionPolicy
        switch source {
        case .fresh:
            let artifact = try fresh(candidate, bytes, s)
            evidence = .fresh(artifact)
            policy = try CapabilityExecutionPolicy(installed: installed, artifact: artifact, payload: bytes, now: environment.wall())
        case .retained:
            let retained = try installed.verifier._verifyRetainedHealthySnapshotV3(exactManifest: candidate.signedManifest,
                exactAssignment: candidate.signedAssignment, payload: bytes, channel: configuration.channel,
                installation: configuration.installation, storedSequence: candidate.sequence, acceptedSequence: s.acceptedSequence)
            guard retained.artifactSHA256 == candidate.artifactSHA256, retained.payloadSHA256 == candidate.payloadSHA256,
                  retained.payloadBytes == candidate.payloadBytes else { throw capabilityRecoveryError("binding") }
            evidence = .retained(retained)
            policy = try CapabilityExecutionPolicy(installed: installed, retained: retained, payload: bytes)
        }
        let cutoff = try startupCutoff(began: began, interval: policy.startupMilliseconds)
        try selectedCurrent(candidate, source: source, began: began, cutoff: cutoff, op)
        let validator = try ExperimentalCapabilityValidator.prepare(module: bytes,
            startupExport: installed.identity.execution.startupExport, configuration: policy.native)
        op.attach(validator); validating = true
        defer { op.detach() }
        if let gate = environment.beforeValidation { await gate() }
        try selectedCurrent(candidate, source: source, began: began, cutoff: cutoff, op)
        try await validator.validate()
        if let gate = environment.afterValidation { await gate() }
        try selectedCurrent(candidate, source: source, began: began, cutoff: cutoff, op)
        try revalidate(evidence, candidate: candidate, bytes: bytes)
        guard selectionEpoch < UInt64.max else { recoveryRequired = true; throw capabilityRecoveryError("generation") }
        let epoch = selectionEpoch + 1, launch = UUID().uuidString
        let input = CapabilityConsumedStartup(key: selectionKey, module: bytes, startupExport: installed.identity.execution.startupExport,
            policy: policy, evidence: evidence, source: source, candidateID: candidate.candidateID, launchID: launch,
            generation: epoch, began: began, cutoff: cutoff)
        let result = CapabilityStartupSelection(key: selectionKey, input: input)
        guard var next = state else { throw capabilityRecoveryError("closed") }
        next.attempt = CapabilityStoredAttempt(launchID: launch, candidateID: candidate.candidateID,
            source: source == .fresh ? "fresh" : "healthy", startedAtWallTime: environment.wall(), effectsMayHaveOpened: false)
        // No construction is possible until this exact attempt is durable.
        try commit(next, op)
        selectionEpoch = epoch; prepared = result
        // If cancellation/cutoff wins during fsync, explicitly discard this
        // unconsumed attempt; never leave an orphan or publish late authority.
        do { try op.check(); try checkStartupClock(began: began, cutoff: cutoff) }
        catch { try discardPrepared(result); throw error }
        return result
    }
    func consume(_ selection: CapabilityStartupSelection, signals: CapabilityAttemptSignals,
                 _ op: CapabilityRecoveryOperation) throws -> CapabilityConsumedStartup {
        let (_, s) = try available(op)
        guard prepared === selection, active == nil, signals.generation == selection.generation,
              s.attempt?.launchID == selection.launchID else { throw capabilityRecoveryError("selection") }
        do {
            try checkStartupClock(began: selection.startupBeganUptimeNanoseconds, cutoff: selection.startupCutoffUptimeNanoseconds)
            try signals.requireCommitEntry(expectedGeneration: selection.generation)
            let input = try selection.inspect(for: selectionKey)
            guard let candidate = s.candidates[input.candidateID] else { throw capabilityRecoveryError("selection") }
            try revalidate(input.evidence, candidate: candidate, bytes: input.module)
            try op.check(); try signals.requireCommitEntry(expectedGeneration: input.generation)
            _ = try selection.take(for: selectionKey)
            prepared = nil; active = input; activeSignals = signals
            return input
        } catch {
            do { try discardPrepared(selection) }
            catch { poison(); throw CapabilitySelectionConsumeError.cleanupRequiresReopen }
            throw CapabilitySelectionConsumeError.rejected
        }
    }
    private func discardPrepared(_ selection: CapabilityStartupSelection) throws {
        guard prepared === selection, let directory, var next = state,
              next.attempt?.launchID == selection.launchID, next.attempt?.effectsMayHaveOpened == false else {
            throw capabilityRecoveryError("selection")
        }
        next.attempt = nil; next.lastRecovery = "selection_rejected"
        let encoded = try encode(next)
        // This is bounded cleanup of the already entered attempt transaction,
        // not acceptance or rollback. It must run even if its operation stopped.
        state = next; selection.invalidate(for: selectionKey); prepared = nil
        do { try directory.atomicState(encoded); publish() } catch { poison(); throw error }
    }
    func recordEffectsIntent(_ input: CapabilityConsumedStartup, signals: CapabilityAttemptSignals,
                             _ op: CapabilityRecoveryOperation) throws {
        let (d, s) = try bound(input, signals, op)
        try checkStartupClock(began: input.startupBeganUptimeNanoseconds, cutoff: input.startupCutoffUptimeNanoseconds)
        guard let candidate = s.candidates[input.candidateID], let attempt = s.attempt, !attempt.effectsMayHaveOpened else { throw capabilityRecoveryError("effects_intent") }
        try revalidate(input.evidence, candidate: candidate, bytes: input.module)
        var next = s; next.attempt = attempt.recordingEffectsIntent()
        let encoded = try encode(next)
        try op.enterCommit(); try signals.enterEffectsIntentCommit(expectedGeneration: input.generation)
        // The sticky latch wins even if the following write is uncertain.
        state = next
        do { try d.atomicState(encoded); publish() } catch { recoveryRequired = true; poison(); throw error }
        try op.check(); try signals.requireCommitEntry(expectedGeneration: input.generation)
    }
    func confirmEffectsEnabled(_ input: CapabilityConsumedStartup, signals: CapabilityAttemptSignals,
                               _ op: CapabilityRecoveryOperation) throws {
        let (_, s) = try bound(input, signals, op)
        guard s.attempt?.effectsMayHaveOpened == true, signals.snapshot.effectsMayHaveOpened,
              effectsEnabledAt == nil else { throw capabilityRecoveryError("enable") }
        try checkStartupClock(began: input.startupBeganUptimeNanoseconds, cutoff: input.startupCutoffUptimeNanoseconds)
        try signals.requireCommitEntry(expectedGeneration: input.generation)
        // Only the private coordinator calls this AFTER actual native enable.
        effectsEnabledAt = environment.monotonic()
    }
    func reportMilestone(_ input: CapabilityConsumedStartup, id: String, _ op: CapabilityRecoveryOperation) throws {
        guard let signals = activeSignals else { throw capabilityRecoveryError("attempt") }
        _ = try bound(input, signals, op)
        guard effectsEnabledAt != nil, configuration.requiredMilestones.contains(id) else { throw capabilityRecoveryError("milestone") }
        try signals.requireCommitEntry(expectedGeneration: input.generation)
        milestones.insert(id) // Fixed installed <=16 set; duplicates are idempotent.
    }
    func commitHealth(_ input: CapabilityConsumedStartup, signals: CapabilityAttemptSignals,
                      _ op: CapabilityRecoveryOperation) throws -> Bool {
        let (d, s) = try bound(input, signals, op)
        guard let began = effectsEnabledAt, configuration.requiredMilestones.isSubset(of: milestones),
              let candidate = s.candidates[input.candidateID], s.attempt?.effectsMayHaveOpened == true else { throw capabilityRecoveryError("health") }
        let now = environment.monotonic(), interval = configuration.observationSeconds * 1_000_000_000
        guard now >= began, now - began >= interval else { throw capabilityRecoveryError("observation") }
        try revalidate(input.evidence, candidate: candidate, bytes: input.module)
        var next = s
        let health = CapabilityStoredHealth(candidateID: input.candidateID, launchID: input.launchID,
            committedAtWallTime: environment.wall(), observationSeconds: configuration.observationSeconds, completedMilestones: milestones)
        if next.healthy?.candidateID != input.candidateID { next.previousHealthy = next.healthy }
        next.healthy = health // Retained may reaffirm only its exact existing record.
        let encoded = try encode(next)
        try op.enterCommit(); try signals.requireCommitEntry(expectedGeneration: input.generation)
        state = next
        do { try d.atomicState(encoded); publish() } catch { recoveryRequired = true; poison(); throw error }
        // A concurrent terminal cannot undo entered I/O or masquerade as health.
        try op.check()
        return !signals.snapshot.stopped
    }
    func failAndPrepareFallback(_ input: CapabilityConsumedStartup, signals: CapabilityAttemptSignals,
                                began: UInt64, _ op: CapabilityRecoveryOperation) async throws -> CapabilityRecoveryDisposition {
        let (_, s) = try bound(input, signals, op)
        guard let candidate = s.candidates[input.candidateID] else { throw capabilityRecoveryError("attempt") }
        let snapshot = signals.snapshot
        guard snapshot.stopped else { throw capabilityRecoveryError("terminal_missing") }
        let failure = CapabilityRecoveryFailure.classify(snapshot)
        let effects = snapshot.effectsMayHaveOpened || s.attempt?.effectsMayHaveOpened == true
        var next = s
        if failure == .deterministicTrap {
            let old = next.failures[candidate.artifactSHA256] ?? 0
            guard old > 0 || next.failures.count < 256 else { throw capabilityRecoveryError("history") }
            let count = min(configuration.failureThreshold, old + 1)
            next.failures[candidate.artifactSHA256] = count
            if count >= configuration.failureThreshold {
                guard next.quarantine[candidate.artifactSHA256] != nil || next.quarantine.count < 256 else { throw capabilityRecoveryError("history") }
                next.quarantine[candidate.artifactSHA256] = "deterministic_trap"
            }
        }
        next.lastRecovery = (effects ? "effects_" : "") + failure.rawValue
        next.attempt = nil
        try commit(next, op)
        prepared = nil; active = nil; activeSignals = nil; effectsEnabledAt = nil; milestones.removeAll()
        if effects { recoveryRequired = true; return .recoveryRequired }
        // Cancellation/deadline/explicit close stop the whole owner, never start
        // a replacement under a retired coordinator generation.
        if [.cancelled, .deadline, .closed].contains(failure) { return .nativeFallback }
        if let selection = try await prepareRetained(excludingArtifact: candidate.artifactSHA256, began: began, op) { return .selection(selection) }
        return .nativeFallback
    }
    private func bound(_ input: CapabilityConsumedStartup, _ signals: CapabilityAttemptSignals,
                       _ op: CapabilityRecoveryOperation) throws -> (CapabilityDurableDirectory, CapabilityRecoveryState) {
        let result = try available(op)
        guard active === input, activeSignals === signals, input.wasIssued(by: selectionKey),
              selectionEpoch == input.generation, signals.generation == input.generation,
              result.1.attempt?.candidateID == input.candidateID, result.1.attempt?.launchID == input.launchID else {
            throw capabilityRecoveryError("attempt")
        }
        return result
    }
    private func selectedCurrent(_ candidate: CapabilityRecoveryCandidate, source: CapabilitySelectionSource,
                                 began: UInt64, cutoff: UInt64, _ op: CapabilityRecoveryOperation) throws {
        let (_, s) = try available(op)
        guard s.attempt == nil, s.candidates[candidate.candidateID]?.candidateID == candidate.candidateID,
              s.quarantine[candidate.artifactSHA256] == nil else { throw capabilityRecoveryError("stale") }
        if source == .retained { try requireStoredHealth(candidate.candidateID, s) }
        try checkStartupClock(began: began, cutoff: cutoff)
    }
    private func requireStoredHealth(_ id: String, _ s: CapabilityRecoveryState) throws {
        guard [s.healthy, s.previousHealthy].contains(where: { $0?.candidateID == id }) else { throw capabilityRecoveryError("retained_provenance") }
    }
    private func fresh(_ c: CapabilityRecoveryCandidate, _ bytes: Data, _ s: CapabilityRecoveryState) throws -> VerifiedArtifactV3 {
        let artifact = try installed.verifier.verifyArtifact(signedManifest: c.signedManifest, payload: bytes, now: environment.wall())
        let assignment = try installed.verifier.verifyAssignment(signedAssignment: c.signedAssignment, artifact: artifact,
            channel: configuration.channel, installation: configuration.installation, lastSequence: 0, now: environment.wall())
        guard assignment.sequence == c.sequence, c.sequence <= s.acceptedSequence,
              artifact.artifactSHA256 == c.artifactSHA256, UInt64(bytes.count) == c.payloadBytes,
              ReleaseVerifier.sha256(bytes) == c.payloadSHA256 else { throw capabilityRecoveryError("binding") }
        return artifact
    }
    private func revalidate(_ evidence: CapabilitySelectionEvidence, candidate: CapabilityRecoveryCandidate, bytes: Data) throws {
        guard let s = state, s.quarantine[candidate.artifactSHA256] == nil else { throw capabilityRecoveryError("quarantine") }
        switch evidence {
        case .fresh(let artifact):
            _ = try installed.verifier.revalidateArtifact(artifact, payload: bytes, now: environment.wall())
            _ = try fresh(candidate, bytes, s)
        case .retained(let retained):
            try requireStoredHealth(candidate.candidateID, s)
            let checked = try installed.verifier._revalidateRetainedHealthyV3(retained, payload: bytes)
            guard checked.signedManifest == candidate.signedManifest, checked.signedAssignment == candidate.signedAssignment,
                  checked.sequence == candidate.sequence, checked.sequence <= s.acceptedSequence else { throw capabilityRecoveryError("binding") }
        }
    }
    private func startupCutoff(began: UInt64, interval: UInt64) throws -> UInt64 {
        let ns = interval.multipliedReportingOverflow(by: 1_000_000), end = began.addingReportingOverflow(ns.partialValue)
        guard !ns.overflow, !end.overflow else { throw capabilityRecoveryError("deadline") }
        return end.partialValue
    }
    private func checkStartupClock(began: UInt64, cutoff: UInt64) throws {
        let now = environment.monotonic()
        guard now >= began, now < cutoff else { throw capabilityRecoveryError("deadline") }
    }

    // Called only after finish() has actually returned to its ingress owner, so
    // its payload/validator frame no longer precedes outer-slot retirement.
    func finishRetired() { validating = false; retireIfClosed() }
    func close() {
        if !closed {
            closed = true; activeSignals?.requestStop(.closed)
            directory?.close(); directory = nil; publish(); state = nil
            prepared?.invalidate(for: selectionKey)
            prepared = nil; active = nil; activeSignals = nil; effectsEnabledAt = nil; milestones.removeAll()
        }
        retireIfClosed()
    }
    private func retireIfClosed() { if closed && !validating { control.markIOClosed() } }
    private func available(_ op: CapabilityRecoveryOperation) throws -> (CapabilityDurableDirectory, CapabilityRecoveryState) {
        try op.check()
        guard !closed, !poisoned, let directory, let state else { throw capabilityRecoveryError("unavailable") }
        return (directory, state)
    }
    private func pending(_ s: CapabilityRecoveryState) throws -> CapabilityRecoveryCandidate {
        guard let p = s.pending else { throw capabilityRecoveryError("download_absent") }; return p
    }
    private func authorizePending(_ p: CapabilityRecoveryCandidate, _ s: CapabilityRecoveryState) throws {
        let o = try installed.verifier._authorizeOfferV3(exactManifest: p.signedManifest, exactAssignment: p.signedAssignment,
            channel: configuration.channel, installation: configuration.installation, lastSequence: 0, now: environment.wall())
        guard o.artifactSHA256 == p.artifactSHA256, o.sequence == p.sequence, p.sequence == s.acceptedSequence,
              o.payloadSHA256 == p.payloadSHA256, o.payloadBytes == p.payloadBytes, s.quarantine[p.artifactSHA256] == nil else {
            throw capabilityRecoveryError("binding")
        }
    }
    private func current(_ op: CapabilityRecoveryOperation, candidate: CapabilityRecoveryCandidate, began: UInt64, cutoff: UInt64) throws {
        let (_, s) = try available(op)
        guard s.pending?.candidateID == candidate.candidateID, s.acceptedSequence == candidate.sequence else { throw capabilityRecoveryError("stale") }
        let now = environment.monotonic()
        guard now >= began, now < cutoff else { op.cancel(); throw capabilityRecoveryError("deadline") }
    }
    private func commit(_ next: CapabilityRecoveryState, _ op: CapabilityRecoveryOperation) throws {
        guard let directory else { throw capabilityRecoveryError("closed") }
        let encoded = try encode(next); try op.enterCommit()
        state = next
        do { try directory.atomicState(encoded); publish() } catch { poison(); throw error }
    }
    private func encode(_ next: CapabilityRecoveryState) throws -> Data {
        try validate(next)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let bytes = try encoder.encode(next)
        guard bytes.count <= 1_048_576 else { throw capabilityRecoveryError("size") }; return bytes
    }
    private func validate(_ s: CapabilityRecoveryState) throws {
        guard s.kind == "mixer-capability-cold-start-v1", s.schemaVersion == 3,
              s.fingerprint == installed.identity.fingerprint, s.host == installed.identity.installedRuntime,
              s.channel == configuration.channel, s.installation == configuration.installation,
              s.candidates.count <= 4, s.failures.count <= 256, s.quarantine.count <= 256,
              s.failures.allSatisfy({ capabilityRecoveryDigest($0.key) && $0.value <= configuration.failureThreshold }),
              s.quarantine.allSatisfy({ capabilityRecoveryDigest($0.key) && capabilityRecoveryIdentifier($0.value) }),
              s.lastRecovery.isEmpty || capabilityRecoveryIdentifier(s.lastRecovery) else { throw capabilityRecoveryError("state") }
        func candidate(_ c: CapabilityRecoveryCandidate) throws {
            guard capabilityRecoveryDigest(c.candidateID), capabilityRecoveryDigest(c.artifactSHA256), capabilityRecoveryDigest(c.payloadSHA256),
                  c.sequence > 0, c.sequence <= s.acceptedSequence, (1...s.host.maxPayloadBytes).contains(c.payloadBytes),
                  c.signedManifest.count <= 65_536, c.signedAssignment.count <= 65_536,
                  try c.candidateID == CapabilityRecoveryCandidate.id(artifact: c.artifactSHA256, sequence: c.sequence,
                    manifest: c.signedManifest, assignment: c.signedAssignment) else { throw capabilityRecoveryError("state") }
        }
        for (id, c) in s.candidates { guard id == c.candidateID else { throw capabilityRecoveryError("state") }; try candidate(c) }
        if let p = s.pending { try candidate(p); guard p.sequence == s.acceptedSequence else { throw capabilityRecoveryError("state") } }
        if let staged = s.staged { guard s.candidates[staged] != nil else { throw capabilityRecoveryError("state") } }
        for health in [s.healthy, s.previousHealthy].compactMap({ $0 }) {
            guard s.candidates[health.candidateID] != nil, capabilityRecoveryIdentifier(health.launchID), health.committedAtWallTime > 0,
                  (1...3600).contains(health.observationSeconds), health.observationSeconds >= configuration.observationSeconds,
                  health.completedMilestones.count <= 16, health.completedMilestones.allSatisfy(capabilityRecoveryIdentifier),
                  configuration.requiredMilestones.isSubset(of: health.completedMilestones) else { throw capabilityRecoveryError("state") }
        }
        if let a = s.attempt {
            guard s.candidates[a.candidateID] != nil, capabilityRecoveryIdentifier(a.launchID), ["fresh", "healthy"].contains(a.source), a.startedAtWallTime > 0 else { throw capabilityRecoveryError("state") }
        }
    }
    private func compact(_ s: inout CapabilityRecoveryState) {
        let keep = Set([s.staged, s.healthy?.candidateID, s.previousHealthy?.candidateID, s.attempt?.candidateID].compactMap { $0 })
        for id in s.candidates.keys.sorted() where s.candidates.count > 4 && !keep.contains(id) { s.candidates.removeValue(forKey: id) }
    }
    private func cleanup() throws {
        guard let directory, let state else { return }
        var names: Set<String> = ["state.json", ".lock"]
        for c in state.candidates.values { names.insert(payload(c)) }
        if let p = state.pending { names.insert(part(p)); names.insert(payload(p)) }
        do { try directory.pruneOwnedFiles(keeping: names) } catch { poison(); throw error }
    }
    private func reserve(_ bytes: UInt64, _ d: CapabilityDurableDirectory) throws {
        let free = try d.availableBytes()
        guard free >= bytes, free - bytes >= configuration.reserveDiskBytes else { throw capabilityRecoveryError("disk") }
    }
    private func publish() { control.publish(state, poisoned: poisoned) }
    private func poison() { poisoned = true; publish() }
    private func part(_ c: CapabilityRecoveryCandidate) -> String { c.candidateID + ".payload.part" }
    private func payload(_ c: CapabilityRecoveryCandidate) -> String { c.payloadSHA256 + ".payload" }
}
