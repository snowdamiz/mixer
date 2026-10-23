import Foundation

// The exact copied test fixture helper uses Bundle.module. This standalone
// verification app packages those immutable JSON fixtures in its main bundle.
extension Bundle {
    static var module: Bundle { .main }
}
