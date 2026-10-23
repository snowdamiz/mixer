#if canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)
import CMixerUITransport
// Verification-only fixed native command edge, linked only in harness builds.
// Scalar lookup precedes the actual product helper; no weak promotion occurs.
@_cdecl("mxish_swift_scalar_entry")
func stage4HostScalarEntry(_ facade: UInt64, _ kind: UInt32) -> Int32 {
    for slot in 0..<16 {
        if CapabilityAndroidRegistry.shared.record(slot: slot, facade: facade) != nil {
            return CapabilityGuestUIAndroidResources.scalarEntry(facade: facade, slot: slot, kind: kind)
        }
    }
    return Int32(MXUIT_STALE.rawValue)
}
#endif
