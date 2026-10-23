import Dispatch
import Foundation
import MixerCapabilities
import MixerExperimentalCapabilityRuntime
import XCTest

// AUTHORED, UNQUALIFIED: requires the frozen bridge/native candidate and recorded
// actual debug/release execution. No internal SDK or bridge test hooks are used.
private enum ReviewFailure: Error, Sendable {
    case missingFixture(String)
    case timeout(String)
    case unexpectedValue(String)
}

private struct StoreContext: Sendable {
    let directory: URL
    let store: AppPrivateKeyValueStore
}

private func fixture(_ name: String) throws -> Data {
    guard let url = Bundle.module.url(forResource: name, withExtension: "wasm", subdirectory: "Fixtures") else {
        throw ReviewFailure.missingFixture(name)
    }
    return try Data(contentsOf: url)
}

private func policy(allow: Bool = true) throws -> CapabilityPolicy {
    let grant = CapabilityGrant(capabilityID: CapabilitySchemas.storageID,
        schemaSHA256: CapabilitySchemas.storageSHA256, permissions: ["storage.appPrivate"],
        namespaces: ["bridge_review"])
    return try CapabilityPolicy(installed: [grant], manifest: allow ? [grant] : [])
}

private func withStore(_ body: @Sendable (StoreContext) async throws -> Void) async throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-independent-bridge-" + UUID().uuidString)
    let context = try StoreContext(directory: directory, store: AppPrivateKeyValueStore(directory: directory, namespaces: ["bridge_review"]))
    do {
        try await body(context)
        await context.store.close()
        try FileManager.default.removeItem(at: directory)
    } catch {
        await context.store.close()
        try? FileManager.default.removeItem(at: directory)
        throw error
    }
}

private func create(_ context: StoreContext, fixture name: String = "storage-flow", allow: Bool = true,
                   configuration: ExperimentalCapabilityConfiguration = .init(timeoutMilliseconds: 5000)) async throws -> ExperimentalCapabilitySession {
    let construction = try ExperimentalCapabilitySession.prepare(module: fixture(name), startupExport: "startup",
        configuration: configuration, policy: policy(allow: allow), adapters: InstalledCapabilityAdapters(storage: context.store))
    return try await construction.create()
}

private func read(_ session: ExperimentalCapabilitySession, offset: UInt32, count: Int) async throws -> Data {
    // The public bridge has one ordinary/memory command position. A scheduled wake
    // can occupy it; a finite test-side retry does not change bridge admission.
    let end = ContinuousClock.now.advanced(by: .seconds(5))
    while true {
        do { return try await session.readMemory(offset: offset, count: count) }
        catch let error as ExperimentalCapabilityError where error.code == "command_busy" {
            guard ContinuousClock.now < end else { throw ReviewFailure.timeout("public memory command remained busy") }
            try await Task.sleep(for: .milliseconds(2))
        }
    }
}

private func word(_ session: ExperimentalCapabilitySession, at offset: UInt32) async throws -> UInt32 {
    let data = try await read(session, offset: offset, count: 4)
    guard data.count == 4 else { throw ReviewFailure.unexpectedValue("short public memory read") }
    return data.enumerated().reduce(UInt32(0)) { $0 | (UInt32($1.element) << UInt32($1.offset * 8)) }
}

private func waitForStage(_ session: ExperimentalCapabilitySession, _ expected: UInt32) async throws {
    let end = ContinuousClock.now.advanced(by: .seconds(5))
    while ContinuousClock.now < end {
        let stage = try await word(session, at: 0)
        if stage == expected { return }
        if session.status.closed { throw ReviewFailure.unexpectedValue("closed while waiting for stage: " + (session.status.failure ?? "none")) }
        try await Task.sleep(for: .milliseconds(2))
    }
    throw ReviewFailure.timeout("guest storage stage \(expected), status \(session.status)")
}

private func waitForExits(_ session: ExperimentalCapabilitySession, expected: UInt64) async throws {
    let end = ContinuousClock.now.advanced(by: .seconds(5))
    while ContinuousClock.now < end {
        let status = session.status
        if status.acknowledgements == expected && status.retainedExits == 0 { return }
        if status.closed { throw ReviewFailure.unexpectedValue("closed before exit join: " + (status.failure ?? "none")) }
        try await Task.sleep(for: .milliseconds(2))
    }
    throw ReviewFailure.timeout("actual exit join: \(session.status)")
}

