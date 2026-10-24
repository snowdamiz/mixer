import Foundation
private final class MilestoneCIResources {}
extension Bundle { static var module: Bundle { Bundle(for: MilestoneCIResources.self) } }
final class MilestoneCIReturnFlag: @unchecked Sendable {
    private let lock = NSLock(); private var returned = false
    var didReturn: Bool { lock.lock(); defer { lock.unlock() }; return returned }
    func record() { lock.lock(); returned = true; lock.unlock() }
}
