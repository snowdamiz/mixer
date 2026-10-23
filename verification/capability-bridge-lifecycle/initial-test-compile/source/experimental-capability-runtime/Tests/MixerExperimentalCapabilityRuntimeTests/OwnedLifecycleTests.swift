import Foundation
import Dispatch
import Testing
import MixerCapabilities
@_spi(CapabilityLifecycle) @testable import MixerExperimentalCapabilityRuntime

final class LifecycleRecorder: CapabilityBridgeTerminalObserver, CapabilityBridgeRetirementObserver, @unchecked Sendable {
    struct State { var failures:[ExperimentalCapabilityFailure]=[];var retirements=0 }
    let state=Locked(State())
    func recordTerminalFailure(_ failure:ExperimentalCapabilityFailure){state.withLock{$0.failures.append(failure)}}
    func recordRetired(){state.withLock{$0.retirements += 1}}
    var retired:Int{state.withLock{$0.retirements}}
    var failures:[ExperimentalCapabilityFailure]{state.withLock{$0.failures}}
}
func lifecycleStore(_ directory:URL)throws->AppPrivateKeyValueStore{try AppPrivateKeyValueStore(directory:directory,namespaces:["entries"])}
func lifecycleReopens(_ directory:URL)async throws{let store=try lifecycleStore(directory);await store.close()}
func lifecyclePrepare(_ group:OwnedCapabilityAdapterGroup,module:Data=GuestProgram.build())throws->ExperimentalCapabilityConstruction{
    try ExperimentalCapabilitySession.prepareOwned(module:module,startupExport:"boot",policy:bridgePolicy(),adapterGroup:group)
}
extension ExperimentalBridgeTests{
    @Test func untransferredConcreteGroupClosesOnceAfterFailedSetupAndDeinit()async throws{
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-owned-unused-"+UUID().uuidString);defer{try? FileManager.default.removeItem(at:directory)}
        let recorder=LifecycleRecorder();let store=try lifecycleStore(directory)
        var group:OwnedCapabilityAdapterGroup?=OwnedCapabilityAdapterGroup(storage:store,terminal:recorder,retirement:recorder)
        #expect(throws:CapabilityWireError.self){try URLSessionHTTPTransport(maximumConcurrentRequests:0)} // Real setup failure after KV open.
        let core=group!.core
        DispatchQueue.concurrentPerform(iterations:32){_ in group!.closeIfUntransferred()}
        try await bridgeEventually{recorder.retired==1};#expect(core.cleanupJobCount==1 && recorder.failures.isEmpty)
        group=nil;try await lifecycleReopens(directory)
        let nextRecorder=LifecycleRecorder()
        var abandoned:OwnedCapabilityAdapterGroup?=OwnedCapabilityAdapterGroup(storage:try lifecycleStore(directory),terminal:nextRecorder,retirement:nextRecorder)
        #expect(abandoned != nil);abandoned=nil
        try await bridgeEventually{nextRecorder.retired==1};try await lifecycleReopens(directory)
    }
    @Test func ownedPrepareFailureRetainsGroupAndConsumedFailureReturnsOnlyNewPermit()async throws{
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-owned-admission-"+UUID().uuidString);defer{try? FileManager.default.removeItem(at:directory)}
        let recorder=LifecycleRecorder();let group=OwnedCapabilityAdapterGroup(storage:try lifecycleStore(directory),terminal:recorder,retirement:recorder)
        #expect(throws:ExperimentalCapabilityError("invalid_module_or_startup")){try ExperimentalCapabilitySession.prepareOwned(module:Data(count:4_194_305),startupExport:"boot",policy:bridgePolicy(),adapterGroup:group)}
        var held:[ExperimentalCapabilityConstruction]=[]
        for _ in 0..<16{held.append(try ExperimentalCapabilitySession.prepare(module:Data(),startupExport:"boot",policy:bridgePolicy(),adapters:InstalledCapabilityAdapters()))}
        #expect(throws:ExperimentalCapabilityError("construction_busy")){try lifecyclePrepare(group)}
        #expect(recorder.retired==0 && group.core.cleanupJobCount==0)
        held.removeAll()
        let first=try lifecyclePrepare(group)
        #expect(throws:ExperimentalCapabilityError("adapter_group_consumed")){try lifecyclePrepare(group)}
        // Rejected duplicate transfer must not consume another permit.
        for _ in 0..<15{held.append(try ExperimentalCapabilitySession.prepare(module:Data(),startupExport:"boot",policy:bridgePolicy(),adapters:InstalledCapabilityAdapters()))}
        #expect(held.count==15);held.removeAll();first.cancel()
        try await bridgeEventually{recorder.retired==1};#expect(group.core.cleanupJobCount==1);try await lifecycleReopens(directory)
    }
    @Test func abandonedAndQueuedCancelledOwnedConstructionRetireAfterCleanup()async throws{
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-owned-create-"+UUID().uuidString);defer{try? FileManager.default.removeItem(at:directory)}
        let abandonedRecorder=LifecycleRecorder();let abandonedGroup=OwnedCapabilityAdapterGroup(storage:try lifecycleStore(directory),terminal:abandonedRecorder,retirement:abandonedRecorder)
        var abandoned:ExperimentalCapabilityConstruction?=try lifecyclePrepare(abandonedGroup);#expect(abandoned != nil);abandoned=nil
        try await bridgeEventually{abandonedRecorder.retired==1};try await lifecycleReopens(directory)
        let recorder=LifecycleRecorder();let group=OwnedCapabilityAdapterGroup(storage:try lifecycleStore(directory),terminal:recorder,retirement:recorder)
        let gate=LifecycleQueueGate();ExperimentalQueues.construction.async{gate.hold()};defer{gate.release()}
        try await bridgeEventually{gate.entered}
        let construction=try lifecyclePrepare(group);let pending=Task{try await construction.create()}
        try await Task.sleep(for:.milliseconds(15));pending.cancel()
        #expect(recorder.retired==0 && group.core.cleanupJobCount==0)
        gate.release();await #expect(throws:CancellationError.self){try await pending.value}
        try await bridgeEventually{recorder.retired==1};#expect(group.core.constructorTailObserved && group.core.cleanupJobCount==1)
        #expect(recorder.failures.isEmpty);try await lifecycleReopens(directory)
    }
    @Test func ownedRealStorageDrainAndSessionDeinitRetireAndReleaseObservers()async throws{
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-owned-storage-"+UUID().uuidString);defer{try? FileManager.default.removeItem(at:directory)}
        var recorder:LifecycleRecorder?=LifecycleRecorder();weak var weakRecorder=recorder
        let group=OwnedCapabilityAdapterGroup(storage:try lifecycleStore(directory),terminal:recorder!,retirement:recorder!)
        var session:ExperimentalCapabilitySession?=try await lifecyclePrepare(group).create()
        _ = try await session!.startup();try await session!.enableEffects();_ = try await session!.invoke("run")
        try await bridgeEventually{try await session!.invoke("stage").value == .i32(5)}
        group.closeIfUntransferred();#expect(!session!.status.closed) // No ownership after handoff.
        session=nil;try await bridgeEventually{recorder!.retired==1}
        #expect(recorder!.failures.isEmpty && group.core.cleanupJobCount==1 && group.core.constructorTailObserved)
        try await lifecycleReopens(directory);recorder=nil
        try await bridgeEventually{weakRecorder == nil} // Completed retirement clears both observers.
    }
    @Test func nativeBusyAndOrdinaryCreateErrorsCloseConcreteGroupAndKeepTypedContext()async throws{
        var native:[NativeCapabilitySession]=[]
        for _ in 0..<16{native.append(try NativeCapabilitySession(module:ValidationGuest.build(),startup:"boot",configuration:.init()))}
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-owned-native-"+UUID().uuidString);defer{try? FileManager.default.removeItem(at:directory)}
        let recorder=LifecycleRecorder();let group=OwnedCapabilityAdapterGroup(storage:try lifecycleStore(directory),terminal:recorder,retirement:recorder)
        do{_ = try await lifecyclePrepare(group).create();Issue.record("native registry capacity ignored")}
        catch let error as ExperimentalCapabilityError{#expect(error.failure.kind == .resource(.nativeSessionCapacity) && error.failure.operation == .construction)}
        try await bridgeEventually{recorder.retired==1};#expect(recorder.failures.count==1 && group.core.cleanupJobCount==1);try await lifecycleReopens(directory)
        for owner in native{try owner.close()};native.removeAll()
        for module in [Data([0]),ValidationGuest.build(badData:true)]{
            let observer=LifecycleRecorder();let adapters=OwnedCapabilityAdapterGroup(storage:try lifecycleStore(directory),terminal:observer,retirement:observer)
            await #expect(throws:ExperimentalCapabilityError.self){try await lifecyclePrepare(adapters,module:module).create()}
            try await bridgeEventually{observer.retired==1};#expect(observer.failures.count==1 && observer.failures[0].operation == .construction)
            #expect(adapters.core.cleanupJobCount==1);try await lifecycleReopens(directory)
        }
    }
}
private final class LifecycleQueueGate:@unchecked Sendable{
    private let condition=NSCondition();private var open=false;private var began=false
    func hold(){condition.lock();began=true;let end=Date().addingTimeInterval(5);while !open{if !condition.wait(until:end){break}};condition.unlock()}
    func release(){condition.lock();open=true;condition.broadcast();condition.unlock()}
    var entered:Bool{condition.lock();defer{condition.unlock()};return began}
}
