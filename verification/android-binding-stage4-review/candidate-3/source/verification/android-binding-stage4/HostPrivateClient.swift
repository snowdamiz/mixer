@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

func cannotExtract(_ installation: CapabilityAndroidHostInstallation) {
    _ = installation.lifetime
    _ = installation.permit
    _ = installation.finishAndroidHost
}
func cannotCrossTypes(_ host: CapabilityAndroidHostInstallation,
                      _ status: CapabilityAndroidHostJoinStatus,
                      _ receipt: CapabilityAndroidHostLifetimeReceipt) {
    let _: CapabilityPresentationInstallation = host
    let _: CapabilityPresentationJoinStatus = status
    let _: CapabilityPresentationLifetimeReceipt = receipt
}
func cannotConstruct(_ key: CapabilityAndroidHostLifetimeKey,
                     _ task: Task<Void, Never>, _ control: CapabilityAndroidLifetimeControl,
                     _ evidence: CapabilityAndroidHostFacadeCleanupEvidence) {
    _ = CapabilityAndroidHostTaskReturnEvidence(key: key)
    _ = CapabilityAndroidHostLifetimeCapsule(key: key, task: task, control: control)
    _ = CapabilityAndroidHostLifetimeKey(facade: key.facade, lifetime: key.lifetime, endpoint: key.endpoint)
    _ = CapabilityAndroidHostFacadeCleanupReceipt.validate(evidence, for: key)
    _ = CapabilityAndroidHostLifetimeReceipt.validate
    _ = CapabilityAndroidHostEndpointRetirementEvidence(key: key, callbackFence: 1, uiEntryFence: 1, facadeCleanup: evidence)
    _ = CapabilityAndroidHostFacadeCleanupEvidence(key: key, cleanupSerial: 1, finalEntrySerial: 1,
        bridgeSlotGeneration: 1, clearedExchangeGeneration: nil, clearedResourceStageRevision: 1)
}
