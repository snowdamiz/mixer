import Dispatch
import Foundation
import Testing
@_spi(MixerNativeAppearanceV2) @testable import MixerAndroidRuntime

struct TransactionTests {
    enum Rejected: Error { case input }
    struct Counter: AndroidApplicationEngine {
        var value = 0
        func render() throws -> Data { Data(String(value).utf8) }
        mutating func dispatch(_ input: Data) throws -> Data {
            value += 1
            switch String(decoding: input, as: UTF8.self) {
            case "fail": throw Rejected.input
            case "oversize": return Data(repeating: 65, count: 1_048_577)
            default: return try render()
            }
        }
    }
    struct Reply: Sendable {
        let status: Int32
        let bytes: Data
        let written: Int
        let token: UInt64
    }
    func call<E>(_ registry: AndroidSessionRegistry<E>, _ handle: UInt64,
                 staged: Bool, operation: UInt32 = 1, input: Data = Data(), capacity: Int = 16_384) -> Reply {
        var output = [UInt8](repeating: 0xCC, count: capacity)
        var written = -1
        var token: UInt64 = .max
        let status = input.withUnsafeBytes { raw in
            output.withUnsafeMutableBufferPointer { buffer in
                if staged {
                    return registry.prepareV2(handle, operation, raw.bindMemory(to: UInt8.self).baseAddress,
                                              input.count, buffer.baseAddress, capacity, &written, &token)
                }
                return registry.exchange(handle, operation, raw.bindMemory(to: UInt8.self).baseAddress,
                                         input.count, buffer.baseAddress, capacity, &written)
            }
        }
        return Reply(status: status, bytes: status == 0 ? Data(output.prefix(written)) : Data(),
                     written: written, token: token)
    }
    func render<E>(_ registry: AndroidSessionRegistry<E>, _ handle: UInt64) -> Reply {
        call(registry, handle, staged: false, operation: 0)
    }

    @Test func abortRetainsCommittedEngineAndCommitAdvancesExactlyOnce() {
        let registry = AndroidSessionRegistry { Counter() }
        let handle = registry.create()
        #expect(render(registry, handle).bytes == Data("0".utf8))
        let first = call(registry, handle, staged: true)
        #expect(first.status == 0 && first.token > 0 && first.bytes == Data("1".utf8))
        #expect(render(registry, handle).status == 5)
        #expect(call(registry, handle, staged: false).status == 5)
        let blocked = call(registry, handle, staged: true)
        #expect(blocked.status == 5 && blocked.token == 0 && blocked.written == 0)
        #expect(registry.abortV2(handle, first.token) == 0)
        #expect(registry.abortV2(handle, first.token) == 0)
        #expect(registry.commitV2(handle, first.token) == 6)
        #expect(render(registry, handle).bytes == Data("0".utf8))
        let second = call(registry, handle, staged: true)
        #expect(second.token > first.token)
        #expect(registry.abortV2(handle, first.token) == 0)
        #expect(render(registry, handle).status == 5) // Old abort did not discard the new candidate.
        #expect(registry.commitV2(handle, second.token) == 0)
        #expect(registry.commitV2(handle, second.token) == 6)
        #expect(registry.abortV2(handle, second.token) == 6)
        #expect(render(registry, handle).bytes == Data("1".utf8))
        #expect(registry.destroy(handle) == 0)
    }

    @Test func ownerTokensNeverCrossSessionsOrSurviveDestroy() {
        let registry = AndroidSessionRegistry { Counter() }
        let a = registry.create(), b = registry.create()
        let first = call(registry, a, staged: true), second = call(registry, b, staged: true)
        #expect(first.token != second.token)
        #expect(registry.commitV2(a, second.token) == 6)
        #expect(registry.abortV2(b, first.token) == 6)
        #expect(registry.commitV2(a, 0) == 6)
        #expect(registry.abortV2(a, .max) == 6)
        #expect(registry.destroy(a) == 0)
        #expect(registry.commitV2(a, first.token) == 2)
        #expect(registry.abortV2(a, first.token) == 2)
        let c = registry.create()
        #expect(c > b)
        #expect(registry.commitV2(c, first.token) == 6)
        #expect(registry.commitV2(b, second.token) == 0)
        #expect(render(registry, b).bytes == Data("1".utf8))
        #expect(render(registry, c).bytes == Data("0".utf8))
        #expect(registry.destroy(b) == 0 && registry.destroy(c) == 0)
    }

