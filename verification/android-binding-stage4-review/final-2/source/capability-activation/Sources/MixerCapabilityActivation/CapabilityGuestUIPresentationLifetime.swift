import Foundation
@_spi(GuestUIV1) import MixerGuest
#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
import CMixerUITransport
import CMixerUIAndroidHostBridge
#endif

struct CapabilityPresentationLifetimeID: Sendable, Equatable {
    let rawValue: UInt64
    private init(_ value: UInt64) { rawValue = value }
    private static let counter = CapabilityPresentationCounter()
    static func issue() throws -> Self { Self(try counter.issue()) }
}

private final class CapabilityPresentationCounter: @unchecked Sendable {
    private let lock = NSLock()
    private var value: UInt64 = 0
    func issue() throws -> UInt64 {
        lock.lock(); defer { lock.unlock() }
        guard value < UInt64.max else { throw coldStartError("presentation_identity_exhausted") }
        value += 1; return value
    }
}

enum CapabilityPresentationTaskJoin: Sendable, Equatable { case noTaskCreated, joined }
enum CapabilityPresentationFailureCode: Sendable, Equatable { case invalidState, unsupportedPlatform }
struct CapabilityPresentationFailure: Sendable, Equatable {
    let facade: UInt64
    let lifetime: CapabilityPresentationLifetimeID
    let endpoint: UInt64?
    let code: CapabilityPresentationFailureCode
    fileprivate init(facade: UInt64, lifetime: CapabilityPresentationLifetimeID,
                     endpoint: UInt64?, code: CapabilityPresentationFailureCode) {
        self.facade = facade; self.lifetime = lifetime; self.endpoint = endpoint; self.code = code
    }
}
enum CapabilityPresentationInvariant: Sendable, Equatable {
    case wrongJoinOwner, joinInFlight, missingPublishedResources, invalidState
}
struct CapabilityFacadeCleanupReceipt: Sendable, Equatable {
    let facade: UInt64
    let cleanupSerial: UInt64
    let finalEntrySerial: UInt64
    // Android construction remains private until its native cleanup is implemented.
    private init(facade: UInt64, cleanupSerial: UInt64, finalEntrySerial: UInt64) {
        self.facade = facade; self.cleanupSerial = cleanupSerial; self.finalEntrySerial = finalEntrySerial
    }
}
struct CapabilityPresentationLifetimeReceipt: Sendable, Equatable {
    let facade: UInt64
    let lifetime: CapabilityPresentationLifetimeID
    let endpoint: UInt64?
    let taskJoin: CapabilityPresentationTaskJoin
    let facadeCleanup: CapabilityFacadeCleanupReceipt?
    /// Apple receipts cover its MainActor view retirement. Its public model may
    /// still be retained by an application; this never asserts model destruction.
    fileprivate init(apple facade: UInt64, lifetime: CapabilityPresentationLifetimeID, joined: CapabilityPresentationTaskJoin) {
        self.facade = facade; self.lifetime = lifetime; endpoint = nil
        taskJoin = joined; facadeCleanup = nil
    }
}
enum CapabilityPresentationFinishResult: Sendable, Equatable {
    case retired(CapabilityPresentationLifetimeReceipt)
    case quarantined(CapabilityPresentationFailure)
}
enum CapabilityPresentationJoinStatus: Sendable, Equatable {
    case pending
    case finished(CapabilityPresentationFinishResult)
    case invariant(CapabilityPresentationInvariant)
    var isRetired: Bool { if case .finished(.retired) = self { return true }; return false }
}

