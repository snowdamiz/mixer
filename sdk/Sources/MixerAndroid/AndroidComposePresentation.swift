import Foundation
import MixerUI

@_spi(ComposeHost) public struct AndroidComposePrepareReceipt: Equatable, Sendable {
    public let owner: UUID
    public let sequence: UInt64
    public let documentRevision: UInt64
    public let opaqueID: UUID

    /// Restores the exact fields captured by the native frame or control.
    public init(owner: UUID, sequence: UInt64, documentRevision: UInt64, opaqueID: UUID) {
        self.owner = owner
        self.sequence = sequence
        self.documentRevision = documentRevision
        self.opaqueID = opaqueID
    }
}

@_spi(ComposeHost) public struct AndroidComposeFrame: Sendable {
    public let receipt: AndroidComposePrepareReceipt
    public let snapshot: UIRenderSnapshot
    public let documentUTF8: Data
}

@_spi(ComposeHost) public enum AndroidComposePresentationError: Error, Equatable, Sendable {
    case wrongExecutor
    case reentrant
    case staleOwner
    case staleReceipt
    case revisionNotIncreasing
    case sequenceExhausted
}

/// Owns one Compose presentation lifetime. Run each synchronous turn on the
/// same serial executor. The executor check must be side-effect-free.
@_spi(ComposeHost) public final class AndroidComposePresentation<Outcome> {
    private struct Publication {
        let receipt: AndroidComposePrepareReceipt
        let snapshot: UIRenderSnapshot
        let handle: (UIEventEnvelope, RoutedUIAction) throws -> Outcome
    }

    public let owner = UUID()
    private let validator: UIValidator
    private let isOnExecutor: @Sendable () -> Bool
    private var accepted: Publication?
    private var pending: Publication?
    private var highestPreparedRevision: UInt64?
    private var sequence: UInt64 = 0
    private var retired = false
    private var busy = false

    /// Use the producer's validator for canonical document encoding.
    public init(validator: UIValidator = UIValidator(), isOnExecutor: @escaping @Sendable () -> Bool) {
        self.validator = validator
        self.isOnExecutor = isOnExecutor
    }

    /// Capture the dispatch path for this snapshot. A newer proposal supersedes
    /// any pending frame even if encoding fails. The drawn pair remains usable.
    public func prepare(
        owner: UUID, snapshot: UIRenderSnapshot,
        handle: @escaping (UIEventEnvelope, RoutedUIAction) throws -> Outcome
    ) throws -> AndroidComposeFrame {
        try requireTurn(owner: owner)
        let revision = snapshot.document.revision
        if let highestPreparedRevision, revision <= highestPreparedRevision {
            throw AndroidComposePresentationError.revisionNotIncreasing
        }
        guard sequence < .max else { throw AndroidComposePresentationError.sequenceExhausted }
        return try withTurn {
            pending = nil
            let documentUTF8 = try validator.encode(snapshot.document)
            sequence += 1
            let receipt = AndroidComposePrepareReceipt(owner: owner, sequence: sequence,
                                                        documentRevision: revision, opaqueID: UUID())
            pending = Publication(receipt: receipt, snapshot: snapshot, handle: handle)
            highestPreparedRevision = revision
            return AndroidComposeFrame(receipt: receipt, snapshot: snapshot, documentUTF8: documentUTF8)
        }
    }

    /// Call after the exact candidate finishes drawing with its controls ready.
    @discardableResult
    public func acknowledgeDraw(_ receipt: AndroidComposePrepareReceipt) -> Bool {
        finish(receipt, drawn: true)
    }

    @discardableResult
    public func cancel(_ receipt: AndroidComposePrepareReceipt) -> Bool {
        finish(receipt, drawn: false)
    }

    /// Echo the receipt captured by the originating control. An admitted event
    /// supersedes pending work before the handler runs, as in FeatureSession.
    public func dispatch(_ event: UIEventEnvelope, from receipt: AndroidComposePrepareReceipt) throws -> Outcome {
        try requireTurn(owner: receipt.owner)
        return try withTurn {
            guard let accepted, accepted.receipt == receipt else {
                throw AndroidComposePresentationError.staleReceipt
            }
            let action = try accepted.snapshot.route(event)
            pending = nil
            return try accepted.handle(event, action)
        }
    }

    /// Retire this lifetime before replacing its native binding.
    @discardableResult
    public func retire(owner: UUID) -> Bool {
        guard (try? requireTurn(owner: owner)) != nil else { return false }
        return withTurn {
            retired = true
            pending = nil
            accepted = nil
            return true
        }
    }

    private func finish(_ receipt: AndroidComposePrepareReceipt, drawn: Bool) -> Bool {
        guard (try? requireTurn(owner: receipt.owner)) != nil, pending?.receipt == receipt else { return false }
        return withTurn {
            if drawn { accepted = pending }
            pending = nil
            return true
        }
    }

    private func requireTurn(owner: UUID) throws(AndroidComposePresentationError) {
        guard isOnExecutor() else { throw .wrongExecutor }
        guard !busy else { throw .reentrant }
        guard !retired, self.owner == owner else { throw .staleOwner }
    }

    private func withTurn<Result>(_ operation: () throws -> Result) rethrows -> Result {
        busy = true
        defer { busy = false }
        return try operation()
    }
}
