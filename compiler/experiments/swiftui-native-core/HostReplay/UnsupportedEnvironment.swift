import SwiftUI

struct LocaleView: View {
    @Environment(\.locale) private var locale // refused

    var body: some View { Text("Locale") }
}

func overrideColorScheme() -> some View {
    Text("Dark").environment(\.colorScheme, .dark) // refused
}

func overrideLayoutDirection() -> some View {
    Text("RTL").environment(\.layoutDirection, .rightToLeft) // refused
}

func preferDarkAppearance() -> some View {
    Text("Dark").preferredColorScheme(.dark) // refused
}
