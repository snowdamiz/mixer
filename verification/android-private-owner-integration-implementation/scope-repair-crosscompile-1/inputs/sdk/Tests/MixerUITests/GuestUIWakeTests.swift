import Foundation
import Testing
@_spi(GuestUIV1) @testable import MixerGuest

@Test func guestUIWakeCoalescesAndPreservesRetirementBeforeFinished() async throws {
    let exchange = try GuestUIExchangeV1(generation: 1)
    let wake = exchange.deliveryWake, reader = try wake.takeConsumer()
    #expect(throws: GuestUIControlRejectionV1.consumerAlreadyIssued) { try wake.takeConsumer() }
    for _ in 0..<10_000 { wake.signal() }
    wake.finish()
    #expect(try await reader.next())
    #expect(try await !reader.next())
    wake.signal(); wake.finish()
    #expect(try await !reader.next())
}

@Test func guestUIWakeRejectsExtraWaiterAndCancellationDoesNotLoseIt() async throws {
    let exchange = try GuestUIExchangeV1(generation: 1)
    let wake = exchange.deliveryWake, reader = try wake.takeConsumer()
    let waiter = Task { try await reader.next() }
    defer { wake.finish() }
    for _ in 0..<10_000 {
        if wake.hasWaitingConsumer { break }
        await Task.yield()
    }
    #expect(wake.hasWaitingConsumer)
    await #expect(throws: GuestUIControlRejectionV1.readerBusy) { try await reader.next() }
    waiter.cancel()
    #expect(wake.hasWaitingConsumer)
    wake.signal()
    #expect(try await waiter.value)
    wake.finish()
    #expect(try await !reader.next())
}

@Test func guestUIStopSignalsFinalDeliveryButDoesNotFinishCoordinatorChannel() async throws {
    let exchange = try GuestUIExchangeV1(generation: 1)
    let delivery = try exchange.deliveryWake.takeConsumer()
    let control = try exchange.coordinatorWake.takeConsumer()
    exchange.stop(.closed)
    #expect(try await delivery.next())
    #expect(try await !delivery.next())
    #expect(try await control.next())
    exchange.coordinatorWake.signal()
    #expect(try await control.next())
    exchange.coordinatorWake.finish()
    #expect(try await !control.next())
}
