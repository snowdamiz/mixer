import Foundation
import MixerUI

/// The app retains its existing presentation and effects. Observation registers
/// synchronously on MainActor; cancellation removes that observer only.
@MainActor
public protocol AndroidUIPresentation: AnyObject {
    /// A synchronous capture may be overtaken by observer publications before
    /// returning. Every changed snapshot must be published to registered observers.
    var snapshot: UIRenderSnapshot { get }
    func observe(_ receive: @escaping @MainActor (UIRenderSnapshot) -> Void) -> @MainActor () -> Void
    func send(_ event: UIEventEnvelope) throws
}

/// Optional app-owned atomic transaction for events from one installed frame.
/// Route every event against `snapshot`, apply ordered actions to local state,
/// and publish at most once. Throwing must leave app state and effects unchanged.
/// The host validates admission; it cannot roll back arbitrary app side effects.
@MainActor
public protocol AndroidUIBatchPresentation: AndroidUIPresentation {
    func sendBatch(_ events: [UIEventEnvelope], from snapshot: UIRenderSnapshot) throws
}

/// Negotiated by the native adapter, never inferred from the Android API level.
/// Native installation must still validate geometry, environment and operations.
public struct AndroidUICapabilities: Sendable {
    public let kinds: Set<NodeKind>
    public let textFieldAxes: Set<TextFieldAxis>
    public let appearanceV2: Bool

    public init(kinds: Set<NodeKind> = [], textFieldAxes: Set<TextFieldAxis> = [],
                appearanceV2: Bool = false) {
        self.kinds = kinds; self.textFieldAxes = textFieldAxes; self.appearanceV2 = appearanceV2
    }
}

/// A data receipt, not permission to attach a native view outside deliverLatest.
public struct AndroidUIFrame: Sendable {
    public let profile: AndroidUIProfile
    public let owner: UUID
    public let snapshot: UIRenderSnapshot
    public let packet: Data
    public let appearanceDescriptorV2: Data
    fileprivate let delivery: UUID
}

@MainActor
public protocol AndroidUINativeSurface: AnyObject {
    /// Exact adapter identity; capabilities do not select a runtime profile.
    var profile: AndroidUIProfile { get }
    var capabilities: AndroidUICapabilities { get }
    /// Bind one fresh owner with events gated. Reject activation while another
    /// owner is bound; installation accepts only this exact active owner.
    func activate(owner: UUID) throws
    /// Synchronous final validation/attachment with native events gated. No await,
    /// app dispatch or asynchronous attachment after return. Throw leaves events
    /// gated and discards the failed candidate. Native retries may install only.
    func install(_ frame: AndroidUIFrame) throws
    /// Synchronously invalidate this owner's native callbacks and pending work.
    func revoke(owner: UUID)
}

public enum AndroidUIHostError: Error, Equatable, Sendable {
    case closed, busy, staleOwner, noInstalledFrame, sourceChanged, revisionNotIncreasing
    case appearanceUnsupported, profileMismatch, invalidBatch, batchUnsupported
}

/// Owns presentation delivery, not app transactions. All callbacks execute on
/// MainActor; the JNI adapter must establish its Android-main executor contract.
@MainActor
public final class AndroidUIHost {
    private final class PublicationReceipt {}

    public let profile: AndroidUIProfile
    public private(set) var owner: UUID?
    public private(set) var pendingFrame: AndroidUIFrame?
    public private(set) var sourceFailure: (any Error)?
    private let surface: any AndroidUINativeSurface
    private let capabilities: AndroidUICapabilities
    private let appearance: Data
    private let scheduleDelivery: @MainActor () -> Void
    private var source: (any AndroidUIPresentation)?
    private var unsubscribe: (@MainActor () -> Void)?
    private var latest: AndroidUIFrame?
    private var highestRevision: UInt64?
    private var publicationReceipt = PublicationReceipt()
    private var installed: AndroidUIFrame?
    private var busy = false
    private var closed = false
    private var deliveryScheduled = false

