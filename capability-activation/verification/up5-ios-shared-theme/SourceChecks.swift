import MixerUI
import SwiftUI

@main
struct SourceChecks {
    @MainActor
    static func main() throws {
        let configuration = try FixtureTheme.configuration()
        let theme = try MixerNativeTheme(configuration: configuration)
        let tokens = try FixtureTheme.shared(configuration)

        let light = theme.resolve(scheme: .light, size: .large, contrast: .standard, legibility: nil)
        let dark = theme.resolve(scheme: .dark, size: .accessibility5, contrast: .standard, legibility: nil)
        precondition(light.textPaint(.body) == tokens.light.text.body)
        precondition(dark.textPaint(.body) == tokens.dark.text.body)
        precondition(light.textPaint(.caption) == tokens.light.text.caption)
        precondition(light.profile == .l && dark.profile == .a5)
        precondition(dark.profile.metrics(for: .body).size64 == 3392)
        precondition(light.buttonMetrics == tokens.button)
        precondition(light.fontWeight(.body) == .w400 && light.fontWeight(.headline) == .w600)

        let released = NativeButtonState(isEnabled: true, isPressed: false)
        let pressed = NativeButtonState(isEnabled: true, isPressed: true)
        let disabled = NativeButtonState(isEnabled: false, isPressed: true)
        precondition(released == .enabled && pressed == .pressed && disabled == .disabled)
        precondition(NativeButtonState(isEnabled: false, isPressed: false) == .disabled)
        for (appearance, palette) in [(light, tokens.light), (dark, tokens.dark)] {
            for (role, states) in [(UIResolvedButtonRoleV2.normal, palette.button.normal),
                                   (.destructive, palette.button.destructive), (.cancel, palette.button.cancel)] {
                precondition(appearance.buttonPaint(role, state: released) == states.enabled)
                precondition(appearance.buttonPaint(role, state: pressed) == states.pressed)
                precondition(appearance.buttonPaint(role, state: disabled) == states.disabled)
            }
        }
        precondition(light.buttonPaint(.normal, state: pressed) != light.buttonPaint(.normal, state: released))
        precondition(light.buttonPaint(.normal, state: disabled).background.alpha == 0)

        let black = UIRGBA8V1(red: 0, green: 0, blue: 0, alpha: 255)
        let white = UIRGBA8V1(red: 255, green: 255, blue: 255, alpha: 255)
        for (scheme, ink, backdrop) in [(ColorScheme.light, black, white), (.dark, white, black)] {
            let appearance = theme.resolve(scheme: scheme, size: .large, contrast: .increased, legibility: .bold)
            precondition(appearance.textPaint(.body) == ink && appearance.contrast?.backdrop == backdrop)
            precondition(appearance.profile == .l)
            precondition(appearance.fontWeight(.body) == .w600)
            precondition(appearance.fontWeight(.headline) == .w700)
            precondition(appearance.fontWeight(.navigationExpanded) == .w700)
            for state in [released, pressed, disabled] {
                precondition(appearance.buttonPaint(.normal, state: state) == .init(label: ink, background: backdrop))
            }
        }
        precondition(pressed.contrastStroke.lineWidth > released.contrastStroke.lineWidth)
        precondition(disabled.contrastStroke.dash == [3, 2])
        print("PASS light/dark, measured type, bold, roles, enabled/pressed/disabled and increased-contrast mapping")

        let platform = UIAppearanceConfigurationV2(id: configuration.id, mode:
            .platformSpecific(iOS: tokens, android: tokens, reason: "fixture"))
        try expectError(.unsupportedNativeOperation) { _ = try MixerNativeTheme(configuration: platform) }
        let png = UIAppearanceResourceV1(id: "unused", kind: .iconPNG, path: "unused.png",
                                        sha256: String(repeating: "0", count: 64), bytes: 1,
                                        provenance: "fixture", scale: 1, locale: "und", direction: .neutral)
        try expectError(.unsupportedNativeOperation) {
            _ = try MixerNativeTheme(configuration: .init(id: configuration.id, mode: .shared(tokens), resources: [png]))
        }
        do {
            _ = try MixerNativeTheme(configuration: .init(id: "", mode: .shared(tokens)))
            preconditionFailure("Invalid descriptor ID was admitted")
        } catch is UIAppearanceErrorV2 {}

        let host = try MixerUIHost(document: MixerUI.UIDocument(revision: 1, root:
            UINode(id: "text", kind: .text, properties: ["text": .string("Ready")])))
        for (bold, contrast) in [(true, false), (false, true)] {
            let environment = UIAppearanceEnvironmentV2(scheme: .light, direction: .leftToRight, profile: .l,
                density1024: 1024, viewport: .init(width64: 1024, height64: 1024),
                safeArea64: .init(top: 0, leading: 0, bottom: 0, trailing: 0), localeIdentifier: "en",
                accessibility: .init(boldText: bold, increasedContrast: contrast, reduceMotion: false), generation: 1)
            try expectError(.unsupportedNativeOperation) {
                _ = try UIAppearanceResolverV2.prepare(snapshot: host.snapshot, configuration: configuration,
                                                       environment: environment, platform: .iOS)
            }
        }
        print("PASS shared descriptor validation and legacy resolver refusals")
    }

    private static func expectError(_ expected: UIAppearanceErrorV2, _ operation: () throws -> Void) throws {
        do {
            try operation()
            preconditionFailure("Expected \(expected)")
        } catch let error as UIAppearanceErrorV2 {
            precondition(error == expected, "Expected \(expected); got \(error)")
        }
    }
}
