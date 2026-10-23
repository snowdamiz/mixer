@testable import MixerCapabilityActivation

func forge() throws {
    let id = CapabilityPresentationLifetimeID(1)
    _ = CapabilityPresentationJoinPermit(id)
    _ = CapabilityPresentationLifetimeReceipt(apple: 1, lifetime: id, joined: .joined)
    _ = CapabilityFacadeCleanupReceipt(facade: 1, cleanupSerial: 1, finalEntrySerial: 1)
}
