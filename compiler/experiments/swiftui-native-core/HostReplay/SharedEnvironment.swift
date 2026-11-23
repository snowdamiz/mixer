import SwiftUI

public struct EnvironmentScreen: View {
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.layoutDirection) private var layoutDirection
    @State private var recorded = "No reading"
    private let onRecord: () -> Void

    public init(onRecord: @escaping () -> Void = {}) {
        self.onRecord = onRecord
    }

    public var summary: String {
        let scheme = colorScheme == .dark ? "Dark" : "Light"
        let direction = layoutDirection == .rightToLeft ? "RTL" : "LTR"
        return "\(scheme)/\(direction)"
    }

    public var body: some View {
        VStack {
            Text(summary)
            Text(recorded)
            Button("Record environment") {
                let before = summary
                onRecord()
                recorded = "\(before) -> \(summary)"
            }
        }
    }
}
