import Foundation
extension Bundle {
    static let module = Bundle(path: ProcessInfo.processInfo.environment["MIXER_COLD_START_TEST_BUNDLE"]!)!
}
