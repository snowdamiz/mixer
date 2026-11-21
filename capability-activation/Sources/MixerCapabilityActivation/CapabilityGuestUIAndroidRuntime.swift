#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
import Foundation
@_spi(GuestUIV1) import MixerGuest

extension CapabilityGuestUIAndroidBinding: CapabilityColdStartPresentation {
    func bindForStartup(_ exchange: GuestUIExchangeV1) async throws -> any CapabilityObservedPresentation {
        try await bindHost(exchange)
    }

    func finishForClose() async -> Bool {
        if case .finished = await finishFinalClose(using: nil) { return true }
        return false
    }
}

/// Restricted companion to the installed signed owner. The embedding must
/// install its native presentation transport before opening a store.
@_spi(AndroidGuestUIV1)
public final class CapabilityGuestUIAndroidRuntime: Sendable {
    private let core: CapabilityColdStartCloseCore
    private let binding: CapabilityGuestUIAndroidBinding
    private init(core: CapabilityColdStartCloseCore, binding: CapabilityGuestUIAndroidBinding) {
        self.core = core
        self.binding = binding
    }

    public static func open(configuration: CapabilityColdStartConfiguration,
                            execution: InstalledCapabilityExecution) async throws -> CapabilityGuestUIAndroidRuntime {
        let installed = execution.installed
        guard installed.identity.installedRuntime.scope.platform == "android" else {
            throw coldStartError("android_platform")
        }
        try CapabilityInstalledExecutionMode.requireGuestUI(installed.identity, milestones: configuration.requiredMilestones)
        let checked = try configuration.checked()
        let reservation = try CapabilityAttemptReservation.acquire()
        var transferred = false
        var preparation: CapabilityAndroidHostPreparedPresentation?
        var core: CapabilityColdStartCloseCore?
        do {
            let prepared = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation: reservation)
            preparation = prepared
            let created = try CapabilityColdStartCloseCore(configuration: checked, installed: installed,
                environment: .init(), reservation: reservation, alternatePresentation: prepared.binding)
            core = created
            try prepared.transferToBinding()
            transferred = true
            try await withTaskCancellationHandler {
                let op = try created.control.admit(.opening)
                defer { created.control.finish(op) }
                try await created.worker.open(op)
            } onCancel: {
                created.requestClose(.cancelled)
            }
            guard !created.control.isClosed else { throw CancellationError() }
            return .init(core: created, binding: prepared.binding)
        } catch {
            if !transferred, let preparation { _ = await preparation.cleanupAfterFailure() }
            if let core {
                core.requestClose(.closed)
                await core.waitForClose()
            } else {
                reservation.beginClosing()
            }
            throw error
        }
    }

    public var facade: UInt64 { binding.facade }

    public func stage(manifest: Data, assignment: Data, bytes: Data, finish: Bool = true) async throws {
        guard manifest.count <= 65_536, assignment.count <= 65_536, !bytes.isEmpty, bytes.count <= 1_048_576 else {
            throw coldStartError("size")
        }
        let owner = core
        let op = try owner.control.admit(.download)
        defer { owner.control.finish(op) }
        try await withTaskCancellationHandler {
            try await owner.worker.begin(Self.copy(manifest), Self.copy(assignment), op)
            try await owner.worker.append(Self.copy(bytes), 0, op)
            if finish { try await owner.worker.finishDownload(op) }
        } onCancel: { op.cancel() }
    }

    public func start() async throws -> CapabilityGuestUIActivationSnapshot {
        let op = try core.control.admit(.start)
        defer { core.control.finish(op) }
        return try await withTaskCancellationHandler {
            try await core.worker.start(op)
            return core.control.guestUISnapshot
        } onCancel: { self.core.requestClose(.cancelled) }
    }

    public func downloadOffset() async throws -> UInt64 {
        let op = try core.control.admit(.download)
        defer { core.control.finish(op) }
        return try await withTaskCancellationHandler {
            try await core.worker.offset(op)
        } onCancel: { op.cancel() }
    }

    public func recoverySnapshot() -> CapabilityGuestUIRecoverySnapshot {
        .init(core.control.recoverySnapshot, activation: core.control.guestUISnapshot)
    }

    public func close() async -> Bool {
        core.requestClose(.closed)
        await core.waitForClose()
        guard case .finished = binding.finalStatus else { return false }
        // The coordinator joins its presentation and store. The concrete VM
        // retirement may finish separately after its consuming bridge exit.
        let clock = ContinuousClock()
        let deadline = clock.now + .seconds(5)
        while !core.control.ownerRetired {
            guard clock.now < deadline else { return false }
            do { try await Task.sleep(for: .milliseconds(10)) } catch { return false }
        }
        return true
    }

    deinit { core.requestClose(.closed) }

    private static func copy(_ bytes: Data) -> Data {
        bytes.withUnsafeBytes { buffer in
            guard let base = buffer.baseAddress, !buffer.isEmpty else { return Data() }
            return Data(bytes: base, count: buffer.count)
        }
    }
}
#endif
