import Foundation
import MixerCapabilities

// Separate public consumer: the existing capability-probe and envelopes stay intact.
do {
    guard CommandLine.arguments.count == 3,
          let tag = UInt32(CommandLine.arguments[2]),
          let operation = GuestCapabilityOperationV1(rawValue: tag) else {
        throw CapabilityWireError.invalid("probe operation")
    }
    var data = Data()
    // Permit the contract's one-byte-over-limit case to reach the actual codec.
    // This offline probe's larger input ceiling is not a transport limit.
    while let chunk = try FileHandle.standardInput.read(upToCount: min(8192, 1_048_577 - data.count)), !chunk.isEmpty {
        data.append(chunk)
        guard data.count <= 1_048_576 else { throw CapabilityWireError.invalid("probe input bound") }
    }
    let output: Data
    switch CommandLine.arguments[1] {
    case "arguments":
        output = try GuestCapabilityTransportCodecV1.encodeArguments(
            GuestCapabilityTransportCodecV1.decodeArguments(data, operation: operation))
    case "completion":
        output = try GuestCapabilityTransportCodecV1.encodeCompletion(
            GuestCapabilityTransportCodecV1.decodeCompletion(data, expectedOperation: operation), operation: operation)
    default: throw CapabilityWireError.invalid("probe mode")
    }
    FileHandle.standardOutput.write(output)
} catch {
    FileHandle.standardError.write(Data("guest transport probe rejected input\n".utf8))
    exit(1)
}
