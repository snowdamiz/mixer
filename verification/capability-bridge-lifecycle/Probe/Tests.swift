import Foundation
import Testing
import MixerCapabilities
@_spi(CapabilityLifecycle) @testable import MixerExperimentalCapabilityRuntime

@Suite(.serialized) struct LifecycleOwnerProbeTests{
    @Test func successfulHandoffCannotRetireBeforeConstructorTail()async throws{
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-life-tail-"+UUID().uuidString);defer{try? FileManager.default.removeItem(at:directory)}
        let gate=LifecycleProbeGate();LifecycleProbeHooks.state.withLock{$0.tail=gate};defer{gate.release()}
        let observer=LifecycleRecorder();let group=OwnedCapabilityAdapterGroup(storage:try lifecycleStore(directory),terminal:observer,retirement:observer)
        let session=try await lifecyclePrepare(group).create();try await bridgeEventually{gate.entered};session.close()
        try await bridgeEventually{session.status.drained}
        #expect(observer.retired==0 && !group.core.constructorTailObserved && group.core.cleanupJobCount==1)
        var held:[ExperimentalCapabilityConstruction]=[]
        for _ in 0..<15{held.append(try ExperimentalCapabilitySession.prepare(module:Data(),startupExport:"boot",policy:bridgePolicy(),adapters:InstalledCapabilityAdapters()))}
        #expect(throws:ExperimentalCapabilityError("construction_busy")){try ExperimentalCapabilitySession.prepare(module:Data(),startupExport:"boot",policy:bridgePolicy(),adapters:InstalledCapabilityAdapters())}
        gate.release();try await bridgeEventually{observer.retired==1};held.removeAll()
        #expect(LifecycleProbeHooks.state.withLock{$0.nativeCloses}==1);try await lifecycleReopens(directory)
    }
    @Test func cancelledAfterActualNativeCreateKeepsGroupUntilNativeCleanup()async throws{
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-life-create-"+UUID().uuidString);defer{try? FileManager.default.removeItem(at:directory)}
        let gate=LifecycleProbeGate();LifecycleProbeHooks.state.withLock{$0.created=gate};defer{gate.release()}
        let observer=LifecycleRecorder();let group=OwnedCapabilityAdapterGroup(storage:try lifecycleStore(directory),terminal:observer,retirement:observer)
        let construction=try lifecyclePrepare(group);let pending=Task{try await construction.create()};try await bridgeEventually{gate.entered};pending.cancel()
        #expect(observer.retired==0 && group.core.cleanupJobCount==0)
        #expect(throws:(any Error).self){try lifecycleStore(directory)}
        gate.release();await #expect(throws:CancellationError.self){try await pending.value}
        try await bridgeEventually{observer.retired==1};#expect(observer.failures.isEmpty && group.core.cleanupJobCount==1)
        #expect(LifecycleProbeHooks.state.withLock{$0.nativeCloses}==1);try await lifecycleReopens(directory)
    }
    @Test func concreteStorageCloseMustActuallyReturnBeforeUntransferredRetirement()async throws{
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-life-kv-close-"+UUID().uuidString);defer{try? FileManager.default.removeItem(at:directory)}
        let gate=LifecycleProbeAsyncGate();LifecycleProbeHooks.state.withLock{$0.storageClose=gate};defer{gate.release()}
        let observer=LifecycleRecorder();let group=OwnedCapabilityAdapterGroup(storage:try lifecycleStore(directory),terminal:observer,retirement:observer)
        group.closeIfUntransferred();try await bridgeEventually{gate.entered};group.closeIfUntransferred()
        #expect(observer.retired==0 && group.core.cleanupJobCount==1)
        #expect(throws:(any Error).self){try lifecycleStore(directory)}
        gate.release();try await bridgeEventually{observer.retired==1};try await lifecycleReopens(directory)
        #expect(LifecycleProbeHooks.state.withLock{$0.nativeCloses}==0)
    }
    @Test func wakeTerminalSignalPrecedesHungExitAndFinalRetirement()async throws{
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-life-wake-"+UUID().uuidString);defer{try? FileManager.default.removeItem(at:directory)}
        let gate=LifecycleProbeAsyncGate();LifecycleProbeHooks.state.withLock{$0.invocation=gate};defer{gate.release()}
        let observer=LifecycleRecorder();let group=OwnedCapabilityAdapterGroup(storage:try lifecycleStore(directory),terminal:observer,retirement:observer)
        let imported=ValidationGuest.Import(module:"mixer.capability.v1",name:"storage_put",parameters:[0x7f,0x7f,0x7f],result:0x7f)
        var run=GuestProgram.i(1024);run += GuestProgram.i(Int32(GuestProgram.put.count));run += GuestProgram.i(16);run += [0x10,0,0x0b]
        let module=ValidationGuest.build(memoryMinimum:1,memoryMaximum:1,imports:[imported],wake:[0,0x0b],run:run,arguments:GuestProgram.put)
        let session=try await ExperimentalCapabilitySession.prepareOwned(module:module,startupExport:"boot",configuration:.init(timeoutMilliseconds:150),policy:bridgePolicy(),adapterGroup:group).create()
        _ = try await session.startup();try await session.enableEffects();_ = try await session.invoke("run");try await bridgeEventually{gate.entered}
        try await bridgeEventually{observer.failures.count==1}
        let first=observer.failures[0]
        #expect(first.kind == .guestTrap(.unreachable) && first.operation == .wake && session.status.closed)
        #expect(observer.retired==0 && !session.status.drained && session.status.retainedExits==1)
        await #expect(throws:ExperimentalCapabilityError("closed")){try await session.invoke("run")}
        #expect(observer.failures.count==1)
        gate.release();try await bridgeEventually{observer.retired==1 && session.status.drained}
        #expect(observer.failures==[first] && session.status.acknowledgements==1 && group.core.cleanupJobCount==1)
        #expect(LifecycleProbeHooks.state.withLock{$0.nativeCloses}==1);try await lifecycleReopens(directory)
    }
    @Test func malformedCreateQuarantineClosesAdaptersWithoutRetirementOrCapacityRelease()async throws{
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-life-quarantine-"+UUID().uuidString);defer{try? FileManager.default.removeItem(at:directory)}
        LifecycleProbeHooks.state.withLock{$0.malformedCreate=true}
        let observer=LifecycleRecorder();var group:OwnedCapabilityAdapterGroup?=OwnedCapabilityAdapterGroup(storage:try lifecycleStore(directory),terminal:observer,retirement:observer)
        do{_ = try await lifecyclePrepare(group!).create();Issue.record("injected malformed create accepted")}
        catch let error as ExperimentalCapabilityError{#expect(error.failure.kind == .unknown(.malformedNativeReport) && error.failure.operation == .construction)}
        try await bridgeEventually{do{try await lifecycleReopens(directory);return true}catch{return false}}
        #expect(observer.failures.count==1 && observer.retired==0 && group!.core.cleanupJobCount==1)
        group=nil
        var held:[ExperimentalCapabilityConstruction]=[]
        for _ in 0..<15{held.append(try ExperimentalCapabilitySession.prepare(module:Data(),startupExport:"boot",policy:bridgePolicy(),adapters:InstalledCapabilityAdapters()))}
        #expect(throws:ExperimentalCapabilityError("construction_busy")){try ExperimentalCapabilitySession.prepare(module:Data(),startupExport:"boot",policy:bridgePolicy(),adapters:InstalledCapabilityAdapters())}
        #expect(observer.retired==0 && LifecycleProbeHooks.state.withLock{$0.nativeCloses}==1)
        held.removeAll()
    }
}
