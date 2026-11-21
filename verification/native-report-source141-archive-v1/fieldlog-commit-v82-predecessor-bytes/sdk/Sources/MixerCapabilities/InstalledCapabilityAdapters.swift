#if !os(WASI)
import Foundation

/// The embedding owns the repository across launches. It must check both
/// limits in the same transaction as each mutation that can grow storage.
public protocol InstalledApplicationStorageServing: Sendable {
    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse
    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse
    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse
}

@_spi(InstalledApplicationStorage)
public struct InstalledApplicationStorageAdapter: AppPrivateKeyValueServing {
    private let service: any InstalledApplicationStorageServing
    private let maximumTotalBytes: Int
    private let maximumEntries: Int

    public init(service: any InstalledApplicationStorageServing, maximumTotalBytes: Int, maximumEntries: Int) {
        self.service = service
        self.maximumTotalBytes = maximumTotalBytes
        self.maximumEntries = maximumEntries
    }
    public func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        try await service.get(arguments)
    }
    public func put(_ arguments: KVPutArguments) async throws -> KVMutationResponse {
        try await service.put(arguments, maximumTotalBytes: maximumTotalBytes, maximumEntries: maximumEntries)
    }
    public func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        try await service.delete(arguments)
    }
}

/// Closed native adapters with request-specific cleanup observation. This value
/// does not establish release identity or grant authority; CapabilityHost still
/// applies policy. The installed owner can supply app-owned storage through SPI.
public struct InstalledCapabilityAdapters: Sendable {
    private let http: URLSessionHTTPTransport?
    private let storage: (any AppPrivateKeyValueServing)?
    private let hooks: InstalledCapabilityExecutionHooks

    public init(http: URLSessionHTTPTransport? = nil, storage: AppPrivateKeyValueStore? = nil) {
        self.init(http: http, storage: storage, hooks: .none)
    }

    @_spi(InstalledApplicationStorage)
    public init(http: URLSessionHTTPTransport?, applicationStorage: InstalledApplicationStorageAdapter) {
        self.http = http; self.storage = applicationStorage; self.hooks = .none
    }

    // Scheduling controls for deterministic lifecycle tests only. These never
    // replace the concrete adapter or introduce external cleanup authority.
    init(http: URLSessionHTTPTransport? = nil, storage: AppPrivateKeyValueStore? = nil,
         hooks: InstalledCapabilityExecutionHooks) {
        self.http = http; self.storage = storage; self.hooks = hooks
    }

    func invoke(_ operation: CapabilityOperation, lease: CapabilityExitLease) async throws -> CapabilityResult {
        await hooks.beforeInvocation?()
        do { try Task.checkCancellation() }
        catch { lease.adapterExited(); throw error }
        let result: CapabilityResult
        switch operation {
        case .http(let arguments):
            guard let http else { lease.adapterExited(); throw CapabilityFailure.unavailable }
            result = .http(try await http.request(arguments, didExit: { lease.adapterExited() }))
        case .get(let arguments):
            defer { lease.adapterExited() }
            guard let storage else { throw CapabilityFailure.unavailable }
            result = .get(try await storage.get(arguments))
        case .put(let arguments):
            defer { lease.adapterExited() }
            guard let storage else { throw CapabilityFailure.unavailable }
            result = .put(try await storage.put(arguments))
        case .delete(let arguments):
            defer { lease.adapterExited() }
            guard let storage else { throw CapabilityFailure.unavailable }
            result = .delete(try await storage.delete(arguments))
        }
        await hooks.afterInvocation?()
        return result
    }
}

struct InstalledCapabilityExecutionHooks: Sendable {
    var beforeInvocation: (@Sendable () async -> Void)?
    var afterInvocation: (@Sendable () async -> Void)?
    static let none = InstalledCapabilityExecutionHooks()
}
#endif
