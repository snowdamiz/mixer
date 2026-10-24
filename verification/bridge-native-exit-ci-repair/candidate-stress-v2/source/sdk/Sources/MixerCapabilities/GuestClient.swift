import Foundation

/// Typed encoded-value adapter for an embedding's owned capability imports. This
/// is not a Wasm loader or a claim that the full Swift guest executes in the VM.
public struct GuestCapabilityClient: Sendable {
    public typealias Reserve = @Sendable () async throws -> CapabilityRequestID
    public typealias Invoke = @Sendable (Data) async throws -> Data
    public typealias Cancel = @Sendable (Data) async -> Void
    private let reserve: Reserve
    private let invoke: Invoke
    private let cancel: Cancel
    public init(reserve: @escaping Reserve, invoke: @escaping Invoke, cancel: @escaping Cancel) {
        self.reserve = reserve; self.invoke = invoke; self.cancel = cancel
    }
    func perform(_ operation: CapabilityOperation) async throws -> CapabilityResult {
        _ = try CapabilityOperation.decode(capability: operation.capabilityID, operation: operation.operationID, wire: operation.wire)
        try Task.checkCancellation()
        let call = CapabilityCall(identity: try await reserve(), operation: operation)
        let bytes = try CapabilityCodec.encodeCall(call)
        let cancellation = try CapabilityCodec.encodeCancel(call)
        if Task.isCancelled { await cancel(cancellation); throw CapabilityFailure.cancelled }
        return try await withTaskCancellationHandler {
            let response: Data
            do { response = try await invoke(bytes) }
            catch { if Task.isCancelled { throw CapabilityFailure.cancelled }; throw error }
            switch try CapabilityCodec.decodeCompletion(response, expected: call).outcome {
            case .success(let value): return value
            case .failure(let failure): throw failure
            }
        } onCancel: { Task { await cancel(cancellation) } }
    }
}
