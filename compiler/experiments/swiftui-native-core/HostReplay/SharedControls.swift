import SwiftUI

public struct EditorScreen: View {
    let rows: [Row]
    let retain: (Int, Binding<String>, Binding<Bool>) -> Void

    public init(rows: [Row], retain: @escaping (Int, Binding<String>, Binding<Bool>) -> Void = { _, _, _ in }) {
        self.rows = rows
        self.retain = retain
    }

    public var body: some View {
        List {
            Section("Editors") {
                ForEach(rows, id: \.id) { row in
                    EditorRow(row: row, retain: retain)
                }
            }
            Section {
                HStack { Text("Default layout") }
            }
            Section {
                HStack(alignment: .bottom, spacing: 0) { Text("Footer row") }
            } header: {
                Text("Details")
            }
        }
    }
}

private struct EditorRow: View {
    let row: Row
    let retain: (Int, Binding<String>, Binding<Bool>) -> Void
    @State private var name = ""
    @State private var enabled = false

    var body: some View {
        let _ = retain(row.id, $name, $enabled)
        RowControls(title: row.title, name: $name, enabled: $enabled)
    }
}

private struct RowControls: View {
    let title: String
    @Binding var name: String
    @Binding var enabled: Bool

    var body: some View {
        HStack(alignment: .top, spacing: 12.5) {
            SwiftUI.TextField("Name \(title)", text: $name)
            SwiftUI.Toggle("Enable \(title)", isOn: $enabled)
        }
    }
}
