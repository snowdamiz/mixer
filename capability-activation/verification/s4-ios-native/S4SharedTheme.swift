import MixerApple
import MixerUI

enum S4SharedTheme {
    static let light = S4NativeTheme(
        bodyPaint: rgb(8, 123, 103),
        normalButton: UIButtonStatesV2(
            enabled: UIButtonPaintV2(label: rgb(218, 255, 171), background: rgb(82, 36, 138)),
            pressed: UIButtonPaintV2(label: rgb(218, 255, 171), background: rgb(58, 27, 97)),
            disabled: UIButtonPaintV2(label: rgb(243, 245, 246), background: rgb(84, 90, 93)),
            focus: UIOutlineV2(color: rgb(8, 123, 103), width64: 128, radius64: 512)
        ),
        buttonMetrics: UIButtonMetricsV2(
            labelInsets64: UIInsets64V1(top: 256, leading: 1024, bottom: 256, trailing: 1024),
            minimumHitWidth64: 9216, minimumHitHeight64: 2816, overlayRadius64: 512
        )
    )

    private static func rgb(_ red: UInt8, _ green: UInt8, _ blue: UInt8) -> UIRGBA8V1 {
        UIRGBA8V1(red: red, green: green, blue: blue, alpha: 255)
    }
}
