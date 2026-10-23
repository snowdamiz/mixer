import Foundation
import CMixerVMCapability
@testable import MixerCapabilities

enum LifecycleProbeHooks {
    struct State {
        var tail:LifecycleProbeGate?
        var created:LifecycleProbeGate?
        var storageClose:LifecycleProbeAsyncGate?
        var invocation:LifecycleProbeAsyncGate?
        var malformedCreate=false
        var nativeCloses=0
    }
    static let state=Locked(State())
    static func beforeConstructorTail(){state.withLock{$0.tail}?.hold()}
    static func afterCreate(){state.withLock{$0.created}?.hold()}
    static func beforeStorageClose()async{if let gate=state.withLock({$0.storageClose}){await gate.wait()}}
    static func createReport(_ report:inout MixerVmReport){if state.withLock({$0.malformedCreate}){report.abi_version=2}}
    static func nativeClose(){state.withLock{$0.nativeCloses += 1}}
    static func adapters(http:URLSessionHTTPTransport?,storage:AppPrivateKeyValueStore?)->InstalledCapabilityAdapters{
        var hooks=InstalledCapabilityExecutionHooks.none
        if let gate=state.withLock({$0.invocation}){hooks.afterInvocation={await gate.wait()}}
        return InstalledCapabilityAdapters(http:http,storage:storage,hooks:hooks)
    }
}
final class LifecycleProbeGate:@unchecked Sendable{
    private let condition=NSCondition();private var open=false;private var began=false
    func hold(){condition.lock();began=true;let end=Date().addingTimeInterval(5);while !open{if !condition.wait(until:end){break}};condition.unlock()}
    func release(){condition.lock();open=true;condition.broadcast();condition.unlock()}
    var entered:Bool{condition.lock();defer{condition.unlock()};return began}
}
final class LifecycleProbeAsyncGate:@unchecked Sendable{
    private struct State{var open=false;var entered=false;var waiter:CheckedContinuation<Void,Never>?}
    private let state=Locked(State())
    func wait()async{
        await withCheckedContinuation{continuation in
            let ready=state.withLock{state in
                state.entered=true
                if state.open{return true};precondition(state.waiter==nil);state.waiter=continuation;return false
            }
            if ready{continuation.resume()}
        }
    }
    func release(){let waiter=state.withLock{state in state.open=true;let waiter=state.waiter;state.waiter=nil;return waiter};waiter?.resume()}
    var entered:Bool{state.withLock{$0.entered}}
}
