import CMixerUITransport
@testable import MixerCapabilityActivation
// Fixed verification edge object; product Swift is compiled separately without
// this symbol or any other verification-only declaration.
@_cdecl("mxish_swift_scalar_entry")
func symbolHostEntry(_ facade:UInt64,_ kind:UInt32)->Int32{
    for slot in 0..<16{
        if CapabilityAndroidRegistry.shared.record(slot:slot,facade:facade) != nil{
            return CapabilityGuestUIAndroidResources.scalarEntry(facade:facade,slot:slot,kind:kind)
        }
    }
    return Int32(MXUIT_STALE.rawValue)
}
