#if os(macOS) && MIXER_PRIVATE_FIELDLOG_EDITOR && MIXER_F11_HOST_ACTION_FIXTURE
    internal func f11ActionDisplay(attachment identity: CapabilityGuestUIAttachmentIdentity)
        -> CapabilityGuestUIDisplayTicket? {
        guard observedNativeDisplay, inputEnabled, let bindingIdentity, let ticket,
              ticket.revision == 2, lastEventResult?.generation == ticket.generation,
              lastEventResult?.sequence == 1, lastEventResult?.outcome == .delivered else { return nil }
        let display = CapabilityGuestUIDisplayTicket(binding: bindingIdentity, attachment: identity, ticket: ticket)
        return isCurrentNativeDisplay(display) ? display : nil
    }

    internal func f11OwnsActionDisplay(_ display: CapabilityGuestUIDisplayTicket) -> Bool {
        inputEnabled && display.ticket.revision == 2 && isCurrentNativeDisplay(display)
    }
#endif
