#if !os(WASI)
import Foundation

/// The embedding captures the selected record and repository revision in the
/// write closure. The guest receives only the ordinary get response.
@_spi(InstalledApplicationStorage)
public struct InstalledGuestUICommitRead: Sendable {
    public typealias Commit = @Sendable (InstalledGuestUICommitPermit) async throws -> KVMutationResponse
    let response: KVGetResponse
    let commit: Commit?

    public init(response: KVGetResponse, commit: Commit? = nil) {
        self.response = response; self.commit = commit
    }
}

/// Owned by the originating event. No identity or permit is serialized.
final class InstalledGuestUICommitContinuation: @unchecked Sendable {
    enum State: Sendable {
        case awaitingFacts
        case prepared(InstalledGuestUICommitRead.Commit)
        case posted(InstalledGuestUICommitRead.Commit)
        case delivered(InstalledGuestUICommitRead.Commit)
        case reserved
        case consumed
        case finished
    }
    private let lock = NSLock()
    private var state = State.awaitingFacts

    func withLock<Result>(_ body: (inout State) throws -> Result) rethrows -> Result {
        lock.lock(); defer { lock.unlock() }
        return try body(&state)
    }
}

/// The repository must consume this inside its revision-checked transaction,
/// immediately before applying the captured mutation, with no suspension.
@_spi(InstalledApplicationStorage)
public struct InstalledGuestUICommitPermit: Sendable {
    private let event: InstalledGuestUICommitEvent
    private let deadline: ContinuousClock.Instant

    init(event: InstalledGuestUICommitEvent, deadline: ContinuousClock.Instant) {
        self.event = event; self.deadline = deadline
    }

    public func consume() throws {
        try event.continuation.withLock { state in
            guard case .reserved = state else { throw CapabilityFailure.permissionDenied }
            state = .finished
            guard event.isLive else { throw CapabilityFailure.permissionDenied }
            try Task.checkCancellation()
            guard ContinuousClock.now < deadline else { throw CapabilityFailure.deadlineExceeded }
            state = .consumed
        }
    }
}
#endif
