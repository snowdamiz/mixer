// Original review-only internal gate/fault probe against unmodified Debug
// products. Manual nativeDidDrain is synthetic gating evidence, never an actual
// exit claim. A deliberately stale internal native handle is not reachable via
// the public SPI and is used only to exercise checked close-failure retention.
import Foundation
import MixerCapabilities
@_spi(CapabilityLifecycle) @testable import MixerExperimentalCapabilityRuntime

final class InternalSink: @unchecked Sendable, CapabilityBridgeTerminalObserver, CapabilityBridgeRetirementObserver {
    private let lock = NSLock()
    private var failures: [ExperimentalCapabilityFailure] = []
    private var retires = 0
    private var events: [String] = []
    func recordTerminalFailure(_ failure: ExperimentalCapabilityFailure) {
        lock.lock(); failures.append(failure); events.append("terminal"); lock.unlock()
    }
    func recordRetired() { lock.lock(); retires += 1; events.append("retired"); lock.unlock() }
    var value: ([ExperimentalCapabilityFailure], Int, [String]) { lock.lock(); defer { lock.unlock() }; return (failures, retires, events) }
}
struct InternalFailure: Error { let message: String }

@main struct InternalProbe {
    @MainActor static var checks = 0
    @MainActor static func check(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
        checks += 1; guard try condition() else { throw InternalFailure(message: message) }
    }
    @MainActor static func wait(_ label: String, _ predicate: () async -> Bool) async throws {
        let cutoff = ContinuousClock.now.advanced(by: .seconds(5))
        while !(await predicate()) {
            guard ContinuousClock.now < cutoff else { throw InternalFailure(message: "timed out: " + label) }
            try await Task.sleep(for: .milliseconds(2))
        }
    }
    static func released(_ directory: URL) async -> Bool {
        do { let reader = try AppPrivateKeyValueStore(directory: directory, namespaces: ["review"]); await reader.close(); return true }
        catch { return false }
    }
    @MainActor static func fillRemaining(_ count: Int) throws -> [ConstructionPermit] {
        var held: [ConstructionPermit] = []
        for _ in 0..<count { held.append(try ConstructionPermit.acquire()) }
        do { _ = try ConstructionPermit.acquire(); throw InternalFailure(message: "retained owner released capacity") }
        catch let error as ExperimentalCapabilityError { try check(error.code == "construction_busy", "retained owner still counts toward fixed sixteen") }
        return held
    }
    @MainActor static func main() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-lifecycle-private-review-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: root) }
        let mode = CommandLine.arguments[1]
        if mode == "gates" {
            // Real concrete storage closes; constructor tail is intentionally
            // absent. The later native drain call below is synthetic.
            let directory = root.appendingPathComponent("gates")
            var sink: InternalSink? = InternalSink(); weak let weakSink = sink
            let group = OwnedCapabilityAdapterGroup(storage: try AppPrivateKeyValueStore(directory: directory, namespaces: ["review"]), terminal: sink!, retirement: sink!)
            _ = try group.core.consume(ConstructionPermit.acquire()); group.core.expectsNative(); sink = nil
            group.core.close(host: nil, nativeOwner: nil)
            try await wait("actual storage close") { await released(directory) }
            try check(weakSink != nil && weakSink!.value.1 == 0, "sinks retained while constructor and native gates remain")
            try check(group.core.cleanupJobCount == 1 && !group.core.constructorTailObserved, "one cleanup Task and absent logical constructor tail")
            group.core.nativeDidDrain() // Synthetic internal gate, explicitly labelled.
            try check(weakSink!.value.1 == 0, "native drain alone cannot retire before constructor tail")
            let retainedSink = weakSink!
            var held = try fillRemaining(15); held.forEach { $0.release() }; held.removeAll()
            group.core.constructorReturned()
            try await wait("synthetic gates complete") { retainedSink.value.1 == 1 }
            try check(retainedSink.value.0.isEmpty && retainedSink.value.2 == ["retired"], "gate completion retires exactly once without terminal failure")
            group.core.constructorReturned(); group.core.nativeDidDrain(); group.closeIfUntransferred()
            try check(retainedSink.value.1 == 1 && group.core.cleanupJobCount == 1, "repeated gate/close notifications remain idempotent")
            var all: [ConstructionPermit] = []; for _ in 0..<16 { all.append(try ConstructionPermit.acquire()) }
            try check(all.count == 16, "exact retirement releases its construction reservation")
            all.forEach { $0.release() }

            let concurrentSink = InternalSink(), concurrentGroup = OwnedCapabilityAdapterGroup(terminal: concurrentSink, retirement: concurrentSink)
            DispatchQueue.concurrentPerform(iterations: 64) { _ in concurrentGroup.closeIfUntransferred() }
            try await wait("concurrent untransferred close") { concurrentSink.value.1 == 1 }
            try check(concurrentGroup.core.cleanupJobCount == 1 && concurrentSink.value.0.isEmpty, "concurrent close owns one cleanup and one retirement")
        } else if mode == "close-failure" {
            let directory = root.appendingPathComponent("close-failure"), sink = InternalSink()
            let group = OwnedCapabilityAdapterGroup(storage: try AppPrivateKeyValueStore(directory: directory, namespaces: ["review"]), terminal: sink, retirement: sink)
            let permit = try ConstructionPermit.acquire(), adapters = try group.core.consume(permit)
            let configuration = ExperimentalCapabilityConfiguration()
            let host = try CapabilityHost(policy: CapabilityPolicy(installed: [], manifest: []), installedAdapters: adapters)
            let native = try NativeCapabilitySession(module: module(), startup: "startup", configuration: configuration)
            group.core.expectsNative(); group.core.constructorReturned()
            let owner = NativeExitOwner(native: native, host: host, configuration: configuration, permit: permit, lifecycle: group.core)
            owner.start()
            try native.close() // Review-only deliberate stale-handle fault.
            owner.stop()
            try await wait("checked repeated native close error") { sink.value.0.count == 1 }
            try await wait("actual adapters close despite native failure") { await released(directory) }
            try check(sink.value.0[0].operation == .close && sink.value.0[0].nativeStatus == 3 && sink.value.0[0].code == "invalid_session", "native close failure has checked immutable status/operation/code")
            try check(owner.closed && !owner.status.drained && sink.value.1 == 0, "failed native close cannot advertise drain or retirement after concrete close")
            try check(sink.value.2 == ["terminal"] && group.core.cleanupJobCount == 1, "close failure signals terminal once and never retires")
            owner.stop("review_second_failure", detail: ExperimentalCapabilityError("review_second_failure").failure)
            try check(sink.value.0.count == 1 && owner.status.failureDetail == sink.value.0[0], "repeated close preserves first checked failure")
            let held = try fillRemaining(15)
            try check(held.count == 15, "failed-close owner retains one reservation after adapter close")
            // Isolated process exits with this intentional failed-close owner;
            // no later probe may use its retained permit/scheduler lifetime.
        } else { throw InternalFailure(message: "unknown mode") }
        print("internal lifecycle review \(mode) passed \(checks) checks")
    }
    static func module() -> Data {
        func name(_ value: String) -> [UInt8] { [UInt8(value.utf8.count)] + Array(value.utf8) }
        func section(_ tag: UInt8, _ content: [UInt8]) -> [UInt8] { [tag, UInt8(content.count)] + content }
        var bytes: [UInt8] = [0,97,115,109,1,0,0,0]
        bytes += section(1, [1,0x60,0,0]); bytes += section(3, [2,0,0])
        bytes += section(7, [2] + name("startup") + [0,0] + name("mixer_guest_capability_ready_v1") + [0,1])
        bytes += section(10, [2,2,0,0x0b,2,0,0x0b]); return Data(bytes)
    }
}
