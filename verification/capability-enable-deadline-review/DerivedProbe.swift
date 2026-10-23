// Review-only executable module built from exact frozen Swift runtime files,
// plus three labelled counter hooks. No package/Rust rebuild or production hook.
// Private stale-close faults run in isolated processes and are not public races.
import Foundation
import Dispatch
import MixerCapabilities

struct EnableDerivedFailure: Error { let message: String }
@main struct EnableDerivedProbe {
    @MainActor static var checks = 0
    @MainActor static func check(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
        checks += 1; guard try condition() else { throw EnableDerivedFailure(message: message) }
    }
    @MainActor static func wait(_ label: String, _ predicate: () async -> Bool) async throws {
        let cutoff = ContinuousClock.now.advanced(by: .seconds(5))
        while !(await predicate()) { guard ContinuousClock.now < cutoff else { throw EnableDerivedFailure(message: label) }; try await Task.sleep(for: .milliseconds(2)) }
    }
    static func policy() throws -> CapabilityPolicy {
        let grant = CapabilityGrant(capabilityID: CapabilitySchemas.storageID, schemaSHA256: CapabilitySchemas.storageSHA256, permissions: ["storage.appPrivate"], namespaces: ["review"])
        return try CapabilityPolicy(installed: [grant], manifest: [grant])
    }
    static func make(_ directory: URL) throws -> (NativeExitOwner, OwnedCapabilityAdapterGroup, EnableDerivedSink) {
        let sink = EnableDerivedSink()
        let group = OwnedCapabilityAdapterGroup(storage: try AppPrivateKeyValueStore(directory: directory, namespaces: ["review"]), terminal: sink, retirement: sink)
        let permit = try ConstructionPermit.acquire(), adapters = try group.core.consume(permit), configuration = ExperimentalCapabilityConfiguration()
        let host = try CapabilityHost(policy: policy(), installedAdapters: adapters)
        let native = try NativeCapabilitySession(module: EnableReviewGuest.module(), startup: "startup", configuration: configuration)
        group.core.expectsNative(); group.core.constructorReturned()
        let owner = NativeExitOwner(native: native, host: host, configuration: configuration, permit: permit, lifecycle: group.core)
        owner.start(); return (owner,group,sink)
    }
    static func reopen(_ directory: URL) async -> Bool {
        do { let reader = try AppPrivateKeyValueStore(directory: directory, namespaces: ["review"]); await reader.close(); return true }
        catch { return false }
    }
    @MainActor static func heldQueue() async throws -> EnableDerivedGate {
        let gate = EnableDerivedGate(); ExperimentalQueues.guest.async { gate.hold() }
        try await wait("guest queue held") { gate.entered }; return gate
    }
    @MainActor static func fill(_ count: Int, expectBusy: Bool) throws {
        var permits: [ConstructionPermit] = []; for _ in 0..<count { permits.append(try ConstructionPermit.acquire()) }
        if expectBusy {
            do { _ = try ConstructionPermit.acquire(); throw EnableDerivedFailure(message: "retained close failure released its permit") }
            catch let error as ExperimentalCapabilityError { try check(error.code == "construction_busy", "retained close failure pins the sixteenth permit") }
        } else { try check(permits.count == 16, "ordinary expiry releases all sixteen permits without quarantine") }
        permits.forEach { $0.release() }
    }
    @MainActor static func main() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-enable-derived-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: root) }
        let mode = CommandLine.arguments[1], directory = root.appendingPathComponent(mode)
        let (owner,group,sink) = try make(directory)
        _ = try await owner.startup()
        if mode == "queued-expiry" {
            let gate = try await heldQueue(); defer { gate.release(); owner.stop() }
            let baseline = EnableReviewHooks.state.withLock { $0.commands }
            let cutoff = DispatchTime.now().uptimeNanoseconds + 30_000_000
            let pending = Task { try await owner.enableOwned(noLaterThanUptimeNanoseconds: cutoff) }
            try await wait("exact enable command admitted") { EnableReviewHooks.state.withLock { $0.commands == baseline + 1 } }
            try await Task.sleep(for: .milliseconds(80))
            try check(DispatchTime.now().uptimeNanoseconds >= cutoff && !owner.closed, "original cutoff expires while admitted command remains queued")
            try check(EnableReviewHooks.state.withLock { $0.nativeEnables == 0 && $0.terminals == 0 && $0.cleanupSawTerminalCounts.isEmpty }, "no early native enable or cleanup while queue is held")
            gate.release()
            do { try await pending.value; throw EnableDerivedFailure(message: "expired command enabled") }
            catch let error as ExperimentalCapabilityError { try check(error.failure.kind == .deadlineExceeded && error.failure.operation == .enableEffects && error.nativeStatus == nil, "local expiry has fixed typed ordinary failure") }
            try await wait("ordinary final retirement") { sink.value.retires == 1 && owner.status.drained }
            try check(EnableReviewHooks.state.withLock { $0.nativeEnables == 0 && $0.cleanupSawTerminalCounts == [1] }, "actual C enable count zero and terminal recorded before cleanup Task enters")
            try check(sink.value.events == ["terminal","retired"] && group.core.cleanupJobCount == 1, "one ordinary cleanup and exact retirement follow first failure")
            try check(!owner.control.withLock { $0.quarantined }, "nil-status local deadline never reaches malformed-native quarantine")
            let reopened = await reopen(directory)
            try check(reopened, "real concrete storage is closed before retirement")
            try fill(16,expectBusy: false)
        } else if mode == "future-and-legacy" {
            try await owner.enableOwned(noLaterThanUptimeNanoseconds: DispatchTime.now().uptimeNanoseconds + 5_000_000_000)
            _ = try await owner.command(turn: true) { try owner.native.invoke("run",arguments: []) }
            try await wait("actual enabled guest storage ack") { owner.status.acknowledgements == 1 }
            try check(EnableReviewHooks.state.withLock { $0.nativeEnables == 1 }, "future owned cutoff calls actual C enable exactly once")
            owner.stop(); try await wait("future retirement") { sink.value.retires == 1 && owner.status.drained }
            try check(sink.value.failures.isEmpty, "future owned enable has no terminal failure")
            let reader = try AppPrivateKeyValueStore(directory: directory, namespaces: ["review"])
            let result = try await reader.get(KVGetArguments(namespace: "review",key: "enabled")); await reader.close()
            try check(result.found && result.valueBase64 == "eWVz", "future enable executes real concrete effect")
            let legacy = try await ExperimentalCapabilitySession.prepare(module: EnableReviewGuest.module(),startupExport: "startup",policy: policy(),adapters: .init()).create()
            _ = try await legacy.startup()
            do { try await legacy.enableOwnedEffects(noLaterThanUptimeNanoseconds: 0); throw EnableDerivedFailure(message: "non-owned accepted") }
            catch let error as ExperimentalCapabilityError { try check(error.code == "owned_session_required" && !legacy.status.closed, "non-owned guard rejects without stopping legacy owner") }
            try check(EnableReviewHooks.state.withLock { $0.nativeEnables == 1 }, "non-owned SPI never calls C enable")
            try await legacy.enableEffects(); try check(EnableReviewHooks.state.withLock { $0.nativeEnables == 2 }, "legacy path retains its ordinary native enable")
            legacy.close(); try await wait("legacy drain") { legacy.status.drained }
        } else if mode == "checked-failure-first" || mode == "deadline-first" {
            let gate = try await heldQueue(); defer { gate.release() }
            let baseline = EnableReviewHooks.state.withLock { $0.commands }
            let pending = Task { try await owner.enableOwned(noLaterThanUptimeNanoseconds: 0) }
            try await wait("fault-path command admitted") { EnableReviewHooks.state.withLock { $0.commands == baseline + 1 } }
            try owner.native.close() // Deliberate private stale-handle injection.
            if mode == "checked-failure-first" {
                owner.stop()
                try await wait("real close failure before queued deadline") { sink.value.failures.count == 1 }
                let first = sink.value.failures[0]
                try check(first.operation == .close && first.nativeStatus == 3 && first.code == "invalid_session", "real checked close failure wins before deadline command")
                gate.release()
                do { try await pending.value; throw EnableDerivedFailure(message: "closed command enabled") }
                catch let error as ExperimentalCapabilityError { try check(error.code == "closed", "already closed queued enable denies rather than fabricating deadline") }
                try check(owner.status.failureDetail == first && sink.value.failures == [first], "queued expiry cannot replace checked first failure")
            } else {
                gate.release()
                do { try await pending.value; throw EnableDerivedFailure(message: "expired fault command enabled") }
                catch let error as ExperimentalCapabilityError { try check(error.code == "startup_deadline", "deadline branch wins before later real close failure") }
                try await wait("real later native close completes") { owner.control.withLock { $0.closeFinished } }
                try check(sink.value.failures.count == 1 && sink.value.failures[0].kind == .deadlineExceeded && owner.status.failureDetail == sink.value.failures[0], "later checked close failure cannot replace first local deadline")
            }
            try await wait("fault concrete close completes") { await reopen(directory) }
            let observations = EnableReviewHooks.state.withLock { $0 }
            try check(observations.nativeEnables == 0 && observations.cleanupSawTerminalCounts.count == 1, "fault race retains zero C enable and one cleanup Task")
            if mode == "deadline-first" {
                try check(observations.cleanupSawTerminalCounts == [1], "deadline winner records terminal before cleanup enters")
            }
            try check(!owner.status.drained && sink.value.retires == 0 && group.core.cleanupJobCount == 1, "failed native close never fabricates final retirement")
            try check(!owner.control.withLock { $0.quarantined }, "ordinary checked3/local expiry are not quarantine classifications")
            try fill(15,expectBusy: true)
        } else { throw EnableDerivedFailure(message: "unknown isolated mode") }
        print("derived owned-enable review \(mode) passed \(checks) checks")
    }
}
