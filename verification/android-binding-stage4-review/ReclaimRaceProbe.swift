import Foundation
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation
import CMixerUITransport
import CMixerUIAndroidHostTest
import MixerReviewReclaimHold

private func require(_ condition: @autoclosure () -> Bool, _ text: String) {
    if !condition() { mxir_release(); fatalError("RECLAIM_RACE_FAIL \(text)") }
}
private func snapshot() -> mxuit_snapshot { var s=mxuit_snapshot(); require(mxuit_inspect(&s)==0,"inspect"); return s }
private func record(_ facade: UInt64) -> (Int,CapabilityAndroidFacadeRecord) {
    for i in 0..<16 { if let r=CapabilityAndroidRegistry.shared.record(slot:i,facade:facade) { return(i,r) } }
    fatalError("missing exact record")
}
private func until(_ predicate: @Sendable () -> Bool) async {
    let deadline=ContinuousClock.now + .seconds(10)
    while !predicate() { require(ContinuousClock.now<deadline,"test observation deadline"); await Task.yield() }
}
private func prepared() async throws -> (CapabilityAttemptReservation,CapabilityAndroidHostPreparedPresentation) {
    let r=try CapabilityAttemptReservation.acquire(), p=try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:r)
    try p.transferToBinding(); return(r,p)
}
private final class Flag: @unchecked Sendable {
    private let lock=NSLock();private var ready=false
    func set(){lock.lock();ready=true;lock.unlock()}
    var value:Bool{lock.lock();defer{lock.unlock()};return ready}
}
@main struct ReclaimRaceProbe {
    static func main() async throws {
        require(mxish_start()==0,"actual fixed UI thread")
        let (ar,ap)=try await prepared(),(br,bp)=try await prepared()
        let (aSlot,aRecord)=record(ap.binding.facade),(bSlot,bRecord)=record(bp.binding.facade)
        let exchange=try GuestUIExchangeV1(generation:9501)
        let startup=try exchange.claimStartup()
        try exchange.finishTurn(startup,documentBytes:Data(#"{"schemaVersion":1,"revision":1,"root":{"id":"race","kind":"text","properties":{"text":"Actual reclaim race"},"actions":[],"children":[]}}"#.utf8))
        try exchange.enterEffectsIntent(generation:9501);try exchange.confirmEffectsEnabled(generation:9501)
        let installation=try await ap.binding.bindHost(exchange), owner=installation.key.endpoint
        installation.requestStop(.closed)
        await until {
            var s=mxuit_owner_snapshot();let global=snapshot()
            return mxuit_inspect_owner(owner,&s)==0 && s.retirement_done==1 && global.fenced_epoch>=s.last_hook_epoch && global.ui_entry_fenced>=s.last_entry_serial
        }
        mxish_pause() // Frozen candidate3 fixture waits actual callback/command return.
        require(mxir_arm(owner)==0,"arm exact old endpoint")
        ar.beginClosing();br.beginClosing()
        let final=Task.detached { await ap.binding.finishFinalClose(using:installation) }
        require(mxir_wait()==0 && mxir_successes()==1,"exact actual C reclaim returned OK once")
        var old=mxuit_owner_snapshot();require(mxuit_inspect_owner(owner,&old)==Int32(MXUIT_STALE.rawValue),"actual C owner is already gone")
        require(aRecord.withLock{$0.endpoint==owner} && installation.status == .pending,"Swift fact not published while original C return held")
        let cell=CapabilityAndroidProgress.shared.cells[bSlot],ready=Flag(),sequence=CapabilityAndroidProgress.shared.cells[bSlot].snapshot.sequence
        let parked=Task.detached { await withCheckedContinuation { (c:CheckedContinuation<Void,Never>) in
            require(cell.register(after:sequence,c) != nil,"actual first progress continuation");ready.set()
        }}
        await until {ready.value}
        await withCheckedContinuation { (c:CheckedContinuation<Void,Never>) in
            require(cell.register(after:sequence,c)==nil && cell.snapshot.fault==Int32(MXUIT_INVALID.rawValue),"real duplicate invariant failure");c.resume()
        }
        let before=cell.snapshot.sequence
        require(mxish_call_entry(bp.binding.facade,4)==0,"actual C-only CLEANUP enter/leave posts real callback")
        mxish_resume()
        await until {cell.snapshot.sequence>before}
        require(CapabilityAndroidProgress.shared.cells[aSlot].snapshot.fault==0,"global fanout cannot win admission while original successful C call still owns it")
        require(ap.binding.finalStatus == .pending && !ar.isReleased && mxish_destructors()==0,"held return cannot finalize facade/resources")
        mxir_release() // Forward exact saved MXUIT_OK; no injected native result/fence.
        await parked.value
        guard case .quarantined=await final.value else {fatalError("faulted facade cannot finish")}
        guard case .finished(.retired(let receipt))=installation.status else {fatalError("completed actual endpoint fact must persist")}
        require(receipt.key.endpoint==owner && receipt.facadeCleanup==nil,"only exact prior nonfinal endpoint fact")
        require(aRecord.withLock{$0.quarantined && $0.closing && $0.resources != nil} && bRecord.withLock{$0.quarantined},"uncertain facade/resources remain")
        require(!ar.isReleased && !br.isReleased && CapabilityAttemptReservation.occupiedSlots==2 && mxish_destructors()==0,"fault pins actual resources and capacity")
        require(snapshot().occupied_facades==2 && mxir_successes()==1,"no facade reclaim or replayed C success")
        print("RECLAIM_RACE_PASS actual_C_OK_once=1 before_global_fault=1 exact_endpoint_fact=1 facade_quarantined=1 destructor=0 capacity_pinned=2")
    }
}
