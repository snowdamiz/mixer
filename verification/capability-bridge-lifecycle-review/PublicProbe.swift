// Original SPI consumer. No @testable import, private completion injection,
// transferred-adapter alias, generic I/O service or synthetic drain acknowledgement.
import Foundation
import MixerCapabilities
@_spi(CapabilityLifecycle) import MixerExperimentalCapabilityRuntime

final class Sink: @unchecked Sendable, CapabilityBridgeTerminalObserver, CapabilityBridgeRetirementObserver {
    private let lock = NSLock()
    private var terminals = 0
    private var retirements = 0
    private var first: ExperimentalCapabilityFailure?
    private var events: [String] = []
    func recordTerminalFailure(_ failure: ExperimentalCapabilityFailure) {
        lock.lock(); defer { lock.unlock() }
        terminals += 1
        events.append("terminal")
        if first == nil { first = failure }
    }
    func recordRetired() { lock.lock(); retirements += 1; events.append("retired"); lock.unlock() }
    var value: (Int, Int, ExperimentalCapabilityFailure?) {
        lock.lock(); defer { lock.unlock() }; return (terminals, retirements, first)
    }
    var ordering: [String] { lock.lock(); defer { lock.unlock() }; return events }
    // Dedicated data sink: deliberately no reference back to any group,
    // construction, session, policy, adapter or outer resource owner.
}
struct ProbeFailure: Error { let message: String }

