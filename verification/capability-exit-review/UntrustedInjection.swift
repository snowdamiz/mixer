import Foundation
import MixerCapabilities
struct SubstituteHTTP: BoundedHTTPServing {
    func request(_ arguments: HTTPRequestArguments) async throws -> HTTPResponse { fatalError("Must not be installed") }
}
struct SubstituteStore: AppPrivateKeyValueServing {
    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse { fatalError("Must not be installed") }
    func put(_ arguments: KVPutArguments) async throws -> KVMutationResponse { fatalError("Must not be installed") }
    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse { fatalError("Must not be installed") }
}
let substitute = InstalledCapabilityAdapters(http: SubstituteHTTP(), storage: SubstituteStore())
