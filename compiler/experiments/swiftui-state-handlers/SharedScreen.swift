#if APPLE_SWIFTUI
import SwiftUI
#endif

struct ProbeScreen: View {
    @State private var first = 1
    @State private var second = 10
    @State private var readSecondFirst = false
    @State private var moved = false
    @State private var showBranch = true

    private let hideBranchForPresentation: Bool

    init(hideBranchForPresentation: Bool = false) {
        self.hideBranchForPresentation = hideBranchForPresentation
    }

    private var reading: String {
        if !showBranch { return "Values \(second)" }
        if readSecondFirst {
            let a = second
            let b = first
            return "Values \(a) / \(b)"
        }
        let a = first
        let b = second
        return "Values \(a) / \(b)"
    }

    var body: some View {
        VStack {
            Text(reading)
            Button("Bump first") { first += 1 }
            Button("Reverse reads") { readSecondFirst.toggle() }
            CapturedWriter(value: $second)
            Button("Move rows") { moved.toggle() }
            Button("Toggle branch") { showBranch.toggle() }
            ForEach(moved ? [2, 1] : [1, 2], id: \.self) { key in
                ProbeRow(key: key)
            }
            if showBranch && !hideBranchForPresentation {
                ProbeBranch()
            } else {
                Text("Branch hidden")
            }
        }
    }
}

private struct CapturedWriter: View {
    @Binding var value: Int

    var body: some View {
        let binding = $value
        Button("Write captured binding") { binding.wrappedValue += 10 }
    }
}

private struct ProbeRow: View {
    let key: Int
    @State private var count = 0

    var body: some View {
        VStack {
            Text("Row \(key) = \(count)")
            Button("Bump row \(key)") { count += 1 }
        }
    }
}

private struct ProbeBranch: View {
    @State private var count = 0

    var body: some View {
        VStack {
            Text("Branch = \(count)")
            Button("Bump branch") { count += 1 }
        }
    }
}