    /// scheduleDelivery must enqueue a later MainActor deliverLatest call. It
    /// must not synchronously call back into the host. One wake is outstanding.
    public init(surface: any AndroidUINativeSurface, profile: AndroidUIProfile, appearance: UIAppearanceConfigurationV2,
                scheduleDelivery: @escaping @MainActor () -> Void) throws {
        guard surface.profile == profile else { throw AndroidUIHostError.profileMismatch }
        let negotiated = surface.capabilities
        guard surface.profile == profile else { throw AndroidUIHostError.profileMismatch }
        let capabilities = AndroidUICapabilities(
            kinds: negotiated.kinds.intersection(profile.capabilities.kinds),
            textFieldAxes: negotiated.textFieldAxes.intersection(profile.capabilities.textFieldAxes),
            appearanceV2: negotiated.appearanceV2)
        guard capabilities.appearanceV2 else { throw AndroidUIHostError.appearanceUnsupported }
        self.profile = profile
        self.surface = surface; self.capabilities = capabilities
        self.appearance = try UIAppearanceDescriptorCodecV2.canonicalData(appearance)
        self.scheduleDelivery = scheduleDelivery
    }

    /// Replacement revokes the old owner before registering the new observer.
    /// An initial callback during registration and a queued callback after cancel
    /// are both supported; an old callback cannot populate the new owner's slot.
    @discardableResult
    public func replace(with source: any AndroidUIPresentation) throws -> UUID {
        try enter(); defer { busy = false }
        try requireSurfaceProfile()
        revoke()
        try requireSurfaceProfile()
        guard !closed else { throw AndroidUIHostError.closed }
        let token = UUID()
        owner = token; self.source = source
        do { try surface.activate(owner: token) }
        catch { revoke(); throw error }
        try requireSurfaceProfile()
        guard owner == token, !closed else { throw AndroidUIHostError.closed }
        let cancel = source.observe { [weak self] snapshot in self?.receivePublication(snapshot, owner: token) }
        guard owner == token, !closed else { cancel(); throw AndroidUIHostError.closed }
        unsubscribe = cancel
        try requireBinding(source, owner: token)
        let receipt = publicationReceipt
        let snapshot = source.snapshot
        try requireBinding(source, owner: token)
        if publicationReceipt === receipt { accept(snapshot, owner: token) }
        try requireBinding(source, owner: token)
        return token
    }

    /// Coalesces intermediate snapshots. Failure keeps the latest candidate for
    /// explicit native retry; it never invokes the app event sink.
    @discardableResult
    public func deliverLatest() throws -> Bool {
        try enter(); defer { busy = false }
        try requireSurfaceProfile()
        deliveryScheduled = false
        if let sourceFailure { throw sourceFailure }
        guard let frame = pendingFrame else { return false }
        guard owner == frame.owner else { throw AndroidUIHostError.staleOwner }
        guard let source else { throw AndroidUIHostError.sourceChanged }
        let snapshot = source.snapshot
        try requireBinding(source, owner: frame.owner)
        if let sourceFailure { throw sourceFailure }
        guard pendingFrame?.delivery == frame.delivery, latest?.delivery == frame.delivery,
              snapshot.document == frame.snapshot.document else { throw AndroidUIHostError.sourceChanged }
        installed = nil
        do { try surface.install(frame) }
        catch { try requireSurfaceProfile(); throw error }
        try requireSurfaceProfile()
        guard owner == frame.owner, !closed else { throw AndroidUIHostError.staleOwner }
        installed = frame
        if pendingFrame?.delivery == frame.delivery { pendingFrame = nil }
        return true
    }

    /// Native must pass the owner and exact envelope captured by the originating
    /// installed control. Neither revisions nor identities are rebased here.
    public func send(owner token: UUID, event: UIEventEnvelope) throws {
        try enter(); defer { busy = false }
        try requireSurfaceProfile()
        guard token == owner else { throw AndroidUIHostError.staleOwner }
        if let sourceFailure { throw sourceFailure }
        guard let installed, let source else { throw AndroidUIHostError.noInstalledFrame }
        let snapshot = source.snapshot
        try requireAdmission(source, owner: token, frame: installed)
        guard snapshot.document == installed.snapshot.document else {
            throw AndroidUIHostError.sourceChanged
        }
        _ = try installed.snapshot.route(event)
        let current = source.snapshot
        try requireAdmission(source, owner: token, frame: installed)
        guard current.document == installed.snapshot.document else { throw AndroidUIHostError.sourceChanged }
        _ = try current.route(event)
        do { try source.send(event) }
        catch { try requireSurfaceProfile(); throw error }
        try requireSurfaceProfile()
    }

    public static let maximumBatchEvents = 32
    public static let maximumBatchBytes = 131_072

