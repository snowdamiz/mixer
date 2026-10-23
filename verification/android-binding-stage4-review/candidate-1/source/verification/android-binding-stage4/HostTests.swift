import Foundation
@_spi(GuestUIV1) import MixerGuest
import MixerUI
@testable import MixerCapabilityActivation
import CMixerUITransport
import CMixerUIAndroidHostTest

func require(_ value: @autoclosure () -> Bool, _ message: String, line: Int = #line) {
    guard value() else { fatalError("HOST_FAIL line=\(line) \(message)") }
}
func transport() -> mxuit_snapshot {
    var value = mxuit_snapshot(); require(mxuit_inspect(&value) == 0, "snapshot"); return value
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
@main struct Stage4HostTests {
    static func main() async throws {
        require(mxish_start() == 0, "fixed platform install")
        let scenario = CommandLine.arguments.dropFirst().first ?? "smoke"
        switch scenario {
        case "smoke": try await smoke()
        case "prebind": try await prebind()
        case "task-hold": if #available(macOS 15.0, *) { try await taskHold() } else { fatalError("executor unavailable") }
        case "single-join": try await singleJoin()
        case "destructor": try await destructor()
        case "helper-alias": try await helperAlias()
        case "fallback": try await fallback()
        case "late-before": try await lateBefore()
        case "late-after": try await lateAfter()
        case "after-reclaim": try await afterReclaim()
        case "terminal-capacity": try await terminalCapacity()
        case "failed-retire": try await failedRetire()
        case "missing-native": try await missingNative()
        case "capacity": try await capacity()
        case "facade-acquire-failure": try await facadeAcquireFailure()
        case "endpoint-acquire-failure": try await endpointAcquireFailure()
        case "bind-failure": try await bindFailure()
        case "cancelled-preparation": try await cancelledPreparation()
        case "nested": try await nested()
        case "fault-leave": try await faultLeave()
        case "fault-read": try await faultRead()
        case "fault-write": try await faultWrite()
        case "cleanup-exhaustion": try await cleanupExhaustion()
        case "c-facade-exhaustion": try await cFacadeExhaustion()
        case "cycles": try await cycles()
        default: fatalError("unknown scenario \(scenario)")
        }
        print("HOST_PASS \(scenario)")
    }
    static func smoke() async throws {
        let reservation = try CapabilityAttemptReservation.acquire()
        let prepared = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation: reservation)
        try prepared.transferToBinding()
        let binding = prepared.binding
        let exchange = try frameExchange(101)
        let installation = try await binding.bindHost(exchange)
        reservation.beginClosing()
        let final = await binding.finishFinalClose(using: installation)
        guard case .finished(let receipt) = final else { fatalError("not final \(final)") }
        require(receipt.lastLifetime.taskJoin == .joined, "actual task joined")
        require(receipt.facadeCleanup.facade == binding.facade, "exact facade")
        require(reservation.isReleased, "reservation returned after destructor")
        require(mxish_destructors() == 1 && mxish_live_allocations() == 0, "native resources destroyed")
        require(transport().occupied == 0 && transport().occupied_facades == 0, "C reclaimed")
        require(transport().owned_fds == 2 && transport().registration == 1, "process baseline")
    }
}

