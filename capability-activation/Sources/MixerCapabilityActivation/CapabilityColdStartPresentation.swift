@_spi(GuestUIV1) import MixerGuest

protocol CapabilityColdStartPresentation: Sendable {
    func bindForStartup(_ exchange: GuestUIExchangeV1) async throws -> any CapabilityObservedPresentation
    func requestFinalClose(_ cause: CapabilityAttemptLocalStop)
    func finishForClose() async -> Bool
}

protocol CapabilityObservedPresentation: Sendable {
    func moveForObservation() -> (any CapabilityObservedPresentation)?
    func isBound(to exchange: GuestUIExchangeV1) -> Bool
    func finishObservation() async -> CapabilityPresentationJoinStatus
}

extension CapabilityGuestUIPresentationBinding: CapabilityColdStartPresentation {
    func bindForStartup(_ exchange: GuestUIExchangeV1) async throws -> any CapabilityObservedPresentation {
        try await bind(exchange)
    }

    func finishForClose() async -> Bool {
        await finishFinalClose(using: takeFinalJoinPermit()).isRetired
    }
}

extension CapabilityPresentationInstallation: CapabilityObservedPresentation {
    func moveForObservation() -> (any CapabilityObservedPresentation)? { move() }
    func isBound(to exchange: GuestUIExchangeV1) -> Bool { lifetime?.isBound(to: exchange) == true }
    func finishObservation() async -> CapabilityPresentationJoinStatus { await finish() }
}
