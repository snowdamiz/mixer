#if os(iOS)
import MixerUI
import SwiftUI

// The S4 fixture installs this adapter only in its private MixerApple build.
public struct S4NativeTheme: Sendable {
    let bodyPaint: UIRGBA8V1
    let normalButton: UIButtonStatesV2
    let buttonMetrics: UIButtonMetricsV2

    public init(bodyPaint: UIRGBA8V1, normalButton: UIButtonStatesV2, buttonMetrics: UIButtonMetricsV2) {
        self.bodyPaint = bodyPaint
        self.normalButton = normalButton
        self.buttonMetrics = buttonMetrics
    }
}

struct S4NativeThemeStyle: ViewModifier {
    let theme: S4NativeTheme?

    func body(content: Content) -> some View {
        if let theme {
            content
                .foregroundStyle(Color(s4: theme.bodyPaint))
                .buttonStyle(S4SaveButtonStyle(states: theme.normalButton, metrics: theme.buttonMetrics))
        } else {
            content
        }
    }
}

private struct S4SaveButtonStyle: ButtonStyle {
    let states: UIButtonStatesV2
    let metrics: UIButtonMetricsV2

    func makeBody(configuration: Configuration) -> some View {
        S4SaveButtonLabel(configuration: configuration, states: states, metrics: metrics)
    }
}

private struct S4SaveButtonLabel: View {
    @Environment(\.isEnabled) private var isEnabled
    let configuration: ButtonStyleConfiguration
    let states: UIButtonStatesV2
    let metrics: UIButtonMetricsV2

    var body: some View {
        let paint = isEnabled ? (configuration.isPressed ? states.pressed : states.enabled) : states.disabled
        let insets = metrics.labelInsets64
        let shape = RoundedRectangle(cornerRadius: CGFloat(metrics.overlayRadius64) / 64)
        configuration.label
            .foregroundStyle(Color(s4: paint.label))
            .padding(EdgeInsets(top: CGFloat(insets.top) / 64, leading: CGFloat(insets.leading) / 64,
                                bottom: CGFloat(insets.bottom) / 64, trailing: CGFloat(insets.trailing) / 64))
            .frame(minWidth: CGFloat(metrics.minimumHitWidth64) / 64, minHeight: CGFloat(metrics.minimumHitHeight64) / 64)
            .background(Color(s4: paint.background), in: shape)
            .contentShape(shape)
    }
}

private extension Color {
    init(s4 color: UIRGBA8V1) {
        self.init(.sRGB, red: Double(color.red) / 255, green: Double(color.green) / 255,
                  blue: Double(color.blue) / 255, opacity: Double(color.alpha) / 255)
    }
}
#endif
