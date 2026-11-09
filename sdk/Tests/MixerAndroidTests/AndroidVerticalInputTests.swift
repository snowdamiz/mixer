import Foundation
import Testing
import MixerUI
import MixerAndroid

private func verticalSnapshot(_ value: String, axis: TextFieldAxis = .vertical) throws -> UIRenderSnapshot {
    var reconciler = UIReconciler(validator: UIValidator(supportedTextFieldAxes: [.horizontal, .vertical]))
    try reconciler.apply(TextField("task", "Task", value: value, action: "changed", axis: axis).document(revision: 1))
    return try reconciler.currentSnapshot()
}
private func verticalEnvironment() -> UIAppearanceEnvironmentV2 {
    UIAppearanceEnvironmentV2(scheme: .light, direction: .leftToRight, profile: .l, density1024: 1024,
        viewport: UIAppearanceViewportV2(width64: 24000, height64: 40000),
        safeArea64: UIInsets64V1(top: 0, leading: 0, bottom: 0, trailing: 0), localeIdentifier: "en-US",
        accessibility: UIAppearanceAccessibilityV2(boldText: false, increasedContrast: false, reduceMotion: false), generation: 1)
}
@Test func verticalProfileRequiresExplicitPacketAndAppearanceAdmission() throws {
    let text = "\nCafé\r\n漢字 e\u{301} 🏗️\nمسؤول"
    let snapshot = try verticalSnapshot(text)
    let configuration = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) { try snapshot.encodeNativePacketV1() }
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) {
        try AndroidUIProfile.legacyHorizontal.prepareAppearance(snapshot: snapshot, configuration: configuration, environment: verticalEnvironment())
    }
    #expect(throws: UIValidationError.unsupportedTextFieldAxis(.vertical)) {
        try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: configuration, environment: verticalEnvironment(), platform: .android)
    }
    let profile = AndroidUIProfile.measuredMultilineV2
    let bytes = try snapshot.encodeNativePacketV1(supportedTextFieldAxes: profile.capabilities.textFieldAxes)
    #expect(String(decoding: bytes, as: UTF8.self).contains("vertical"))
    let plan = try profile.prepareAppearance(snapshot: snapshot, configuration: configuration, environment: verticalEnvironment())
    guard case let .textField(_, value, resolved, _) = plan.node(for: "task")?.recipe else { Issue.record("missing field"); return }
    #expect(Array(value.utf8) == Array(text.utf8))
    #expect(resolved.maximumLines == nil)
    #expect(plan.node(for: "task")?.identity == snapshot.identity(for: "task"))
}
@Test func verticalProfilePreservesHorizontalBytesAndRecipe() throws {
    let snapshot = try verticalSnapshot("Responsible — Zoë", axis: .horizontal)
    let configuration = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
    #expect(try snapshot.encodeNativePacketV1() == snapshot.encodeNativePacketV1(supportedTextFieldAxes: AndroidUIProfile.measuredMultilineV2.capabilities.textFieldAxes))
    let old = try AndroidUIProfile.legacyHorizontal.prepareAppearance(snapshot: snapshot, configuration: configuration, environment: verticalEnvironment())
    let new = try AndroidUIProfile.measuredMultilineV2.prepareAppearance(snapshot: snapshot, configuration: configuration, environment: verticalEnvironment())
    #expect(old.nodes == new.nodes)
    #expect(AndroidUICapabilities().textFieldAxes.isEmpty)
}
