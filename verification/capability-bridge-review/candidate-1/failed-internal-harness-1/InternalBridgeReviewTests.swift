import Foundation
import XCTest
@testable import MixerCapabilities
@testable import MixerExperimentalCapabilityRuntime

// AUTHORED, UNQUALIFIED. Run only against source copies explicitly produced by
// make-derived-review.py. Events are delayed/ordered; no synthetic successful
// completion is counted as concrete storage or real-network success.
private enum InternalReviewFailure: Error {
    case missingFixture(String)
    case timeout(String)
}

private struct InternalStore: Sendable {
    let directory: URL
    let store: AppPrivateKeyValueStore
}

private func internalFixture(_ name: String) throws -> Data {
    guard let url = Bundle.module.url(forResource: name, withExtension: "wasm", subdirectory: "Fixtures") else {
        throw InternalReviewFailure.missingFixture(name)
    }
    return try Data(contentsOf: url)
}

private func internalPolicy(allow: Bool = true) throws -> CapabilityPolicy {
    let grant = CapabilityGrant(capabilityID: CapabilitySchemas.storageID,
        schemaSHA256: CapabilitySchemas.storageSHA256, permissions: ["storage.appPrivate"], namespaces: ["bridge_review"])
    return try CapabilityPolicy(installed: [grant], manifest: allow ? [grant] : [])
}

private func internalStore(_ body: @Sendable (InternalStore) async throws -> Void) async throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-independent-internal-" + UUID().uuidString)
    let context = try InternalStore(directory: directory, store: AppPrivateKeyValueStore(directory: directory, namespaces: ["bridge_review"]))
    do {
        try await body(context)
        await context.store.close(); try FileManager.default.removeItem(at: directory)
    } catch {
        await context.store.close(); try? FileManager.default.removeItem(at: directory)
        throw error
    }
}

private func internalCreate(_ context: InternalStore, name: String = "single-put", allow: Bool = true,
                            configuration: ExperimentalCapabilityConfiguration = .init(timeoutMilliseconds: 5000),
                            adapters: InstalledCapabilityAdapters? = nil) async throws -> ExperimentalCapabilitySession {
    let construction = try ExperimentalCapabilitySession.prepare(module: internalFixture(name), startupExport: "startup",
        configuration: configuration, policy: internalPolicy(allow: allow), adapters: adapters ?? InstalledCapabilityAdapters(storage: context.store))
    return try await construction.create()
}

private func until(_ label: String, _ predicate: () -> Bool) async throws {
    let end = ContinuousClock.now.advanced(by: .seconds(5))
    while !predicate() {
        guard ContinuousClock.now < end else { throw InternalReviewFailure.timeout(label) }
        try await Task.sleep(for: .milliseconds(2))
    }
}

private func internalRead(_ session: ExperimentalCapabilitySession, offset: UInt32, count: Int) async throws -> Data {
    let end = ContinuousClock.now.advanced(by: .seconds(5))
    while true {
        do { return try await session.readMemory(offset: offset, count: count) }
        catch let error as ExperimentalCapabilityError where error.code == "command_busy" {
            guard ContinuousClock.now < end else { throw InternalReviewFailure.timeout("memory command") }
            try await Task.sleep(for: .milliseconds(2))
        }
    }
}

private func internalWord(_ session: ExperimentalCapabilitySession, _ offset: UInt32) async throws -> UInt32 {
    let bytes = try await internalRead(session, offset: offset, count: 4)
    return bytes.enumerated().reduce(UInt32(0)) { $0 | (UInt32($1.element) << UInt32($1.offset * 8)) }
}

private func internalStage(_ session: ExperimentalCapabilitySession, _ expected: UInt32) async throws {
    let end = ContinuousClock.now.advanced(by: .seconds(5))
    while try await internalWord(session, 0) != expected {
        guard ContinuousClock.now < end else { throw InternalReviewFailure.timeout("guest stage \(expected)") }
        try await Task.sleep(for: .milliseconds(2))
    }
}

