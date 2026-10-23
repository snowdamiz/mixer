import Foundation
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation
import CMixerUITransport
import CMixerUIAndroidHostTest
private func check(_ value:@autoclosure ()->Bool,_ message:String){if !value(){fatalError("DEBUG_HOLD_FAIL \(message)")}}
private func record(_ facade:UInt64)->CapabilityAndroidFacadeRecord{
    for i in 0..<16{if let r=CapabilityAndroidRegistry.shared.record(slot:i,facade:facade){return r}}
    fatalError("missing actual facade")
}
private func until(_ predicate:@Sendable ()->Bool) async{
    let deadline=ContinuousClock.now + .seconds(8)
    while !predicate(){check(ContinuousClock.now<deadline,"observation deadline");await Task.yield()}
}
@inline(never) private func acceptedTaskCancellationPoint(_ binding: CapabilityGuestUIAndroidBinding){ mxish_debug_release_point() }
@main struct DebuggerTests{
    static func main() async throws{
        let scenario=CommandLine.arguments[1]
        check(mxish_start()==0,"host install")
        let reservation=try CapabilityAttemptReservation.acquire()
        if scenario=="lifetime-exhaustion"{
            do{_ = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:reservation);fatalError("exhaustion ignored")}catch{}
            reservation.beginClosing();check(reservation.isQuarantined && !reservation.isReleased,"real checked lifetime failure pins")
            var c=mxuit_snapshot();check(mxuit_inspect(&c)==0 && c.occupied==0 && c.occupied_facades==1,"no C endpoint/Task after failed lifetime issue")
            print("DEBUG_HOLD_PASS lifetime-exhaustion");return
        }
        let prepared=try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:reservation)
        try prepared.transferToBinding();let binding=prepared.binding;let r=record(binding.facade)
        if scenario=="gate-order"{
            reservation.beginClosing();guard case .finished=await binding.finishFinalClose(using:nil)else{fatalError("gate control")}
            check(reservation.isReleased,"ordinary gate control");print("DEBUG_HOLD_PASS gate-order");return
        }
        if scenario=="setup-alias"{
            let exchange=try GuestUIExchangeV1(generation:23)
            let bind=Task.detached{()->Bool in do{_ = try await binding.bindHost(exchange);return false}catch{return true}}
            check(mxish_debug_wait(1)==0,"debugger held actual setup helper after weak promotion")
            check(r.withLock{$0.setupAliases==1 && $0.uiAliases==0 && $0.resources != nil},"actual counted setup alias")
            reservation.beginClosing();binding.requestFinalClose(.closed)
            let pending=await binding.finishFinalClose(using:nil);check(pending == .pending,"bind frame still owns initial installation")
            check(!reservation.isReleased,"actual setup alias pins resources")
            mxish_debug_release_point()
            let failedBind=await bind.value;check(failedBind,"close-winning bind explicitly finished same local installation")
            guard case .finished=await binding.finishFinalClose(using:nil)else{fatalError("setup final")}
            check(reservation.isReleased && mxish_destructors()==1,"actual helper return before destruction")
            print("DEBUG_HOLD_PASS setup-alias");return
        }
        if scenario=="bind-return"{
            let exchange=try GuestUIExchangeV1(generation:24)
            let binder=Task.detached{try await binding.bindHost(exchange)}
            check(mxish_debug_wait(1)==0,"actual bind return frame held after gate")
            reservation.beginClosing();binding.requestFinalClose(.closed)
            let absent=await binding.finishFinalClose(using:nil)
            check(absent == .invariant(.wrongJoinOwner),"returned local owner still required")
            check(!reservation.isReleased,"bind return hold pins actual owner")
            mxish_debug_release_point()
            let installation=try await binder.value
            guard case .finished=await binding.finishFinalClose(using:installation)else{fatalError("exact returned bind owner")}
            check(reservation.isReleased && mxish_destructors()==1,"bind caller joins exact local owner")
            print("DEBUG_HOLD_PASS bind-return");return
        }
        if scenario=="cancel-accepted"{
            check(mxish_set_hold(5,binding.facade)==0,"hold actual accepted native RETIRE helper")
            reservation.beginClosing();let final=Task.detached{await binding.finishFinalClose(using:nil)}
            check(mxish_wait_hold()==0,"accepted waiter is executing actual RETIRE helper")
            let endpoint=r.withLock{$0.endpoint}
            var before=mxuit_owner_snapshot();check(mxuit_inspect_owner(endpoint,&before)==0 && before.completing==0 && before.consumer_joined==0,"accepted native waiter before cancel")
            acceptedTaskCancellationPoint(binding)
            check(mxish_debug_wait(1)==0,"debugger cancelled exact common Task handle")
            var after=mxuit_owner_snapshot();check(mxuit_inspect_owner(endpoint,&after)==0 && after.consumer_joined==0 && after.retirement_done==0,"cancellation preserves accepted waiter")
            check(binding.finalStatus == .pending && !reservation.isReleased && mxish_destructors()==0,"cancellation is not join or cleanup")
            mxish_release_hold()
            guard case .finished=await final.value else{fatalError("cancelled accepted Task must actually return")}
            check(reservation.isReleased && mxish_destructors()==1,"cancelled real Task.value plus native cleanup completed")
            print("DEBUG_HOLD_PASS cancel-accepted");return
        }
        if scenario=="progress-token-exhaustion" || scenario=="progress-sequence-exhaustion" || scenario=="progress-tail"{check(mxish_set_hold(9,0)==0,"hold real later callback")}
        reservation.beginClosing();let final=Task.detached{await binding.finishFinalClose(using:nil)}
        if scenario=="progress-tail"{
            check(mxish_wait_hold()==0,"real callback tail held while exact progress waiter registers")
            check(mxish_debug_wait(1)==0,"actual progress waiter registration returned")
            mxish_release_hold()
            check(mxish_debug_wait(2)==0,"native worker held after actual continuation resume")
            await until{reservation.isReleased}
            check(mxish_destructors()==1,"actual final destruction while consumed continuation copy is held")
            mxish_debug_release_point()
            guard case .finished=await final.value else{fatalError("progress tail final")}
            print("DEBUG_HOLD_PASS progress-tail");return
        }
        if scenario=="post-store"{
            check(mxish_debug_wait(1)==0,"exact presentation worker held after terminal store")
            let endpoint=r.withLock{$0.endpoint}
            await until{
                var c=mxuit_owner_snapshot();return mxuit_inspect_owner(endpoint,&c)==0 && c.retirement_done==1
            }
            var c=mxuit_owner_snapshot();check(mxuit_inspect_owner(endpoint,&c)==0 && c.consumer_joined==0,"no native consumer join before actual Task return")
            check(binding.finalStatus == .pending && !reservation.isReleased && mxish_destructors()==0,"terminal store is not Task return")
            mxish_debug_release_point()
            guard case .finished=await final.value else{fatalError("post-store actual final")}
            check(reservation.isReleased && mxish_destructors()==1,"original worker returned and actualTask.value joined")
            print("DEBUG_HOLD_PASS post-store");return
        }
        if scenario=="progress-sequence-exhaustion"{check(mxish_debug_wait(1)==0,"actual progress token registered before sequence exhaustion");mxish_release_hold()}
        guard case .quarantined=await final.value else{fatalError("checked failure must quarantine")}
        if scenario=="progress-token-exhaustion"{mxish_release_hold()}
        check(!reservation.isReleased && reservation.isQuarantined,"real checked counter failure preserves ownership")
        print("DEBUG_HOLD_PASS \(scenario)")
    }
}
