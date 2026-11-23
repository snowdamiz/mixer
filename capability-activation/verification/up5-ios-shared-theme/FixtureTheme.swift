import MixerUI


enum FixtureTheme {
    static func configuration() throws -> UIAppearanceConfigurationV2 {
        let defaults = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
        let base = try shared(defaults)
        let light = palette(base.light, ink: rgb(8, 123, 103),
                            fill: rgb(82, 36, 138), label: rgb(218, 255, 171),
                            pressed: rgb(58, 27, 97), disabled: rgb(169, 81, 43))
        let dark = palette(base.dark, ink: rgb(250, 170, 81),
                           fill: rgb(16, 117, 163), label: rgb(255, 239, 199),
                           pressed: rgb(9, 73, 110), disabled: rgb(190, 152, 228))
        let button = UIButtonMetricsV2(
            labelInsets64: .init(top: 256, leading: 1024, bottom: 256, trailing: 1024),
            minimumHitWidth64: 9216, minimumHitHeight64: 2816, overlayRadius64: 512)
        let theme = UIThemeV2(recipe: base.recipe, typography: base.typography, light: light, dark: dark,
                              stacks: base.stacks, groupedList: base.groupedList, button: button,
                              field: base.field, toggle: base.toggle, navigation: base.navigation)
        return UIAppearanceConfigurationV2(id: "up5-shared-theme", mode: .shared(theme))
    }

    static func shared(_ configuration: UIAppearanceConfigurationV2) throws -> UIThemeV2 {
        guard case let .shared(theme) = configuration.mode else { throw UIAppearanceErrorV2.shape }
        return theme
    }

    private static func palette(_ base: UIPaintsV2, ink: UIRGBA8V1, fill: UIRGBA8V1,
                                label: UIRGBA8V1, pressed: UIRGBA8V1, disabled: UIRGBA8V1) -> UIPaintsV2 {
        let normal = UIButtonStatesV2(
            enabled: .init(label: label, background: fill),
            pressed: .init(label: label, background: pressed),
            disabled: .init(label: disabled, background: .init(red: 0, green: 0, blue: 0, alpha: 0)),
            focus: base.button.normal.focus)
        return UIPaintsV2(canvas: base.canvas, surface: base.surface, separator: base.separator,
                          text: .init(body: ink, headline: base.text.headline, title: base.text.title,
                                      caption: base.text.caption, sectionHeader: base.text.sectionHeader,
                                      navigationExpanded: base.text.navigationExpanded),
                          button: .init(normal: normal, destructive: base.button.destructive, cancel: base.button.cancel),
                          field: base.field, toggle: base.toggle)
    }

    private static func rgb(_ red: UInt8, _ green: UInt8, _ blue: UInt8) -> UIRGBA8V1 {
        UIRGBA8V1(red: red, green: green, blue: blue, alpha: 255)
    }
}
