import Foundation

/// Explicit capability cold-start owner. Executable bytes enter only through
/// signed downloads and this instance's private store. No caller-supplied
/// verifier, artifact, selection, validator or adapter is accepted.
public final class CapabilityColdStartRuntime: Sendable {
    private let core: CapabilityColdStartCloseCore
    private init(_ core: CapabilityColdStartCloseCore) { self.core = core }
    public static func open(configuration: CapabilityColdStartConfiguration,
                            execution: InstalledCapabilityExecution) async throws -> CapabilityColdStartRuntime {
        try await openOwned(configuration: configuration, installed: execution.installed, environment: .init())
    }
    static func openOwned(configuration: CapabilityColdStartConfiguration, installed: InstalledMaterial,
                          environment: CapabilityRecoveryEnvironment) async throws -> CapabilityColdStartRuntime {
        try CapabilityInstalledExecutionMode.requireCapabilityOnly(installed.identity)
        return try await openShared(configuration: configuration, installed: installed, environment: environment, presentation: nil)
    }
#if os(macOS) && MIXER_PRIVATE_F10
    static func openPrivateF10(configuration: CapabilityColdStartConfiguration, execution: InstalledCapabilityExecution,
                               presenter: F10HeadlessPresenter) async throws -> any F10InstalledColdStart {
        guard execution.installed.privateF10 else { throw coldStartError("installed_mode") }
        try CapabilityInstalledExecutionMode.requirePrivateF10(execution.installed.identity, milestones: configuration.requiredMilestones)
        return try await openShared(configuration: configuration, installed: execution.installed, environment: .init(), presentation: presenter)
    }
#endif
#if os(macOS) && MIXER_PRIVATE_FIELDLOG_EDITOR
    @_spi(PrivateFieldLogEditor)
    public static func openFieldLogEditor(configuration: CapabilityColdStartConfiguration, execution: InstalledCapabilityExecution,
                                          presenter: FieldLogEditorPresenter) async throws -> CapabilityColdStartRuntime {
        guard execution.installed.fieldLogEditorID == presenter.identity else { throw coldStartError("installed_mode") }
        try CapabilityInstalledExecutionMode.requireFieldLogEditor(execution.installed.identity, milestones: configuration.requiredMilestones)
        let owner = try await presenter.claimOwner()
        return try await openShared(configuration: configuration, installed: execution.installed, environment: .init(), presentation: owner)
    }
#endif
    private static func openShared(configuration: CapabilityColdStartConfiguration, installed: InstalledMaterial,
                                   environment: CapabilityRecoveryEnvironment,
                                   presentation: (any CapabilityColdStartPresentation)?) async throws -> CapabilityColdStartRuntime {
        var reservation: CapabilityAttemptReservation?
        var core: CapabilityColdStartCloseCore?
        var opening: CapabilityColdStartOperation?
        do {
            let checked = try configuration.checked()
            let acquired = try CapabilityAttemptReservation.acquire()
            reservation = acquired
            let created = try CapabilityColdStartCloseCore(configuration: checked, installed: installed, environment: environment,
                reservation: acquired, alternatePresentation: presentation)
            core = created
            let op = try created.control.admit(.opening); opening = op
            let core = created
            try await withTaskCancellationHandler { try await core.worker.open(op) } onCancel: { core.requestClose(.cancelled) }
            core.control.finish(op)
            guard !core.control.isClosed else { await core.waitForClose(); throw CancellationError() }
            return CapabilityColdStartRuntime(core)
        } catch {
            if let core {
                if let opening { core.control.finish(opening) }
                core.requestClose(.closed); await core.waitForClose()
            } else {
                reservation?.beginClosing()
#if os(macOS) && MIXER_PRIVATE_FIELDLOG_EDITOR
                // Without a core, no startup could have bound this claim.
                if let owner = presentation as? FieldLogEditorPresentationOwner { await owner.release() }
#endif
            }
            throw error
        }
    }
    public func beginDownload(signedManifest: Data, signedAssignment: Data) async throws {
        guard signedManifest.count <= 65_536, signedAssignment.count <= 65_536 else { throw coldStartError("size") }
        let op = try core.control.admit(.download); defer { core.control.finish(op) }
        try await withTaskCancellationHandler { try await beginOwned(signedManifest, signedAssignment, op) } onCancel: { op.cancel() }
    }
    private func beginOwned(_ manifest: Data, _ assignment: Data, _ op: CapabilityColdStartOperation) async throws {
        try op.check()
        let m = Self.snapshot(manifest), a = Self.snapshot(assignment)
        try await core.worker.begin(m, a, op)
    }
    public func downloadOffset() async throws -> UInt64 {
        let op = try core.control.admit(.download); defer { core.control.finish(op) }
        return try await withTaskCancellationHandler { try await core.worker.offset(op) } onCancel: { op.cancel() }
    }
    public func appendDownload(_ bytes: Data, atOffset offset: UInt64) async throws {
        guard bytes.count <= 1_048_576 else { throw coldStartError("size") }
        let op = try core.control.admit(.download); defer { core.control.finish(op) }
        try await withTaskCancellationHandler { try await appendOwned(bytes, offset, op) } onCancel: { op.cancel() }
    }
    private func appendOwned(_ bytes: Data, _ offset: UInt64, _ op: CapabilityColdStartOperation) async throws {
        try op.check(); let owned = Self.snapshot(bytes)
        try await core.worker.append(owned, offset, op)
    }
    public func finishDownload() async throws {
        let op = try core.control.admit(.download); defer { core.control.finish(op) }
        try await withTaskCancellationHandler { try await core.worker.finishDownload(op) } onCancel: { op.cancel() }
    }
    public func cancelDownload() async throws {
        let op = try core.control.admitCancellation(); defer { core.control.finish(op, cancellationPath: true) }
        try await withTaskCancellationHandler { try await core.worker.cancelDownload(op) } onCancel: { op.cancel() }
    }
    public func start() async throws -> CapabilityActivationSnapshot {
        let op = try core.control.admit(.start)
        do {
            try await withTaskCancellationHandler { try await core.worker.start(op) } onCancel: { core.requestClose(.cancelled) }
            core.control.finish(op); return core.control.snapshot
        } catch { core.control.finish(op); throw error }
    }
    public func reportMilestone(_ installedID: String) async throws {
        guard capabilityRecoveryIdentifier(installedID) else { throw coldStartError("milestone") }
        let op = try core.control.admit(.milestone)
        do {
            try await withTaskCancellationHandler { try await core.worker.reportMilestone(installedID, op) } onCancel: { core.requestClose(.cancelled) }
            core.control.finish(op)
        } catch { core.control.finish(op); throw error }
    }
    public func recoverySnapshot() async -> CapabilityColdStartRecoverySnapshot {
        CapabilityColdStartRecoverySnapshot(core.control.recoverySnapshot, activation: core.control.snapshot)
    }
    /// Admission and local cause stop synchronously before native cancellation.
    /// Awaiting close joins coordinator work/fds; actual native exit may remain
    /// counted indefinitely and is exposed by cleanupPending.
    public func close() async { core.requestClose(.closed); await core.waitForClose() }
    deinit { core.requestClose(.closed) }
    private static func snapshot(_ bytes: Data) -> Data {
        bytes.withUnsafeBytes { $0.isEmpty ? Data() : Data(bytes: $0.baseAddress!, count: $0.count) }
    }
}