    @Test func capacityAndEngineFailuresRetainNoCandidateAndNoReduction() {
        let registry = AndroidSessionRegistry { Counter() }
        let handle = registry.create()
        let small = call(registry, handle, staged: true, capacity: 0)
        #expect(small.status == 3 && small.written == 1 && small.token == 0)
        #expect(render(registry, handle).bytes == Data("0".utf8))
        for input in ["fail", "oversize"] {
            let failed = call(registry, handle, staged: true, input: Data(input.utf8))
            #expect(failed.status == 4 && failed.written == 0 && failed.token == 0)
            #expect(render(registry, handle).bytes == Data("0".utf8))
        }
        let accepted = call(registry, handle, staged: true)
        #expect(accepted.status == 0 && accepted.token == 1)
        #expect(registry.commitV2(handle, accepted.token) == 0)
        #expect(render(registry, handle).bytes == Data("1".utf8))
        #expect(registry.destroy(handle) == 0)
    }

    @Test func invalidPrepareZerosOutputMetadataAndDoesNotRetainState() {
        let registry = AndroidSessionRegistry { Counter() }
        let handle = registry.create()
        for (operation, length, capacity) in [(UInt32(2),0,0), (0,1,0), (1,-1,0),
                                              (1,131_073,0), (1,1,0), (1,0,-1), (1,0,1_048_577), (1,0,1)] {
            var written = 99
            var token: UInt64 = 99
            #expect(registry.prepareV2(handle, operation, nil, length, nil, capacity, &written, &token) == 1)
            #expect(written == 0 && token == 0)
        }
        var token: UInt64 = 99
        #expect(registry.prepareV2(handle, 0, nil, 0, nil, 0, nil, &token) == 1)
        #expect(token == 0)
        var written = 99
        #expect(registry.prepareV2(handle, 0, nil, 0, nil, 0, &written, nil) == 1)
        #expect(written == 0)
        #expect(registry.prepareV2(0, 0, nil, 0, nil, 0, &written, &token) == 2)
        #expect(written == 0 && token == 0)
        #expect(render(registry, handle).bytes == Data("0".utf8))
        #expect(registry.destroy(handle) == 0)
    }

    @Test func renderCandidateAndRegistryCapacityStayBounded() {
        let registry = AndroidSessionRegistry { Counter() }
        let handles = (0..<16).map { _ in registry.create() }
        #expect(Set(handles).count == 16 && !handles.contains(0))
        let pending = handles.map { call(registry, $0, staged: true, operation: 0) }
        #expect(pending.allSatisfy { $0.status == 0 && $0.bytes == Data("0".utf8) })
        #expect(Set(pending.map(\.token)).count == 16)
        #expect(registry.create() == 0)
        for (handle, candidate) in zip(handles, pending) {
            #expect(registry.commitV2(handle, candidate.token) == 0)
            #expect(render(registry, handle).bytes == Data("0".utf8))
            #expect(registry.destroy(handle) == 0)
        }
        let replacement = registry.create()
        #expect(replacement > handles.last!)
        #expect(registry.destroy(replacement) == 0)
    }

    @Test func realDocumentRevisionAndIdentityWaitForNativeDecision() throws {
        let fixture = RuntimeTests()
        let registry = AndroidSessionRegistry { try fixture.session() }
        let handle = registry.create()
        let initial = render(registry, handle).bytes
        let event = try fixture.event(initial, value: "Café 東京 🧪")
        let aborted = call(registry, handle, staged: true, input: event)
        #expect(aborted.status == 0 && aborted.bytes != initial)
        #expect(registry.abortV2(handle, aborted.token) == 0)
        #expect(render(registry, handle).bytes == initial)
        let accepted = call(registry, handle, staged: true, input: event)
        #expect(accepted.status == 0 && accepted.bytes == aborted.bytes)
        #expect(registry.commitV2(handle, accepted.token) == 0)
        #expect(render(registry, handle).bytes == accepted.bytes)
        let stale = call(registry, handle, staged: true, input: event)
        #expect(stale.status == 4 && stale.token == 0 && stale.written == 0)
        #expect(render(registry, handle).bytes == accepted.bytes)
        #expect(registry.destroy(handle) == 0)
    }

    final class Decisions: @unchecked Sendable {
        let lock = NSLock()
        var commit: Int32 = -1
        var abort: Int32 = -1
        func set(_ value: Int32, commit: Bool) {
            lock.lock(); defer { lock.unlock() }
            if commit { self.commit = value } else { self.abort = value }
        }
    }
    @Test func concurrentCommitAndAbortLinearizeOneDecision() {
        let registry = AndroidSessionRegistry { Counter() }
        for _ in 0..<24 {
            let handle = registry.create()
            let candidate = call(registry, handle, staged: true)
            let results = Decisions()
            DispatchQueue.concurrentPerform(iterations: 2) { index in
                results.set(index == 0 ? registry.commitV2(handle, candidate.token)
                                      : registry.abortV2(handle, candidate.token), commit: index == 0)
            }
            #expect((results.commit == 0 && results.abort == 6) || (results.commit == 6 && results.abort == 0))
            #expect(render(registry, handle).bytes == Data((results.commit == 0 ? "1" : "0").utf8))
            #expect(registry.destroy(handle) == 0)
        }
    }
}