private final class WeakResource {
    weak var resource: CapabilityGuestUIAndroidResources?
    init(_ resource: CapabilityGuestUIAndroidResources?) { self.resource = resource }
}
private struct Owner {
    let reservation: CapabilityAttemptReservation
    let prepared: CapabilityAndroidHostPreparedPresentation
    var binding: CapabilityGuestUIAndroidBinding { prepared.binding }
}
private func owner() async throws -> Owner {
    let reservation = try CapabilityAttemptReservation.acquire()
    let prepared = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation: reservation)
    try prepared.transferToBinding()
    return Owner(reservation: reservation, prepared: prepared)
}
private func waitUntil(_ predicate: () -> Bool) async throws {
    let deadline = ContinuousClock.now + .seconds(8)
    while !predicate() {
        require(ContinuousClock.now < deadline, "test observation deadline")
        await Task.yield()
    }
}
private func record(_ facade: UInt64) -> CapabilityAndroidFacadeRecord {
    for i in 0..<16 { if let r = CapabilityAndroidRegistry.shared.record(slot: i, facade: facade) { return r } }
    fatalError("missing record")
}
private final class DropOwner: @unchecked Sendable {
    private let lock = NSLock()
    private var value = false
    var dropped: Bool { lock.lock(); defer { lock.unlock() }; return value }
    func mark() { lock.lock(); value = true; lock.unlock() }
}
private final class AdapterResource: @unchecked Sendable {
    let marker: DropOwner
    init(_ marker: DropOwner) { self.marker = marker }
    deinit { marker.mark() }
}
private func holdAdapter(_ obligation: CapabilityAdapterObligation, marker: DropOwner) throws {
    try obligation.retainOwner(AdapterResource(marker))
}
extension Stage4HostTests {
    static func prebind() async throws {
        let o = try await owner(); o.reservation.beginClosing()
        require(transport().occupied == 1 && transport().requests == 0, "one parked prebind task")
        guard case .finished(let final) = await o.binding.finishFinalClose(using: nil) else { fatalError("prebind close") }
        require(final.lastLifetime.key.endpoint > 0 && final.lastLifetime.taskJoin == .joined, "prebind actual task")
        require(o.reservation.isReleased && mxish_destructors() == 1, "prebind destructor")
    }
    @available(macOS 15.0, *)
    static func taskHold() async throws {
        let executor = HoldingExecutor()
        let o = try await withTaskExecutorPreference(executor) { try await owner() }
        require(executor.totalJobs > 0, "actual inherited executor used")
        executor.pause(); mxish_pause()
        o.binding.requestFinalClose(.closed); o.reservation.beginClosing()
        let finish = Task { await o.binding.finishFinalClose(using: nil) }
        mxish_resume()
        FileHandle.standardOutput.write(Data(("TASK_HOLD phase1 jobs=\(executor.totalJobs) held=\(executor.heldJobs)" + "\n").utf8))
        try await waitUntil { executor.heldJobs > 0 }
        FileHandle.standardOutput.write(Data(("TASK_HOLD phase2 jobs=\(executor.totalJobs) held=\(executor.heldJobs)" + "\n").utf8))
        executor.runOneAndPause()
        let endpoint = record(o.binding.facade).withLock { $0.endpoint }
        FileHandle.standardOutput.write(Data(("TASK_HOLD phase3 endpoint=\(endpoint) jobs=\(executor.totalJobs) held=\(executor.heldJobs)" + "\n").utf8))
        try await waitUntil {
            var value = mxuit_owner_snapshot()
            return mxuit_inspect_owner(endpoint, &value) == 0 && value.retirement_done == 1 && executor.heldJobs > 0
        }
        var held = mxuit_owner_snapshot(); require(mxuit_inspect_owner(endpoint, &held) == 0, "real terminal endpoint")
        require(held.consumer_joined == 0 && transport().occupied == 1 && !o.reservation.isReleased && o.binding.finalStatus == .pending,
            "successful RETIRE cannot substitute for actual Task return")
        executor.resume()
        let result = await finish.value
        guard case .finished = result else { fatalError("actual task close \(result)") }
        require(o.reservation.isReleased, "Task.value completed")
    }
    static func singleJoin() async throws {
        let o = try await owner()
        let exchange = try frameExchange(201)
        let installation = try await o.binding.bindHost(exchange)
        require(mxish_set_hold(5, o.binding.facade) == 0, "hold retire")
        installation.requestStop(.closed)
        let first = Task { await installation.finish() }
        require(mxish_wait_hold() == 0, "real RETIRE held")
        await withTaskGroup(of: CapabilityAndroidHostJoinStatus.self) { group in
            for _ in 0..<64 { group.addTask { await installation.finish() } }
            for await value in group {
                require(value == .pending || value == .invariant(.wrongJoinOwner), "one join authority")
            }
        }
        require(transport().occupied == 1, "held endpoint cannot reclaim")
        mxish_release_hold()
        let receipt = await first.value
        guard case .finished(.retired) = receipt else { fatalError("first retirement \(receipt)") }
        let repeated = await installation.finish(); require(repeated == receipt, "exact immutable readback")
        o.reservation.beginClosing()
        guard case .finished = await o.binding.finishFinalClose(using: nil) else { fatalError("final") }
        require(o.reservation.isReleased, "released")
    }
    static func destructor() async throws {
        let o = try await owner(); let r = record(o.binding.facade)
        let weakResource = WeakResource(r.resources)
        require(weakResource.resource != nil, "actual reservation-owned resource exists")
        require(mxish_set_hold(7, o.binding.facade) == 0, "hold actual destructor")
        o.reservation.beginClosing()
        let final = Task { await o.binding.finishFinalClose(using: nil) }
        require(mxish_wait_hold() == 0, "inside actual deinit")
        require(!o.reservation.isReleased && CapabilityAttemptReservation.occupiedSlots == 1, "destructor pins capacity")
        require(transport().occupied_facades == 0 && transport().occupied == 0, "C already reclaimed")
        require(o.binding.finalStatus == .pending && mxish_destructors() == 0, "no final receipt before deinit returned")
        mxish_release_hold()
        guard case .finished = await final.value else { fatalError("final after destructor") }
        require(weakResource.resource == nil && o.reservation.isReleased && mxish_destructors() == 1, "actual weak nil and capacity")
        withExtendedLifetime(o.prepared) {}
    }
    static func helperAlias() async throws {
        let o = try await owner()
        require(mxish_set_hold(3, o.binding.facade) == 0, "hold apply")
        let installation = try await o.binding.bindHost(frameExchange(301))
        require(mxish_wait_hold() == 0, "actual leased inner helper")
        let r = record(o.binding.facade)
        require(r.withLock { $0.uiAliases == 1 && $0.setupAliases == 0 }, "counted synchronous UI alias")
        o.reservation.beginClosing()
        let final = Task { await o.binding.finishFinalClose(using: installation) }
        try await waitUntil { r.withLock { $0.closing } }
        require(!o.reservation.isReleased && transport().active_entry_serial != 0, "actual helper pins resources")
        mxish_release_hold()
        guard case .finished = await final.value else { fatalError("helper final") }
        require(o.reservation.isReleased, "helper really returned before final")
    }
    static func fallback() async throws {
        let o = try await owner(); let adapter = try o.reservation.reserveAdapterGroup(); let marker = DropOwner()
        try holdAdapter(adapter, marker: marker)
        let first = try await o.binding.bindHost(frameExchange(401))
        first.requestStop(.closed)
        let old = await first.finish()
        guard case .finished(.retired(let a)) = old else { fatalError("old") }
        let next = try await o.binding.bindHost(frameExchange(402))
        require(next.key.endpoint != a.key.endpoint && next.key.lifetime != a.key.lifetime, "fresh endpoint/lifetime")
        let repeated = await first.finish(); require(repeated == old, "old result after reuse")
        o.reservation.beginClosing()
        guard case .finished(let final) = await o.binding.finishFinalClose(using: next) else { fatalError("fallback close") }
        require(final.lastLifetime.key == next.key && !o.reservation.isReleased, "independent adapter obligation pins")
        require(!marker.dropped, "adapter still retained")
        adapter.retire(); require(marker.dropped && o.reservation.isReleased, "actual adapter destruction")
    }
    static func lateBefore() async throws {
        let o = try await owner(); require(mxish_set_hold(2, o.binding.facade) == 0, "hold before decision")
        let first = try await o.binding.bindHost(frameExchange(501)); first.requestStop(.closed)
        let finish = Task { await first.finish() }
        require(mxish_wait_hold() == 0, "native inspection before retire decision")
        o.binding.requestFinalClose(.closed); o.reservation.beginClosing(); mxish_release_hold()
        guard case .finished(.retired(let receipt)) = await finish.value else { fatalError("late before") }
        require(receipt.facadeCleanup != nil, "same exact helper final clear")
        guard case .finished = await o.binding.finishFinalClose(using: nil) else { fatalError("final") }
        require(transport().owners_issued == 1, "no extra terminal")
    }
    static func lateAfter() async throws {
        let o = try await owner(); require(mxish_set_hold(5, o.binding.facade) == 0, "hold after decision")
        let first = try await o.binding.bindHost(frameExchange(502)); first.requestStop(.closed)
        let finish = Task { await first.finish() }
        require(mxish_wait_hold() == 0, "actual final=0 helper")
        o.binding.requestFinalClose(.closed); o.reservation.beginClosing(); mxish_release_hold()
        guard case .finished(.retired(let old)) = await finish.value else { fatalError("old") }
        require(old.facadeCleanup == nil, "nonfinal cannot issue final evidence")
        guard case .finished(let final) = await o.binding.finishFinalClose(using: nil) else { fatalError("terminal final") }
        require(final.lastLifetime.key.endpoint != old.key.endpoint && transport().owners_issued == 2, "one fresh terminal")
    }
    static func afterReclaim() async throws {
        let o = try await owner(); let first = try await o.binding.bindHost(frameExchange(503))
        first.requestStop(.closed)
        guard case .finished(.retired(let old)) = await first.finish() else { fatalError("old") }
        require(old.facadeCleanup == nil && transport().occupied == 0, "between attempts")
        o.reservation.beginClosing(); o.binding.requestFinalClose(.closed)
        guard case .finished(let final) = await o.binding.finishFinalClose(using: nil) else { fatalError("terminal") }
        require(final.lastLifetime.key.endpoint != old.key.endpoint && transport().owners_issued == 2, "terminal after endpoint absence")
        do { _ = try await o.binding.bindHost(frameExchange(504)); fatalError("reopened") } catch {}
        require(transport().occupied == 0 && o.reservation.isReleased, "closed scalar shell")
    }
    static func terminalCapacity() async throws {
        let o = try await owner(); let first = try await o.binding.bindHost(frameExchange(601)); first.requestStop(.closed)
        guard case .finished(.retired) = await first.finish() else { fatalError("first") }
        for _ in 0..<16 { var id: UInt64 = 0; require(mxuit_acquire(&id) == 0 && id > 0, "real C exhaustion") }
        o.reservation.beginClosing()
        let result = await o.binding.finishFinalClose(using: nil)
        guard case .quarantined = result else { fatalError("terminal capacity must pin") }
        require(!o.reservation.isReleased && o.reservation.isQuarantined && mxish_live_allocations() > 0, "resource pinned")
        let repeated = await o.binding.finishFinalClose(using: nil); require(repeated == result, "immutable failure no retry")
    }
    static func failedRetire() async throws {
        let o = try await owner(); mxish_fail_retire(o.binding.facade)
        o.reservation.beginClosing()
        guard case .quarantined = await o.binding.finishFinalClose(using: nil) else { fatalError("retire must fail") }
        var snapshot = mxuit_owner_snapshot(); let r = record(o.binding.facade)
        let endpoint = r.withLock { $0.endpoint }; require(mxuit_inspect_owner(endpoint, &snapshot) == 0, "still pinned")
        require(snapshot.consumer_joined == 0 && !o.reservation.isReleased && r.withLock { $0.cleanup == nil }, "no fake join/cleanup")
    }
    static func missingNative() async throws {
        let o = try await owner(); require(mxish_set_hold(3, o.binding.facade) == 0, "hold apply")
        let first = try await o.binding.bindHost(frameExchange(602)); require(mxish_wait_hold() == 0, "published slot")
        mxish_lose_owner(o.binding.facade); mxish_release_hold()
        try await waitUntil { transport().completions > 0 }
        o.reservation.beginClosing()
        guard case .quarantined = await o.binding.finishFinalClose(using: first) else { fatalError("missing native must pin") }
        require(!o.reservation.isReleased && record(o.binding.facade).withLock { $0.cleanup == nil }, "missing is not empty")
    }
    static func capacity() async throws {
        var all: [Owner] = []
        for _ in 0..<16 { all.append(try await owner()) }
        require(transport().occupied == 16 && transport().occupied_facades == 16 && transport().requests == 0, "all fixed reserved/published")
        do { _ = try CapabilityAndroidRegistry.shared.acquireFacade(); fatalError("seventeenth admitted") } catch {}
        require(transport().facades_issued == 16, "Swift rejects before C issue")
        for o in all {
            o.reservation.beginClosing()
            guard case .finished = await o.binding.finishFinalClose(using: nil) else { fatalError("capacity cleanup") }
        }
        require(CapabilityAttemptReservation.occupiedSlots == 0 && mxish_live_allocations() == 0, "all reclaimed")
    }
    static func facadeAcquireFailure() async throws {
        for _ in 0..<16 { var id: UInt64 = 0; require(mxuit_facade_acquire(&id) == 0, "fill actual C facade slots") }
        let reservation = try CapabilityAttemptReservation.acquire()
        do { _ = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation: reservation); fatalError("must reject") } catch {}
        reservation.beginClosing(); require(reservation.isReleased && transport().occupied == 0, "proven empty rollback")
    }
    static func endpointAcquireFailure() async throws {
        for _ in 0..<16 { var id: UInt64 = 0; require(mxuit_acquire(&id) == 0, "fill actual endpoints") }
        let reservation = try CapabilityAttemptReservation.acquire()
        do { _ = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation: reservation); fatalError("must reject") } catch {}
        reservation.beginClosing()
        require(reservation.isQuarantined && !reservation.isReleased && transport().occupied_facades == 1, "live facade/resource uncertainty pinned")
        require(transport().requests == 0, "no nonexistent consumer")
    }
    static func bindFailure() async throws {
        let o = try await owner(); let exchange = try frameExchange(701)
        let reader = try exchange.deliveryWake.takeConsumer()
        do { _ = try await o.binding.bindHost(exchange); fatalError("duplicate reader") } catch {}
        require(exchange.snapshot().stop != nil && transport().occupied == 0, "same local installation joined on failure")
        o.reservation.beginClosing()
        guard case .finished = await o.binding.finishFinalClose(using: nil) else { fatalError("bind failure final") }
        withExtendedLifetime(reader) {}
    }
    static func cancelledPreparation() async throws {
        let reservation = try CapabilityAttemptReservation.acquire()
        let task = Task { try await CapabilityGuestUIAndroidBinding.prepareHost(reservation: reservation) }
        task.cancel()
        do { _ = try await task.value; fatalError("cancel ignored") } catch {}
        reservation.beginClosing()
        require(reservation.isReleased && !reservation.isQuarantined && transport().occupied == 0 && transport().occupied_facades == 0, "same preparation frame explicitly joined cleanup")
    }
    static func nested() async throws {
        let o = try await owner(); mxish_nested(o.binding.facade)
        let first = try await o.binding.bindHost(frameExchange(801))
        try await waitUntil { mxish_nested_checks() > 0 }
        require(transport().fault == 0, "nested callback rejected before failed-event handling")
        require(mxuit_ui_validate(o.binding.facade, 1) == 9, "wrong UI thread rejects")
        o.reservation.beginClosing()
        guard case .finished = await o.binding.finishFinalClose(using: first) else { fatalError("nested close") }
    }
    static func faultLeave() async throws {
        let a = try await owner(); let b = try await owner(); let c = try await owner()
        require(mxish_set_hold(3, c.binding.facade) == 0, "hold native helper before leave")
        let xb = try frameExchange(901); let ib = try await b.binding.bindHost(xb)
        try await waitUntil { transport().completions > 0 }
        let xc = try frameExchange(902); let ic = try await c.binding.bindHost(xc)
        require(mxish_wait_hold() == 0, "actual C active entry")
        require(mxish_inject_syscall(4) == 0, "actual leave write fault")
        mxish_release_hold()
        try await waitUntil { transport().fault != 0 }
        for (o, i) in [(a, Optional<CapabilityAndroidHostInstallation>.none),(b, ib),(c,ic)] {
            o.reservation.beginClosing()
            guard case .quarantined = await o.binding.finishFinalClose(using: i) else { fatalError("fault fanout") }
            require(!o.reservation.isReleased, "fault pins all wait states")
        }
        require(xb.snapshot().stop != nil && xc.snapshot().stop != nil, "delivery and rendezvous stop")
    }
    static func faultRead() async throws {
        let o = try await owner(); mxish_pause(); require(mxish_inject_syscall(3) == 0, "real callback read failure")
        let first = try await o.binding.bindHost(frameExchange(903)); mxish_resume()
        try await waitUntil { transport().fault != 0 }
        o.reservation.beginClosing()
        guard case .quarantined = await o.binding.finishFinalClose(using: first) else { fatalError("read pins") }
    }
    static func faultWrite() async throws {
        let o = try await owner(); mxish_pause(); require(mxish_inject_syscall(4) == 0, "real worker write failure")
        let first = try await o.binding.bindHost(frameExchange(904))
        try await waitUntil { transport().fault != 0 }
        o.reservation.beginClosing()
        guard case .quarantined = await o.binding.finishFinalClose(using: first) else { fatalError("write pins") }
    }
    static func cleanupExhaustion() async throws {
        let o = try await owner(); let r = record(o.binding.facade)
        r.withLock { $0.cleanupSerial = .max } // Failure-only test control; cannot mint evidence.
        o.reservation.beginClosing()
        guard case .quarantined = await o.binding.finishFinalClose(using: nil) else { fatalError("no cleanup wrap") }
        require(r.withLock { $0.cleanupSerial == .max && $0.cleanup == nil }, "no synthetic serial/evidence")
    }
    static func cFacadeExhaustion() async throws {
        require(mxish_set_c_counter(2, UInt64(Int64.max)) == 0, "real checked facade counter")
        let reservation = try CapabilityAttemptReservation.acquire()
        do { _ = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation: reservation); fatalError("exhausted") } catch {}
        reservation.beginClosing(); require(reservation.isReleased && transport().occupied_facades == 0, "empty exhaustion rollback")
    }
    static func cycles() async throws {
        for _ in 0..<64 {
            let o = try await owner(); let a = try await o.binding.bindHost(frameExchange(1001)); a.requestStop(.closed)
            guard case .finished(.retired) = await a.finish() else { fatalError("cycle first") }
            let b = try await o.binding.bindHost(frameExchange(1002)); o.reservation.beginClosing()
            guard case .finished = await o.binding.finishFinalClose(using: b) else { fatalError("cycle final") }
            require(o.reservation.isReleased && transport().occupied == 0 && transport().occupied_facades == 0, "bounded cycle")
        }
        let s = transport()
        require(s.owned_fds == 2 && s.registration == 1 && s.maximum_occupied <= 1 && s.maximum_waiters <= 1, "fixed baseline no owner FDs/threads")
        require(mxish_live_allocations() == 0 && mxish_destructors() == 64, "no growing host resources")
    }
}