private func startInternal(_ session: ExperimentalCapabilitySession) async throws {
    _ = try await session.startup()
    try await session.enableEffects()
}

private func internalDrain(_ session: ExperimentalCapabilitySession) async throws {
    session.close()
    try await until("native/host close and exit join") { session.status.drained }
}

private func firstTicket(_ owner: NativeExitOwner) throws -> NativeTicket {
    guard let ticket = owner.control.withLock({ $0.tickets.compactMap { $0 }.first }) else {
        throw InternalReviewFailure.timeout("registered ticket")
    }
    return ticket
}

final class InternalBridgeReviewTests: XCTestCase, @unchecked Sendable {
    func testEmptyNativeCallPayloadIsStrictLocalRejectionWithNoIO() async throws {
        // Guest imports reject length0 themselves. A structurally valid empty C
        // Call is injected only in this labelled derived metadata boundary test.
        ReviewBridgeControls.install(.init(emptyTakenPayload: true))
        defer { ReviewBridgeControls.resetAndRelease() }
        try await internalStore { context in
            let session = try await internalCreate(context)
            defer { session.close() }
            try await startInternal(session)
            _ = try await session.invoke("run")
            try await internalStage(session, 2)
            try await until("local no-I/O acknowledgement") { session.status.acknowledgements == 1 }
            let count = try await internalWord(session, 68)
            let raw = try await internalRead(session, offset: 4096, count: Int(count))
            XCTAssertEqual(try GuestCapabilityTransportCodecV1.decodeCompletion(raw, expectedOperation: .storagePut), .rejected(.invalidArguments))
            XCTAssertEqual(ReviewBridgeControls.starts, 0)
            let value = try await context.store.get(KVGetArguments(namespace: "bridge_review", key: "alpha"))
            XCTAssertFalse(value.found)
            XCTAssertNil(session.status.failure)
            try await internalDrain(session)
        }
    }

    func testRealCallbacksRemainTentativeUntilAcceptanceIsPublished() async throws {
        let gate = ReviewAsyncGate()
        ReviewBridgeControls.install(.init(acceptancePublish: gate))
        defer { ReviewBridgeControls.resetAndRelease() }
        try await internalStore { context in
            let session = try await internalCreate(context, allow: false)
            defer { session.close(); gate.open() }
            try await startInternal(session)
            _ = try await session.invoke("run")
            try await until("observed-submit acceptance gate") { gate.entered == 1 }
            let ticket = try firstTicket(session.reviewExitOwner)
            let snapshot = ticket.state.withLock { $0 }
            XCTAssertTrue(snapshot.callbackReceived)
            XCTAssertTrue(snapshot.exitObserved)
            XCTAssertNil(snapshot.accepted)
            XCTAssertTrue(snapshot.workerRunning)
            XCTAssertFalse(snapshot.resultHandled)
            XCTAssertFalse(snapshot.acknowledged)
            XCTAssertEqual(session.status.acknowledgements, 0)
            let stage = try await internalWord(session, 0)
            XCTAssertEqual(stage, 1)
            gate.open()
            try await internalStage(session, 2)
            try await until("one acknowledgement") { session.status.acknowledgements == 1 }
            XCTAssertNil(session.status.failure)
            try await internalDrain(session)
        }
    }

    func testQueuedWorkerCanStartOnlyOnceAcrossOtherPumpSignals() async throws {
        let gate = ReviewAsyncGate()
        ReviewBridgeControls.install(.init(workerStart: gate))
        defer { ReviewBridgeControls.resetAndRelease() }
        try await internalStore { context in
            let session = try await internalCreate(context)
            defer { session.close(); gate.open() }
            try await startInternal(session)
            _ = try await session.invoke("run")
            try await until("worker start") { gate.entered >= 1 }
            let owner = session.reviewExitOwner
            for _ in 0..<16 { owner.signal(); try await Task.sleep(for: .milliseconds(2)) }
            XCTAssertEqual(ReviewBridgeControls.starts, 1)
            let ticket = try firstTicket(owner)
            let snapshot = ticket.state.withLock { $0 }
            XCTAssertTrue(snapshot.admissionStarted)
            XCTAssertTrue(snapshot.workerRunning)
            XCTAssertNotNil(snapshot.typedOperation)
            XCTAssertNil(snapshot.expected)
            let before = try await context.store.get(KVGetArguments(namespace: "bridge_review", key: "alpha"))
            XCTAssertFalse(before.found)
            gate.open()
            try await internalStage(session, 2)
            try await until("one actual exit") { session.status.acknowledgements == 1 }
            XCTAssertEqual(ReviewBridgeControls.starts, 1)
            XCTAssertNil(session.status.failure)
            try await internalDrain(session)
        }
    }

