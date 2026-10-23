import Foundation
import Dispatch
import MixerRuntime
import MixerUpdates

/// A cancellation bridge for synchronous native work. Its lock is never held
/// during VM invocation. Cancel-before-publish closes the subsequently created
/// instance; completed work cannot be cancelled by a late timer.
final class StartupWork: @unchecked Sendable {
    enum Stop: String { case cancelled, deadline }
    private let lock = NSLock()
    private var session: VMSession?
    private var stop: Stop?
    private var finished = false

    func cancel(_ reason: Stop) {
        lock.lock()
        guard !finished else { lock.unlock(); return }
        if stop == nil { stop = reason }
        let current = session
        lock.unlock()
        try? current?.close()
    }

    private func publish(_ value: VMSession) throws {
        lock.lock(); let reason = stop
        if reason == nil { session = value }
        lock.unlock()
        if let reason { try? value.close(); throw Self.error(reason) }
    }

    private func complete() throws {
        lock.lock(); let reason = stop; finished = true; session = nil; lock.unlock()
        if let reason { throw Self.error(reason) }
    }

    private static func error(_ stop: Stop) -> UpdateError {
        UpdateError("activation.\(stop.rawValue)", "Native startup was \(stop.rawValue)")
    }

    func execute(payload: Data, policy: InstalledExecution, artifact: VerifiedArtifact,
                 startedAt: UInt64) throws -> (VMSession, VMInvocation) {
        let duration = try policy.startupMilliseconds(artifact) * 1_000_000
        let now = DispatchTime.now().uptimeNanoseconds
        guard now >= startedAt, now - startedAt < duration else {
            cancel(.deadline); throw Self.error(.deadline)
        }
        let deadline = DispatchTime.now() + .nanoseconds(Int(duration - (now - startedAt)))
        let timer = DispatchWorkItem { [weak self] in self?.cancel(.deadline) }
        DispatchQueue.global(qos: .userInitiated).asyncAfter(deadline: deadline, execute: timer)
        defer { timer.cancel() }
        let instance = try VMSession(module: payload, profile: policy.profile, limits: policy.boundedLimits(artifact))
        do {
            try publish(instance)
            let result = try instance.invoke(policy.startupExport)
            // A delayed watchdog cannot allow late results to become active.
            let end = DispatchTime.now().uptimeNanoseconds
            if end < startedAt || end - startedAt >= duration { cancel(.deadline) }
            try complete()
            return (instance, result)
        } catch {
            try? instance.close()
            // Prefer explicit host cancellation/deadline over the resulting VM
            // cancellation error; these are not deterministic guest traps.
            try complete()
            throw error
        }
    }
}
