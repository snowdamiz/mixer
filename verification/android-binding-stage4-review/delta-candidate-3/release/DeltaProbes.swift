import Foundation
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation
import CMixerUITransport
import CMixerUIAndroidHostTest

private func ensure(_ value: @autoclosure () -> Bool, _ message: String) {
    if !value() { fatalError("DELTA_FAIL \(message)") }
}
private func transportState() -> mxuit_snapshot {
    var s = mxuit_snapshot(); ensure(mxuit_inspect(&s) == 0, "real transport snapshot"); return s
}
private func lookup(_ facade: UInt64) -> (Int, CapabilityAndroidFacadeRecord) {
    for index in 0..<16 {
        if let r = CapabilityAndroidRegistry.shared.record(slot: index, facade: facade) { return (index,r) }
    }
    fatalError("facade record missing")
}
private struct Owner {
    let reservation: CapabilityAttemptReservation
    let prepared: CapabilityAndroidHostPreparedPresentation
    var binding: CapabilityGuestUIAndroidBinding { prepared.binding }
}
private func prepare() async throws -> Owner {
    let reservation = try CapabilityAttemptReservation.acquire()
    let prepared = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation: reservation)
    try prepared.transferToBinding()
    return Owner(reservation: reservation, prepared: prepared)
}
private func eventual(_ predicate: () -> Bool) async {
    let deadline = ContinuousClock.now + .seconds(8)
    while !predicate() { ensure(ContinuousClock.now < deadline, "bounded test observation"); await Task.yield() }
}
private func exchange(_ generation: UInt64) throws -> GuestUIExchangeV1 {
    let e = try GuestUIExchangeV1(generation: generation)
    let startup = try e.claimStartup()
    try e.finishTurn(startup, documentBytes: Data(#"{"schemaVersion":1,"revision":1,"root":{"id":"review-root","kind":"text","properties":{"text":"Independent final-2 review"},"actions":[],"children":[]}}"#.utf8))
    try e.enterEffectsIntent(generation: generation); try e.confirmEffectsEnabled(generation: generation)
    return e
}
private func leasedRace() async throws {
    let o = try await prepare(), facade = o.binding.facade
    let (slot,r) = lookup(facade)
    let before = transportState()
    ensure(CapabilityGuestUIAndroidResources.scalarEntry(facade: facade, slot: slot, kind: 0) == Int32(MXUIT_WRONG_THREAD.rawValue), "wrong host thread rejected")
    ensure(transportState().ui_entries_issued == before.ui_entries_issued && r.withLock { $0.uiAliases == 0 }, "wrong thread before lease/lookup/alias")
    mxish_pause(); mxish_nested(facade)
    ensure(mxish_call_entry(facade, 3) == 0, "real first CLEANUP lease")
    ensure(mxish_live_allocations() == 3 && mxish_nested_checks() > 0, "real resources and nested callback rejection")
    ensure(mxish_set_hold(4, facade) == 0, "hold actual synchronous helper")
    let ingress = Task.detached { mxish_call_entry(facade, 0) }
    ensure(mxish_wait_hold() == 0, "inside actual INGRESS native helper")
    ensure(r.withLock { $0.uiAliases == 1 && $0.setupAliases == 0 }, "actual UI alias counted")
    ensure(transportState().active_entry_facade == facade, "actual C lease held")
    o.reservation.beginClosing()
    let close = Task { await o.binding.finishFinalClose(using: nil) }
    await eventual { r.withLock { $0.closing } }
    ensure(o.binding.finalStatus == .pending && !o.reservation.isReleased, "helper pins finalizer")
    mxish_release_hold(); let ingressResult = await ingress.value
    ensure(ingressResult == 0, "real inner helper returned")
    ensure(r.withLock { $0.uiAliases == 0 } && transportState().active_entry_serial == 0, "alias released only after inner return and lease leave")
    ensure(mxish_call_entry(facade, 0) == Int32(MXUIT_CLOSED.rawValue), "closing ingress rejected")
    ensure(mxish_call_entry(facade, 3) == 0, "closing CLEANUP still leased")
    ensure(o.binding.finalStatus == .pending && !o.reservation.isReleased, "no callback return fence fabricated")
    mxish_resume()
    guard case .finished = await close.value else { fatalError("leased race finalization") }
    ensure(o.reservation.isReleased && mxish_destructors() == 1, "actual helper/fence/destructor joined")
    ensure(mxish_call_entry(facade, 3) == Int32(MXUIT_STALE.rawValue), "reclaimed facade cannot promote resources")
    print("LEASE_RACE wrong_thread=1 real_ingress_cleanup=1 alias_held=1 late_close=1 actual_destructor=1")
}
private func fallbackIDs() async throws {
    let o = try await prepare(), facade = o.binding.facade
    var maximum: UInt64 = 0
    var previous: CapabilityAndroidHostInstallation?
    for generation in 6001...6003 {
        let installation = try await o.binding.bindHost(exchange(UInt64(generation)))
        await eventual { mxish_last_id(facade, 3) > maximum }
        let ids = (1...3).map { mxish_last_id(facade, UInt32($0)) }
        ensure(ids.allSatisfy { $0 > maximum } && Set(ids).count == 3, "fresh monotonic distinct facade-long tokens")
        maximum = ids.max()!
        installation.requestStop(.closed)
        guard case .finished(.retired) = await installation.finish() else { fatalError("nonfinal exact Task/native join") }
        if let previous { ensure(previous.status != .pending, "old immutable readback survives endpoint reuse") }
        previous = installation
        print("FALLBACK generation=\(generation) IDs=\(ids)")
    }
    o.reservation.beginClosing()
    guard case .finished = await o.binding.finishFinalClose(using: nil) else { fatalError("sequential terminal finalization") }
    ensure(o.reservation.isReleased && mxish_destructors() == 1, "fallback final owner/destructor")
}
private final class Flag: @unchecked Sendable {
    private let lock = NSLock(); private var state = false
    func set() { lock.lock(); state = true; lock.unlock() }
    var value: Bool { lock.lock(); defer { lock.unlock() }; return state }
}
private func duplicateProgressFanout(retireFirst: Bool = false) async throws {
    let a = try await prepare(), b = try await prepare()
    let aEndpoint = lookup(a.binding.facade).1.withLock { $0.endpoint }
    if retireFirst {
        CapabilityAndroidRegistry.shared.control(owner: aEndpoint)!.requestStop(.closed)
        await eventual {
            var s = mxuit_owner_snapshot()
            return mxuit_inspect_owner(aEndpoint, &s) == 0 && s.retirement_done == 1
        }
    }
    mxish_pause()
    let (slot, ar) = lookup(a.binding.facade), (_, br) = lookup(b.binding.facade)
    let cell = CapabilityAndroidProgress.shared.cells[slot], firstReady = Flag()
    let sequence = cell.snapshot.sequence
    let existing = Task {
        await withCheckedContinuation { (c: CheckedContinuation<Void,Never>) in
            ensure(cell.register(after: sequence, c) != nil, "real first progress continuation")
            firstReady.set()
        }
    }
    await eventual { firstReady.value }
    await withCheckedContinuation { (c: CheckedContinuation<Void,Never>) in
        ensure(cell.register(after: sequence, c) == nil, "duplicate waiter rejected")
        c.resume()
    }
    ensure(cell.snapshot.fault == Int32(MXUIT_INVALID.rawValue), "real duplicate check sets sticky failure")
    // Only a real C callback may drive the checked-fault fanout. No fence or
    // receipt value is written, and no successful join is synthesized here.
    (retireFirst ? b.binding : a.binding).requestFinalClose(.closed); mxish_resume()
    await existing.value
    await eventual { CapabilityAndroidProgress.shared.cells.allSatisfy { $0.snapshot.fault == Int32(MXUIT_INVALID.rawValue) } }
    ensure(ar.withLock { $0.quarantined && $0.closing } && br.withLock { $0.quarantined && $0.closing }, "global admission quarantine before wake")
    ensure(mxish_destructors() == 0 && !a.reservation.isReleased && !b.reservation.isReleased, "fault retains exact resources and capacity")
    do { _ = try CapabilityAndroidRegistry.shared.acquireFacade(); fatalError("fault admitted replacement") } catch {}
    a.reservation.beginClosing(); b.reservation.beginClosing()
    guard case .quarantined = await b.binding.finishFinalClose(using: nil) else { fatalError("other prebind wait fanout") }
    if retireFirst {
        guard case .quarantined = await a.binding.finishFinalClose(using: nil) else { fatalError("late fault must not create receipt") }
        var s = mxuit_owner_snapshot()
        ensure(mxuit_inspect_owner(aEndpoint, &s) == 0, "fault preserves old endpoint")
        print("LATE_PROGRESS_FAULT retirement_done=\(s.retirement_done) consumer_joined=\(s.consumer_joined) final_quarantined=1 endpoint_retained=1")
        if CommandLine.arguments.contains("expect-zero") { ensure(s.consumer_joined == 0, "already-latched control fault cannot assert consumer return") }
    }
    ensure(mxish_destructors() == 0 && CapabilityAttemptReservation.occupiedSlots == 2, "no false resource retirement")
    print("PROGRESS_FANOUT duplicate_origin=1 actual_callback=1 all_16_faulted=1 other_prebind_woken=1 capacity_pinned=2")
}
@main struct DeltaProbes {
    static func main() async throws {
        ensure(mxish_start() == 0, "actual fixed host install")
        switch CommandLine.arguments[1] {
        case "leased-race": try await leasedRace()
        case "fallback-ids": try await fallbackIDs()
        case "duplicate-progress-fanout": try await duplicateProgressFanout()
        case "late-progress-join": try await duplicateProgressFanout(retireFirst: true)
        default: fatalError("unknown delta probe")
        }
        print("DELTA_PROBE_PASS \(CommandLine.arguments[1])")
    }
}
