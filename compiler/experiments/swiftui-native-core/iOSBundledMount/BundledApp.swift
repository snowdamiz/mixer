import SwiftUI
import UP5StarterFeature
@testable import MixerApple

@main
struct BundledApp: App {
    var body: some Scene {
        WindowGroup { StarterShell() }
    }
}

private struct StarterShell: View {
    @StateObject private var fixture = StarterFixture()
    @State private var showsFeature = true

    var body: some View {
        VStack {
            if showsFeature {
                fixture.mount.view()
                Button("Hold next display") { fixture.holdNext = true }
                Button("Release display") { fixture.releaseDisplay() }
                    .disabled(fixture.heldDisplay == nil)
                Button("Close feature") { showsFeature = false }
                if fixture.heldDisplay != nil { Text("Display held") }
            }
            MountStatus(mount: fixture.mount)
        }
        .padding()
    }
}

@MainActor
private final class StarterFixture: ObservableObject {
    let mount: MixerBundledFeatureMount<StarterFeature>
    @Published private(set) var heldDisplay: UUID?
    var holdNext = false

    init() {
        mount = try! MixerBundledFeatureMount { StarterFeature() }
        mount.host.holdNativeDisplay = { [weak self] id in
            guard let self, holdNext else { return false }
            if heldDisplay != id { heldDisplay = id }
            return true
        }
    }

    func releaseDisplay() {
        guard let heldDisplay else { return }
        holdNext = false
        self.heldDisplay = nil
        mount.host.completeFeatureDisplay(heldDisplay)
    }
}

private struct MountStatus: View {
    @ObservedObject var mount: MixerBundledFeatureMount<StarterFeature>

    var body: some View {
        Text(label).accessibilityIdentifier("mount-status")
    }

    private var label: String {
        switch mount.status {
        case .starting: "Feature starting"
        case .ready: "Feature ready"
        case .failed: "Feature failed"
        case .closed: "Feature closed"
        }
    }
}