/// A copied reference cannot duplicate ownership: a move invalidates the old
/// cell, and an admitted join transitions its sole current cell to inFlight.
final class CapabilityPresentationJoinPermit: @unchecked Sendable {
    private enum State { case owned, moved, inFlight, consumed }
    private let lock = NSLock()
    private var state = State.owned
    fileprivate let lifetime: CapabilityPresentationLifetimeID
    fileprivate init(_ lifetime: CapabilityPresentationLifetimeID) { self.lifetime = lifetime }
    fileprivate func move() -> CapabilityPresentationJoinPermit? {
        lock.lock(); defer { lock.unlock() }
        guard case .owned = state else { return nil }
        state = .moved; return CapabilityPresentationJoinPermit(lifetime)
    }
    fileprivate func begin(_ expected: CapabilityPresentationLifetimeID) -> CapabilityPresentationInvariant? {
        lock.lock(); defer { lock.unlock() }
        guard lifetime == expected else { return .wrongJoinOwner }
        switch state {
        case .owned: state = .inFlight; return nil
        case .inFlight: return .joinInFlight
        case .moved, .consumed: return .wrongJoinOwner
        }
    }
    fileprivate func consume() { lock.lock(); state = .consumed; lock.unlock() }
}

/// The Apple adapter is weakly reached only for a final actor retirement turn.
/// No model/frame/resource is stored in the common lifetime or join permit.
protocol CapabilityPresentationRetirement: AnyObject, Sendable {
    func retireEmptyPresentation() async -> Bool
}

