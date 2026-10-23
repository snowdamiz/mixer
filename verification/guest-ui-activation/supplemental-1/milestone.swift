import MixerCapabilityActivation
import MixerGuest
@MainActor func probe(_ p: GuestUIPresentation, _ r: CapabilityGuestUIRuntime) async throws { try await r.reportMilestone("first_screen") }
