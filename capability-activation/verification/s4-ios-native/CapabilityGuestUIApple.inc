
#if os(iOS)
extension CapabilityGuestUIIOSController {
    fileprivate var s4ProbeAppeared: Bool? { probe?.appeared }
    fileprivate var s4ProbeHasAppeared: Bool? { probe?.s4HasAppeared }
}

extension GuestUIPresentation {
    public var s4NativeProbeAppeared: Bool? {
        (s4AttachmentObserver as? CapabilityGuestUIIOSController)?.s4ProbeAppeared
    }
    public var s4NativeProbeHasAppeared: Bool? {
        (s4AttachmentObserver as? CapabilityGuestUIIOSController)?.s4ProbeHasAppeared
    }
}
#endif