    func testExitBeforeForwardedRealResultDoesNotAcknowledgeEarly() async throws {
        ReviewBridgeControls.install(.init(holdDelivery: true))
        defer { ReviewBridgeControls.resetAndRelease() }
        try await internalStore { context in
            let session = try await internalCreate(context)
            defer { session.close(); ReviewBridgeControls.releaseDelivery() }
            try await startInternal(session)
            _ = try await session.invoke("run")
            try await until("captured real result and actual exit") {
                guard ReviewBridgeControls.holdingDelivery,
                      let ticket = session.reviewExitOwner.control.withLock({ $0.tickets.compactMap { $0 }.first }) else { return false }
                return ticket.state.withLock { $0.exitObserved && $0.accepted == true && !$0.workerRunning }
            }
            XCTAssertEqual(session.status.acknowledgements, 0)
            let stage = try await internalWord(session, 0)
            XCTAssertEqual(stage, 1)
            ReviewBridgeControls.releaseDelivery()
            try await internalStage(session, 2)
            try await until("post decision before ack") { session.status.acknowledgements == 1 }
            XCTAssertNil(session.status.failure)
            try await internalDrain(session)
        }
    }

    func testForwardedRealResultBeforeExitKeepsNativeOwnership() async throws {
        ReviewBridgeControls.install(.init(holdExit: true))
        defer { ReviewBridgeControls.resetAndRelease() }
        try await internalStore { context in
            let session = try await internalCreate(context)
            defer { session.close(); ReviewBridgeControls.releaseExit() }
            try await startInternal(session)
            _ = try await session.invoke("run")
            try await internalStage(session, 2)
            XCTAssertTrue(ReviewBridgeControls.holdingExit)
            XCTAssertEqual(session.status.acknowledgements, 0)
            XCTAssertEqual(session.status.retainedExits, 1)
            let actual = try await context.store.get(KVGetArguments(namespace: "bridge_review", key: "alpha"))
            XCTAssertEqual(actual, KVGetResponse(found: true, valueBase64: "AAECA//+gA=="))
            ReviewBridgeControls.releaseExit()
            try await until("delayed exit acknowledged") { session.status.acknowledgements == 1 }
            XCTAssertNil(session.status.failure)
            try await internalDrain(session)
        }
    }

    func testNoResultReachesExpiryThenLatePayloadCannotRefillTombstone() async throws {
        ReviewBridgeControls.install(.init(holdDelivery: true))
        defer { ReviewBridgeControls.resetAndRelease() }
        try await internalStore { context in
            let session = try await internalCreate(context, configuration: .init(timeoutMilliseconds: 200))
            defer { session.close(); ReviewBridgeControls.releaseDelivery() }
            try await startInternal(session)
            _ = try await session.invoke("run")
            try await until("held real completion") { ReviewBridgeControls.holdingDelivery }
            try await internalStage(session, 2)
            try await until("actual exit plus expiry decision") { session.status.acknowledgements == 1 }
            let length = try await internalWord(session, 68)
            let raw = try await internalRead(session, offset: 4096, count: Int(length))
            XCTAssertEqual(try GuestCapabilityTransportCodecV1.decodeCompletion(raw, expectedOperation: .storagePut), .failure(.deadlineExceeded))
            let ticket = try firstTicket(session.reviewExitOwner)
            ReviewBridgeControls.releaseDelivery()
            session.reviewExitOwner.signal()
            try await Task.sleep(for: .milliseconds(30))
            XCTAssertNil(ticket.state.withLock { $0.callback })
            XCTAssertEqual(session.status.retainedPayloadBytes, 0)
            XCTAssertNil(session.status.failure)
            try await internalDrain(session)
        }
    }

