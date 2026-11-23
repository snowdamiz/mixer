
#if os(iOS)
extension GuestUIPresentation {
    public var s4ObservedNativeDisplay: Bool { observedNativeDisplay }
    var s4AttachmentObserver: (any CapabilityGuestUIAttachmentObserver)? { attachmentObserver }
}
#endif
