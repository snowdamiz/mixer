import Foundation
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
        print("SPI concrete-group constructor failure and retirement observed")
    }
    private enum Failure:Error{case unexpectedSuccess,missingRetirement}
}