@main struct PublicProbe {
    @MainActor static var checks = 0
    @MainActor static func check(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
        checks += 1; guard try condition() else { throw ProbeFailure(message: message) }
    }
    @MainActor static func wait(_ label: String, until predicate: () -> Bool) async throws {
        let cutoff = ContinuousClock.now.advanced(by: .seconds(5))
        while !predicate() {
            guard ContinuousClock.now < cutoff else { throw ProbeFailure(message: "timed out: " + label) }
            try await Task.sleep(for: .milliseconds(2))
        }
    }
    static func owned(_ directory: URL, _ sink: Sink) throws -> OwnedCapabilityAdapterGroup {
        // No alias to the concrete adapter survives ownership transfer.
        OwnedCapabilityAdapterGroup(storage: try AppPrivateKeyValueStore(directory: directory, namespaces: ["review"]), terminal: sink, retirement: sink)
    }
    static func policy() throws -> CapabilityPolicy {
        let grant = CapabilityGrant(capabilityID: CapabilitySchemas.storageID, schemaSHA256: CapabilitySchemas.storageSHA256,
                                    permissions: ["storage.appPrivate"], namespaces: ["review"])
        return try CapabilityPolicy(installed: [grant], manifest: [grant])
    }
    static func reopened(_ directory: URL) throws -> AppPrivateKeyValueStore {
        try AppPrivateKeyValueStore(directory: directory, namespaces: ["review"])
    }
    @MainActor static func main() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-lifecycle-public-review-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: root) }

        // Actual Wasm dispatch -> actual closed KV adapter -> actual persisted data.
        do {
            let directory = root.appendingPathComponent("normal"), sink = Sink(), group = try owned(directory, sink)
            let construction = try ExperimentalCapabilitySession.prepareOwned(module: module(), startupExport: "startup", policy: policy(), adapterGroup: group)
            let session = try await construction.create(); _ = try await session.startup(); try await session.enableEffects()
            _ = try await session.invoke("run")
            try await wait("real KV exit acknowledgement") { session.status.acknowledgements == 1 }
            try check(sink.value.0 == 0 && sink.value.1 == 0, "live success cannot retire")
            group.closeIfUntransferred()
            try check(!session.status.closed, "transferred group close cannot close its session")
            session.close(); session.close()
            try await wait("normal exact retirement") { sink.value.1 == 1 }
            try check(session.status.drained && session.status.failure == nil, "retirement follows actual normal native drain")
            try check(sink.value.0 == 0 && sink.value.1 == 1, "normal close has one retirement and no terminal failure")
            let reader = try reopened(directory)
            let value = try await reader.get(KVGetArguments(namespace: "review", key: "lifecycle"))
            try check(value.found && value.valueBase64 == "bGlmZQ==", "real guest put committed exact storage bytes")
            await reader.close()
        }

        // Asynchronous ready export failure is checked wake evidence, not an
        // ordinary call's thrown error and not a substitute for actual retirement.
        do {
            let directory = root.appendingPathComponent("wake-trap"), sink = Sink(), group = try owned(directory, sink)
            let session = try await ExperimentalCapabilitySession.prepareOwned(module: module(trappingWake: true), startupExport: "startup", policy: policy(), adapterGroup: group).create()
            _ = try await session.startup(); try await session.enableEffects(); _ = try await session.invoke("run")
            try await wait("spontaneous wake failure") { sink.value.0 == 1 }
            try check(sink.value.2?.kind == .guestTrap(.unreachable), "observer receives checked unreachable kind")
            try check(sink.value.2?.operation == .wake && sink.value.2?.code == "unreachable", "observer retains wake operation and code")
            try check(session.status.closed, "terminal failure synchronously closes bridge admission")
            session.close(); group.closeIfUntransferred()
            try await wait("wake failure actual retirement") { sink.value.1 == 1 }
            try check(sink.value.0 == 1 && sink.value.1 == 1 && session.status.drained, "terminal first failure and retirement are each exactly once")
            try check(sink.ordering == ["terminal", "retired"], "checked wake failure precedes exact retirement")
            let reader = try reopened(directory); await reader.close()
        }

        do {
            let directory = root.appendingPathComponent("cancel-unused"), sink = Sink(), group = try owned(directory, sink)
            let construction = try ExperimentalCapabilitySession.prepareOwned(module: module(), startupExport: "startup", policy: policy(), adapterGroup: group)
            do { _ = try ExperimentalCapabilitySession.prepareOwned(module: module(), startupExport: "startup", policy: policy(), adapterGroup: group); throw ProbeFailure(message: "group consumed twice") }
            catch let error as ExperimentalCapabilityError { try check(error.code == "adapter_group_consumed", "duplicate group transfer rejects explicitly") }
            construction.cancel(); construction.cancel(); group.closeIfUntransferred()
            try await wait("unused construction cancellation") { sink.value.1 == 1 }
            try check(sink.value.0 == 0 && sink.value.1 == 1, "cancel-before-create is cleanup rather than terminal VM failure")
            do { _ = try await construction.create(); throw ProbeFailure(message: "cancelled create accepted") }
            catch let error as ExperimentalCapabilityError { try check(error.code == "construction_consumed", "cancelled construction remains one-shot") }
            let reader = try reopened(directory); await reader.close()
        }

        do {
            let directory = root.appendingPathComponent("bad-module"), sink = Sink(), group = try owned(directory, sink)
            let construction = try ExperimentalCapabilitySession.prepareOwned(module: Data([0]), startupExport: "startup", policy: policy(), adapterGroup: group)
            do { _ = try await construction.create(); throw ProbeFailure(message: "malformed module accepted") }
            catch is ExperimentalCapabilityError { }
            try await wait("known native constructor failure") { sink.value.1 == 1 }
            try check(sink.value.0 == 1 && sink.value.2?.operation == .construction, "known constructor rejection delivers typed first failure")
            try check(sink.ordering == ["terminal", "retired"], "constructor failure observer precedes adapter cleanup retirement")
            let reader = try reopened(directory); await reader.close()
        }

        do {
            let directory = root.appendingPathComponent("abandoned-group"), sink = Sink()
            var group: OwnedCapabilityAdapterGroup? = try owned(directory, sink)
            weak let weakGroup = group
            group = nil
            try await wait("abandoned untransferred group") { sink.value.1 == 1 }
            try check(weakGroup == nil && sink.value.0 == 0, "dedicated sink allows group deinit and no fabricated failure")
            let reader = try reopened(directory); await reader.close()
        }

        do {
            let directory = root.appendingPathComponent("abandoned-construction"), sink = Sink(), group = try owned(directory, sink)
            var construction: ExperimentalCapabilityConstruction? = try ExperimentalCapabilitySession.prepareOwned(module: module(), startupExport: "startup", policy: policy(), adapterGroup: group)
            weak let weakConstruction = construction; construction = nil
            try await wait("abandoned consumed construction") { sink.value.1 == 1 }
            try check(weakConstruction == nil && sink.value.0 == 0, "unused transferred construction deinit closes adapters")
            let reader = try reopened(directory); await reader.close()
        }
        print("public lifecycle SPI review passed \(checks) checks")
    }

    // Original bounded Wasm builder. Imports exact storage_put and poll, defines
    // memory/startup/run/ready, and embeds one strict owned argument object.
    static func module(trappingWake: Bool = false) -> Data {
        func u(_ value: Int) -> [UInt8] {
            var value = value, bytes: [UInt8] = []
            repeat { let byte = UInt8(value & 127); value >>= 7; bytes.append(byte | (value == 0 ? 0 : 128)) } while value != 0
            return bytes
        }
        func signed(_ value: Int) -> [UInt8] {
            var value = value, bytes: [UInt8] = []
            while true {
                var byte = UInt8(value & 127); value >>= 7
                let done = (value == 0 && byte & 64 == 0) || (value == -1 && byte & 64 != 0)
                if !done { byte |= 128 }; bytes.append(byte); if done { return bytes }
            }
        }
        func name(_ value: String) -> [UInt8] { u(value.utf8.count) + Array(value.utf8) }
        func section(_ tag: UInt8, _ content: [UInt8]) -> [UInt8] { [tag] + u(content.count) + content }
        func i32(_ value: Int) -> [UInt8] { [0x41] + signed(value) }
        func body(_ code: [UInt8]) -> [UInt8] { let content = [UInt8(0)] + code + [0x0b]; return u(content.count) + content }
        let arguments = Array("{\"namespace\":\"review\",\"key\":\"lifecycle\",\"valueBase64\":\"bGlmZQ==\"}".utf8)
        var bytes: [UInt8] = [0,97,115,109,1,0,0,0]
        bytes += section(1, [3,0x60,0,0,0x60,3,0x7f,0x7f,0x7f,1,0x7f,0x60,4,0x7e,0x7f,0x7f,0x7f,1,0x7f])
        bytes += section(2, [2] + name("mixer.capability.v1") + name("storage_put") + [0,1] + name("mixer.capability.v1") + name("poll") + [0,2])
        bytes += section(3, [3,0,0,0]); bytes += section(5, [1,0,1])
        bytes += section(7, [3] + name("startup") + [0,2] + name("run") + [0,3] + name("mixer_guest_capability_ready_v1") + [0,4])
        let run = i32(0) + i32(arguments.count) + i32(1024) + [0x10,0,0x1a]
        let ready = trappingWake ? [UInt8(0)] : i32(5000) + i32(1024) + [0x29,3,0] + i32(2048) + i32(1024) + i32(4096) + [0x10,1,0x36,2,0]
        bytes += section(10, [3] + body([]) + body(run) + body(ready))
        bytes += section(11, [1,0] + i32(0) + [0x0b] + u(arguments.count) + arguments)
        return Data(bytes)
    }
}
