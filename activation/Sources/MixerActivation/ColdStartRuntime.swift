import Foundation
import Dispatch
import MixerRuntime
import MixerUpdates

public struct ActivationSnapshot: Sendable, Equatable {
    public enum Phase: String, Sendable { case idle, starting, guest, nativeFallback, closed }
    public let phase: Phase
    public let source: ColdStartSelection.Source?
    public let artifactSHA256: String?
    public let startupResult: VMInvocation?
    /// At most two startup failures (candidate and one retained healthy fallback),
    /// followed by at most one runtime failure. Codes never include file contents.
    public let failureCodes: [String]
}

/// Composes the durable verifier with the installed owned VM. One instance is one
/// app-process feature session: start exactly once, then close at lifecycle end.
/// Native fallback is an explicit result; the embedding launches its real compiled
/// feature implementation. This class never fabricates UI or native success.
public actor ColdStartRuntime {
    private let updater: ColdStartUpdater
    private let policy: InstalledExecution
    private var phase: ActivationSnapshot.Phase = .idle
    private var selection: ColdStartSelection?
    private var session: VMSession?
    private var startupWork: StartupWork?
    private var result: VMInvocation?
    private var failures: [String] = []
    private var operationBusy = false
    private var earnedHealth = false

    public static func open(configuration: ColdStartConfiguration, verifier: ReleaseVerifier,
                            execution: InstalledExecution) throws -> ColdStartRuntime {
        try execution.check(verifier.host)
        let updater = try ColdStartUpdater.open(configuration: configuration, verifier: verifier,
            executableValidator: { payload, artifact in try execution.validate(payload, artifact: artifact) })
        return ColdStartRuntime(updater: updater, policy: execution)
    }

    private init(updater: ColdStartUpdater, policy: InstalledExecution) {
        self.updater = updater; self.policy = policy
    }

    deinit {
        startupWork?.cancel(.cancelled)
        try? session?.close()
        // DurableDirectory releases its file descriptor/lock when the updater's
        // last reference dies. Explicit close is preferred at app lifecycle end.
    }

    public func snapshot() -> ActivationSnapshot {
        ActivationSnapshot(phase: phase, source: selection?.source,
            artifactSHA256: selection?.artifactSHA256, startupResult: result, failureCodes: failures)
    }

    public func recoverySnapshot() async -> UpdateRecoverySnapshot { await updater.snapshot() }

    /// Download methods are available before startup. The host supplies network
    /// chunks; this slice has no HTTP transport and never stages unsigned bytes.
    public func beginDownload(signedManifest: Data, signedAssignment: Data, now: UInt64) async throws {
        try beginIdleOperation(); defer { operationBusy = false }
        try await updater.beginDownload(signedManifest: signedManifest, signedAssignment: signedAssignment, now: now)
    }
    public func downloadOffset() async throws -> UInt64 {
        try beginIdleOperation(); defer { operationBusy = false }
        return try await updater.downloadOffset()
    }
    public func appendDownload(_ bytes: Data, atOffset offset: UInt64, now: UInt64) async throws {
        try beginIdleOperation(); defer { operationBusy = false }
        try await updater.appendDownload(bytes, atOffset: offset, now: now)
    }
    public func finishDownload(now: UInt64) async throws {
        try beginIdleOperation(); defer { operationBusy = false }
        try await updater.finishDownload(now: now)
    }
    public func cancelDownload() async throws {
        try beginIdleOperation(); defer { operationBusy = false }
        try await updater.cancelDownload()
    }

    /// Executes the native-configured startup export with no arguments. Validation,
    /// construction and startup are charged to the signed monotonic time budget;
    /// decoding/construction are bounded but cannot be forcibly preempted. A late
    /// result is discarded. At most one already-healthy guest is attempted after a
    /// failed candidate, then the host receives nativeFallback.
    public func start(now: UInt64) async throws -> ActivationSnapshot {
        try beginIdleOperation(); operationBusy = false
        phase = .starting
        let began = DispatchTime.now().uptimeNanoseconds
        do {
            let selected = try await updater.selectAtColdStart(now: now)
            try requireOpen()
            return try await activate(selected, startedAt: began)
        } catch {
            try requireOpen()
            record(error); phase = .nativeFallback; selection = nil; result = nil
            return snapshot()
        }
    }

    private func activate(_ initial: ColdStartSelection, startedAt: UInt64) async throws -> ActivationSnapshot {
        var selected = initial
        var began = startedAt
        for attempt in 0..<2 {
            try requireOpen()
            selection = selected
            guard selected.source != .nativeFallback else { phase = .nativeFallback; return snapshot() }
            guard let payload = selected.payload, let artifact = selected.verifiedArtifact,
                  artifact.artifactSHA256 == selected.artifactSHA256,
                  artifact.payloadSHA256 == selected.payloadSHA256 else {
                throw UpdateError("activation.binding", "Selection lacks verified payload metadata")
            }
            let work = StartupWork(); startupWork = work
            do {
                let policy = self.policy
                let start = began
                let (created, output) = try await withTaskCancellationHandler {
                    try await Task.detached(priority: .userInitiated) {
                        try work.execute(payload: payload, policy: policy, artifact: artifact, startedAt: start)
                    }.value
                } onCancel: { work.cancel(.cancelled) }
                startupWork = nil
                guard phase != .closed else { try? created.close(); throw UpdateError("activation.closed", "Feature session is closed") }
                guard !Task.isCancelled else { try? created.close(); throw UpdateError("activation.cancelled", "Startup caller cancelled") }
                session = created; result = output; phase = .guest
                return snapshot()
            } catch {
                startupWork = nil
                try requireOpen()
                record(error)
                if selected.source == .provisional, let launch = selected.launchID {
                    let fallbackBegan = DispatchTime.now().uptimeNanoseconds
                    let fallback = try await updater.reportFailure(launchID: launch, reason: classification(error))
                    try requireOpen()
                    if attempt == 0, !Task.isCancelled, fallback.source == .healthy {
                        selected = fallback; began = fallbackBegan
                        continue
                    }
                }
                phase = .nativeFallback; selection = nil; result = nil
                return snapshot()
            }
        }
        phase = .nativeFallback; selection = nil; result = nil
        return snapshot()
    }

    /// Retains guest memory/globals between calls. One call is admitted at a time;
    /// the actor remains responsive to close while native work runs off the UI actor.
    /// A terminal VM error ends this guest session. The app must enter its compiled
    /// fallback and reconcile external effects; this slice has no effect imports.
    public func invoke(_ export: String, arguments: [VMValue] = []) async throws -> VMInvocation {
        guard phase == .guest, let current = session else { throw UpdateError("activation.inactive", "No active guest") }
        guard !operationBusy else { throw UpdateError("activation.busy", "An operation is already running") }
        operationBusy = true
        defer { operationBusy = false }
        do {
            let output = try await withTaskCancellationHandler {
                try await Task.detached(priority: .userInitiated) { try current.invoke(export, arguments: arguments) }.value
            } onCancel: { try? current.cancel() }
            try requireOpen()
            try Task.checkCancellation()
            return output
        } catch {
            guard phase != .closed else { throw error }
            // Native argument count/type errors can be terminal at the interpreter
            // boundary; conservatively retire on any error rather than reuse it.
            try? current.close(); session = nil; record(error); phase = .nativeFallback; result = nil
            if let selected = selection, selected.source == .provisional, !earnedHealth, let launch = selected.launchID {
                _ = try await updater.reportFailure(launchID: launch, reason: classification(error))
            }
            selection = nil
            throw error
        }
    }

    /// Only installed host code reports rendered/restored milestones. A successful
    /// guest export is not health by itself. The durable store also enforces its
    /// configured observation interval with a monotonic clock.
    public func markHealthy(now: UInt64, completedMilestones: Set<String>) async throws {
        guard phase == .guest, !operationBusy, !earnedHealth,
              selection?.source == .provisional, let launch = selection?.launchID else {
            throw UpdateError("activation.health", "No provisional successful startup to mark healthy")
        }
        operationBusy = true; defer { operationBusy = false }
        try await updater.markHealthy(launchID: launch, now: now, completedMilestones: completedMilestones)
        earnedHealth = true
    }

    public func close() async {
        guard phase != .closed else { return }
        phase = .closed; startupWork?.cancel(.cancelled); startupWork = nil
        try? session?.close(); session = nil; selection = nil; result = nil
        await updater.close()
    }

    private func beginIdleOperation() throws {
        guard phase == .idle, !operationBusy else { throw UpdateError("activation.state", "Operation requires an idle cold-start session") }
        operationBusy = true
    }
    private func requireOpen() throws {
        guard phase != .closed else { throw UpdateError("activation.closed", "Feature session is closed") }
    }
    private func record(_ error: any Error) {
        guard failures.count < 3 else { return }
        if let vm = error as? VMFailure { failures.append(vm.code) }
        else if let update = error as? UpdateError { failures.append(update.code) }
        else { failures.append("activation.internal") }
    }
    private func classification(_ error: any Error) -> StartupFailure {
        let traps: Set<String> = ["unreachable", "fuel_exhausted", "memory_out_of_bounds",
            "table_out_of_bounds", "indirect_call_null", "indirect_call_type_mismatch",
            "call_depth_exceeded", "operand_stack_exceeded", "integer_divide_by_zero",
            "integer_overflow", "invalid_conversion_to_integer", "host_call_limit", "host_abort"]
        if let vm = error as? VMFailure, vm.status == 2, traps.contains(vm.code) { return .deterministicTrap }
        return .unknownInterruption
    }
}
