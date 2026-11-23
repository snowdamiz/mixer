import MixerSwiftUI
import MixerUI
import ReplayFeature

private func appearance(_ scheme: UIColorSchemeV1, _ direction: UILayoutDirectionV1) -> UIAppearanceEnvironmentV2 {
    UIAppearanceEnvironmentV2(
        scheme: scheme, direction: direction, profile: .l, density1024: 1024,
        viewport: UIAppearanceViewportV2(width64: 24_960, height64: 54_016),
        safeArea64: UIInsets64V1(top: 0, leading: 0, bottom: 0, trailing: 0),
        localeIdentifier: "en-US",
        accessibility: UIAppearanceAccessibilityV2(boldText: false, increasedContrast: false, reduceMotion: false),
        generation: 1
    )
}

private struct EnvironmentMount: View {
    @Environment(\.colorScheme) private var colorScheme
    let screen: EnvironmentScreen
    var probe: (() -> ColorScheme) -> Void = { _ in }

    var body: some View {
        let _ = probe { colorScheme }
        screen
    }
}

private extension EnvironmentValues {
    var customScheme: ColorScheme { preconditionFailure("An unsupported environment getter ran") }
}

private struct UnsupportedEnvironmentScreen: View {
    @Environment(\.customScheme) private var scheme

    var body: some View { Text(scheme == .dark ? "Dark" : "Light") }
}

func typedEnvironment() throws {
    let session = FeatureSession(executor: replayExecutor)
    let inner = FeatureSession(executor: replayExecutor)
    var nestedDispatch: () -> Void = {}
    let screen = EnvironmentScreen { nestedDispatch() }
    let innerScreen = EnvironmentScreen {
        expect(screen.summary == "Light/LTR", "An inner event must have no access to the outer declaration")
    }

    func stage(_ environment: UIAppearanceEnvironmentV2? = nil) throws -> PreparedFrame {
        try session.prepare(environment: environment) { EnvironmentMount(screen: screen) }
    }

    let defaults = try stage()
    expect(text(defaults) == ["Light/LTR", "No reading"], "A mount without host input must use both defaults")
    expect(screen.summary == "Light/LTR", "An idle environment read must use defaults")

    var nestedBuild: Result<PreparedFrame, any Error>?
    let first = try session.prepare(environment: appearance(.dark, .rightToLeft)) {
        expect(screen.summary == "Light/LTR", "The root factory must not bind unrelated view declarations")
        return EnvironmentMount(screen: screen) { enclosingScheme in
            expect(enclosingScheme() == .dark, "The outer body must see its host input")
            nestedBuild = Result {
                try inner.prepare(environment: appearance(.dark, .leftToRight)) {
                    expect(enclosingScheme() == .light, "A nested mount must mask the enclosing turn")
                    return innerScreen
                }
            }
            expect(enclosingScheme() == .dark, "A nested mount must restore the enclosing turn")
        }
    }
    let nested = try nestedBuild!.get()
    expect(text(nested) == ["Dark/LTR", "No reading"], "The inner document must use its own host input")
    expect(text(first) == ["Dark/RTL", "No reading"], "Both resolved host values must reach the outer document")
    expect(!session.finish(defaults.presentation.token, outcome: .drawnAndInputReady), "Superseded defaults are stale")
    accept(first, in: session)
    accept(nested, in: inner)

    let firstEvent = event(first, button: "Record environment")
    let candidateEnvironment = appearance(.light, .leftToRight)
    for outcome: PresentationOutcome in [.canceled, .failed] {
        let candidate = try stage(candidateEnvironment)
        let input = event(candidate, button: "Record environment")
        expect(text(candidate) == ["Light/LTR", "No reading"], "Each candidate must use its own host input")
        expect(session.dispatch(candidate.presentation.token, input) == .rejected, "Staged input must be refused")
        expect(session.finish(candidate.presentation.token, outcome: outcome), "Discard must consume its own candidate")
        expect(!session.finish(candidate.presentation.token, outcome: .drawnAndInputReady),
               "A discarded environment cannot be promoted")
        expect(session.dispatch(candidate.presentation.token, input) == .rejected, "Discarded input must be refused")
        expect(session.acceptedPresentation?.snapshot.document == first.presentation.snapshot.document,
               "Discard must leave the accepted document intact")
    }

    let refused = try stage(candidateEnvironment)
    try expectError(FeatureError.unsupportedEnvironment) {
        _ = try session.prepare(environment: candidateEnvironment) { UnsupportedEnvironmentScreen() }
    }
    expect(!session.finish(refused.presentation.token, outcome: .drawnAndInputReady),
           "A refused build must supersede the previous candidate")

    let pending = try stage(candidateEnvironment)
    nestedDispatch = {
        expect(inner.dispatch(nested.presentation.token, event(nested, button: "Record environment")) ==
               .handled(superseded: nil), "Nested dispatch must route on its own accepted frame")
    }
    defer { nestedDispatch = {} }
    expect(session.dispatch(first.presentation.token, firstEvent) == .handled(superseded: pending.presentation.token),
           "Accepted input must supersede pending environment changes")
    expect(!session.finish(pending.presentation.token, outcome: .drawnAndInputReady),
           "Late draw after accepted input must be refused")
    nestedDispatch = {}

    let updatedInner = try inner.prepare { innerScreen }
    expect(text(updatedInner) == ["Light/LTR", "Dark/LTR -> Dark/LTR"],
           "Inner action must use the inner accepted environment and update only inner state")
    let successor = try stage(appearance(.light, .rightToLeft))
    expect(text(successor) == ["Light/RTL", "Dark/RTL -> Dark/RTL"],
           "Outer action must use the outer accepted environment before and after nested dispatch")
    accept(successor, in: session)
    expect(session.dispatch(first.presentation.token, firstEvent) == .rejected,
           "Promoting new environment must retire the previous frame's input")
    expect(session.dispatch(successor.presentation.token, event(successor, button: "Record environment")) ==
           .handled(superseded: nil), "The successor must handle its own input")
    expect(text(try stage()) == ["Light/LTR", "Light/RTL -> Light/RTL"],
           "Successor input must read the promoted snapshot and a subsequent default build must reset both values")
    expect(screen.summary == "Light/LTR", "Finished turns must leave idle reads at their defaults")
    print("PASS typed environment defaults, host snapshots, mount isolation, and accepted frame callbacks")
}
