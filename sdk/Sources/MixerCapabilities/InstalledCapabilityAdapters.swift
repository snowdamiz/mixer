/// Host provenance for the one scoped read taken from a validated V1 event turn.
@_spi(InstalledApplicationStorage)
public struct InstalledGuestUICommitEvent: Sendable {
    public let generation: UInt64
    public let sequence: UInt64
    public let turnSerial: UInt64
    public let displayedRevision: UInt64
    public let nodeID: String
    public let actionID: String
    private let live: @Sendable () -> Bool
    #if !os(WASI)
    let continuation = InstalledGuestUICommitContinuation()
    #endif

    public init(generation: UInt64, sequence: UInt64, turnSerial: UInt64, displayedRevision: UInt64,
                nodeID: String, actionID: String, isLive: @escaping @Sendable () -> Bool) {
        self.generation = generation; self.sequence = sequence; self.turnSerial = turnSerial
        self.displayedRevision = displayedRevision; self.nodeID = nodeID; self.actionID = actionID
        self.live = isLive
    }

    /// Samples the original owner's effect admission, including after a suspension.
    public var isLive: Bool { live() }

    #if !os(WASI)
    /// The owning bridge calls this only after posting the exact successful
    /// result to the originating native request.
    public func didPostFacts() -> Bool {
        continuation.withLock { state in
            guard case .prepared(let commit) = state, isLive else { return false }
            state = .posted(commit)
            return true
        }
    }

    public func didConsumeFacts() -> Bool {
        continuation.withLock { state in
            guard case .posted(let commit) = state, isLive else { return false }
            state = .delivered(commit)
            return true
        }
    }

    public func invalidateCommit() {
        continuation.withLock { state in
            if case .consumed = state { return }
            state = .finished
        }
    }
    #endif
}

#if !os(WASI)
import Foundation

/// The embedding owns the repository across launches. It must check both
/// limits in the same transaction as each mutation that can grow storage.
public protocol InstalledApplicationStorageServing: Sendable {
    func get(_ arguments: KVGetArguments) async throws -> KVGetResponse
    func put(_ arguments: KVPutArguments, maximumTotalBytes: Int, maximumEntries: Int) async throws -> KVMutationResponse
    func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse
}

/// One installed development action and its closed storage commands.
@_spi(InstalledApplicationStorage)
public struct InstalledGuestUICommitFacts: Sendable {
    public let arguments: KVGetArguments
    public let nodeID: String
    public let actionID: String
    public let commitArguments: KVPutArguments?
    fileprivate let read: @Sendable (InstalledGuestUICommitEvent) async throws -> InstalledGuestUICommitRead

    /// A retained facts lease and its same-turn put each reserve one slot
    /// and up to 512 KiB each for arguments and completion in the native mailbox.
    public func supportsTransport(maximumRequests: UInt32, reservationBytes: UInt64) -> Bool {
        commitArguments == nil || (maximumRequests >= 2 && reservationBytes >= 2_097_152)
    }

    public init(arguments: KVGetArguments, nodeID: String, actionID: String,
                read: @escaping @Sendable (InstalledGuestUICommitEvent) async throws -> KVGetResponse) {
        self.arguments = arguments; self.nodeID = nodeID; self.actionID = actionID
        self.commitArguments = nil
        self.read = { .init(response: try await read($0)) }
    }

    public init(arguments: KVGetArguments, nodeID: String, actionID: String, commitArguments: KVPutArguments,
                read: @escaping @Sendable (InstalledGuestUICommitEvent) async throws -> InstalledGuestUICommitRead) {
        self.arguments = arguments; self.nodeID = nodeID; self.actionID = actionID
        self.commitArguments = commitArguments; self.read = read
    }
}

@_spi(InstalledApplicationStorage)
public struct InstalledApplicationStorageAdapter: AppPrivateKeyValueServing {
    private let service: any InstalledApplicationStorageServing
    private let maximumTotalBytes: Int
    private let maximumEntries: Int
    fileprivate let guestUICommitFacts: InstalledGuestUICommitFacts?

