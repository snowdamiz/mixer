import CMixerVMCapability
import Foundation

private struct Observation: Encodable {
    let frames: [Data]
    let truncatedRefusals: Int
    let mismatchedRefusals: Int
    let closed: Bool
}

private func exercise(_ task: some TaskPath, closed: () throws -> Bool) throws -> Observation {
    var task = task
    var frames = [try task.frame()]
    for revision in 1...3 {
        let valid = event(revision)
        try check(valid.last == 0x7d, "missing closing brace in fixture")
        let truncated = Array(valid.dropLast())
        for invalid in [truncated, truncated + [0x5d]] {
            let accepted = try task.activate(invalid)
            let after = try task.frame()
            try check(!accepted && after == frames.last, "refused event changed revision \(revision)")
        }
        let accepted = try task.activate(valid)
        try check(accepted, "current event refused at revision \(revision)")
        frames.append(try task.frame())
    }
    return Observation(frames: frames, truncatedRefusals: 3, mismatchedRefusals: 3, closed: try closed())
}

private struct Refusal: Encodable {
    let status: UInt32
    let code: String
    let message: String
    let offset: UInt32
}

private func describeRefusal(_ status: UInt32, _ report: MixerVmReport) throws -> Refusal {
    try check(status == 1 && report.status == status && report.abi_version == 1 && report.reserved == 0
        && report.value_type == 0 && report.value == 0 && report.fuel_used == 0
        && report.host_calls_used == 0 && report.function == .max, "unexpected validation report")
    func string<T>(_ field: T) -> String {
        withUnsafeBytes(of: field) { String(decoding: $0.prefix { $0 != 0 }, as: UTF8.self) }
    }
    return Refusal(status: status, code: string(report.code), message: string(report.message), offset: report.offset)
}

private func validateSharedMemory(_ module: Data) throws -> [String: Refusal] {
    let configuration = ExperimentalCapabilityConfiguration(memoryPages: 1, hostCalls: 0)
    var limits = configuration.vm
    var capability = configuration.capability
    var report = MixerVmReport()
    var handle: UInt64 = 0
    defer {
        if handle != 0 { _ = mixer_vm_capability_session_close_v1(handle, &report) }
    }
    return try module.withUnsafeBytes { raw in
        let bytes = raw.bindMemory(to: UInt8.self)
        let status = mixer_vm_capability_guest_ui_validate_v1(
            bytes.baseAddress, bytes.count, &limits, &capability, &report)
        let validation = try describeRefusal(status, report)
        let start = Array("mixer_guest_ui_start_v1".utf8)
        report = MixerVmReport()
        let created = mixer_vm_capability_session_create_v1(
            bytes.baseAddress, bytes.count, start, start.count, &limits, &capability, &handle, &report)
        try check(handle == 0, "session published a handle for the shared-memory module")
        return ["validation": validation, "construction": try describeRefusal(created, report)]
    }
}

@main private enum CompactHost {
    static func main() throws {
        let args = CommandLine.arguments
        try check(args.count == 3, "expected a mode and Wasm path")
        let encoder = JSONEncoder()
        let result: Data
        switch args[1] {
        case "native":
            result = try encoder.encode(exercise(NativeTask()) { false })
        case "guest":
            let owned = OwnedTask(try Data(contentsOf: URL(fileURLWithPath: args[2])), measureComponents: false)
            try owned.open()
            result = try encoder.encode(exercise(owned) {
                try owned.close()
                return true
            })
        case "shared-memory":
            result = try encoder.encode(validateSharedMemory(Data(contentsOf: URL(fileURLWithPath: args[2]))))
        default:
            throw CheckFailed(reason: "unknown mode")
        }
        print(String(decoding: result, as: UTF8.self))
    }
}