final class CapabilityGuestUIPresentationLifetime: @unchecked Sendable {
    let id: CapabilityPresentationLifetimeID
    let facade: UInt64
    private enum Backend {
        case apple
#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
        case androidHost(CapabilityAndroidHostLifetimeKey, CapabilityAndroidLifetimeControl)
#endif
    }
    private let backend: Backend
    fileprivate var isAppleBackend: Bool { if case .apple = backend { return true }; return false }
    private let lock = NSLock()
#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
    private var hostResult: CapabilityAndroidHostJoinStatus = .pending
    private var hostReturnObserved = false
#endif
    private weak var retirement: (any CapabilityPresentationRetirement)?
    private weak var exchange: GuestUIExchangeV1?
    private var task: Task<Void, Never>?
    private var bound = false
    private var stopping: CapabilityAttemptLocalStop?
    private var joining = false
    private var issued = false
    private var result: CapabilityPresentationJoinStatus = .pending
    init(id: CapabilityPresentationLifetimeID, facade: UInt64? = nil, retirement: any CapabilityPresentationRetirement) {
        self.id = id; self.facade = facade ?? id.rawValue; self.retirement = retirement; backend = .apple
    }
    func installation() throws -> CapabilityPresentationInstallation {
        lock.lock(); defer { lock.unlock() }
        guard isAppleBackend else { throw coldStartError("presentation_host_scope") }
        guard !issued else { throw coldStartError("presentation_permit_issued") }
        issued = true
        return CapabilityPresentationInstallation(lifetime: self, permit: CapabilityPresentationJoinPermit(id))
    }
    func attach(_ task: Task<Void, Never>, exchange: GuestUIExchangeV1) -> Bool {
        lock.lock()
        guard isAppleBackend, !bound, !joining, result == .pending else { lock.unlock(); return false }
        self.task = task; self.exchange = exchange; bound = true
        let stop = stopping; lock.unlock()
        if stop != nil { exchange.stop(.closed) }
        return true
    }
    func requestStop(_ cause: CapabilityAttemptLocalStop) {
#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
        if case .androidHost(_, let control) = backend { control.requestStop(cause); return }
#endif
        lock.lock(); if stopping == nil { stopping = cause }; let exchange = exchange; lock.unlock()
        exchange?.stop(.closed)
    }
    func isBound(to expected: GuestUIExchangeV1) -> Bool {
        lock.lock(); defer { lock.unlock() }; return isAppleBackend && bound && exchange === expected
    }
    var status: CapabilityPresentationJoinStatus {
        guard isAppleBackend else { return .invariant(.invalidState) }
        lock.lock(); defer { lock.unlock() }; return result
    }
    private func admit(_ permit: CapabilityPresentationJoinPermit) -> (Task<Void, Never>?, Bool, CapabilityPresentationJoinStatus?) {
        lock.lock(); defer { lock.unlock() }
        guard isAppleBackend else { return (nil, false, .invariant(.invalidState)) }
        guard permit.lifetime == id else { return (nil, false, .invariant(.wrongJoinOwner)) }
        if result != .pending { return (nil, false, result) }
        if joining { return (nil, false, .pending) }
        if let invalid = permit.begin(id) { return (nil, false, .invariant(invalid)) }
        joining = true; return (task, bound, nil)
    }
    private func publish(_ value: CapabilityPresentationJoinStatus) {
        lock.lock(); result = value; task = nil; joining = false; lock.unlock()
    }
    func finish(using permit: CapabilityPresentationJoinPermit) async -> CapabilityPresentationJoinStatus {
        guard isAppleBackend else { return .invariant(.invalidState) }
        let (task, wasBound, early) = admit(permit)
        if let early { return early }
        if let task { await task.value } // The actual Task return, not a signal.
        // A bound lifetime is never permitted to fabricate an empty-task receipt.
        guard !wasBound || task != nil else {
            let failure = CapabilityPresentationFailure(facade: facade, lifetime: id, endpoint: nil, code: .invalidState)
            let value = CapabilityPresentationJoinStatus.finished(.quarantined(failure))
            permit.consume(); publish(value); return value
        }
        let retired = await retirement?.retireEmptyPresentation() ?? true
        guard retired else {
            let failure = CapabilityPresentationFailure(facade: facade, lifetime: id, endpoint: nil, code: .invalidState)
            let value = CapabilityPresentationJoinStatus.finished(.quarantined(failure))
            permit.consume(); publish(value); return value
        }
        let value = CapabilityPresentationJoinStatus.finished(.retired(
            CapabilityPresentationLifetimeReceipt(apple: facade, lifetime: id, joined: task == nil ? .noTaskCreated : .joined)))
        permit.consume(); publish(value); return value
    }
#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
    private init(host start: CapabilityAndroidHostLifetimeStart) {
        id = start.key.lifetime; facade = start.key.facade
        backend = .androidHost(start.key, start.control); task = start.task; issued = true
    }
    static func consumeAndroidHost(_ capsule: CapabilityAndroidHostLifetimeCapsule) throws -> CapabilityAndroidHostInstallation {
        guard let start = capsule.takeForCommonLifetime() else { throw coldStartError("android_capsule_consumed") }
        let lifetime = CapabilityGuestUIPresentationLifetime(host: start)
        return CapabilityAndroidHostInstallation(lifetime: lifetime, permit: CapabilityPresentationJoinPermit(start.key.lifetime))
    }
    fileprivate var androidKey: CapabilityAndroidHostLifetimeKey? {
        guard case .androidHost(let key, _) = backend else { return nil }; return key
    }
    fileprivate func bindAndroidHost(_ exchange: GuestUIExchangeV1) throws {
        guard case .androidHost(_, let control) = backend else { throw coldStartError("android_scope") }
        try control.bind(exchange)
    }
    fileprivate var androidStatus: CapabilityAndroidHostJoinStatus {
        guard case .androidHost = backend else { return .invariant(.invalidState) }
        lock.lock(); defer { lock.unlock() }; return hostReturnObserved ? hostResult : .pending
    }
    fileprivate func observeAndroidReturn() { lock.lock(); hostReturnObserved = true; lock.unlock() }
    private func admitAndroid(_ permit: CapabilityPresentationJoinPermit) -> (Task<Void, Never>?, CapabilityAndroidHostJoinStatus?) {
        lock.lock(); defer { lock.unlock() }
        guard case .androidHost = backend else { return (nil, .invariant(.invalidState)) }
        guard permit.lifetime == id else { return (nil, .invariant(.wrongJoinOwner)) }
        if hostResult != .pending { return (nil, hostResult) }
        if joining { return (nil, .pending) }
        if let invalid = permit.begin(id) { return (nil, .invariant(invalid)) }
        joining = true; return (task, nil)
    }
    private func publishAndroid(_ value: CapabilityAndroidHostJoinStatus) {
        lock.lock(); hostResult = value; task = nil; joining = false; lock.unlock()
    }
    fileprivate func finishAndroidHost(using permit: CapabilityPresentationJoinPermit) async -> CapabilityAndroidHostJoinStatus {
        guard case .androidHost(let key, let control) = backend else { return .invariant(.invalidState) }
        let (task, early) = admitAndroid(permit)
        if let early { return early }
        control.requestStop(.closed)
        guard let task else {
            let value = CapabilityAndroidHostJoinStatus.finished(.quarantined(.init(key: key, code: .invalidState)))
            permit.consume(); publishAndroid(value); return value
        }
        await task.value
        let returned = CapabilityAndroidHostTaskReturnEvidence(key: key)
        let value: CapabilityAndroidHostJoinStatus
        switch await control.joinNative(after: returned) {
        case .retired(let native):
            if let receipt = CapabilityAndroidHostLifetimeReceipt.validate(taskReturn: returned, native: native) {
                value = .finished(.retired(receipt))
            } else { value = .finished(.quarantined(.init(key: key, code: .invalidState))) }
        case .quarantined(let failure): value = .finished(.quarantined(failure))
        }
        permit.consume(); publishAndroid(value); return value
    }
#endif

}

