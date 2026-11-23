#if os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE
import MixerApple
@_spi(GuestUIV1) import MixerGuest
import MixerUI
import OSLog
import SwiftUI
import UIKit
import UniformTypeIdentifiers

@MainActor
struct F11NativeNote: UIViewRepresentable {
    static let field = "entry.f1100000-0000-4000-8000-000000000001.note"
    static let log = Logger(subsystem: "dev.mixer.fieldlog.f11simulator", category: "F11Paste")
    let presentation: GuestUIPresentation
    let host: MixerUIHost
    let attachment: CapabilityGuestUIAttachmentIdentity

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> UIStackView {
        let coordinator = context.coordinator
        let note = coordinator.note
        note.delegate = coordinator
        note.coordinator = coordinator
        note.font = .preferredFont(forTextStyle: .body)
        note.accessibilityIdentifier = "f11.note"
        note.accessibilityLabel = "Note"
        note.autocorrectionType = .no
        note.smartQuotesType = .no
        note.smartDashesType = .no
        note.smartInsertDeleteType = .no
        note.heightAnchor.constraint(equalToConstant: 160).isActive = true
        note.pasteConfiguration = UIPasteConfiguration(acceptableTypeIdentifiers: [UTType.utf8PlainText.identifier])

        let paste = coordinator.paste
        paste.target = note
        paste.accessibilityIdentifier = "f11.paste"
        paste.heightAnchor.constraint(equalToConstant: 44).isActive = true

        let layout = UIStackView(arrangedSubviews: [note, paste])
        layout.axis = .vertical
        layout.spacing = 8
        return layout
    }

    static func dismantleUIView(_ view: UIStackView, coordinator: Coordinator) {
        coordinator.current = nil
        coordinator.request = nil
        coordinator.paste.target = nil
    }

    func updateUIView(_ view: UIStackView, context: Context) {
        let coordinator = context.coordinator
        let document = host.snapshot.document
        let value = document.root.children.first?.properties["value"]?.string ?? ""
        if coordinator.revision != document.revision {
            coordinator.note.text = value
            coordinator.revision = document.revision
            coordinator.request = nil
            coordinator.submitted = false
        }
        let display = presentation.f11PasteDisplay(host: host, attachment: attachment)
        coordinator.note.isEditable = display != nil
        coordinator.current = nil
        coordinator.paste.isEnabled = display != nil && !coordinator.submitted && coordinator.request == nil
        coordinator.observeFrame(nativeRevision: presentation.f11NativeRevision)
        guard let display, let identity = host.snapshot.identity(for: Self.field) else { return }
        let send = presentation.actionHandler(host: host, attachment: attachment)
        coordinator.current = { [weak presentation, weak host] in
            guard let presentation, let host,
                  presentation.renderHost === host, presentation.inputEnabled,
                  presentation.isCurrentNativeDisplay(display) else { return nil }
            return { complete in
                let envelope = UIEventEnvelope(revision: display.ticket.revision, identity: identity,
                    event: .textChange, value: .string(complete))
                guard let action = try? host.route(envelope) else { return .rejected }
                let accepted = presentation.lifecycleObservation?.counters.acceptedEvents
                send(action)
                return presentation.lifecycleObservation?.counters.acceptedEvents == accepted ? .unconfirmed : .accepted
            }
        }
    }

    @MainActor
    final class PasteTextView: UITextView {
        weak var coordinator: Coordinator?

        override func canPaste(_ itemProviders: [NSItemProvider]) -> Bool {
            itemProviders.count == 1 && itemProviders[0].hasItemConformingToTypeIdentifier(UTType.utf8PlainText.identifier)
        }

        override func paste(itemProviders: [NSItemProvider]) {
            coordinator?.receive(itemProviders)
        }
    }

    enum Route: String { case rejected, unconfirmed, accepted }

    @MainActor
    final class Coordinator: NSObject, UITextViewDelegate {
        let note = PasteTextView()
        let paste: UIPasteControl = {
            let configuration = UIPasteControl.Configuration()
            configuration.displayMode = .iconAndLabel
            return UIPasteControl(configuration: configuration)
        }()
        var revision: UInt64?
        var submitted = false
        var current: (@MainActor () -> (@MainActor (String) -> Route)?)?
        var request: UUID?
        private var insertionRange: NSRange?
        private var pasteStatus = "waiting"
        private var editStatus = "waiting"
        private var routeStatus = "waiting"
        private var frameStatus = "waiting"

        func receive(_ providers: [NSItemProvider]) {
            guard note.canPaste(providers) else { pasteStatus = "type-rejected"; report(); return }
            guard request == nil, !submitted, note.window != nil, let authority = current, authority() != nil else {
                pasteStatus = "inactive"; report(); return
            }
            let id = UUID()
            request = id
            paste.isEnabled = false
            let selection = note.selectedRange
            pasteStatus = "provider focus=\(note.isFirstResponder) selection=\(bounded(selection.location)),\(bounded(selection.length))"
            report()
            _ = providers[0].loadDataRepresentation(forTypeIdentifier: UTType.utf8PlainText.identifier) { [weak self] data, error in
                Task { @MainActor [weak self] in
                    self?.finish(id, data: error == nil ? data : nil, authority: authority)
                }
            }
        }

        private func finish(_ id: UUID, data: Data?, authority: @MainActor () -> (@MainActor (String) -> Route)?) {
            guard request == id else { return }
            request = nil
            guard note.window != nil, let submit = authority() else { pasteStatus = "stale"; report(); return }
            guard let data, data.elementsEqual("Edited".utf8), let suffix = String(data: data, encoding: .utf8) else {
                pasteStatus = "bytes-rejected"
                paste.isEnabled = true
                report()
                return
            }
            pasteStatus = "bytes-accepted"
            let before = note.text ?? ""
            let end = note.endOfDocument
            let offset = note.offset(from: note.beginningOfDocument, to: end)
            guard offset == before.utf16.count, let range = note.textRange(from: end, to: end) else {
                editStatus = "range-rejected"; report(); return
            }
            submitted = true
            insertionRange = NSRange(location: offset, length: 0)
            note.replace(range, withText: suffix)
            insertionRange = nil
            let edited = note.text ?? ""
            guard edited.utf8.elementsEqual((before + suffix).utf8) else {
                editStatus = "edit-rejected"; report(); return
            }
            editStatus = "inserted=\(bounded(offset)),0 bytes=\(data.count)"
            routeStatus = submit(edited).rawValue
            report()
        }

        func textView(_ textView: UITextView, shouldChangeTextIn range: NSRange, replacementText text: String) -> Bool {
            insertionRange == range && text.utf8.elementsEqual("Edited".utf8)
        }

        func observeFrame(nativeRevision: UInt64?) {
            let frame = "document=\(revision == 2 ? 2 : 1) native=\(nativeRevision == 2 ? 2 : nativeRevision == 1 ? 1 : 0)"
            guard frameStatus != frame else { return }
            frameStatus = frame
            report()
        }

        private func report() {
            let status = "paste=\(pasteStatus) edit=\(editStatus) route=\(routeStatus) \(frameStatus)"
            paste.accessibilityValue = status
            F11NativeNote.log.notice("\(status, privacy: .public)")
        }

        private func bounded(_ number: Int) -> Int {
            (0...1024).contains(number) ? number : -1
        }
    }
}
#endif
