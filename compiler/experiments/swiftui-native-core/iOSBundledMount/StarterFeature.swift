import SwiftUI

public struct StarterFeature: View {
    @State private var count = 0
    @State private var title = ""

    public init() {}

    public var body: some View {
        VStack {
            Text("Bundled starter")
            Text("Count: \(count)")
            Button("Increment") { count += 1 }
            TextField("Title", text: $title)
            Text("Draft: \(title)")
        }
    }
}