/// A movable pair; references to an emptied installation carry no authority.
final class CapabilityPresentationInstallation: @unchecked Sendable {
    private let lock = NSLock()
    private var owned: (CapabilityGuestUIPresentationLifetime, CapabilityPresentationJoinPermit)?
    fileprivate init(lifetime: CapabilityGuestUIPresentationLifetime, permit: CapabilityPresentationJoinPermit) {
        precondition(lifetime.isAppleBackend)
        owned = (lifetime, permit)
    }
    func move() -> CapabilityPresentationInstallation? {
        lock.lock(); defer { lock.unlock() }
        guard let (lifetime, permit) = owned, let next = permit.move() else { return nil }
        owned = nil; return CapabilityPresentationInstallation(lifetime: lifetime, permit: next)
    }
    func takePermit() -> CapabilityPresentationJoinPermit? {
        lock.lock(); defer { lock.unlock() }
        guard let (_, permit) = owned, let moved = permit.move() else { return nil }
        owned = nil; return moved
    }
    var lifetime: CapabilityGuestUIPresentationLifetime? {
        lock.lock(); defer { lock.unlock() }; return owned?.0
    }
    func finish() async -> CapabilityPresentationJoinStatus {
        let value = take()
        guard let (lifetime, permit) = value else { return .invariant(.wrongJoinOwner) }
        return await lifetime.finish(using: permit)
    }
    private func take() -> (CapabilityGuestUIPresentationLifetime, CapabilityPresentationJoinPermit)? {
        lock.lock(); defer { lock.unlock() }
        guard let (lifetime, permit) = owned, let moved = permit.move() else { return nil }
        owned = nil; return (lifetime, moved)
    }
}