    func testCloseAfterEightRawTakesProgressesAfterTwoExhaustedBudgets() async throws {
        let gate = ReviewSyncGate()
        ReviewBridgeControls.install(.init(afterDrain: gate, expireScans: 2))
        defer { ReviewBridgeControls.resetAndRelease() }
        try await internalStore { context in
            let session = try await internalCreate(context, name: "burst-eight", configuration: .init(timeoutMilliseconds: 5000, batchMilliseconds: 1))
            defer { session.close(); gate.open() }
            try await startInternal(session)
            _ = try await session.invoke("run")
            try await until("eight registered raw takes") { gate.entered == 1 }
            let tickets = session.reviewExitOwner.control.withLock { $0.tickets.compactMap { $0 } }
            XCTAssertEqual(tickets.count, 8)
            XCTAssertTrue(tickets.allSatisfy { $0.state.withLock { !$0.admissionStarted && !$0.workerRunning && $0.accepted == nil } })
            session.close()
            try await until("both close jobs signalled before gate opens") { ReviewBridgeControls.closeSignals == 2 }
            gate.open()
            try await internalDrain(session)
            XCTAssertFalse(gate.timedOut)
            XCTAssertGreaterThanOrEqual(ReviewBridgeControls.scans, 3)
            XCTAssertEqual(session.status.acknowledgements, 8)
            let value = try await context.store.get(KVGetArguments(namespace: "bridge_review", key: "alpha"))
            XCTAssertFalse(value.found)
        }
    }

    func testTakeReturningAfterCloseRegistersOnlyLocalNoIOExit() async throws {
        let gate = ReviewSyncGate()
        ReviewBridgeControls.install(.init(lateTake: gate))
        defer { ReviewBridgeControls.resetAndRelease() }
        try await internalStore { context in
            let session = try await internalCreate(context)
            defer { session.close(); gate.open() }
            try await startInternal(session)
            _ = try await session.invoke("run")
            try await until("successful native take paused before Swift registration") { gate.entered == 1 }
            session.close()
            try await until("close completed outside blocked guest executor") { ReviewBridgeControls.closeSignals == 2 }
            gate.open()
            try await internalDrain(session)
            XCTAssertFalse(gate.timedOut)
            XCTAssertEqual(session.status.acknowledgements, 1)
            XCTAssertEqual(ReviewBridgeControls.starts, 0)
            let value = try await context.store.get(KVGetArguments(namespace: "bridge_review", key: "alpha"))
            XCTAssertFalse(value.found)
        }
    }

    func testCloseAfterReservedIDBeforeWaiterPublicationDisposesReservation() async throws {
        let gate = ReviewAsyncGate()
        ReviewBridgeControls.install(.init(reservedID: gate))
        defer { ReviewBridgeControls.resetAndRelease() }
        try await internalStore { context in
            let session = try await internalCreate(context)
            defer { session.close(); gate.open() }
            try await startInternal(session)
            _ = try await session.invoke("run")
            try await until("host ID recorded before waiter publication") { gate.entered == 1 }
            let ticket = try firstTicket(session.reviewExitOwner)
            let before = ticket.state.withLock { $0 }
            XCTAssertNotNil(before.expected)
            XCTAssertNil(before.envelopeWaiter)
            XCTAssertNil(before.accepted)
            XCTAssertTrue(before.workerRunning)
            session.close()
            try await until("host and C close signalled") { ReviewBridgeControls.closeSignals == 2 }
            gate.open()
            try await internalDrain(session)
            XCTAssertEqual(session.status.acknowledgements, 1)
            XCTAssertTrue(ticket.state.withLock { $0.reservationDisposed && $0.localExit && $0.accepted == false && !$0.workerRunning })
            let actual = try await context.store.get(KVGetArguments(namespace: "bridge_review", key: "alpha"))
            XCTAssertFalse(actual.found)
        }
    }

