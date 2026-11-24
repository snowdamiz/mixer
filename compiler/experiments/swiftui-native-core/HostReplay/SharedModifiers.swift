import SwiftUI

public struct ModifierScreen: View {
    let rows: [Row]
    let locked: Bool
    let saveLabel: String

    public init(rows: [Row], locked: Bool, saveLabel: String) {
        self.rows = rows
        self.locked = locked
        self.saveLabel = saveLabel
    }

    public var body: some View {
        VStack {
            ForEach(rows, id: \.id) { row in
                ModifierRow(row: row, saveLabel: saveLabel).disabled(false).id("editor")
            }
        }
        .disabled(locked)
    }
}

private struct ModifierRow: View {
    let row: Row
    let saveLabel: String
    @State private var saves = 0
    @State private var name = ""
    @State private var flag = false

    var body: some View {
        HStack {
            Text("\(row.title) \(saves)").accessibilityLabel("Save count")
            Button("Save \(row.title)") { saves += 1 }
                .disabled(false)
                .id("save")
                .accessibilityLabel(saveLabel)
                .accessibilityHint("Records the current edit")
            TextField("Name", text: $name)
                .accessibilityHint("Enter the full name")
                .disabled(false)
            Toggle("Flag", isOn: $flag)
                .disabled(false)
                .accessibilityLabel("Flag for review")
        }
    }
}
