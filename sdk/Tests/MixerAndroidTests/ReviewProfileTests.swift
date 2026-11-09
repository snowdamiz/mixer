import Foundation
import Testing
import MixerUI
import MixerAndroid

@MainActor private final class ReviewSurface: AndroidUINativeSurface {
    var profile: AndroidUIProfile = .measuredMultilineRetirementV3
    var capabilities = AndroidUIProfile.measuredMultilineRetirementV3.capabilities
    var active: UUID?
    var frames: [AndroidUIFrame] = []
    var revoked: [UUID] = []
    var onActivate: (() -> Void)?
    func activate(owner: UUID) throws { active = owner; onActivate?() }
    func install(_ frame: AndroidUIFrame) throws { frames.append(frame) }
    func revoke(owner: UUID) { revoked.append(owner); if active == owner { active = nil } }
}
@MainActor private final class ReviewSource: AndroidUIPresentation {
    let value: UIRenderSnapshot
    var onRead: (() -> Void)?
    var sends = 0
    init() throws {
        var r = UIReconciler()
        try r.apply(Button("go", "Go", action: "go").document(revision: 1))
        value = try r.currentSnapshot()
    }
    var snapshot: UIRenderSnapshot { onRead?(); return value }
    func observe(_ receive: @escaping @MainActor (UIRenderSnapshot) -> Void) -> @MainActor () -> Void { receive(value); return {} }
    func send(_ event: UIEventEnvelope) throws { sends += 1 }
}
@MainActor private func reviewHost(_ s: ReviewSurface) throws -> AndroidUIHost {
    try AndroidUIHost(surface: s, profile: s.profile, appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: {})
}
@Test @MainActor func reviewProfileEveryMismatchRefusesBeforeActivation() throws {
    for selected in AndroidUIProfile.allCases {
        for actual in AndroidUIProfile.allCases where selected != actual {
            let surface = ReviewSurface(); surface.profile = actual
            #expect(throws: AndroidUIHostError.profileMismatch) {
                try AndroidUIHost(surface: surface, profile: selected, appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: {})
            }
            #expect(surface.active == nil && surface.frames.isEmpty)
        }
    }
}
@Test @MainActor func reviewProfileNegotiatedKindsStayRestricted() throws {
    let surface = ReviewSurface(); surface.capabilities = AndroidUICapabilities(kinds: [.text], textFieldAxes: [.horizontal], appearanceV2: true)
    let host = try reviewHost(surface); defer { host.close() }
    _ = try host.replace(with: ReviewSource())
    #expect(throws: (any Error).self) { try host.deliverLatest() }
    #expect(surface.frames.isEmpty)
}
@Test @MainActor func reviewProfileDriftDuringDeliverySnapshotMustRefuse() throws {
    let surface = ReviewSurface(), source = try ReviewSource()
    let host = try reviewHost(surface); defer { host.close() }
    let owner = try host.replace(with: source)
    source.onRead = { surface.profile = .measuredMultilineV2 }
    #expect(throws: AndroidUIHostError.profileMismatch) { try host.deliverLatest() }
    #expect(surface.frames.isEmpty && host.owner == nil && surface.revoked == [owner])
}
@Test @MainActor func reviewProfileDriftDuringSendSnapshotMustRefuseEffects() throws {
    let surface = ReviewSurface(), source = try ReviewSource()
    let host = try reviewHost(surface); defer { host.close() }
    let owner = try host.replace(with: source)
    #expect(try host.deliverLatest())
    let event = UIEventEnvelope(revision: 1, identity: try #require(source.value.identity(for: "go")), event: .activate)
    source.onRead = { surface.profile = .measuredMultilineV2 }
    #expect(throws: AndroidUIHostError.profileMismatch) { try host.send(owner: owner, event: event) }
    #expect(source.sends == 0 && host.owner == nil && surface.revoked == [owner])
}
@Test @MainActor func reviewProfileDriftDuringActivationMustRefuseOwner() throws {
    let surface = ReviewSurface(), source = try ReviewSource()
    let host = try reviewHost(surface); defer { host.close() }
    surface.onActivate = { surface.profile = .measuredMultilineV2 }
    #expect(throws: AndroidUIHostError.profileMismatch) { try host.replace(with: source) }
    #expect(host.owner == nil && host.pendingFrame == nil)
}
