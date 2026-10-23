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
@inline(never) @_optimize(none) private func acceptedTaskCancellationPoint(_ binding: CapabilityGuestUIAndroidBinding)->UInt{
    mxish_debug_release_point()
    // A verification-only identity read keeps the exact caller-owned scalar
    // binding argument materialized in optimized debugger builds.
    return UInt(bitPattern:Unmanaged.passUnretained(binding).toOpaque())
}
private final class DiagnosticSignal:@unchecked Sendable{
    private let lock=NSLock();private var ready=false
    func mark(){lock.lock();ready=true;lock.unlock()}
    var value:Bool{lock.lock();defer{lock.unlock()};return ready}
}
@main struct DebuggerTests{
    static func main() async throws{
        let scenario=CommandLine.arguments[1]
        check(mxish_start()==0,"host install")
        let reservation=try CapabilityAttemptReservation.acquire()
        if scenario=="lifetime-exhaustion-after-cycle"{
            let warm=try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:reservation)
            try warm.transferToBinding();reservation.beginClosing()
            guard case .finished=await warm.binding.finishFinalClose(using:nil)else{fatalError("actual warm counter owner close")}
            check(reservation.isReleased && mxish_destructors()==1,"real warm cycle initializes actual global counter")
            let later=try CapabilityAttemptReservation.acquire();mxish_debug_mark(30)
            do{_ = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:later);fatalError("actual lifetime exhaustion ignored")}catch{}
            later.beginClosing()
            var c=mxuit_snapshot();check(mxuit_inspect(&c)==0 && c.owners_issued==1 && c.occupied==0 && c.occupied_facades==1,"checked second lifetime failure precedes actual second C endpoint issue")
            check(later.isQuarantined && !later.isReleased && mxish_destructors()==1,"new actual owner remains pinned after checked lifetime exhaustion")
            print("DEBUG_HOLD_PASS lifetime-exhaustion-after-cycle");return
        }
        if scenario=="lifetime-exhaustion"{
            do{_ = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:reservation);fatalError("exhaustion ignored")}catch{}
            reservation.beginClosing();check(reservation.isQuarantined && !reservation.isReleased,"real checked lifetime failure pins")
            var c=mxuit_snapshot();check(mxuit_inspect(&c)==0 && c.occupied==0 && c.occupied_facades==1,"no C endpoint/Task after failed lifetime issue")
            print("DEBUG_HOLD_PASS lifetime-exhaustion");return
        }
        if scenario=="reservation-hold"{
            var reservations=[reservation]
            for _ in 1..<16{reservations.append(try CapabilityAttemptReservation.acquire())}
            let firstReservation=reservations[0]
            let first=Task.detached{try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:firstReservation)}
            check(mxish_debug_wait(1)==0,"actual Swift facade reservation held before C ID publication")
            var others:[Task<CapabilityAndroidHostPreparedPresentation,Error>]=[]
            let contenderReady=DiagnosticSignal(),second=reservations[1]
            others.append(Task.detached{contenderReady.mark();return try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:second)})
            await until{contenderReady.value}
            // One contender proves the held admission boundary without blocking
            // every cooperative worker. Remaining real admissions race after
            // release; the ordinary suite separately races all16 factories.
            for _ in 0..<8{await Task.yield()}
            var before=mxuit_snapshot();check(mxuit_inspect(&before)==0 && before.facades_issued==0 && before.owners_issued==0 && before.requests==0,"reserved original cannot be stolen or publish C identity while admission held")
            check(CapabilityAttemptReservation.occupiedSlots==16,"actual outer reservations bounded during held publication")
            mxish_debug_release_point()
            for index in 2..<16{let next=reservations[index];others.append(Task.detached{try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:next)})}
            var all=[try await first.value]
            for next in others{all.append(try await next.value)}
            var published=mxuit_snapshot();check(mxuit_inspect(&published)==0 && published.occupied_facades==16 && published.occupied==16 && published.requests==0,"all16 actual prebind owners published once")
            do{_ = try CapabilityAndroidRegistry.shared.acquireFacade();fatalError("17th stolen Swift record")}catch{}
            for index in 0..<16{let prepared=all[index];try prepared.transferToBinding();reservations[index].beginClosing();guard case .finished=await prepared.binding.finishFinalClose(using:nil)else{fatalError("actual held reservation cleanup")}}
            check(CapabilityAttemptReservation.occupiedSlots==0 && mxish_destructors()==16,"original and racing factories return only after real destruction")
            print("DEBUG_HOLD_PASS reservation-hold");return
        }
        let prepared=try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:reservation)
        try prepared.transferToBinding();let binding=prepared.binding;let r=record(binding.facade)
        if scenario=="stale-cleanup-replay"{
            check(mxish_set_hold(7,binding.facade)==0,"hold first actual destructor after genuine final cleanup")
            reservation.beginClosing();let oldFinal=Task.detached{await binding.finishFinalClose(using:nil)}
            check(mxish_wait_hold()==0,"genuine first cleanup retained until actual destructor returns")
            let stale=r.withLock{$0.cleanup!};check(stale.key.facade==binding.facade,"genuinely produced immutable cleanup identity")
            mxish_release_hold();guard case .finished=await oldFinal.value else{fatalError("first completed facade")}
            check(reservation.isReleased && mxish_destructors()==1,"original facade actually completed")
            let laterReservation=try CapabilityAttemptReservation.acquire()
            let laterPrepared=try await CapabilityGuestUIAndroidBinding.prepareHost(reservation:laterReservation)
            try laterPrepared.transferToBinding();let later=laterPrepared.binding;let laterRecord=record(later.facade)
            check(later.facade != stale.key.facade,"later actual facade reuses record with fresh identity")
            mxish_debug_mark(10) // Verification-only breakpoint phase, not product authority.
            laterReservation.beginClosing();let laterFinal=Task.detached{await later.finishFinalClose(using:nil)}
            check(mxish_debug_wait(11)==0,"actual later final gate held after Task/native endpoint retirement")
            let current=laterRecord.withLock{$0.cleanup!}
            check(current.key.facade==later.facade && current.cleanupSerial==stale.cleanupSerial,"same numeric serial is scoped to different real facade identities")
            laterRecord.withLock{$0.cleanup=stale} // Replay only; no evidence constructor or field mutation.
            mxish_debug_release_point()
            guard case .quarantined=await laterFinal.value else{fatalError("stale immutable cleanup replay accepted")}
            var native=mxuit_snapshot();check(mxuit_inspect(&native)==0 && native.occupied_facades==1,"later uncertain facade cannot reclaim")
            check(!laterReservation.isReleased && laterReservation.isQuarantined && mxish_destructors()==1,"later real resources/capacity pinned after stale replay")
            print("STALE_CLEANUP_REPLAY old_facade=\(stale.key.facade) later_facade=\(later.facade) same_serial=\(stale.cleanupSerial) final_success=0 capacity_pinned=1")
            print("DEBUG_HOLD_PASS stale-cleanup-replay");return
        }
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
            let heldOwner=acceptedTaskCancellationPoint(binding)
            check(heldOwner==UInt(bitPattern:Unmanaged.passUnretained(binding).toOpaque()),"exact caller-owned scalar binding identity")
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
        if scenario=="cleanup-wrong-entry" || scenario=="cleanup-wrong-generation"{
            let endpoint=r.withLock{$0.endpoint};var actual=mxuit_owner_snapshot()
            check(mxuit_inspect_owner(endpoint,&actual)==0 && actual.consumer_joined==0 && actual.retirement_done==0,"wrong actual entry/native generation cannot earn join or RETIRE success")
            check(r.withLock{$0.cleanup==nil} && mxish_destructors()==0 && mxish_live_allocations()==0,"real native clear alone cannot authorize final cleanup or destruction")
        }
        check(!reservation.isReleased && reservation.isQuarantined,"real checked counter failure preserves ownership")
        print("DEBUG_HOLD_PASS \(scenario)")
    }
}
