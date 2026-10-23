import Foundation
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation
import CMixerUITransport
import CMixerUIAndroidHostTest
import CMixerUIAndroidTransportProbe
private func check(_ value:@autoclosure ()->Bool,_ message:String){if !value(){mxish_probe_release();mxish_release_hold();fatalError("SUPPLEMENT_FAIL \(message)")}}
private func snapshot()->mxuit_snapshot{var s=mxuit_snapshot();check(mxuit_inspect(&s)==0,"actual C snapshot");return s}
private func until(_ predicate:@Sendable()->Bool)async{let deadline=ContinuousClock.now + .seconds(8);while !predicate(){check(ContinuousClock.now<deadline,"observation deadline");await Task.yield()}}
private func exchange(_ generation:UInt64)throws->GuestUIExchangeV1{
    let value=try GuestUIExchangeV1(generation:generation);let startup=try value.claimStartup()
    try value.finishTurn(startup,documentBytes:Data(#"{"schemaVersion":1,"revision":1,"root":{"id":"root","kind":"text","properties":{"text":"Supplemental actual host"},"actions":[],"children":[]}}"#.utf8))
    try value.enterEffectsIntent(generation:generation);try value.confirmEffectsEnabled(generation:generation);return value
}
@main struct SupplementalHostTests{
    static func main()async throws{
        check(mxish_start()==0,"fixed host install");let scenario=CommandLine.arguments[1]
        let reservation=try CapabilityAttemptReservation.acquire()
        if scenario=="c-endpoint-exhaustion"{
            check(mxish_set_c_counter(1,UInt64.max)==0,"actual C endpoint counter failure control")
            do{_ = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:reservation);fatalError("C endpoint identity wrapped")}catch{}
            reservation.beginClosing();let c=snapshot()
            check(c.owners_issued==UInt64.max && c.occupied==0 && c.occupied_facades==1 && c.requests==0,"no zero/reused C endpoint or nonexistent joined assertion")
            check(reservation.isQuarantined && !reservation.isReleased && mxish_destructors()==0,"live facade and resource obligation pinned")
            print("SUPPLEMENT_PASS \(scenario)");return
        }
        let prepared=try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:reservation);try prepared.transferToBinding();let binding=prepared.binding
        if scenario=="c-entry-exhaustion"{
            check(mxish_set_c_counter(3,UInt64.max)==0,"actual C entry counter failure control")
            reservation.beginClosing();guard case .quarantined=await binding.finishFinalClose(using:nil)else{fatalError("C UI entry wrapped")}
            let c=snapshot();check(c.ui_entries_issued==UInt64.max && c.fault != 0 && c.occupied==1 && c.occupied_facades==1,"checked C entry overflow is sticky and never reused")
            check(!reservation.isReleased && mxish_destructors()==0 && mxish_live_allocations()==0,"entry rejection precedes native/resource promotion")
            print("SUPPLEMENT_PASS \(scenario)");return
        }
        let first=try await binding.bindHost(exchange(7001));await until{snapshot().completions>0};mxish_pause()
        if scenario=="fallback-before-fence"{
            check(mxish_set_hold(9,0)==0,"hold actual platform return before later fence")
            first.requestStop(.closed);let finishing=Task.detached{await first.finish()};mxish_resume();check(mxish_wait_hold()==0,"old real retirement callback returned to platform tail")
            let rejected=try exchange(7002)
            do{_ = try await binding.bindHost(rejected);fatalError("fallback bypassed authoritative old finish")}catch{}
            check(rejected.snapshot().stop != nil && snapshot().owners_issued==1 && first.status == .pending,"no successor identity/Task before actual old finish returned")
            mxish_release_hold();guard case .finished(.retired)=await finishing.value else{fatalError("old actual join")}
            let next=try await binding.bindHost(exchange(7003));reservation.beginClosing()
            guard case .finished=await binding.finishFinalClose(using:next)else{fatalError("fresh exact fallback owner")}
            check(next.key.endpoint != first.key.endpoint && reservation.isReleased && mxish_destructors()==1,"fresh sequential fallback after actual old finish")
        }else if scenario=="late-after-completion"{
            check(mxish_probe_arm(4,first.key.endpoint)==0,"hold actual C completion tail after real Swift complete returned")
            first.requestStop(.closed);let finishing=Task.detached{await first.finish()};mxish_resume();check(mxish_probe_wait()==0,"nonfinal RETIRE completion returned")
            check(snapshot().completing==1,"actual C completion tail still active")
            binding.requestFinalClose(.closed);reservation.beginClosing();mxish_probe_release()
            guard case .finished(.retired(let old))=await finishing.value else{fatalError("nonfinal exact old retirement")}
            check(old.facadeCleanup==nil,"late close cannot fabricate cleanup in already-completed old helper")
            guard case .finished(let final)=await binding.finishFinalClose(using:nil)else{fatalError("fresh terminal after old completion")}
            check(final.lastLifetime.key.endpoint != old.key.endpoint && snapshot().owners_issued==2 && reservation.isReleased,"one sequential TERMINAL after actual old finish, no guest restart")
        }else{fatalError("unknown supplemental scenario")}
        print("SUPPLEMENT_PASS \(scenario)")
    }
}
