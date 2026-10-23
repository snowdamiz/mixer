import Foundation
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation
import CMixerUITransport
import CMixerUIAndroidHostTest
import CMixerUIAndroidTransportProbe
private func check(_ value: @autoclosure () -> Bool, _ message: String) { if !value() { mxish_probe_release(); mxish_release_hold(); fatalError("PROBE_FAIL \(message)") } }
private func snapshot() -> mxuit_snapshot { var s=mxuit_snapshot();check(mxuit_inspect(&s)==0,"inspect");return s }
private func until(_ predicate: @Sendable () -> Bool) async {
    let deadline=ContinuousClock.now + .seconds(8)
    while !predicate() { check(ContinuousClock.now<deadline,"observation deadline");await Task.yield() }
}
private final class ProbeReady:@unchecked Sendable{
    private let lock=NSLock();private var ready=false
    func mark(){lock.lock();ready=true;lock.unlock()}
    var value:Bool{lock.lock();defer{lock.unlock()};return ready}
}
@main struct ProbeTests {
    static func main() async throws {
        check(mxish_start()==0,"install")
        let scenario=CommandLine.arguments[1]
        let reservation=try CapabilityAttemptReservation.acquire()
        let prepared=try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:reservation)
        try prepared.transferToBinding();let binding=prepared.binding
        var owner:UInt64=0
        for i in 0..<16 { if let r=CapabilityAndroidRegistry.shared.record(slot:i,facade:binding.facade){owner=r.withLock{$0.endpoint}} }
        check(owner>0,"actual endpoint")
        if scenario=="fast" || scenario=="request-rejection" {
            mxish_pause();check(mxish_probe_arm(scenario=="fast" ? 6:7,owner)==0,"arm actual request")
            let exchange=try GuestUIExchangeV1(generation:17)
            let startup=try exchange.claimStartup()
            try exchange.finishTurn(startup,documentBytes:Data(#"{"schemaVersion":1,"revision":1,"root":{"id":"root","kind":"text","properties":{"text":"Exact host"},"actions":[],"children":[]}}"#.utf8))
            try exchange.enterEffectsIntent(generation:17);try exchange.confirmEffectsEnabled(generation:17)
            let installation=try await binding.bindHost(exchange)
            check(mxish_probe_wait()==0,"caller remains within actual request wrapper")
            let waiter=mxish_probe_request_waiter();check(mxish_probe_request_owner()==owner && waiter>0,"exact published request")
            if scenario=="request-rejection" {
                check(mxish_probe_preempt_request(owner,waiter+1)==0,"real C predecessor forces actual BUSY rejection")
                mxish_probe_release()
                let result=await installation.finish()
                guard case .finished(.quarantined)=result else {fatalError("rejection must quarantine")}
                check(snapshot().occupied==1 && !reservation.isReleased,"no joined/reclaim for rejected retire")
                mxish_resume();reservation.beginClosing()
                guard case .quarantined=await binding.finishFinalClose(using:nil) else {fatalError("final uncertainty")}
            } else {
                mxish_resume();await until{snapshot().completions>0}
                check(installation.status == .pending,"real completion before request caller returns")
                mxish_probe_release();reservation.beginClosing()
                guard case .finished=await binding.finishFinalClose(using:installation) else{fatalError("fast exact completion")}
                // Old identity and duplicate native completion cannot consume a later wait.
                capabilityAndroidComplete(owner,waiter,2,0)
                check(reservation.isReleased,"no stale completion authority")
            }
            print("PROBE_PASS \(scenario)");return
        }
        let point:UInt32
        switch scenario {case "lost-before","fault-after-join":point=1;case "lost-after":point=2;case "ui-leave":point=3;case "completion":point=4;case "progress":point=5;case "no-progress":point=0;case "late-entry":point=8;default:fatalError("unknown")}
        if point>0 {check(mxish_probe_arm(point,point==3 || point==8 ? binding.facade:point==5 ? 0:owner)==0,"arm real boundary")}
        if scenario=="lost-before" || scenario=="lost-after" || scenario=="no-progress" || scenario=="fault-after-join" {check(mxish_set_hold(9,0)==0,"hold actual platform return tail")}
        reservation.beginClosing();let final=Task.detached{await binding.finishFinalClose(using:nil)}
        if scenario=="fault-after-join" {
            check(mxish_probe_wait()==0 && mxish_wait_hold()==0,"actual first BUSY reclaim and native platform tail held")
            var actual=mxuit_owner_snapshot();check(mxuit_inspect_owner(owner,&actual)==0 && actual.consumer_joined==1,"genuine Task returned before native join assertion")
            let slot=(0..<16).first{CapabilityAndroidRegistry.shared.record(slot:$0,facade:binding.facade) != nil}!
            let cell=CapabilityAndroidProgress.shared.cells[slot],ready=ProbeReady();let sequence=cell.snapshot.sequence
            let existing=Task.detached{await withCheckedContinuation{(c:CheckedContinuation<Void,Never>) in
                check(cell.register(after:sequence,c) != nil,"real first progress continuation");ready.mark()
            }}
            await until{ready.value}
            await withCheckedContinuation{(c:CheckedContinuation<Void,Never>) in check(cell.register(after:sequence,c)==nil,"duplicate wait failure");c.resume()}
            // The held real reclaim call still owns registry admission. Let
            // that actual BUSY return before waiting for fault fanout's lock.
            mxish_release_hold();mxish_probe_release();await existing.value
            await until{CapabilityAndroidProgress.shared.cells.allSatisfy{$0.snapshot.fault==4}}
            guard case .quarantined=await final.value else{fatalError("post-admission fault must block reclaim/evidence")}
            check(mxuit_inspect_owner(owner,&actual)==0 && actual.consumer_joined==1 && snapshot().occupied==1,"actual joined fact cannot release uncertain endpoint")
            check(!reservation.isReleased && mxish_destructors()==0,"post-admission fault retains actual resource owner/capacity")
            print("PROBE_PASS fault-after-join consumer_joined=1 retirement_receipt=0 capacity_pinned=1");return
        }
        if scenario=="no-progress" {
            check(mxish_wait_hold()==0,"platform tail")
            await until{mxish_probe_reclaim_calls()>=2}
            check(mxish_probe_reclaim_calls()==2,"one first and one mandatory second reclaim")
            for _ in 0..<128 {await Task.yield()}
            check(mxish_probe_reclaim_calls()==2 && binding.finalStatus == .pending && !reservation.isReleased,"no polling or timeout success")
            mxish_release_hold()
        } else {
            check(mxish_probe_wait()==0,"actual operation boundary")
            if scenario=="lost-before" || scenario=="lost-after" {
                check(mxish_wait_hold()==0,"actual earlier callback return")
                mxish_release_hold();await until{snapshot().fenced_epoch>0 && snapshot().ui_entry_fenced>0}
                check(!reservation.isReleased,"actual blocked reclaim frame")
            } else if scenario=="late-entry" {
                check(snapshot().occupied==0 && snapshot().occupied_facades==1,"endpoint absent before facade reclaim")
                check(mxish_call_entry(binding.facade,3)==3,"lookup-disabled late CLEANUP takes lease without resource promotion")
                check(mxish_set_hold(10,binding.facade)==0,"hold later real C cleanup entry")
                let facade=binding.facade
                let entering=Task.detached{mxish_call_entry(facade,4)}
                check(mxish_wait_hold()==0,"late cleanup entry admitted")
                let lateEntry=snapshot().active_entry_serial;check(lateEntry>0,"active late lease")
                mxish_probe_release();await until{mxish_probe_facade_calls()>=2}
                check(!reservation.isReleased && binding.finalStatus == .pending,"late facade entry fences finalization without endpoint")
                mxish_release_hold();let entered=await entering.value;check(entered==0,"actual late leave returned")
                guard case .finished(let result)=await final.value else{fatalError("late final")}
                check(result.facadeReturnFence>=lateEntry && reservation.isReleased,"later accepted callback fenced late entry")
                print("PROBE_PASS late-entry");return
            } else if scenario=="ui-leave" {
                check(snapshot().active_entry_serial>0 && !reservation.isReleased,"inner returned but real C UI entry still held")
            } else if scenario=="completion" {
                await until{mxish_probe_reclaim_calls()>=2}
                check(snapshot().completing==1 && snapshot().occupied==1 && !reservation.isReleased,"real completion tail pins endpoint")
            } else if scenario=="progress" {
                await until{reservation.isReleased}
                check(mxish_destructors()==1 && snapshot().occupied_facades==0,"healthy process-only progress tail may coexist with final destruction")
            }
            mxish_probe_release()
        }
        guard case .finished(let result)=await final.value else{fatalError("final proof")}
        check(result.lastLifetime.taskJoin == .joined && reservation.isReleased && mxish_destructors()==1,"actual joins/destructor")
        print("PROBE_PASS \(scenario) reclaims=\(mxish_probe_reclaim_calls())")
    }
}