#if os(macOS) && MIXER_PRIVATE_F10
protocol F10InstalledColdStart: Sendable {
    func beginDownload(signedManifest: Data, signedAssignment: Data) async throws
    func appendDownload(_ bytes: Data, atOffset offset: UInt64) async throws
    func finishDownload() async throws
    func start() async throws -> CapabilityActivationSnapshot
    func recoverySnapshot() async -> CapabilityColdStartRecoverySnapshot
    func close() async
}
extension CapabilityColdStartRuntime: F10InstalledColdStart {}
#endif

/// Separate from facade deinit. This is the only coordinator cleanup Task; it
/// never substitutes for or awaits the bridge's host-close/native-exit cleanup.
final class CapabilityColdStartCloseCore: @unchecked Sendable {
    let control: CapabilityColdStartControl
    let worker: CapabilityColdStartWorker
    let guestUIBinding: CapabilityGuestUIPresentationBinding?
    private let presentation: (any CapabilityColdStartPresentation)?
    private let lock = NSLock()
    private var closeStarted = false
    private var closeJob: Task<Void, Never>?
    init(configuration: CapabilityRecoveryConfiguration, installed: InstalledMaterial,
         environment: CapabilityRecoveryEnvironment, reservation: CapabilityAttemptReservation,
         guestUIBinding: CapabilityGuestUIPresentationBinding? = nil,
         alternatePresentation: (any CapabilityColdStartPresentation)? = nil) throws {
        precondition(guestUIBinding == nil || alternatePresentation == nil)
        let admission = try reservation.issueStoreAdmission()
        let control = CapabilityColdStartControl(reservation: reservation)
        self.control = control; self.guestUIBinding = guestUIBinding
        presentation = alternatePresentation ?? guestUIBinding
        worker = CapabilityColdStartWorker(configuration: configuration, installed: installed,
            environment: environment, admission: admission, control: control, presentation: presentation)
    }
    func requestClose(_ cause: CapabilityAttemptLocalStop) {
        presentation?.requestFinalClose(cause)
        control.requestClose(cause)
        lock.lock(); defer { lock.unlock() }
        guard !closeStarted else { return }
        closeStarted = true
        closeJob = Task.detached { [self] in
            if let observation = control.detachObservation(),
               let result = await observation.finish(), !result.isRetired { control.reservation.quarantine() }
            await control.waitForOrdinaryTail()
            // A bind/install loser still owns its local permit until the above
            // ordinary tail. Only now may core move the remaining pre-bind cell.
            if let presentation, await !presentation.finishForClose() { control.reservation.quarantine() }
            let recovery = await worker.closeStore()
            control.storeDidClose(recovery)
            control.reservation.beginClosing()
#if os(macOS) && MIXER_PRIVATE_FIELDLOG_EDITOR
            if let owner = presentation as? FieldLogEditorPresentationOwner, !control.reservation.isQuarantined {
                await owner.release()
            }
#endif
            finishJob()
        }
    }
    private func finishJob() { lock.lock(); closeJob = nil; lock.unlock() }
    private func jobSnapshot() -> Task<Void, Never>? { lock.lock(); defer { lock.unlock() }; return closeJob }
    func waitForClose() async {
        let job = jobSnapshot()
        await job?.value
    }
}
