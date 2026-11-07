#if canImport(UIKit)
import UIKit
import MixerUI

/// An owner/window capture, never a public Environment supplied as authority.
@MainActor final class AppearanceEnvironmentV2 {
    enum Failure: Error { case unattached, profile, unsupportedAccessibility, generationExhausted, runtime }
    private var generation: UInt64 = 0
    private var last: UIAppearanceEnvironmentV2?
    private var windowID: ObjectIdentifier?
    private var invalidated = true
    func invalidate() { invalidated = true }

    func capture(_ view: UIView) throws -> UIAppearanceEnvironmentV2 {
        guard let window = view.window, view.bounds.width > 0, view.bounds.height > 0 else { throw Failure.unattached }
        let version = ProcessInfo.processInfo.operatingSystemVersion
        // Public APIs compile for iOS17; only this executed runtime is admitted.
        guard version.majorVersion == 26 && version.minorVersion == 5 else { throw Failure.runtime }
        let traits = view.traitCollection
        let profiles: [UIContentSizeCategory: UISharedTextProfileV1] = [
            .extraSmall: .xs, .small: .s, .medium: .m, .large: .l, .extraLarge: .xl,
            .extraExtraLarge: .xxl, .extraExtraExtraLarge: .xxxl,
            .accessibilityMedium: .a1, .accessibilityLarge: .a2, .accessibilityExtraLarge: .a3,
            .accessibilityExtraExtraLarge: .a4, .accessibilityExtraExtraExtraLarge: .a5]
        guard let profile = profiles[traits.preferredContentSizeCategory] else { throw Failure.profile }
        let accessibility = UIAppearanceAccessibilityV2(boldText: UIAccessibility.isBoldTextEnabled,
            increasedContrast: traits.accessibilityContrast == .high, reduceMotion: UIAccessibility.isReduceMotionEnabled)
        guard !accessibility.boldText, !accessibility.increasedContrast else { throw Failure.unsupportedAccessibility }
        let scale = try UIAppearanceGeometryV2.normalizeDensity(Double(window.screen.scale))
        func extent(_ x: CGFloat) throws -> UInt32 { try UIAppearanceGeometryV2.measuredExtent64(Double(x)) }
        let insets = view.safeAreaInsets
        let candidate = UIAppearanceEnvironmentV2(scheme: traits.userInterfaceStyle == .dark ? .dark : .light,
            direction: view.effectiveUserInterfaceLayoutDirection == .rightToLeft ? .rightToLeft : .leftToRight,
            profile: profile, density1024: scale,
            viewport: .init(width64: try extent(view.bounds.width), height64: try extent(view.bounds.height)),
            safeArea64: .init(top: try extent(insets.top), leading: try extent(view.effectiveUserInterfaceLayoutDirection == .rightToLeft ? insets.right : insets.left),
                              bottom: try extent(insets.bottom), trailing: try extent(view.effectiveUserInterfaceLayoutDirection == .rightToLeft ? insets.left : insets.right)),
            localeIdentifier: Locale.current.identifier, accessibility: accessibility, generation: 0)
        if invalidated || windowID != ObjectIdentifier(window) || last != candidate {
            guard generation < UInt64.max else { throw Failure.generationExhausted }
            generation += 1; last = candidate; windowID = ObjectIdentifier(window); invalidated = false
        }
        return UIAppearanceEnvironmentV2(scheme: candidate.scheme, direction: candidate.direction, profile: candidate.profile,
            density1024: candidate.density1024, viewport: candidate.viewport, safeArea64: candidate.safeArea64,
            localeIdentifier: candidate.localeIdentifier, accessibility: accessibility, generation: generation)
    }
}
#endif
