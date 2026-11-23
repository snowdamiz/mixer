import TitleSupport

public struct Text {
    public let value: String

    public init(_ title: String) {
        value = prepareTitle(title)
    }
}
