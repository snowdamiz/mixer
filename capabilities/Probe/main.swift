import Foundation
import MixerCapabilities

do {
    let mode = CommandLine.arguments.dropFirst().first ?? "roundtrip"
    var data = Data()
    while let chunk = try FileHandle.standardInput.read(upToCount: min(8192, 524289 - data.count)), !chunk.isEmpty {
        data.append(chunk); if data.count > 524288 { throw CapabilityWireError.invalid("probe bound") }
    }
    guard data.count <= 524288 else { throw CapabilityWireError.invalid("probe bound") }
    let output: Data
    if mode == "decode-completion" {
        guard CommandLine.arguments.count == 3, case .call(let expected) = try CapabilityCodec.decodeInbound(Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[2]))) else { throw CapabilityWireError.invalid("probe expected") }
        output = try CapabilityCodec.encodeCompletion(CapabilityCodec.decodeCompletion(data, expected: expected))
    } else {
        let inbound = try CapabilityCodec.decodeInbound(data)
        switch inbound {
        case .cancel(let cancellation): output = try CapabilityCodec.encodeCancellation(cancellation)
        case .call(let call):
            if mode == "complete" {
                let result: CapabilityResult
                switch call.operation {
                case .http: result = .http(HTTPResponse(status: 200, headers: [], bodyBase64: "Zml4dHVyZQ=="))
                case .get: result = .get(KVGetResponse(found: true, valueBase64: "Zml4dHVyZQ=="))
                case .put: result = .put(KVMutationResponse(committed: true))
                case .delete: result = .delete(KVMutationResponse(committed: true))
                }
                output = try CapabilityCodec.encodeCompletion(CapabilityCompletion(call: call, outcome: .success(result)))
            } else if mode == "roundtrip" { output = try CapabilityCodec.encodeCall(call) }
            else { throw CapabilityWireError.invalid("probe mode") }
        }
    }
    FileHandle.standardOutput.write(output)
} catch { FileHandle.standardError.write(Data("capability probe rejected input\n".utf8)); exit(1) }
