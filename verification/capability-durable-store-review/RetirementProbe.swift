import Foundation
import Darwin
@testable import MixerCapabilityActivation

private final class BlockingDestructor: @unchecked Sendable {
    let entered: DispatchSemaphore
    let release: DispatchSemaphore
    init(_ entered: DispatchSemaphore, _ release: DispatchSemaphore) {
        self.entered = entered; self.release = release
    }
    deinit {
        entered.signal()
        precondition(release.wait(timeout: .now() + 10) == .success)
    }
}
private final class EmptyOwner: @unchecked Sendable {}

@main struct IndependentRetirementProbe {
    static func main() throws {
        if CommandLine.arguments.dropFirst().first == "replacement" { try adapterReplacement(); return }
        let blockStore = CommandLine.arguments.dropFirst().first != "adapter-first"
        let reservations = try (0..<16).map { _ in try CapabilityAttemptReservation.acquire() }
        let owner = reservations[0]
        let store = try owner.issueStoreAdmission().claimStore()
        let adapter = try owner.reserveAdapterGroup()
        let entered = DispatchSemaphore(value: 0), release = DispatchSemaphore(value: 0)
        let storeReturned = DispatchSemaphore(value: 0)
        if blockStore {
            try store.retainOwner(BlockingDestructor(entered, release)); try adapter.retainOwner(EmptyOwner())
        } else {
            try adapter.retainOwner(BlockingDestructor(entered, release)); try store.retainOwner(EmptyOwner())
        }
        owner.beginClosing()
        DispatchQueue.global().async {
            if blockStore { store.retire() } else { adapter.retire() }
            storeReturned.signal()
        }
        precondition(entered.wait(timeout: .now() + 10) == .success)
        if blockStore { adapter.retire() } else { store.retire() }
        let countBeforeRelease = CapabilityAttemptReservation.occupiedSlots
        let releasedBeforeDestructor = owner.isReleased
        let extra = try? CapabilityAttemptReservation.acquire()
        print("held_store_destructor occupied=\(countBeforeRelease) released=\(releasedBeforeDestructor) extra_admitted=\(extra != nil)")
        release.signal()
        precondition(storeReturned.wait(timeout: .now() + 10) == .success)
        reservations.forEach { $0.beginClosing() }; extra?.beginClosing()
        guard countBeforeRelease == 16, !releasedBeforeDestructor, extra == nil else {
            print("FAIL premature outer-pool release")
            exit(1)
        }
        precondition(CapabilityAttemptReservation.occupiedSlots == 0)
        print("concurrent retained-owner destruction is included in outer retirement")
    }
    private static func adapterReplacement() throws {
        let owner = try CapabilityAttemptReservation.acquire(), adapter = try owner.reserveAdapterGroup()
        let entered = DispatchSemaphore(value: 0), release = DispatchSemaphore(value: 0), returned = DispatchSemaphore(value: 0)
        try adapter.retainOwner(BlockingDestructor(entered, release))
        DispatchQueue.global().async { adapter.retire(); returned.signal() }
        precondition(entered.wait(timeout: .now() + 10) == .success)
        let replacement = try? owner.reserveAdapterGroup()
        owner.beginClosing()
        let released = owner.isReleased
        release.signal(); precondition(returned.wait(timeout: .now() + 10) == .success)
        replacement?.retire()
        guard replacement == nil, !released else { print("FAIL replacement admitted during retained destructor"); exit(1) }
        precondition(owner.isReleased && CapabilityAttemptReservation.occupiedSlots == 0)
        print("adapter replacement waits for retained-owner destruction")
    }
}
