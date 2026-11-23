#if canImport(SwiftUI)
import MixerUI
import SwiftUI

/// App-supplied appearance for literal Text and Button in MixerNativeView.
/// This value conveys no resource installation or guest display authority.
public struct MixerNativeTheme: Sendable, Equatable {
    private let theme: UIThemeV2

    public init(configuration: UIAppearanceConfigurationV2) throws {
        try UIAppearanceDescriptorCodecV2.validate(configuration)
        guard case let .shared(theme) = configuration.mode,
              configuration.resources.isEmpty,
              case .systemSans = theme.typography.font else {
            throw UIAppearanceErrorV2.unsupportedNativeOperation
        }
        self.theme = theme
    }

    func resolve(scheme: ColorScheme, size: DynamicTypeSize, contrast: ColorSchemeContrast,
                 legibility: LegibilityWeight?) -> ResolvedNativeTheme {
        ResolvedNativeTheme(
            paints: scheme == .dark ? theme.dark : theme.light,
            buttonMetrics: theme.button,
            profile: size.mixerProfile ?? theme.typography.defaultProfile,
            contrast: contrast == .increased ? NativeContrastPaints(dark: scheme == .dark) : nil,
            bold: legibility == .bold
        )
    }
}

struct ResolvedNativeTheme {
    let paints: UIPaintsV2
    let buttonMetrics: UIButtonMetricsV2
    let profile: UISharedTextProfileV1
    let contrast: NativeContrastPaints?
    let bold: Bool

    func fontWeight(_ role: UISharedTextRoleV1) -> UIFontWeightV1 {
        let weight = profile.metrics(for: role).weight
        guard bold else { return weight }
        switch weight {
        case .w400, .w500: return .w600
        case .w600, .w700: return .w700
        }
    }

    func font(_ role: UISharedTextRoleV1) -> Font {
        let weight: Font.Weight = switch fontWeight(role) {
        case .w400: .regular
        case .w500: .medium
        case .w600: .semibold
        case .w700: .bold
        }
        return .system(size: CGFloat(profile.metrics(for: role).size64) / 64, weight: weight)
    }

    func textPaint(_ role: UISharedTextRoleV1) -> UIRGBA8V1 {
        if let contrast { return contrast.ink }
        switch role {
        case .body: return paints.text.body
        case .headline: return paints.text.headline
        case .title: return paints.text.title
        case .caption: return paints.text.caption
        case .sectionHeader: return paints.text.sectionHeader
        case .navigationExpanded: return paints.text.navigationExpanded
        }
    }

    func buttonPaint(_ role: UIResolvedButtonRoleV2, state: NativeButtonState) -> UIButtonPaintV2 {
        if let contrast {
            return UIButtonPaintV2(label: contrast.ink, background: contrast.backdrop)
        }
        let states: UIButtonStatesV2 = switch role {
        case .normal: paints.button.normal
        case .destructive: paints.button.destructive
        case .cancel: paints.button.cancel
        }
        switch state {
        case .enabled: return states.enabled
        case .pressed: return states.pressed
        case .disabled: return states.disabled
        }
    }
}

struct NativeContrastPaints {
    let ink: UIRGBA8V1
    let backdrop: UIRGBA8V1

    init(dark: Bool) {
        let black = UIRGBA8V1(red: 0, green: 0, blue: 0, alpha: 255)
        let white = UIRGBA8V1(red: 255, green: 255, blue: 255, alpha: 255)
        ink = dark ? white : black
        backdrop = dark ? black : white
    }
}

enum NativeButtonState: Equatable {
    case enabled, pressed, disabled

    init(isEnabled: Bool, isPressed: Bool) {
        self = isEnabled ? (isPressed ? .pressed : .enabled) : .disabled
    }

    var contrastStroke: StrokeStyle {
        switch self {
        case .enabled: StrokeStyle(lineWidth: 1)
        case .pressed: StrokeStyle(lineWidth: 3)
        case .disabled: StrokeStyle(lineWidth: 1, dash: [3, 2])
        }
    }
}

struct NativeThemedButtonStyle: ButtonStyle {
    let theme: ResolvedNativeTheme
    let role: UIResolvedButtonRoleV2

    func makeBody(configuration: Configuration) -> some View {
        NativeThemedButtonLabel(configuration: configuration, theme: theme, role: role)
    }
}

private struct NativeThemedButtonLabel: View {
    @Environment(\.isEnabled) private var isEnabled
    let configuration: ButtonStyleConfiguration
    let theme: ResolvedNativeTheme
    let role: UIResolvedButtonRoleV2

    var body: some View {
        let state = NativeButtonState(isEnabled: isEnabled, isPressed: configuration.isPressed)
        let paint = theme.buttonPaint(role, state: state)
        let metrics = theme.buttonMetrics
        let insets = metrics.labelInsets64
        let shape = RoundedRectangle(cornerRadius: CGFloat(metrics.overlayRadius64) / 64)
        configuration.label
            .font(theme.font(.body))
            .foregroundStyle(Color(mixerRGBA: paint.label))
            .padding(EdgeInsets(top: CGFloat(insets.top) / 64, leading: CGFloat(insets.leading) / 64,
                                bottom: CGFloat(insets.bottom) / 64, trailing: CGFloat(insets.trailing) / 64))
            .frame(minWidth: CGFloat(metrics.minimumHitWidth64) / 64,
                   minHeight: CGFloat(metrics.minimumHitHeight64) / 64)
            .background(Color(mixerRGBA: paint.background), in: shape)
            .overlay {
                if let contrast = theme.contrast {
                    // The outer and inner edges stay visible on either light or dark surroundings.
                    shape.strokeBorder(Color(mixerRGBA: contrast.backdrop), lineWidth: 1)
                        .overlay {
                            shape.inset(by: 1).strokeBorder(Color(mixerRGBA: contrast.ink),
                                                           style: state.contrastStroke)
                        }
                        .allowsHitTesting(false)
                }
            }
            .contentShape(shape)
    }
}

extension Color {
    init(mixerRGBA paint: UIRGBA8V1) {
        self.init(.sRGB, red: Double(paint.red) / 255, green: Double(paint.green) / 255,
                  blue: Double(paint.blue) / 255, opacity: Double(paint.alpha) / 255)
    }
}

private extension DynamicTypeSize {
    var mixerProfile: UISharedTextProfileV1? {
        switch self {
        case .xSmall: .xs
        case .small: .s
        case .medium: .m
        case .large: .l
        case .xLarge: .xl
        case .xxLarge: .xxl
        case .xxxLarge: .xxxl
        case .accessibility1: .a1
        case .accessibility2: .a2
        case .accessibility3: .a3
        case .accessibility4: .a4
        case .accessibility5: .a5
        @unknown default: nil
        }
    }
}
#endif
