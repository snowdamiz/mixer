import SwiftUI
import MixerApple
import AppFeatures
@main struct ObserverConsumerApp: App {
    @State private var host: MixerUIHost?
    @State private var failure: String?
    var body: some Scene {
        WindowGroup {
            Group {
                if let host { MixerNativeView(host: host, onAction: { _ in }) }
                else if let failure { Text(failure) }
                else { ProgressView() }
            }.task {
                do { host = try MixerUIHost(document: ProjectFeature.document(entries: [])) }
                catch { failure = String(describing: error) }
            }
        }
    }
}
