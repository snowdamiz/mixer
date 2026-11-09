import Foundation
import Testing
import MixerUI
import MixerAndroid

private enum ProfileFixFailure: Error { case install, sink }

@MainActor private final class ProfileFixSurface: AndroidUINativeSurface {
    var identity: AndroidUIProfile = .measuredMultilineRetirementV3
    var onProfile: (() -> Void)?
    var profile: AndroidUIProfile { onProfile?(); return identity }
    var onCapabilities: (() -> Void)?
    var capabilities: AndroidUICapabilities { onCapabilities?(); return AndroidUIProfile.measuredMultilineRetirementV3.capabilities }
    var active: UUID?
    var activated: [UUID] = []
    var revoked: [UUID] = []
    var frames: [AndroidUIFrame] = []
    var onActivate: (() throws -> Void)?
    var onInstall: (() throws -> Void)?
    var onRevoke: (() -> Void)?
    func activate(owner: UUID) throws { active = owner; activated.append(owner); try onActivate?() }
    func install(_ frame: AndroidUIFrame) throws { try onInstall?(); frames.append(frame) }
    func revoke(owner: UUID) { revoked.append(owner); if active == owner { active = nil }; onRevoke?() }
}

@MainActor private final class ProfileFixSource: AndroidUIPresentation {
    let value: UIRenderSnapshot
    var reads = 0
    var onRead: ((Int) -> Void)?
    var onObserve: (() -> Void)?
    var onCancel: (() -> Void)?
    var onSend: (() throws -> Void)?
    var callback: (@MainActor (UIRenderSnapshot) -> Void)?
    var cancellations = 0
    var sends = 0
    init() throws {
        var reconciler = UIReconciler()
        try reconciler.apply(Button("go", "Go", action: "go").document(revision: 1))
        value = try reconciler.currentSnapshot()
    }
    var snapshot: UIRenderSnapshot { reads += 1; onRead?(reads); return value }
    func observe(_ receive: @escaping @MainActor (UIRenderSnapshot) -> Void) -> @MainActor () -> Void {
        callback = receive; receive(value); onObserve?()
        return { self.cancellations += 1; self.callback = nil; self.onCancel?() }
    }
    func send(_ event: UIEventEnvelope) throws { sends += 1; try onSend?() }
}

