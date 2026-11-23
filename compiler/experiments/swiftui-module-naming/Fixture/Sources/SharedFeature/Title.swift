import SwiftUI

public enum SharedTitle {
    public static func make(_ title: String) -> SwiftUI.Text {
        SwiftUI.Text(title)
    }
}
