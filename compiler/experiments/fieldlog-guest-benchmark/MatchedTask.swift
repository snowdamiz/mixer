import CMixerVMCapability
import Dispatch
import Foundation

struct CheckFailed: Error {
    let reason: String
}

func check(_ condition: @autoclosure () -> Bool, _ reason: String) throws {
    guard condition() else { throw CheckFailed(reason: reason) }
}

func event(_ revision: Int) -> [UInt8] {
    Array("""
    {"actionID":"task.toggle","event":"activate","nodeID":"toggle","revision":\(revision),"schemaVersion":1,"sequence":\(revision),"value":null}
    """.utf8)
}

protocol TaskPath {
    mutating func frame() throws -> Data
    mutating func activate(_ bytes: [UInt8]) throws -> Bool
}

struct NativeTask: TaskPath {
    var task = TaskCompletion()

    func frame() -> Data {
        var bytes = Data(count: task.revision == 5 ? 0 : 2048)
        let count = bytes.withUnsafeMutableBytes { task.render(into: $0) }
        bytes.count = count
        return bytes
    }

    mutating func activate(_ bytes: [UInt8]) -> Bool {
        bytes.withUnsafeBytes { task.accepts($0) } && task.activate(requireReview: true)
    }
}

final class OwnedTask: TaskPath {
    private let configuration = ExperimentalCapabilityConfiguration(memoryPages: 1, hostCalls: 0)
    private let module: Data
    private var handle: UInt64 = 0
    private var header: UInt32 = 0
    private var inputOffset: UInt32 = 0
    private var report = MixerVmReport()
    private let measureComponents: Bool
    private var writeNS: UInt64 = 0
    private var invokeNS: UInt64 = 0
    private(set) var fuel: UInt64 = 0
    var components: [UInt64] { [writeNS, invokeNS] }

    init(_ module: Data, measureComponents: Bool) {
        self.module = module
        self.measureComponents = measureComponents
    }

    func open() throws {
        var limits = configuration.vm
        var capability = configuration.capability
        let status = module.withUnsafeBytes { bytes in
            mixer_vm_capability_guest_ui_validate_v1(bytes.bindMemory(to: UInt8.self).baseAddress,
                bytes.count, &limits, &capability, &report)
        }
        try verify(status, .validation)
        let start = Array("mixer_guest_ui_start_v1".utf8)
        let created = module.withUnsafeBytes { bytes in
            mixer_vm_capability_session_create_v1(bytes.bindMemory(to: UInt8.self).baseAddress,
                bytes.count, start, start.count, &limits, &capability, &handle, &report)
        }
        try verify(created, .construction)
        try check(handle != 0, "missing owned session")
        try verify(mixer_vm_capability_session_startup_v1(handle, &report), .startup)
        guard case .i32(let address) = try NativeDiagnostics.value(report, operation: .startup),
              address > 0 else { throw CheckFailed(reason: "invalid startup header") }
        header = UInt32(address)
        try verify(mixer_vm_capability_session_enable_v1(handle, &report), .enableEffects)
    }

    func close() throws {
        try verify(mixer_vm_capability_session_close_v1(handle, &report), .close)
        try check(mixer_vm_capability_session_startup_v1(handle, &report) == 3, "stale handle admitted")
        handle = 0
    }

    deinit {
        if handle != 0 { _ = mixer_vm_capability_session_close_v1(handle, &report) }
    }

    private func verify(_ status: UInt32, _ operation: ExperimentalCapabilityFailureOperation) throws {
        try NativeDiagnostics.check(status, report, operation: operation, moduleLength: module.count,
            configuration: configuration, debugLines: status == 2 ? GuestDebugLines(module: module) : nil)
    }

    private func read(_ offset: UInt32, _ count: Int) throws -> Data {
        var result = Data(count: count)
        let status = result.withUnsafeMutableBytes {
            mixer_vm_capability_session_read_v1(handle, offset, $0.bindMemory(to: UInt8.self).baseAddress,
                count, &report)
        }
        try verify(status, .readMemory)
        return result
    }

    func frame() throws -> Data {
        let bytes = try read(header, 32)
        let words = bytes.withUnsafeBytes { raw in
            stride(from: 0, to: 32, by: 4).map {
                UInt32(littleEndian: raw.loadUnaligned(fromByteOffset: $0, as: UInt32.self))
            }
        }
        try check(header <= 65536 - 6176 && words[0] == 827_672_909 && words[1] == 32
            && words[3] > 0 && words[3] <= 2048
            && words[4] == header + 32 && words[5] == 4096 && words[2] == words[4] + words[5]
            && words[2] <= 65536 - 2048 && words[6] == 0 && words[7] == 0, "invalid compact header")
        inputOffset = words[4]
        return try read(words[2], Int(words[3]))
    }

