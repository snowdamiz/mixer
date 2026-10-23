import Foundation

actor CandidateGate {
    private var released = false
    private var waiting = 0
    private var pending: [CheckedContinuation<Void, Never>] = []
    func hold() async {
        guard !released else { return }
        waiting += 1
        await withCheckedContinuation { pending.append($0) }
    }
    func count() -> Int { waiting }
    func release() { released = true; let p = pending; pending.removeAll(); for c in p { c.resume() } }
}
enum ReviewCandidateHooks {
    static let watchdog = CandidateGate()
    static let beforeInvocationReturn = CandidateGate()
    static let workerStart = CandidateGate()
    static func beforeWorkerDeadlineCheck() async {
        if CommandLine.arguments[1] == "late-admission" { await workerStart.hold() }
    }
}
final class CandidateRecord: @unchecked Sendable {
    private let lock = NSLock()
    private var payloads: [Data] = []
    private var time: ContinuousClock.Instant?
    private var exits = 0
    private var invocations = 0
    func invoked() { lock.lock(); invocations += 1; lock.unlock() }
    func invocationCount() -> Int { lock.lock(); defer { lock.unlock() }; return invocations }
    func deliver(_ bytes: Data) { lock.lock(); payloads.append(bytes); time = ContinuousClock.now; lock.unlock() }
    func exit() { lock.lock(); exits += 1; lock.unlock() }
    func state() -> ([Data], ContinuousClock.Instant?, Int) { lock.lock(); defer { lock.unlock() }; return (payloads, time, exits) }
}
enum CandidateFailure: Error { case failed(String) }
func check(_ okay: @autoclosure () -> Bool, _ label: String) throws { if !okay() { throw CandidateFailure.failed(label) } }
@MainActor
func eventually(_ check: @MainActor () async -> Bool) async throws {
    let bound = ContinuousClock.now.advanced(by: .seconds(3))
    while !(await check()) { if ContinuousClock.now >= bound { throw CandidateFailure.failed("synchronization timeout") }; await Task.yield() }
}

@main
struct CandidateProbe {
    static func main() async throws {
        let timely = CommandLine.arguments[1] == "timely"
        let admission = CommandLine.arguments[1] == "late-admission"
        let timeout: UInt32 = timely ? 500 : 25
        let directory = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
        let grant = CapabilityGrant(capabilityID: CapabilitySchemas.storageID, schemaSHA256: CapabilitySchemas.storageSHA256, permissions: ["storage.appPrivate"], namespaces: ["deadline"])
        let policy = try CapabilityPolicy(installed: [grant], manifest: [grant])
        let store = try AppPrivateKeyValueStore(directory: directory, namespaces: ["deadline"])
        let beforeComplete = CandidateGate()
        let record = CandidateRecord()
        let adapter = InstalledCapabilityAdapters(storage: store, hooks: InstalledCapabilityExecutionHooks(beforeInvocation: { record.invoked() }, afterInvocation: { await beforeComplete.hold() }))
        let host = try CapabilityHost(policy: policy, maximumRequests: 1, timeoutMilliseconds: timeout, installedAdapters: adapter)
        let id = try await host.issueRequestID()
        let operation: CapabilityOperation = admission
            ? .put(KVPutArguments(namespace: "deadline", key: "admission", valueBase64: "YQ=="))
            : .get(KVGetArguments(namespace: "deadline", key: "missing"))
        let call = CapabilityCall(identity: id, operation: operation)
        let beforeStorage = try await store.get(KVGetArguments(namespace: "deadline", key: "admission"))
        try check(!beforeStorage.found, "admission fixture must start absent")
        let started = ContinuousClock.now
        try await host.submitObserved(CapabilityCodec.encodeCall(call), deliver: { record.deliver($0) }, didExit: { record.exit() })
        try await eventually {
            let returned = admission ? await ReviewCandidateHooks.workerStart.count() : await beforeComplete.count()
            let watchdog = await ReviewCandidateHooks.watchdog.count()
            return returned == 1 && watchdog == 1
        }
        if !timely { try await ContinuousClock().sleep(for: .milliseconds(100)) }
        if admission { await ReviewCandidateHooks.workerStart.release() }
        else { await beforeComplete.release() }
        try await eventually { await ReviewCandidateHooks.beforeInvocationReturn.count() == 1 && record.state().0.count == 1 }
        let first = record.state()
        let decoded = try CapabilityCodec.decodeCompletion(first.0[0], expected: call)
        if timely {
            try check(decoded.outcome == .success(.get(KVGetResponse(found: false, valueBase64: ""))), "timely success changed")
            try check(started.duration(to: first.1!) < .milliseconds(Int64(timeout)), "timely test missed its budget")
        } else {
            try check(decoded.outcome == .failure(.deadlineExceeded), "late result was not converted to deadlineExceeded")
            try check(started.duration(to: first.1!) >= .milliseconds(Int64(timeout)), "late test did not exceed budget")
        }
        // complete() has already returned, while the real installed lease still
        // awaits invocationReturned(). This separate test-only gate proves the
        // candidate did not release capacity along with terminal delivery.
        try check(first.2 == 0, "native exit was reported before invocation return")
        var retained = false
        do { _ = try await host.issueRequestID() } catch { retained = true }
        try check(retained, "terminal delivery released the installed lease")
        if timely { try await ContinuousClock().sleep(until: first.1!.advanced(by: .milliseconds(Int64(timeout) + 100))) }
        // Invoke the existing deadline handler after the actual monotonic cutoff,
        // through a same-file test-only forwarding method. It must not replace
        // either the prior success or the prior deadline failure.
        await host.reviewDeliverExpiredWatchdog(id)
        try check(record.state().0.count == 1 && record.state().2 == 0, "later watchdog changed terminal/exit")
        if admission {
            try check(record.invocationCount() == 0, "late admission invoked the adapter")
            let afterStorage = try await store.get(KVGetArguments(namespace: "deadline", key: "admission"))
            try check(afterStorage == beforeStorage, "late admission mutated storage")
        } else { try check(record.invocationCount() == 1, "normal invocation missing") }
        await ReviewCandidateHooks.beforeInvocationReturn.release()
        try await eventually { record.state().2 == 1 }
        var next: CapabilityRequestID?
        try await eventually { do { next = try await host.issueRequestID(); return true } catch { return false } }
        try check(next?.generation == id.generation + 1, "joined exit did not release slot")
        await ReviewCandidateHooks.watchdog.release()
        await host.close(); await store.close()
        try check(record.state().0.count == 1 && record.state().2 == 1, "duplicate terminal or exit")
        let elapsed = started.duration(to: first.1!).components
        let ms = Double(elapsed.seconds) * 1000 + Double(elapsed.attoseconds) / 1e15
        print("mode=derived-fix-\(admission ? "late-admission" : timely ? "timely-success" : "late-completion"); timeout_ms=\(timeout); first_delivery_ms=\(ms); outcome=\(decoded.outcome); later_expired_watchdog_preserved_first=true; terminal_delivered_before_native_exit=true; slot_retained_after_complete_until_invocationReturned=true; callbacks=1; observed_exit=1; adapter_invocations=\(record.invocationCount()); storage_unchanged_on_late_admission=\(admission); next_generation=\(next!.generation)")
    }
}
