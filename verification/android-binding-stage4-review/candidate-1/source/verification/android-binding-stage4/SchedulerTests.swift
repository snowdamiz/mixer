import Foundation
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation
import CMixerUITransport
import CMixerUIAndroidHostTest
import CMixerUIAndroidSchedulerProbe

private func check(_ value: @autoclosure () -> Bool, _ message: String) {
    if !value() { mxish_scheduler_release(); fatalError("SCHEDULER_FAIL \(message)") }
}
@main struct SchedulerTests {
    static func main() async throws {
        check(mxish_scheduler_install_status() == 0 && mxish_start() == 0, "fixed runtime hook/install")
        defer { mxish_scheduler_release(); check(mxish_scheduler_unhook() == 0, "unhook clean") }
        let reservation = try CapabilityAttemptReservation.acquire()
        let prepared = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation: reservation)
        try prepared.transferToBinding(); let binding = prepared.binding
        let holding = CommandLine.arguments.dropFirst().first == "hold"
        var endpoint: UInt64 = 0
        for i in 0..<16 {
            if let r = CapabilityAndroidRegistry.shared.record(slot: i, facade: binding.facade) { endpoint = r.withLock { $0.endpoint } }
        }
        check(endpoint > 0, "actual acquired endpoint")
        if holding { check(mxish_scheduler_arm(endpoint) == 0, "arm exact RETIRE endpoint") }
        reservation.beginClosing()
        let final = Task { await binding.finishFinalClose(using: nil) }
        if holding {
            check(mxish_scheduler_wait() == 0, "captured actual runtime resume job")
            check(mxish_scheduler_captured_owner() == endpoint && mxish_scheduler_captured_waiter() > 0 && mxish_scheduler_captured_jobs() == 1, "unambiguous exact completion context")
            let deadline = ContinuousClock.now + .seconds(5)
            var state = mxuit_owner_snapshot()
            while true {
                check(mxuit_inspect_owner(endpoint, &state) == 0, "endpoint pinned")
                if state.retirement_done == 1 { break }
                check(ContinuousClock.now < deadline, "actual C RETIRE return"); await Task.yield()
            }
            check(state.consumer_joined == 0 && !reservation.isReleased && binding.finalStatus == .pending,
                  "real Task.value cannot finish while real successful-RETIRE resume job parked")
            check(mxish_destructors() == 0, "no resource destruction before actual Task return")
            print("SCHEDULER_HELD owner=\(endpoint) waiter=\(mxish_scheduler_captured_waiter()) retirement_done=1 consumer_joined=0 destructor=0")
            mxish_scheduler_release()
        }
        guard case .finished(let receipt) = await final.value else { fatalError("not final") }
        check(receipt.lastLifetime.taskJoin == .joined && reservation.isReleased && mxish_destructors() == 1,
              "original exact job forwarded and actual Task.value joined")
        print("SCHEDULER_PASS \(holding ? "held" : "no-hold") actual_task_joined=1 destructor=1")
    }
}
