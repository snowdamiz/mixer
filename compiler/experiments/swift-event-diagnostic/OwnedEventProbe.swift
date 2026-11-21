import CMixerVMCapability
import Foundation

private struct ProbeFailure: Error {
    let stage: String
}

private func require(_ condition: Bool, _ stage: String) throws {
    guard condition else { throw ProbeFailure(stage: stage) }
}

private struct Observation: Encodable {
    let metadataIdentityMatched: Bool
    let initialDocument: String
    let eventResults: [Int32]
    let nativeStatus: UInt32
    let code: String
    let functionIndex: UInt32
    let absoluteOffset: UInt32
    let fuelUsed: UInt64
    let file: String?
    let line: UInt32?
    let column: UInt32?
    let closedHandleStatus: UInt32
}

private func replay(_ module: Data, _ candidate: Data) throws -> Observation {
    let configuration = ExperimentalCapabilityConfiguration(memoryPages: 1, hostCalls: 0)
    var limits = configuration.vm
    var capability = configuration.capability
    var report = MixerVmReport()
    var handle: UInt64 = 0
    let debugLines = candidate == module ? GuestDebugLines(module: module) : nil
    func verify(_ status: UInt32, _ operation: ExperimentalCapabilityFailureOperation) throws {
        try NativeDiagnostics.check(status, report, operation: operation, moduleLength: module.count,
                                    configuration: configuration, debugLines: debugLines)
    }
    let start = Array("mixer_guest_ui_start_v1".utf8)
    let event = Array("mixer_guest_ui_event_v1".utf8)
    try module.withUnsafeBytes { raw in
        let bytes = raw.bindMemory(to: UInt8.self)
        try verify(mixer_vm_capability_guest_ui_validate_v1(bytes.baseAddress, bytes.count,
                                                          &limits, &capability, &report), .validation)
        try verify(mixer_vm_capability_session_create_v1(bytes.baseAddress, bytes.count,
            start, start.count, &limits, &capability, &handle, &report), .construction)
    }
    defer { if handle != 0 { _ = mixer_vm_capability_session_close_v1(handle, &report) } }
    try verify(mixer_vm_capability_session_startup_v1(handle, &report), .startup)
    guard case .i32(let address) = try NativeDiagnostics.value(report, operation: .startup),
          address > 0 else { throw ProbeFailure(stage: "startup address") }
    try verify(mixer_vm_capability_session_enable_v1(handle, &report), .enableEffects)

    func read(_ offset: UInt32, count: Int) throws -> Data {
        var bytes = Data(count: count)
        let status = bytes.withUnsafeMutableBytes { raw in
            mixer_vm_capability_session_read_v1(handle, offset, raw.bindMemory(to: UInt8.self).baseAddress,
                                               count, &report)
        }
        try verify(status, .readMemory)
        return bytes
    }

    let header = try read(UInt32(address), count: 32).withUnsafeBytes { raw in
        stride(from: 0, to: 32, by: 4).map {
            UInt32(littleEndian: raw.loadUnaligned(fromByteOffset: $0, as: UInt32.self))
        }
    }
    try require(header[0] == 827_672_909 && header[1] == 32 && header[4] == UInt32(address) + 32
                && header[5] == 128 && header[2] == header[4] + header[5]
                && (1...224).contains(header[3]) && header[6] == 0 && header[7] == 0, "control header")
    let initial = try read(header[2], count: Int(header[3]))
    guard let document = String(data: initial, encoding: .utf8) else {
        throw ProbeFailure(stage: "document encoding")
    }
    func activate(sequence: Int, suffix: String = "") throws -> Int32 {
        let input = Array((#"{"actionID":"validate","event":"activate","nodeID":"button","revision":1,"schemaVersion":1,"sequence":"#
                         + String(sequence) + #","value":null}"# + suffix).utf8)
        try verify(mixer_vm_capability_session_write_v1(handle, header[4], input, input.count, &report),
                   .writeMemory)
        var length = ExperimentalVMValue.i32(Int32(input.count)).native
        try verify(mixer_vm_capability_session_invoke_v1(handle, event, event.count, &length, 1, &report),
                   .invocation)
        guard case .i32(let result) = try NativeDiagnostics.value(report, operation: .invocation) else {
            throw ProbeFailure(stage: "event result")
        }
        return result
    }

    let normal = try [activate(sequence: 1), activate(sequence: 2, suffix: "\n")]
    try require(normal == [0, 1] && read(header[2], count: initial.count) == initial, "nonfault event")
    do {
        _ = try activate(sequence: 2)
        throw ProbeFailure(stage: "faulting event returned")
    } catch let error as ExperimentalCapabilityError {
        let failure = error.failure
        guard failure.kind == .guestTrap(.unreachable), failure.operation == .invocation,
              failure.nativeStatus == 2, let location = failure.location,
              let function = location.functionIndex, report.fuel_used > 0, report.host_calls_used == 0 else {
            throw error
        }
        let fuel = report.fuel_used
        try verify(mixer_vm_capability_session_close_v1(handle, &report), .close)
        let stale = mixer_vm_capability_session_startup_v1(handle, &report)
        handle = 0
        try require(stale == 3, "closed handle")
        return Observation(metadataIdentityMatched: candidate == module, initialDocument: document,
                           eventResults: normal, nativeStatus: 2, code: failure.code, functionIndex: function,
                           absoluteOffset: location.byteOffset, fuelUsed: fuel, file: location.source?.file,
                           line: location.source?.line, column: location.source?.column, closedHandleStatus: stale)
    }
}

@main
private enum Probe {
    static func main() {
        do {
            let args = CommandLine.arguments.dropFirst()
            try require(args.count == 4, "expected diagnostic, stripped, alternate, and wrong-table modules")
            let modules = try args.map { try Data(contentsOf: URL(fileURLWithPath: $0)) }
            let diagnostic = modules[0], stripped = modules[1], alternate = modules[2]
            let results = try [
                "matched": replay(diagnostic, diagnostic),
                "stripped": replay(stripped, stripped),
                "wrongTable": replay(diagnostic, modules[3]),
                "alternate": replay(alternate, alternate),
            ]
            print(String(decoding: try JSONEncoder().encode(results), as: UTF8.self))
        } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(1)
        }
    }
}
