import Foundation

private final class ColdStartCIResources {}
extension Bundle {
    static var module: Bundle { Bundle(for: ColdStartCIResources.self) }
}
final class CIAsyncReturnFlag: @unchecked Sendable {
    private let lock = NSLock()
    private var returned = false
    var didReturn: Bool { lock.lock(); defer { lock.unlock() }; return returned }
    func record() { lock.lock(); returned = true; lock.unlock() }
}