    func testCloseBeforeEnvelopeWaiterResumesCannotAdmitIO() async throws {
        let gate = ReviewSyncGate()
        ReviewBridgeControls.install(.init(envelopeResume: gate))
        defer { ReviewBridgeControls.resetAndRelease() }
        try await internalStore { context in
            let session = try await internalCreate(context)
            defer { session.close(); gate.open() }
            try await startInternal(session)
            _ = try await session.invoke("run")
            try await until("encoded envelope before waiter resumption") { gate.entered == 1 }
            let ticket = try firstTicket(session.reviewExitOwner)
            XCTAssertNotNil(ticket.state.withLock { $0.expected })
            XCTAssertNil(ticket.state.withLock { $0.accepted })
            session.close()
            try await until("off-executor native and host close") { ReviewBridgeControls.closeSignals == 2 }
            gate.open()
            try await internalDrain(session)
            XCTAssertFalse(gate.timedOut)
            XCTAssertEqual(session.status.acknowledgements, 1)
            XCTAssertTrue(ticket.state.withLock { $0.localExit && $0.reservationDisposed && $0.accepted == false })
            let actual = try await context.store.get(KVGetArguments(namespace: "bridge_review", key: "alpha"))
            XCTAssertFalse(actual.found)
        }
    }

    func testConcreteStorageExitOwnerSurvivesPublicCloseAndDeinit() async throws {
        // SDK-only scheduling control on the REAL concrete store. No held event
        // in ReviewBridgeControls may artificially retain the owner in this case.
        ReviewBridgeControls.install(.init())
        defer { ReviewBridgeControls.resetAndRelease() }
        let gate = ReviewAsyncGate()
        defer { gate.open() }
        try await internalStore { context in
            let adapters = InstalledCapabilityAdapters(storage: context.store,
                hooks: InstalledCapabilityExecutionHooks(beforeInvocation: nil, afterInvocation: { await gate.hold() }))
            var session: ExperimentalCapabilitySession? = try await internalCreate(context, adapters: adapters)
            weak var publicWeak = session
            weak var ownerWeak = session?.reviewExitOwner
            try await startInternal(session!)
            _ = try await session!.invoke("run")
            try await until("concrete store has returned but host join remains gated") { gate.entered == 1 }
            session!.close(); session = nil
            XCTAssertNil(publicWeak)
            XCTAssertNotNil(ownerWeak)
            let module = try internalFixture("single-put"), allowed = try internalPolicy()
            var pending: [ExperimentalCapabilityConstruction] = []
            for _ in 0..<15 {
                pending.append(try ExperimentalCapabilitySession.prepare(module: module, startupExport: "startup",
                    policy: allowed, adapters: InstalledCapabilityAdapters()))
            }
            XCTAssertThrowsError(try ExperimentalCapabilitySession.prepare(module: module, startupExport: "startup",
                policy: allowed, adapters: InstalledCapabilityAdapters())) { error in
                XCTAssertEqual((error as? ExperimentalCapabilityError)?.code, "construction_busy")
            }
            gate.open()
            try await until("exit owner has joined or deinitialized after join") { ownerWeak == nil || ownerWeak?.status.drained == true }
            let final = try ExperimentalCapabilitySession.prepare(module: module, startupExport: "startup",
                policy: allowed, adapters: InstalledCapabilityAdapters())
            pending.append(final)
            // Sixteen real replacement C creations detect a lost old native ack,
            // even if a defective Swift permit happened to have been released.
            var replacements: [ExperimentalCapabilitySession] = []
            for construction in pending { replacements.append(try await construction.create()) }
            XCTAssertEqual(replacements.count, 16)
            for replacement in replacements { replacement.close() }
            for replacement in replacements { try await internalDrain(replacement) }
        }
    }
}

