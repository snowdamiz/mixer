import Foundation
import Testing
import MixerUI
import MixerAndroid

@MainActor private final class ProfileSurface: AndroidUINativeSurface {
    var profile: AndroidUIProfile
    var capabilities: AndroidUICapabilities
    var owners: [UUID] = []
    var frames: [AndroidUIFrame] = []
    var revoked: [UUID] = []
    init(_ profile: AndroidUIProfile, capabilities: AndroidUICapabilities? = nil) {
        self.profile = profile; self.capabilities = capabilities ?? profile.capabilities
    }
    func activate(owner: UUID) throws { owners.append(owner) }
    func install(_ frame: AndroidUIFrame) throws { frames.append(frame) }
    func revoke(owner: UUID) { revoked.append(owner) }
}
@MainActor private final class ProfilePresentation: AndroidUIPresentation {
    let snapshot: UIRenderSnapshot
    var sends = 0
    init() throws {
        var reconciler = UIReconciler(validator: UIValidator(supportedTextFieldAxes: [.horizontal, .vertical]))
        try reconciler.apply(TextField("note", "Note", value: "Café\r\n漢字 e\u{301} 🏗️", action: "edit", axis: .vertical).document(revision: 1))
        snapshot = try reconciler.currentSnapshot()
    }
    func observe(_ receive: @escaping @MainActor (UIRenderSnapshot) -> Void) -> @MainActor () -> Void {
        receive(snapshot); return {}
    }
    func send(_ event: UIEventEnvelope) throws { sends += 1 }
}
private func profileEnvironment() -> UIAppearanceEnvironmentV2 {
    UIAppearanceEnvironmentV2(scheme: .light, direction: .leftToRight, profile: .l, density1024: 1024,
        viewport: UIAppearanceViewportV2(width64: 24000, height64: 40000),
        safeArea64: UIInsets64V1(top: 0, leading: 0, bottom: 0, trailing: 0), localeIdentifier: "en-US",
        accessibility: UIAppearanceAccessibilityV2(boldText: false, increasedContrast: false, reduceMotion: false), generation: 1)
}
@Test func profile10MapsEveryNativeIdentityWithoutConflatingV2AndV3() {
    #expect(AndroidUIProfile.allCases.map(\.rawValue) == ["LEGACY_HORIZONTAL", "MEASURED_MULTILINE_V2", "MEASURED_MULTILINE_RETIREMENT_V3", "MEASURED_MULTILINE_LONG_NOTES_V4"])
    #expect(AndroidUIProfile.measuredMultilineV2 != .measuredMultilineRetirementV3)
    #expect(AndroidUIProfile.measuredMultilineLongNotesV4 != .measuredMultilineRetirementV3)
    #expect(AndroidUIProfile.measuredMultilineLongNotesV4.textValuePolicy == .longNoteV1)
    #expect(AndroidUIProfile.measuredMultilineRetirementV3.textValuePolicy == .standard)
    #expect(AndroidUIProfile.measuredMultilineV2.capabilities.textFieldAxes == AndroidUIProfile.measuredMultilineRetirementV3.capabilities.textFieldAxes)
    #expect(AndroidUIProfile.legacyHorizontal.capabilities.textFieldAxes == [.horizontal])
}
@Test @MainActor func profile10V3AppearanceAndPacketPreserveV2UnicodeRecipe() throws {
    let source = try ProfilePresentation(), config = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
    let v2 = AndroidUIProfile.measuredMultilineV2, v3 = AndroidUIProfile.measuredMultilineRetirementV3
    let before = try v2.prepareAppearance(snapshot: source.snapshot, configuration: config, environment: profileEnvironment())
    let after = try v3.prepareAppearance(snapshot: source.snapshot, configuration: config, environment: profileEnvironment())
    #expect(before.nodes == after.nodes)
    #expect(try source.snapshot.encodeNativePacketV1(supportedTextFieldAxes: v2.capabilities.textFieldAxes) == source.snapshot.encodeNativePacketV1(supportedTextFieldAxes: v3.capabilities.textFieldAxes))
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) {
        try AndroidUIProfile.legacyHorizontal.prepareAppearance(snapshot: source.snapshot, configuration: config, environment: profileEnvironment())
    }
    #expect(source.sends == 0)
}
@Test @MainActor func profile10EqualAxesCannotAuthorizeMismatchedSurface() throws {
    let surface = ProfileSurface(.measuredMultilineV2)
    #expect(throws: AndroidUIHostError.profileMismatch) {
        try AndroidUIHost(surface: surface, profile: .measuredMultilineRetirementV3,
            appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: {})
    }
    #expect(surface.owners.isEmpty && surface.frames.isEmpty)
}
@Test @MainActor func profile10FrameCarriesExplicitV3AndInstallationDoesNotSendEffects() throws {
    let surface = ProfileSurface(.measuredMultilineRetirementV3), source = try ProfilePresentation()
    let host = try AndroidUIHost(surface: surface, profile: .measuredMultilineRetirementV3,
        appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: {})
    defer { host.close() }
    let owner = try host.replace(with: source)
    #expect(host.profile == .measuredMultilineRetirementV3)
    #expect(host.pendingFrame?.profile == .measuredMultilineRetirementV3)
    #expect(surface.frames.isEmpty && source.sends == 0)
    #expect(try host.deliverLatest())
    #expect(surface.frames.count == 1 && surface.frames[0].owner == owner)
    #expect(surface.frames[0].profile == .measuredMultilineRetirementV3 && source.sends == 0)
    #expect(try !host.deliverLatest())
}
@Test @MainActor func profile10ChangedSurfaceIdentityRevokesBeforeInstallation() throws {
    let surface = ProfileSurface(.measuredMultilineRetirementV3), source = try ProfilePresentation()
    let host = try AndroidUIHost(surface: surface, profile: .measuredMultilineRetirementV3,
        appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: {})
    defer { host.close() }
    let owner = try host.replace(with: source)
    surface.profile = .measuredMultilineV2
    #expect(throws: AndroidUIHostError.profileMismatch) { try host.deliverLatest() }
    #expect(host.owner == nil && host.pendingFrame == nil)
    #expect(surface.revoked == [owner] && surface.frames.isEmpty && source.sends == 0)
}
@Test @MainActor func profile10InflatedCapabilitiesCannotUpgradeLegacySelection() throws {
    let surface = ProfileSurface(.legacyHorizontal, capabilities: AndroidUIProfile.measuredMultilineRetirementV3.capabilities)
    let host = try AndroidUIHost(surface: surface, profile: .legacyHorizontal,
        appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: {})
    defer { host.close() }
    _ = try host.replace(with: ProfilePresentation())
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) { try host.deliverLatest() }
    #expect(surface.frames.isEmpty)
}