#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
struct CapabilityAndroidHostTaskReturnEvidence: Sendable, Equatable {
    let key: CapabilityAndroidHostLifetimeKey
    fileprivate init(key: CapabilityAndroidHostLifetimeKey) { self.key = key }
}
struct CapabilityAndroidHostFacadeCleanupReceipt: Sendable, Equatable {
    let facade: UInt64
    let cleanupSerial: UInt64
    let finalEntrySerial: UInt64
    let bridgeSlotGeneration: UInt64
    private init(_ evidence: CapabilityAndroidHostFacadeCleanupEvidence) {
        facade = evidence.key.facade; cleanupSerial = evidence.cleanupSerial
        finalEntrySerial = evidence.finalEntrySerial; bridgeSlotGeneration = evidence.bridgeSlotGeneration
    }
    fileprivate static func validate(_ evidence: CapabilityAndroidHostFacadeCleanupEvidence,
                                     for key: CapabilityAndroidHostLifetimeKey) -> Self? {
        guard evidence.key == key, evidence.cleanupSerial > 0, evidence.finalEntrySerial > 0,
              evidence.bridgeSlotGeneration > 0, evidence.clearedResourceStageRevision > 0 else { return nil }
        return Self(evidence)
    }
}
struct CapabilityAndroidHostLifetimeReceipt: Sendable, Equatable {
    let key: CapabilityAndroidHostLifetimeKey
    let taskJoin: CapabilityPresentationTaskJoin
    let facadeCleanup: CapabilityAndroidHostFacadeCleanupReceipt?
    private init(key: CapabilityAndroidHostLifetimeKey, cleanup: CapabilityAndroidHostFacadeCleanupReceipt?) {
        self.key = key; taskJoin = .joined; facadeCleanup = cleanup
    }
    fileprivate static func validate(taskReturn: CapabilityAndroidHostTaskReturnEvidence,
                                     native: CapabilityAndroidHostEndpointRetirementEvidence) -> Self? {
        guard taskReturn.key == native.key, native.callbackFence > 0, native.uiEntryFence > 0 else { return nil }
        let cleanup: CapabilityAndroidHostFacadeCleanupReceipt?
        if let evidence = native.facadeCleanup {
            guard let validated = CapabilityAndroidHostFacadeCleanupReceipt.validate(evidence, for: native.key) else { return nil }
            cleanup = validated
        } else { cleanup = nil }
        return Self(key: native.key, cleanup: cleanup)
    }
}
enum CapabilityAndroidHostFinishResult: Sendable, Equatable {
    case retired(CapabilityAndroidHostLifetimeReceipt), quarantined(CapabilityAndroidHostFailure)
}
enum CapabilityAndroidHostJoinStatus: Sendable, Equatable {
    case pending, finished(CapabilityAndroidHostFinishResult), invariant(CapabilityPresentationInvariant)
}
final class CapabilityAndroidHostInstallation: @unchecked Sendable {
    let key: CapabilityAndroidHostLifetimeKey
    private let lifetime: CapabilityGuestUIPresentationLifetime
    private let lock = NSLock()
    private var permit: CapabilityPresentationJoinPermit?
    fileprivate init(lifetime: CapabilityGuestUIPresentationLifetime, permit: CapabilityPresentationJoinPermit) {
        precondition(lifetime.androidKey != nil)
        key = lifetime.androidKey!; self.lifetime = lifetime; self.permit = permit
    }
    func move() -> CapabilityAndroidHostInstallation? {
        lock.lock(); defer { lock.unlock() }
        guard let next = permit?.move() else { return nil }
        permit = nil; return CapabilityAndroidHostInstallation(lifetime: lifetime, permit: next)
    }
    func bind(_ exchange: GuestUIExchangeV1) throws { try lifetime.bindAndroidHost(exchange) }
    func requestStop(_ cause: CapabilityAttemptLocalStop) { lifetime.requestStop(cause) }
    private func take() -> CapabilityPresentationJoinPermit? {
        lock.lock(); defer { lock.unlock() }
        guard let next = permit?.move() else { return nil }; permit = nil; return next
    }
    func finish() async -> CapabilityAndroidHostJoinStatus {
        // Immutable readback survives moves and endpoint-slot reuse.
        let previous = lifetime.androidStatus
        if previous != .pending { return previous }
        guard let permit = take() else { return .invariant(.wrongJoinOwner) }
        let result = await lifetime.finishAndroidHost(using: permit)
        lifetime.observeAndroidReturn() // The authoritative common finish actually returned.
        return result
    }
    var status: CapabilityAndroidHostJoinStatus { lifetime.androidStatus }
}
#endif
