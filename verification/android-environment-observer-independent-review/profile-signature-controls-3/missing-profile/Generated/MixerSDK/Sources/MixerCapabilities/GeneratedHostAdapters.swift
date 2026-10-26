// Generated typed host protocols/dispatch; no guest-selected native lookup.
import Foundation
public protocol BoundedHTTPServing: Sendable {
    func request(_ arguments: HTTPRequestArguments) async throws -> HTTPResponse
}
public protocol AppPrivateKeyValueServing: Sendable {
    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse
    func put(_ arguments: KVPutArguments) async throws -> KVMutationResponse
    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse
}
enum GeneratedCapabilityDispatch {
    static func invoke(_ operation: CapabilityOperation, http: CapabilityHost.HTTPTransport?, storage: (any AppPrivateKeyValueServing)?) async throws -> CapabilityResult {
        switch operation {
        case .http(let arguments): guard let http else { throw CapabilityFailure.unavailable }; return .http(try await http(arguments))
        case .get(let arguments): guard let storage else { throw CapabilityFailure.unavailable }; return .get(try await storage.get(arguments))
        case .put(let arguments): guard let storage else { throw CapabilityFailure.unavailable }; return .put(try await storage.put(arguments))
        case .delete(let arguments): guard let storage else { throw CapabilityFailure.unavailable }; return .delete(try await storage.delete(arguments))
        }
    }
}