// Run this fault class in its own filtered process. Conservative metadata-fault
// quarantine is allowed to pin a permit and must not contaminate capacity tests.
final class InternalBridgeMetadataFaultReviewTests: XCTestCase, @unchecked Sendable {
    func testMalformedSuccessfulStartupReportsPermanentlyCloseAttempt() async throws {
        for fault in [ReviewBridgeControls.StartupFault.wrongABI, .invalidI32] {
            ReviewBridgeControls.install(.init(startupFault: fault))
            defer { ReviewBridgeControls.resetAndRelease() }
            try await internalStore { context in
                let session = try await internalCreate(context)
                defer { session.close() }
                do { _ = try await session.startup(); XCTFail("malformed native success metadata must throw") }
                catch let error as ExperimentalCapabilityError {
                    XCTAssertTrue(error.code.hasPrefix("invalid_native_"))
                }
                XCTAssertTrue(session.status.closed, "local metadata failure must synchronously close the attempt")
                do { _ = try await session.invoke("stage"); XCTFail("faulted attempt remained usable") }
                catch let error as ExperimentalCapabilityError { XCTAssertEqual(error.code, "closed") }
                let actual = try await context.store.get(KVGetArguments(namespace: "bridge_review", key: "startup_probe"))
                XCTAssertFalse(actual.found)
            }
        }
    }
}

private final class ModuleBufferRelease: @unchecked Sendable {
    private let lock = NSLock()
    private var value = false
    var released: Bool { lock.lock(); defer { lock.unlock() }; return value }
    func mark() { lock.lock(); value = true; lock.unlock() }
}

private struct ObservedModule: Sendable {
    var data: Data?
    let marker: ModuleBufferRelease
}

private func observedModule() throws -> ObservedModule {
    let raw = try internalFixture("single-put")
    let marker = ModuleBufferRelease()
    let pointer = UnsafeMutableRawPointer.allocate(byteCount: raw.count, alignment: 8)
    raw.withUnsafeBytes { bytes in pointer.copyMemory(from: bytes.baseAddress!, byteCount: bytes.count) }
    let data = Data(bytesNoCopy: pointer, count: raw.count, deallocator: .custom { pointer, _ in
        pointer.deallocate(); marker.mark()
    })
    return ObservedModule(data: data, marker: marker)
}

// Separate filtered process: this deliberately creates ambiguous native reports
// and expects permanent conservative Swift permit quarantine without module data.
final class InternalBridgeConstructorFaultReviewTests: XCTestCase, @unchecked Sendable {
    func testAmbiguousCreateRetainsBudgetButReleasesModuleInputBuffer() async throws {
        let faults: [ReviewBridgeControls.CreateFault] = [.wrongABI, .publishedErrorHandle, .successZeroHandle]
        let allowed = try internalPolicy()
        for (index, fault) in faults.enumerated() {
            ReviewBridgeControls.install(.init(createFault: fault))
            defer { ReviewBridgeControls.resetAndRelease() }
            var observed = try observedModule()
            let release = observed.marker
            let construction = try ExperimentalCapabilitySession.prepare(module: observed.data!, startupExport: "startup",
                policy: allowed, adapters: InstalledCapabilityAdapters())
            observed.data = nil
            XCTAssertFalse(release.released, "prepared construction still owns the input before create")
            do { _ = try await construction.create(); XCTFail("expected ambiguous native creation failure") }
            catch is ExperimentalCapabilityError {}
            try await until("failed create worker relinquishes input Data storage") { release.released }
            var pending: [ExperimentalCapabilityConstruction] = []
            for _ in 0..<(15 - index) {
                pending.append(try ExperimentalCapabilitySession.prepare(module: internalFixture("single-put"), startupExport: "startup",
                    policy: allowed, adapters: InstalledCapabilityAdapters()))
            }
            XCTAssertThrowsError(try ExperimentalCapabilitySession.prepare(module: internalFixture("single-put"), startupExport: "startup",
                policy: allowed, adapters: InstalledCapabilityAdapters())) { error in
                XCTAssertEqual((error as? ExperimentalCapabilityError)?.code, "construction_busy")
            }
            withExtendedLifetime(construction) {}
            pending.removeAll()
        }
    }
}