    public init(service: any InstalledApplicationStorageServing, maximumTotalBytes: Int, maximumEntries: Int) {
        self.init(service: service, maximumTotalBytes: maximumTotalBytes, maximumEntries: maximumEntries,
                  guestUICommitFacts: nil)
    }
    public init(service: any InstalledApplicationStorageServing, maximumTotalBytes: Int, maximumEntries: Int,
                guestUICommitFacts: InstalledGuestUICommitFacts?) {
        self.service = service
        self.maximumTotalBytes = maximumTotalBytes
        self.maximumEntries = maximumEntries
        self.guestUICommitFacts = guestUICommitFacts
    }
    public func get(_ arguments: KVGetArguments) async throws -> KVGetResponse {
        try await get(arguments, commitEvent: nil)
    }
    fileprivate func get(_ arguments: KVGetArguments, commitEvent: InstalledGuestUICommitEvent?) async throws -> KVGetResponse {
        guard let facts = guestUICommitFacts else { return try await service.get(arguments) }
        guard facts.arguments == arguments else {
            guard facts.commitArguments == nil else { throw CapabilityFailure.permissionDenied }
            return try await service.get(arguments)
        }
        guard let commitEvent, commitEvent.nodeID == facts.nodeID, commitEvent.actionID == facts.actionID,
              commitEvent.isLive else { throw CapabilityFailure.permissionDenied }
        let captured = try await facts.read(commitEvent)
        if let commit = captured.commit, captured.response.found, facts.commitArguments != nil {
            try commitEvent.continuation.withLock { state in
                guard case .awaitingFacts = state, commitEvent.isLive else { throw CapabilityFailure.permissionDenied }
                state = .prepared(commit)
            }
        }
        return captured.response
    }
    public func put(_ arguments: KVPutArguments) async throws -> KVMutationResponse {
        try await put(arguments, commitEvent: nil, deadline: .now)
    }
    fileprivate func put(_ arguments: KVPutArguments, commitEvent: InstalledGuestUICommitEvent?,
                         deadline: ContinuousClock.Instant) async throws -> KVMutationResponse {
        guard let command = guestUICommitFacts?.commitArguments else {
            return try await service.put(arguments, maximumTotalBytes: maximumTotalBytes, maximumEntries: maximumEntries)
        }
        guard let commitEvent, command == arguments else { throw CapabilityFailure.permissionDenied }
        let commit = try commitEvent.continuation.withLock { state in
            guard case .delivered(let commit) = state, commitEvent.isLive else { throw CapabilityFailure.permissionDenied }
            state = .reserved
            return commit
        }
        defer { commitEvent.invalidateCommit() }
        let result = try await commit(.init(event: commitEvent, deadline: deadline))
        try commitEvent.continuation.withLock { state in
            guard case .consumed = state else { throw CapabilityFailure.permissionDenied }
        }
        return result
    }
    public func delete(_ arguments: KVDeleteArguments) async throws -> KVMutationResponse {
        guard guestUICommitFacts?.commitArguments == nil else { throw CapabilityFailure.permissionDenied }
        return try await service.delete(arguments)
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

    @_spi(InstalledApplicationStorage)
    public var guestUICommitFacts: InstalledGuestUICommitFacts? {
        (storage as? InstalledApplicationStorageAdapter)?.guestUICommitFacts
    }

    // Scheduling controls for deterministic lifecycle tests only. These never
    // replace the concrete adapter or introduce external cleanup authority.
    init(http: URLSessionHTTPTransport? = nil, storage: AppPrivateKeyValueStore? = nil,
         hooks: InstalledCapabilityExecutionHooks) {
        self.http = http; self.storage = storage; self.hooks = hooks
    }

    func invoke(_ operation: CapabilityOperation, lease: CapabilityExitLease, deadline: ContinuousClock.Instant,
                commitEvent: InstalledGuestUICommitEvent?) async throws -> CapabilityResult {
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
            if let applicationStorage = storage as? InstalledApplicationStorageAdapter {
                result = .get(try await applicationStorage.get(arguments, commitEvent: commitEvent))
            } else {
                result = .get(try await storage.get(arguments))
            }
        case .put(let arguments):
            defer { lease.adapterExited() }
            guard let storage else { throw CapabilityFailure.unavailable }
            if let applicationStorage = storage as? InstalledApplicationStorageAdapter {
                result = .put(try await applicationStorage.put(arguments, commitEvent: commitEvent, deadline: deadline))
            } else {
                result = .put(try await storage.put(arguments))
            }
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
