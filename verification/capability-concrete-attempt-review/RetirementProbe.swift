import Foundation
import Dispatch
@testable import MixerCapabilityActivation

private struct Failed: Error { let reason: String }
private func need(_ good: @autoclosure () -> Bool, _ reason: String) throws {
    if !good() { throw Failed(reason: reason) }
}
private func rejects(_ operation: () throws -> Void) throws {
    var rejected = false; do { try operation() } catch { rejected = true }
    try need(rejected, "Expected bounded admission rejection")
}
private final class Flag: @unchecked Sendable {
    private let lock = NSLock(); private var v = false
    func set() { lock.lock(); v = true; lock.unlock() }
    var value: Bool { lock.lock(); defer { lock.unlock() }; return v }
}
@main struct Review {
    static func main() async throws {
        let before = CapabilityAttemptReservation.occupiedSlots
        let orders = [[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]]
        for order in orders {
            let owner = try CapabilityAttemptReservation.acquire()
            let token = CapabilityConcreteRetirement(obligation: try owner.reserveAdapterGroup())
            token.expectGroup(); try token.beginMethod(); owner.beginClosing()
            for (index,event) in order.enumerated() {
                switch event { case 0: token.recordRetired(); case 1: token.setupDidReturn(); default: token.methodDidReturn() }
                try need(token.completed == (index == 2), "Retired before every independent condition")
                try need(owner.isReleased == (index == 2), "Outer slot released before join")
            }
            let success = await token.wait(), duplicate = await token.wait()
            try need(success && !duplicate, "Retirement wait is not one-shot")
        }
        for _ in 0..<128 {
            let owner = try CapabilityAttemptReservation.acquire()
            let token = CapabilityConcreteRetirement(obligation: try owner.reserveAdapterGroup())
            token.expectGroup(); try token.beginMethod()
            await withTaskGroup(of: Void.self) { group in
                group.addTask { for _ in 0..<8 { token.recordRetired() } }
                group.addTask { for _ in 0..<8 { token.setupDidReturn() } }
                group.addTask { token.methodDidReturn() }
            }
            try need(token.completed, "Concurrent actual join lost")
            let replacement = try owner.reserveAdapterGroup(); replacement.retire()
            owner.beginClosing(); try need(owner.isReleased, "Slot not released after joined retirement")
        }
        for beforeRegistration in [false,true] {
            let owner = try CapabilityAttemptReservation.acquire()
            let token = CapabilityConcreteRetirement(obligation: try owner.reserveAdapterGroup())
            token.expectGroup(); owner.beginClosing()
            if beforeRegistration { token.cancelWait() }
            let waiting = Task { await token.wait() }
            if !beforeRegistration { waiting.cancel() }
            let result = await waiting.value
            try need(!result && !token.completed && !owner.isReleased, "Wait cancellation fabricated actual exit")
            token.setupDidReturn(); try need(!token.completed, "Setup alone fabricated bridge exit")
            token.recordRetired(); try need(token.completed && owner.isReleased, "Cancelled wait prevented actual retirement")
        }
        for _ in 0..<128 {
            let owner = try CapabilityAttemptReservation.acquire()
            let token = CapabilityConcreteRetirement(obligation: try owner.reserveAdapterGroup())
            token.expectGroup()
            let waiting = Task { await token.wait() }
            await withTaskGroup(of: Void.self) { group in
                group.addTask { token.setupDidReturn(); token.recordRetired() }
                group.addTask { waiting.cancel() }
            }
            _ = await waiting.value
            try need(token.completed, "Cancelled wait/finish race lost actual retirement")
            let replacement = try owner.reserveAdapterGroup(); replacement.retire(); owner.beginClosing()
            try need(owner.isReleased, "Cancelled race leaked actual completed obligation")
        }
        try need(CapabilityAttemptReservation.occupiedSlots == before, "Review leaked capacity")
        print("PASS 6 join permutations +128 concurrent joins +2 cancelled-wait orders +128 cancel/finish races; no counter reset")
    }
}
