import SwiftUI

public struct DifferentialScreen: View {
    @State private var reversed = false
    @State private var draft = ""
    @State private var readback = "none"

    public init() {}

    public var body: some View {
        VStack {
            Button("Move rows") { reversed.toggle() }
            ForEach(reversed ? ["B", "A"] : ["A", "B"], id: \.self) { name in
                CounterRow(name: name)
            }
            Button("Read draft") { readback = draft }
            Text("Readback: \(readback)")
            TextField("Draft", text: $draft)
            Text("Draft: \(draft.isEmpty ? "empty" : draft)")
        }
    }
}

private struct CounterRow: View {
    let name: String
    @State private var count = 0

    var body: some View {
        VStack {
            Text("Row \(name): \(count)")
            Button("Increment \(name)") { count += 1 }
        }
    }
}
