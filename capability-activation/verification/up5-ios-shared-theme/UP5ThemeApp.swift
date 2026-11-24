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
    @State private var contactSample = "waiting"
    private let arguments = ProcessInfo.processInfo.arguments
    private var comparesPress: Bool { arguments.contains("--compare-press") }
    private var usesAppleControl: Bool { comparesPress && arguments.contains("--apple-press-control") }
    private var capturePress: Bool {
        arguments.contains("--held-press-probe") || (comparesPress && !usesAppleControl)
    }
    private var observeContact: Bool { arguments.contains("--contact-probe") }

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
                if capturePress || comparesPress {
                    Text(heldSample).lineLimit(1).accessibilityIdentifier("held-sample")
                }
                if observeContact {
                    Text(contactSample).lineLimit(1).accessibilityIdentifier("contact-sample")
                }
                if comparesPress {
                    Text(verbatim: "\(fixture.actionCount)").accessibilityIdentifier("fixture-action-count")
                }
                Group {
                    if comparesPress {
                        PressComparisonLayout {
                            if usesAppleControl {
                                SwiftUI.Button(role: nil, action: fixture.appleSave) {
                                    SwiftUI.Text("Save sample")
                                        .frame(width: 144, height: 44)
                                        .contentShape(RoundedRectangle(cornerRadius: 8))
                                }
                                .buttonStyle(.plain)
                                .accessibilityIdentifier("save")
                            } else if let host = fixture.bundled {
                                MixerNativeView(host: host, onAction: fixture.bundledAction).sharedTheme(fixture.theme)
                            }
                        }
                    } else if let owner = fixture.owner {
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
                if capturePress || observeContact {
                    HeldPressProbe(capturePress: capturePress, actionCount: { fixture.actionCount },
                                   report: { heldSample = $0 },
                                   reportContact: observeContact ? { contactSample = $0 } : nil)
                        .allowsHitTesting(false)
                }
            }
            .preferredColorScheme(dark ? .dark : .light)
            .task { await fixture.start() }
        }
    }
}

private struct PressComparisonLayout<Control: View>: View {
    @ViewBuilder let control: () -> Control

    var body: some View {
        GeometryReader { geometry in
            let bounds = geometry.frame(in: .global)
            let row = CGRect(x: bounds.minX, y: bounds.midY - 22, width: bounds.width, height: 44)
            let blank = CGRect(x: row.minX, y: row.minY - 220, width: row.width, height: 108)
            let frames = [row, blank].flatMap { [$0.minX, $0.minY, $0.width, $0.height] }
            control()
                .frame(width: row.width, height: row.height)
                .position(x: geometry.size.width / 2, y: geometry.size.height / 2)
            Text("Comparison geometry")
                .accessibilityLabel(Text(verbatim: frames.map { String(Double($0)) }.joined(separator: " ")))
                .accessibilityIdentifier("press-comparison-geometry")
                .position(x: geometry.size.width / 2, y: geometry.size.height - 20)
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
        } else if arguments.contains("--held-press-probe") || arguments.contains("--compare-press") {
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
    @Published private(set) var actionCount = 0
    private var signed: SignedFixture?

    func start() async {
        guard status == "starting" else { return }
        do {
            let args = ProcessInfo.processInfo.arguments
            if args.contains("--held-press-probe") || args.contains("--compare-press") {
                try HeldPressProbe.discardPreviousCapture()
            }
            if args.contains("--compare-press") && args.contains("--apple-press-control") {
                status = "Apple control"
                return
            }
            if !args.contains("--platform-control") {
                theme = try MixerNativeTheme(configuration: FixtureTheme.configuration())
            }
            if args.contains("--signed-guest") {
                try await startGuest()
            } else {
                let document = args.contains("--compare-press")
                    ? MixerUI.UIDocument(revision: 1, root: Self.saveNode)
                    : Self.document(includeDisabledAncestor: args.contains("--ancestor-disabled-probe"))
                bundled = try MixerUIHost(document: document)
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

    func appleSave() {
        actionCount += 1
        result = "Apple action routed"
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

    private static let saveNode = UINode(id: "save", kind: .button, properties: ["label": .string("Save sample")],
                                         actions: [UIActionBinding(id: "sample.save", event: .activate)])

    private static func document(includeDisabledAncestor: Bool) -> MixerUI.UIDocument {
        var children = [
            UINode(id: "status", kind: .text, properties: ["text": .string("Ready")]),
            saveNode,
            UINode(id: "unavailable", kind: .button, properties: ["label": .string("Unavailable"), "disabled": .bool(true)],
                   actions: [UIActionBinding(id: "sample.disabled", event: .activate)])
        ]
        if includeDisabledAncestor {
            let child = UINode(id: "ancestor-disabled-save", kind: .button, properties: ["label": .string("Save draft")],
                               actions: [UIActionBinding(id: "sample.draft", event: .activate)])
            children.append(UINode(id: "disabled-group", kind: .vStack, properties: ["disabled": .bool(true)],
                                   children: [child]))
        }
        return MixerUI.UIDocument(revision: 1, root: UINode(id: "root", kind: .vStack, children: children))
    }
}
