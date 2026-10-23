import Foundation
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation
import CMixerUITransport
import CMixerUIAndroidHostTest

func check(_ value: @autoclosure () -> Bool, _ message: String) {
    if !value() { fatalError("REVIEW_FAIL \(message)") }
}
func state() -> mxuit_snapshot {
    var value = mxuit_snapshot(); check(mxuit_inspect(&value) == 0, "inspect"); return value
}
func facadeRecord(_ facade: UInt64) -> CapabilityAndroidFacadeRecord {
    for slot in 0..<16 {
        if let result = CapabilityAndroidRegistry.shared.record(slot: slot, facade: facade) { return result }
    }
    fatalError("record absent")
}
final class WeakState: @unchecked Sendable {
    weak var reservation: CapabilityAttemptReservation?
    weak var binding: CapabilityGuestUIAndroidBinding?
    weak var resources: CapabilityGuestUIAndroidResources?
    let facade: UInt64
    init(_ reservation: CapabilityAttemptReservation, _ binding: CapabilityGuestUIAndroidBinding) {
        self.reservation = reservation; self.binding = binding; facade = binding.facade
        resources = facadeRecord(facade).resources
    }
}
@inline(never)
func abandonTransferred() async throws -> WeakState {
    let reservation = try CapabilityAttemptReservation.acquire()
    let prepared = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation: reservation)
    try prepared.transferToBinding()
    return WeakState(reservation, prepared.binding)
}
@inline(never)
func quarantineFailedRetire() async throws -> WeakState {
    let reservation = try CapabilityAttemptReservation.acquire()
    let prepared = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation: reservation)
    try prepared.transferToBinding()
    let weak = WeakState(reservation, prepared.binding)
    mxish_fail_retire(prepared.binding.facade)
    reservation.beginClosing()
    guard case .quarantined = await prepared.binding.finishFinalClose(using: nil) else { fatalError("expected quarantine") }
    return weak
}
func observeDrop(_ weak: WeakState, abandoned: Bool) async {
    for _ in 0..<100 { await Task.yield() }
    check(weak.binding == nil, "binding shell actually dropped")
    check(weak.reservation != nil, "exact reservation chain retained after drop")
    check(weak.resources != nil, "actual resource retained after drop")
    check(weak.reservation?.isQuarantined == true, "outer quarantine")
    check(CapabilityAttemptReservation.occupiedSlots == 1, "outer capacity pinned")
    check(mxish_destructors() == 0, "no premature resource destructor")
    let record = facadeRecord(weak.facade)
    let scalar = record.withLock { ($0.quarantined, $0.closing, $0.lookupEnabled, $0.endpoint) }
    print("DROP resourceAlive=1 reservationAlive=1 bindingAlive=0 recordQuarantined=\(scalar.0) closing=\(scalar.1) lookup=\(scalar.2) endpoint=\(scalar.3)")
    if abandoned {
        check(!scalar.0 && !scalar.1 && scalar.2, "reproduced transferred abandonment record gap")
        var endpoint = mxuit_owner_snapshot()
        check(mxuit_inspect_owner(scalar.3, &endpoint) == 0, "abandoned endpoint exists")
        print("ABANDONMENT_FINDING endpointClosing=\(endpoint.closing) retirement=\(endpoint.retirement_done) requests=\(state().requests)")
    } else {
        check(scalar.0 && scalar.1, "failed retire registry quarantine")
        check(mxish_live_allocations() == 3, "uncertain actual native allocations retained")
    }
    var held: [CapabilityAttemptReservation] = []
    for _ in 0..<15 { held.append(try! CapabilityAttemptReservation.acquire()) }
    do { _ = try CapabilityAttemptReservation.acquire(); fatalError("seventeenth admitted") } catch {}
    for reservation in held { reservation.beginClosing() }
    check(CapabilityAttemptReservation.occupiedSlots == 1, "uncertain slot remains pinned after other owners close")
}
func heldDestructor() async throws {
    let reservation = try CapabilityAttemptReservation.acquire()
    let prepared = try await CapabilityGuestUIAndroidBinding.prepareHost(reservation: reservation)
    try prepared.transferToBinding()
    let weak = WeakState(reservation, prepared.binding)
    let facade = prepared.binding.facade
    check(mxish_set_hold(7, facade) == 0, "destructor hold installed")
    reservation.beginClosing()
    let finish = Task { await prepared.binding.finishFinalClose(using: nil) }
    check(mxish_wait_hold() == 0, "actual destructor entered")
    let record = facadeRecord(facade)
    check(record.withLock { $0.reserved && $0.facadeReclaimed && $0.facade == facade && !$0.lookupEnabled && $0.resources == nil }, "Swift tombstone remains through destructor")
    check(!reservation.isReleased && CapabilityAttemptReservation.occupiedSlots == 1, "capacity remains through destructor")
    check(prepared.binding.finalStatus == .pending && mxish_destructors() == 0, "actual destructor return precedes final receipt")
    check(state().occupied == 0 && state().occupied_facades == 0, "C returned before Swift destructor")
    var held: [CapabilityAttemptReservation] = []
    for _ in 0..<15 { held.append(try CapabilityAttemptReservation.acquire()) }
    do { _ = try CapabilityAttemptReservation.acquire(); fatalError("seventeenth while destructor held") } catch {}
    mxish_release_hold()
    guard case .finished = await finish.value else { fatalError("final completion") }
    check(weak.resources == nil && reservation.isReleased && mxish_destructors() == 1, "destructor actually returned")
    check(record.withLock { !$0.reserved && $0.facade == 0 }, "Swift cell/reservation returned after destructor")
    let replacement = try CapabilityAttemptReservation.acquire(); replacement.beginClosing()
    for reservation in held { reservation.beginClosing() }
    check(CapabilityAttemptReservation.occupiedSlots == 0, "capacity recovers")
}
@main struct ReviewProbes {
    static func main() async throws {
        check(mxish_start() == 0, "real platform")
        switch CommandLine.arguments[1] {
        case "drop-failed-retire": await observeDrop(try await quarantineFailedRetire(), abandoned: false)
        case "drop-transferred": await observeDrop(try await abandonTransferred(), abandoned: true)
        case "destructor-contention": try await heldDestructor()
        default: fatalError("unknown probe")
        }
        print("REVIEW_PROBE_PASS \(CommandLine.arguments[1])")
    }
}
