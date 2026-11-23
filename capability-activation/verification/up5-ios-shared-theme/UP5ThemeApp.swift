import Foundation
import MixerApple
import MixerCapabilityActivation
import MixerUI
import SwiftUI

@main
struct UP5ThemeApp: App {
    @StateObject private var fixture = FixtureRun()
    @State private var dark = false

    var body: some Scene {
        WindowGroup {
            VStack {
                Text(fixture.status).accessibilityIdentifier("fixture-status")
                Text(fixture.result).accessibilityIdentifier("fixture-result")
                Group {
                    if let owner = fixture.owner {
                        MixerGuestScreen(presentation: owner.presentation).sharedTheme(fixture.theme)
                    } else if let host = fixture.bundled {
                        MixerNativeView(host: host, onAction: fixture.bundledAction).sharedTheme(fixture.theme)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)

                Button(dark ? "Use light" : "Use dark") { dark.toggle() }
                Button("Close fixture") { Task { await fixture.close() } }
            }
            .padding()
            .preferredColorScheme(dark ? .dark : .light)
            .task { await fixture.start() }
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
    private var signed: SignedFixture?

    func start() async {
        guard status == "starting" else { return }
        do {
            let args = ProcessInfo.processInfo.arguments
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
        result = action.actionID == "sample.save" ? "bundled action routed" : "wrong action"
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
        UINode(id: "unavailable", kind: .button, properties: ["label": .string("Unavailable"), "disabled": .bool(true)])
    ]))
}