    func activate(_ bytes: [UInt8]) throws -> Bool {
        let writeStart = measureComponents ? DispatchTime.now().uptimeNanoseconds : 0
        try verify(mixer_vm_capability_session_write_v1(handle, inputOffset, bytes, bytes.count, &report),
            .writeMemory)
        let invokeStart = measureComponents ? DispatchTime.now().uptimeNanoseconds : 0
        let name = Array("mixer_guest_ui_event_v1".utf8)
        var length = ExperimentalVMValue.i32(Int32(bytes.count)).native
        let status = mixer_vm_capability_session_invoke_v1(handle, name, name.count, &length, 1, &report)
        if measureComponents {
            writeNS = invokeStart - writeStart
            invokeNS = DispatchTime.now().uptimeNanoseconds - invokeStart
        }
        try verify(status, .invocation)
        fuel = report.fuel_used
        guard case .i32(let code) = try NativeDiagnostics.value(report, operation: .invocation),
              code == 0 || code == 1 else { throw CheckFailed(reason: "unexpected guest event result") }
        return code == 0
    }
}

private struct Sample: Encodable {
    var frames: [Data]
    var turnNS: [UInt64] = []
    var componentNS: [[UInt64]] = []
    var fuel: [UInt64] = []
    var refusals = 0
    var diagnostic: String?
    var closed = false
}

private func exercise(_ path: inout some TaskPath, mode: String) throws -> Sample {
    let controls = mode.hasSuffix("-control") || mode == "native-fault"
    let inputs = (1...4).map(event)
    var sample = Sample(frames: [try path.frame()])
    for index in 0..<3 {
        if controls && index == 1 {
            for invalid in [inputs[0], inputs[1] + [10]] {
                let accepted = try path.activate(invalid)
                let unchanged = try path.frame() == sample.frames.last
                try check(!accepted && unchanged, "refusal changed the frame")
                sample.refusals += 1
            }
        }
        let start = DispatchTime.now().uptimeNanoseconds
        let accepted = try path.activate(inputs[index])
        let frame = try path.frame()
        let elapsed = DispatchTime.now().uptimeNanoseconds - start
        try check(accepted && elapsed > 0, "missing accepted turn")
        sample.frames.append(frame)
        sample.turnNS.append(elapsed)
        if let owned = path as? OwnedTask {
            sample.fuel.append(owned.fuel)
            if mode == "guest-profile" { sample.componentNS.append(owned.components) }
        }
    }
    if mode == "guest-control" || mode == "native-fault" {
        do {
            let accepted = try path.activate(inputs[3])
            try check(accepted, "fourth input was refused before the diagnostic")
            _ = try path.frame()
            throw CheckFailed(reason: "diagnostic turn returned a frame")
        } catch let error as ExperimentalCapabilityError {
            let failure = error.failure
            try check(failure.kind == .guestTrap(.unreachable) && failure.operation == .invocation
                && failure.nativeStatus == 2 && failure.location?.source?.file == "TaskCompletion.swift"
                && failure.location?.source?.line == 94 && failure.location?.source?.column == 9,
                "unexpected source diagnostic: \(error)")
            guard let location = failure.location else { throw CheckFailed(reason: "missing native coordinates") }
            sample.diagnostic = "\(error) [function=\(location.functionIndex ?? .max) wasmOffset=\(location.byteOffset)]"
        }
    }
    return sample
}

#if !SWIFT_SUPPORT_MATRIX
@main private enum MatchedTask {
    static func main() {
        do {
            let args = CommandLine.arguments
            try check(args.count == 3, "expected a mode and guest path")
            let mode = args[1]
            var sample: Sample
            switch mode {
            case "native", "native-control", "native-fault":
                var native = NativeTask()
                sample = try exercise(&native, mode: mode)
            case "guest", "guest-control", "guest-profile":
                var owned = OwnedTask(try Data(contentsOf: URL(fileURLWithPath: args[2])),
                    measureComponents: mode == "guest-profile")
                try owned.open()
                sample = try exercise(&owned, mode: mode)
                try owned.close()
                sample.closed = true
            default:
                throw CheckFailed(reason: "unknown mode")
            }
            print(String(decoding: try JSONEncoder().encode(sample), as: UTF8.self))
        } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(1)
        }
    }
}
#endif