    /// Every original envelope is admitted against the same installed receipt
    /// before the one app transaction. No scalar fallback, revision or ID rebasing.
    public func sendBatch(owner token: UUID, events: [UIEventEnvelope]) throws {
        try enter(); defer { busy = false }
        try requireSurfaceProfile()
        guard token == owner else { throw AndroidUIHostError.staleOwner }
        if let sourceFailure { throw sourceFailure }
        guard !events.isEmpty, events.count <= Self.maximumBatchEvents,
              try JSONEncoder().encode(events).count <= Self.maximumBatchBytes else {
            throw AndroidUIHostError.invalidBatch
        }
        guard let installed, let source else { throw AndroidUIHostError.noInstalledFrame }
        guard let batchSource = source as? any AndroidUIBatchPresentation else {
            throw AndroidUIHostError.batchUnsupported
        }
        let snapshot = source.snapshot
        try requireAdmission(source, owner: token, frame: installed)
        guard snapshot.document == installed.snapshot.document else { throw AndroidUIHostError.sourceChanged }
        for event in events { _ = try installed.snapshot.route(event) }
        let current = source.snapshot
        try requireAdmission(source, owner: token, frame: installed)
        guard current.document == installed.snapshot.document else { throw AndroidUIHostError.sourceChanged }
        for event in events { _ = try current.route(event) }
        do { try batchSource.sendBatch(events, from: installed.snapshot) }
        catch { try requireSurfaceProfile(); throw error }
        try requireSurfaceProfile()
    }

    /// Close revokes before calling cancellation/native code, including reentrant
    /// close during install. Durable app work is neither cancelled nor undone.
    public func close() {
        guard !closed else { return }
        closed = true
        deliveryScheduled = false
        revoke()
    }

    private func enter() throws {
        guard !closed else { throw AndroidUIHostError.closed }
        guard !busy else { throw AndroidUIHostError.busy }
        busy = true
    }

    private func requireSurfaceProfile() throws {
        guard surface.profile == profile else {
            revoke()
            throw AndroidUIHostError.profileMismatch
        }
    }

    private func requireBinding(_ source: any AndroidUIPresentation, owner token: UUID) throws {
        try requireSurfaceProfile()
        guard !closed else { throw AndroidUIHostError.closed }
        guard owner == token, self.source === source else { throw AndroidUIHostError.staleOwner }
    }

    private func requireAdmission(_ source: any AndroidUIPresentation, owner token: UUID,
                                  frame: AndroidUIFrame) throws {
        try requireBinding(source, owner: token)
        if let sourceFailure { throw sourceFailure }
        guard installed?.delivery == frame.delivery, latest?.delivery == frame.delivery else {
            throw AndroidUIHostError.sourceChanged
        }
    }

    private func revoke() {
        let oldOwner = owner, cancel = unsubscribe
        owner = nil; unsubscribe = nil; source = nil; latest = nil
        installed = nil; pendingFrame = nil; highestRevision = nil
        publicationReceipt = PublicationReceipt()
        sourceFailure = nil
        if let oldOwner { surface.revoke(owner: oldOwner) }
        cancel?()
    }

    private func receivePublication(_ snapshot: UIRenderSnapshot, owner token: UUID) {
        guard !closed, token == owner else { return }
        publicationReceipt = PublicationReceipt()
        accept(snapshot, owner: token)
    }

    private func accept(_ snapshot: UIRenderSnapshot, owner token: UUID) {
        guard !closed, token == owner else { return }
        do {
            if let highestRevision, snapshot.document.revision < highestRevision {
                throw AndroidUIHostError.revisionNotIncreasing
            }
            let duplicate = highestRevision == snapshot.document.revision
            highestRevision = snapshot.document.revision
            _ = try UIValidator(supportedKinds: capabilities.kinds,
                                supportedTextFieldAxes: capabilities.textFieldAxes).validate(snapshot.document)
            let packet = try snapshot.encodeNativePacketV1(supportedTextFieldAxes: capabilities.textFieldAxes)
            if duplicate {
                guard let latest, latest.packet == packet else { throw AndroidUIHostError.revisionNotIncreasing }
                return
            }
            let frame = AndroidUIFrame(profile: profile, owner: token, snapshot: snapshot, packet: packet,
                                       appearanceDescriptorV2: appearance, delivery: UUID())
            latest = frame; pendingFrame = frame; sourceFailure = nil
        } catch {
            sourceFailure = error; pendingFrame = nil; installed = nil
        }
        if !deliveryScheduled {
            deliveryScheduled = true
            scheduleDelivery()
        }
    }
}
