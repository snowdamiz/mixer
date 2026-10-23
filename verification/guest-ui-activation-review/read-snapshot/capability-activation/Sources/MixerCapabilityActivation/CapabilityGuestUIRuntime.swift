#if canImport(SwiftUI) && canImport(MixerApple)
import Foundation
import MixerApple

/// Signed guest UI owner. Its private presentation binding is the only route
/// for native events and visible-screen observations. No executable, document,
/// callback, adapter or milestone injection is exposed.
public final class CapabilityGuestUIRuntime: Sendable {
    private let core: CapabilityColdStartCloseCore
    private init(_ core: CapabilityColdStartCloseCore) { self.core = core }
    public static func open(configuration: CapabilityColdStartConfiguration,
                            execution: InstalledCapabilityExecution) async throws -> CapabilityGuestUIRuntime {
        try await openOwned(configuration: configuration, installed: execution.installed, environment: .init())
    }
    static func openOwned(configuration: CapabilityColdStartConfiguration, installed: InstalledMaterial,
                          environment: CapabilityRecoveryEnvironment) async throws -> CapabilityGuestUIRuntime {
        try CapabilityInstalledExecutionMode.requireGuestUI(installed.identity, milestones: configuration.requiredMilestones)
        let checked = try configuration.checked()
        let reservation = try CapabilityAttemptReservation.acquire() // Before actor/I/O/captured owner allocation.
        let core: CapabilityColdStartCloseCore
        do {
            let binding = await CapabilityGuestUIPresentationBinding()
            try Task.checkCancellation()
            core = try CapabilityColdStartCloseCore(configuration: checked, installed: installed,
                environment: environment, reservation: reservation, guestUIBinding: binding)
        }
        catch { reservation.beginClosing(); throw error }
        let op = try core.control.admit(.opening)
        do {
            try await withTaskCancellationHandler { try await core.worker.open(op) } onCancel: { core.requestClose(.cancelled) }
            core.control.finish(op)
            guard !core.control.isClosed else { await core.waitForClose(); throw CancellationError() }
            return CapabilityGuestUIRuntime(core)
        } catch {
            core.control.finish(op); core.requestClose(.closed); await core.waitForClose(); throw error
        }
    }
    @MainActor public var presentation: GuestUIPresentation {
        // This private facade can only be constructed with its UI binding.
        core.guestUIBinding!.presentation
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
    public func start() async throws -> CapabilityGuestUIActivationSnapshot {
        let op = try core.control.admit(.start)
        do {
            try await withTaskCancellationHandler { try await core.worker.start(op) } onCancel: { core.requestClose(.cancelled) }
            core.control.finish(op); return core.control.guestUISnapshot
        } catch { core.control.finish(op); throw error }
    }
    public func recoverySnapshot() async -> CapabilityGuestUIRecoverySnapshot {
        CapabilityGuestUIRecoverySnapshot(core.control.recoverySnapshot, activation: core.control.guestUISnapshot)
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

#endif
