import Foundation
import Dispatch
import MixerCapabilities
@_spi(CapabilityLifecycle) import MixerExperimentalCapabilityRuntime

private final class Sink: CapabilityBridgeTerminalObserver, CapabilityBridgeRetirementObserver, @unchecked Sendable {
    private let lock=NSLock()
    private var terminal:ExperimentalCapabilityFailure?
    private var retired=0
    func recordTerminalFailure(_ failure:ExperimentalCapabilityFailure){lock.lock();if terminal==nil{terminal=failure};lock.unlock()}
    func recordRetired(){lock.lock();retired += 1;lock.unlock()}
    var snapshot:(ExperimentalCapabilityFailure?,Int){lock.lock();defer{lock.unlock()};return(terminal,retired)}
}
@main struct LifecycleCrossProbe {
    static func main()async throws{
        let sink=Sink(), group=OwnedCapabilityAdapterGroup(terminal:Sink(),retirement:Sink())
        group.closeIfUntransferred() // Separate unused group also owns one bounded cleanup.
        let owned=OwnedCapabilityAdapterGroup(terminal:sink,retirement:sink)
        let construction=try ExperimentalCapabilitySession.prepareOwned(module:Data(),startupExport:"boot",policy:CapabilityPolicy(installed:[],manifest:[]),adapterGroup:owned)
        do{_ = try await construction.create();throw Failure.unexpectedSuccess}
        catch let error as ExperimentalCapabilityError{
            guard error.failure.kind == .validation(.malformed),error.failure.operation == .construction else{throw error}
        }
        for _ in 0..<200{if sink.snapshot.1==1{break};try await Task.sleep(for:.milliseconds(5))}
        let result=sink.snapshot
        guard result.1==1,result.0?.kind == .validation(.malformed) else{throw Failure.missingRetirement}
        let liveSink=Sink(), liveGroup=OwnedCapabilityAdapterGroup(terminal:liveSink,retirement:liveSink)
        // Original no-effect Wasm: empty boot/wake exports and required zero-page memory.
        let wake=Array("mixer_guest_capability_ready_v1".utf8)
        let exports:[UInt8]=[2,4,98,111,111,116,0,0,UInt8(wake.count)] + wake + [0,1]
        var bytes:[UInt8]=[0,97,115,109,1,0,0,0,1,4,1,96,0,0,3,3,2,0,0,5,4,1,1,0,0]
        bytes += [7,UInt8(exports.count)] + exports
        bytes += [10,7,2,2,0,11,2,0,11]
        let module=Data(bytes)
        let session=try await ExperimentalCapabilitySession.prepareOwned(module:module,startupExport:"boot",policy:CapabilityPolicy(installed:[],manifest:[]),adapterGroup:liveGroup).create()
        _ = try await session.startup()
        try await session.enableOwnedEffects(noLaterThanUptimeNanoseconds:DispatchTime.now().uptimeNanoseconds + 5_000_000_000)
        session.close()
        for _ in 0..<200{if liveSink.snapshot.1==1{break};try await Task.sleep(for:.milliseconds(5))}
        guard liveSink.snapshot.1==1,liveSink.snapshot.0==nil else{throw Failure.missingRetirement}
        print("SPI concrete-group constructor failure and retirement observed")
        print("SPI owned enable deadline linked and admitted before cutoff")
    }
    private enum Failure:Error{case unexpectedSuccess,missingRetirement}
}
