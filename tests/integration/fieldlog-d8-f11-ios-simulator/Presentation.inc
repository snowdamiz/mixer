#if os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE
    @Published internal private(set) var f11NativeRevision: UInt64?

    internal var f11UsesNoteRenderer: Bool {
        exchange?.requiresDeferredStartup == true
            && renderHost?.snapshot.document.root.children.first?.id == F11NativeNote.field
    }

    internal func f11PasteDisplay(host: MixerUIHost, attachment identity: CapabilityGuestUIAttachmentIdentity)
        -> CapabilityGuestUIDisplayTicket? {
        guard f11NativeRevision == 1, inputEnabled, renderHost === host,
              attachment === identity, let bindingIdentity, let ticket, ticket.revision == 1 else { return nil }
        let display = CapabilityGuestUIDisplayTicket(binding: bindingIdentity, attachment: identity, ticket: ticket)
        return isCurrentNativeDisplay(display) ? display : nil
    }

    internal func f11ActionDisplay() -> CapabilityGuestUIDisplayTicket? {
        guard f11NativeRevision == 2, inputEnabled, let bindingIdentity, let attachment, let ticket,
              ticket.revision == 2, lastEventResult?.generation == ticket.generation,
              lastEventResult?.sequence == 1, lastEventResult?.outcome == .delivered else { return nil }
        let display = CapabilityGuestUIDisplayTicket(binding: bindingIdentity, attachment: attachment, ticket: ticket)
        return f11OwnsActionDisplay(display) ? display : nil
    }

    internal func f11OwnsActionDisplay(_ display: CapabilityGuestUIDisplayTicket) -> Bool {
        f11NativeRevision == 2 && inputEnabled && display.ticket.revision == 2 && isCurrentNativeDisplay(display)
    }
#endif
// SECTION
#if os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE
                model.f11NativeRevision = nil
#endif
// SECTION
#if os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE
        if f11UsesNoteRenderer, attachment === identity, let bindingIdentity, let ticket,
           ticket.revision == 2, f11NativeRevision != 2 {
            let value = CapabilityGuestUIDisplayTicket(binding: bindingIdentity, attachment: identity, ticket: ticket)
            return isCurrentNativeDisplay(value) ? value : nil
        }
#endif
// SECTION
#if os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE
        if f11UsesNoteRenderer, value.ticket.revision == 2 {
            // The shipped UIKit probe also acknowledges the edited frame. Keep the
            // exchange's first-screen receipt single-use.
            guard observedNativeDisplay, f11NativeRevision != 2, isCurrentNativeDisplay(value) else { return false }
            f11NativeRevision = 2
            return true
        }
#endif
// SECTION
#if os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE
                    if presentation.f11UsesNoteRenderer {
                        F11NativeNote(presentation: presentation, host: host, attachment: attachment)
                            .frame(maxWidth: .infinity)
                            .frame(height: 212)
                    } else {
                        renderer(host, height: viewport.size.height)
                    }
#else
                    renderer(host, height: viewport.size.height)
#endif
