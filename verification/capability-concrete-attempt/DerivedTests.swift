// Appended only to the immutable copied ConcreteAttemptTests.swift so its own
// private fixture helpers stay in the same source file. Each test is isolated.
extension ConcreteAttemptTests {
    func testDerivedSetupTailPinsAfterActualBridgeRetirementAndWaitCancellation() async throws {
        let f = try fixture(), (store,owner,input,signals) = try await selected(f)
        let gate = ConcreteProbeGate(); ConcreteProbeHooks.holdSetup(gate); defer { gate.release() }
        let attempt = try CapabilityConcreteAttempt(consumed: input,installed: f.installed,reservation: owner,signals: signals)
        let pending = Task { try await attempt.construct() }
        try await eventually("derived setup gate not reached") { gate.entered }
        let token = attempt.stop(cause: .cancelled)
        try await eventually("actual bridge did not retire while setup frame held") { ConcreteProbeHooks.observations.bridges == 1 }
        XCTAssertFalse(token.completed); XCTAssertThrowsError(try owner.reserveAdapterGroup())
        let waiting = Task { await token.wait() }
        try await eventually("single retirement waiter not installed") { ConcreteProbeHooks.observations.waiters == 1 }
        let duplicate = await token.wait(); XCTAssertFalse(duplicate)
        waiting.cancel(); let cancelled = await waiting.value; XCTAssertFalse(cancelled)
        XCTAssertFalse(token.completed)
        signals.finishNotifications(); owner.beginClosing(); await store.close(); XCTAssertFalse(owner.isReleased)
        let others = try (0..<(16-CapabilityAttemptReservation.occupiedSlots)).map { _ in try CapabilityAttemptReservation.acquire() }
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots,16); XCTAssertThrowsError(try CapabilityAttemptReservation.acquire())
        gate.release(); do { try await pending.value; XCTFail("stopped held setup succeeded") } catch {}
        try await eventually("logical setup tail did not retire") { token.completed }
        XCTAssertTrue(owner.isReleased); others.forEach { $0.beginClosing() }; try await reopen(f)
    }
    func testDerivedMethodFramePinsAfterActualBridgeRetirement() async throws {
        let f = try fixture(), (store,owner,input,signals) = try await selected(f)
        let attempt = try CapabilityConcreteAttempt(consumed: input,installed: f.installed,reservation: owner,signals: signals)
        try await attempt.construct()
        let gate = ConcreteProbeGate(); ConcreteProbeHooks.holdMethod(gate); defer { gate.release() }
        let pending = Task { try await attempt.startup() }
        try await eventually("derived method frame gate not reached") { gate.entered }
        let token = attempt.stop()
        try await eventually("actual bridge did not retire with method frame held") { ConcreteProbeHooks.observations.bridges == 1 }
        XCTAssertFalse(token.completed); XCTAssertThrowsError(try owner.reserveAdapterGroup())
        let waiting = Task { await token.wait() }
        try await eventually("method retirement waiter not installed") { ConcreteProbeHooks.observations.waiters == 1 }
        signals.finishNotifications(); owner.beginClosing(); await store.close(); XCTAssertFalse(owner.isReleased)
        gate.release(); do { _ = try await pending.value; XCTFail("stopped method returned success") } catch {}
        let retired = await waiting.value; XCTAssertTrue(retired); XCTAssertTrue(token.completed); XCTAssertTrue(owner.isReleased)
        try await reopen(f)
    }
    func testDerivedFailureAfterReturnedKVInitClosesInlineWithoutBridge() async throws {
        let f = try fixture(), (store,owner,input,signals) = try await selected(f)
        ConcreteProbeHooks.failAfterStorage()
        let attempt = try CapabilityConcreteAttempt(consumed: input,installed: f.installed,reservation: owner,signals: signals)
        do { try await attempt.construct(); XCTFail("fixed partial setup fault ignored") }
        catch let error as UpdateError { XCTAssertEqual(error.code,"test.concrete.partial") }
        let retired = await attempt.retirement.wait(); XCTAssertTrue(retired)
        XCTAssertEqual(ConcreteProbeHooks.observations.bridges,0); XCTAssertNil(signals.snapshot.firstBridgeFailure)
        XCTAssertTrue(FileManager.default.fileExists(atPath: f.kvDirectory.path)); try await reopen(f)
        let next = try owner.reserveAdapterGroup(); next.retire(); await close(store,owner,signals)
    }
}
