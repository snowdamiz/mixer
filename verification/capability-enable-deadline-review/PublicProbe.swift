import Foundation
import Dispatch
import MixerCapabilities
@_spi(CapabilityLifecycle) import MixerExperimentalCapabilityRuntime

final class EnablePublicSink: @unchecked Sendable, CapabilityBridgeTerminalObserver, CapabilityBridgeRetirementObserver {
    private let lock = NSLock()
    private var failures: [ExperimentalCapabilityFailure] = []
    private var retirements = 0
    private var events: [String] = []
    func recordTerminalFailure(_ failure: ExperimentalCapabilityFailure) { lock.lock(); failures.append(failure); events.append("terminal"); lock.unlock() }
    func recordRetired() { lock.lock(); retirements += 1; events.append("retired"); lock.unlock() }
    var value: ([ExperimentalCapabilityFailure], Int, [String]) { lock.lock(); defer { lock.unlock() }; return (failures,retirements,events) }
}
struct EnablePublicFailure: Error { let message: String }
@main struct EnablePublicProbe {
    @MainActor static var checks = 0
    @MainActor static func check(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
        checks += 1; guard try condition() else { throw EnablePublicFailure(message: message) }
    }
    @MainActor static func wait(_ label: String, _ predicate: () -> Bool) async throws {
        let cutoff = ContinuousClock.now.advanced(by: .seconds(5))
        while !predicate() { guard ContinuousClock.now < cutoff else { throw EnablePublicFailure(message: label) }; try await Task.sleep(for: .milliseconds(2)) }
    }
    static func policy() throws -> CapabilityPolicy {
        let grant = CapabilityGrant(capabilityID: CapabilitySchemas.storageID, schemaSHA256: CapabilitySchemas.storageSHA256, permissions: ["storage.appPrivate"], namespaces: ["review"])
        return try CapabilityPolicy(installed: [grant], manifest: [grant])
    }
    static func group(_ directory: URL, _ sink: EnablePublicSink) throws -> OwnedCapabilityAdapterGroup {
        OwnedCapabilityAdapterGroup(storage: try AppPrivateKeyValueStore(directory: directory, namespaces: ["review"]), terminal: sink, retirement: sink)
    }
    @MainActor static func main() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-enable-public-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: root) }
        do {
            let sink = EnablePublicSink(), directory = root.appendingPathComponent("future"), group = try group(directory,sink)
            let session = try await ExperimentalCapabilitySession.prepareOwned(module: EnableReviewGuest.module(), startupExport: "startup", policy: policy(), adapterGroup: group).create()
            _ = try await session.startup()
            try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: DispatchTime.now().uptimeNanoseconds + 5_000_000_000)
            _ = try await session.invoke("run"); try await wait("real guest storage ack") { session.status.acknowledgements == 1 }
            try check(!session.status.closed && sink.value.0.isEmpty && sink.value.1 == 0, "future cutoff enables real guest effect without terminal signal")
            session.close(); try await wait("future retirement") { sink.value.1 == 1 }
            let reader = try AppPrivateKeyValueStore(directory: directory, namespaces: ["review"])
            let result = try await reader.get(KVGetArguments(namespace: "review", key: "enabled")); await reader.close()
            try check(result.found && result.valueBase64 == "eWVz", "actual enabled native guest persisted exact bytes")
            try check(session.status.drained && session.status.failure == nil, "future success closes and retires normally")
        }
        do {
            let sink = EnablePublicSink(), directory = root.appendingPathComponent("zero"), group = try group(directory,sink)
            let session = try await ExperimentalCapabilitySession.prepareOwned(module: EnableReviewGuest.module(), startupExport: "startup", policy: policy(), adapterGroup: group).create()
            _ = try await session.startup()
            do { try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: 0); throw EnablePublicFailure(message: "expired cutoff accepted") }
            catch let error as ExperimentalCapabilityError {
                try check(error.code == "startup_deadline" && error.failure.kind == .deadlineExceeded && error.failure.operation == .enableEffects && error.nativeStatus == nil, "fixed local deadline has typed ordinary failure")
            }
            try await wait("expired normal retirement") { sink.value.1 == 1 }
            try check(session.status.closed && session.status.drained && sink.value.2 == ["terminal","retired"], "expiry terminal precedes actual retirement")
            let reader = try AppPrivateKeyValueStore(directory: directory, namespaces: ["review"]); await reader.close()
            var held: [ExperimentalCapabilityConstruction] = []
            for _ in 0..<16 { held.append(try ExperimentalCapabilitySession.prepare(module: Data(), startupExport: "startup", policy: policy(), adapters: .init())) }
            try check(held.count == 16, "ordinary expiry restores every bridge permit"); held.removeAll()
        }
        do {
            let session = try await ExperimentalCapabilitySession.prepare(module: EnableReviewGuest.module(), startupExport: "startup", policy: policy(), adapters: .init()).create()
            _ = try await session.startup()
            do { try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: 0); throw EnablePublicFailure(message: "development owner accepted") }
            catch let error as ExperimentalCapabilityError { try check(error.failure.kind == .callerAPI(.invalidLifecycleState) && error.code == "owned_session_required", "non-owned SPI rejects before deadline classification") }
            try check(!session.status.closed && session.status.failure == nil, "SPI misuse keeps development owner unchanged")
            try await session.enableEffects(); try check(!session.status.closed, "legacy enable remains usable")
            session.close(); try await wait("legacy drain") { session.status.drained }
        }
        do {
            let sink = EnablePublicSink(), group = try group(root.appendingPathComponent("trap"),sink)
            let session = try await ExperimentalCapabilitySession.prepareOwned(module: EnableReviewGuest.module(trappingStartup: true), startupExport: "startup", policy: policy(), adapterGroup: group).create()
            do { _ = try await session.startup(); throw EnablePublicFailure(message: "unreachable startup accepted") }
            catch let error as ExperimentalCapabilityError { try check(error.failure.kind == .guestTrap(.unreachable) && error.failure.operation == .startup, "actual startup trap is checked first failure") }
            let first = session.status.failureDetail
            do { try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: 0); throw EnablePublicFailure(message: "terminal owner enabled") }
            catch let error as ExperimentalCapabilityError { try check(error.code == "closed", "preexisting terminal rejects queued work") }
            try await wait("trap retirement") { sink.value.1 == 1 }
            try check(sink.value.0.count == 1 && sink.value.0[0] == first && session.status.failureDetail == first, "later expiry cannot replace checked startup trap")
        }
        do {
            let sink = EnablePublicSink(), group = try group(root.appendingPathComponent("closed"),sink)
            let session = try await ExperimentalCapabilitySession.prepareOwned(module: EnableReviewGuest.module(), startupExport: "startup", policy: policy(), adapterGroup: group).create()
            _ = try await session.startup(); session.close()
            do { try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds: 0); throw EnablePublicFailure(message: "closed owner enabled") }
            catch let error as ExperimentalCapabilityError { try check(error.code == "closed", "already closed denies without deadline failure") }
            try await wait("normal closed retirement") { sink.value.1 == 1 }
            try check(session.status.failure == nil && sink.value.0.isEmpty, "already closed path preserves normal close classification")
        }
        print("public owned-enable review passed \(checks) checks")
    }
}
