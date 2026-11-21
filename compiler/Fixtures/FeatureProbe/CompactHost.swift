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

private struct NativePreview: TaskPath {
    private let render: (UnsafeRawBufferPointer, UnsafeMutableRawBufferPointer) -> Bool
    private var result: Data

    init(outputSize: Int, render: @escaping (UnsafeRawBufferPointer, UnsafeMutableRawBufferPointer) -> Bool) {
        self.render = render
        result = Data(count: outputSize)
    }

    func frame() -> Data { result }

    mutating func activate(_ bytes: [UInt8]) -> Bool {
        bytes.withUnsafeBytes { input in
            result.withUnsafeMutableBytes { render(input, $0) }
        }
    }
}

private struct PreviewObservation: Encodable {
    let frames: [Data]
    let truncatedRefusedWithoutPublication: Bool
    let guestFuel: [UInt64]
    let closed: Bool
}

private func exercisePreview(
    _ path: inout some TaskPath, inputs: Data, width: Int
) throws -> PreviewObservation {
    try check(!inputs.isEmpty && inputs.count <= 8 * width && inputs.count.isMultiple(of: width),
              "invalid preview case file")
    var frames = [try path.frame()]
    var guestFuel: [UInt64] = []
    let owned = path as? OwnedTask
    for offset in stride(from: 0, to: inputs.count, by: width) {
        let accepted = try path.activate(Array(inputs[offset ..< offset + width]))
        try check(accepted, "valid preview input refused at offset \(offset)")
        frames.append(try path.frame())
        if let owned { guestFuel.append(owned.fuel) }
    }
    let refused = try !path.activate(Array(inputs.prefix(width - 1)))
    let unchanged = try path.frame() == frames.last
    try check(refused && unchanged, "truncated preview input changed the result")
    try owned?.close()
    return PreviewObservation(frames: frames, truncatedRefusedWithoutPublication: refused,
                              guestFuel: guestFuel, closed: owned != nil)
}

@main private enum CompactHost {
    static func main() throws {
        let args = CommandLine.arguments
        try check(args.count >= 3, "expected a mode and Wasm path")
        let mode = args[1]
        let preview = ["floating-native", "floating-guest", "associated-native", "associated-guest"].contains(mode)
        try check(args.count == (preview ? 4 : 3), "unexpected replay arguments")
        let encoder = JSONEncoder()
        let result: Data
        switch mode {
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
        case "floating-native", "associated-native":
            let floating = mode == "floating-native"
            let width = floating ? FloatingPointPreview.inputSize : AssociatedTypesPreview.inputSize
            var path = floating
                ? NativePreview(outputSize: FloatingPointPreview.outputSize, render: FloatingPointPreview.render)
                : NativePreview(outputSize: AssociatedTypesPreview.outputSize, render: AssociatedTypesPreview.render)
            let inputs = try Data(contentsOf: URL(fileURLWithPath: args[3]))
            result = try encoder.encode(exercisePreview(&path, inputs: inputs, width: width))
        case "floating-guest", "associated-guest":
            let width = mode == "floating-guest" ? FloatingPointPreview.inputSize : AssociatedTypesPreview.inputSize
            var path = OwnedTask(try Data(contentsOf: URL(fileURLWithPath: args[2])), measureComponents: false)
            let inputs = try Data(contentsOf: URL(fileURLWithPath: args[3]))
            try path.open()
            result = try encoder.encode(exercisePreview(&path, inputs: inputs, width: width))
        default:
            throw CheckFailed(reason: "unknown mode")
        }
        print(String(decoding: result, as: UTF8.self))
    }
}
