#if os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE
    @Published internal private(set) var f11NativeRevision: UInt64?

    internal let f11Trace = F11DisplayTrace()

    internal func f11CurrentDisplayRefusal(_ value: CapabilityGuestUIDisplayTicket) -> String? {
        let snapshot = exchange?.snapshot()
        return F11DisplayAdmission(bindingMatches: value.binding === bindingIdentity,
            attachmentMatches: value.attachment === attachment, current: ticket.map(f11Stamp),
            offered: f11Stamp(value.ticket), exchangeExists: exchange != nil, stopped: snapshot?.stop != nil,
            effectsConfirmed: snapshot?.effectsConfirmed == true, exchangeGeneration: snapshot?.generation,
            displayedRevision: snapshot?.displayedRevision).refusal
    }

    internal func f11TicketRefusal(_ identity: CapabilityGuestUIAttachmentIdentity) -> String? {
        guard attachment === identity else { return "attachment-mismatch" }
        guard !observedNativeDisplay || (f11UsesNoteRenderer && ticket?.revision == 2 && f11NativeRevision != 2)
        else { return "already-observed" }
        guard let bindingIdentity else { return "no-binding" }
        guard let ticket else { return "no-current-ticket" }
        return f11CurrentDisplayRefusal(.init(binding: bindingIdentity, attachment: identity, ticket: ticket))
    }

    private func f11Stamp(_ value: GuestUIPresentationTicketV1) -> F11DisplayStamp {
        .init(generation: value.generation, serial: value.frameSerial, revision: value.revision)
    }

    internal var f11DisplayFacts: String {
        let snapshot = exchange?.snapshot()
        let stamp = ticket.map { "\($0.generation),\($0.frameSerial),\($0.revision)" } ?? "-"
        return "observed=\(observedNativeDisplay) input=\(inputEnabled) f11Renderer=\(f11UsesNoteRenderer) model=\(stamp)"
            + " effects=\(snapshot?.effectsConfirmed == true) stopped=\(snapshot?.stop != nil)"
            + " generation=\(snapshot?.generation ?? 0) displayed=\(snapshot?.displayedRevision ?? 0)"
    }

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
            f11Trace.transition("revision-two-observed")
            return true
        }
#endif
// SECTION
#if os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE
                    if presentation.f11UsesNoteRenderer {
                        F11NativeNote(presentation: presentation, host: host, attachment: attachment,
                            document: host.snapshot.document,
                            pasteDisplay: presentation.f11PasteDisplay(host: host, attachment: attachment))
                            .frame(maxWidth: .infinity)
                            .frame(height: 212)
                    } else {
                        renderer(host, height: viewport.size.height)
                    }
#else
                    renderer(host, height: viewport.size.height)
#endif
