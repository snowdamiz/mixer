import Foundation
import CMixerVMCapability

// Derived-copy control only: this file is never a production package input.
enum ValidationProbeHooks {
    enum Mode { case ordinary, malformed, held(ValidationProbeGate) }
    static let mode = Locked(Mode.ordinary)
    static func afterReturn(_ report: inout MixerVmReport) {
        switch mode.withLock({$0}) {
        case .ordinary: break
        case .malformed: report.abi_version = 2
        case .held(let gate): gate.hold()
        }
    }
}
final class ValidationProbeGate: @unchecked Sendable {
    private let condition=NSCondition()
    private var open=false
    private var started=false
    func hold() {
        condition.lock();started=true
        let end=Date().addingTimeInterval(5)
        while !open { if !condition.wait(until:end) { break } }
        condition.unlock()
    }
    func release() { condition.lock();open=true;condition.broadcast();condition.unlock() }
    var entered:Bool { condition.lock();defer{condition.unlock()};return started }
}
