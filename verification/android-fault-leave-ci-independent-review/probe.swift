import Foundation
@_spi(GuestUIV1) @testable import MixerGuest
import MixerUI
@testable import MixerCapabilityActivation
import CMixerUITransport
import CMixerUIAndroidHostTest

func require(_ value: @autoclosure () -> Bool, _ message: String, line: Int = #line) {
    guard value() else { fatalError("REVIEW_FAIL line=\(line) \(message)") }
}
func transport() -> mxuit_snapshot {
    var value = mxuit_snapshot(); require(mxuit_inspect(&value) == 0, "snapshot"); return value
}
func ownerSnapshot(_ endpoint: UInt64) -> mxuit_owner_snapshot {
    var value = mxuit_owner_snapshot()
    require(mxuit_inspect_owner(endpoint, &value) == 0, "actual endpoint")
    return value
}
func trace(_ phase: String) {
    let s = transport()
    FileHandle.standardOutput.write(Data(("REVIEW_STATE \(phase) epoch=\(s.callback_epoch) callbacks=\(s.callbacks) requests=\(s.requests) completions=\(s.completions) pending=\(s.pending_pipe_hint) active=\(s.callback_active) fault=\(s.fault)\n").utf8))
}
func frameExchange(_ generation: UInt64) throws -> GuestUIExchangeV1 {
    let exchange = try GuestUIExchangeV1(generation: generation)
    let claim = try exchange.claimStartup()
    let bytes = Data(#"{"schemaVersion":1,"revision":1,"root":{"id":"root","kind":"vStack","properties":{},"actions":[],"children":[{"id":"text","kind":"text","properties":{"text":"Host signed UI"},"actions":[],"children":[]},{"id":"save","kind":"button","properties":{"label":"Save"},"actions":[{"id":"save","event":"activate"}],"children":[]}]}}"#.utf8)
    try exchange.finishTurn(claim, documentBytes: bytes)
    try exchange.enterEffectsIntent(generation: generation)
    try exchange.confirmEffectsEnabled(generation: generation)
    return exchange
}
private struct Owner: Sendable {
    let reservation: CapabilityAttemptReservation
    let prepared: CapabilityAndroidHostPreparedPresentation
    var binding: CapabilityGuestUIAndroidBinding { prepared.binding }
    var endpoint: UInt64 {
        for i in 0..<16 {
            if let r = CapabilityAndroidRegistry.shared.record(slot: i, facade: binding.facade) {
                return r.withLock { $0.endpoint }
            }
        }
        fatalError("missing endpoint")
    }
}
private func owner() async throws -> Owner {
    let reservation = try CapabilityAttemptReservation.acquire()
    let prepared = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation: reservation)
    try prepared.transferToBinding()
    return Owner(reservation: reservation, prepared: prepared)
}
private func waitUntil(line: Int = #line, _ predicate: () -> Bool) async throws {
    let deadline = ContinuousClock.now + .seconds(8)
    while !predicate() {
        require(ContinuousClock.now < deadline, "observation deadline", line: line)
        await Task.yield()
    }
}
private func fixedPredicate() -> Bool {
    let snapshot = transport()
    return snapshot.completions > 0 && snapshot.pending_pipe_hint == 0 && snapshot.callback_active == 0
}
@main struct Review {
    static func main() async throws {
        try await probe()
    }
    static func probe() async throws {
        require(mxish_start() == 0, "actual fixed host platform")
        let mode = CommandLine.arguments[1]
        require(mode == "old" || mode == "fixed", "mode")
        let old = mode == "old"
        let a = try await owner()
        let b = try await owner()
        let c = try await owner()
        require(mxish_set_hold(3, c.binding.facade) == 0, "same held C apply as original fixture")
        mxish_review_arm_completion(b.endpoint)
        mxish_review_arm_task(b.endpoint)
        let xb = try frameExchange(901); let ib = try await b.binding.bindHost(xb)
        require(mxish_review_wait_completion() == 0, "C count before actual Swift completion")
        let first = transport()
        require(first.completions == 1 && first.pending_pipe_hint == 1 && first.callback_active == 1,
                "actual old-predicate window")
        require(!fixedPredicate(), "fixed wait excludes old window")
        trace("b-completion-barrier")
        let xc = try frameExchange(902)
        let ic: CapabilityAndroidHostInstallation
        if old {
            require(transport().completions > 0, "unchanged old predicate admits c")
            ic = try await c.binding.bindHost(xc)
            try await waitUntil { transport().requests == 2 && ownerSnapshot(c.endpoint).waiter == 1 }
            mxish_review_release_completion()
        } else {
            mxish_review_release_completion()
            try await waitUntil { fixedPredicate() }
            require(mxish_review_wait_task() == 0, "b real resumed task before reading next delivery")
            require(transport().requests == 1, "idle before c with actual b continuation held")
            trace("fixed-idle-b-job-still-held")
            ic = try await c.binding.bindHost(xc)
        }
        require(mxish_wait_hold() == 0, "actual held c apply")
        let held = transport()
        require(held.completions == 1 && held.requests == 2 && held.callback_active == 1,
                "c in actual native helper")
        require(held.pending_pipe_hint == (old ? 1 : 0), "causal pending bit at exact injection point")
        require(old ? held.callback_epoch == first.callback_epoch : held.callback_epoch > first.callback_epoch,
                "old same callback versus fixed later callback")
        require(mxish_review_wait_task() == 0, "b real resumed task before reading next delivery")
        mxish_review_release_task()
        try await waitUntil { xb.deliveryWake.hasWaitingConsumer }
        let parked = ownerSnapshot(b.endpoint)
        require(parked.waiter == 0 && parked.active_helper == 0 && parked.completing == 0,
                "b's delayed actual task parks on delivery without another C request")
        require(transport().requests == 2 && transport().pending_pipe_hint == (old ? 1 : 0),
                "no asynchronous b demand before c leave")
        trace("held-c-b-task-parked")
        require(mxish_inject_syscall(4) == 0, "same real write fault injection as fixture")
        mxish_release_hold()
        var ia: CapabilityAndroidHostInstallation?
        if old {
            try await waitUntil { transport().completions == 2 && transport().pending_pipe_hint == 0 && transport().callback_active == 0 }
            require(transport().fault == 0, "old c leave coalesced and did not consume injected failure")
            try await waitUntil { xc.deliveryWake.hasWaitingConsumer }
            trace("old-idle-no-fault")
            // Trigger an unrelated actual Swift/C transport write. Its fault
            // proves the old schedule left the one-shot injection unconsumed.
            ia = try await a.binding.bindHost(frameExchange(903))
        }
        try await waitUntil { transport().fault != 0 }
        trace(old ? "old-later-real-request-consumed-fault" : "fixed-c-leave-fault")
        for (o, i) in [(a, ia), (b, Optional(ib)), (c, Optional(ic))] {
            o.reservation.beginClosing()
            guard case .quarantined = await o.binding.finishFinalClose(using: i) else { fatalError("original fault fanout") }
            require(!o.reservation.isReleased, "original all-state reservation pinning")
        }
        require(xb.snapshot().stop != nil && xc.snapshot().stop != nil, "original exchange stop assertions")
        print("REVIEW_PASS \(mode) actual-Swift-C delayed-b-task-parked fault-fanout-preserved")
    }
}
