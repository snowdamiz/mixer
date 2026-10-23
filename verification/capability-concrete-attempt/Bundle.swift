import Foundation

// Direct host test-bundle resource lookup. No package graph is generated; the
// retained immutable transition test resource bundle contains the same fixtures.
extension Bundle {
    static let module = Bundle(path: ProcessInfo.processInfo.environment["MIXER_CONCRETE_TEST_BUNDLE"]!)!
}
