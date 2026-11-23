import AppFeatures
import SwiftUI

@main
struct NativeProductApp: SwiftUI.App {
    var body: some SwiftUI.Scene {
        SwiftUI.WindowGroup {
            SwiftUI.Text(String(reflecting: type(of: SharedTitle.make("Shared feature"))))
        }
    }
}
