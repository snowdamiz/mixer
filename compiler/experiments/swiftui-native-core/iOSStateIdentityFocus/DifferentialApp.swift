import SwiftUI
import MixerApple
import GC4AppleFeature
import GC4MixerFeature

@main
struct DifferentialApp: App {
    private let useMixer = ProcessInfo.processInfo.arguments.contains("--mixer")

    var body: some Scene {
        WindowGroup {
            Group {
                if useMixer {
                    BundledScreen()
                } else {
                    GC4AppleFeature.DifferentialScreen()
                }
            }
            .padding()
        }
    }
}

private struct BundledScreen: View {
    @StateObject private var mount = try! MixerBundledFeatureMount {
        GC4MixerFeature.DifferentialScreen()
    }

    var body: some View {
        mount.view()
    }
}
