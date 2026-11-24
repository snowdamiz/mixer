import SwiftUI
import MixerApple
import MixerSwiftUI
import GC4AppleFeature
import GC4MixerFeature

@main
struct DifferentialApp: App {
    private let useMixer = ProcessInfo.processInfo.arguments.contains("--mixer")
    private let testErasure = ProcessInfo.processInfo.arguments.contains("--erased")

    var body: some Scene {
        WindowGroup {
            Group {
                if testErasure {
                    if useMixer {
                        BundledScreen { GC4MixerFeature.ErasedLifetimeScreen() }
                    } else {
                        GC4AppleFeature.ErasedLifetimeScreen()
                    }
                } else if useMixer {
                    BundledScreen { GC4MixerFeature.DifferentialScreen() }
                } else {
                    GC4AppleFeature.DifferentialScreen()
                }
            }
            .padding()
        }
    }
}

private struct BundledScreen<Content: MixerSwiftUI.View>: SwiftUI.View {
    @StateObject private var mount: MixerBundledFeatureMount<Content>

    init(content: @escaping @MainActor () -> Content) {
        _mount = StateObject(wrappedValue: try! MixerBundledFeatureMount(content: content))
    }

    var body: some SwiftUI.View {
        mount.view()
    }
}
