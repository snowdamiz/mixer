#if !os(WASI)
import Foundation

/// Closed native adapters with request-specific cleanup observation. This value
/// does not establish release identity or grant authority; CapabilityHost still
/// applies policy. Arbitrary service conformers/HTTP closures are not eligible.
public struct InstalledCapabilityAdapters: Sendable {
    private let http: URLSessionHTTPTransport?
    private let storage: AppPrivateKeyValueStore?
    private let hooks: InstalledCapabilityExecutionHooks

    public init(http: URLSessionHTTPTransport? = nil, storage: AppPrivateKeyValueStore? = nil) {
        self.init(http: http, storage: storage, hooks: .none)
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
