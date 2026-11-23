import SharedFeature
import SwiftUI

@main
struct AppleShell: SwiftUI.App {
    var body: some SwiftUI.Scene {
        SwiftUI.WindowGroup {
            SwiftUI.Text(SharedTitle.make("S1").value)
        }
    }
}