private func closeAndDrain(_ session: ExperimentalCapabilitySession) async throws {
    session.close()
    session.close()
    let end = ContinuousClock.now.advanced(by: .seconds(5))
    while !session.status.drained && ContinuousClock.now < end { try await Task.sleep(for: .milliseconds(2)) }
    guard session.status.drained else { throw ReviewFailure.timeout("public close did not drain: \(session.status)") }
}

private func expectAsyncError(_ code: String, _ body: () async throws -> Void,
                              file: StaticString = #filePath, line: UInt = #line) async {
    do { try await body(); XCTFail("expected \(code)", file: file, line: line) }
    catch let error as ExperimentalCapabilityError { XCTAssertEqual(error.code, code, file: file, line: line) }
    catch { XCTFail("expected \(code), got \(error)", file: file, line: line) }
}

private func assertStartup(_ session: ExperimentalCapabilitySession) async throws {
    _ = try await session.startup()
    let enqueue = try await word(session, at: 8), poll = try await word(session, at: 12)
    XCTAssertEqual(enqueue, 0)
    XCTAssertEqual(poll, 0)
    let count = try await word(session, at: 16)
    XCTAssertGreaterThan(count, 0)
    XCTAssertLessThanOrEqual(count, 1024)
    let data = try await read(session, offset: 2048, count: Int(count))
    XCTAssertEqual(try GuestCapabilityTransportCodecV1.decodeCompletion(data, expectedOperation: .storagePut), .failure(.unavailable))
}

private func assertCompletion(_ session: ExperimentalCapabilitySession, stage: UInt32,
                              operation: GuestCapabilityOperationV1, expected: GuestCapabilityCompletionV1) async throws {
    let count = try await word(session, at: 64 + stage * 4)
    XCTAssertGreaterThan(count, 0)
    XCTAssertLessThanOrEqual(count, 1024)
    let data = try await read(session, offset: 4096 + (stage - 1) * 2048, count: Int(count))
    XCTAssertEqual(try GuestCapabilityTransportCodecV1.decodeCompletion(data, expectedOperation: operation), expected)
    XCTAssertEqual(data, try GuestCapabilityTransportCodecV1.encodeCompletion(expected, operation: operation),
        "actual guest bytes must match the strict canonical wrapper, without host identity")
}

private final class ConcurrentConstructions: @unchecked Sendable {
    private let lock = NSLock()
    private var owners: [ExperimentalCapabilityConstruction] = []
    private var errors: [String] = []
    func retain(_ value: ExperimentalCapabilityConstruction) { lock.lock(); owners.append(value); lock.unlock() }
    func failed(_ error: any Error) { lock.lock(); errors.append((error as? ExperimentalCapabilityError)?.code ?? String(describing: error)); lock.unlock() }
    var counts: (Int, [String]) { lock.lock(); defer { lock.unlock() }; return (owners.count, errors) }
    func abandonAll() { lock.lock(); owners.removeAll(); lock.unlock() }
}

final class PublicBridgeReviewTests: XCTestCase, @unchecked Sendable {
    func testConcreteStorageBinaryMissingEmptyAndDeleteThroughFixedWake() async throws {
        try await withStore { context in
            let session = try await create(context)
            defer { session.close() }
            try await assertStartup(session)
            let startupValue = try await context.store.get(KVGetArguments(namespace: "bridge_review", key: "startup_probe"))
            XCTAssertEqual(startupValue, KVGetResponse(found: false, valueBase64: ""))
            try await session.enableEffects()
            let accepted = try await session.invoke("run")
            XCTAssertEqual(accepted.value, .i32(0))
            try await waitForStage(session, 8)
            let committed = KVMutationResponse(committed: true)
            try await assertCompletion(session, stage: 1, operation: .storagePut, expected: .success(.put(committed)))
            try await assertCompletion(session, stage: 2, operation: .storageGet,
                expected: .success(.get(KVGetResponse(found: true, valueBase64: "AAECA//+gA=="))))
            try await assertCompletion(session, stage: 3, operation: .storageDelete, expected: .success(.delete(committed)))
            try await assertCompletion(session, stage: 4, operation: .storageGet,
                expected: .success(.get(KVGetResponse(found: false, valueBase64: ""))))
            try await assertCompletion(session, stage: 5, operation: .storagePut, expected: .success(.put(committed)))
            try await assertCompletion(session, stage: 6, operation: .storageGet,
                expected: .success(.get(KVGetResponse(found: true, valueBase64: ""))))
            try await assertCompletion(session, stage: 7, operation: .storageDelete, expected: .success(.delete(committed)))
            let finalValue = try await context.store.get(KVGetArguments(namespace: "bridge_review", key: "alpha"))
            XCTAssertEqual(finalValue, KVGetResponse(found: false, valueBase64: ""))
            try await waitForExits(session, expected: 7)
            XCTAssertEqual(session.status.acceptedCalls, 7)
            XCTAssertLessThanOrEqual(session.status.maximumBatchTurns, 4)
            XCTAssertNil(session.status.failure)
            try await closeAndDrain(session)
        }
    }

