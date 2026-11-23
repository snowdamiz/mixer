import SwiftUI

public struct Row {
    let id: Int
    let title: String

    public init(_ id: Int, _ title: String) {
        self.id = id
        self.title = title
    }
}

public struct Screen: View {
    let rows: [Row]
    let showRows: Bool
    let markedFirst: Bool
    let retain: (Int, Binding<Bool>) -> Void
    let onActivate: () -> Void

    public init(
        rows: [Row], showRows: Bool = true, markedFirst: Bool = false,
        retain: @escaping (Int, Binding<Bool>) -> Void = { _, _ in },
        onActivate: @escaping () -> Void = {}
    ) {
        self.rows = rows
        self.showRows = showRows
        self.markedFirst = markedFirst
        self.retain = retain
        self.onActivate = onActivate
    }

    public var body: some View {
        VStack {
            Text("Rows")
            if showRows {
                ForEach(rows, id: \.id) { row in
                    CounterRow(row: row, markedFirst: markedFirst, retain: retain, onActivate: onActivate)
                }
            }
        }
    }
}

private struct CounterRow: View {
    let row: Row
    let markedFirst: Bool
    let retain: (Int, Binding<Bool>) -> Void
    let onActivate: () -> Void
    @State private var count = 0
    @State private var marked = false

    var body: some View {
        let mark = $marked
        let _ = retain(row.id, mark)
        VStack {
            if markedFirst {
                Text("\(row.title) \(marked) \(count)")
            } else {
                Text("\(row.title) \(count) \(marked)")
            }
            Button("Increment \(row.title)") {
                count += 1
                mark.wrappedValue.toggle()
                onActivate()
            }
        }
    }
}
