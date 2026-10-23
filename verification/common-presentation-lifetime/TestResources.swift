import Foundation

private final class PresentationTestResources {}
extension Bundle {
    static var module: Bundle { Bundle(for: PresentationTestResources.self) }
}