    func testPolicyDenialExercisesCallbacksInsideHostAcceptance() async throws {
        // SDK Host.accept synchronously delivers permissionDenied and joined exit
        // before submitObserved returns. This uses the actual public installed
        // host path, rather than injected callbacks or a substitute adapter.
        try await withStore { context in
            let session = try await create(context, allow: false)
            defer { session.close() }
            try await assertStartup(session)
            try await session.enableEffects()
            _ = try await session.invoke("run")
            try await waitForStage(session, 8)
            let operations: [GuestCapabilityOperationV1] = [.storagePut, .storageGet, .storageDelete, .storageGet, .storagePut, .storageGet, .storageDelete]
            for (index, operation) in operations.enumerated() {
                try await assertCompletion(session, stage: UInt32(index + 1), operation: operation, expected: .failure(.permissionDenied))
            }
            let value = try await context.store.get(KVGetArguments(namespace: "bridge_review", key: "alpha"))
            XCTAssertFalse(value.found)
            try await waitForExits(session, expected: 7)
            XCTAssertNil(session.status.failure)
            try await closeAndDrain(session)
        }
    }

    func testStrictMalformedArgumentsProduceRejectionAndNoConcreteEffect() async throws {
        for name in ["empty-arguments", "duplicate-key", "wrong-operation-object", "noncanonical-base64"] {
            try await withStore { context in
                let session = try await create(context, fixture: name)
                defer { session.close() }
                try await assertStartup(session)
                try await session.enableEffects()
                let accepted = try await session.invoke("run")
                XCTAssertEqual(accepted.value, .i32(0), "C accepts structural bytes before strict bridge decoding")
                try await waitForStage(session, 2)
                try await assertCompletion(session, stage: 1, operation: .storagePut, expected: .rejected(.invalidArguments))
                let value = try await context.store.get(KVGetArguments(namespace: "bridge_review", key: "alpha"))
                XCTAssertFalse(value.found)
                try await waitForExits(session, expected: 1)
                XCTAssertNil(session.status.failure)
                try await closeAndDrain(session)
            }
        }
    }

    func testConcurrentPrepareSeventeenthRejectsAndAbandonmentReturnsCapacity() throws {
        let module = try fixture("storage-flow"), allowed = try policy()
        let inventory = ConcurrentConstructions()
        DispatchQueue.concurrentPerform(iterations: 17) { _ in
            do {
                inventory.retain(try ExperimentalCapabilitySession.prepare(module: module, startupExport: "startup",
                    policy: allowed, adapters: InstalledCapabilityAdapters()))
            } catch { inventory.failed(error) }
        }
        XCTAssertEqual(inventory.counts.0, 16)
        XCTAssertEqual(inventory.counts.1, ["construction_busy"])
        inventory.abandonAll()
        // The previous constructions never scheduled create. Losing the last
        // reference must release their permits without a Task or native call.
        var replacements: [ExperimentalCapabilityConstruction] = []
        for _ in 0..<16 {
            replacements.append(try ExperimentalCapabilitySession.prepare(module: module, startupExport: "startup",
                policy: allowed, adapters: InstalledCapabilityAdapters()))
        }
        XCTAssertEqual(replacements.count, 16)
        replacements.removeAll()
    }

    func testCancelBeforeCreateIsOneShotAndDoesNotRetainPermit() async throws {
        let module = try fixture("storage-flow"), allowed = try policy()
        let cancelled = try ExperimentalCapabilitySession.prepare(module: module, startupExport: "startup",
            policy: allowed, adapters: InstalledCapabilityAdapters())
        cancelled.cancel(); cancelled.cancel()
        await expectAsyncError("construction_consumed") { _ = try await cancelled.create() }
        var pending: [ExperimentalCapabilityConstruction] = []
        for _ in 0..<16 {
            pending.append(try ExperimentalCapabilitySession.prepare(module: module, startupExport: "startup",
                policy: allowed, adapters: InstalledCapabilityAdapters()))
        }
        XCTAssertEqual(pending.count, 16, "cancelled construction is still strongly retained here")
        withExtendedLifetime(cancelled) {}
        pending.removeAll()
    }