@MainActor private func profileFixHost(_ surface: ProfileFixSurface) throws -> AndroidUIHost {
    try AndroidUIHost(surface: surface, profile: .measuredMultilineRetirementV3,
        appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: {})
}
@MainActor private func profileFixEvent(_ source: ProfileFixSource) throws -> UIEventEnvelope {
    UIEventEnvelope(revision: 1, identity: try #require(source.value.identity(for: "go")), event: .activate)
}

@Test @MainActor func profileFixCapabilitiesCallbackCannotChangeConstructionIdentity() throws {
    let surface = ProfileFixSurface()
    surface.onCapabilities = { surface.identity = .measuredMultilineV2 }
    #expect(throws: AndroidUIHostError.profileMismatch) { try profileFixHost(surface) }
    #expect(surface.activated.isEmpty && surface.frames.isEmpty && surface.revoked.isEmpty)
}

@Test(arguments: [false, true]) @MainActor
func profileFixReplacementCancellationCannotActivateChangedSurface(duringRevoke: Bool) throws {
    let surface = ProfileFixSurface(), old = try ProfileFixSource(), next = try ProfileFixSource()
    let host = try profileFixHost(surface); defer { host.close() }
    let owner = try host.replace(with: old)
    if duringRevoke { surface.onRevoke = { surface.identity = .measuredMultilineV2 } }
    else { old.onCancel = { surface.identity = .measuredMultilineV2 } }
    #expect(throws: AndroidUIHostError.profileMismatch) { try host.replace(with: next) }
    #expect(surface.activated == [owner] && surface.revoked == [owner] && surface.active == nil)
    #expect(host.owner == nil && host.pendingFrame == nil && old.cancellations == 1 && next.reads == 0)
}

@Test @MainActor func profileFixObservationCompletionCancelsExactRegistration() throws {
    let surface = ProfileFixSurface(), source = try ProfileFixSource()
    let host = try profileFixHost(surface); defer { host.close() }
    source.onObserve = { surface.identity = .measuredMultilineV2 }
    #expect(throws: AndroidUIHostError.profileMismatch) { try host.replace(with: source) }
    #expect(surface.revoked == surface.activated && surface.revoked.count == 1 && surface.active == nil)
    #expect(source.cancellations == 1 && source.callback == nil && source.reads == 0)
    #expect(host.owner == nil && host.pendingFrame == nil && surface.frames.isEmpty)
}

@Test @MainActor func profileFixInitialSnapshotDriftRevokesBeforeReturningOwner() throws {
    let surface = ProfileFixSurface(), source = try ProfileFixSource()
    let host = try profileFixHost(surface); defer { host.close() }
    source.onRead = { _ in surface.identity = .measuredMultilineV2 }
    #expect(throws: AndroidUIHostError.profileMismatch) { try host.replace(with: source) }
    #expect(host.owner == nil && host.pendingFrame == nil && surface.frames.isEmpty)
    #expect(source.cancellations == 1 && surface.revoked == surface.activated)
}

@Test(arguments: [1, 2]) @MainActor
func profileFixEitherEventSnapshotRefusesBeforeAppEffect(offset: Int) throws {
    let surface = ProfileFixSurface(), source = try ProfileFixSource()
    let host = try profileFixHost(surface); defer { host.close() }
    let owner = try host.replace(with: source)
    #expect(try host.deliverLatest())
    let target = source.reads + offset
    source.onRead = { if $0 == target { surface.identity = .measuredMultilineV2 } }
    #expect(throws: AndroidUIHostError.profileMismatch) { try host.send(owner: owner, event: profileFixEvent(source)) }
    #expect(source.sends == 0 && source.reads == target && source.cancellations == 1)
    #expect(host.owner == nil && host.pendingFrame == nil && surface.revoked == [owner])
}

@Test @MainActor func profileFixInstallCompletionRevokesReceiptWithoutAppReplay() throws {
    let surface = ProfileFixSurface(), source = try ProfileFixSource()
    let host = try profileFixHost(surface); defer { host.close() }
    let owner = try host.replace(with: source)
    surface.onInstall = { surface.identity = .measuredMultilineV2 }
    #expect(throws: AndroidUIHostError.profileMismatch) { try host.deliverLatest() }
    #expect(host.owner == nil && host.pendingFrame == nil && surface.active == nil)
    #expect(surface.revoked == [owner] && source.cancellations == 1 && source.sends == 0)
    surface.identity = .measuredMultilineRetirementV3; surface.onInstall = nil
    #expect(try !host.deliverLatest())
    #expect(throws: AndroidUIHostError.staleOwner) { try host.send(owner: owner, event: profileFixEvent(source)) }
    #expect(source.sends == 0 && surface.frames.count == 1)
}

@Test(arguments: [false, true]) @MainActor
func profileFixThrowingInstallRetainsRetryOnlyWhileProfileMatches(drift: Bool) throws {
    let surface = ProfileFixSurface(), source = try ProfileFixSource()
    let host = try profileFixHost(surface); defer { host.close() }
    let owner = try host.replace(with: source)
    surface.onInstall = { if drift { surface.identity = .measuredMultilineV2 }; throw ProfileFixFailure.install }
    if drift {
        #expect(throws: AndroidUIHostError.profileMismatch) { try host.deliverLatest() }
        #expect(host.owner == nil && host.pendingFrame == nil && surface.revoked == [owner])
    } else {
        #expect(throws: ProfileFixFailure.install) { try host.deliverLatest() }
        #expect(host.owner == owner && host.pendingFrame?.owner == owner && surface.revoked.isEmpty)
        surface.onInstall = nil
        #expect(try host.deliverLatest())
    }
    #expect(source.sends == 0)
}

@Test(arguments: [false, true]) @MainActor
func profileFixSinkCompletionDriftRevokesWithoutReplayingCompletedEffect(throwsError: Bool) throws {
    let surface = ProfileFixSurface(), source = try ProfileFixSource()
    let host = try profileFixHost(surface); defer { host.close() }
    let owner = try host.replace(with: source)
    #expect(try host.deliverLatest())
    source.onSend = { surface.identity = .measuredMultilineV2; if throwsError { throw ProfileFixFailure.sink } }
    #expect(throws: AndroidUIHostError.profileMismatch) { try host.send(owner: owner, event: profileFixEvent(source)) }
    #expect(source.sends == 1 && source.cancellations == 1 && surface.revoked == [owner])
    surface.identity = .measuredMultilineRetirementV3
    #expect(try !host.deliverLatest())
    #expect(throws: AndroidUIHostError.staleOwner) { try host.send(owner: owner, event: profileFixEvent(source)) }
    #expect(source.sends == 1)
}

@Test @MainActor func profileFixProfileGetterCloseCannotAdmitAnEvent() throws {
    let surface = ProfileFixSurface(), source = try ProfileFixSource()
    let host = try profileFixHost(surface)
    let owner = try host.replace(with: source)
    #expect(try host.deliverLatest())
    source.onRead = { _ in surface.onProfile = { surface.onProfile = nil; host.close() } }
    #expect(throws: AndroidUIHostError.closed) { try host.send(owner: owner, event: profileFixEvent(source)) }
    #expect(source.sends == 0 && source.cancellations == 1 && surface.revoked == [owner])
}
