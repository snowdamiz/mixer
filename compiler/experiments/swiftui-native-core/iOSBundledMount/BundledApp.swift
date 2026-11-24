import SwiftUI
import MixerApple
import UP5StarterFeature

@main
struct BundledApp: App {
    var body: some Scene {
        WindowGroup { StarterShell() }
    }
}

private struct StarterShell: View {
    @State private var mount: MixerBundledFeatureMount<StarterFeature>? = try! MixerBundledFeatureMount { StarterFeature() }

    var body: some View {
        VStack {
            if let mount {
                mount.view()
                MountStatus(mount: mount)
                Button("Close feature") {
                    mount.cancel()
                    self.mount = nil
                }
            } else {
                Text("Feature closed")
            }
        }
        .padding()
    }
}

private struct MountStatus: View {
    @ObservedObject var mount: MixerBundledFeatureMount<StarterFeature>

    var body: some View {
        Text(mount.status == .ready ? "Feature ready" : "Feature starting")
            .accessibilityIdentifier("mount-status")
    }
}
