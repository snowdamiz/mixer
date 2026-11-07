// Generated typed guest value adapters; embedding supplies owned imports.
extension GuestCapabilityClient {
    public func http(_ arguments: HTTPRequestArguments) async throws -> HTTPResponse {
        guard case .http(let response) = try await perform(.http(arguments)) else { throw CapabilityWireError.invalid("result binding") }; return response
    }
    public func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        guard case .get(let response) = try await perform(.get(arguments)) else { throw CapabilityWireError.invalid("result binding") }; return response
    }
    public func put(_ arguments: KVPutArguments) async throws -> KVMutationResponse {
        guard case .put(let response) = try await perform(.put(arguments)) else { throw CapabilityWireError.invalid("result binding") }; return response
    }
    public func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        guard case .delete(let response) = try await perform(.delete(arguments)) else { throw CapabilityWireError.invalid("result binding") }; return response
    }
}
