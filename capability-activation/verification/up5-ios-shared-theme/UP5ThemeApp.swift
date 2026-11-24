import Foundation
import MixerApple
import MixerCapabilityActivation
import MixerUI
import SwiftUI
import UIKit

@main
struct UP5ThemeApp: App {
    @StateObject private var fixture = FixtureRun()
    @State private var dark = false
    @State private var heldSample = "waiting"
    private let arguments = ProcessInfo.processInfo.arguments

    var body: some Scene {
        WindowGroup {
            VStack {
                Text(fixture.status).accessibilityIdentifier("fixture-status")
                Text(fixture.result).accessibilityIdentifier("fixture-result")
                if arguments.contains("--contrast-probe") {
                    ContrastObservation()
                }
                if arguments.contains("--system-bold-text-probe") {
                    BoldTextObservation()
                }
                if arguments.contains("--held-press-probe") {
                    Text(heldSample).lineLimit(1).accessibilityIdentifier("held-sample")
                }
                Group {
                    if let owner = fixture.owner {
                        MixerGuestScreen(presentation: owner.presentation).sharedTheme(fixture.theme)
                    } else if let host = fixture.bundled {
                        MixerNativeView(host: host, onAction: fixture.bundledAction).sharedTheme(fixture.theme)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background {
                    if arguments.contains("--contrast-probe") {
                        Color(.sRGB, red: 0.33, green: 0.43, blue: 0.52)
                    }
                }
                .modifier(FixtureTypographyControl(arguments: arguments))

                Button(dark ? "Use light" : "Use dark") { dark.toggle() }
                Button("Close fixture") { Task { await fixture.close() } }
            }
            .padding()
            .background {
                if arguments.contains("--held-press-probe") {
                    HeldPressProbe(actionCount: { fixture.actionCount }, report: { heldSample = $0 })
                        .allowsHitTesting(false)
                }
            }
            .preferredColorScheme(dark ? .dark : .light)
            .task { await fixture.start() }
        }
    }
}

private struct ContrastObservation: View {
    @Environment(\.colorSchemeContrast) private var contrast

    var body: some View {
        Text(verbatim: "swiftui=\(contrast == .increased) system=\(UIAccessibility.isDarkerSystemColorsEnabled)")
            .accessibilityIdentifier("contrast-observation")
    }
}

private struct BoldTextObservation: View {
    @Environment(\.legibilityWeight) private var weight
    @Environment(\.dynamicTypeSize) private var size

    var body: some View {
        let legibility = switch weight {
        case .bold?: "bold"
        case .regular?: "regular"
        case nil: "unspecified"
        @unknown default: "unknown"
        }
        Text(verbatim: "system=\(UIAccessibility.isBoldTextEnabled) swiftui=\(legibility) size=\(size)")
            .accessibilityIdentifier("bold-text-observation")
    }
}

private struct FixtureTypographyControl: ViewModifier {
    let arguments: [String]

    func body(content: Content) -> some View {
        if arguments.contains("--bold-loan") {
            content.environment(\.legibilityWeight, .bold).environment(\.dynamicTypeSize, .large)
        } else if arguments.contains("--regular-loan") {
            content.environment(\.legibilityWeight, .regular).environment(\.dynamicTypeSize, .large)
        } else if arguments.contains("--held-press-probe") {
            content.environment(\.dynamicTypeSize, .large)
        } else {
            content
        }
    }
}

@MainActor
private final class FixtureRun: ObservableObject {
    @Published private(set) var status = "starting"
    @Published private(set) var result = "empty"
    @Published private(set) var theme: MixerNativeTheme?
    @Published private(set) var bundled: MixerUIHost?
    @Published private(set) var owner: CapabilityGuestUIRuntime?
    private(set) var actionCount = 0
    private var signed: SignedFixture?

    func start() async {
        guard status == "starting" else { return }
        do {
            let args = ProcessInfo.processInfo.arguments
            if args.contains("--held-press-probe") {
                try HeldPressProbe.discardPreviousCapture()
            }
            if !args.contains("--platform-control") {
                theme = try MixerNativeTheme(configuration: FixtureTheme.configuration())
            }
            if args.contains("--signed-guest") {
                try await startGuest()
            } else {
                bundled = try MixerUIHost(document: Self.document)
                status = "bundled"
            }
        } catch {
            status = "ERROR \(error)"
        }
    }

    private func startGuest() async throws {
        let support = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                                  appropriateFor: nil, create: true)
        let root = support.appendingPathComponent("UP5Theme-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        let fixture = try SignedFixture(root: root)
        signed = fixture
        let runtime = try await CapabilityGuestUIRuntime.open(configuration: fixture.configuration, execution: fixture.execution)
        let bytes = GuestUISignedProgram.build()
        let offer = try fixture.offer(bytes, sequence: 1)
        try await runtime.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment)
        try await runtime.appendDownload(bytes, atOffset: 0)
        try await runtime.finishDownload()
        let staged = await runtime.recoverySnapshot()
        let candidate = try require(staged.staged, "staged candidate")
        owner = runtime
        let launch = try await runtime.start()
        try check(launch.candidateID == candidate && launch.acceptedSequence == 1 && launch.launchID != nil,
                  "wrong signed guest selected")
        let deadline = ContinuousClock.now + .seconds(15)
        while true {
            let state = await runtime.recoverySnapshot()
            if state.activation.phase == .healthyGuest, state.healthy == candidate { break }
            try check(ContinuousClock.now < deadline, "signed guest did not reach native display health")
            try await Task.sleep(for: .milliseconds(20))
        }
        status = "signed guest healthy"
    }

    func bundledAction(_ action: RoutedUIAction) {
        actionCount += 1
        if action.actionID != "sample.save" {
            result = "wrong action"
        } else {
            result = actionCount == 1 ? "bundled action routed" : "bundled action routed \(actionCount) times"
        }
    }

    func close() async {
        if let owner { await owner.close() }
        do {
            status = "closed, disk=" + (try signed?.liveSavedValue() ?? "empty")
            if let signed { try FileManager.default.removeItem(at: signed.root) }
        } catch {
            status = "ERROR \(error)"
        }
    }

    private static let document = MixerUI.UIDocument(revision: 1, root: UINode(id: "root", kind: .vStack, children: [
        UINode(id: "status", kind: .text, properties: ["text": .string("Ready")]),
        UINode(id: "save", kind: .button, properties: ["label": .string("Save sample")],
               actions: [UIActionBinding(id: "sample.save", event: .activate)]),
        UINode(id: "unavailable", kind: .button, properties: ["label": .string("Unavailable"), "disabled": .bool(true)],
               actions: [UIActionBinding(id: "sample.disabled", event: .activate)])
    ]))
}
