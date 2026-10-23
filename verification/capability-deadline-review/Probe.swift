import Foundation

actor ReviewGate {
    private var open = false
    private var waiting = 0
    private var continuations: [CheckedContinuation<Void, Never>] = []
    func hold() async {
        guard !open else { return }
        waiting += 1
        await withCheckedContinuation { continuations.append($0) }
    }
    func waiters() -> Int { waiting }
    func release() {
        open = true
        let pending = continuations
        continuations.removeAll()
        for continuation in pending { continuation.resume() }
    }
}

enum ReviewHooks {
    static let watchdog = ReviewGate()
    // This is the sole test-only call inserted into the derived Host copy.
    // It isolates a scheduler-delayed watchdog and supplies no external time.
    static func beforeWatchdogSleep() async { await watchdog.hold() }
}

final class ReviewRecord: @unchecked Sendable {
    private let lock = NSLock()
    private var payloads: [Data] = []
    private var times: [ContinuousClock.Instant] = []
    private var exits = 0
    func delivered(_ data: Data) {
        lock.lock(); defer { lock.unlock() }
        payloads.append(data)
        times.append(ContinuousClock.now)
    }
    func exited() { lock.lock(); exits += 1; lock.unlock() }
    func state() -> (payloads: [Data], times: [ContinuousClock.Instant], exits: Int) {
        lock.lock(); defer { lock.unlock() }
        return (payloads, times, exits)
    }
}

func require(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    if !condition() { throw ReviewFailure.failed(message) }
}
enum ReviewFailure: Error { case failed(String) }

@MainActor
func awaitCondition(_ predicate: @MainActor () async -> Bool) async throws {
    let bound = ContinuousClock.now.advanced(by: .seconds(3))
    while !(await predicate()) {
        if ContinuousClock.now >= bound { throw ReviewFailure.failed("bounded synchronization timed out") }
        await Task.yield()
    }
}

@main
struct DeadlineProbe {
    static func main() async throws {
        let delayed = CommandLine.arguments[1] == "delayed-watchdog"
        let directory = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
        let grant = CapabilityGrant(capabilityID: CapabilitySchemas.storageID,
                                    schemaSHA256: CapabilitySchemas.storageSHA256,
                                    permissions: ["storage.appPrivate"], namespaces: ["deadline"])
        let policy = try CapabilityPolicy(installed: [grant], manifest: [grant])
        let store = try AppPrivateKeyValueStore(directory: directory, namespaces: ["deadline"])
        let afterNative = ReviewGate()
        let hooks = InstalledCapabilityExecutionHooks(beforeInvocation: nil, afterInvocation: { await afterNative.hold() })
        let adapters = InstalledCapabilityAdapters(storage: store, hooks: hooks)
        let host = try CapabilityHost(policy: policy, maximumRequests: 1,
                                      timeoutMilliseconds: 25, installedAdapters: adapters)
        let id = try await host.issueRequestID()
        let call = CapabilityCall(identity: id, operation: .get(KVGetArguments(namespace: "deadline", key: "absent")))
        let record = ReviewRecord()
        let acceptedBefore = ContinuousClock.now
        try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: { record.delivered($0) }, didExit: { record.exited() })
        try await awaitCondition { await afterNative.waiters() == 1 }
        if delayed { try await awaitCondition { await ReviewHooks.watchdog.waiters() == 1 } }
        // Storage has returned, but the dispatch task is deliberately held in
        // the existing installed-adapter afterInvocation seam. The independent
        // exit observer must await invocation return, regardless of terminal.
        try await ContinuousClock().sleep(until: acceptedBefore.advanced(by: .milliseconds(100)))
        try require(record.state().exits == 0, "exit observer ran before dispatch returned")
        var quotaBlocked = false
        do { _ = try await host.issueRequestID() } catch { quotaBlocked = true }
        try require(quotaBlocked, "installed slot reused while invocation still held")
        if delayed {
            try require(record.state().payloads.isEmpty, "watchdog escaped test gate")
        } else {
            try await awaitCondition { !record.state().payloads.isEmpty }
            let beforeReturn = try CapabilityCodec.decodeCompletion(record.state().payloads[0], expected: call)
            try require(beforeReturn.outcome == .failure(.deadlineExceeded), "normal watchdog did not install timeout")
        }
        await afterNative.release()
        try await awaitCondition { record.state().payloads.count == 1 && record.state().exits == 1 }
        let result = record.state()
        let completion = try CapabilityCodec.decodeCompletion(result.payloads[0], expected: call)
        let elapsed = acceptedBefore.duration(to: result.times[0])
        try require(elapsed >= .milliseconds(25), "test did not cross configured timeout")
        if delayed {
            try require(completion.outcome == .success(.get(KVGetResponse(found: false, valueBase64: ""))), "delayed watchdog did not reproduce the late-success path")
        } else {
            try require(completion.outcome == .failure(.deadlineExceeded), "earlier terminal was replaced by late success")
        }
        var replacement: CapabilityRequestID?
        try await awaitCondition {
            do { replacement = try await host.issueRequestID(); return true } catch { return false }
        }
        try require(replacement?.generation == id.generation + 1, "slot not reusable after joined exit")
        await ReviewHooks.watchdog.release()
        await host.close()
        await store.close()
        try require(record.state().payloads.count == 1 && record.state().exits == 1, "duplicate completion/exit")
        let components = elapsed.components
        let milliseconds = Double(components.seconds) * 1000 + Double(components.attoseconds) / 1e15
        print("mode=\(delayed ? "captured-host-with-watchdog-gate" : "original-host-control"); configured_timeout_ms=25; delivery_elapsed_ms=\(milliseconds); outcome=\(completion.outcome); callbacks=1; observed_exit=1; quota_blocked_until_dispatch_return=true; next_generation=\(replacement!.generation)")
    }
}
