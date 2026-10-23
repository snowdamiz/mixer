import SwiftUI

// Hidden reference strings preserve foreground pixels while exercising native
// SwiftUI layout. fixedSize prevents the background proposal from truncating them.
@MainActor
public struct FontLineBoxSampler: View {
    public init() {}
    public var body: some View {
        ZStack {
            sample("body", font: .body, lines: 1)
            sample("body", font: .body, lines: 2)
            sample("headline", font: .headline, lines: 1)
            sample("headline", font: .headline, lines: 2)
            sample("title", font: .title, lines: 1)
            sample("title", font: .title, lines: 2)
            sample("caption", font: .caption, lines: 1)
            sample("caption", font: .caption, lines: 2)
        }
        .hidden()
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
    private func sample(_ role: String, font: Font, lines: Int) -> some View {
        Text(lines == 1 ? "Ag" : "Ag\nAg")
            .font(font)
            .lineLimit(nil)
            .fixedSize(horizontal: true, vertical: true)
            .background(LineBoxSizeProbe(id: role + (lines == 1 ? ".one" : ".two")))
    }
}

@MainActor
private struct LineBoxSizeProbe: View {
    let id: String
    var body: some View {
        GeometryReader { geometry in
            Color.clear
                .onAppear { record(geometry.size) }
                .onChange(of: geometry.size) { _, new in record(new) }
        }
    }
    private func record(_ size: CGSize) {
        FontProfileEvidence.lineBoxes[id] = ["width": size.width, "height": size.height]
    }
}
