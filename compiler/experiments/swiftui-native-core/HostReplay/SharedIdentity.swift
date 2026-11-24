import SwiftUI

public struct ExplicitCounter: View {
    let title: String
    let onIncrement: () -> Void
    @State private var count = 0

    public init(_ title: String, onIncrement: @escaping () -> Void = {}) {
        self.title = title
        self.onIncrement = onIncrement
    }

    public var body: some View {
        VStack {
            Text("\(title) \(count)")
            Button("Increment \(title)") {
                count += 1
                onIncrement()
            }
        }
    }
}

public struct ExplicitSiblings: View {
    let swapped: Bool
    let firstKey: Int
    let inner: Int
    let outer: String

    public init(swapped: Bool = false, firstKey: Int = 1, inner: Int = 7, outer: String = "outer") {
        self.swapped = swapped
        self.firstKey = firstKey
        self.inner = inner
        self.outer = outer
    }

    public var body: some View {
        VStack {
            ExplicitCounter(swapped ? "B" : "A").id(swapped ? 2 : firstKey)
            Text("Between")
            ExplicitCounter(swapped ? "A" : "B").id(swapped ? firstKey : 2)
            ExplicitCounter("String").id("1")
            ExplicitCounter("Nested").id(inner).id(outer)
        }
    }
}

public struct ExplicitRows: View {
    let rows: [Row]
    let firstKey: Int
    let loopKey: Int

    public init(_ rows: [Row], firstKey: Int = 1, loopKey: Int = 1) {
        self.rows = rows
        self.firstKey = firstKey
        self.loopKey = loopKey
    }

    public var body: some View {
        VStack {
            ForEach(rows, id: \.id) { row in
                ExplicitCounter(row.title).id(row.title == "R1" ? firstKey : 1)
            }.id(loopKey)
        }
    }
}

public struct ExplicitScopes: View {
    let firstBranch: Bool
    let showOptional: Bool
    @State private var total = 0

    public init(firstBranch: Bool = true, showOptional: Bool = true) {
        self.firstBranch = firstBranch
        self.showOptional = showOptional
    }

    public var body: some View {
        VStack {
            Text("Parent \(total)")
            if firstBranch {
                ExplicitCounter("Branch") { total += 1 }.id(1)
            } else {
                ExplicitCounter("Branch") { total += 1 }.id(1)
            }
            if showOptional {
                ExplicitCounter("Optional").id(1)
            }
            IdentityScope(title: "Left")
            IdentityScope(title: "Right")
        }
    }
}

private struct IdentityScope: View {
    let title: String

    var body: some View { ExplicitCounter(title).id(1) }
}

public func erasedCounter(_ title: String, alternate: Bool) -> AnyView {
    let counter = ExplicitCounter(title).id(1)
    if alternate {
        return AnyView(erasing: counter.disabled(false))
    }
    return AnyView(counter)
}