    func testRepeatedCreateAndLateConstructionCancelPreserveReturnedSession() async throws {
        try await withStore { context in
            let construction = try ExperimentalCapabilitySession.prepare(module: fixture("storage-flow"), startupExport: "startup",
                policy: policy(), adapters: InstalledCapabilityAdapters(storage: context.store))
            let session = try await construction.create()
            defer { session.close() }
            await expectAsyncError("construction_consumed") { _ = try await construction.create() }
            construction.cancel()
            XCTAssertFalse(session.status.closed)
            try await assertStartup(session)
            XCTAssertFalse(session.status.closed)
            try await closeAndDrain(session)
        }
    }

    func testOrdinaryRejectedNativeCreateReturnsConstructionCapacity() async throws {
        let allowed = try policy()
        let rejected = try ExperimentalCapabilitySession.prepare(module: Data([0]), startupExport: "startup",
            policy: allowed, adapters: InstalledCapabilityAdapters())
        do { _ = try await rejected.create(); XCTFail("expected ordinary module validation rejection") }
        catch let error as ExperimentalCapabilityError { XCTAssertEqual(error.nativeStatus, 1) }
        var replacements: [ExperimentalCapabilityConstruction] = []
        for _ in 0..<16 {
            replacements.append(try ExperimentalCapabilitySession.prepare(module: fixture("single-put"), startupExport: "startup",
                policy: allowed, adapters: InstalledCapabilityAdapters()))
        }
        XCTAssertEqual(replacements.count, 16)
        withExtendedLifetime(rejected) {}
        replacements.removeAll()
    }

    func testOrdinaryNativeAPIRejectionDoesNotTerminateUsableSession() async throws {
        try await withStore { context in
            let session = try await create(context)
            defer { session.close() }
            do { try await session.enableEffects(); XCTFail("enable before startup must reject") }
            catch let error as ExperimentalCapabilityError { XCTAssertEqual(error.nativeStatus, 3) }
            XCTAssertFalse(session.status.closed)
            try await assertStartup(session)
            try await session.enableEffects()
            let stage = try await word(session, at: 0)
            XCTAssertEqual(stage, 0)
            XCTAssertNil(session.status.failure)
            try await closeAndDrain(session)
        }
    }

    func testNonconsumingReadyGuestYieldsWhileAnotherSessionProgresses() async throws {
        try await withStore { context in
            let nonconsumer = try await create(context, fixture: "ready-not-consumed")
            defer { nonconsumer.close() }
            try await assertStartup(nonconsumer)
            try await nonconsumer.enableEffects()
            _ = try await nonconsumer.invoke("run")
            let end = ContinuousClock.now.advanced(by: .seconds(5))
            while nonconsumer.status.yields < 3 {
                guard ContinuousClock.now < end else { throw ReviewFailure.timeout("nonconsuming wake did not yield") }
                try await Task.sleep(for: .milliseconds(2))
            }
            let second = try await create(context, fixture: "single-put")
            defer { second.close() }
            try await assertStartup(second)
            try await second.enableEffects()
            _ = try await second.invoke("run")
            try await waitForStage(second, 2)
            try await waitForExits(second, expected: 1)
            XCTAssertLessThanOrEqual(nonconsumer.status.maximumBatchTurns, 4)
            XCTAssertGreaterThan(nonconsumer.status.yields, 0)
            XCTAssertNil(nonconsumer.status.failure)
            XCTAssertNil(second.status.failure)
            try await closeAndDrain(second)
            try await closeAndDrain(nonconsumer)
        }
    }

    func testUnsuccessfulOriginatingTurnStartsNoConcreteStorageWork() async throws {
        for export in ["enqueueThenTrap", "enqueueThenSpin"] {
            try await withStore { context in
                let session = try await create(context, configuration: .init(fuel: 20000, timeoutMilliseconds: 5000))
                defer { session.close() }
                try await assertStartup(session)
                try await session.enableEffects()
                do { _ = try await session.invoke(export); XCTFail("expected terminal guest failure") }
                catch let error as ExperimentalCapabilityError { XCTAssertEqual(error.nativeStatus, 2) }
                let value = try await context.store.get(KVGetArguments(namespace: "bridge_review", key: "trap_probe"))
                XCTAssertFalse(value.found, "enqueued work must remain turn-transactional until successful return")
                try await closeAndDrain(session)
                XCTAssertEqual(session.status.acceptedCalls, 0)
                XCTAssertEqual(session.status.acknowledgements, 0)
            }
        }
    }
}
